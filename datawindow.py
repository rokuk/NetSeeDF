import numpy as np
from PyQt6.QtGui import QCursor
from netCDF4 import Dataset
from PyQt6.QtWidgets import QCheckBox, QMessageBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QLabel, \
    QHBoxLayout, QSpinBox, QAbstractItemView, QMenu, QApplication
from PyQt6.QtCore import Qt


# Window which shows a table of the data for the chosen variable and some info about the variable.
# Displayed when 'Show data' button is clicked.
class DataWindow(QWidget):
    def __init__(self, file_name, variable_name, file_path):
        super().__init__()

        self.setWindowTitle(variable_name + " - NetSeeDF")
        self.setMinimumSize(200, 500)

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
        data_table.customContextMenuRequested.connect(self.open_menu)
        data_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.data_table = data_table

        if len(data.shape) == 1: # 1-dimensional data
            data_table.setRowCount(len(data))
            data_table.setColumnCount(1)
            for i in range(len(data)):
                data_table.setItem(i, 0, QTableWidgetItem(str(data[i])))
            data_table.resizeColumnsToContents()

        elif len(data.shape) == 2: # 2-dimensional data
            data_table.setRowCount(len(data))
            data_table.setColumnCount(len(data[0]))
            for i in range(len(data)):
                for j in range(len(data[0])):
                    data_table.setItem(i, j, QTableWidgetItem(str(data[i][j])))
            data_table.resizeColumnsToContents()

        elif len(data.shape) == 3: # 3-dimensional data
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

            # # x axis variable selector
            # xaxis_selector_widget = QWidget()
            # xaxis_selector_layout = QHBoxLayout()
            # xaxis_selector_layout.addWidget(QLabel("X axis variable: "))
            # xaxis_dropdown = QComboBox()
            # xaxis_dropdown.addItems(variable_data.dimensions)
            # xaxis_dropdown.setCurrentText(variable_data.dimensions[x_dim_index]) # set the computed default dimension
            # xaxis_selector_layout.addWidget(xaxis_dropdown)
            # xaxis_selector_widget.setLayout(xaxis_selector_layout)
            # xaxis_selector_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
            #
            # # y axis variable selector
            # yaxis_selector_widget = QWidget()
            # yaxis_selector_layout = QHBoxLayout()
            # yaxis_selector_layout.addWidget(QLabel("Y axis variable: "))
            # yaxis_dropdown = QComboBox()
            # yaxis_dropdown.addItems(variable_data.dimensions)
            # yaxis_dropdown.setCurrentText(variable_data.dimensions[y_dim_index]) # set the computed default dimension
            # yaxis_selector_layout.addWidget(yaxis_dropdown)
            # yaxis_selector_widget.setLayout(yaxis_selector_layout)
            # yaxis_selector_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

            # slicing variable index selector
            slice_selector_widget = QWidget()
            slice_selector_layout = QHBoxLayout()
            slice_selector_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
            slice_selector_widget.setLayout(slice_selector_layout)
            slice_selector_layout.addWidget(QLabel("Slice index: "))
            slice_selector_layout.addWidget(QLabel(variable_data.dimensions[slice_dim_index] + "  ="))
            slice_spinner = QSpinBox()
            slice_spinner.setMinimum(0)
            slice_spinner.setMaximum(variable_data.shape[slice_dim_index]-1) # set max index to size of the axis corresponding to the slicing variable
            slice_spinner.setValue(0)
            slice_spinner.valueChanged.connect(self.update_table)
            self.slice_spinner = slice_spinner
            slice_selector_layout.addWidget(slice_spinner)
            try:
                units = ncfile.variables[variable_data.dimensions[slice_dim_index]].units # get units of the slicing variable
                slice_units = QLabel("   units: " + units)
                slice_selector_layout.addWidget(slice_units)
            except Exception: # in case the units are not included in the file
                pass

            # axis selectors container
            axis_selectors_widget = QWidget()
            axis_selectors_layout = QVBoxLayout()
            #axis_selectors_layout.addWidget(xaxis_selector_widget)
            #axis_selectors_layout.addWidget(yaxis_selector_widget)
            axis_selectors_layout.addWidget(slice_selector_widget)

            labels_selector = QWidget()
            labels_selector_layout = QHBoxLayout()
            labels_checkbox = QCheckBox()
            labels_selector_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
            labels_selector.setLayout(labels_selector_layout)
            labels_checkbox.checkStateChanged.connect(self.update_headers)
            self.labels_checkbox = labels_checkbox
            labels_selector_layout.addWidget(labels_checkbox)
            labels_selector_layout.addWidget(QLabel("show axis values"))

            axis_selectors_layout.addWidget(labels_selector)
            axis_selectors_widget.setLayout(axis_selectors_layout)
            layout.addWidget(axis_selectors_widget)

            self.update_table()  # load initial data into table
            self.update_headers() # set table headers

        else: # other shapes of data, which are not supported
            print(data.shape)
            dlg = QMessageBox(self)
            dlg.setWindowTitle("NetSeeDF error")
            dlg.setText("This shape of data is not supported yet!")
            dlg.exec()

        layout.addWidget(data_table)

        # we are done reading the data from the NetCDF file
        ncfile.close()

        self.setLayout(layout)


    def update_table(self):
        sliced_data = self.data.take(self.slice_spinner.value(), axis=self.slice_dim_index)  # subset data with the current slice index

        sliced_data[sliced_data == self.fill_value] = np.nan  # replace fill values with numpy's NaN

        # display data
        self.data_table.setRowCount(len(sliced_data))
        self.data_table.setColumnCount(len(sliced_data[0]))
        for i in range(len(sliced_data)):
            for j in range(len(sliced_data[0])):
                self.data_table.setItem(i, j, QTableWidgetItem(str(sliced_data[i, j])))

        self.data_table.resizeColumnsToContents()


    def update_headers(self):
        if self.labels_checkbox.isChecked(): # display lat lon values as table headers
            if self.xdataunit == "degrees_east": # if the axis represent lat lon coordinates and units are given in the NetCDF file, display the degree symbol
                self.data_table.setHorizontalHeaderLabels([str(i) + "°" for i in self.xdata])
            else:
                self.data_table.setHorizontalHeaderLabels([str(i) for i in self.xdata])
            if self.xdataunit == "degrees_north":
                self.data_table.setHorizontalHeaderLabels([str(i) + "°" for i in self.ydata])
            else:
                self.data_table.setVerticalHeaderLabels([str(i) for i in self.ydata])
        else: # display axis indexes in headers
            self.data_table.setHorizontalHeaderLabels([str(i) for i in range(1,len(self.xdata)+1)])
            self.data_table.setVerticalHeaderLabels([str(i) for i in range(1,len(self.ydata)+1)])

        self.data_table.resizeColumnsToContents()


    def open_menu(self, point):
        item = self.data_table.itemAt(point)
        if item:
            menu = QMenu()
            copy_action = menu.addAction("Copy")
            action = menu.exec(QCursor.pos())
            if action == copy_action:
                QApplication.clipboard().setText(item.text())