import ctypes
import numpy as np
from PyQt6.QtGui import QImage
from loguru import logger

import devices.camera.toupcam as toupcam
from .base_camera import BaseCamera

def _dummy_event_cb(n_event, ctx):
    pass

class ToupcamCamera(BaseCamera):
    def __init__(self, model):
        self._model = model
        self._hcam = None
        self._connected = False

        self._width = 0
        self._height = 0

        self._last_frame: QImage | None = None

        self._exposure_us = 10_000
        self._gain = 100

    def connect(self) -> None:
        logger.info(f"Opening Toupcam: {self._model.displayname}")

        self._hcam = toupcam.Toupcam.Open(self._model.id)
        if not self._hcam:
            raise RuntimeError("Failed to open Toupcam")

        self._width, self._height = self._hcam.get_Size()

        self._hcam.put_AutoExpoEnable(0)
        self._hcam.put_ExpoTime(self._exposure_us)
        self._hcam.put_ExpoAGain(self._gain)

        self._hcam.StartPullModeWithCallback(_dummy_event_cb, None)

        self._connected = True
        logger.info(
            "Toupcam connected (%dx%d)",
            self._width,
            self._height,
        )

    def disconnect(self) -> None:
        if self._hcam:
            self._hcam.Close()

        self._hcam = None
        self._connected = False
        self._last_frame = None

        logger.info("Toupcam disconnected")

    def is_connected(self) -> bool:
        return self._connected

    def capture(self) -> QImage:
        if not self._connected or not self._hcam:
            raise RuntimeError("Camera not connected")

        buf = ctypes.create_string_buffer(
            self._width * self._height * 3
        )

        self._hcam.PullImageV2(buf, 24, None)

        arr = np.frombuffer(buf, dtype=np.uint8).reshape(
            (self._height, self._width, 3)
        )

        qimg = QImage(
            arr.data,
            self._width,
            self._height,
            self._width * 3,
            QImage.Format.Format_RGB888,
        ).convertToFormat(QImage.Format.Format_RGB32)

        return qimg.copy()

    def set_exposure(self, value: int) -> None:
        self._exposure_us = int(value)
        if self._hcam:
            self._hcam.put_ExpoTime(self._exposure_us)

    def set_gain(self, value: int) -> None:
        self._gain = int(value)
        if self._hcam:
            self._hcam.put_ExpoAGain(self._gain)
