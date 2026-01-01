import time
from loguru import logger
from config import MOTOR_SETTLE_TIME_SEC
from .base_motor_controller import BaseMotorController


class DummyMotorController(BaseMotorController):
    def __init__(self):
        self._connected = False
        self.position = (0.0, 0.0)

    def connect(self) -> None:
        self._connected = True
        logger.info("Dummy motor controller connected")

    def disconnect(self) -> None:
        self._connected = False
        logger.info("Dummy motor controller disconnected")

    def is_connected(self) -> bool:
        return self._connected

    def move_to(self, x: float, y: float) -> None:
        if not self._connected:
            raise RuntimeError("Motor controller not connected")
        time.sleep(MOTOR_SETTLE_TIME_SEC)
        self.position = (x, y)
        # logger.debug(f"Dummy motor reached ({x:.3f}, {y:.3f})")
