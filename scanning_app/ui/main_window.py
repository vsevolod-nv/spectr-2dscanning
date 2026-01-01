from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QMainWindow, QMessageBox, QSplitter, QWidget

from config import (
    DEFAULT_SPLITTER_SIZES,
    WINDOW_HEIGHT,
    WINDOW_TITLE,
    WINDOW_WIDTH,
    WINDOW_X,
    WINDOW_Y,
)
from controllers.app_controller import AppController
from .camera_view_widget import CameraViewWidget
from .heatmap_preview_widget import HeatmapPreviewWidget
from .sidebar import SidebarWidget
from .spectra_preview_widget import SpectraPreviewWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.setGeometry(WINDOW_X, WINDOW_Y, WINDOW_WIDTH, WINDOW_HEIGHT)

        self.controller = AppController()
        self._heatmap_initialized = False

        self._init_ui()
        self._connect_signals()
        self._populate_device_lists()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self.sidebar = SidebarWidget()
        layout.addWidget(self.sidebar)

        self.camera_widget = CameraViewWidget()
        self.camera_widget.camera = None

        self.heatmap_widget = HeatmapPreviewWidget()
        self.spectra_widget = SpectraPreviewWidget()

        top = QSplitter(Qt.Orientation.Horizontal)
        top.addWidget(self.camera_widget)
        top.addWidget(self.heatmap_widget)
        top.setSizes(DEFAULT_SPLITTER_SIZES["top"])

        main = QSplitter(Qt.Orientation.Vertical)
        main.addWidget(top)
        main.addWidget(self.spectra_widget)
        main.setSizes(DEFAULT_SPLITTER_SIZES["main"])

        layout.addWidget(main)

    def _connect_signals(self):
        s = self.sidebar

        s.connect_camera_requested.connect(self._on_connect_camera)
        s.disconnect_camera_requested.connect(self._on_disconnect_camera)

        s.connect_spectrometer_requested.connect(self._on_connect_spectrometer)
        s.disconnect_spectrometer_requested.connect(self._on_disconnect_spectrometer)

        s.connect_motors_requested.connect(self._on_connect_motors)
        s.disconnect_motors_requested.connect(self._on_disconnect_motors)

        s.capture_image_requested.connect(self._on_capture_image)
        s.start_scan_requested.connect(self._on_start_scan)
        s.stop_scan_requested.connect(self._on_stop_scan)

        s.raman_min.valueChanged.connect(self._on_raman_range_changed)
        s.raman_max.valueChanged.connect(self._on_raman_range_changed)

        self.spectra_widget.raman_range_selected.connect(
            self._on_raman_range_from_spectrum
        )
        self.heatmap_widget.scan_point_selected.connect(self._on_heatmap_point_selected)

    def _on_raman_range_from_spectrum(self, rmin, rmax):
        self.sidebar.set_raman_range(rmin, rmax)
        self.heatmap_widget.set_raman_range(rmin, rmax)

    def _on_raman_range_changed(self):
        rmin = self.sidebar.raman_min.value()
        rmax = self.sidebar.raman_max.value()

        self.spectra_widget.set_raman_range(rmin, rmax)
        self.heatmap_widget.set_raman_range(rmin, rmax)

    def _populate_device_lists(self):
        self.sidebar.cam_conn.populate_device_list(self.controller.list_cameras())
        self.sidebar.spec_conn.populate_device_list(
            self.controller.list_spectrometers()
        )
        self.sidebar.motor_conn.populate_device_list(self.controller.list_motors())

    def _on_connect_camera(self, name):
        self.controller.connect_camera(name)
        self.camera_widget.camera = self.controller.camera
        self.sidebar.cam_conn.set_connected(True)

    def _on_disconnect_camera(self):
        self.controller.disconnect_camera()
        self.camera_widget.camera = None
        self.sidebar.cam_conn.set_connected(False)

    def _on_connect_spectrometer(self, name):
        self.controller.connect_spectrometer(name)
        self.sidebar.spec_conn.set_connected(True)

    def _on_disconnect_spectrometer(self):
        self.controller.disconnect_spectrometer()
        self.sidebar.spec_conn.set_connected(False)

    def _on_connect_motors(self, name):
        self.controller.connect_motors(name)
        self.sidebar.motor_conn.set_connected(True)

    def _on_disconnect_motors(self):
        self.controller.disconnect_motors()
        self.sidebar.motor_conn.set_connected(False)

    def _on_capture_image(self):
        if not self.controller.camera:
            QMessageBox.warning(self, "Camera", "Camera not connected")
            return

        image = self.controller.camera.capture()
        self.camera_widget.set_image(image)

    def _on_start_scan(self):
        if (
            not self.controller.camera
            or not self.controller.motors
            or not self.controller.spectrometer
        ):
            QMessageBox.warning(self, "Scan", "Not all devices connected")
            return

        roi = self.camera_widget.get_roi_rect()
        if not roi:
            QMessageBox.warning(self, "Scan", "ROI not selected")
            return

        self._heatmap_initialized = False
        scan_params = self.sidebar.get_scan_parameters()

        worker = self.controller.start_scan(roi, scan_params)
        self.sidebar.set_scan_running(True)

        worker.progress_updated.connect(
            lambda value: self.sidebar.status_lbl.setText(f"Scanning… {value}%")
        )
        worker.eta_updated.connect(self.sidebar.eta_lbl.setText)
        worker.point_acquired.connect(self._on_scan_point)
        worker.finished.connect(self._on_scan_finished)

        worker.start()

    def _on_scan_point(self, point):
        if not self._heatmap_initialized:
            self.heatmap_widget.initialize_grid([point])
            self._heatmap_initialized = True

        self.spectra_widget.update_from_scan_point(point)
        self.heatmap_widget.add_scan_point(point)

    def _on_stop_scan(self):
        self.controller.stop_scan()
        self.sidebar.set_scan_running(False)

    def _on_scan_finished(self):
        self.sidebar.set_scan_running(False)

    def _on_heatmap_point_selected(self, point):
        self.spectra_widget.update_from_scan_point(point)
        self.spectra_widget.set_raman_range(
            self.sidebar.raman_min.value(),
            self.sidebar.raman_max.value(),
        )
