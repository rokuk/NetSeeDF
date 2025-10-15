import numpy as np
from PySide6.QtCore import QAbstractTableModel, Qt, QObject, Slot
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QMenu, QApplication, QFileDialog, QMessageBox
from folium import MacroElement
from jinja2 import Template
from netCDF4 import num2date, Dataset
from pandas import DataFrame


def show_context_menu(self, point):
    index = self.data_table.indexAt(point)
    if index.isValid():
        menu = QMenu()
        copy_action = menu.addAction("Copy")
        action = menu.exec(QCursor.pos())
        if action == copy_action:
            value = index.data()
            QApplication.clipboard().setText(str(value))


def show_dialog_and_save(self, selected_data, suggested_filename, use_last_dir=True):
    dialog = QFileDialog(self, "Save File")
    dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
    dialog.setNameFilters(["Excel File (*.xlsx)", "CSV File (*.csv)", "Text File (*.txt)"])
    dialog.setDefaultSuffix("xlsx")
    if use_last_dir: dialog.setDirectory(self.last_directory)  # Use last directory
    dialog.setOption(QFileDialog.Option.DontConfirmOverwrite, False)
    dialog.selectFile(suggested_filename)

    if dialog.exec():
        file_paths = dialog.selectedFiles()
        if file_paths:
            file_path = file_paths[0]

            # Determine selected filter
            selected_filter = dialog.selectedNameFilter()
            if "Excel" in selected_filter:
                ext = ".xlsx"
            elif "CSV" in selected_filter:
                ext = ".csv"
            elif "Text" in selected_filter:
                ext = ".txt"
            else:
                ext = ""

            # Automatically add extension if not present
            if not file_path.lower().endswith(ext):
                file_path += ext

            # Update last directory
            if use_last_dir: self.last_directory = str(QFileDialog.directory(dialog).absolutePath())

            try:
                if not isinstance(selected_data, DataFrame):
                    selected_data = DataFrame(selected_data)

                if ext == ".txt":
                    selected_data.to_csv(file_path, index=False, header=False, sep=" ")
                elif ext == ".csv":
                    selected_data.to_csv(file_path, index=False, header=False)
                elif ext == ".xlsx":
                    selected_data.to_excel(file_path, index=False, header=False)
            except Exception:
                dlg = QMessageBox(self)
                dlg.setWindowTitle("NetSeeDF message")
                dlg.setText("There was an error saving the file!")
                dlg.exec()
                return


def get_max_width(data_table, labels):
    metrics = data_table.fontMetrics()
    if hasattr(labels, 'tolist'):
        labels = labels.tolist()
    labels = [str(lbl) for lbl in labels]
    max_width = 0
    for label in labels:
        width = metrics.horizontalAdvance(label)
        if width > max_width:
            max_width = width
    return max_width


class TableModel(QAbstractTableModel):
    def __init__(self, data, xlabels, ylabels):
        super().__init__()
        self.data = data
        self.xlabels = xlabels
        self.ylabels = ylabels
        self.label_headers = False

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            return str(self.data[index.row(), index.column()])
        else:
            return None

    def rowCount(self, parent=None):
        return self.data.shape[0]

    def columnCount(self, parent=None):
        if len(self.data.shape) == 2:
            return self.data.shape[1]
        else:
            return 1

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            if self.label_headers:  # label headers
                if orientation == Qt.Orientation.Horizontal:
                    return str(self.xlabels[section])
                if orientation == Qt.Orientation.Vertical:
                    return str(self.ylabels[section])
            else:  # do not label headers
                return str(section + 1)
        return None

    def show_label_headers(self, label_headers):
        self.label_headers = label_headers

    def set_data(self, data):
        self.beginResetModel()
        self.data = data
        self.endResetModel()

    def get_xwidth(self, data_table):
        return get_max_width(data_table, self.xlabels)

    def get_ywidth(self, data_table):
        return get_max_width(data_table, self.ylabels)


class SimpleTableModel(QAbstractTableModel):
    def __init__(self, data):
        super().__init__()
        self.data = data

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            return str(self.data[index.row(), index.column()])
        else:
            return None

    def rowCount(self, parent=None):
        return self.data.shape[0]

    def columnCount(self, parent=None):
        if len(self.data.shape) == 2:
            return self.data.shape[1]
        else:
            return 1

    def set_data(self, data):
        self.beginResetModel()
        self.data = data
        self.endResetModel()


def find_closest_grid_point(lat, lon, x, y):
    i = np.abs(x - lon).argmin()
    j = np.abs(y - lat).argmin()
    return i, j


class Backend(QObject):
    def __init__(self, file_path, variable_name, xdata, ydata, tdata, tunits, calendar, x_dim_index, y_dim_index, slice_dim_index,
                 show_map_popup, window_instance):
        super().__init__()
        self.file_path = file_path
        self.variable_name = variable_name
        self.xdata = xdata
        self.ydata = ydata
        self.tdata = tdata
        self.tunits = tunits
        self.calendar = calendar
        self.x_dim_index = x_dim_index
        self.y_dim_index = y_dim_index
        self.slice_dim_index = slice_dim_index
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
            self.show_map_popup(gridlat, gridlon,
                                gridval)  # show popup with lat, lon and value of the closest grid point

    @Slot()
    def on_export_requested(self):
        # slice the data with the selected grid indexes (from on_map_click)
        idx = [slice(None)] * 3  # sorry, but it works
        idx[self.x_dim_index] = self.last_gridi
        idx[self.y_dim_index] = self.last_gridj
        idx[self.slice_dim_index] = ...

        ncfile = Dataset(self.file_path, "r")
        variable_data = ncfile.variables[self.variable_name]
        timeseries = variable_data[tuple(idx)]  # slice the data for the grid point to get the timeseries
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

        df = DataFrame({"time": datetimes, "variable": timeseries})

        show_dialog_and_save(self.window_instance, df, "timeseries", False)

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
                } else {
                    alert("qt or QWebChannel is not defined");
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
