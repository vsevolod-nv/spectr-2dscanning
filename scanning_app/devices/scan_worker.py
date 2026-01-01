import time
from typing import List, Tuple

import numpy as np
from loguru import logger
from PyQt6.QtCore import QThread, pyqtSignal

from config import SPECTRUM_MAX_WAVENUMBER


class ScanWorker(QThread):
    progress_updated = pyqtSignal(int)
    finished = pyqtSignal(list)
    eta_updated = pyqtSignal(str)
    data_point_acquired = pyqtSignal(tuple)

    def __init__(self, roi_rect, scan_params, motor_controller, spectrometer):
        super().__init__()
        self.roi_rect = roi_rect
        self.scan_params = scan_params
        self.motor_controller = motor_controller
        self.spectrometer = spectrometer
        self._is_stopped = False

    def stop(self):
        self._is_stopped = True

    def run(self):
        x_start = self.roi_rect.left()
        x_end = self.roi_rect.right()
        y_start = self.roi_rect.top()
        y_end = self.roi_rect.bottom()

        step_x = max(0.1, self.scan_params["step_size_x"])
        step_y = max(0.1, self.scan_params["step_size_y"])

        x_points = np.arange(x_start, x_end, step_x)
        y_points = np.arange(y_start, y_end, step_y)

        total_points = len(x_points) * len(y_points)
        if total_points == 0:
            logger.warning("No scan points generated—empty ROI or invalid step size")
            self.finished.emit([])
            return

        results: List[Tuple[float, float, float]] = []
        start_time = time.time()

        for i, y in enumerate(y_points):
            if self._is_stopped:
                logger.info("Scan stopped by user")
                break

            for j, x in enumerate(x_points):
                if self._is_stopped:
                    break

                self.motor_controller.move_to(x, y)
                spectrum = self.spectrometer.capture_spectrum()

                raman_min = self.scan_params["raman_min"]
                raman_max = self.scan_params["raman_max"]
                spectrum_len = len(spectrum)

                if SPECTRUM_MAX_WAVENUMBER > 0:
                    min_idx = int((raman_min / SPECTRUM_MAX_WAVENUMBER) * spectrum_len)
                    max_idx = int((raman_max / SPECTRUM_MAX_WAVENUMBER) * spectrum_len)
                else:
                    min_idx, max_idx = 0, spectrum_len

                min_idx = max(0, min_idx)
                max_idx = min(spectrum_len, max_idx)

                intensity = (
                    np.sum(spectrum[min_idx:max_idx]) if min_idx < max_idx else 0.0
                )

                point_data = (x, y, intensity)
                results.append(point_data)

                processed = i * len(x_points) + j + 1
                elapsed = time.time() - start_time
                if processed > 0:
                    remaining = total_points - processed
                    eta_seconds = (elapsed / processed) * remaining
                    m, s = divmod(eta_seconds, 60)
                    h, m = divmod(m, 60)
                    eta_str = f"{int(h):02}:{int(m):02}:{int(s):02}"
                else:
                    eta_str = "--:--:--"

                self.eta_updated.emit(eta_str)
                self.progress_updated.emit(int((processed / total_points) * 100))

        logger.info(f"Scan completed. Collected {len(results)} data points")
        self.finished.emit(results)
