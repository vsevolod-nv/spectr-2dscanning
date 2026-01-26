from pathlib import Path

import numpy as np
from PyQt6.QtCore import Qt
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
    WINDOW_HEIGHT,
    WINDOW_TITLE,
    WINDOW_WIDTH,
    WINDOW_X,
    WINDOW_Y,
)

from controllers.app_controller import AppController
from devices.scan_worker import ScanPoint
from ui.app_state import AppState, ScanMode
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
        self.state = AppState()

        self._live_mode = True
        self._last_live_point = None
        self._live_scan_points = []

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

        sb.connect_camera_requested.connect(self._connect_camera)
        sb.disconnect_camera_requested.connect(self._disconnect_camera)
        sb.capture_image_requested.connect(self._capture_image)

        sb.connect_spectrometer_requested.connect(self._connect_spectrometer)
        sb.disconnect_spectrometer_requested.connect(self._disconnect_spectrometer)

        sb.connect_motors_requested.connect(self._connect_motors)
        sb.disconnect_motors_requested.connect(self._disconnect_motors)

        sb.scan_toggle_requested.connect(self._toggle_scan)
        sb.save_project_requested.connect(self._save_project)
        sb.open_project_requested.connect(self._open_project)
        sb.reset_requested.connect(self._reset_viewer)

        self.heatmap_widget.scan_point_selected.connect(
            self._on_heatmap_point_selected
        )
        self.spectra_widget.raman_range_selected.connect(
            self._on_raman_range_changed
        )
        self.spectra_widget.live_requested.connect(
            self._return_to_live_mode
        )

    def _populate_device_lists(self):
        self.sidebar.cam_conn.populate_device_list(
            self.controller.list_cameras()
        )
        self.sidebar.spec_conn.populate_device_list(
            self.controller.list_spectrometers()
        )
        self.sidebar.motor_conn.populate_device_list(
            self.controller.list_motors()
        )

    def _set_viewer_mode_ui(self, enabled: bool):
        sb = self.sidebar

        sb.cam_conn.setEnabled(not enabled)
        sb.spec_conn.setEnabled(not enabled)
        sb.motor_conn.setEnabled(not enabled)

        sb.capture_btn.setEnabled(not enabled)
        sb.scan_btn.setEnabled(not enabled)

    def _connect_camera(self, name: str):
        self.controller.connect_camera(name)
        self.camera_widget.camera = self.controller.camera
        self.sidebar.cam_conn.set_connected(True)

    def _disconnect_camera(self):
        self.controller.disconnect_camera()
        self.camera_widget.camera = None
        self.camera_widget.set_image(None)
        self.sidebar.cam_conn.set_connected(False)

    def _capture_image(self):
        if not self.controller.camera:
            QMessageBox.warning(self, "Camera", "Camera not connected")
            return

        cam = self.controller.camera
        settings = self.sidebar.get_camera_settings()

        cam.set_auto_exposure(settings["auto_exposure"])
        cam.set_auto_white_balance(settings["auto_white_balance"])

        if not settings["auto_exposure"]:
            cam.set_exposure(settings["exposure_us"])
            cam.set_gain(settings["gain"])

        cam.set_gamma(settings["gamma"])
        cam.set_contrast(settings["contrast"])

        self.camera_widget.set_image(
            self.controller.capture_camera_image()
        )

    def _connect_spectrometer(self, name: str):
        self.controller.connect_spectrometer(name)
        self.sidebar.spec_conn.set_connected(True)

    def _disconnect_spectrometer(self):
        self.controller.disconnect_spectrometer()
        self.sidebar.spec_conn.set_connected(False)

    def _connect_motors(self, name: str):
        self.controller.connect_motors(name)
        self.sidebar.motor_conn.set_connected(True)

    def _disconnect_motors(self):
        self.controller.disconnect_motors()
        self.sidebar.motor_conn.set_connected(False)

    def _toggle_scan(self):
        if self.controller.scan_worker is None:
            self._start_scan()
        else:
            self._stop_scan()

    def _start_scan(self):
        roi = self.camera_widget.get_roi_rect()
        if roi is None:
            QMessageBox.warning(self, "Scan", "Select ROI first")
            return

        if not self.controller.motors or not self.controller.spectrometer:
            QMessageBox.warning(
                self, "Scan", "Motors and spectrometer must be connected"
            )
            return

        worker = self.controller.start_scan(
            roi, self.sidebar.get_scan_parameters()
        )

        self.state.scan_mode = ScanMode.SCANNING
        self.sidebar.set_scan_active(True)
        self._live_scan_points.clear()

        worker.progress_updated.connect(
            lambda v: self.sidebar.status_lbl.setText(f"Progress: {v}%")
        )
        worker.eta_updated.connect(self.sidebar.eta_lbl.setText)
        worker.point_acquired.connect(self._on_scan_point_acquired)
        worker.finished.connect(self._scan_finished)

        self.heatmap_widget.initialize_grid(
            worker.generate_planned_points()
        )

        worker.start()

    def _stop_scan(self):
        self.controller.stop_scan()
        self.sidebar.set_scan_active(False)
        self.state.scan_mode = ScanMode.IDLE

    def _scan_finished(self, points):
        if not points:
            self.sidebar.set_scan_active(False)
            self.state.scan_mode = ScanMode.IDLE
            return

        self._set_viewer_mode_ui(True)
        self.controller.finalize_scan(
            points, self.sidebar.get_scan_parameters()
        )

        self.state.scan_mode = ScanMode.VIEWER
        self.sidebar.set_scan_active(False)
        self.sidebar.set_save_enabled(True)
        self.sidebar.reset_btn.setVisible(True)

        self.heatmap_widget.populate_from_points(
            points,
            self.sidebar.raman_min.value(),
            self.sidebar.raman_max.value(),
        )

    def _on_scan_point_acquired(self, point):
        self._live_scan_points.append(point)
        self._last_live_point = point

        self.heatmap_widget.populate_from_points(
            self._live_scan_points,
            self.sidebar.raman_min.value(),
            self.sidebar.raman_max.value(),
        )

        if self._live_mode:
            self.heatmap_widget.highlight_point(point)
            self.spectra_widget.update_from_scan_point(point)
            self.spectra_widget.live_btn.setVisible(False)

    def _on_heatmap_point_selected(self, point):
        self._live_mode = False
        self.spectra_widget.update_from_scan_point(point)

        if self.state.scan_mode == ScanMode.SCANNING:
            self.spectra_widget.live_btn.setVisible(True)

    def _return_to_live_mode(self):
        self._live_mode = True
        self.spectra_widget.live_btn.setVisible(False)

        if self._last_live_point:
            self.heatmap_widget.highlight_point(self._last_live_point)
            self.spectra_widget.update_from_scan_point(self._last_live_point)

    def _on_raman_range_changed(self, rmin, rmax):
        self.heatmap_widget.set_raman_range(rmin, rmax)

        self.sidebar.raman_min.blockSignals(True)
        self.sidebar.raman_max.blockSignals(True)
        self.sidebar.raman_min.setValue(rmin)
        self.sidebar.raman_max.setValue(rmax)
        self.sidebar.raman_min.blockSignals(False)
        self.sidebar.raman_max.blockSignals(False)

    def _save_project(self):
        if not self.controller.current_scan:
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Save Scan", "", "Raman 2D Scan (*.raman2dscan)"
        )
        if not path:
            return

        self.controller.set_heatmap_png(
            self.heatmap_widget.export_png()
        )
        self.controller.update_camera_images(
            raw=self.camera_widget.export_raw_png(),
            overview=self.camera_widget.export_overview_png(),
        )
        self.controller.save_current_scan(Path(path))

    def _open_project(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Scan", "", "Raman 2D Scan (*.raman2dscan)"
        )
        if not path:
            return

        self._set_viewer_mode_ui(True)
        scan = self.controller.load_scan(Path(path))

        measured = self._scanpoints_from_scanresult(scan)
        planned = self._planned_points_from_scanmeta(scan)

        self._live_scan_points = measured
        self._live_mode = False

        self.state.scan_mode = ScanMode.VIEWER
        self.sidebar.reset_btn.setVisible(True)
        self.sidebar.set_save_enabled(False)

        self.heatmap_widget.initialize_grid(planned)
        self.heatmap_widget.populate_from_points(
            measured,
            scan.heatmap_bounds[0],
            scan.heatmap_bounds[1],
        )

        self.spectra_widget.clear()
        self.spectra_widget.live_btn.setVisible(False)

        self.camera_widget.clear_roi()
        if scan.camera_overview_png:
            from PyQt6.QtGui import QImage

            self.camera_widget.set_image(
                QImage.fromData(scan.camera_overview_png, "PNG")
            )
        else:
            self.camera_widget.set_image(None)

    def _reset_viewer(self):
        self._set_viewer_mode_ui(False)

        self.state.scan_mode = ScanMode.IDLE
        self.controller.current_scan = None

        self.sidebar.reset_btn.setVisible(False)
        self.sidebar.set_save_enabled(False)
        self.sidebar.status_lbl.setText("Idle")
        self.sidebar.eta_lbl.setText("--:--:--")

        self.heatmap_widget.clear()
        self.spectra_widget.clear()
        self.camera_widget.clear_roi()
        self.camera_widget.set_image(None)

    def _planned_points_from_scanmeta(self, scan):
        x0, y0, w, h = scan.scan_meta["roi"]
        step_x = scan.scan_meta["step_size_x"]
        step_y = scan.scan_meta["step_size_y"]

        xs = np.arange(x0, x0 + w, step_x)
        ys = np.arange(y0, y0 + h, step_y)

        return [
            ScanPoint(float(x), float(y), None, None)
            for y in ys
            for x in xs
        ]

    def _scanpoints_from_scanresult(self, scan):
        return [
            ScanPoint(
                float(x),
                float(y),
                df["wavenumber_cm1"].to_numpy(float),
                df["intensity"].to_numpy(float),
            )
            for (x, y), df in scan.spectra_df.groupby(["x", "y"])
        ]
