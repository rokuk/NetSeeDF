import sys
import traceback

from fbs_runtime.application_context import cached_property
from fbs_runtime.application_context.PySide6 import ApplicationContext


def excepthook(type, value, tback):
    traceback.print_exception(type, value, tback)
    sys.__excepthook__(type, value, tback)


sys.excepthook = excepthook

import os

if sys.platform == "linux":
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"]="--disable-gpu"

from pathlib import Path
from netCDF4 import Dataset
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QPlainTextEdit, QHBoxLayout, \
    QPushButton, QWidget, QTreeWidget, QTreeWidgetItem, QFileDialog, QGridLayout
from PySide6.QtCore import Qt

from datawindow_1d import DataWindow1d
from datawindow_2d import DataWindow2d
from datawindow_3d import DataWindow3d
from plotwindow_2d import PlotWindow2d
from plotwindow_3d import PlotWindow3d


class MainWindow(QMainWindow):
    def __init__(self, appcontext):
        super().__init__()

        self.appcontext = appcontext

        self.setWindowTitle("NetSeeDF")
        self.setMinimumSize(900, 400)

        self.file_paths = []
        self.firsttreeitem = True
        self.file_paths_dict = {}
        self.open_windows = []

        file_button = QPushButton("Open NetCDF file")
        file_button.clicked.connect(self.open_file)

        tree = QTreeWidget()
        tree.setColumnCount(2)
        tree.setHeaderLabels(["Name", "Description", "Shape"])
        tree.setStyleSheet("QTreeView::item:selected { background-color:#007acc; color:white;}")
        tree.currentItemChanged.connect(self.on_selection_change)
        tree.setColumnWidth(0, 200)
        tree.setColumnWidth(1, 120)
        self.tree = tree

        data_button = QPushButton("Show data")
        data_button.clicked.connect(self.show_data)
        data_button.setEnabled(False)
        self.data_button = data_button
        plot_button = QPushButton("Show map")
        plot_button.clicked.connect(self.show_map)
        plot_button.setEnabled(False)
        self.plot_button = plot_button

        buttons_widget = QWidget()
        buttons_layout = QHBoxLayout()
        buttons_widget.setLayout(buttons_layout)
        buttons_layout.addWidget(data_button)
        buttons_layout.addWidget(plot_button)

        text_area = QPlainTextEdit()
        text_area.setPlaceholderText("Open a file to view its contents")
        text_area.setReadOnly(True)
        text_area.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        text_area.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.text_area = text_area

        main_widget = QWidget()
        main_layout = QGridLayout()
        main_widget.setLayout(main_layout)
        main_layout.addWidget(file_button, 0, 0)
        main_layout.addWidget(tree, 1, 0)
        main_layout.addWidget(buttons_widget, 0, 1)
        main_layout.addWidget(text_area, 1, 1)
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
                        try:
                            longname = ncfile.variables[var].description
                        except Exception:
                            pass

                shapeofdata = ""
                try:
                    shapeofdata = str(ncfile.variables[var].shape)
                except IndexError:
                    pass
                child = QTreeWidgetItem([var, longname, shapeofdata])
                item.addChild(child)

            # print(ncfile.groups)

            # for children in walktree(ncfile):
            #    for child in children:
            #        print(child)

            ncfile.close()

            self.tree.addTopLevelItem(item)
            self.tree.expandItem(item)
            self.tree.setCurrentItem(item)

    # Get currently selected item in the tree view and the number of dimensions of the variable
    def get_info_about_selected(self):
        current_item = self.tree.currentItem()
        variable_name = current_item.data(0, Qt.ItemDataRole.DisplayRole)
        file_name = current_item.parent().data(0, Qt.ItemDataRole.DisplayRole)
        file_path = self.file_paths_dict[file_name]

        # Read the data shape
        ncfile = Dataset(file_path, "r")
        num_dimensions = len(ncfile.variables[variable_name].shape)
        ncfile.close()

        return num_dimensions, file_name, variable_name, file_path

    # Displays a table of the data for the selected variable in a new window
    def show_data(self):
        num_dimensions, file_name, variable_name, file_path = self.get_info_about_selected()

        if num_dimensions == 1:
            dataw = DataWindow1d(file_name, variable_name, file_path)
        elif num_dimensions == 2:
            dataw = DataWindow2d(file_name, variable_name, file_path)
        elif num_dimensions == 3:
            dataw = DataWindow3d(file_name, variable_name, file_path)
        else:
            dlg = QMessageBox(self)
            dlg.setWindowTitle("NetSeeDF message")
            dlg.setText("This shape of data is currently not supported!")
            dlg.exec()
            return

        dataw.show()
        self.open_windows.append(dataw)

    # Plot the data for the selected variable in a new window
    def show_map(self):
        num_dimensions, file_name, variable_name, file_path = self.get_info_about_selected()

        if num_dimensions == 3:
            plotw = PlotWindow3d(file_name, variable_name, file_path, self.appcontext)
        elif num_dimensions == 2:
            plotw = PlotWindow2d(file_name, variable_name, file_path, self.appcontext)
        else:
            dlg = QMessageBox(self)
            dlg.setWindowTitle("NetSeeDF message")
            dlg.setText("This shape of data is currently not supported!")
            dlg.exec()
            return

        plotw.show()
        self.open_windows.append(plotw)

    # Called when the user select a new row in the tree view of files and variables
    # File info or variable info is displayed in the text area
    def on_selection_change(self, current, previous):
        selection_name = current.data(0, Qt.ItemDataRole.DisplayRole)
        parent = current.parent()

        if parent is None:  # file is selected
            ncfile = Dataset(self.file_paths_dict[selection_name], "r")

            dimensiontext = "dimension \t size\n ----------------------\n"
            for key, value in ncfile.dimensions.items():
                dimensiontext += key + "\t" + str(value.size) + "\n"

            attrtext = ""
            for key in ncfile.ncattrs():
                value = ncfile.getncattr(str(key))
                attrtext += str(key) + "\t" + str(value) + "\n"

            ncfile.close()

            self.text_area.setPlainText(
                selection_name + "\n\nDIMENSIONS\n" + dimensiontext + "\n\nATTRIBUTES\n" + attrtext)
            self.plot_button.setEnabled(False)
            self.data_button.setEnabled(False)

        else:  # variable is selected
            parent_name = parent.data(0, Qt.ItemDataRole.DisplayRole)  # get the name of the file containing the selected variable
            ncfile = Dataset(self.file_paths_dict[parent_name], "r")
            self.text_area.setPlainText(str(ncfile.variables[selection_name]))
            if len(ncfile.variables[selection_name].shape) == 3 or len(
                    ncfile.variables[selection_name].shape) == 2:  # only enable plot button for 3-dimensional variables
                self.plot_button.setEnabled(True)
            else:
                self.plot_button.setEnabled(False)
            self.data_button.setEnabled(True)
            ncfile.close()


class AppContext(ApplicationContext):
    def run(self):
        self.main_window.show()
        return self.app.exec()

    @cached_property
    def main_window(self):
        return MainWindow(self)

    @cached_property
    def webchanneljs(self):
        webchannelcodepath = self.get_resource("qwebchannel.js")
        with open(webchannelcodepath) as f:
            webchanneljs = f.read()
        return webchanneljs


if __name__ == "__main__":
    try:  # Set taskbar icon on Windows
        from ctypes import windll  # Only exists on Windows.
        myappid = 'org.rokuk.netseedf'
        windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except ImportError:
        pass

    appctxt = AppContext()
    exit_code = appctxt.run()
    sys.exit(exit_code)
