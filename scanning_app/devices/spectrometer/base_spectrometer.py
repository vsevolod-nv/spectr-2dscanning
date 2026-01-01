from abc import ABC, abstractmethod
import numpy as np


class BaseSpectrometer(ABC):
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
    def acquire_spectrum(self) -> tuple[np.ndarray, np.ndarray]:
        ...
