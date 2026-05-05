import threading
import time
from typing import List
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QTableView, QPushButton, QComboBox
from PyQt5.QtCore import Qt


class TableViewHelper:
    def __init__(self, column_labels: List[str], tableView: QTableView, use_checkbox=True):
        self.column_labels = column_labels
        self.tableView = tableView
        self.use_checkbox = use_checkbox
        self.__model = QStandardItemModel(0, len(self.column_labels))
        self.__model.setHorizontalHeaderLabels(self.column_labels)
        if use_checkbox:
            self.__model.setHeaderData(0, Qt.Horizontal, Qt.Unchecked, Qt.CheckStateRole)
            self.set_keyPressEvent()
        self.tableView.setModel(self.__model)
    
    def set_keyPressEvent(self):
        original_keypress = self.tableView.keyPressEvent
        def _keyPressEvent(event):
            if event.key() == Qt.Key_Space:
                indexes = self.tableView.selectionModel().selectedRows()
                rows = [ix.row() for ix in indexes]
                for row in rows:
                    item = self.__model.item(row, 0)
                    new_state = Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked
                    item.setCheckState(new_state)
            original_keypress(event)
        self.tableView.keyPressEvent = _keyPressEvent
    @property
    def row_selected(self):
        return [index.row() for index in self.tableView.selectionModel().selectedRows()]
    @property
    def model(self):
        return self.__model
    def set_item_text(self, row: int, col: int, text: str):
        if text is None: text = ""
        text = str(text)
        item = self.__model.item(row, col)
        if item is None:
            new_item = QStandardItem(text)
            # If this is the first column, make the item checkable so each row has its own checkbox
            if col == 0 and self.use_checkbox:
                new_item.setFlags(new_item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                new_item.setCheckable(True)
                new_item.setCheckState(Qt.Unchecked)
            self.__model.setItem(row, col, new_item)
        else:
            item.setText(text)
            # ensure first column items remain checkable when updated
            if col == 0 and not item.isCheckable() and self.use_checkbox:
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                item.setCheckable(True)
                item.setCheckState(Qt.Unchecked)
    def insert_row(self):
        row = self.__model.rowCount()
        self.__model.insertRow(row)
        
        return row


    def get_checked_rows(self):
        """Return list of row indices which have their first-column checkbox checked."""
        rows = []
        for row in range(self.__model.rowCount()):
            item = self.__model.item(row, 0)
            if item and item.isCheckable() and item.checkState() == Qt.Checked:
                rows.append(row)
        return rows