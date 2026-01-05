from PyQt6.QtCore import QThread, pyqtSignal


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
