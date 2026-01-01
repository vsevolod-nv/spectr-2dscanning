from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QGroupBox,
    QDoubleSpinBox,
    QSpinBox,
    QScrollArea,
)
from PyQt6.QtCore import pyqtSignal, Qt
from .ui_components import StatusIndicator, DeviceConnectionWidget
from config import (
    EXPOSURE_MIN,
    EXPOSURE_MAX,
    EXPOSURE_DEFAULT,
    GAIN_MIN,
    GAIN_MAX,
    GAIN_DEFAULT,
    MOTOR_STEP_RANGE_MIN,
    MOTOR_STEP_RANGE_MAX,
    DEFAULT_STEP_SIZE_X,
    DEFAULT_STEP_SIZE_Y,
    MOTOR_XY_RANGE_MIN,
    MOTOR_XY_RANGE_MAX,
    ROI_SIZE_MIN,
    ROI_SIZE_MAX,
    DEFAULT_ROI_X,
    DEFAULT_ROI_Y,
    DEFAULT_ROI_W,
    DEFAULT_ROI_H,
)
from loguru import logger


class SidebarWidget(QScrollArea):
    connect_camera_requested = pyqtSignal(str)
    refresh_camera_list_requested = pyqtSignal()
    connect_spectrometer_requested = pyqtSignal(str)
    refresh_spectrometer_list_requested = pyqtSignal()
    connect_motors_requested = pyqtSignal(str)
    refresh_motors_list_requested = pyqtSignal()

    apply_camera_settings_requested = pyqtSignal()
    capture_image_requested = pyqtSignal()
    apply_manual_roi_requested = pyqtSignal()
    start_scan_requested = pyqtSignal()
    stop_scan_requested = pyqtSignal()

    camera_connection_status_changed = pyqtSignal(bool)
    spectrometer_connection_status_changed = pyqtSignal(bool)
    motors_connection_status_changed = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.setFixedWidth(320)
        self.setWidgetResizable(True)
        self.setup_ui()

    def setup_ui(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(10)

        status_group = QGroupBox("System Status")
        status_layout = QVBoxLayout()
        self.cam_status = StatusIndicator("Camera")
        self.spec_status = StatusIndicator("Spectrometer")
        self.motor_status = StatusIndicator("Motors")
        status_layout.addWidget(self.cam_status)
        status_layout.addWidget(self.spec_status)
        status_layout.addWidget(self.motor_status)
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        self.cam_conn_widget = DeviceConnectionWidget("Camera")
        cam_conn_group = QGroupBox("Camera Connection")
        cam_conn_layout = QVBoxLayout(cam_conn_group)
        cam_conn_layout.addWidget(self.cam_conn_widget)
        layout.addWidget(cam_conn_group)

        self.spec_conn_widget = DeviceConnectionWidget("Spectrometer")
        spec_conn_group = QGroupBox("Spectrometer Connection")
        spec_conn_layout = QVBoxLayout(spec_conn_group)
        spec_conn_layout.addWidget(self.spec_conn_widget)
        layout.addWidget(spec_conn_group)

        self.motor_conn_widget = DeviceConnectionWidget("Motors")
        motor_conn_group = QGroupBox("Motors Connection")
        motor_conn_layout = QVBoxLayout(motor_conn_group)
        motor_conn_layout.addWidget(self.motor_conn_widget)
        layout.addWidget(motor_conn_group)

        cam_ctrl_group = QGroupBox("Camera Settings")
        cam_ctrl_layout = QVBoxLayout()
        exp_layout = QHBoxLayout()
        exp_layout.addWidget(QLabel("Exposure (µs):"))
        self.expo_spin = QSpinBox()
        self.expo_spin.setRange(EXPOSURE_MIN, EXPOSURE_MAX)
        self.expo_spin.setValue(EXPOSURE_DEFAULT)
        exp_layout.addWidget(self.expo_spin)
        cam_ctrl_layout.addLayout(exp_layout)
        gain_layout = QHBoxLayout()
        gain_layout.addWidget(QLabel("Gain:"))
        self.gain_spin = QSpinBox()
        self.gain_spin.setRange(GAIN_MIN, GAIN_MAX)
        self.gain_spin.setValue(GAIN_DEFAULT)
        gain_layout.addWidget(self.gain_spin)
        cam_ctrl_layout.addLayout(gain_layout)
        ctrl_btns_layout = QHBoxLayout()
        self.apply_settings_btn = QPushButton("Apply")
        self.capture_btn = QPushButton("Capture")
        self.cam_conn_widget.connect_requested.connect(
            self.connect_camera_requested.emit
        )
        self.cam_conn_widget.refresh_requested.connect(
            self.refresh_camera_list_requested.emit
        )
        self.spec_conn_widget.connect_requested.connect(
            self.connect_spectrometer_requested.emit
        )
        self.spec_conn_widget.refresh_requested.connect(
            self.refresh_spectrometer_list_requested.emit
        )
        self.motor_conn_widget.connect_requested.connect(
            self.connect_motors_requested.emit
        )
        self.motor_conn_widget.refresh_requested.connect(
            self.refresh_motors_list_requested.emit
        )
        self.apply_settings_btn.clicked.connect(
            self.apply_camera_settings_requested.emit
        )
        self.capture_btn.clicked.connect(self.capture_image_requested.emit)
        ctrl_btns_layout.addWidget(self.apply_settings_btn)
        ctrl_btns_layout.addWidget(self.capture_btn)
        cam_ctrl_layout.addLayout(ctrl_btns_layout)
        cam_ctrl_group.setLayout(cam_ctrl_layout)
        layout.addWidget(cam_ctrl_group)

        roi_group = QGroupBox("ROI Adjustment")
        roi_layout = QVBoxLayout()
        row1 = QHBoxLayout()
        self.roi_x = self._create_double_spin(
            "X:", DEFAULT_ROI_X, MOTOR_XY_RANGE_MIN, MOTOR_XY_RANGE_MAX
        )
        self.roi_y = self._create_double_spin(
            "Y:", DEFAULT_ROI_Y, MOTOR_XY_RANGE_MIN, MOTOR_XY_RANGE_MAX
        )
        row1.addLayout(self.roi_x[0])
        row1.addLayout(self.roi_y[0])
        row2 = QHBoxLayout()
        self.roi_w = self._create_double_spin(
            "W:", DEFAULT_ROI_W, ROI_SIZE_MIN, ROI_SIZE_MAX
        )
        self.roi_h = self._create_double_spin(
            "H:", DEFAULT_ROI_H, ROI_SIZE_MIN, ROI_SIZE_MAX
        )
        row2.addLayout(self.roi_w[0])
        row2.addLayout(self.roi_h[0])
        roi_layout.addLayout(row1)
        roi_layout.addLayout(row2)
        self.apply_roi_btn = QPushButton("Update ROI on Image")
        self.apply_roi_btn.clicked.connect(self.apply_manual_roi_requested.emit)
        roi_layout.addWidget(self.apply_roi_btn)
        self.roi_info_lbl = QLabel("Current: None")
        self.roi_info_lbl.setStyleSheet("color: #666; font-size: 10px;")
        roi_layout.addWidget(self.roi_info_lbl)
        roi_group.setLayout(roi_layout)
        layout.addWidget(roi_group)

        scan_set_group = QGroupBox("Scan Step Size")
        scan_set_layout = QVBoxLayout()
        row_step = QHBoxLayout()
        self.step_x = self._create_double_spin(
            "X (µm):",
            DEFAULT_STEP_SIZE_X,
            MOTOR_STEP_RANGE_MIN,
            MOTOR_STEP_RANGE_MAX,
            0.1,
        )
        self.step_y = self._create_double_spin(
            "Y (µm):",
            DEFAULT_STEP_SIZE_Y,
            MOTOR_STEP_RANGE_MIN,
            MOTOR_STEP_RANGE_MAX,
            0.1,
        )
        row_step.addLayout(self.step_x[0])
        row_step.addLayout(self.step_y[0])
        scan_set_layout.addLayout(row_step)
        scan_set_group.setLayout(scan_set_layout)
        layout.addWidget(scan_set_group)

        exec_group = QGroupBox("Scan Control")
        exec_layout = QVBoxLayout()
        self.status_lbl = QLabel("Status: Idle")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setStyleSheet(
            "font-weight: bold; font-size: 12px; margin-bottom: 5px;"
        )
        self.eta_lbl = QLabel("--:--:--")
        self.eta_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.start_btn = QPushButton("START SCAN")
        self.start_btn.setFixedHeight(40)
        self.start_btn.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold;"
        )
        self.start_btn.clicked.connect(self.start_scan_requested.emit)
        self.stop_btn = QPushButton("STOP")
        self.stop_btn.setFixedHeight(30)
        self.stop_btn.setStyleSheet("background-color: #F44336; color: white;")
        self.stop_btn.clicked.connect(self.stop_scan_requested.emit)
        self.stop_btn.setEnabled(False)
        exec_layout.addWidget(self.status_lbl)
        exec_layout.addWidget(self.eta_lbl)
        exec_layout.addWidget(self.start_btn)
        exec_layout.addWidget(self.stop_btn)
        exec_group.setLayout(exec_layout)
        layout.addWidget(exec_group)

        layout.addStretch()
        self.setWidget(container)

    def _create_double_spin(self, label_text, default, vmin, vmax, step=1.0):
        layout = QHBoxLayout()
        lbl = QLabel(label_text)
        spin = QDoubleSpinBox()
        spin.setRange(vmin, vmax)
        spin.setValue(default)
        spin.setSingleStep(step)
        layout.addWidget(lbl)
        layout.addWidget(spin)
        return layout, spin

    def get_roi_values(self):
        return (
            self.roi_x[1].value(),
            self.roi_y[1].value(),
            self.roi_w[1].value(),
            self.roi_h[1].value(),
        )

    def set_roi_values(self, x, y, w, h):
        self.roi_x[1].setValue(x)
        self.roi_y[1].setValue(y)
        self.roi_w[1].setValue(w)
        self.roi_h[1].setValue(h)

    def get_scan_steps(self):
        return self.step_x[1].value(), self.step_y[1].value()

    def get_exposure(self):
        return self.expo_spin.value()

    def get_gain(self):
        return self.gain_spin.value()

    def set_scan_state(self, is_scanning):
        self.start_btn.setEnabled(not is_scanning)
        self.stop_btn.setEnabled(is_scanning)
        self.apply_roi_btn.setEnabled(not is_scanning)
        self.cam_conn_widget.set_connect_button_enabled(not is_scanning)
        self.spec_conn_widget.set_connect_button_enabled(not is_scanning)
        self.motor_conn_widget.set_connect_button_enabled(not is_scanning)
        self.cam_conn_widget.set_refresh_button_enabled(not is_scanning)
        self.spec_conn_widget.set_refresh_button_enabled(not is_scanning)
        self.motor_conn_widget.set_refresh_button_enabled(not is_scanning)

    def update_camera_status_widget(self, is_connected: bool, extra_info: str = ""):
        self.cam_conn_widget.update_status(is_connected, extra_info)
        self.cam_status.set_status(is_connected)
        self.camera_connection_status_changed.emit(is_connected)
        logger.info(
            f"Camera connection status updated: {'Connected' if is_connected else 'Disconnected'}"
        )

    def update_spectrometer_status_widget(
        self, is_connected: bool, extra_info: str = ""
    ):
        self.spec_conn_widget.update_status(is_connected, extra_info)
        self.spec_status.set_status(is_connected)
        self.spectrometer_connection_status_changed.emit(is_connected)
        logger.info(
            f"Spectrometer connection status updated: {'Connected' if is_connected else 'Disconnected'}"
        )

    def update_motors_status_widget(self, is_connected: bool, extra_info: str = ""):
        self.motor_conn_widget.update_status(is_connected, extra_info)
        self.motor_status.set_status(is_connected)
        self.motors_connection_status_changed.emit(is_connected)
        logger.info(
            f"Motors connection status updated: {'Connected' if is_connected else 'Disconnected'}"
        )

    def populate_camera_list(self, camera_list: list):
        self.cam_conn_widget.populate_device_list(camera_list)
        logger.debug(f"Camera list populated with {len(camera_list)} devices")

    def populate_spectrometer_list(self, spec_list: list):
        self.spec_conn_widget.populate_device_list(spec_list)
        logger.debug(f"Spectrometer list populated with {len(spec_list)} devices")

    def populate_motors_list(self, motor_list: list):
        self.motor_conn_widget.populate_device_list(motor_list)
        logger.debug(f"Motors list populated with {len(motor_list)} devices")
