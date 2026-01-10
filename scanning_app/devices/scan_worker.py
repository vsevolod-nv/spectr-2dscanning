import time
from dataclasses import dataclass

import numpy as np
from loguru import logger
from PyQt6.QtCore import QThread, pyqtSignal


@dataclass
class ScanPoint:
    x: float
    y: float
    raman_shifts: np.ndarray | None
    intensities: np.ndarray | None


class ScanWorker(QThread):
    progress_updated = pyqtSignal(int)
    eta_updated = pyqtSignal(str)
    point_acquired = pyqtSignal(object)
    finished = pyqtSignal(list)

    def __init__(self, roi_rect, scan_params, motor_controller, spectrometer):
        super().__init__()
        self.roi_rect = roi_rect
        self.scan_params = scan_params
        self.motor_controller = motor_controller
        self.spectrometer = spectrometer
        self._is_stopped = False

    def stop(self):
        logger.info("ScanWorker stop requested")
        self._is_stopped = True

    def run(self):
        try:
            x_start = self.roi_rect.left()
            x_end = self.roi_rect.right()
            y_start = self.roi_rect.top()
            y_end = self.roi_rect.bottom()

            step_x = max(0.1, float(self.scan_params["step_size_x"]))
            step_y = max(0.1, float(self.scan_params["step_size_y"]))

            x_points = np.arange(x_start, x_end, step_x)
            y_points = np.arange(y_start, y_end, step_y)

            total_points = len(x_points) * len(y_points)
            if total_points == 0:
                logger.warning("No scan points generated")
                self.finished.emit([])
                return

            results: list[ScanPoint] = []
            start_time = time.time()
            processed = 0

            for y in y_points:
                if self._is_stopped:
                    break

                for x in x_points:
                    if self._is_stopped:
                        break

                    self.motor_controller.move_to(x, y)
                    raman_shifts, intensities = self.spectrometer.acquire_spectrum()

                    point = ScanPoint(
                        x=float(x),
                        y=float(y),
                        raman_shifts=raman_shifts,
                        intensities=intensities,
                    )

                    results.append(point)
                    self.point_acquired.emit(point)

                    processed += 1
                    elapsed = time.time() - start_time
                    remaining = total_points - processed
                    eta_sec = (elapsed / processed) * remaining if processed else 0

                    hours, rem = divmod(int(eta_sec), 3600)
                    minutes, seconds = divmod(rem, 60)

                    self.eta_updated.emit(f"{hours:02}:{minutes:02}:{seconds:02}")
                    self.progress_updated.emit(int(processed / total_points * 100))

            logger.info(
                "Scan %s. Collected %d points",
                "stopped early" if self._is_stopped else "completed",
                len(results),
            )
            self.finished.emit(results)

        except Exception:
            logger.exception("Unhandled exception in ScanWorker")
            self.finished.emit([])

    def generate_planned_points(self):
        x_start = self.roi_rect.left()
        x_end = self.roi_rect.right()
        y_start = self.roi_rect.top()
        y_end = self.roi_rect.bottom()

        step_x = max(0.1, float(self.scan_params["step_size_x"]))
        step_y = max(0.1, float(self.scan_params["step_size_y"]))

        return [
            ScanPoint(x, y, None, None)
            for y in np.arange(y_start, y_end, step_y)
            for x in np.arange(x_start, x_end, step_x)
        ]
