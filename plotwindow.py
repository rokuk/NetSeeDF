import io
from matplotlib import pyplot as plt
import numpy as np
import numpy.ma as ma
import folium
from PyQt6.QtCore import QUrl
from netCDF4 import Dataset
import cartopy.crs as ccrs
from cartopy.img_transform import warp_array
from PyQt6.QtWidgets import QVBoxLayout, QWidget, QHBoxLayout, QLabel, QSpinBox
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt
import matplotlib
import base64
import utils


class PlotWindow(QWidget):
    def __init__(self, file_name, variable_name, file_path):
        super().__init__()

        self.setWindowTitle(variable_name + " - NetSeeDF")
        self.setMinimumSize(1300, 600)
        self.view = 0

        ncfile = Dataset(file_path, "r")
        variable_data = ncfile.variables[variable_name]
        data = np.array(variable_data[:]) # cast data to a numpy array

        self.fill_value = variable_data.get_fill_value()
        self.data = data

        # defaults for the indices of dimensions in the NetCDF file data
        slice_dim_index = 0
        x_dim_index = 1
        y_dim_index = 2

        # try to find which dimension is at which index in the NetCDF data
        if "time" in variable_data.dimensions:
            slice_dim_index = variable_data.dimensions.index("time")
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

        # get x and y axis variable data
        self.xdata = ncfile.variables[variable_data.dimensions[x_dim_index]][:]
        self.ydata = ncfile.variables[variable_data.dimensions[y_dim_index]][:]

        # GUI setup
        layout = QVBoxLayout()
        var_label = QLabel("Variable: \t" + variable_name)
        layout.addWidget(var_label)
        file_label = QLabel("File: \t\t" + file_name)
        layout.addWidget(file_label)

        slice_selector_widget = QWidget()
        slice_selector_layout = QHBoxLayout()
        slice_selector_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        slice_selector_widget.setLayout(slice_selector_layout)
        slice_selector_layout.addWidget(QLabel("Slice index: "))
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
            slice_units = QLabel("   units: " + units)
            slice_selector_layout.addWidget(slice_units)
        except Exception:  # in case the units are not included in the file
            pass
        layout.addWidget(slice_selector_widget)

        # Folium map
        self.map = folium.Map(location=[0, 0], zoom_start=1)
        self.map._name = "folium"
        self.map._id = "1"
        #self.colormap = matplotlib.colormaps["inferno"]
        self.view = QWebEngineView()
        layout.addWidget(self.view)

        # Intial data load
        sliced_data = self.data.take(0, axis=self.slice_dim_index)
        sliced_data = ma.masked_equal(sliced_data, self.fill_value)

        # Map raster layer
        folium.raster_layers.ImageOverlay(
            image="data:image/png;base64," + self.getb64image(sliced_data),
            bounds=[[np.min(self.ydata), np.min(self.xdata)], [np.max(self.ydata), np.max(self.xdata)]],
            opacity=0.5
        ).add_to(self.map)

        folium.FitOverlays().add_to(self.map)  # fit the map view to the overlay size

        html_data = self.map.get_root().render()
        self.view.setHtml(html_data, QUrl("about:blank"))

        self.setLayout(layout)

    def update_map(self):
        sliced_data = self.data.take(self.slice_spinner.value(),
                                     axis=self.slice_dim_index)  # subset data with the current slice index
        sliced_data = ma.masked_equal(sliced_data, self.fill_value) # mask missing values (given by the _FillValue in the NetCDF file)

        # update image overlay layer on the folium map
        js_code = 'var overlay = null;folium_1.eachLayer(function(layer){if(layer instanceof L.ImageOverlay){overlay = layer;}});if(overlay !== null){overlay.setUrl("data:image/png;base64,' + self.getb64image(sliced_data) + '");}'
        self.view.page().runJavaScript(js_code)

    def getb64image(self, image_data):
        image = io.BytesIO()
        plt.pcolormesh(self.xdata, self.ydata, image_data, cmap="inferno")
        plt.axis("off")
        plt.savefig(image, format="png", bbox_inches="tight")
        plt.close()
        image.seek(0)
        return base64.b64encode(image.read()).decode("utf-8")