from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QMessageBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QLabel, \
    QHBoxLayout, QPushButton, QTableView
from netCDF4 import Dataset, num2date

import utils
from tableutils import SimpleTableModel


# Window which shows a table of the data for the chosen variable and some info about the variable.
# Displayed when 'Show data' button is clicked.
class DataWindow2d(QWidget):
    def __init__(self, file_name, variable_name, file_path):
        super().__init__()

        self.setWindowTitle(variable_name + " - NetSeeDF")
        self.setMinimumSize(200, 500)

        self.last_directory = str(Path.home())
        self.variable_name = variable_name
        self.has_units = False

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
            self.has_units = True
            layout.addWidget(unit_label)
        except Exception:
            pass

        print(ncfile.variables)

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
        self.data_table = data_table

        str_data = data.astype(str)
        if self.has_units:  # the data in the table has degrees displayed if the units are degrees
            if variable_data.units == "degrees_east" or variable_data.units == "degrees_north":
                str_data = str_data + "°"

        self.model = SimpleTableModel(str_data)
        self.data_table.setModel(self.model)

        export_widget = QWidget()
        export_layout = QHBoxLayout()
        export_widget.setLayout(export_layout)
        export_button = QPushButton("Export data")
        export_button.clicked.connect(self.export_1d_2d)

        # add checkbox to convert dates, if the variable has calendar and units attributes
        add_checkbox = False
        if "calendar" in variable_data.ncattrs() and "units" in variable_data.ncattrs():
            try:
                _ = num2date(data, variable_data.units, variable_data.calendar)
                self.tunits = variable_data.units
                self.calendar = variable_data.calendar
                add_checkbox = True
            except Exception:
                pass
        elif variable_name == "time_bnds":
            if "time" in ncfile.variables:
                try:
                    _ = num2date(data, ncfile.variables["time"].units, ncfile.variables["time"].calendar)
                    self.tunits = ncfile.variables["time"].units
                    self.calendar = ncfile.variables["time"].calendar
                    add_checkbox = True
                except Exception:
                    pass

        if add_checkbox:
            calendar_checkbox = QCheckBox()
            calendar_checkbox.checkStateChanged.connect(self.convert_datetime_2d)
            self.calendar_checkbox = calendar_checkbox
            export_layout.addWidget(calendar_checkbox)
            export_layout.addWidget(QLabel("convert date/time"))

        export_layout.addStretch()
        export_layout.addWidget(export_button)
        layout.addWidget(export_widget)
        layout.addWidget(data_table)

        # we are done reading the data from the NetCDF file
        ncfile.close()

        self.setLayout(layout)

    def convert_datetime_2d(self):
        if self.calendar_checkbox.isChecked():
            try:
                conv_data = []
                for row in self.data:
                    conv_data.append(num2date(row, self.tunits, self.calendar))
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
        self.model.set_data(str_data)
        self.data_table.update()

        self.data_table.resizeColumnsToContents()

    def show_context_menu(self, point):
        utils.show_context_menu(self, point)

    def export_1d_2d(self):
        utils.show_dialog_and_save(self, self.data, self.variable_name)
