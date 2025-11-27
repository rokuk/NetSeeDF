import base64
import io

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QVBoxLayout, QWidget, QHBoxLayout, QLabel, QSpinBox, QSizePolicy, QCheckBox, QMessageBox, \
    QDoubleSpinBox
from netCDF4 import num2date
from cartopy import crs as ccrs
from matplotlib.cm import ScalarMappable, get_cmap
from matplotlib.colors import Normalize
from matplotlib import use as mpluse
from matplotlib import style as mplstyle
from matplotlib import pyplot as plt

mplstyle.use('fast')
mpluse("agg")

from plotutils import WebChannelJS, PlotBackend
import datautils
import utils
import offline


class PlotWindow(QWidget):
    def __init__(self, appcontext, var_props):
        super().__init__()

        offline.set_appcontext(appcontext)
        offline.setup_folium()
        import folium

        slicedata, slicecalendar, slicetunits, timesliceindex, variable_units, variable_calendar, variable_description, xboundaries, yboundaries, initial_plotdata, xdata, ydata, xdataunit, ydataunit = datautils.get_initial_data(var_props)

        self.state = "init"
        self.autoscale = True
        self.var_props = var_props
        self.variable_units = variable_units
        self.xboundaries = xboundaries
        self.yboundaries = yboundaries

        self.setWindowTitle(var_props["file_path"] + " - NetSeeDF")
        self.setMinimumSize(650, 600)

        # GUI setup
        layout = QVBoxLayout()
        file_label = QLabel("File: \t\t" + var_props["file_path"], wordWrap=True)
        layout.addWidget(file_label)
        var_label = QLabel("Variable: \t" + var_props["variable_name"], wordWrap=True)
        layout.addWidget(var_label)

        if variable_description is not None:
            desc_label = QLabel("Description: \t" + variable_description, wordWrap=True)
            layout.addWidget(desc_label)

        if variable_units is not None:
            unit_label = QLabel("Units: \t\t" + variable_units, wordWrap=True)
            layout.addWidget(unit_label)

            if variable_units == "K":
                temp_convert_widget = QWidget()
                temp_convert_layout = QHBoxLayout()
                temp_convert_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
                temp_convert_widget.setLayout(temp_convert_layout)
                temp_convert_checkbox = QCheckBox()
                temp_convert_checkbox.checkStateChanged.connect(self.on_convert_temp)
                self.temp_convert_checkbox = temp_convert_checkbox
                temp_convert_layout.addWidget(temp_convert_checkbox)
                temp_convert_layout.addWidget(QLabel("convert to °C"))
                layout.addWidget(temp_convert_widget)

        # slice widgets
        self.slice_spinners = []
        self.slice_date_labels = []
        self.slice_dates_list = []

        for i in range(len(var_props["sliceable_dims"])):
            slice_dim = var_props["sliceable_dims"][i]
            slice_selector_widget = QWidget()
            slice_selector_layout = QHBoxLayout()
            slice_selector_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
            slice_selector_widget.setLayout(slice_selector_layout)
            slice_selector_layout.addWidget(QLabel(slice_dim + ": "))
            slice_spinner = QSpinBox()
            slice_spinner.setMinimum(1)
            slice_spinner.setMaximum(var_props["sizes"][slice_dim])  # set max index to size of the axis corresponding to the slicing variable
            slice_spinner.setValue(1)
            slice_spinner.valueChanged.connect(self.update_map)
            slice_selector_layout.addWidget(slice_spinner)
            slice_selector_layout.addWidget(QLabel(" of " + str(var_props["sizes"][slice_dim])))
            self.slice_spinners.append(slice_spinner)

            try:
                slice_dates = num2date(slicedata[i], slicetunits[i], slicecalendar[i])
                self.slice_dates_list.append(slice_dates)
                slice_date_label = QLabel(" =  " + str(slice_dates[0]))
                self.slice_date_labels.append(slice_date_label)
                slice_selector_layout.addWidget(self.slice_date_labels[i])
            except Exception:
                self.slice_dates_list.append(None)
                self.slice_date_labels.append(None)

            layout.addWidget(slice_selector_widget)

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

        cbar_container = QWidget()
        cbar_container_layout = QVBoxLayout()
        cbar_container_layout.setAlignment(Qt.AlignmentFlag.AlignBottom)
        max_spinner = QDoubleSpinBox()
        min_spinner = QDoubleSpinBox()
        max_spinner.setEnabled(False)
        min_spinner.setEnabled(False)
        max_spinner.setRange(-1e300, 1e300)
        min_spinner.setRange(-1e300, 1e300)
        max_spinner.setFixedWidth(125)
        min_spinner.setFixedWidth(125)
        self.max_spinner = max_spinner
        self.min_spinner = min_spinner

        autoscale_widget = QWidget()
        autoscale_layout = QHBoxLayout()
        autoscale_checkbox = QCheckBox()
        autoscale_checkbox.setChecked(True)
        self.autoscale_checkbox = autoscale_checkbox
        autoscale_layout.addWidget(autoscale_checkbox)
        autoscale_layout.addWidget(QLabel("auto scale"))
        autoscale_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        autoscale_widget.setLayout(autoscale_layout)

        # setup channel for communication between map js and python
        self.channel = QWebChannel()
        print(slicedata[timesliceindex])
        print(timesliceindex)
        print(slicetunits)
        self.backend = PlotBackend(var_props, xdata, ydata, variable_units, slicedata[timesliceindex], slicetunits[timesliceindex], slicecalendar[timesliceindex], self.show_map_popup, self)
        self.backend.set_data(initial_plotdata)
        self.channel.registerObject('backend', self.backend)
        self.view.page().setWebChannel(self.channel)

        # extent of map
        xmin, ymin, xmax, ymax = np.min(xboundaries), np.min(yboundaries), np.max(xboundaries), np.max(yboundaries)
        ymin = max(ymin, -85)
        ymax = min(ymax, 85)
        self.xmin, self.xmax, self.ymin, self.ymax = xmin, xmax, ymin, ymax

        image, colorbar = self.getb64image(initial_plotdata)

        print(initial_plotdata)

        # map raster layer
        folium.raster_layers.ImageOverlay(
            image="data:image/png;base64," + image,
            bounds=[[ymin, xmin], [ymax, xmax]],
            opacity=0.6
        ).add_to(self.map)

        folium.FitOverlays().add_to(self.map)  # fit the view to the overlay size

        scriptelement = folium.Element('<script>' + appcontext.webchanneljs + '</script>')
        self.map.get_root().html.add_child(scriptelement)
        self.map.add_child(WebChannelJS())

        html_data = self.map.get_root().render()
        self.view.setHtml(html_data)  # load the html

        qimage = QImage.fromData(colorbar)
        pixmap = QPixmap.fromImage(qimage)
        cbar = QLabel()
        cbar.setPixmap(pixmap)
        self.cbar = cbar

        max_spinner.valueChanged.connect(self.scale_changed)
        min_spinner.valueChanged.connect(self.scale_changed)
        autoscale_checkbox.checkStateChanged.connect(self.on_autoscale_changed)

        cbar_container_layout.addStretch()
        cbar_container_layout.addWidget(autoscale_widget)
        cbar_container_layout.addWidget(max_spinner)
        cbar_container_layout.addWidget(cbar)
        cbar_container_layout.addWidget(min_spinner)
        cbar_container.setLayout(cbar_container_layout)

        maplayout.addWidget(cbar_container)
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
        slice_indices = []
        for i in range(len(self.var_props["sliceable_dims"])):
            slice_index = self.slice_spinners[i].value() - 1 # get the index of the slice from the spinner
            slice_indices.append(slice_index)

            if self.slice_dates_list[i] is not None:
                self.slice_date_labels[i].setText(" =  " + str(self.slice_dates_list[i][slice_indices[i]]))

        sliced_data = datautils.get_sliced_data(self.var_props, slice_indices)

        if self.variable_units is not None:
            if self.variable_units == "K":
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

        #self.backend.set_data(sliced_data)

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
        self.state = "generating image"

        image = io.BytesIO()
        colorbar = io.BytesIO()

        ax = plt.axes(projection=ccrs.epsg(3857))

        source_crs = ccrs.PlateCarree()

        max_value = np.nanmax(image_data)
        min_value = np.nanmin(image_data)
        rounded_max_value = utils.round_max_value(max_value)
        rounded_min_value = utils.round_min_value(min_value)
        step = utils.calculate_step(rounded_min_value, rounded_max_value)
        steporder = utils.getorder(step)

        if steporder < 0:
            stepdecimals = abs(steporder)
        else:
            stepdecimals = 0
            step = 1

        if self.autoscale:
            self.max_spinner.setDecimals(stepdecimals)
            self.min_spinner.setDecimals(stepdecimals)
            self.max_spinner.setSingleStep(step)
            self.min_spinner.setSingleStep(step)

            #if steporder < 0:
            #    scale_max_value = rounded_max_value
            #    scale_min_value = rounded_min_value
            #else:
            scale_max_value = max_value
            scale_min_value = min_value

            self.max_spinner.setValue(scale_max_value)
            self.min_spinner.setValue(scale_min_value)

        else:
            scale_max_value = self.max_spinner.value()
            scale_min_value = self.min_spinner.value()

        if self.variable_units is not None:
            if self.variable_units in ["mm", "day"]:  # force the color scale minimum value to 0
                scale_min_value = 0
                if self.autoscale:
                    self.min_spinner.setValue(0)

        ax.set_extent([self.xmin, self.xmax, self.ymin, self.ymax], crs=source_crs)
        ax.axis("off")

        norm = Normalize(vmin=scale_min_value, vmax=scale_max_value)
        cmap = get_cmap("inferno")
        cmap.set_extremes(under='grey', over='red')
        sm = ScalarMappable(norm=norm, cmap=cmap)

        ax.pcolormesh(self.xboundaries, self.yboundaries, image_data, cmap=cmap, transform=source_crs,
                      vmin=scale_min_value, vmax=scale_max_value, shading="flat")
        plt.savefig(image, format="png", bbox_inches="tight", pad_inches=0, dpi=500)

        fig, ax = plt.subplots(figsize=(1.1, 3.5), layout="constrained")

        if scale_min_value > min_value and scale_max_value < max_value:
            extend = "both"
        elif scale_min_value > min_value:
            extend = "min"
        elif scale_max_value < max_value:
            extend = "max"
        else:
            extend = "neither"

        cbar = fig.colorbar(sm, cax=ax, extend=extend)

        if self.variable_units is not None:
            if self.variable_units == "K":
                if self.temp_convert_checkbox.isChecked():
                    cbar.set_label("°C")
                else:
                    cbar.set_label(self.variable_units)
            else:
                cbar.set_label(self.variable_units)
        fig.savefig(colorbar, format="png", bbox_inches="tight")

        plt.close("all")
        image.seek(0)
        colorbar.seek(0)

        self.state = "image done"
        return base64.b64encode(image.read()).decode("utf-8"), colorbar.read()

    def on_convert_temp(self):
        self.update_map()

    def scale_changed(self):
        if self.state != "generating image":  # hack to not trigger update if we are in the middle of one
            if self.max_spinner.value() > self.min_spinner.value():
                self.update_map()

    def on_autoscale_changed(self):
        self.autoscale = self.autoscale_checkbox.isChecked()
        if self.autoscale:
            self.max_spinner.setEnabled(False)
            self.min_spinner.setEnabled(False)
            self.update_map()
        else:
            self.max_spinner.setEnabled(True)
            self.min_spinner.setEnabled(True)






