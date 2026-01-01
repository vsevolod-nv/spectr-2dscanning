# main_window.py
from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QSplitter, QMessageBox
from PyQt6.QtCore import Qt, QRectF
import pickle
from loguru import logger

from .sidebar import SidebarWidget
from .camera_view_widget import CameraViewWidget
from .scan_setup_widget import ScanSetupWidget
from .heatmap_preview_widget import HeatmapPreviewWidget
from .spectra_preview_widget import SpectraPreviewWidget
from devices.scan_worker import ScanWorker
from devices import DummyMotorController, Spectrometer, DummyCamera
from config import (
    WINDOW_TITLE,
    WINDOW_X,
    WINDOW_Y,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    DEFAULT_SPLITTER_SIZES,
    PICKLE_FILENAME,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.setGeometry(WINDOW_X, WINDOW_Y, WINDOW_WIDTH, WINDOW_HEIGHT)

        self.motor_controller = DummyMotorController()
        self.spectrometer = Spectrometer()
        self.camera = DummyCamera()

        self.scan_in_progress = False
        self.worker = None

        self.init_ui()
        self.connect_devices()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.sidebar = SidebarWidget()
        main_layout.addWidget(self.sidebar)

        self.camera_widget = CameraViewWidget()
        self.camera_widget.camera = self.camera
        self.heatmap_widget = HeatmapPreviewWidget()
        self.spectra_widget = SpectraPreviewWidget()
        self.scan_setup_widget = ScanSetupWidget()

        top_splitter = QSplitter(Qt.Orientation.Horizontal)
        top_splitter.addWidget(self.camera_widget)
        top_splitter.addWidget(self.heatmap_widget)
        top_splitter.setSizes(DEFAULT_SPLITTER_SIZES.get("top", [500, 500]))

        content_splitter = QSplitter(Qt.Orientation.Vertical)
        content_splitter.addWidget(top_splitter)
        content_splitter.addWidget(self.spectra_widget)
        content_splitter.setSizes(DEFAULT_SPLITTER_SIZES.get("main", [600, 200]))

        main_layout.addWidget(content_splitter)

        self._connect_sidebar_signals()
        self._connect_widget_signals()

    def _connect_sidebar_signals(self):
        s = self.sidebar
        s.connect_camera_requested.connect(self.connect_specific_camera)
        s.refresh_camera_list_requested.connect(self.refresh_camera_list)
        s.connect_spectrometer_requested.connect(self.connect_spectrometer)
        s.refresh_spectrometer_list_requested.connect(self.refresh_spectrometer_list)
        s.connect_motors_requested.connect(self.connect_motors)
        s.refresh_motors_list_requested.connect(self.refresh_motors_list)

        s.apply_camera_settings_requested.connect(self.apply_camera_settings)
        s.capture_image_requested.connect(self.capture_image)
        s.apply_manual_roi_requested.connect(self.apply_manual_roi)
        s.start_scan_requested.connect(self.start_scan)
        s.stop_scan_requested.connect(self.stop_scan)

        s.camera_connection_status_changed.connect(
            self.on_camera_connection_status_changed
        )
        s.spectrometer_connection_status_changed.connect(
            self.on_spectrometer_connection_status_changed
        )
        s.motors_connection_status_changed.connect(
            self.on_motors_connection_status_changed
        )

    def _connect_widget_signals(self):
        self.camera_widget.roi_changed.connect(self.on_visual_roi_changed)

    def connect_devices(self):
        self.update_status_indicators()
        self.refresh_camera_list()
        self.refresh_spectrometer_list()
        self.refresh_motors_list()

    def update_status_indicators(self):
        self.sidebar.cam_status.set_status(self.camera.is_connected)
        self.sidebar.spec_status.set_status(self.spectrometer.is_connected)
        self.sidebar.motor_status.set_status(self.motor_controller.is_connected)

        self.sidebar.update_camera_status_widget(self.camera.is_connected)
        self.sidebar.update_spectrometer_status_widget(self.spectrometer.is_connected)
        self.sidebar.update_motors_status_widget(self.motor_controller.is_connected)

    def refresh_camera_list(self):
        camera_list = self.camera.list_cameras()
        self.sidebar.populate_camera_list(camera_list)
        logger.info(f"Refreshed camera list: {camera_list}")

    def refresh_spectrometer_list(self):
        self.sidebar.populate_spectrometer_list(["Dummy Spectrometer"])

    def refresh_motors_list(self):
        self.sidebar.populate_motors_list(["Dummy Motor Controller"])

    def connect_specific_camera(self, name):
        success = self.camera.connect()
        if success:
            QMessageBox.information(self, "Success", f"Connected to {name}")
        else:
            QMessageBox.warning(self, "Error", f"Failed to connect to {name}")
        self.sidebar.update_camera_status_widget(self.camera.is_connected)
        self.sidebar.cam_status.set_status(self.camera.is_connected)

    def connect_spectrometer(self, name):
        success = self.spectrometer.connect()
        if success:
            logger.info(f"Connected to Spectrometer: {name}")
        else:
            QMessageBox.warning(self, "Error", f"Failed to connect to {name}")
        self.sidebar.update_spectrometer_status_widget(self.spectrometer.is_connected)
        self.sidebar.spec_status.set_status(self.spectrometer.is_connected)

    def connect_motors(self, name):
        success = self.motor_controller.connect()
        if success:
            logger.info(f"Connected to Motors: {name}")
        else:
            QMessageBox.warning(self, "Error", f"Failed to connect to {name}")
        self.sidebar.update_motors_status_widget(self.motor_controller.is_connected)
        self.sidebar.motor_status.set_status(self.motor_controller.is_connected)

    def apply_camera_settings(self):
        if not self.camera.is_connected:
            return
        expo = self.sidebar.get_exposure()
        gain = self.sidebar.get_gain()
        try:
            self.camera.hcam.put_ExpoTime(expo)
            self.camera.hcam.put_ExpoAGain(gain)
        except Exception as e:
            logger.error(f"Cam setting error: {e}")

    def capture_image(self):
        if not self.camera.is_connected:
            QMessageBox.warning(self, "Error", "Camera not connected")
            return
        try:
            img = self.camera.capture_image()
            logger.info(f"Got image from camera, size: {img.size()}")
            self.camera_widget.set_image(img)
            logger.info("Set image in camera_widget successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Capture Error", f"An error occurred: {str(e)}")
            logger.error(f"Capture Error: {e}")

    def apply_manual_roi(self):
        x, y, w, h = self.sidebar.get_roi_values()
        self.camera_widget.add_roi(QRectF(x, y, w, h))

    def on_visual_roi_changed(self, rect: QRectF):
        self.sidebar.set_roi_values(rect.x(), rect.y(), rect.width(), rect.height())
        self.sidebar.roi_info_lbl.setText(
            f"Selection: X={rect.x():.1f}, Y={rect.y():.1f}"
        )

    def start_scan(self):
        if not self.camera_widget.has_captured():
            QMessageBox.warning(self, "Wait", "Please capture an image first.")
            return
        roi = self.camera_widget.get_roi_rect()
        if not roi:
            QMessageBox.warning(self, "Wait", "Please select an ROI on the image.")
            return
        if not (self.motor_controller.is_connected and self.spectrometer.is_connected):
            QMessageBox.warning(
                self, "Hardware", "Motors or Spectrometer not connected."
            )
            return

        step_x, step_y = self.sidebar.get_scan_steps()
        raman_min = self.scan_setup_widget.raman_min_spinbox.value()
        raman_max = self.scan_setup_widget.raman_max_spinbox.value()
        scan_params = {
            "step_size_x": step_x,
            "step_size_y": step_y,
            "raman_min": raman_min,
            "raman_max": raman_max,
        }

        self.sidebar.set_scan_state(True)
        self.sidebar.status_lbl.setText("Status: Scanning...")
        self.scan_in_progress = True

        self.worker = ScanWorker(
            roi, scan_params, self.motor_controller, self.spectrometer
        )
        self.worker.progress_updated.connect(self.on_scan_progress)
        self.worker.eta_updated.connect(self.sidebar.eta_lbl.setText)
        self.worker.finished.connect(self.on_scan_finished)
        self.worker.start()

    def stop_scan(self):
        if self.worker:
            self.worker.stop()
            self.sidebar.status_lbl.setText("Status: Stopping...")

    def on_scan_progress(self, val):
        self.sidebar.status_lbl.setText(f"Scanning... {val}%")

    def on_scan_finished(self, results):
        self.scan_in_progress = False
        self.sidebar.set_scan_state(False)
        self.sidebar.status_lbl.setText("Status: Completed")
        self.heatmap_widget.update_heatmap(results)
        if results:
            try:
                with open(PICKLE_FILENAME, "wb") as f:
                    pickle.dump(results, f)
                logger.info("Data saved.")
            except Exception as e:
                QMessageBox.warning(self, "Save Error", str(e))

    def on_camera_connection_status_changed(self, is_connected):
        self.sidebar.capture_btn.setEnabled(is_connected)
        logger.info(
            f"Camera connection status changed to: {is_connected}. "
            f"Capture button enabled: {is_connected}"
        )

    def on_spectrometer_connection_status_changed(self, is_connected):
        logger.info(f"Spectrometer connection status changed to: {is_connected}")

    def on_motors_connection_status_changed(self, is_connected):
        logger.info(f"Motors connection status changed to: {is_connected}")
