import numpy as np
from PyQt6.QtGui import QCursor
from netCDF4 import Dataset, num2date
from PyQt6.QtWidgets import QCheckBox, QMessageBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QLabel, \
    QHBoxLayout, QSpinBox, QMenu, QApplication, QPushButton, QFileDialog
from PyQt6.QtCore import Qt
import openpyxl
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
        data_table = QTableWidget(self)
        data_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        data_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        data_table.customContextMenuRequested.connect(utils.show_context_menu)
        data_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
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
        slice_selector_layout.addWidget(QLabel("Slice index: "))
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

        self.update_table()  # load initial data into table
        self.update_headers()  # set table headers

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
        str_data = self.get_selected_data().astype(str)

        if self.can_convert_datetime:
            try:
                slice_date = num2date(self.tdata[self.slice_spinner.value()], self.tunits, self.calendar)
                self.slice_date_label.setText(str(slice_date))
            except Exception:
                pass

        # display data
        self.data_table.setRowCount(len(str_data))
        self.data_table.setColumnCount(len(str_data[0]))
        for i in range(len(str_data)):
            for j in range(len(str_data[0])):
                self.data_table.setItem(i, j, QTableWidgetItem(str_data[i, j]))


    def update_headers(self):
        if self.labels_checkbox.isChecked():  # display lat lon values as table headers
            if self.xdataunit == "degrees_east":  # if the axis represent lat lon coordinates and units are given in the NetCDF file, display the degree symbol
                self.data_table.setHorizontalHeaderLabels([str(i) + "°" for i in self.xdata])
            else:
                self.data_table.setHorizontalHeaderLabels([str(i) for i in self.xdata])

            if self.ydataunit == "degrees_north":
                self.data_table.setVerticalHeaderLabels([str(i) + "°" for i in self.ydata])
            else:
                self.data_table.setVerticalHeaderLabels([str(i) for i in self.ydata])
        else:  # display axis indexes in headers
            self.data_table.setHorizontalHeaderLabels([str(i) for i in range(1, len(self.xdata) + 1)])
            self.data_table.setVerticalHeaderLabels([str(i) for i in range(1, len(self.ydata) + 1)])


    def export_3d(self):
        self.show_dialog_and_save(self.get_selected_data())


    def show_dialog_and_save(self, selected_data):
        dialog = QFileDialog(self, "Save File")
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        dialog.setNameFilters(["Excel File (*.xlsx)", "CSV File (*.csv)", "Text File (*.txt)"])
        dialog.setDefaultSuffix("xlsx")
        dialog.setDirectory(self.last_directory)  # Use last directory
        dialog.setOption(QFileDialog.Option.DontConfirmOverwrite, False)

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
                self.last_directory = str(QFileDialog.directory(dialog).absolutePath())

                try:
                    # Save example content based on file type
                    if ext == ".txt":
                        np.savetxt(file_path, selected_data, delimiter="\t")
                    elif ext == ".csv":
                        np.savetxt(file_path, selected_data, delimiter=",", fmt="%s")
                    elif ext == ".xlsx":
                        wb = openpyxl.Workbook()
                        ws = wb.active

                        for row in selected_data:
                            ws.append(row.tolist())  # Convert NumPy row to list

                        wb.save(file_path) # write the workbook to file
                except Exception:
                    dlg = QMessageBox(self)
                    dlg.setWindowTitle("NetSeeDF message")
                    dlg.setText("There was an error saving the file!")
                    dlg.exec()
                    return
