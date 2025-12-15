from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QScrollArea, QGroupBox,
    QMessageBox, QSplitter, QDoubleSpinBox, QSpinBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QPen, QBrush
import pickle
import numpy as np
import time
from .camera_view_widget import CameraViewWidget
from .scan_setup_widget import ScanSetupWidget
from .heatmap_preview_widget import HeatmapPreviewWidget
from .spectra_preview_widget import SpectraPreviewWidget
from devices.motors import DummyMotorController
from devices.spectrometer import Spectrometer
from config import WINDOW_WIDTH, WINDOW_HEIGHT, SIDEBAR_WIDTH


class ScanWorker(QThread):
    """Background worker for scanning"""
    progress_updated = pyqtSignal(int)
    finished = pyqtSignal(list)
    eta_updated = pyqtSignal(str)
    
    def __init__(self, roi_rect, scan_params, motor_controller, spectrometer):
        super().__init__()
        self.roi_rect = roi_rect
        self.scan_params = scan_params
        self.motor_controller = motor_controller
        self.spectrometer = spectrometer
        self._is_stopped = False 
    
    def stop(self):
        """Stop the scan"""
        self._is_stopped = True
    
    def run(self):
        x_start = self.roi_rect.left()
        x_end = self.roi_rect.right()
        y_start = self.roi_rect.top()
        y_end = self.roi_rect.bottom()
        
        step_x = self.scan_params['step_size_x']
        step_y = self.scan_params['step_size_y']
        
        x_points = np.arange(x_start, x_end, step_x)
        y_points = np.arange(y_start, y_end, step_y)
        
        total_points = len(x_points) * len(y_points)
        results = []
        
        start_time = time.time()
        
        for i, y in enumerate(y_points):
            if self._is_stopped:
                break
            for j, x in enumerate(x_points):
                if self._is_stopped:
                    break
                
                self.motor_controller.move_to(x, y)
                
                spectrum = self.spectrometer.capture_spectrum()
                
                raman_min = self.scan_params['raman_min']
                raman_max = self.scan_params['raman_max']

                spectrum_len = len(spectrum)
                min_idx = int((raman_min / 4000) * spectrum_len)
                max_idx = int((raman_max / 4000) * spectrum_len)
                min_idx = max(0, min_idx)
                max_idx = min(spectrum_len, max_idx)
                
                integrated_intensity = np.sum(spectrum[min_idx:max_idx])
                
                results.append((x, y, integrated_intensity))

                elapsed = time.time() - start_time
                processed = i * len(x_points) + j + 1
                remaining = total_points - processed
                eta_seconds = (elapsed / processed) * remaining if processed > 0 else 0
                eta_str = f"{eta_seconds//3600:02.0f}:{(eta_seconds%3600)//60:02.0f}:{eta_seconds%60:02.0f}"
                self.eta_updated.emit(eta_str)

                progress = int((processed / total_points) * 100)
                self.progress_updated.emit(progress)
        
        self.finished.emit(results)


