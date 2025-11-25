import numpy as np
from folium import MacroElement
from jinja2 import Template
from PySide6.QtCore import QObject, Slot
from netCDF4 import Dataset, num2date

from utils import show_dialog_and_save


def find_closest_grid_point(lat, lon, x, y):
    i = np.abs(x - lon).argmin()
    j = np.abs(y - lat).argmin()
    return i, j

class PlotBackend(QObject):
    def __init__(self, var_props, xdata, ydata, variable_units, tdata, tunits, calendar, show_map_popup, window_instance):
        super().__init__()
        self.file_path = var_props["file_path"]
        self.variable_name = var_props["variable_name"]
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
            if self.variable_units is not None:
                if self.variable_units == "K":
                    if self.window_instance.temp_convert_checkbox.isChecked():
                        try:
                            gridval = gridval - 273.15
                        except Exception:
                            pass

            value_string = str(gridval)
            if self.variable_units is not None:
                value_string += " " + self.variable_units
            self.show_map_popup(gridlat, gridlon, value_string)  # show popup with lat, lon and value of the closest grid point

    @Slot()
    def on_export_requested(self):
        # slice the data with the selected grid indexes (from on_map_click)
        idx = [slice(None)] * 3  # sorry, but it works
        idx[self.x_dim_index] = self.last_gridi
        idx[self.y_dim_index] = self.last_gridj
        idx[self.slice_dim_index] = ...

        ncfile = Dataset(self.file_path, "r")
        variable_data = ncfile.variables[self.variable_name]
        timeseries = variable_data[tuple(idx)] # slice the data for the grid point to get the timeseries
        ncfile.close()

        if self.window_instance.has_units:
            if self.window_instance.variable_units == "K":
                if self.window_instance.temp_convert_checkbox.isChecked():
                    try:
                        timeseries = timeseries - 273.15
                    except Exception:
                        pass

        if self.tunits is not None and self.calendar is not None:
            datetimes = num2date(self.tdata, self.tunits, self.calendar)
        else:
            datetimes = self.tdata

        suggested_filename = self.variable_name + "_" + self.slice_dimension_name + str(self.slice_spinner.value())
        show_dialog_and_save(self.window_instance, np.array([datetimes, timeseries]).T, suggested_filename, False)

        self.window_instance.close_map_popups()


class Backend2d(QObject):
    def __init__(self, xdata, ydata, data, show_map_popup):
        super().__init__()
        self.xdata = xdata
        self.ydata = ydata
        self.data = data
        self.show_map_popup = show_map_popup

    @Slot(float, float)
    def on_map_click(self, lat, lon):
        # check if coordinates are inside the bounds of the data, if outside do nothing
        if (self.xdata.min() < lon < self.xdata.max()) and (self.ydata.min() < lat < self.ydata.max()):
            gridi, gridj = find_closest_grid_point(lat, lon, self.xdata, self.ydata)
            gridlat, gridlon, gridval = self.ydata[gridj], self.xdata[gridi], self.data[gridj, gridi]
            self.show_map_popup(gridlat, gridlon, gridval)  # show popup with lat, lon and value of the closest grid point


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
