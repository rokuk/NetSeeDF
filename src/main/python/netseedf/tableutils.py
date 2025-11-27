from PySide6.QtCore import QAbstractTableModel
from PySide6.QtGui import Qt


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
    def __init__(self, current_data, xlabels, ylabels):
        super().__init__()
        self.current_data = current_data[::-1]
        self.xlabels = xlabels
        self.ylabels = ylabels[::-1]
        self.label_headers = False

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            return str(self.current_data[index.row(), index.column()])
        else:
            return None

    def rowCount(self, parent=None):
        return self.current_data.shape[0]

    def columnCount(self, parent=None):
        if len(self.current_data.shape) == 2:
            return self.current_data.shape[1]
        else:
            return 1

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            if self.label_headers:  # label headers
                if orientation == Qt.Orientation.Horizontal:
                    return str(self.xlabels[section])
                if orientation == Qt.Orientation.Vertical:
                    return str(self.ylabels[section])
            else:  # do not label headers
                return str(section + 1)
        return None

    def show_label_headers(self, label_headers):
        self.label_headers = label_headers
        self.headerDataChanged.emit(Qt.Orientation.Horizontal, 0, self.columnCount() - 1)
        self.headerDataChanged.emit(Qt.Orientation.Vertical, 0, self.rowCount() - 1)

    def set_data(self, current_data):
        self.beginResetModel()
        self.current_data = current_data[::-1]
        self.endResetModel()

    def get_xwidth(self, data_table):
        return get_max_width(data_table, self.xlabels)

    def get_ywidth(self, data_table):
        return get_max_width(data_table, self.ylabels)


class SimpleTableModel(QAbstractTableModel):
    def __init__(self, current_data):
        super().__init__()
        self.current_data = current_data

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            return str(self.current_data[index.row(), index.column()])
        else:
            return None

    def rowCount(self, parent=None):
        return self.current_data.shape[0]

    def columnCount(self, parent=None):
        if len(self.current_data.shape) == 2:
            return self.current_data.shape[1]
        else:
            return 1

    def set_data(self, current_data):
        self.beginResetModel()
        self.current_data = current_data
        self.endResetModel()
