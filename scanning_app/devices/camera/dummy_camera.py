from pathlib import Path

from loguru import logger
from PyQt6.QtGui import QImage

from .base_camera import BaseCamera


class DummyCamera(BaseCamera):
    def __init__(self, image_path: str | Path | None = None):
        self._connected = False

        if image_path is None:
            self._image_path = Path(__file__).parent / "cow.jpg"
        else:
            self._image_path = Path(image_path)

        self._image_path = self._image_path.resolve()
        logger.info(f"Using dummy image: {self._image_path}")

    def connect(self) -> None:
        self._connected = True
        logger.info("Dummy camera connected")

    def disconnect(self) -> None:
        self._connected = False
        logger.info("Dummy camera disconnected")

    def is_connected(self) -> bool:
        return self._connected

    def capture(self) -> QImage:
        image = QImage(str(self._image_path))
        if image.isNull():
            raise RuntimeError(f"Failed to load dummy image: {self._image_path}")

        return image

    def set_exposure(self, value: int) -> None:
        logger.debug(f"Dummy camera exposure set to {value}")

    def set_gain(self, value: int) -> None:
        logger.debug(f"Dummy camera gain set to {value}")
