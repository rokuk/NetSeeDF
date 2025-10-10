import base64
import io

import folium  # must be after importing offline folium
import numpy as np
import numpy.ma as ma
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWebEngineCore import QWebEngineUrlScheme
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QVBoxLayout, QWidget, QHBoxLayout, QLabel, QSpinBox
from folium import Element
from matplotlib import pyplot as plt
from netCDF4 import Dataset, num2date

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

        ncfile = Dataset(file_path, "r")
        variable_data = ncfile.variables[variable_name]
        data = np.array(variable_data[:])  # cast data to a numpy array

        self.fill_value = variable_data.get_fill_value()
        self.data = data
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

        if "lon" in variable_data.dimensions:
            x_dim_index = variable_data.dimensions.index("lon")
        elif "X" in variable_data.dimensions:
            x_dim_index = variable_data.dimensions.index("X")

        if "lat" in variable_data.dimensions:
            y_dim_index = variable_data.dimensions.index("lat")
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

        slice_selector_widget = QWidget()
        slice_selector_layout = QHBoxLayout()
        slice_selector_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        slice_selector_widget.setLayout(slice_selector_layout)
        slice_selector_layout.addWidget(QLabel("Slice: "))
        slice_selector_layout.addWidget(QLabel(variable_data.dimensions[slice_dim_index] + "  ="))
        slice_spinner = QSpinBox()
        slice_spinner.setMinimum(0)
        slice_spinner.setMaximum(variable_data.shape[
                                     slice_dim_index] - 1)  # set max index to size of the axis corresponding to the slicing variable
        slice_spinner.setValue(0)
        slice_spinner.valueChanged.connect(self.update_map)
        self.slice_spinner = slice_spinner
        slice_selector_layout.addWidget(slice_spinner)

        try:
            units = ncfile.variables[
                variable_data.dimensions[slice_dim_index]].units  # get units of the slicing variable
            self.tunits = units
        except Exception:  # in case the units are not included in the file
            pass

        try:
            slice_date = num2date(self.tdata[0], self.tunits, self.calendar)
            self.slice_date_label = QLabel(str(slice_date))
            slice_selector_layout.addWidget(self.slice_date_label)
            self.can_convert_datetime = True
        except Exception:  # in case the calendar or units are not available
            pass

        layout.addWidget(slice_selector_widget)

        ncfile.close()

        scheme = QWebEngineUrlScheme(b'qrc')
        scheme.setFlags(QWebEngineUrlScheme.Flag.LocalScheme | QWebEngineUrlScheme.Flag.LocalAccessAllowed)
        QWebEngineUrlScheme.registerScheme(scheme)

        # Folium map
        self.map = folium.Map(location=[0, 0], zoom_start=1)
        self.map._name = "folium"
        self.map._id = "1"

        self.view = QWebEngineView()
        mapwidget = QWidget()
        maplayout = QHBoxLayout()
        mapwidget.setLayout(maplayout)
        maplayout.addWidget(self.view)

        # Intial data load
        sliced_data = self.data.take(0, axis=self.slice_dim_index)
        sliced_data = ma.masked_equal(sliced_data, self.fill_value)

        image, colorbar = self.getb64image(sliced_data)

        # map raster layer
        folium.raster_layers.ImageOverlay(
            image="data:image/png;base64," + image,
            bounds=[[np.min(self.ydata), np.min(self.xdata)], [np.max(self.ydata), np.max(self.xdata)]],
            opacity=0.5
        ).add_to(self.map)

        folium.FitOverlays().add_to(self.map)  # fit the view to the overlay size

        # setup QWebChannel, initialize backend instance and register the channel so the JS instance can access the backend object
        self.channel = QWebChannel()
        self.backend = utils.Backend(sliced_data, self.data, self.xdata, self.ydata, self.tdata, self.tunits, self.calendar, x_dim_index, y_dim_index,
                                     slice_dim_index, self.show_map_popup, self)
        self.channel.registerObject('backend', self.backend)
        self.view.page().setWebChannel(self.channel)

        with open("qwebchannel.js") as f:
            webchanneljs = f.read()

        scriptelement = Element('<script>' + webchanneljs + '</script>')
        self.map.get_root().html.add_child(scriptelement)
        self.map.add_child(utils.WebChannelJS())

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
                self.slice_date_label.setText(str(slice_date))
            except Exception:
                pass

        sliced_data = self.data.take(slice_index, axis=self.slice_dim_index)  # subset data with the current slice index
        sliced_data = ma.masked_equal(sliced_data,
                                      self.fill_value)  # mask missing values (given by the _FillValue in the NetCDF file)
        self.backend.set_data(sliced_data)  # send the sliced data to the backend instance

        # generate images
        image, colorbar = self.getb64image(sliced_data)

        # update image overlay layer on the folium map
        js_code = 'var overlay = null;folium_1.eachLayer(function(layer){if(layer instanceof L.ImageOverlay){overlay = layer;}});if(overlay !== null){overlay.setUrl("data:image/png;base64,' + image + '");}'
        self.view.page().runJavaScript(js_code)

        qimage = QImage.fromData(colorbar)
        pixmap = QPixmap.fromImage(qimage)
        self.cbar.setPixmap(pixmap)

    def getb64image(self, image_data):
        image = io.BytesIO()
        colorbar = io.BytesIO()

        plt.figure()

        if self.has_units:
            if self.variable_units in ["mm", "day"]: # set the color scale minimum value to 0
                mpb = plt.pcolormesh(self.xdata, self.ydata, image_data, cmap="inferno", shading="nearest", vmin=0)
            else:
                mpb = plt.pcolormesh(self.xdata, self.ydata, image_data, cmap="inferno", shading="nearest")
        else:
            mpb = plt.pcolormesh(self.xdata, self.ydata, image_data, cmap="inferno", shading="nearest")

        plt.axis("off")
        plt.savefig(image, format="png", bbox_inches="tight")

        fig, ax = plt.subplots()
        fig.colorbar(mpb, ax=ax)
        ax.remove()
        fig.savefig(colorbar, format="png", bbox_inches="tight")

        plt.close("all")
        image.seek(0)
        colorbar.seek(0)
        return base64.b64encode(image.read()).decode("utf-8"), colorbar.read()
