from abc import ABC, abstractmethod
import time
from .base_device import BaseDevice


class AbstractMotorController(BaseDevice, ABC):
    """Abstract base class for motor controllers"""
    
    @abstractmethod
    def move_to(self, x: float, y: float):
        """Move motors to specified coordinates"""
        pass


class DummyMotorController(AbstractMotorController):
    """Dummy implementation of motor controller"""
    
    def __init__(self):
        super().__init__()
        self.position = [0.0, 0.0]
    
    def connect(self):
        self._is_connected = True
        return True
    
    def disconnect(self):
        self._is_connected = False
    
    def move_to(self, x: float, y: float):
        """Synchronous move to implementation"""
        time.sleep(0.001)
        self.position = [x, y]
        return True