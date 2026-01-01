from config import DEBUG


class DeviceFactory:
    def available_cameras(self) -> list[str]:
        devices: list[str] = []
        if DEBUG:
            devices.append("Dummy Camera")
        return devices

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

    def create_camera(self, name: str):
        if name == "Dummy Camera" and DEBUG:
            from devices.camera.dummy_camera import DummyCamera

            return DummyCamera()
        raise ValueError(f"Unknown camera: {name}")

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
