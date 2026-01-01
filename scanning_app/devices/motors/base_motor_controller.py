from abc import ABC, abstractmethod


class BaseMotorController(ABC):
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
    def move_to(self, x: float, y: float) -> None:
        ...
