from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QScrollArea, QGroupBox,
    QMessageBox, QSplitter, QDoubleSpinBox, QSpinBox
)
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPixmap
import pickle
 
from .camera_view_widget import CameraViewWidget
from .heatmap_preview_widget import HeatmapPreviewWidget
from .spectra_preview_widget import SpectraPreviewWidget
from devices.scan_worker import ScanWorker
from .ui_components import DeviceConnectionCard
 
from devices.motors import DummyMotorController
from devices.spectrometer import Spectrometer
 
from config import (
    WINDOW_TITLE, WINDOW_X, WINDOW_Y, WINDOW_WIDTH, WINDOW_HEIGHT,
    SIDEBAR_WIDTH, DEFAULT_STEP_SIZE_X, DEFAULT_STEP_SIZE_Y,
    DEFAULT_ROI_X, DEFAULT_ROI_Y, DEFAULT_ROI_W, DEFAULT_ROI_H,
    EXPOSURE_MIN, EXPOSURE_MAX, EXPOSURE_DEFAULT,
    GAIN_MIN, GAIN_MAX, GAIN_DEFAULT,
    MOTOR_XY_RANGE_MIN, MOTOR_XY_RANGE_MAX,
    MOTOR_STEP_RANGE_MIN, MOTOR_STEP_RANGE_MAX,
    ROI_SIZE_MIN, ROI_SIZE_MAX, DEFAULT_SPLITTER_SIZES,
    PICKLE_FILENAME
)
 
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.setGeometry(WINDOW_X, WINDOW_Y, WINDOW_WIDTH, WINDOW_HEIGHT)
 
        self.motor_controller = DummyMotorController()
        self.spectrometer = Spectrometer()
        
        self.camera_widget = CameraViewWidget()
        self.heatmap_widget = HeatmapPreviewWidget()
        self.spectra_widget = SpectraPreviewWidget()

        self.scan_in_progress = False
        self.worker = None
 
        self.setup_ui()
 
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        sidebar = self.create_sidebar()
        main_layout.addWidget(sidebar, 1)
 
        content_splitter = QSplitter(Qt.Orientation.Vertical)
        
        top_splitter = QSplitter(Qt.Orientation.Horizontal)
        top_splitter.addWidget(self.camera_widget)
        top_splitter.addWidget(self.heatmap_widget)
        top_splitter.setSizes(DEFAULT_SPLITTER_SIZES.get("top", [500, 500]))
 
        content_splitter.addWidget(top_splitter)
        content_splitter.addWidget(self.spectra_widget)
        content_splitter.setSizes(DEFAULT_SPLITTER_SIZES.get("main", [600, 200]))
 
        main_layout.addWidget(content_splitter, 3)
        central_widget.setLayout(main_layout)
 
    def create_sidebar(self):
        sidebar = QScrollArea()
        sidebar.setFixedWidth(SIDEBAR_WIDTH)
        sidebar.setWidgetResizable(True)
        
        sidebar_content = QWidget()
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_layout.setSpacing(15)
 
        self.cam_conn_card = DeviceConnectionCard(
            "Camera Connection", 
            self.camera_widget.camera, 
            self.camera_widget.camera.list_cameras
        )

        self.spec_conn_card = DeviceConnectionCard(
            "Spectrometer Connection",
            self.spectrometer,
            lambda: ["Spectrometer 1 (USB)", "Spectrometer 2 (Mock)"] # Mocking list logic
        )

        self.motor_conn_card = DeviceConnectionCard(
            "Motor Connection",
            self.motor_controller,
            lambda: ["COM1", "COM3", "Dummy Controller"] # Mocking list logic
        )
 
        sidebar_layout.addWidget(self.cam_conn_card)
        sidebar_layout.addWidget(self.spec_conn_card)
        sidebar_layout.addWidget(self.motor_conn_card)

        sidebar_layout.addWidget(self._create_camera_control_group())
        sidebar_layout.addWidget(self._create_motor_step_group())
        sidebar_layout.addWidget(self._create_roi_adjust_group())
        sidebar_layout.addWidget(self._create_raman_settings_group())
        sidebar_layout.addWidget(self._create_scan_controls_group())
        
        sidebar_layout.addStretch()
        sidebar_content.setLayout(sidebar_layout)
        sidebar.setWidget(sidebar_content)
        return sidebar
 
    def _create_camera_control_group(self):
        group = QGroupBox("Camera Settings")
        layout = QVBoxLayout()
 
        expo_layout = QHBoxLayout()
        expo_layout.addWidget(QLabel("Exposure (µs):"))
        self.expo_spinbox = QSpinBox()
        self.expo_spinbox.setRange(EXPOSURE_MIN, EXPOSURE_MAX)
        self.expo_spinbox.setValue(EXPOSURE_DEFAULT)
        expo_layout.addWidget(self.expo_spinbox)
        layout.addLayout(expo_layout)

        gain_layout = QHBoxLayout()
        gain_layout.addWidget(QLabel("Analog Gain:"))
        self.gain_spinbox = QSpinBox()
        self.gain_spinbox.setRange(GAIN_MIN, GAIN_MAX)
        self.gain_spinbox.setValue(GAIN_DEFAULT)
        gain_layout.addWidget(self.gain_spinbox)
        layout.addLayout(gain_layout)

        apply_btn = QPushButton("Apply Settings")
        capture_btn = QPushButton("Capture Image")
        
        apply_btn.clicked.connect(self.apply_camera_settings)
        capture_btn.clicked.connect(self.capture_camera_image)
 
        layout.addWidget(apply_btn)
        layout.addWidget(capture_btn)
        group.setLayout(layout)
        return group
 
    def _create_motor_step_group(self):
        group = QGroupBox("Scan Step Size")
        layout = QVBoxLayout()
 
        for label, default_val in [("X Step (μm):", DEFAULT_STEP_SIZE_X), ("Y Step (μm):", DEFAULT_STEP_SIZE_Y)]:
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            spin = QDoubleSpinBox()
            spin.setRange(MOTOR_STEP_RANGE_MIN, MOTOR_STEP_RANGE_MAX)
            spin.setValue(default_val)
            spin.setSingleStep(0.1)
            row.addWidget(spin)
            layout.addLayout(row)
            
            if "X" in label: self.x_step_spinbox = spin
            else: self.y_step_spinbox = spin
 
        group.setLayout(layout)
        return group
 
    def _create_roi_adjust_group(self):
        group = QGroupBox("ROI Adjustment")
        layout = QVBoxLayout()

        pos_layout = QHBoxLayout()
        pos_layout.addWidget(QLabel("X:"))
        self.roi_x_spinbox = QDoubleSpinBox()
        self.roi_x_spinbox.setRange(MOTOR_XY_RANGE_MIN, MOTOR_XY_RANGE_MAX)
        self.roi_x_spinbox.setValue(DEFAULT_ROI_X)
        pos_layout.addWidget(self.roi_x_spinbox)
 
        pos_layout.addWidget(QLabel("Y:"))
        self.roi_y_spinbox = QDoubleSpinBox()
        self.roi_y_spinbox.setRange(MOTOR_XY_RANGE_MIN, MOTOR_XY_RANGE_MAX)
        self.roi_y_spinbox.setValue(DEFAULT_ROI_Y)
        pos_layout.addWidget(self.roi_y_spinbox)
        layout.addLayout(pos_layout)
 
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("W:"))
        self.roi_w_spinbox = QDoubleSpinBox()
        self.roi_w_spinbox.setRange(ROI_SIZE_MIN, ROI_SIZE_MAX)
        self.roi_w_spinbox.setValue(DEFAULT_ROI_W)
        size_layout.addWidget(self.roi_w_spinbox)
 
        size_layout.addWidget(QLabel("H:"))
        self.roi_h_spinbox = QDoubleSpinBox()
        size_layout.addWidget(self.roi_h_spinbox)
        self.roi_h_spinbox.setRange(ROI_SIZE_MIN, ROI_SIZE_MAX)
        self.roi_h_spinbox.setValue(DEFAULT_ROI_H)
        layout.addLayout(size_layout)
 
        self.roi_info_label = QLabel("ROI: Default")
        layout.addWidget(self.roi_info_label)
 
        apply_roi_button = QPushButton("Update ROI on Image")
        apply_roi_button.clicked.connect(self.apply_roi_changes)
        layout.addWidget(apply_roi_button)
 
        group.setLayout(layout)
        return group
    
    def _create_raman_settings_group(self):
        group = QGroupBox("Spectra Settings")
        layout = QVBoxLayout()
        
        l1 = QHBoxLayout()
        l1.addWidget(QLabel("Min Wavenumber:"))
        self.raman_min_spinbox = QDoubleSpinBox()
        self.raman_min_spinbox.setRange(0, 4000)
        self.raman_min_spinbox.setValue(500)
        l1.addWidget(self.raman_min_spinbox)
        
        l2 = QHBoxLayout()
        l2.addWidget(QLabel("Max Wavenumber:"))
        self.raman_max_spinbox = QDoubleSpinBox()
        self.raman_max_spinbox.setRange(0, 4000)
        self.raman_max_spinbox.setValue(1500)
        l2.addWidget(self.raman_max_spinbox)
        
        layout.addLayout(l1)
        layout.addLayout(l2)
        group.setLayout(layout)
        return group
 
    def _create_scan_controls_group(self):
        group = QGroupBox("Scan Execution")
        layout = QVBoxLayout()
        
        self.scan_status_label = QLabel("Status: Ready")
        self.eta_label = QLabel("")
        
        self.start_scan_button = QPushButton("Start Scan")
        self.start_scan_button.clicked.connect(self.start_scan)
        self.start_scan_button.setStyleSheet("background-color: #d4f7d4; font-weight: bold;")
        
        self.stop_scan_button = QPushButton("STOP")
        self.stop_scan_button.clicked.connect(self.stop_scan)
        self.stop_scan_button.setEnabled(False)
        self.stop_scan_button.setStyleSheet("background-color: #ffcccc;")
        
        layout.addWidget(self.scan_status_label)
        layout.addWidget(self.eta_label)
        layout.addWidget(self.start_scan_button)
        layout.addWidget(self.stop_scan_button)
        
        group.setLayout(layout)
        return group
 
    def apply_camera_settings(self):
        if not self.camera_widget.camera.is_connected:
            QMessageBox.warning(self, "Error", "Camera not connected.")
            return
        
        try:
            self.camera_widget.camera.hcam.put_ExpoTime(self.expo_spinbox.value())
            self.camera_widget.camera.hcam.put_ExpoAGain(self.gain_spinbox.value())
            QMessageBox.information(self, "Done", "Settings applied.")
        except AttributeError:
             QMessageBox.warning(self, "Error", "Camera driver does not support these direct calls.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
 
    def capture_camera_image(self):
        if not self.camera_widget.camera.is_connected:
            QMessageBox.warning(self, "Error", "Camera not connected.")
            return
        try:
            image = self.camera_widget.camera.capture_image()
            pixmap = QPixmap.fromImage(image)
            self.camera_widget.scene.clear()
            self.camera_widget.scene.addPixmap(pixmap)
            self.camera_widget.view.setSceneRect(self.camera_widget.scene.itemsBoundingRect())
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Capture failed: {e}")
 
    def apply_roi_changes(self):
        x = self.roi_x_spinbox.value()
        y = self.roi_y_spinbox.value()
        w = self.roi_w_spinbox.value()
        h = self.roi_h_spinbox.value()
        
        self.camera_widget.clear_roi()
        new_rect = QRectF(x, y, w, h)
        self.camera_widget.add_roi(new_rect)
        self.roi_info_label.setText(f"Manual: X={x}, Y={y}")
 
    def start_scan(self):
        if not self.camera_widget.camera.has_captured():
            QMessageBox.warning(self, "Missing Image", "Capture an image first to reference coordinates.")
            return
 
        if self.scan_in_progress: return
 
        if not (self.camera_widget.camera.is_connected and 
                self.motor_controller.is_connected and 
                self.spectrometer.is_connected):
            QMessageBox.warning(self, "Connection Error", "Please ensure Camera, Motors, and Spectrometer are all connected (Green light).")
            return
 
        roi_rect = self.camera_widget.get_roi_rect()
        if not roi_rect:
            QMessageBox.warning(self, "Missing ROI", "Please select a Region of Interest (ROI) on the camera image.")
            return
 
        scan_params = {
            "step_size_x": self.x_step_spinbox.value(),
            "step_size_y": self.y_step_spinbox.value(),
            "raman_min": self.raman_min_spinbox.value(),
            "raman_max": self.raman_max_spinbox.value(),
        }
        
        self.set_ui_scanning_state(True)
        
        self.worker = ScanWorker(roi_rect, scan_params, self.motor_controller, self.spectrometer)
        self.worker.progress_updated.connect(self.update_scan_progress)
        self.worker.eta_updated.connect(lambda t: self.eta_label.setText(f"ETA: {t}"))
        self.worker.error_occurred.connect(self.on_scan_error)
        self.worker.finished.connect(self.on_scan_finished)
        self.worker.start()
 
    def stop_scan(self):
        if self.worker and self.scan_in_progress:
            self.worker.stop()
            self.scan_status_label.setText("Status: Stopping...")
 
    def set_ui_scanning_state(self, is_scanning):
        self.scan_in_progress = is_scanning
        self.start_scan_button.setEnabled(not is_scanning)
        self.stop_scan_button.setEnabled(is_scanning)
        
        self.motor_conn_card.setEnabled(not is_scanning)
        self.spec_conn_card.setEnabled(not is_scanning)
        
        if is_scanning:
            self.scan_status_label.setText("Status: Scanning...")
        else:
            self.scan_status_label.setText("Status: Idle")
 
    def update_scan_progress(self, progress):
        self.scan_status_label.setText(f"Scanning... {progress}%")
 
    def on_scan_error(self, err_msg):
        self.set_ui_scanning_state(False)
        QMessageBox.critical(self, "Scan Error", err_msg)
 
    def on_scan_finished(self, scan_data):
        self.set_ui_scanning_state(False)
        self.scan_status_label.setText("Status: Completed")
        
        self.heatmap_widget.update_heatmap(scan_data)
        
        try:
            with open(PICKLE_FILENAME, "wb") as f:
                pickle.dump(scan_data, f)
            QMessageBox.information(self, "Success", f"Scan saved to {PICKLE_FILENAME}")
        except Exception as e:
            QMessageBox.warning(self, "Save Error", f"Could not save data: {e}")