from loguru import logger
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QColor, QPen, QPainter


class StatusIndicator(QWidget):
    def __init__(self, label_text="Status"):
        super().__init__()
        self.label_text = label_text
        self._status = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.indicator_symbol = QFrame()
        self.indicator_symbol.setFixedSize(12, 12)
        self.indicator_symbol.setStyleSheet(self._get_indicator_style(False))

        self.indicator_label = QLabel(self.label_text)

        layout.addWidget(self.indicator_symbol)
        layout.addWidget(self.indicator_label)
        layout.addStretch()

    def _get_indicator_style(self, is_on):
        color = "#4CAF50" if is_on else "#F44336"
        return f"border-radius: 6px; background-color: {color};"

    def set_status(self, is_on: bool):
        self._status = is_on
        self.indicator_symbol.setStyleSheet(self._get_indicator_style(is_on))

    def get_status(self):
        return self._status


class DeviceConnectionWidget(QWidget):
    connect_requested = pyqtSignal(str)
    refresh_requested = pyqtSignal()

    def __init__(self, device_name="Device", parent=None):
        super().__init__(parent)
        self.device_name = device_name
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        sel_layout = QHBoxLayout()
        self.combo = QComboBox()
        self.combo.addItem(f"Select {self.device_name}...")
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setFixedWidth(60)
        self.refresh_btn.clicked.connect(self.refresh_requested.emit)
        sel_layout.addWidget(self.combo)
        sel_layout.addWidget(self.refresh_btn)

        btn_layout = QHBoxLayout()
        self.connect_btn = QPushButton("Connect")
        self.status_label = QLabel("Status: Disconnected")
        self.status_label.setStyleSheet("color: red")
        self.connect_btn.clicked.connect(self._on_connect_clicked)
        btn_layout.addWidget(self.connect_btn)

        layout.addLayout(sel_layout)
        layout.addLayout(btn_layout)
        layout.addWidget(self.status_label)

    def _on_connect_clicked(self):
        target = self.combo.currentText()
        if "Select" in target:
            logger.debug("No device selected; ignoring connection request.")
            return
        logger.info(f"Connection requested for device: {target}")
        self.connect_requested.emit(target)

    def update_status(self, is_connected: bool, extra_info: str = ""):
        if is_connected:
            self.status_label.setText(f"Status: Connected {extra_info}")
            self.status_label.setStyleSheet("color: green")
            self.connect_btn.setText("Disconnect")
            logger.info(f"{self.device_name} connected. {extra_info}")
        else:
            self.status_label.setText(f"Status: Disconnected {extra_info}")
            self.status_label.setStyleSheet("color: red")
            self.connect_btn.setText("Connect")
            logger.warning(f"{self.device_name} disconnected. {extra_info}")

    def populate_device_list(self, device_list: list):
        self.combo.clear()
        self.combo.addItem(f"Select {self.device_name}...")
        self.combo.addItems(device_list)
        logger.debug(f"Populated {self.device_name} list with {len(device_list)} devices.")

    def get_selected_device(self):
        return self.combo.currentText()

    def set_connect_button_enabled(self, enabled: bool):
        self.connect_btn.setEnabled(enabled)

    def set_refresh_button_enabled(self, enabled: bool):
        self.refresh_btn.setEnabled(enabled)