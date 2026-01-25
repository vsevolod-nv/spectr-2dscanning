from enum import Enum, auto


class ScanMode(Enum):
    IDLE = auto()
    SCANNING = auto()
    VIEWER = auto()


class AppState:
    def __init__(self):
        self.scan_mode = ScanMode.IDLE
        self.spectra_live = False
        self.selected_point = None

    @property
    def is_scanning(self) -> bool:
        return self.scan_mode == ScanMode.SCANNING

    @property
    def is_viewer(self) -> bool:
        return self.scan_mode == ScanMode.VIEWER

    @property
    def can_go_live(self) -> bool:
        return self.is_scanning and not self.spectra_live
