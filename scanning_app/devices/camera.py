import os
from PyQt6.QtGui import QImage
from PyQt6.QtCore import QObject, pyqtSignal
from loguru import logger

HARDCODED_IMAGE_PATH = r"C:\projects\spectr-2dscanning\scanning_app\devices\cow.jpg"


class CameraError(Exception):
    pass


class DummyCamera(QObject):
    connected = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.is_connected = False
        self.name = "Simulated Dummy Camera"
        self.hcam = self._MockHandle()

    class _MockHandle:
        def put_ExpoTime(self, val):
            logger.debug(f"[Dummy Camera] Exposure time set to: {val}")

        def put_ExpoAGain(self, val):
            logger.debug(f"[Dummy Camera] Gain set to: {val}")

    def list_cameras(self):
        return ["Simulated Dummy Camera - Default"]

    def connect(self):
        self.is_connected = True
        self.connected.emit(True)
        logger.info(
            f"[Dummy Camera] Connected. Looking for image at: {HARDCODED_IMAGE_PATH}"
        )
        return True

    def connect_by_name(self, name):
        return self.connect()

    def disconnect(self):
        self.is_connected = False
        self.connected.emit(False)
        logger.info("[Dummy Camera] Disconnected.")

    def capture_image(self) -> QImage:
        if not self.is_connected:
            raise CameraError("Camera not connected")

        if not os.path.exists(HARDCODED_IMAGE_PATH):
            raise CameraError(f"Dummy image file not found: {HARDCODED_IMAGE_PATH}")

        image = QImage(HARDCODED_IMAGE_PATH)
        if image.isNull():
            raise CameraError(
                f"Failed to load dummy image from: {HARDCODED_IMAGE_PATH}"
            )

        converted_image = image.convertToFormat(QImage.Format.Format_RGB32)
        if converted_image.isNull():
            raise CameraError(
                f"Failed to convert dummy image to RGB32: {HARDCODED_IMAGE_PATH}"
            )

        logger.debug(
            f"[Dummy Camera] Successfully loaded and converted image: {HARDCODED_IMAGE_PATH}"
        )
        return converted_image

    def has_captured(self):
        return self.is_connected
