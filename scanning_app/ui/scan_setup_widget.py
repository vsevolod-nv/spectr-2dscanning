from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QDoubleSpinBox,
    QPushButton, QGroupBox
)
from PyQt6.QtCore import pyqtSignal
from config import (
    BUTTON_HEIGHT,
    DOUBLE_SPINBOX_WIDTH,
    DEFAULT_STEP_SIZE_X,
    DEFAULT_STEP_SIZE_Y,
    RAMAN_MIN_DEFAULT,
    RAMAN_MAX_DEFAULT,
    RAMAN_MIN_LIMIT,
    RAMAN_MAX_LIMIT,
)


class ScanSetupWidget(QWidget):
    start_scan_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        grid_group = QGroupBox("Grid Setup")
        grid_layout = QFormLayout()

        self.step_size_x_spinbox = QDoubleSpinBox()
        self.step_size_x_spinbox.setRange(0.1, 100.0)
        self.step_size_x_spinbox.setValue(DEFAULT_STEP_SIZE_X)
        self.step_size_x_spinbox.setSuffix(" μm")
        self.step_size_x_spinbox.setFixedWidth(DOUBLE_SPINBOX_WIDTH)

        self.step_size_y_spinbox = QDoubleSpinBox()
        self.step_size_y_spinbox.setRange(0.1, 100.0)
        self.step_size_y_spinbox.setValue(DEFAULT_STEP_SIZE_Y)
        self.step_size_y_spinbox.setSuffix(" μm")
        self.step_size_y_spinbox.setFixedWidth(DOUBLE_SPINBOX_WIDTH)

        grid_layout.addRow("X Step Size:", self.step_size_x_spinbox)
        grid_layout.addRow("Y Step Size:", self.step_size_y_spinbox)
        grid_group.setLayout(grid_layout)

        raman_group = QGroupBox("Raman Shift Range")
        raman_layout = QFormLayout()

        self.raman_min_spinbox = QDoubleSpinBox()
        self.raman_min_spinbox.setRange(RAMAN_MIN_LIMIT, RAMAN_MAX_LIMIT - 1)
        self.raman_min_spinbox.setValue(RAMAN_MIN_DEFAULT)
        self.raman_min_spinbox.setSuffix(" cm⁻¹")
        self.raman_min_spinbox.setFixedWidth(DOUBLE_SPINBOX_WIDTH)

        self.raman_max_spinbox = QDoubleSpinBox()
        self.raman_max_spinbox.setRange(RAMAN_MIN_LIMIT + 1, RAMAN_MAX_LIMIT)
        self.raman_max_spinbox.setValue(RAMAN_MAX_DEFAULT)
        self.raman_max_spinbox.setSuffix(" cm⁻¹")
        self.raman_max_spinbox.setFixedWidth(DOUBLE_SPINBOX_WIDTH)

        raman_layout.addRow("Min:", self.raman_min_spinbox)
        raman_layout.addRow("Max:", self.raman_max_spinbox)
        raman_group.setLayout(raman_layout)

        self.start_scan_button = QPushButton("Start Scan")
        self.start_scan_button.setFixedHeight(BUTTON_HEIGHT)
        self.start_scan_button.clicked.connect(self.start_scan_requested.emit)

        layout.addWidget(grid_group)
        layout.addWidget(raman_group)
        layout.addWidget(self.start_scan_button)
        layout.addStretch()

        self.setLayout(layout)

    def get_scan_parameters(self):
        return {
            "step_size_x": self.step_size_x_spinbox.value(),
            "step_size_y": self.step_size_y_spinbox.value(),
            "raman_min": self.raman_min_spinbox.value(),
            "raman_max": self.raman_max_spinbox.value(),
        }