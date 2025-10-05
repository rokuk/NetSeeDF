import numpy as np
import pandas as pd
from PyQt6.QtCore import QAbstractTableModel, Qt
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QMenu, QApplication, QFileDialog, QMessageBox


def show_context_menu(self, point):
    index = self.data_table.indexAt(point)
    if index.isValid():
        menu = QMenu()
        copy_action = menu.addAction("Copy")
        action = menu.exec(QCursor.pos())
        if action == copy_action:
            value = index.data()
            QApplication.clipboard().setText(str(value))


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
                    df = pd.DataFrame(selected_data)
                    df.to_excel(file_path, index=False, header=False)
            except Exception:
                dlg = QMessageBox(self)
                dlg.setWindowTitle("NetSeeDF message")
                dlg.setText("There was an error saving the file!")
                dlg.exec()
                return


def get_max_width(data_table, labels):
    metrics = data_table.fontMetrics()
    if hasattr(labels, 'tolist'):
        labels = labels.tolist()
    labels = [str(lbl) for lbl in labels]
    max_width = 0
    for label in labels:
        width = metrics.horizontalAdvance(label)
        if width > max_width:
            max_width = width
    return max_width


class TableModel(QAbstractTableModel):
    def __init__(self, data, xlabels, ylabels):
        super().__init__()
        self.data = data
        self.xlabels = xlabels
        self.ylabels = ylabels
        self.label_headers = False

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            value = self.data[index.row(), index.column()]
            return str(value)
        return None

    def rowCount(self, parent=None):
        return self.data.shape[0]

    def columnCount(self, parent=None):
        if len(self.data.shape) == 2:
            return self.data.shape[1]
        else:
            return 1

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            if self.label_headers: # label headers
                if orientation == Qt.Orientation.Horizontal:
                    return str(self.xlabels[section])
                if orientation == Qt.Orientation.Vertical:
                    return str(self.ylabels[section])
            else: # do not label headers
                return str(section+1)
        return None

    def show_label_headers(self, label_headers):
        self.label_headers = label_headers

    def set_data(self, data):
        self.beginResetModel()
        self.data = data
        self.endResetModel()

    def get_xwidth(self, data_table):
        return get_max_width(data_table, self.xlabels)

    def get_ywidth(self, data_table):
        return get_max_width(data_table, self.ylabels)