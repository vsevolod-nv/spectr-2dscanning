from config import DEBUG
import devices.camera.toupcam as toupcam


class DeviceFactory:
    def __init__(self):
        self._toupcam_models: dict[str, toupcam.ToupcamModel] = {}

    def available_cameras(self) -> list[str]:
        devices = []

        if DEBUG:
            devices.append("Dummy Camera")

        self._toupcam_models.clear()

        try:
            for cam in toupcam.Toupcam.EnumV2():
                ui_name = f"Toupcam: {cam.displayname}"
                devices.append(ui_name)
                self._toupcam_models[ui_name] = cam
        except Exception:
            pass

        return devices

    def create_camera(self, name: str):
        if name == "Dummy Camera" and DEBUG:
            from devices.camera.dummy_camera import DummyCamera
            return DummyCamera()

        if name in self._toupcam_models:
            from devices.camera.toupcam_camera import ToupcamCamera
            return ToupcamCamera(self._toupcam_models[name])

        raise ValueError(f"Unknown camera: {name}")

    def available_spectrometers(self) -> list[str]:
        devices: list[str] = []
        if DEBUG:
            devices.append("Dummy Spectrometer")
        return devices

    def available_motors(self) -> list[str]:
        devices: list[str] = []
        if DEBUG:
            devices.append("Dummy Motor Controller")
        return devices

    def create_spectrometer(self, name: str):
        if name == "Dummy Spectrometer" and DEBUG:
            from devices.spectrometer.dummy_spectrometer import DummySpectrometer

            return DummySpectrometer()
        raise ValueError(f"Unknown spectrometer: {name}")

    def create_motors(self, name: str):
        if name == "Dummy Motor Controller" and DEBUG:
            from devices.motors.dummy_motor_controller import DummyMotorController

            return DummyMotorController()
        raise ValueError(f"Unknown motor controller: {name}")
