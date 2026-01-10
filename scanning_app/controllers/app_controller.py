from pathlib import Path

import numpy as np
import pandas as pd

from controllers.scan_result import ScanResult
from devices.device_factory import DeviceFactory
from devices.scan_worker import ScanWorker
from project_io.load_project import Raman2DScanReader
from project_io.save_project import Raman2DScanWriter


class AppController:
    def __init__(self):
        self.device_factory = DeviceFactory()

        self.camera = None
        self.spectrometer = None
        self.motors = None

        self.scan_worker = None
        self.current_scan = None

        self.heatmap_png_bytes = None
        self.camera_png_bytes = None

        self.scan_dirty = False

        self.camera_raw_png = None
        self.camera_overview_png = None

        self._current_roi = None
        self._current_scan_params = None

    def set_heatmap_png(self, png_bytes: bytes) -> None:
        self.heatmap_png_bytes = png_bytes

    def set_camera_png(self, png_bytes: bytes) -> None:
        self.camera_png_bytes = png_bytes

    def list_cameras(self):
        return self.device_factory.available_cameras()

    def list_spectrometers(self):
        return self.device_factory.available_spectrometers()

    def list_motors(self):
        return self.device_factory.available_motors()

    def connect_camera(self, name):
        self.camera = self.device_factory.create_camera(name)
        self.camera.connect()

    def connect_spectrometer(self, name):
        self.spectrometer = self.device_factory.create_spectrometer(name)
        self.spectrometer.connect()

    def connect_motors(self, name):
        self.motors = self.device_factory.create_motors(name)
        self.motors.connect()

    def disconnect_camera(self):
        if self.camera:
            self.camera.disconnect()
        self.camera = None

    def disconnect_spectrometer(self):
        if self.spectrometer:
            self.spectrometer.disconnect()
        self.spectrometer = None

    def disconnect_motors(self):
        if self.motors:
            self.motors.disconnect()
        self.motors = None

    def start_scan(self, roi_rect, scan_params):
        if not self.motors or not self.spectrometer:
            raise RuntimeError("Motors or spectrometer not connected")

        if self.scan_worker is not None:
            raise RuntimeError("Scan already running")

        self._current_roi = (
            float(roi_rect.x()),
            float(roi_rect.y()),
            float(roi_rect.width()),
            float(roi_rect.height()),
        )
        self._current_scan_params = dict(scan_params)

        self.scan_worker = ScanWorker(
            roi_rect=roi_rect,
            scan_params=scan_params,
            motor_controller=self.motors,
            spectrometer=self.spectrometer,
        )
        return self.scan_worker

    def stop_scan(self):
        if self.scan_worker:
            self.scan_worker.stop()
            self.scan_worker = None

    def finalize_scan(self, scan_points, scan_params):
        self.current_scan = self._build_scan_result(scan_points)
        self.scan_dirty = True

    def _build_scan_result(self, scan_points):
        rows = []
        for point in scan_points:
            for wn, inten in zip(point.raman_shifts, point.intensities):
                rows.append(
                    {
                        "x": float(point.x),
                        "y": float(point.y),
                        "wavenumber_cm1": float(wn),
                        "intensity": float(inten),
                    }
                )

        spectra_df = pd.DataFrame(rows)

        scan_meta = {
            "num_points": len(scan_points),
            "step_size_x": self._current_scan_params["step_size_x"],
            "step_size_y": self._current_scan_params["step_size_y"],
            "roi": self._current_roi,
        }

        spectrometer_meta = {
            "integration_time_ms": self.spectrometer.integration_time_ms,
            "averages": self.spectrometer.averages,
            "excitation_wavelength_nm": (self.spectrometer.excitation_wavelength_nm),
        }

        heatmap_bounds = (
            self._current_scan_params["raman_min"],
            self._current_scan_params["raman_max"],
        )

        heatmap_grid = self._compute_heatmap_from_points(
            scan_points,
            heatmap_bounds,
        )

        return ScanResult(
            scan_meta=scan_meta,
            spectrometer_meta=spectrometer_meta,
            heatmap_bounds=heatmap_bounds,
            spectra_df=spectra_df,
            heatmap_grid=heatmap_grid,
            heatmap_png=self.heatmap_png_bytes,
            camera_overview_png=self.camera_overview_png,
            camera_raw_png=self.camera_raw_png,
        )

    def _compute_heatmap_from_points(self, scan_points, heatmap_bounds):
        x0, y0, w, h = self._current_roi
        step_x = self._current_scan_params["step_size_x"]
        step_y = self._current_scan_params["step_size_y"]

        xs = np.arange(x0, x0 + w, step_x)
        ys = np.arange(y0, y0 + h, step_y)

        grid = np.full((len(ys), len(xs)), np.nan)

        x_index = {round(x, 6): i for i, x in enumerate(xs)}
        y_index = {round(y, 6): i for i, y in enumerate(ys)}

        left, right = heatmap_bounds

        for point in scan_points:
            xi = x_index.get(round(point.x, 6))
            yi = y_index.get(round(point.y, 6))

            if xi is None or yi is None:
                continue

            mask = (point.raman_shifts >= left) & (point.raman_shifts <= right)
            grid[yi, xi] = float(point.intensities[mask].sum())

        return grid

    def save_current_scan(self, path: Path):
        if self.current_scan is None:
            raise RuntimeError("No scan data to save")

        self.current_scan.camera_png = self.camera_overview_png
        self.current_scan.camera_raw_png = self.camera_raw_png

        writer = Raman2DScanWriter()
        writer.write(
            path=path,
            scan_meta=self.current_scan.scan_meta,
            spectrometer_meta=self.current_scan.spectrometer_meta,
            heatmap_bounds=self.current_scan.heatmap_bounds,
            spectra_df=self.current_scan.spectra_df,
            heatmap_grid=self.current_scan.heatmap_grid,
            heatmap_png=self.current_scan.heatmap_png,
            camera_png=self.current_scan.camera_png,
            camera_raw_png=self.current_scan.camera_raw_png,
        )

        self.scan_dirty = False

    def load_scan(self, path: Path):
        reader = Raman2DScanReader()
        self.current_scan = reader.read(path)
        self.scan_dirty = False
        return self.current_scan

    def update_camera_images(self, *, raw: bytes, overview: bytes):
        self.camera_raw_png = raw
        self.camera_overview_png = overview
