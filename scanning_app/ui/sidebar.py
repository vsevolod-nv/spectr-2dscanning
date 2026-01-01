from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDoubleSpinBox,
    QGroupBox,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from config import (
    DEFAULT_STEP_SIZE_X,
    DEFAULT_STEP_SIZE_Y,
    EXPOSURE_DEFAULT,
    EXPOSURE_MAX,
    EXPOSURE_MIN,
    GAIN_DEFAULT,
    GAIN_MAX,
    GAIN_MIN,
    RAMAN_MAX_LIMIT,
    RAMAN_MIN_LIMIT,
)
from .ui_components import DeviceConnectionWidget


class SidebarWidget(QScrollArea):
    connect_camera_requested = pyqtSignal(str)
    disconnect_camera_requested = pyqtSignal()

    connect_spectrometer_requested = pyqtSignal(str)
    disconnect_spectrometer_requested = pyqtSignal()

    connect_motors_requested = pyqtSignal(str)
    disconnect_motors_requested = pyqtSignal()

    capture_image_requested = pyqtSignal()
    start_scan_requested = pyqtSignal()
    stop_scan_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setFixedWidth(320)
        self.setWidgetResizable(True)
        self._build_ui()

    def _build_ui(self):
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setSpacing(10)

        layout.addWidget(self._build_connections())
        layout.addWidget(self._build_camera_controls())
        layout.addWidget(self._build_scan_controls())
        layout.addStretch()

        self.setWidget(root)

    def _build_connections(self):
        group = QGroupBox("Devices")
        layout = QVBoxLayout(group)

        self.cam_conn = DeviceConnectionWidget("Camera")
        self.spec_conn = DeviceConnectionWidget("Spectrometer")
        self.motor_conn = DeviceConnectionWidget("Motors")

        self.cam_conn.connect_requested.connect(self.connect_camera_requested)
        self.cam_conn.disconnect_requested.connect(self.disconnect_camera_requested)

        self.spec_conn.connect_requested.connect(self.connect_spectrometer_requested)
        self.spec_conn.disconnect_requested.connect(
            self.disconnect_spectrometer_requested
        )

        self.motor_conn.connect_requested.connect(self.connect_motors_requested)
        self.motor_conn.disconnect_requested.connect(self.disconnect_motors_requested)

        layout.addWidget(self.cam_conn)
        layout.addWidget(self.spec_conn)
        layout.addWidget(self.motor_conn)

        return group

    def _build_camera_controls(self):
        group = QGroupBox("Camera")
        layout = QVBoxLayout(group)

        self.expo_spin = QSpinBox()
        self.expo_spin.setRange(EXPOSURE_MIN, EXPOSURE_MAX)
        self.expo_spin.setValue(EXPOSURE_DEFAULT)

        self.gain_spin = QSpinBox()
        self.gain_spin.setRange(GAIN_MIN, GAIN_MAX)
        self.gain_spin.setValue(GAIN_DEFAULT)

        self.capture_btn = QPushButton("Capture Image")
        self.capture_btn.clicked.connect(self.capture_image_requested.emit)

        layout.addWidget(QLabel("Exposure (µs)"))
        layout.addWidget(self.expo_spin)
        layout.addWidget(QLabel("Gain"))
        layout.addWidget(self.gain_spin)
        layout.addWidget(self.capture_btn)

        return group

    def _build_scan_controls(self):
        group = QGroupBox("Scan")
        layout = QVBoxLayout(group)

        self.step_x = self._spin("Step X (µm)", DEFAULT_STEP_SIZE_X, 0.1)
        self.step_y = self._spin("Step Y (µm)", DEFAULT_STEP_SIZE_Y, 0.1)

        self.raman_min = self._spin(
            "Raman Min",
            RAMAN_MIN_LIMIT,
            step=1.0,
            min_val=RAMAN_MIN_LIMIT,
            max_val=RAMAN_MAX_LIMIT,
        )
        self.raman_max = self._spin(
            "Raman Max",
            RAMAN_MAX_LIMIT,
            step=1.0,
            min_val=RAMAN_MIN_LIMIT,
            max_val=RAMAN_MAX_LIMIT,
        )

        self.status_lbl = QLabel("Idle")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.eta_lbl = QLabel("--:--:--")
        self.eta_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.start_btn = QPushButton("START SCAN")
        self.stop_btn = QPushButton("STOP")
        self.stop_btn.setEnabled(False)

        self.start_btn.clicked.connect(self.start_scan_requested.emit)
        self.stop_btn.clicked.connect(self.stop_scan_requested.emit)

        for widget in (
            self.step_x,
            self.step_y,
            self.raman_min,
            self.raman_max,
            self.status_lbl,
            self.eta_lbl,
            self.start_btn,
            self.stop_btn,
        ):
            layout.addWidget(widget)

        return group

    def _spin(
        self,
        label,
        default,
        step=1.0,
        min_val=None,
        max_val=None,
    ):
        box = QDoubleSpinBox()
        box.setSingleStep(step)
        box.setPrefix(f"{label}: ")

        if min_val is not None and max_val is not None:
            box.setRange(min_val, max_val)

        box.setValue(default)
        return box

    def get_scan_parameters(self):
        return {
            "step_size_x": self.step_x.value(),
            "step_size_y": self.step_y.value(),
            "raman_min": self.raman_min.value(),
            "raman_max": self.raman_max.value(),
        }

    def set_scan_running(self, running: bool):
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
        self.status_lbl.setText("Scanning…" if running else "Idle")

    def set_raman_range(self, rmin, rmax):
        self.raman_min.blockSignals(True)
        self.raman_max.blockSignals(True)

        self.raman_min.setValue(rmin)
        self.raman_max.setValue(rmax)

        self.raman_min.blockSignals(False)
        self.raman_max.blockSignals(False)
