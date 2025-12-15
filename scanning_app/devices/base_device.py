from abc import ABC, abstractmethod


class BaseDevice(ABC):
    
    def __init__(self):
        self._is_connected = False
    
    @property
    def is_connected(self):
        return self._is_connected
    
    @abstractmethod
    def connect(self):
        pass
    
    @abstractmethod
    def disconnect(self):
        pass