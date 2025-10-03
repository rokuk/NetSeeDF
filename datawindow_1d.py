import numpy as np
from PyQt6.QtGui import QCursor
from netCDF4 import Dataset, num2date
from PyQt6.QtWidgets import QCheckBox, QMessageBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QLabel, \
    QHBoxLayout, QMenu, QApplication, QPushButton, QFileDialog
from PyQt6.QtCore import Qt
import openpyxl
from pathlib import Path

import utils


# Window which shows a table of the data for the chosen variable and some info about the variable.
# Displayed when 'Show data' button is clicked.
class DataWindow1d(QWidget):
    def __init__(self, file_name, variable_name, file_path):
        super().__init__()

        self.setWindowTitle(variable_name + " - NetSeeDF")
        self.setMinimumSize(200, 500)
        self.last_directory = str(Path.home())

        ncfile = Dataset(file_path, "r")
        variable_data = ncfile.variables[variable_name]
        data = np.array(variable_data[:]) # cast data to a numpy array

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

        str_data = data.astype(str)
        data_table.setRowCount(len(data))
        data_table.setColumnCount(1)
        for i in range(len(data)):
            data_table.setItem(i, 0, QTableWidgetItem(str_data[i]))

        export_widget = QWidget()
        export_layout = QHBoxLayout()
        export_widget.setLayout(export_layout)
        export_button = QPushButton("Export data")
        export_button.clicked.connect(self.export_data)

        if "calendar" in variable_data.ncattrs() and "units" in variable_data.ncattrs():
            try:
                slice_dates = num2date(data, variable_data.units, variable_data.calendar)
                self.tunits = variable_data.units
                self.calendar = variable_data.calendar

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
        self.data_table.setRowCount(len(str_data))
        self.data_table.setColumnCount(1)
        for i in range(len(str_data)):
            self.data_table.setItem(i, 0, QTableWidgetItem(str_data[i]))

        self.data_table.resizeColumnsToContents()


    def export_data(self):
        self.show_dialog_and_save(self.data)

    
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
                            ws.append([row]) # write float to row

                        wb.save(file_path) # write the workbook to file
                except Exception:
                    dlg = QMessageBox(self)
                    dlg.setWindowTitle("NetSeeDF message")
                    dlg.setText("There was an error saving the file!")
                    dlg.exec()
                    return
