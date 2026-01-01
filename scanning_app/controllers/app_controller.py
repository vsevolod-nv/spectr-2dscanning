from devices.device_factory import DeviceFactory
from devices.scan_worker import ScanPoint, ScanWorker


class AppController:
    def __init__(self):
        self.device_factory = DeviceFactory()

        self.camera = None
        self.spectrometer = None
        self.motors = None

        self.scan_worker: ScanWorker | None = None
        self.last_scan: list[ScanPoint] | None = None

    def list_cameras(self) -> list[str]:
        return self.device_factory.available_cameras()

    def list_spectrometers(self) -> list[str]:
        return self.device_factory.available_spectrometers()

    def list_motors(self) -> list[str]:
        return self.device_factory.available_motors()

    def connect_camera(self, name: str) -> None:
        self.camera = self.device_factory.create_camera(name)
        self.camera.connect()

    def connect_spectrometer(self, name: str) -> None:
        self.spectrometer = self.device_factory.create_spectrometer(name)
        self.spectrometer.connect()

    def connect_motors(self, name: str) -> None:
        self.motors = self.device_factory.create_motors(name)
        self.motors.connect()

    def disconnect_camera(self) -> None:
        if self.camera:
            self.camera.disconnect()
        self.camera = None

    def disconnect_spectrometer(self) -> None:
        if self.spectrometer:
            self.spectrometer.disconnect()
        self.spectrometer = None

    def disconnect_motors(self) -> None:
        if self.motors:
            self.motors.disconnect()
        self.motors = None

    def start_scan(self, roi_rect, scan_params) -> ScanWorker:
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

    def stop_scan(self) -> None:
        if self.scan_worker:
            self.scan_worker.stop()
            self.scan_worker = None
