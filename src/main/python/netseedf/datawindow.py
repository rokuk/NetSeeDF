from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QTableWidget, QVBoxLayout, QWidget, QLabel, \
    QHBoxLayout, QSpinBox, QPushButton, QTableView, QMessageBox
from netCDF4 import Dataset, num2date
import numpy as np

import utils
import datautils
import tableutils

# Window which shows a table of the data for the chosen variable and some info about the variable.
# Displayed when 'Show data' button is clicked.
class DataWindow(QWidget):
    def __init__(self, var_props):
        super().__init__()

        self.setWindowTitle(var_props["file_path"] + " - NetSeeDF")
        self.setMinimumSize(700, 600)

        slicedata, slicecalendar, slicetunits, variable_units, variable_calendar, variable_description, xboundaries, yboundaries, initial_data, xdata, ydata, xdataunit, ydataunit = datautils.get_initial_data(var_props)

        self.var_props = var_props
        self.variable_units = variable_units
        self.variable_calendar = variable_calendar
        self.last_directory = str(Path.home())

        if initial_data.shape == ():
            initial_data = initial_data.reshape((1,1))

        if len(initial_data.shape) == 1:
            initial_data = initial_data.reshape((initial_data.shape[0], 1))

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

        if var_props["can_slice"]:
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
                slice_spinner.valueChanged.connect(self.update_table)
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

        # data table
        data_table = QTableView(self)
        data_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        data_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        data_table.customContextMenuRequested.connect(self.show_context_menu)
        data_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        data_table.verticalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        data_table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.data_table = data_table

        # axis options container
        labels_selector = QWidget()
        labels_selector_layout = QHBoxLayout()
        labels_checkbox = QCheckBox()
        labels_selector.setLayout(labels_selector_layout)
        labels_checkbox.checkStateChanged.connect(self.update_headers)
        self.labels_checkbox = labels_checkbox
        if xdata is not None and ydata is not None:
            labels_selector_layout.addWidget(labels_checkbox)
            labels_selector_layout.addWidget(QLabel("show axis values"))
        else:
            if variable_calendar is not None:
                _ = num2date(initial_data, variable_units, variable_calendar)
                calendar_checkbox = QCheckBox()
                calendar_checkbox.checkStateChanged.connect(self.convert_datetime)
                self.calendar_checkbox = calendar_checkbox
                labels_selector_layout.addWidget(calendar_checkbox)
                labels_selector_layout.addWidget(QLabel("convert date/time"))
        labels_selector_layout.addStretch()
        export_button = QPushButton("Export data")
        export_button.clicked.connect(self.export_3d)
        labels_selector_layout.addWidget(export_button)
        layout.addWidget(labels_selector)

        xlabels, ylabels = None, None
        if xdata is not None and ydata is not None:
            if xdataunit == "degrees_east":  # if the axis represent lat lon coordinates and units are given in the NetCDF file, display the degree symbol
                xlabels = xdata.astype(str) + "°"
            else:
                xlabels = xdata.astype(str)

            if ydataunit == "degrees_north":  # if the axis represent lat lon coordinates and units are given in the NetCDF file, display the degree symbol
                ylabels = ydata.astype(str) + "°"
            else:
                ylabels = ydata.astype(str)

        self.model = tableutils.TableModel(initial_data.astype(str), xlabels, ylabels)
        self.data_table.setModel(self.model)

        if xdata is not None and ydata is not None:
            max_xwidth = self.model.get_xwidth(self.data_table)
            max_ywidth = self.model.get_ywidth(self.data_table)

            self.data_table.verticalHeader().setFixedWidth(max_ywidth + 20)

            for col in range(len(xdata)):
                self.data_table.horizontalHeader().resizeSection(col, max_xwidth + 20)

        layout.addWidget(data_table)

        self.setLayout(layout)

    def convert_datetime(self):
        normal_data = self.get_selected_data()
        if self.calendar_checkbox.isChecked():
            try:
                conv_data = num2date(normal_data, self.variable_units, self.variable_calendar)
                conv_data = np.array(conv_data)
            except Exception:
                dlg = QMessageBox(self)
                dlg.setWindowTitle("NetSeeDF message")
                dlg.setText("There was an error while calculating the dates/times!")
                dlg.exec()
                return

            str_data = conv_data.astype(str)
        else:
            str_data = normal_data.astype(str)

        if str_data.shape == ():
            str_data = str_data.reshape((1,1))

        if len(str_data.shape) == 1:
            str_data = str_data.reshape((str_data.shape[0], 1))

        self.model.set_data(str_data)

        self.data_table.resizeColumnsToContents()

    def get_selected_indices(self):
        # get slice indices from spinners
        slice_indices = []
        for i in range(len(self.slice_spinners)):
            slice_index = self.slice_spinners[i].value() - 1  # get the index of the slice from the spinner
            slice_indices.append(slice_index)
        return slice_indices

    def update_table(self):
        slice_indices = self.get_selected_indices()

        for i in range(len(self.var_props["sliceable_dims"])):
            # update text next to slice index spinners
            if self.slice_dates_list[i] is not None:
                self.slice_date_labels[i].setText(" =  " + str(self.slice_dates_list[i][slice_indices[i]]))

        sliced_data = self.get_selected_data(slice_indices)

        self.model.set_data(sliced_data.astype(str))

    def get_selected_data(self, slice_indices=None):
        if slice_indices is None:
            slice_indices = self.get_selected_indices()

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

        return sliced_data

    def update_headers(self):
        self.model.show_label_headers(self.labels_checkbox.isChecked())

    def on_convert_temp(self):
        self.update_table()

    def show_context_menu(self, point):
        utils.show_context_menu_3d(self, point, self, self.tdata, self.tunits, self.calendar, self.slice_dimension_name, self.variable_name, self.file_path, self.x_dim_index, self.y_dim_index, self.slice_dim_index)

    def export_3d(self):
        suggested_filename = self.var_props["variable_name"]
        for i in range(len(self.var_props["sliceable_dims"])):
            suggested_filename = suggested_filename + "_" + self.var_props["sliceable_dims"][i] + str(self.slice_spinners[i].value())
        utils.show_dialog_and_save(self, self.get_selected_data(), suggested_filename)
