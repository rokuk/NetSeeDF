import numpy as np
from netCDF4 import Dataset, num2date
from PyQt6.QtWidgets import QCheckBox, QTableWidget, QVBoxLayout, QWidget, QLabel, \
    QHBoxLayout, QSpinBox, QPushButton, QTableView
from PyQt6.QtCore import Qt
from pathlib import Path

import utils


# Window which shows a table of the data for the chosen variable and some info about the variable.
# Displayed when 'Show data' button is clicked.
class DataWindow3d(QWidget):
    def __init__(self, file_name, variable_name, file_path):
        super().__init__()

        self.setWindowTitle(variable_name + " - NetSeeDF")
        self.setMinimumSize(200, 500)
        self.last_directory = str(Path.home())

        ncfile = Dataset(file_path, "r")
        variable_data = ncfile.variables[variable_name]
        data = np.array(variable_data[:])  # cast data to a numpy array

        self.fill_value = variable_data.get_fill_value()
        self.data = data

        layout = QVBoxLayout()
        file_label = QLabel("File: \t\t" + file_name)
        layout.addWidget(file_label)
        var_label = QLabel("Variable: \t" + variable_name)
        layout.addWidget(var_label)

        # display units of the variable if given in the NetCDF file
        try:
            unit_label = QLabel("Units: \t\t" + variable_data.units)
            layout.addWidget(unit_label)
        except Exception:
            pass

        # display calendar type if given the NetCDF file
        try:
            if variable_data.calendar is not None:
                calendar_label = QLabel("Calendar: \t" + variable_data.calendar)
                layout.addWidget(calendar_label)
        except Exception:
            pass

        # display the data in a table
        data_table = QTableView(self)
        data_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        data_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        data_table.customContextMenuRequested.connect(self.show_context_menu)
        data_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        data_table.verticalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        data_table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.data_table = data_table

        self.setMinimumSize(700, 600)

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
        self.tdata = ncfile.variables[variable_data.dimensions[slice_dim_index]][:]

        # get x and y axis data units if available
        self.xdataunit = ""
        try:
            self.xdataunit = ncfile.variables[variable_data.dimensions[x_dim_index]].units
        except Exception:
            pass

        self.ydataunit = ""
        try:
            self.ydataunit = ncfile.variables[variable_data.dimensions[y_dim_index]].units
        except Exception:
            pass

        # get calendar from file if available
        try:
            self.calendar = ncfile.variables[variable_data.dimensions[slice_dim_index]].calendar
        except Exception:
            pass

        # slicing variable index selector
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
        slice_spinner.valueChanged.connect(self.update_table)
        self.slice_spinner = slice_spinner
        slice_selector_layout.addWidget(slice_spinner)

        # axis selectors container
        axis_selectors_widget = QWidget()
        axis_selectors_layout = QVBoxLayout()
        axis_selectors_layout.addWidget(slice_selector_widget)
        labels_selector = QWidget()
        labels_selector_layout = QHBoxLayout()
        labels_checkbox = QCheckBox()
        labels_selector.setLayout(labels_selector_layout)
        labels_checkbox.checkStateChanged.connect(self.update_headers)
        self.labels_checkbox = labels_checkbox
        labels_selector_layout.addWidget(labels_checkbox)
        labels_selector_layout.addWidget(QLabel("show axis values"))
        labels_selector_layout.addStretch()
        export_button = QPushButton("Export data")
        export_button.clicked.connect(self.export_3d)
        labels_selector_layout.addWidget(export_button)

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

        axis_selectors_layout.addWidget(labels_selector)
        axis_selectors_widget.setLayout(axis_selectors_layout)
        layout.addWidget(axis_selectors_widget)

        # set up the table model and load initial data
        initial_data = self.get_selected_data().astype(str)

        if self.xdataunit == "degrees_east":  # if the axis represent lat lon coordinates and units are given in the NetCDF file, display the degree symbol
            xlabels = self.xdata.astype(str) + "°"
        else:
            xlabels = self.xdata.astype(str)

        if self.ydataunit == "degrees_north":  # if the axis represent lat lon coordinates and units are given in the NetCDF file, display the degree symbol
            ylabels = self.ydata.astype(str) + "°"
        else:
            ylabels = self.ydata.astype(str)

        self.model = utils.TableModel(initial_data, xlabels, ylabels)
        self.data_table.setModel(self.model)

        max_xwidth = self.model.get_xwidth(self.data_table)
        max_ywidth = self.model.get_ywidth(self.data_table)

        self.data_table.verticalHeader().setFixedWidth(max_ywidth + 20)

        for col in range(len(self.xdata)):
            self.data_table.horizontalHeader().resizeSection(col, max_xwidth + 20)

        self.data_table.update()

        layout.addWidget(data_table)

        # we are done reading the data from the NetCDF file
        ncfile.close()

        self.setLayout(layout)


    def get_selected_data(self):
        slice_index = self.slice_spinner.value()
        sliced_data = self.data.take(slice_index, axis=self.slice_dim_index)  # subset data with the current slice index
        sliced_data[sliced_data == self.fill_value] = np.nan  # replace fill values with numpy's NaN
        return sliced_data


    def update_table(self):
        slice_2d = self.get_selected_data().astype(str)
        self.model.set_data(slice_2d)
        self.data_table.update()


    def update_headers(self):
        self.model.show_label_headers(self.labels_checkbox.isChecked())
        self.data_table.update()


    def show_context_menu(self, point):
        utils.show_context_menu(self, point)


    def export_3d(self):
        utils.show_dialog_and_save(self, self.get_selected_data())
