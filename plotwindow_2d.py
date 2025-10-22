import base64
import io

from offline_folium import offline # must be before importing folium, DO NOT REMOVE
import folium  # must be after importing offline folium
import numpy as np
import numpy.ma as ma
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineUrlScheme
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QVBoxLayout, QWidget, QHBoxLayout, QLabel, QSpinBox, QSizePolicy, QCheckBox, QMessageBox
from matplotlib import pyplot as plt
from netCDF4 import Dataset, num2date
from cartopy import crs as ccrs
import matplotlib.style as mplstyle
from matplotlib import use as mpluse

from plotbackend import Backend2d, WebChannelJS

mplstyle.use('fast')
mpluse("agg")

import utils


class PlotWindow2d(QWidget):
    def __init__(self, file_name, variable_name, file_path):
        super().__init__()

        self.setWindowTitle(variable_name + " - NetSeeDF")
        self.setMinimumSize(650, 600)
        self.file_path = file_path
        self.variable_name = variable_name
        self.can_convert_datetime = False
        self.has_units = False
        self.variable_units = None
        self.tunits = None
        self.calendar = None
        self.units_are_kelvin = False

        ncfile = Dataset(file_path, "r")
        variable_data = ncfile.variables[variable_name]
        self.fill_value = variable_data.get_fill_value()

        # defaults for the indices of dimensions in the NetCDF file data
        x_dim_index = 1
        y_dim_index = 0

        # try to find which dimension is at which index in the NetCDF data
        if "lon" in variable_data.dimensions:
            x_dim_index = variable_data.dimensions.index("lon")
        elif "longitude" in variable_data.dimensions:
            x_dim_index = variable_data.dimensions.index("longitude")
        elif "X" in variable_data.dimensions:
            x_dim_index = variable_data.dimensions.index("X")

        if "lat" in variable_data.dimensions:
            y_dim_index = variable_data.dimensions.index("lat")
        elif "latitude" in variable_data.dimensions:
            y_dim_index = variable_data.dimensions.index("latitude")
        elif "Y" in variable_data.dimensions:
            y_dim_index = variable_data.dimensions.index("Y")

        # if above guesses fail, make sure the selection makes sense (all indexes are distinct)
        if x_dim_index == 1:
            y_dim_index = 0
        else:
            y_dim_index = 1

        # get x, y and time axis variable data
        self.xdata = ncfile.variables[variable_data.dimensions[x_dim_index]][:]
        self.ydata = ncfile.variables[variable_data.dimensions[y_dim_index]][:]

        # GUI setup
        layout = QVBoxLayout()
        file_label = QLabel("File: \t\t" + file_name)
        layout.addWidget(file_label)
        var_label = QLabel("Variable: \t" + variable_name)
        layout.addWidget(var_label)

        # display units of the variable if given in the NetCDF file
        try:
            unit_label = QLabel("Units: \t\t" + variable_data.units)
            self.has_units = True
            self.variable_units = variable_data.units
            layout.addWidget(unit_label)
        except Exception:
            pass

        # display description of the variable if given in the NetCDF file
        try:
            desc_label = QLabel("Description: \t" + variable_data.description, wordWrap=True)
            layout.addWidget(desc_label)
        except Exception:
            pass

        scheme = QWebEngineUrlScheme(b'qrc')
        scheme.setFlags(QWebEngineUrlScheme.Flag.LocalScheme | QWebEngineUrlScheme.Flag.LocalAccessAllowed)
        QWebEngineUrlScheme.registerScheme(scheme)

        # folium map
        self.map = folium.Map(location=[0, 0], zoom_start=1)
        self.map._name = "folium"
        self.map._id = "1"

        self.view = QWebEngineView()
        self.view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        mapwidget = QWidget()
        maplayout = QHBoxLayout()
        mapwidget.setLayout(maplayout)
        maplayout.addWidget(self.view)

        # intial data load
        masked_data = ma.masked_equal(variable_data, self.fill_value)

        ncfile.close()

        image, colorbar = self.getb64image(masked_data)

        # map raster layer
        xmin, ymin, xmax, ymax = np.min(self.xdata), np.min(self.ydata), np.max(self.xdata), np.max(self.ydata)
        if ymin < -85:
            ymin = -85
        if ymax > 85:
            ymax = 85

        folium.raster_layers.ImageOverlay(
            image="data:image/png;base64," + image,
            bounds=[[ymin, xmin], [ymax, xmax]],
            opacity=0.5
        ).add_to(self.map)

        folium.FitOverlays().add_to(self.map)  # fit the view to the overlay size

        # setup QWebChannel, initialize backend instance and register the channel so the JS instance can access the backend object
        self.channel = QWebChannel()
        self.backend = Backend2d(self.xdata, self.ydata, masked_data, self.show_map_popup)
        self.channel.registerObject('backend', self.backend)
        self.view.page().setWebChannel(self.channel)

        with open("qwebchannel.js") as f:
            webchanneljs = f.read()

        scriptelement = folium.Element('<script>' + webchanneljs + '</script>')
        self.map.get_root().html.add_child(scriptelement)
        self.map.add_child(WebChannelJS())

        html_data = self.map.get_root().render()
        self.view.setHtml(html_data)  # load the html

        # display colorbar
        qimage = QImage.fromData(colorbar)
        pixmap = QPixmap.fromImage(qimage)
        cbar = QLabel()
        cbar.setPixmap(pixmap)
        self.cbar = cbar

        maplayout.addWidget(cbar)

        layout.addWidget(mapwidget)

        self.setLayout(layout)

    def show_map_popup(self, lat, lon, value):
        js_code = """L.popup()
                    .setLatLng(L.latLng({latval},{lonval}))
                    .setContent('{latval}°, {lonval}°<br>{pointval}')
                    .openOn(folium_1);""".format(latval=lat, lonval=lon, pointval=value)
        self.view.page().runJavaScript(js_code)

    def getb64image(self, image_data):
        image = io.BytesIO()
        colorbar = io.BytesIO()

        ax = plt.axes(projection=ccrs.epsg(3857))

        source_crs = ccrs.PlateCarree()

        if self.has_units:
            if self.variable_units in ["mm", "day"]:  # set the color scale minimum value to 0
                mpb = ax.pcolormesh(self.xdata, self.ydata, image_data, cmap="inferno", transform=source_crs, vmin=0)
            else:
                mpb = ax.pcolormesh(self.xdata, self.ydata, image_data, cmap="inferno", transform=source_crs)
        else:
            mpb = ax.pcolormesh(self.xdata, self.ydata, image_data, cmap="inferno", transform=source_crs)

        xmin, ymin, xmax, ymax = np.min(self.xdata), np.min(self.ydata), np.max(self.xdata), np.max(self.ydata)
        ymin = max(ymin, -85)
        ymax = min(ymax, 85)
        ax.set_extent([xmin, xmax, ymin, ymax], crs=source_crs)
        ax.axis("off")
        plt.savefig(image, format="png", bbox_inches="tight", pad_inches=0, dpi=400)

        fig, ax = plt.subplots()
        cbar = fig.colorbar(mpb, ax=ax)
        if self.has_units:
            cbar.set_label(self.variable_units)
        ax.remove()
        fig.savefig(colorbar, format="png", bbox_inches="tight")

        plt.close("all")
        image.seek(0)
        colorbar.seek(0)
        return base64.b64encode(image.read()).decode("utf-8"), colorbar.read()