from abc import ABC, abstractmethod
from time import sleep

from loguru import logger

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
        logger.info("Dummy motor controller connected")
        return True

    def disconnect(self) -> None:
        self._is_connected = False
        logger.info("Dummy motor controller disconnected")

    def move_to(self, x: float, y: float) -> bool:
        logger.debug(f"Moving dummy motor to ({x}, {y})")
        sleep(DUMMY_MOTOR_MOVE_DELAY_SEC)
        self.position = [x, y]
        logger.debug(f"Dummy motor reached position ({x}, {y})")
        return True
