from .base_device import BaseDevice
import numpy as np
from config import (
    SPECTRUM_WAVELENGTH_START,
    SPECTRUM_WAVELENGTH_END,
    SPECTRUM_NUM_POINTS,
    SPECTRUM_NOISE_FLOOR,
)
from loguru import logger


class Spectrometer(BaseDevice):
    def __init__(self):
        super().__init__()
        self.wavelength_range = np.linspace(
            SPECTRUM_WAVELENGTH_START,
            SPECTRUM_WAVELENGTH_END,
            SPECTRUM_NUM_POINTS,
        )

    def connect(self) -> bool:
        self._is_connected = True
        logger.info("Spectrometer connected")
        return True

    def disconnect(self) -> None:
        self._is_connected = False
        logger.info("Spectrometer disconnected")

    def capture_spectrum(self) -> np.ndarray:
        spectrum = np.random.rand(len(self.wavelength_range)) + SPECTRUM_NOISE_FLOOR
        logger.debug("Spectrum captured")
        return spectrum
