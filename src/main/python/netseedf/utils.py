import numpy as np
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QMenu, QApplication, QFileDialog, QMessageBox
from netCDF4 import num2date, Dataset
from math import floor, log10, ceil, copysign


def getorder(x):
    return floor(log10(abs(x)))


def round_max_value(x):
    if x == 0:
        return 0.0
    order = getorder(x)
    scale = 10 ** order
    rounded = ceil(abs(x) / scale) * scale
    return copysign(rounded, x)


def round_min_value(x):
    if x == 0:
        return 0.0
    order = getorder(x)
    scale = 10 ** order
    rounded = floor(abs(x) / scale) * scale
    return copysign(rounded, x)


def calculate_step(minvalue, maxvalue):
    if minvalue == 0:
        value = maxvalue
    elif maxvalue == 0:
        value = minvalue
    else:
        minorder = getorder(minvalue)
        maxorder = getorder(maxvalue)

        if minorder < maxorder:
            value = minvalue
        else:
            value = maxvalue

    if value == 0:
        return 0.1

    order = floor(log10(abs(value)))
    return 10 ** order


def grid_boundaries_from_centers(x_centers, y_centers):
    if len(x_centers) < 2 or len(y_centers) < 2:
        return  x_centers, y_centers # dont do anything if only one point or none

    x_centers = np.array(x_centers)
    y_centers = np.array(y_centers)

    # Compute midpoints between centers
    x_bounds = (x_centers[:-1] + x_centers[1:]) / 2
    y_bounds = (y_centers[:-1] + y_centers[1:]) / 2

    # Extend edges to cover outer boundaries
    x_bounds = np.concatenate((
        [x_centers[0] - (x_bounds[0] - x_centers[0])],
        x_bounds,
        [x_centers[-1] + (x_centers[-1] - x_bounds[-1])]
    ))

    # TODO only do this if lon,lat crs
    if x_bounds[0] < -180:
        x_bounds[0] = -180
    if x_bounds[-1] > 180:
        x_bounds[-1] = 180

    y_bounds = np.concatenate((
        [y_centers[0] - (y_bounds[0] - y_centers[0])],
        y_bounds,
        [y_centers[-1] + (y_centers[-1] - y_bounds[-1])]
    ))

    return x_bounds, y_bounds


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


def show_context_menu_3d(self, point, window_instance, tdata, tunits, calendar, slice_dimension_name, variable_name, file_path, x_dim_index, y_dim_index, slice_dim_index):
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
                datetimes = num2date(tdata, tunits, calendar)
            else:
                datetimes = tdata

            suggested_filename = variable_name + "_" + slice_dimension_name + str(self.slice_spinner.value())

            show_dialog_and_save(window_instance, np.array([datetimes, timeseries]).T, suggested_filename, False)


def show_dialog_and_save(self, selected_data, suggested_filename, use_last_dir=True):
    dialog = QFileDialog(self, "Save File")
    dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
    dialog.setNameFilters(["CSV File (*.csv)", "Tab-separated File (*.tsv)",  "Text File (*.txt)"])
    dialog.setDefaultSuffix("csv")
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
            elif "Tab" in selected_filter:
                ext = ".tsv"
            else:
                dlg = QMessageBox(self)
                dlg.setWindowTitle("NetSeeDF message")
                dlg.setText("There was an error while saving the file: " + selected_filter)
                dlg.exec()
                return

            # Automatically add extension if not present
            if not file_path.lower().endswith(ext):
                file_path += ext

            # Update last directory
            if use_last_dir: self.last_directory = str(QFileDialog.directory(dialog).absolutePath())

            if ext == ".txt":
                np.savetxt(file_path, selected_data, delimiter=" ", fmt='%s')
            elif ext == ".csv":
                np.savetxt(file_path, selected_data, delimiter=",", fmt='%s')
            elif ext == ".tsv":
                np.savetxt(file_path, selected_data, delimiter="\t", fmt='%s')
