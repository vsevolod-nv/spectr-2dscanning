from abc import ABC, abstractmethod
from PyQt6.QtGui import QImage


class BaseCamera(ABC):
    @abstractmethod
    def connect(self) -> None:
        ...

    @abstractmethod
    def disconnect(self) -> None:
        ...

    @abstractmethod
    def is_connected(self) -> bool:
        ...

    @abstractmethod
    def capture(self) -> QImage:
        ...

    @abstractmethod
    def set_exposure(self, value: int) -> None:
        ...

    @abstractmethod
    def set_gain(self, value: int) -> None:
        ...