class MainWindow(QMainWindow):
    """Main application window with sidebar and split layout"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Microscope Control System")
        self.setGeometry(100, 100, WINDOW_WIDTH, WINDOW_HEIGHT)

        self.motor_controller = DummyMotorController()
        self.spectrometer = Spectrometer()
        self.devices = [self.motor_controller, self.spectrometer]

        self.camera_widget = CameraViewWidget()
        self.scan_setup_widget = ScanSetupWidget()
        self.heatmap_widget = HeatmapPreviewWidget()
        self.spectra_widget = SpectraPreviewWidget()

        self.scan_in_progress = False
        self.worker = None

        self.scan_setup_widget.start_scan_requested.connect(self.start_scan)

        self.setup_ui()
        
        self.camera_widget.capture_button.clicked.connect(self.setup_roi_interaction)
        
        for device in self.devices:
            device.connect()
    
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
        top_splitter.setSizes([WINDOW_WIDTH // 3, WINDOW_WIDTH // 3])

        content_splitter.addWidget(top_splitter)
        content_splitter.addWidget(self.spectra_widget)
        content_splitter.setSizes([WINDOW_HEIGHT // 2, WINDOW_HEIGHT // 2])
        
        main_layout.addWidget(content_splitter, 3)
        
        central_widget.setLayout(main_layout)
    
    def create_sidebar(self):
        """Create the sidebar with settings"""
        sidebar = QScrollArea()
        sidebar.setFixedWidth(SIDEBAR_WIDTH)
        sidebar.setWidgetResizable(True)
        
        sidebar_content = QWidget()
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        
        connection_group = QGroupBox("Connections")
        connection_layout = QVBoxLayout()
        self.connection_status_label = QLabel("All devices connected")
        self.connection_status_label.setStyleSheet("color: green;")
        connection_layout.addWidget(self.connection_status_label)
        connection_group.setLayout(connection_layout)

        roi_group = QGroupBox("ROI Selection")
        roi_layout = QVBoxLayout()
        self.roi_info_label = QLabel("No ROI selected")
        self.roi_info_label.setWordWrap(True)
        roi_layout.addWidget(self.roi_info_label)
        roi_group.setLayout(roi_layout)

        motor_step_group = QGroupBox("Motor Step Settings")
        motor_step_layout = QVBoxLayout()

        x_step_layout = QHBoxLayout()
        x_step_layout.addWidget(QLabel("X Step Size (μm):"))
        self.x_step_spinbox = QDoubleSpinBox()
        self.x_step_spinbox.setRange(0.1, 100.0)
        self.x_step_spinbox.setValue(1.0)
        self.x_step_spinbox.setSingleStep(0.1)
        x_step_layout.addWidget(self.x_step_spinbox)
        motor_step_layout.addLayout(x_step_layout)
    
        y_step_layout = QHBoxLayout()
        y_step_layout.addWidget(QLabel("Y Step Size (μm):"))
        self.y_step_spinbox = QDoubleSpinBox()
        self.y_step_spinbox.setRange(0.1, 100.0)
        self.y_step_spinbox.setValue(1.0)
        self.y_step_spinbox.setSingleStep(0.1)
        y_step_layout.addWidget(self.y_step_spinbox)
        motor_step_layout.addLayout(y_step_layout)
        
        motor_step_group.setLayout(motor_step_layout)
        
        roi_adjust_group = QGroupBox("ROI Adjustment")
        roi_adjust_layout = QVBoxLayout()

        roi_pos_layout = QHBoxLayout()
        roi_pos_layout.addWidget(QLabel("X:"))
        self.roi_x_spinbox = QDoubleSpinBox()
        self.roi_x_spinbox.setRange(-1000, 1000)
        self.roi_x_spinbox.setValue(0.0)
        self.roi_x_spinbox.setSingleStep(1.0)
        roi_pos_layout.addWidget(self.roi_x_spinbox)
        
        roi_pos_layout.addWidget(QLabel("Y:"))
        self.roi_y_spinbox = QDoubleSpinBox()
        self.roi_y_spinbox.setRange(-1000, 1000)
        self.roi_y_spinbox.setValue(0.0)
        self.roi_y_spinbox.setSingleStep(1.0)
        roi_pos_layout.addWidget(self.roi_y_spinbox)
        roi_adjust_layout.addLayout(roi_pos_layout)
        
        roi_size_layout = QHBoxLayout()
        roi_size_layout.addWidget(QLabel("W:"))
        self.roi_w_spinbox = QDoubleSpinBox()
        self.roi_w_spinbox.setRange(1, 2000)
        self.roi_w_spinbox.setValue(100.0)
        self.roi_w_spinbox.setSingleStep(1.0)
        roi_size_layout.addWidget(self.roi_w_spinbox)
        
        roi_size_layout.addWidget(QLabel("H:"))
        self.roi_h_spinbox = QDoubleSpinBox()
        self.roi_h_spinbox.setRange(1, 2000)
        self.roi_h_spinbox.setValue(100.0)
        self.roi_h_spinbox.setSingleStep(1.0)
        roi_size_layout.addWidget(self.roi_h_spinbox)
        roi_adjust_layout.addLayout(roi_size_layout)
        
        self.apply_roi_button = QPushButton("Apply ROI Changes")
        self.apply_roi_button.clicked.connect(self.apply_roi_changes)
        roi_adjust_layout.addWidget(self.apply_roi_button)
        
        roi_adjust_group.setLayout(roi_adjust_layout)

        scan_group = QGroupBox("Scan Status")
        scan_layout = QVBoxLayout()
        self.scan_status_label = QLabel("Ready")
        scan_layout.addWidget(self.scan_status_label)
        self.eta_label = QLabel("ETA: --:--:--") 
        self.eta_label.setVisible(False)
        scan_layout.addWidget(self.eta_label)
        scan_group.setLayout(scan_layout)
        
        scan_controls_group = QGroupBox("Scan Controls")
        scan_controls_layout = QVBoxLayout()
        self.start_scan_button = QPushButton("Start Scan")
        self.start_scan_button.clicked.connect(self.start_scan)
        scan_controls_layout.addWidget(self.start_scan_button)
        self.stop_scan_button = QPushButton("Stop Scan")
        self.stop_scan_button.clicked.connect(self.stop_scan)
        self.stop_scan_button.setEnabled(False)
        scan_controls_layout.addWidget(self.stop_scan_button)
        scan_controls_group.setLayout(scan_controls_layout)
        
        sidebar_layout.addWidget(connection_group)
        sidebar_layout.addWidget(roi_group)
        sidebar_layout.addWidget(motor_step_group)
        sidebar_layout.addWidget(roi_adjust_group)
        sidebar_layout.addWidget(scan_group)
        sidebar_layout.addWidget(scan_controls_group)
        sidebar_layout.addStretch()
        
        sidebar_content.setLayout(sidebar_layout)
        sidebar.setWidget(sidebar_content)
        
        return sidebar
    
    def setup_roi_interaction(self):
        """Set up ROI drawing interaction - now handled in camera widget"""
        pass 
    
    def apply_roi_changes(self):
        """Apply manual ROI adjustments"""
        current_roi = self.camera_widget.get_roi_rect()
        if current_roi:
            x = self.roi_x_spinbox.value()
            y = self.roi_y_spinbox.value()
            w = self.roi_w_spinbox.value()
            h = self.roi_h_spinbox.value()
            
            self.camera_widget.clear_roi()
            from PyQt6.QtCore import QRectF
            new_rect = QRectF(x, y, w, h)
            self.camera_widget.add_roi(new_rect)

            self.roi_info_label.setText(f"Manual ROI: X={x:.2f}, Y={y:.2f}, W={w:.2f}, H={h:.2f}")
    
    def start_scan(self):
        """Start scanning process"""
        if self.scan_in_progress:
            print("Scan already in progress!")
            return
        
        roi_rect = self.camera_widget.get_roi_rect()
        if not roi_rect:
            print("No ROI selected!")
            return
        
        all_connected = all(device.is_connected for device in self.devices)
        if not all_connected:
            print("Not all devices connected!")
            return
        
        scan_params = {
            'step_size_x': self.x_step_spinbox.value(),
            'step_size_y': self.y_step_spinbox.value(),
            'raman_min': self.scan_setup_widget.raman_min_spinbox.value(),
            'raman_max': self.scan_setup_widget.raman_max_spinbox.value()
        }
        
        self.start_scan_button.setEnabled(False)
        self.stop_scan_button.setEnabled(True)
        self.scan_in_progress = True

        self.eta_label.setVisible(True)

        self.scan_status_label.setText("Scanning...")
        self.eta_label.setText("ETA: Calculating...")

        self.worker = ScanWorker(
            roi_rect, scan_params, self.motor_controller, self.spectrometer
        )
        self.worker.progress_updated.connect(self.update_scan_progress)
        self.worker.eta_updated.connect(self.update_eta)
        self.worker.finished.connect(self.on_scan_finished)
        self.worker.start()
    
    def stop_scan(self):
        """Stop the current scan"""
        if self.scan_in_progress and self.worker:
            self.worker.stop()
            self.worker.wait()
            self.scan_in_progress = False

            self.start_scan_button.setEnabled(True)
            self.stop_scan_button.setEnabled(False)
            self.scan_status_label.setText("Scan stopped")
            self.eta_label.setVisible(False)
    
    def update_scan_progress(self, progress):
        """Update scan progress"""
        self.scan_status_label.setText(f"Scanning... {progress}%")
    
    def update_eta(self, eta_str):
        """Update estimated time of arrival"""
        self.eta_label.setText(f"ETA: {eta_str}")
    
    def on_scan_finished(self, scan_data):
        """Handle scan completion"""
        if self.worker:
            self.worker = None
        
        self.start_scan_button.setEnabled(True)
        self.stop_scan_button.setEnabled(False)
        self.scan_in_progress = False
        
        self.scan_status_label.setText("Scan completed!")
        
        self.eta_label.setVisible(False)

        self.heatmap_widget.update_heatmap(scan_data)
        
        with open('scan_data.pkl', 'wb') as f:
            pickle.dump(scan_data, f)
        
        print(f"Scan completed! Data saved to scan_data.pkl ({len(scan_data)} points)")