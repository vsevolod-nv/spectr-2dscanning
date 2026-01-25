from pathlib import Path

import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QWidget,
)

from config import (
    DEFAULT_SPLITTER_SIZES,
    WINDOW_TITLE,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    WINDOW_X,
    WINDOW_Y,
    DEFAULT_STEP_SIZE_X,
    DEFAULT_STEP_SIZE_Y,
    EXPOSURE_DEFAULT,
    GAIN_DEFAULT,
    RAMAN_MIN_LIMIT,
    RAMAN_MAX_LIMIT,
)

from ui.app_state import AppState, ScanMode
from controllers.app_controller import AppController
from .camera_view_widget import CameraViewWidget
from .heatmap_preview_widget import HeatmapPreviewWidget
from .sidebar import SidebarWidget
from .spectra_preview_widget import SpectraPreviewWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.state = AppState()
        self.controller = AppController()
        self._scan_points: list = []

        self._configure_window()
        self._init_ui()
        self._connect_signals()
        self._populate_device_lists()

        self._enter_idle_mode()

    def _configure_window(self):
        self.setWindowTitle(WINDOW_TITLE)
        self.setGeometry(WINDOW_X, WINDOW_Y, WINDOW_WIDTH, WINDOW_HEIGHT)

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self.sidebar = SidebarWidget()
        layout.addWidget(self.sidebar)

        self.camera_widget = CameraViewWidget()
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
        sb = self.sidebar

        sb.reset_requested.connect(self._reset_application)
        sb.open_project_requested.connect(self._open_project)
        sb.save_project_requested.connect(self._save_project)

        sb.connect_camera_requested.connect(self._connect_camera)
        sb.disconnect_camera_requested.connect(self._disconnect_camera)
        sb.connect_spectrometer_requested.connect(self._connect_spectrometer)
        sb.disconnect_spectrometer_requested.connect(self._disconnect_spectrometer)
        sb.connect_motors_requested.connect(self._connect_motors)
        sb.disconnect_motors_requested.connect(self._disconnect_motors)

        sb.capture_image_requested.connect(self._capture_image)
        self.sidebar.scan_toggle_requested.connect(self._toggle_scan)

        sb.raman_min.valueChanged.connect(self._update_raman_range)
        sb.raman_max.valueChanged.connect(self._update_raman_range)

        self.heatmap_widget.scan_point_selected.connect(self._select_scan_point)
        self.spectra_widget.raman_range_selected.connect(self._set_raman_range_from_spectrum)
        self.spectra_widget.live_requested.connect(self._return_to_live)

    def _toggle_scan(self):
        if self.state.scan_mode == ScanMode.SCANNING:
            self._stop_scan()
            self.sidebar.set_scan_active(False)
        else:
            self._start_scan()
            self.sidebar.set_scan_active(True)

    def _sync_spectra_controls(self):
        self.spectra_widget.live_btn.setVisible(self.state.can_go_live)

    def _enter_idle_mode(self):
        self.state.scan_mode = ScanMode.IDLE
        self.state.spectra_live = False
        self.state.selected_point = None
        self._sync_spectra_controls()

        self.sidebar.set_viewer_mode(False)
        self.sidebar.set_scan_active(False)

    def _enter_viewer_mode(self):
        self.state.scan_mode = ScanMode.VIEWER
        self.state.spectra_live = False
        self.state.selected_point = None
        self._sync_spectra_controls()

        self.sidebar.set_viewer_mode(True)

    def _populate_device_lists(self):
        self.sidebar.cam_conn.populate_device_list(self.controller.list_cameras())
        self.sidebar.spec_conn.populate_device_list(self.controller.list_spectrometers())
        self.sidebar.motor_conn.populate_device_list(self.controller.list_motors())

    def _connect_camera(self, name):
        self.controller.connect_camera(name)
        self.camera_widget.camera = self.controller.camera
        self.sidebar.cam_conn.set_connected(True)

    def _disconnect_camera(self):
        self.controller.disconnect_camera()
        self.camera_widget.camera = None
        self.sidebar.cam_conn.set_connected(False)

    def _connect_spectrometer(self, name):
        self.controller.connect_spectrometer(name)
        self.sidebar.spec_conn.set_connected(True)

    def _disconnect_spectrometer(self):
        self.controller.disconnect_spectrometer()
        self.sidebar.spec_conn.set_connected(False)

    def _connect_motors(self, name):
        self.controller.connect_motors(name)
        self.sidebar.motor_conn.set_connected(True)

    def _disconnect_motors(self):
        self.controller.disconnect_motors()
        self.sidebar.motor_conn.set_connected(False)

    def _capture_image(self):
        if not self.controller.camera:
            QMessageBox.warning(self, "Camera", "Camera not connected")
            return

        image = self.controller.camera.capture()
        self.camera_widget.set_image(image)
        self._update_camera_images()

    def _start_scan(self):
        if not all((self.controller.camera, self.controller.motors, self.controller.spectrometer)):
            QMessageBox.warning(self, "Scan", "Not all devices connected")
            return

        roi = self.camera_widget.get_roi_rect()
        if not roi:
            QMessageBox.warning(self, "Scan", "ROI not selected")
            return

        self.state.scan_mode = ScanMode.SCANNING
        self.state.spectra_live = True
        self.state.selected_point = None
        self._sync_spectra_controls()

        self._scan_points.clear()
        self.sidebar.set_save_enabled(False)
        self.sidebar.set_viewer_mode(False)

        worker = self.controller.start_scan(roi, self.sidebar.get_scan_parameters())
        self.heatmap_widget.initialize_grid(worker.generate_planned_points())

        worker.point_acquired.connect(self._handle_scan_point)
        worker.finished.connect(self._finish_scan)
        worker.start()

    def _handle_scan_point(self, point):
        self._scan_points.append(point)

        self.heatmap_widget.populate_from_points(
            self._scan_points,
            self.sidebar.raman_min.value(),
            self.sidebar.raman_max.value(),
        )

        if self.state.spectra_live:
            self.spectra_widget.update_from_scan_point(point)
            self.heatmap_widget.highlight_point(point)

    def _stop_scan(self):
        self.controller.stop_scan()
        self._finish_scan()

    def _finish_scan(self):
        if not self._scan_points:
            return

        self.controller.finalize_scan(
            self._scan_points,
            self.sidebar.get_scan_parameters(),
        )

        self.sidebar.set_scan_active(False)
        self.sidebar.set_save_enabled(True)

        self._enter_idle_mode()

    def _select_scan_point(self, point):
        self.state.spectra_live = False
        self.state.selected_point = point
        self._sync_spectra_controls()

        self.spectra_widget.update_from_scan_point(point)
        self.heatmap_widget.highlight_point(point)

    def _return_to_live(self):
        if not self._scan_points:
            return

        self.state.spectra_live = True
        self.state.selected_point = None
        self._sync_spectra_controls()

        point = self._scan_points[-1]
        self.spectra_widget.update_from_scan_point(point)
        self.heatmap_widget.highlight_point(point)

    def _set_raman_range_from_spectrum(self, rmin, rmax):
        self.sidebar.set_raman_range(rmin, rmax)
        self.heatmap_widget.set_raman_range(rmin, rmax)

    def _update_raman_range(self):
        rmin = self.sidebar.raman_min.value()
        rmax = self.sidebar.raman_max.value()

        self.spectra_widget.set_raman_range(rmin, rmax)
        self.heatmap_widget.set_raman_range(rmin, rmax)

    def _save_project(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Raman 2D Scan",
            "",
            "Raman 2D Scan (*.raman2dscan)",
        )
        if not path:
            return

        self._update_camera_images()
        self.controller.save_current_scan(Path(path))

    def _open_project(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Raman 2D Scan",
            "",
            "Raman 2D Scan (*.raman2dscan)",
        )
        if not path:
            return

        scan = self.controller.load_scan(Path(path))
        self._load_scan_into_ui(scan)
        self._enter_viewer_mode()

    def _load_scan_into_ui(self, scan):
        if scan.camera_overview_png:
            image = QImage.fromData(scan.camera_overview_png, "PNG")
            image = image.convertToFormat(QImage.Format.Format_RGB32)
            self.camera_widget.set_image(image)

        points = []
        grouped = scan.spectra_df.groupby(["x", "y"])
        for (x, y), group in grouped:
            points.append(
                type(
                    "P",
                    (),
                    {
                        "x": float(x),
                        "y": float(y),
                        "raman_shifts": group["wavenumber_cm1"].values,
                        "intensities": group["intensity"].values,
                    },
                )
            )

        roi = scan.scan_meta.get("roi")
        if roi:
            x0, y0, w, h = roi
            xs = np.arange(x0, x0 + w, scan.scan_meta["step_size_x"])
            ys = np.arange(y0, y0 + h, scan.scan_meta["step_size_y"])
            planned = [type("P", (), {"x": x, "y": y}) for y in ys for x in xs]
        else:
            planned = points

        self.heatmap_widget.initialize_grid(planned)
        self.heatmap_widget.populate_from_points(points, *scan.heatmap_bounds)

        if points:
            self.spectra_widget.update_from_scan_point(points[0])

        self.sidebar.set_raman_range(*scan.heatmap_bounds)

    def _reset_application(self):
        self.controller.stop_scan()
        self.controller.current_scan = None
        self.controller.scan_dirty = False

        self._disconnect_camera()
        self._disconnect_spectrometer()
        self._disconnect_motors()

        self.camera_widget.clear_roi()
        self.camera_widget.set_image(None)
        self.heatmap_widget.clear()
        self.spectra_widget.clear()

        self.sidebar.set_save_enabled(False)
        self.sidebar.step_x.setValue(DEFAULT_STEP_SIZE_X)
        self.sidebar.step_y.setValue(DEFAULT_STEP_SIZE_Y)
        self.sidebar.expo_spin.setValue(EXPOSURE_DEFAULT)
        self.sidebar.gain_spin.setValue(GAIN_DEFAULT)
        self.sidebar.set_raman_range(RAMAN_MIN_LIMIT, RAMAN_MAX_LIMIT)
        self.sidebar.eta_lbl.setText("--:--:--")

        self._populate_device_lists()
        self._enter_idle_mode()

    def closeEvent(self, event):
        if not self.controller.current_scan or not self.controller.scan_dirty:
            event.accept()
            return

        choice = QMessageBox.question(
            self,
            "Unsaved Scan",
            "You have an unsaved Raman scan. Save before exit?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
        )

        if choice == QMessageBox.StandardButton.Save:
            self._save_project()
            event.accept()
        elif choice == QMessageBox.StandardButton.Discard:
            event.accept()
        else:
            event.ignore()

    def _update_camera_images(self):
        self.controller.update_camera_images(
            raw=self.camera_widget.export_raw_png(),
            overview=self.camera_widget.export_overview_png(),
        )
