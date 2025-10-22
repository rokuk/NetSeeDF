import numpy as np
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QMenu, QApplication, QFileDialog
from netCDF4 import num2date, Dataset

def slice_data(file_path, variable_name, slice_dim_index, slice_index):
    ncfile = Dataset(file_path, "r")
    variable_data = ncfile.variables[variable_name]

    if slice_dim_index == 0:  # select the slice and read it into memory from disk
        sliced_data = variable_data[slice_index, :, :]
    elif slice_dim_index == 1:
        sliced_data = variable_data[:, slice_index, :]
    else:
        sliced_data = variable_data[:, :, slice_index]

    ncfile.close()

    return sliced_data


def show_context_menu(self, point):
    index = self.data_table.indexAt(point)
    if index.isValid():
        menu = QMenu()
        copy_action = menu.addAction("Copy")
        action = menu.exec(QCursor.pos())
        if action == copy_action:
            value = index.data()
            QApplication.clipboard().setText(str(value))

def show_context_menu_3d(self, point, window_instance, tdata, tunits, calendar, variable_name, file_path, x_dim_index, y_dim_index, slice_dim_index):
    index = self.data_table.indexAt(point)
    if index.isValid():
        menu = QMenu()
        copy_action = menu.addAction("Copy")
        export_action = menu.addAction("Export timeseries")
        action = menu.exec(QCursor.pos())
        if action == copy_action:
            value = index.data()
            QApplication.clipboard().setText(str(value))
        elif action == export_action:
            # slice the data with the selected grid indexes (from on_map_click)
            idx = [slice(None)] * 3  # sorry, but it works
            idx[x_dim_index] = index.column()
            idx[y_dim_index] = index.row()
            idx[slice_dim_index] = ...

            ncfile = Dataset(file_path, "r")
            variable_data = ncfile.variables[variable_name]
            timeseries = variable_data[tuple(idx)]  # slice the data for the grid point to get the timeseries
            ncfile.close()

            if window_instance.has_units:
                if window_instance.variable_units == "K":
                    if window_instance.temp_convert_checkbox.isChecked():
                        try:
                            timeseries = timeseries - 273.15
                        except Exception:
                            pass

            if tunits is not None and calendar is not None:
                datetimes = num2date(self.tdata, self.tunits, self.calendar)
            else:
                datetimes = tdata

            suggested_filename = self.variable_name + "_" + self.slice_dimension_name + str(self.slice_spinner.value())
            show_dialog_and_save(window_instance, [datetimes, timeseries], suggested_filename, False)



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
            if "CSV" in selected_filter:
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

            if ext == ".txt":
                np.savetxt(file_path, selected_data, delimiter=" ")
            elif ext == ".csv":
                selected_data.to_csv(file_path, index=False, header=False)
                np.savetxt(file_path, selected_data, delimiter=",")