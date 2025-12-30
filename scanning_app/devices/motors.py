from abc import ABC, abstractmethod
import time
from .base_device import BaseDevice
from config import DUMMY_MOTOR_MOVE_DELAY_SEC


class AbstractMotorController(BaseDevice, ABC):
    @abstractmethod
    def move_to(self, x: float, y: float) -> bool:
        pass


class DummyMotorController(AbstractMotorController):
    def __init__(self):
        super().__init__()
        self.position = [0.0, 0.0]

    def connect(self) -> bool:
        self._is_connected = True
        return True

    def disconnect(self) -> None:
        self._is_connected = False

    def move_to(self, x: float, y: float) -> bool:
        time.sleep(DUMMY_MOTOR_MOVE_DELAY_SEC)
        self.position = [x, y]
        return True