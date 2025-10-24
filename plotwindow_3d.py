import base64
import io

from offline_folium import offline # must be before importing folium, DO NOT REMOVE
import folium  # must be after importing offline folium
import numpy as np
import numpy.ma as ma
from PySide6.QtCore import Qt
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

from plotbackend import WebChannelJS, Backend3d

mplstyle.use('fast')
mpluse("agg")

import utils


class PlotWindow3d(QWidget):
    def __init__(self, file_name, variable_name, file_path):
        super().__init__()

        self.setWindowTitle(variable_name + " - NetSeeDF")
        self.setMinimumSize(650, 600)
        self.view = 0
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
        slice_dim_index = 0
        x_dim_index = 1
        y_dim_index = 2

        # try to find which dimension is at which index in the NetCDF data
        if "time" in variable_data.dimensions:
            slice_dim_index = variable_data.dimensions.index("time")
        elif "Time" in variable_data.dimensions:
            slice_dim_index = variable_data.dimensions.index("Time")
        elif "T" in variable_data.dimensions:
            slice_dim_index = variable_data.dimensions.index("T")
        elif "valid_time" in variable_data.dimensions:
            slice_dim_index = variable_data.dimensions.index("valid_time")

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
        if (x_dim_index == 1 and y_dim_index == 2) or (x_dim_index == 2 and y_dim_index == 1):
            slice_dim_index = 0
        elif (x_dim_index == 0 and y_dim_index == 2) or (x_dim_index == 2 and y_dim_index == 0):
            slice_dim_index = 1
        elif (x_dim_index == 0 and y_dim_index == 1) or (x_dim_index == 1 and y_dim_index == 0):
            slice_dim_index = 2

        self.slice_dim_index = slice_dim_index

        # get x, y and time axis variable data
        self.xdata = ncfile.variables[variable_data.dimensions[x_dim_index]][:]
        self.ydata = ncfile.variables[variable_data.dimensions[y_dim_index]][:]
        self.tdata = ncfile.variables[variable_data.dimensions[slice_dim_index]][:]

        try:
            self.calendar = ncfile.variables[variable_data.dimensions[slice_dim_index]].calendar
        except Exception:
            pass

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

        slice_selector_widget = QWidget()
        slice_selector_layout = QHBoxLayout()
        slice_selector_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        slice_selector_widget.setLayout(slice_selector_layout)
        slice_selector_layout.addWidget(QLabel(variable_data.dimensions[slice_dim_index] + ": "))
        slice_spinner = QSpinBox()
        slice_spinner.setMinimum(0)
        slice_spinner.setMaximum(variable_data.shape[
                                     slice_dim_index] - 1)  # set max index to size of the axis corresponding to the slicing variable
        slice_spinner.setValue(0)
        slice_spinner.valueChanged.connect(self.update_map)
        self.slice_spinner = slice_spinner
        slice_selector_layout.addWidget(slice_spinner)
        slice_selector_layout.addWidget(QLabel(" of " + str(variable_data.shape[slice_dim_index] - 1)))

        try:
            units = ncfile.variables[
                variable_data.dimensions[slice_dim_index]].units  # get units of the slicing variable
            self.tunits = units
        except Exception:  # in case the units are not included in the file
            pass

        try:
            slice_date = num2date(self.tdata[0], self.tunits, self.calendar)
            self.slice_date_label = QLabel(" =  " + str(slice_date))
            slice_selector_layout.addWidget(self.slice_date_label)
            self.can_convert_datetime = True
        except Exception:  # in case the calendar or units are not available
            pass

        layout.addWidget(slice_selector_widget)

        if self.has_units:
            if self.variable_units == "K":
                temp_convert_widget = QWidget()
                temp_convert_layout = QHBoxLayout()
                temp_convert_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
                temp_convert_widget.setLayout(temp_convert_layout)
                temp_convert_checkbox = QCheckBox()
                temp_convert_checkbox.checkStateChanged.connect(self.on_convert_temp)
                self.temp_convert_checkbox = temp_convert_checkbox
                temp_convert_layout.addWidget(temp_convert_checkbox)
                temp_convert_layout.addWidget(QLabel("convert to °C"))
                self.units_are_kelvin = True
                layout.addWidget(temp_convert_widget)

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
        if self.slice_dim_index == 0:  # select the slice and read it into memory from disk
            sliced_data = variable_data[0, :, :]
        elif self.slice_dim_index == 1:
            sliced_data = variable_data[:, 0, :]
        else:
            sliced_data = variable_data[:, :, 0]

        ncfile.close()

        sliced_data = ma.masked_equal(sliced_data, self.fill_value)

        image, colorbar = self.getb64image(sliced_data)

        # map raster layer
        xmin, ymin, xmax, ymax = np.min(self.xdata), np.min(self.ydata), np.max(self.xdata), np.max(self.ydata)
        if ymin < -85:
            ymin = -85
        if ymax > 85:
            ymax = 85

        folium.raster_layers.ImageOverlay(
            image="data:image/png;base64," + image,
            bounds=[[ymin, xmin], [ymax, xmax]],
            opacity=0.6
        ).add_to(self.map)

        folium.FitOverlays().add_to(self.map)  # fit the view to the overlay size

        # setup QWebChannel, initialize backend instance and register the channel so the JS instance can access the backend object
        self.channel = QWebChannel()
        self.backend = Backend3d(file_path, variable_name, self.xdata, self.ydata, self.tdata, self.tunits, self.calendar, x_dim_index, y_dim_index,
                                       slice_dim_index, self.show_map_popup, self)
        self.backend.set_data(sliced_data)
        self.channel.registerObject('backend', self.backend)
        self.view.page().setWebChannel(self.channel)

        with open("qwebchannel.js") as f:
            webchanneljs = f.read()

        scriptelement = folium.Element('<script>' + webchanneljs + '</script>')
        self.map.get_root().html.add_child(scriptelement)
        self.map.add_child(WebChannelJS())

        html_data = self.map.get_root().render()
        self.view.setHtml(html_data)  # load the html

        # display colorbar and min, max fields
        qimage = QImage.fromData(colorbar)
        pixmap = QPixmap.fromImage(qimage)
        cbar = QLabel()
        cbar.setPixmap(pixmap)
        self.cbar = cbar

        cbarcontainer = QWidget()
        cbarcontainer_layout = QVBoxLayout()

        maxcontainer = QWidget()
        mincontainer = QWidget()

        cbarcontainer_layout.addWidget(maxcontainer)
        cbarcontainer_layout.addWidget(cbar)
        cbarcontainer_layout.addWidget(mincontainer)

        maplayout.addWidget(cbar)

        layout.addWidget(mapwidget)

        self.setLayout(layout)

    def show_map_popup(self, lat, lon, value):
        js_code = """L.popup()
                    .setLatLng(L.latLng({latval},{lonval}))
                    .setContent('{latval}°, {lonval}°<br>{pointval}<br><button onclick="window.backend.on_export_requested();">Export data for this point</button>')
                    .openOn(folium_1);""".format(latval=lat, lonval=lon, pointval=value)
        self.view.page().runJavaScript(js_code)

    def close_map_popups(self):
        self.view.page().runJavaScript("folium_1.closePopup();")

    def update_map(self):
        slice_index = self.slice_spinner.value()  # get the index of the slice from the spinner

        if self.can_convert_datetime:
            try:
                slice_date = num2date(self.tdata[slice_index], self.tunits, self.calendar)
                self.slice_date_label.setText(" =  " + str(slice_date))
            except Exception:
                pass

        sliced_data = utils.slice_data(self.file_path, self.variable_name, self.slice_dim_index, slice_index)

        sliced_data = ma.masked_equal(sliced_data, self.fill_value)  # mask missing values (given by the _FillValue in the NetCDF file)

        if self.has_units:
            if self.units_are_kelvin:
                if self.temp_convert_checkbox.isChecked():
                    try:
                        sliced_data = sliced_data - 273.15
                    except Exception:
                        self.temp_convert_checkbox.setChecked(False)
                        dlg = QMessageBox(self)
                        dlg.setWindowTitle("NetSeeDF message")
                        dlg.setText("There was an error while converting to degrees Celsius!")
                        dlg.exec()
                        return

        self.backend.set_data(sliced_data)

        # generate images
        image, colorbar = self.getb64image(sliced_data)

        # update image overlay layer on the folium map
        js_code = 'var overlay = null;folium_1.eachLayer(function(layer){if(layer instanceof L.ImageOverlay){overlay = layer;}});if(overlay !== null){overlay.setUrl("data:image/png;base64,' + image + '");}'
        self.view.page().runJavaScript(js_code)

        qimage = QImage.fromData(colorbar)
        pixmap = QPixmap.fromImage(qimage)
        self.cbar.setPixmap(pixmap)

        self.close_map_popups()

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
            if self.units_are_kelvin:
                if self.temp_convert_checkbox.isChecked():
                    cbar.set_label("°C")
                else:
                    cbar.set_label(self.variable_units)
            else:
                cbar.set_label(self.variable_units)
        ax.remove()
        fig.savefig(colorbar, format="png", bbox_inches="tight")

        plt.close("all")
        image.seek(0)
        colorbar.seek(0)
        return base64.b64encode(image.read()).decode("utf-8"), colorbar.read()

    def on_convert_temp(self):
        self.update_map()