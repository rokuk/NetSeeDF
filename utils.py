# try to interpret the shape string as a tuple and return the sze of it
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QMenu, QApplication


def tuple_length(tuple_str):
    if not isinstance(tuple_str, str):
        return -1
    s = tuple_str.strip()
    if not (s.startswith('(') and s.endswith(')')):
        return -1
    inner = s[1:-1]
    # Disallow nested tuples
    if '(' in inner or ')' in inner:
        return -1
    # Empty tuple
    if inner == '':
        return -1
    # Whitespace only is invalid
    if inner.strip() == '':
        return -1
    # Special case: all elements empty, e.g., '(, )'
    parts = inner.split(',')
    if all(p.strip() == '' for p in parts):
        return -1
    # No trailing comma allowed (except for single element)
    if parts[-1].strip() == '':
        if len(parts) == 2 and parts[0].strip() != '':
            return 1  # single element tuple like '(1,)'
        return -1
    # No empty elements allowed
    if any(p.strip() == '' for p in parts):
        return -1
    return len(parts)


def show_context_menu(self, point):
    item = self.data_table.itemAt(point)
    if item:
        menu = QMenu()
        copy_action = menu.addAction("Copy")
        action = menu.exec(QCursor.pos())
        if action == copy_action:
            QApplication.clipboard().setText(item.text())