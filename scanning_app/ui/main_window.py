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
    WINDOW_HEIGHT,
    WINDOW_TITLE,
    WINDOW_WIDTH,
    WINDOW_X,
    WINDOW_Y,
    DEFAULT_STEP_SIZE_X, 
    DEFAULT_STEP_SIZE_Y, 
    EXPOSURE_DEFAULT,
    GAIN_DEFAULT,
    RAMAN_MIN_LIMIT,
    RAMAN_MAX_LIMIT
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
        self._scan_finalized = False
        self._scan_running = False
        self._spectra_live_mode = True
        self._locked_point = None
        self._collected_scan_points = []

        self._init_ui()
        self._connect_signals()
        self._populate_device_lists()
        self.sidebar.set_viewer_mode(False)

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
        sidebar = self.sidebar

        sidebar.reset_requested.connect(self._on_reset)

        sidebar.open_project_requested.connect(self._on_open_project)
        sidebar.set_viewer_mode(True)

        sidebar.connect_camera_requested.connect(self._on_connect_camera)
        sidebar.disconnect_camera_requested.connect(self._on_disconnect_camera)

        sidebar.connect_spectrometer_requested.connect(self._on_connect_spectrometer)
        sidebar.disconnect_spectrometer_requested.connect(
            self._on_disconnect_spectrometer
        )

        sidebar.connect_motors_requested.connect(self._on_connect_motors)
        sidebar.disconnect_motors_requested.connect(self._on_disconnect_motors)

        sidebar.capture_image_requested.connect(self._on_capture_image)
        sidebar.start_scan_requested.connect(self._on_start_scan)
        sidebar.stop_scan_requested.connect(self._on_stop_scan)

        sidebar.save_project_requested.connect(self._on_save_project)

        sidebar.raman_min.valueChanged.connect(self._on_raman_range_changed)
        sidebar.raman_max.valueChanged.connect(self._on_raman_range_changed)

        self.spectra_widget.raman_range_selected.connect(
            self._on_raman_range_from_spectrum
        )
        self.heatmap_widget.scan_point_selected.connect(self._on_heatmap_point_selected)

        self.spectra_widget.live_requested.connect(self._on_live_requested)

    def _on_reset(self):
        self.controller.stop_scan()
        self.sidebar.set_scan_running(False)
        self._on_disconnect_camera()
        self._on_disconnect_spectrometer()
        self._on_disconnect_motors()
        self.camera_widget.clear_roi()
        self.camera_widget.set_image(None)
        self._scan_running = False
        self._spectra_live_mode = False
        self.spectra_widget.live_btn.setVisible(False)

        self._heatmap_initialized = False
        self._scan_finalized = False
        self._collected_scan_points = []
        self.controller.current_scan = None 
        self.controller.scan_dirty = False 
        self.controller.heatmap_png_bytes = None 
        self.controller.camera_raw_png = None
        self.controller.camera_overview_png = None
        self.sidebar.set_viewer_mode(False)
        self.sidebar.set_save_enabled(False)
        self.sidebar.step_x.setValue(DEFAULT_STEP_SIZE_X)
        self.sidebar.step_y.setValue(DEFAULT_STEP_SIZE_Y)
        self.sidebar.set_raman_range(RAMAN_MIN_LIMIT, RAMAN_MAX_LIMIT)
        self.sidebar.expo_spin.setValue(EXPOSURE_DEFAULT)
        self.sidebar.gain_spin.setValue(GAIN_DEFAULT)
        self.heatmap_widget.clear()
        self.spectra_widget.clear()
        self.spectra_widget.set_raman_range(RAMAN_MIN_LIMIT, RAMAN_MAX_LIMIT)
        self._populate_device_lists()
        self.sidebar.eta_lbl.setText("--:--:--")

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
        self._update_camera_images()

    def _on_start_scan(self):
        
        self._scan_running = True
        self._spectra_live_mode = True
        self._locked_point = None
        self.spectra_widget.live_btn.setVisible(False)

        self.sidebar.set_viewer_mode(False)

        if not all(
            (
                self.controller.camera,
                self.controller.motors,
                self.controller.spectrometer,
            )
        ):
            QMessageBox.warning(self, "Scan", "Not all devices connected")
            return

        roi = self.camera_widget.get_roi_rect()
        if not roi:
            QMessageBox.warning(self, "Scan", "ROI not selected")
            return

        self._scan_finalized = False
        self._collected_scan_points = []
        self.sidebar.set_save_enabled(False)

        scan_params = self.sidebar.get_scan_parameters()
        worker = self.controller.start_scan(roi, scan_params)

        planned_points = worker.generate_planned_points()
        self.heatmap_widget.initialize_grid(planned_points)
        self._heatmap_initialized = True

        self.sidebar.set_scan_running(True)

        worker.progress_updated.connect(
            lambda value: self.sidebar.status_lbl.setText(f"Scanning… {value}%")
        )
        worker.eta_updated.connect(self.sidebar.eta_lbl.setText)
        worker.point_acquired.connect(self._on_scan_point)
        worker.finished.connect(self._on_scan_finished)

        worker.start()

    def _on_scan_point(self, point):
        self._collected_scan_points.append(point)

        if self._spectra_live_mode:
            self.spectra_widget.update_from_scan_point(point)
            self.heatmap_widget.highlight_point(point)

        rmin = self.sidebar.raman_min.value()
        rmax = self.sidebar.raman_max.value()

        self.heatmap_widget.populate_from_points(
            self._collected_scan_points,
            rmin,
            rmax,
        )

    def _on_stop_scan(self):
        self.controller.stop_scan()
        self.sidebar.set_scan_running(False)

        if self._collected_scan_points and not self._scan_finalized:
            self.controller.finalize_scan(
                self._collected_scan_points,
                self.sidebar.get_scan_parameters(),
            )
            self._scan_running = False
            self._scan_finalized = True
            self.sidebar.set_save_enabled(True)

        self._spectra_live_mode = False
        self.spectra_widget.live_btn.setVisible(False)

    def _on_scan_finished(self):
        self.sidebar.set_scan_running(False)

        if self._scan_finalized:
            return

        if self._collected_scan_points:
            self.controller.finalize_scan(
                self._collected_scan_points,
                self.sidebar.get_scan_parameters(),
            )
            self._scan_running = False
            self._scan_finalized = True
            self.sidebar.set_save_enabled(True)

        self._spectra_live_mode = False
        self.spectra_widget.live_btn.setVisible(False)

    def _on_raman_range_from_spectrum(self, rmin, rmax):
        self.sidebar.set_raman_range(rmin, rmax)
        self.heatmap_widget.set_raman_range(rmin, rmax)

    def _on_raman_range_changed(self):
        rmin = self.sidebar.raman_min.value()
        rmax = self.sidebar.raman_max.value()

        self.spectra_widget.set_raman_range(rmin, rmax)
        self.heatmap_widget.set_raman_range(rmin, rmax)

    def _on_heatmap_point_selected(self, point):
        self._spectra_live_mode = False
        self._locked_point = point

        self.spectra_widget.update_from_scan_point(point)
        self.heatmap_widget.highlight_point(point)

        if self._scan_running:
            self.spectra_widget.live_btn.setVisible(True)
        else:
            self.spectra_widget.live_btn.setVisible(False)

        self.spectra_widget.set_raman_range(
            self.sidebar.raman_min.value(),
            self.sidebar.raman_max.value(),
        )

    def closeEvent(self, event):
        ctrl = self.controller

        if not ctrl.current_scan or not ctrl.scan_dirty:
            event.accept()
            return

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Unsaved Scan")
        msg.setText("You have an unsaved Raman scan.")
        msg.setInformativeText("Do you want to save it before quitting?")
        msg.setStandardButtons(
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel
        )
        msg.setDefaultButton(QMessageBox.StandardButton.Save)

        result = msg.exec()

        if result == QMessageBox.StandardButton.Save:
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Raman 2D Scan",
                "",
                "Raman 2D Scan (*.raman2dscan)",
            )
            if not path:
                event.ignore()
                return

            ctrl.save_current_scan(Path(path))
            event.accept()
        elif result == QMessageBox.StandardButton.Discard:
            event.accept()
        else:
            event.ignore()

    def _on_save_project(self):
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

    def _load_scan_into_ui(self, scan):
        self.spectra_widget.live_btn.setVisible(False)
        if scan.camera_overview_png:
            image = QImage.fromData(scan.camera_overview_png, "PNG")

            if image.isNull():
                raise RuntimeError("Failed to load camera PNG from project")

            image = image.convertToFormat(QImage.Format.Format_RGB32)
            image = image.copy()

            self.camera_widget.set_image(image)

        points = []
        grouped = scan.spectra_df.groupby(["x", "y"])

        for (x, y), group in grouped:
            if group.empty:
                continue

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
        step_x = scan.scan_meta["step_size_x"]
        step_y = scan.scan_meta["step_size_y"]

        if roi:
            x0, y0, w, h = roi
            xs = np.arange(x0, x0 + w, step_x)
            ys = np.arange(y0, y0 + h, step_y)

            planned_points = [
                type("P", (), {"x": float(x), "y": float(y)}) for y in ys for x in xs
            ]
        else:
            planned_points = points

        self.heatmap_widget.initialize_grid(planned_points)

        rmin, rmax = scan.heatmap_bounds
        self.heatmap_widget.populate_from_points(points, rmin, rmax)

        if points:
            self.spectra_widget.update_from_scan_point(points[0])

        self.spectra_widget.set_interactive(False)
        self.sidebar.set_raman_range(rmin, rmax)
        self.spectra_widget.set_raman_range(rmin, rmax)
        self.heatmap_widget.set_raman_range(rmin, rmax)
        self.spectra_widget.set_interactive(True)
        self.sidebar.set_viewer_mode(True)

    def _on_open_project(self):
        self._scan_running = False
        self._spectra_live_mode = False
        self.spectra_widget.live_btn.setVisible(False)

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Raman 2D Scan",
            "",
            "Raman 2D Scan (*.raman2dscan)",
        )
        if not path:
            return

        self.spectra_widget.set_interactive(False)
        scan = self.controller.load_scan(Path(path))
        self._load_scan_into_ui(scan)
        self.spectra_widget.set_interactive(True)
        self.sidebar.set_viewer_mode(True)

    def _update_camera_images(self):
        self.controller.update_camera_images(
            raw=self.camera_widget.export_raw_png(),
            overview=self.camera_widget.export_overview_png(),
        )

    def _on_live_requested(self):
        self._spectra_live_mode = True
        self._locked_point = None
        self.spectra_widget.live_btn.setVisible(False)

        if self._collected_scan_points:
            last = self._collected_scan_points[-1]
            self.spectra_widget.update_from_scan_point(last)
            self.heatmap_widget.highlight_point(last)
