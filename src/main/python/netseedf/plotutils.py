import numpy as np
from folium import MacroElement
from jinja2 import Template
from PySide6.QtCore import QObject, Slot
from netCDF4 import num2date

import utils
import datautils


def find_closest_grid_point(lat, lon, x, y):
    i = np.abs(x - lon).argmin()
    j = np.abs(y - lat).argmin()
    return i, j

class PlotBackend(QObject):
    def __init__(self, var_props, xdata, ydata, variable_units, tdata, tunits, calendar, show_map_popup, window_instance):
        super().__init__()
        self.var_props = var_props
        self.xdata = xdata
        self.ydata = ydata
        self.variable_units = variable_units
        self.tdata = tdata
        self.tunits = tunits
        self.calendar = calendar
        self.show_map_popup = show_map_popup
        self.window_instance = window_instance
        self.last_gridi = 0
        self.last_gridj = 0
        self.data = None

    def set_data(self, data):
        self.data = data

    @Slot(float, float)
    def on_map_click(self, lat, lon):
        # check if coordinates are inside the bounds of the data, if outside do nothing
        if (self.xdata.min() < lon < self.xdata.max()) and (self.ydata.min() < lat < self.ydata.max()):
            gridi, gridj = find_closest_grid_point(lat, lon, self.xdata, self.ydata)
            gridlat, gridlon, gridval = self.ydata[gridj], self.xdata[gridi], self.data[gridj, gridi]
            self.last_gridi, self.last_gridj = gridi, gridj

            is_celsius = False
            if self.variable_units is not None:
                if self.variable_units == "K":
                    if self.window_instance.temp_convert_checkbox.isChecked():
                        try:
                            gridval = gridval - 273.15
                            is_celsius = True
                        except Exception:
                            pass

            value_string = str(gridval)
            if gridval != np.nan and self.variable_units is not None:
                if is_celsius:
                    value_string += " °C"
                elif self.variable_units == "1":
                    pass
                else:
                    value_string += " " + self.variable_units
            self.show_map_popup(gridlat, gridlon, value_string)  # show popup with lat, lon and value of the closest grid point

    @Slot()
    def on_export_requested(self):
        slice_indices = []
        for i in range(len(self.var_props["sliceable_dims"])):
            slice_index = self.window_instance.slice_spinners[i].value() - 1  # get the index of the slice from the spinner
            slice_indices.append(slice_index)

        timeseries = datautils.slice_timeseries(self.var_props, slice_indices, self.last_gridi, self.last_gridj, self.var_props["t_dim"]) # we assume that data should be sliced along the first identified time dimension

        if self.variable_units is not None:
            if self.variable_units == "K":
                if self.window_instance.temp_convert_checkbox.isChecked():
                    try:
                        timeseries = timeseries - 273.15
                    except Exception:
                        pass

        if self.tunits is not None and self.calendar is not None:
            print(self.tdata, self.tunits, self.calendar)
            datetimes = num2date(self.tdata, self.tunits, self.calendar)
        else:
            datetimes = self.tdata

        suggested_filename = self.var_props["variable_name"] + "_" + self.var_props["t_dim"]

        utils.show_dialog_and_save(self.window_instance, np.array([datetimes, timeseries]).T, suggested_filename, False)

        self.window_instance.close_map_popups()

class WebChannelJS(MacroElement):
    _template = Template("""
            {% macro script(this, kwargs) %}
            function setupWebChannel() {
                if (typeof qt !== "undefined" && typeof QWebChannel !== "undefined") {
                    new QWebChannel(qt.webChannelTransport, function(channel) {
                        window.backend = channel.objects.backend;
                    });
                }
            }
            document.addEventListener('DOMContentLoaded', setupWebChannel, false);
            {{this._parent.get_name()}}.on('click', function(e) {
                window.backend.on_map_click(e.latlng.lat, e.latlng.lng);
            });
            {% endmacro %}
        """)

    def __init__(self):
        super().__init__()
