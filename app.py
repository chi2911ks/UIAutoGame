
import os
import re
import logging
from collections import defaultdict

from PyQt5.QtWidgets import (QMainWindow, QApplication, QHeaderView, QPushButton, QComboBox, QMenu, QFileDialog, QMessageBox, QDialog, QGroupBox, QLineEdit)
from PyQt5.QtWidgets import QMainWindow, QApplication, QFileDialog, QLineEdit, QCheckBox, QSpinBox, QDoubleSpinBox, QLabel, QComboBox, QMessageBox, QDialog, QPlainTextEdit, QRadioButton, QWidget, QListView, QHBoxLayout, QVBoxLayout, QSpacerItem, QSizePolicy
from PyQt5.QtCore import (
    Qt, QAbstractTableModel, QModelIndex, pyqtSignal, QSize
)
from PyQt5.QtCore import Qt, pyqtSlot, QEventLoop, QTimer, QItemSelectionModel, QSemaphore
from PyQt5.QtGui import QIcon
from adbutils import adb
from gui_helper.table_view import TableViewHelper
from gui.mainwindow_ui import Ui_MainWindow
from mission import Mission
from utils.json_handle import JSONHandler
from worker import Worker
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
        self.device_logs = defaultdict(list)
        self.run_all_changing = False
        
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
        self.main_widget.runAllCb.stateChanged.connect(self.on_run_all_changed)
        self.main_widget.showPhoneCb.stateChanged.connect(self.on_show_phone_changed)
        self.show()
    def initLogging(self):
        self.logger = logging.getLogger("AutoGameLogger")
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False
        if not self.logger.handlers:
            file_handler = logging.FileHandler("logs/app.log", encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"))
            self.logger.addHandler(file_handler)

            gui_handler = QtPlainTextEditHandler(self.main_widget.logs)
            gui_handler.setLevel(logging.INFO)
            
            gui_handler.setFormatter(logging.Formatter("%(message)s"))
            self.logger.addHandler(gui_handler)
    def log(self, message, level=logging.INFO):
        if hasattr(self, 'logger'):
            self.logger.log(level, message)
        self._store_device_log(message)

    def _store_device_log(self, message):
        match = re.match(r'^\[([^\]]+)\]\s*(.*)$', message)
        if match:
            serial = match.group(1)
            self.device_logs[serial].append(message)
        else:
            self.device_logs["GLOBAL"].append(message)

    def initTable(self):
        self.table_helper = TableViewHelper(["Devices", "Status", "Log"], self.main_widget.devicesTable)
        self.model = self.table_helper.model
        
        self.main_widget.devicesTable.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.main_widget.devicesTable.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.main_widget.devicesTable.setColumnWidth(2, 40)
        self.refresh_devices()
        self.model.dataChanged.connect(self.on_data_changed)
    
    def initMissionArea(self):
        self.checkBoxes = {}
        for mission in Mission:
            mission_widget, checkbox = self.create_mission_widget(mission.value)
            self.checkBoxes[mission] = checkbox
            self.main_widget.verticalLayout_2.addWidget(mission_widget)
        self.main_widget.selectAllCb.stateChanged.connect(self.on_select_all_changed)
        spacerItem = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.main_widget.verticalLayout_2.addItem(spacerItem)
        self.log(f"Mission area initialized with {len(Mission)} missions.")
    def get_selected_missions(self):
        """
        The function `get_selected_missions` retrieves the text of all missions from a dictionary of
        checkboxes and returns them as a list.
        :return: A list of all missions.
        """
        missions = []
        for name, cb in self.checkBoxes.items():
            if cb.isChecked():
                missions.append(name)
        return missions
    @pyqtSlot(int)
    def on_run_all_changed(self, state):
        print("Run all state changed:", state)
        if state == Qt.Checked:
            for row in range(self.table_helper.model.rowCount()):
                item = self.table_helper.model.item(row, 0)
                item.setCheckState(Qt.Checked)
            if self.startThread():
                self.log("Run all started.")
            else:
                self.log("Failed to start run all.")
                for row in range(self.table_helper.model.rowCount()):
                    item = self.table_helper.model.item(row, 0)
                    item.setCheckState(Qt.Unchecked)
        else:
            self.stopThread()
    def on_select_all_changed(self, state):
        for checkbox in self.checkBoxes.values():
            checkbox.blockSignals(True)
            checkbox.setChecked(state == Qt.Checked)
            checkbox.blockSignals(False)
        self.check_box_state_changed(True if state == Qt.Checked else False)
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
    def check_box_state_changed(self, state):
        all_checked = sum(cb.isChecked() for cb in self.checkBoxes.values())
        self.main_widget.label_mission_selected.setText(f"Số nhiệm vụ đã chọn: {all_checked}")
        if state == Qt.Unchecked and hasattr(self, 'worker') and self.worker.isRunning():
            self.log(f"Device restart mission(s).")
            self.restartThread()

    def on_data_changed(self, topLeft: QModelIndex, bottomRight: QModelIndex, roles):
        if Qt.CheckStateRole in roles:
            self.main_widget.label_devices_selected.setText(f"Đã chọn: {len(self.get_devices_checked())}")
            
            
    def refresh_devices(self):
        """
        The `refresh_devices` function clears existing rows in a model, retrieves a list of devices,
        updates a label with the total number of devices, and populates a table with device information.
        """
        # self.device_logs.clear()
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.log("Cannot refresh devices while worker is running.", level=logging.WARNING)
            QMessageBox.warning(self, "Worker đang chạy", "Không thể làm mới danh sách thiết bị khi worker đang chạy. Vui lòng dừng worker trước khi làm mới.")
            return
        self.model.removeRows(0, self.model.rowCount())
        devices = self.get_devices()
        self.main_widget.label_total_devices.setText(f"Tổng số thiết bị: {len(devices)}")
        for device in devices:
            row = self.table_helper.insert_row()
            self.table_helper.set_item_text(row, 0, device)
            self._set_row_log_button(row, device)
        self.log(f"Refreshed devices list: {len(devices)} device(s) found.")
    def get_devices(self):
        # return ["emulator-555%s" % i for i in range(10)]
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
    def get_serial(self, row):
        item = self.table_helper.model.item(row, 0)
        return item.text() if item else None

    def show_device_log_dialog(self, serial):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Log thiết bị {serial}")
        dialog.resize(700, 400)

        layout = QVBoxLayout(dialog)
        log_view = QPlainTextEdit(dialog)
        log_view.setReadOnly(True)
        log_view.setPlainText("\n".join(self.device_logs.get(serial, ["Không có log cho thiết bị này."])))
        layout.addWidget(log_view)

        dialog.exec_()

    def _set_row_log_button(self, row, serial):
        button = QPushButton("")
        button.setFlat(True)
        button.setStyleSheet("border: none; background: transparent;")

        icon_path = os.path.join(os.path.dirname(__file__), "icons", "log.svg")
        button.setIcon(QIcon(icon_path))
        button.setIconSize(QSize(18, 18))

        button.setToolTip("Xem log thiết bị")
        button.clicked.connect(lambda checked, s=serial: self.show_device_log_dialog(s))
        self.main_widget.devicesTable.setIndexWidget(self.model.index(row, 2), button)

    @pyqtSlot()
    def on_deviceLogBtn_clicked(self):
        selected = self.main_widget.devicesTable.selectionModel().selectedRows()
        if not selected:
            QMessageBox.warning(self, "Chưa chọn thiết bị", "Vui lòng chọn một thiết bị để xem log.")
            return
        if len(selected) > 1:
            QMessageBox.warning(self, "Chọn một thiết bị", "Vui lòng chỉ chọn một thiết bị để xem log.")
            return
        row = selected[0].row()
        serial = self.get_serial(row)
        if serial:
            self.show_device_log_dialog(serial)

    @pyqtSlot()
    def on_loadDevicesBtn_clicked(self):
        self.refresh_devices()
        self.main_widget.label_devices_selected.setText("Đã chọn: 0")
        self.log("Load devices button clicked.")
    
    @pyqtSlot()
    def on_startBtn_clicked(self):
        if self.main_widget.startBtn.text() == "START":
            if self.checkFirstRun():
                self.startThread()
        else:
            self.stopThread()
    
    def stopThread(self):
        self.log("Stopping worker thread.")
        if hasattr(self, 'worker'):
            if self.worker.isRunning():
                self.main_widget.startBtn.setEnabled(False)
                self.worker.stop()
            else:
                self.main_widget.startBtn.setText("START")
        else:
            self.main_widget.startBtn.setText("START")
    def checkFirstRun(self):
        selected_devices = self.get_devices_checked()
        if not selected_devices:
            QMessageBox.warning(self, "Chưa chọn thiết bị", "Vui lòng chọn ít nhất một thiết bị để bắt đầu.")
            return
        selected_missions = [name for name, cb in self.checkBoxes.items() if cb.isChecked()]
        if not selected_missions:
            QMessageBox.warning(self, "Chưa chọn nhiệm vụ", "Vui lòng chọn ít nhất một nhiệm vụ để bắt đầu.")
            return
        return True
    def startThread(self):
        self.main_widget.startBtn.setText("STOP")
        self.worker = Worker(app=self)
        self.worker.logs.connect(self.log)
        self.worker.show_status.connect(lambda row, status: self.table_helper.set_item_text(row, 1, status))
        self.worker.finished.connect(self.finished)
        self.worker.start()
        return self.worker
    def finished(self):
        self.main_widget.startBtn.setEnabled(True)
        self.log("Worker thread finished.")
        self.main_widget.startBtn.setText("START")
    def restartThread(self):
        if hasattr(self, 'worker'):
            self.worker.stop()
        self.startThread()
    @pyqtSlot()
    def on_pauseBtn_clicked(self):
        if self.main_widget.pauseBtn.text() == "PAUSE":
            self.main_widget.pauseBtn.setText("RESUME")
            self.worker.pause()
        else:
            self.main_widget.pauseBtn.setText("PAUSE")
            self.worker.resume()
    @pyqtSlot()
    def on_resizeBtn_clicked(self):
        width, height = self.main_widget.widthPhone.text(), self.main_widget.heightPhone.text()
        int_width, int_height = None, None
        try:
            int_width = int(width)
            int_height = int(height)
        except ValueError:
            QMessageBox.warning(self, "Invalid input", "Please enter valid integers for width and height.")
            return
        print("Resize button clicked with width:", int_width, "and height:", int_height)
    @pyqtSlot()
    def on_loadDataBtn_clicked(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self,"Load Data File", "","Text Files (*.txt);;All Files (*)", options=options)
        if fileName:
            self.log(f"Loading data from {fileName}")
            try:
                with open(fileName, 'r', encoding='utf-8') as f:
                    data = f.read()
                    self.log("Data loaded successfully.")
            except Exception as e:
                self.log(f"Error loading data: {e}", level=logging.ERROR)
                QMessageBox.critical(self, "Error", f"Failed to load data: {e}")
    def on_show_phone_changed(self, state):
        if state == Qt.Checked:
            print("Show phone checkbox checked")
        else:
            print("Show phone checkbox unchecked")
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    main = App()
    sys.exit(app.exec_())
