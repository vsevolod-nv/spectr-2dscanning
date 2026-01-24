import ctypes
import time
import numpy as np

from PyQt6.QtGui import QImage
from loguru import logger

import toupcam

from config import (
    TOUPCAM_AUTO_EXPO_ENABLED,
    TOUPCAM_DEFAULT_EXPO_TIME_US,
    TOUPCAM_DEFAULT_EXPO_AGAIN,
    TOUPCAM_SNAP_WAIT_SECONDS,
    TOUPCAM_PIXEL_FORMAT_BITS,
)

from .base_camera import BaseCamera


class ToupcamCamera(BaseCamera):
    def __init__(self):
        self._hcam = None
        self._connected = False

        self._width = None
        self._height = None

        self._exposure = TOUPCAM_DEFAULT_EXPO_TIME_US
        self._gain = TOUPCAM_DEFAULT_EXPO_AGAIN

    def connect(self) -> None:
        logger.info("Opening Toupcam camera")

        self._hcam = toupcam.Toupcam.Open(None)
        if not self._hcam:
            raise RuntimeError("Failed to open Toupcam camera")

        self._width, self._height = self._hcam.get_Size()

        self._hcam.put_AutoExpoEnable(
            1 if TOUPCAM_AUTO_EXPO_ENABLED else 0
        )
        self._hcam.put_ExpoTime(self._exposure)
        self._hcam.put_ExpoAGain(self._gain)

        self._hcam.StartPullModeWithCallback(None, None)

        self._connected = True
        logger.info(
            "Toupcam connected (%dx%d)", self._width, self._height
        )

    def disconnect(self) -> None:
        if self._hcam:
            logger.info("Closing Toupcam camera")
            self._hcam.Close()

        self._hcam = None
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def set_exposure(self, value: int) -> None:
        self._exposure = int(value)
        if self._hcam:
            self._hcam.put_ExpoTime(self._exposure)
        logger.debug("Toupcam exposure set to %d µs", value)

    def set_gain(self, value: int) -> None:
        self._gain = int(value)
        if self._hcam:
            self._hcam.put_ExpoAGain(self._gain)
        logger.debug("Toupcam gain set to %d", value)

    def capture(self) -> QImage:
        if not self._connected or not self._hcam:
            raise RuntimeError("Toupcam not connected")

        logger.debug("Toupcam snap requested")

        self._hcam.Snap(0)
        time.sleep(TOUPCAM_SNAP_WAIT_SECONDS)

        buf = ctypes.create_string_buffer(
            self._width * self._height * 3
        )

        self._hcam.PullStillImageV2(
            buf,
            TOUPCAM_PIXEL_FORMAT_BITS,
            None,
        )

        arr = np.frombuffer(
            buf, dtype=np.uint8
        ).reshape((self._height, self._width, 3))

        qimage = QImage(
            arr.data,
            self._width,
            self._height,
            self._width * 3,
            QImage.Format.Format_RGB888,
        ).convertToFormat(QImage.Format.Format_RGB32)

        logger.debug("Toupcam image captured")

        return qimage.copy()
