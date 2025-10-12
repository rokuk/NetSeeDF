from pathlib import Path

import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QCheckBox, QMessageBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QLabel, \
    QHBoxLayout, QPushButton
from netCDF4 import Dataset, num2date

import utils


# Window which shows a table of the data for the chosen variable and some info about the variable.
# Displayed when 'Show data' button is clicked.
class DataWindow1d(QWidget):
    def __init__(self, file_name, variable_name, file_path):
        super().__init__()

        self.setWindowTitle(variable_name + " - NetSeeDF")
        self.setMinimumSize(200, 500)

        self.last_directory = str(Path.home())
        self.variable_name = variable_name
        self.has_units = False
        self.can_convert_datetime = False

        ncfile = Dataset(file_path, "r")
        variable_data = ncfile.variables[variable_name]
        data = np.array(variable_data[:])  # cast data to a numpy array

        self.fill_value = variable_data.get_fill_value()
        data = np.where(data == self.fill_value, np.nan, data)
        self.data = data

        layout = QVBoxLayout()
        file_label = QLabel("File: \t\t" + file_name)
        layout.addWidget(file_label)
        var_label = QLabel("Variable: \t" + variable_name)
        layout.addWidget(var_label)

        # display units of the variable if given in the NetCDF file
        try:
            unit_label = QLabel("Units: \t\t" + variable_data.units)
            self.has_units = True
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
        data_table = QTableWidget(self)
        data_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        data_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        data_table.customContextMenuRequested.connect(self.show_context_menu)
        data_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.data_table = data_table

        str_data = data.astype(str)
        if self.has_units:  # the data in the table has degrees displayed if the units are degrees
            if variable_data.units == "degrees_east" or variable_data.units == "degrees_north":
                str_data = str_data + "°"

        data_table.setRowCount(len(data))
        data_table.setColumnCount(1)
        for i in range(len(data)):
            data_table.setItem(i, 0, QTableWidgetItem(str_data[i]))
        data_table.resizeColumnsToContents()

        export_widget = QWidget()
        export_layout = QHBoxLayout()
        export_widget.setLayout(export_layout)
        export_button = QPushButton("Export data")
        export_button.clicked.connect(self.export_data)

        if "calendar" in variable_data.ncattrs() and "units" in variable_data.ncattrs():
            try:
                _ = num2date(data, variable_data.units, variable_data.calendar)
                self.tunits = variable_data.units
                self.calendar = variable_data.calendar
                self.can_convert_datetime = True

                calendar_checkbox = QCheckBox()
                calendar_checkbox.checkStateChanged.connect(self.convert_datetime_1d)
                self.calendar_checkbox = calendar_checkbox
                export_layout.addWidget(calendar_checkbox)
                export_layout.addWidget(QLabel("convert date/time"))
            except Exception:
                pass

        export_layout.addStretch()
        export_layout.addWidget(export_button)
        layout.addWidget(export_widget)

        layout.addWidget(data_table)

        ncfile.close()

        self.setLayout(layout)

    def convert_datetime_1d(self):
        if self.calendar_checkbox.isChecked():
            try:
                conv_data = num2date(self.data, self.tunits, self.calendar)
                conv_data = np.array(conv_data)
            except Exception:
                dlg = QMessageBox(self)
                dlg.setWindowTitle("NetSeeDF message")
                dlg.setText("There was an error while calculating the dates/times!")
                dlg.exec()
                return

            str_data = conv_data.astype(str)
        else:
            str_data = self.data.astype(str)

        # display data
        for i in range(len(str_data)):
            self.data_table.setItem(i, 0, QTableWidgetItem(str_data[i]))

        self.data_table.resizeColumnsToContents()

    def show_context_menu(self, point):
        utils.show_context_menu(self, point)

    def export_data(self):
        if self.can_convert_datetime:
            if self.calendar_checkbox.isChecked(): # if dates are converted
                conv_data = num2date(self.data, self.tunits, self.calendar)
                data_to_export = np.array(conv_data)
            else:
                data_to_export = self.data
        else:
            data_to_export = self.data

        utils.show_dialog_and_save(self, data_to_export, self.variable_name)
