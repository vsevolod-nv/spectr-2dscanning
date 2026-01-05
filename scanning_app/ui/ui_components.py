from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

class DeviceConnectionWidget(QWidget):
    connect_requested = pyqtSignal(str)
    disconnect_requested = pyqtSignal()

    def __init__(self, device_name: str = "Device", parent=None) -> None:
        super().__init__(parent)
        self.device_name = device_name
        self._connected = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.combo = QComboBox()
        self.combo.addItem(f"Select {self.device_name}...")

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self._on_button_clicked)

        self.status_label = QLabel("Status: Disconnected")
        self.status_label.setStyleSheet("color: #b00020; font-size: 11px;")

        layout.addWidget(self.combo)
        layout.addWidget(self.connect_btn)
        layout.addWidget(self.status_label)

    def _on_button_clicked(self) -> None:
        if self._connected:
            self.disconnect_requested.emit()
            return

        name = self.combo.currentText()
        if "Select" in name:
            return

        self.connect_requested.emit(name)

    def populate_device_list(self, devices: list[str]) -> None:
        self.combo.clear()
        self.combo.addItem(f"Select {self.device_name}...")
        self.combo.addItems(devices)

    def set_connected(self, connected: bool, info: str = "") -> None:
        self._connected = connected

        if connected:
            self.status_label.setText(f"Status: Connected {info}")
            self.status_label.setStyleSheet("color: #2e7d32; font-size: 11px;")
            self.connect_btn.setText("Disconnect")
            self.combo.setEnabled(False)
            return

        self.status_label.setText("Status: Disconnected")
        self.status_label.setStyleSheet("color: #b00020; font-size: 11px;")
        self.connect_btn.setText("Connect")
        self.combo.setEnabled(True)
