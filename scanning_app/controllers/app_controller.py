from pathlib import Path

import numpy as np
import pandas as pd

from controllers.scan_result import ScanResult
from devices.device_factory import DeviceFactory
from devices.scan_worker import ScanWorker
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
        self.current_scan = self._build_scan_result(scan_points, scan_params)
        self.scan_dirty = True

    def _build_scan_result(self, scan_points, scan_params):
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
            "step_size_x": scan_params["step_size_x"],
            "step_size_y": scan_params["step_size_y"],
        }

        spectrometer_meta = {
            "integration_time_ms": self.spectrometer.integration_time_ms,
            "averages": self.spectrometer.averages,
            "excitation_wavelength_nm": (self.spectrometer.excitation_wavelength_nm),
        }

        heatmap_bounds = (
            scan_params["raman_min"],
            scan_params["raman_max"],
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
            camera_png=self.camera_png_bytes,
        )

    def save_current_scan(self, path: Path):
        if self.current_scan is None:
            raise RuntimeError("No scan data to save")

        self.current_scan.heatmap_png = self.heatmap_png_bytes
        self.current_scan.camera_png = self.camera_png_bytes

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
        )

        self.scan_dirty = False

    def _compute_heatmap_from_points(self, scan_points, heatmap_bounds):
        xs = sorted({p.x for p in scan_points})
        ys = sorted({p.y for p in scan_points})

        x_index = {x: i for i, x in enumerate(xs)}
        y_index = {y: i for i, y in enumerate(ys)}

        grid = np.zeros((len(ys), len(xs)), dtype=float)

        left, right = heatmap_bounds

        for point in scan_points:
            mask = (point.raman_shifts >= left) & (point.raman_shifts <= right)
            grid[y_index[point.y], x_index[point.x]] = float(
                point.intensities[mask].sum()
            )

        return grid
