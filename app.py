import os
import re
import logging

from PyQt5.QtWidgets import (QMainWindow, QApplication, QHeaderView, QPushButton, QComboBox, QMenu, QFileDialog, QMessageBox, QDialog, QGroupBox, QLineEdit)
from PyQt5.QtWidgets import QMainWindow, QApplication, QFileDialog, QLineEdit, QCheckBox, QSpinBox, QDoubleSpinBox, QLabel, QComboBox, QMessageBox, QDialog, QPlainTextEdit, QRadioButton, QWidget, QListView, QHBoxLayout, QSpacerItem, QSizePolicy
from PyQt5.QtCore import (
    Qt, QAbstractTableModel, QModelIndex, pyqtSignal
)
from PyQt5.QtCore import Qt, pyqtSlot, QEventLoop, QTimer, QItemSelectionModel, QSemaphore
from PyQt5.QtGui import QIcon
from adbutils import adb
from gui_helper.table_view import TableViewHelper
from gui.mainwindow_ui import Ui_MainWindow
from utils.json_handle import JSONHandler
os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)

class QtPlainTextEditHandler(logging.Handler):
    def __init__(self, widget):
        super().__init__()
        self.widget = widget

    def emit(self, record):
        try:
            msg = self.format(record)
            if self.widget is not None:
                self.widget.appendPlainText(msg)
        except Exception:
            self.handleError(record)

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.initLogging()
        
        self.initSettings()
        self.initTable()
        self.initMissionArea()
        
    def initSettings(self):
        """
        The `initSettings` function in Python initializes settings for Qt widgets by connecting signals
        to update JSON data and loading settings from a JSON file.
        """
        def __on_changed(text):
            sender = self.sender()
            object_name = sender.objectName()
            if object_name == "qt_spinbox_lineedit": return
            self.json_handle.update_json(object_name, text)
        def __connect_settings():
            for ob in self.main_widget.tab_settings.findChildren((QLineEdit, QCheckBox, QRadioButton, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit)):
                if isinstance(ob, QLineEdit):
                    ob.textChanged.connect(__on_changed)
                elif isinstance(ob, QPlainTextEdit):
                    ob.textChanged.connect(lambda o=ob: __on_changed(o.toPlainText()))
                elif isinstance(ob, QCheckBox):
                    ob.stateChanged.connect(__on_changed)
                elif isinstance(ob, QRadioButton):
                    ob.clicked.connect(__on_changed)
                elif isinstance(ob, (QSpinBox, QDoubleSpinBox)):
                    ob.valueChanged.connect(__on_changed)
                elif isinstance(ob, QComboBox):
                    ob.currentTextChanged.connect(__on_changed)
        
        def __load_settings():
            """
            The function `__load_settings` reads data from a JSON file and updates the settings of
            various Qt widgets accordingly.
            """
            data = {}
            data = self.json_handle.read_json()
            childs = self.main_widget.tab_settings.findChildren((QLineEdit,  QCheckBox, QRadioButton, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit))
            for ob in childs:
                object_wd = ob.objectName()
                if data and object_wd in data:
                    if isinstance(ob, QLineEdit):
                        ob.setText(data[object_wd])
                    elif isinstance(ob, QPlainTextEdit):
                        ob.setPlainText(data[object_wd])
                    elif isinstance(ob, (QCheckBox, QRadioButton)):
                        ob.setChecked(data[object_wd])
                    elif isinstance(ob, (QSpinBox, QDoubleSpinBox)):
                        ob.setValue(data[object_wd])
                    elif isinstance(ob, QComboBox):
                        ob.setCurrentText(data[object_wd])
        self.json_handle = JSONHandler("data\\settings.json")
        __load_settings()
        __connect_settings()
    def initUI(self):
        self.main_widget = Ui_MainWindow()
        self.main_widget.setupUi(self)
        self.show()
    def initLogging(self):
        self.logger = logging.getLogger("KhanKhan")
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False
        if not self.logger.handlers:
            file_handler = logging.FileHandler("logs/app.log", encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"))
            self.logger.addHandler(file_handler)

            gui_handler = QtPlainTextEditHandler(self.main_widget.logs)
            gui_handler.setLevel(logging.INFO)
            gui_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S"))
            self.logger.addHandler(gui_handler)

        self.logger.info("Logging initialized")

    def log(self, message, level=logging.INFO):
        if hasattr(self, 'logger'):
            self.logger.log(level, message)

    def initTable(self):
        self.table_helper = TableViewHelper(["Devices", "Status"], self.main_widget.devicesTable)
        self.model = self.table_helper.model
        self.refresh_devices()
        self.model.dataChanged.connect(self.on_data_changed)
    
    def initMissionArea(self):
        self.checkBoxes = {}
        missions = ["[NV] LV12", "[NV] LV13", "[NV] LV14", "[NV] LV15", "[NV] LV16", "[NV] LV17", "[NV] LV18", "[NV] LV19", "[NV] LV20"]
        for mission in missions:
            mission_widget, checkbox = self.create_mission_widget(mission)
            self.checkBoxes[mission] = checkbox
            self.main_widget.verticalLayout_2.addWidget(mission_widget)
        self.main_widget.selectAllCb.stateChanged.connect(self.on_select_all_changed)
        spacerItem = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.main_widget.verticalLayout_2.addItem(spacerItem)
        self.log(f"Mission area initialized with {len(missions)} missions.")
    def on_select_all_changed(self, state):
        for checkbox in self.checkBoxes.values():
            checkbox.blockSignals(True)
            checkbox.setChecked(state == Qt.Checked)
            checkbox.blockSignals(False)
        self.check_box_state_changed(False)
    def create_mission_widget(self, mission_name):
        mission_widget = QWidget()
        mission_layout = QHBoxLayout(mission_widget)
        mission_widget.setStyleSheet("background-color: #dedede;")
        checkbox = QCheckBox()
        # Sanitize mission_name: keep only ASCII alphanumeric and underscores
        sanitized_name = re.sub(r'[^a-zA-Z0-9_]', '', mission_name)
        checkbox.setObjectName(f"missionCheckbox_{sanitized_name}")
        checkbox.setText(mission_name)
        checkbox.stateChanged.connect(self.check_box_state_changed)
        mission_layout.addWidget(checkbox)
        mission_layout.addStretch()
        return mission_widget, checkbox
    def check_box_state_changed(self, _):
        all_checked = sum(cb.isChecked() for cb in self.checkBoxes.values())
        self.main_widget.label_mission_selected.setText(f"Số nhiệm vụ đã chọn: {all_checked}")

    def on_data_changed(self, topLeft: QModelIndex, bottomRight: QModelIndex, roles):
        if Qt.CheckStateRole in roles:
            self.main_widget.label_devices_selected.setText(f"Đã chọn: {len(self.get_devices_checked())}")
    def refresh_devices(self):
        """
        The `refresh_devices` function clears existing rows in a model, retrieves a list of devices,
        updates a label with the total number of devices, and populates a table with device information.
        """
        self.model.removeRows(0, self.model.rowCount())
        devices = self.get_devices()
        self.main_widget.label_total_devices.setText(f"Tổng số thiết bị: {len(devices)}")
        for device in devices:
            row = self.table_helper.insert_row()
            self.table_helper.set_item_text(row, 0, device)
        self.log(f"Refreshed devices list: {len(devices)} device(s) found.")
    def get_devices(self):
        return [i.serial for i in adb.device_list()]
    def get_devices_checked(self):
        """
        The function `get_devices_checked` retrieves the text of checked rows in a table and returns
        them as a list of devices.
        :return: A list of devices that have been checked in the table.
        """
        devices = []
        for row in self.table_helper.get_checked_rows():
            item = self.table_helper.model.item(row, 0)
            devices.append(item.text())
        return devices

    @pyqtSlot()
    def on_loadDevicesBtn_clicked(self):
        self.refresh_devices()
        self.main_widget.label_devices_selected.setText("Đã chọn: 0")
        self.log("Load devices button clicked.")
    

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    main = App()
    sys.exit(app.exec_())
