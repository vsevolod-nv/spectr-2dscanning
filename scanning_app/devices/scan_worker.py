from PyQt6.QtCore import QThread, pyqtSignal
import numpy as np
import time
from config import SPECTRUM_MAX_WAVENUMBER
 
class ScanWorker(QThread):
    progress_updated = pyqtSignal(int)
    finished = pyqtSignal(list)
    eta_updated = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
 
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
        try:
            x_start = self.roi_rect.left()
            x_end = self.roi_rect.right()
            y_start = self.roi_rect.top()
            y_end = self.roi_rect.bottom()
 
            step_x = self.scan_params["step_size_x"]
            step_y = self.scan_params["step_size_y"]
 
            x_points = np.arange(x_start, x_end, step_x)
            y_points = np.arange(y_start, y_end, step_y)
 
            total_points = len(x_points) * len(y_points)
            if total_points == 0:
                self.error_occurred.emit("ROI too small or step size too large.")
                return
 
            results = []
            start_time = time.time()
            processed_count = 0
 
            for i, y in enumerate(y_points):
                if self._is_stopped: break
                for j, x in enumerate(x_points):
                    if self._is_stopped: break
 
                    self.motor_controller.move_to(x, y)
                    spectrum = self.spectrometer.capture_spectrum()
 
                    raman_min = self.scan_params["raman_min"]
                    raman_max = self.scan_params["raman_max"]
                    spectrum_len = len(spectrum)
                    
                    min_idx = int((raman_min / SPECTRUM_MAX_WAVENUMBER) * spectrum_len)
                    max_idx = int((raman_max / SPECTRUM_MAX_WAVENUMBER) * spectrum_len)
                    min_idx = max(0, min(min_idx, spectrum_len - 1))
                    max_idx = max(min_idx + 1, min(max_idx, spectrum_len))
 
                    integrated_intensity = np.sum(spectrum[min_idx:max_idx])
                    results.append((x, y, integrated_intensity))
 
                    processed_count += 1
                    elapsed = time.time() - start_time
                    remaining = total_points - processed_count
                    
                    if processed_count > 0:
                        eta_seconds = (elapsed / processed_count) * remaining
                        hours = int(eta_seconds // 3600)
                        minutes = int((eta_seconds % 3600) // 60)
                        seconds = int(eta_seconds % 60)
                        self.eta_updated.emit(f"{hours:02}:{minutes:02}:{seconds:02}")
                    
                    progress = int((processed_count / total_points) * 100)
                    self.progress_updated.emit(progress)
 
            self.finished.emit(results)
 
        except Exception as e:
            self.error_occurred.emit(str(e))