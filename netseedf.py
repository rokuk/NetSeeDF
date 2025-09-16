import sys
import os
from pathlib import Path

from netCDF4 import Dataset
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox, QPlainTextEdit, QHBoxLayout, QVBoxLayout, \
    QPushButton, QWidget, QTreeWidget, QTreeWidgetItem, QFileDialog
from PyQt6.QtCore import Qt
from datawindow import DataWindow
from plotwindow import PlotWindow


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("NetSeeDF")
        self.setGeometry(2800, 100, 1000, 600)

        self.file_paths = []
        self.firsttreeitem = True
        self.file_paths_dict = {}
        self.open_windows = []

        select_widget = QWidget()
        select_layout = QVBoxLayout()
        self.select_layout = select_layout
        select_widget.setLayout(select_layout)

        file_button = QPushButton("Open NetCDF file")
        file_button.clicked.connect(self.open_file)
        select_layout.addWidget(file_button)

        tree = QTreeWidget()
        tree.setColumnCount(2)
        tree.setHeaderLabels(["Name", "Description", "Shape"])
        tree.setStyleSheet("QTreeView::item:selected { background-color:#007acc; color:white;}")
        tree.currentItemChanged.connect(self.on_selection_change)
        tree.setColumnWidth(0, 230)
        tree.setColumnWidth(1, 150)
        select_layout.addWidget(tree)
        self.tree = tree

        desc_widget = QWidget()
        desc_layout = QVBoxLayout()
        desc_widget.setLayout(desc_layout)

        data_button = QPushButton("Show data")
        data_button.clicked.connect(self.show_data)
        data_button.setEnabled(False)
        self.data_button = data_button
        plot_button = QPushButton("Make plot")
        plot_button.clicked.connect(self.make_plot)
        plot_button.setEnabled(False)
        self.plot_button = plot_button

        buttons_widget = QWidget()
        buttons_layout = QHBoxLayout()
        buttons_widget.setLayout(buttons_layout)
        buttons_layout.addWidget(data_button)
        buttons_layout.addWidget(plot_button)
        desc_layout.addWidget(buttons_widget)

        text_area = QPlainTextEdit()
        text_area.setPlaceholderText("Open a file to view its contents")
        text_area.setReadOnly(True)
        text_area.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        text_area.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.text_area = text_area
        desc_layout.addWidget(text_area)

        main_layout = QHBoxLayout()
        main_widget = QWidget()
        main_widget.setLayout(main_layout)
        main_layout.addWidget(select_widget)
        main_layout.addWidget(desc_widget)
        self.setCentralWidget(main_widget)


    # Closes all windows when the MainWindow is closed.
    def closeEvent(self, event):
        QApplication.closeAllWindows()
        event.accept()


    # Show a file dialog and add the selected file to the tree of files and the variables they contain
    # Called when 'Open NetCDF file' button is clicked
    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open NetCDF file",
            str(Path.home()),
            "NetCDF files (*.nc)"
        )

        #file_path = r"C:\Users\rokuk\Documents\Code\aquacrop-testing\inputdata\historical\tas_12km_ARSO_v5_day_19810101_20101231.nc"

        if file_path:
            if file_path in self.file_paths:
                dlg = QMessageBox(self)
                dlg.setWindowTitle("NetSeeDF message")
                dlg.setText("This file is already open!")
                dlg.exec()
                return

            basename = os.path.basename(file_path)
            self.file_paths.append(file_path)
            self.file_paths_dict[basename] = file_path

            ncfile = Dataset(file_path, "r")

            item = QTreeWidgetItem([basename])

            for var in ncfile.variables:
                longname = ""
                try:
                    longname = ncfile.variables[var].long_name
                except Exception:
                    try:
                        longname = ncfile.variables[var].standard_name
                    except Exception:
                        pass

                shapeofdata = ""
                try:
                    shapeofdata = str(ncfile.variables[var].shape)
                except IndexError:
                    pass
                child = QTreeWidgetItem([var, longname, shapeofdata])
                item.addChild(child)

            #print(ncfile.groups)

            #for children in walktree(ncfile):
            #    for child in children:
            #        print(child)

            ncfile.close()

            self.tree.addTopLevelItem(item)
            self.tree.expandItem(item)
            self.tree.setCurrentItem(item)


    # Displays a table of the data for the selected variable in a new window
    def show_data(self):
        current_item = self.tree.currentItem()
        variable_name = current_item.data(0, Qt.ItemDataRole.DisplayRole)
        file_name = current_item.parent().data(0, Qt.ItemDataRole.DisplayRole)
        file_path = self.file_paths_dict[file_name]

        dataw = DataWindow(file_name, variable_name, file_path)
        dataw.show()
        self.open_windows.append(dataw)


    # Plot the data for the selected variable in a new window
    def make_plot(self):
        current_item = self.tree.currentItem()
        variable_name = current_item.data(0, Qt.ItemDataRole.DisplayRole)
        file_name = current_item.parent().data(0, Qt.ItemDataRole.DisplayRole)
        file_path = self.file_paths_dict[file_name]

        plotw = PlotWindow(file_name, variable_name, file_path)
        plotw.show()
        self.open_windows.append(plotw)

    # Called when the user select a new row in the tree view of files and variables
    # File info or variable info is displayed in the text area
    def on_selection_change(self, current, previous):
        selection_name = current.data(0, Qt.ItemDataRole.DisplayRole)
        parent = current.parent()

        if parent is None: # file is selected
            ncfile = Dataset(self.file_paths_dict[selection_name], "r")

            dimensiontext = "dimension \t size\n ----------------------\n"
            for key, value in ncfile.dimensions.items():
                dimensiontext += key + "\t" + str(value.size) + "\n"

            attrtext = ""
            for key in ncfile.ncattrs():
                value = ncfile.getncattr(str(key))
                attrtext += str(key) + "\t" + str(value) + "\n"

            ncfile.close()

            self.text_area.setPlainText(selection_name + "\n\nDIMENSIONS\n" + dimensiontext + "\n\nATTRIBUTES\n" + attrtext)
            self.plot_button.setEnabled(False)
            self.data_button.setEnabled(False)

        else: # variable is selected
            parent_name = parent.data(0, Qt.ItemDataRole.DisplayRole) # get the name of the file containing the selected variable
            ncfile = Dataset(self.file_paths_dict[parent_name], "r")
            self.text_area.setPlainText(str(ncfile.variables[selection_name]))
            if len(ncfile.variables[selection_name].shape) == 3: # only enable plot button for 3-dimensional variables
                self.plot_button.setEnabled(True)
            self.data_button.setEnabled(True)
            ncfile.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())