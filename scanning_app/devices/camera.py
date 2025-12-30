from .base_device import BaseDevice
from PyQt6.QtGui import QImage
import numpy as np
from . import toupcam
import ctypes
import time
from config import (
    TOUPCAM_AUTO_EXPO_ENABLED,
    TOUPCAM_DEFAULT_EXPO_TIME_US,
    TOUPCAM_DEFAULT_EXPO_AGAIN,
    TOUPCAM_SNAP_WAIT_SECONDS,
    TOUPCAM_PIXEL_FORMAT_BITS,
    TOUPCAM_IMAGE_FORMAT,
)


class ToupCamCamera(BaseDevice):
    def __init__(self):
        super().__init__()
        self.hcam = None
        self._w = 0
        self._h = 0
        self._has_captured = False

    def list_cameras(self):
        try:
            arr = toupcam.Toupcam.EnumV2()
            return [info.displayname for info in arr]
        except Exception:
            return []

    def connect_by_name(self, name: str):
        if self.hcam:
            self.disconnect()
        try:
            arr = toupcam.Toupcam.EnumV2()
            for info in arr:
                if info.displayname == name:
                    self.hcam = toupcam.Toupcam.Open(info.id)
                    if self.hcam:
                        self._w, self._h = self.hcam.get_Size()
                        self.hcam.put_AutoExpoEnable(int(TOUPCAM_AUTO_EXPO_ENABLED))
                        self.hcam.put_ExpoTime(TOUPCAM_DEFAULT_EXPO_TIME_US)
                        self.hcam.put_ExpoAGain(TOUPCAM_DEFAULT_EXPO_AGAIN)
                        self._is_connected = True
                        self._has_captured = False
                        return True
        except Exception:
            pass
        return False

    def connect(self):
        cams = self.list_cameras()
        if cams:
            return self.connect_by_name(cams[0])
        return False

    def disconnect(self):
        if self.hcam:
            self.hcam.Close()
            self.hcam = None
        self._is_connected = False
        self._has_captured = False

    def capture_image(self):
        if not self.hcam:
            raise RuntimeError("Camera not connected")

        self.hcam.StartPullModeWithCallback(lambda *args: None, None)
        self.hcam.Snap(0)
        time.sleep(TOUPCAM_SNAP_WAIT_SECONDS)

        buf = ctypes.create_string_buffer(self._w * self._h * 3)
        self.hcam.PullStillImageV2(buf, TOUPCAM_PIXEL_FORMAT_BITS, None)

        arr = np.frombuffer(buf, dtype=np.uint8).reshape((self._h, self._w, 3))
        arr = np.flipud(arr).copy()
        self._has_captured = True

        format_enum = getattr(QImage.Format, f"Format_{TOUPCAM_IMAGE_FORMAT}")
        return QImage(arr.tobytes(), self._w, self._h, format_enum)

    def has_captured(self):
        return self._has_captured