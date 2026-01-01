import time

import numpy as np
from loguru import logger

from config import (
    SPECTRUM_NOISE_FLOOR,
    SPECTRUM_NUM_POINTS,
    SPECTRUM_WAVELENGTH_END,
    SPECTRUM_WAVELENGTH_START,
)
from .base_spectrometer import BaseSpectrometer


class DummySpectrometer(BaseSpectrometer):
    def __init__(self):
        self._connected = False

        self.wavelengths = np.linspace(
            SPECTRUM_WAVELENGTH_START,
            SPECTRUM_WAVELENGTH_END,
            SPECTRUM_NUM_POINTS,
        )

        self._peaks = [
            (520, 1.0, 25),
            (1000, 0.7, 40),
            (1600, 0.5, 35),
        ]

        logger.info("Dummy spectrometer initialized")

    def connect(self) -> None:
        self._connected = True
        logger.info("Dummy spectrometer connected")

    def disconnect(self) -> None:
        self._connected = False
        logger.info("Dummy spectrometer disconnected")

    def is_connected(self) -> bool:
        return self._connected

    def acquire_spectrum(self) -> tuple[np.ndarray, np.ndarray]:
        if not self._connected:
            raise RuntimeError("Spectrometer not connected")

        time.sleep(0.02)

        intensities = np.zeros_like(self.wavelengths)

        for center, amplitude, width in self._peaks:
            jitter = np.random.normal(0, 2.0)
            intensities += amplitude * np.exp(
                -((self.wavelengths - (center + jitter)) ** 2) / (2 * width**2)
            )

        noise = np.random.normal(
            loc=SPECTRUM_NOISE_FLOOR,
            scale=0.03,
            size=len(self.wavelengths),
        )
        intensities += noise

        intensities = np.clip(intensities, 0, None)

        logger.debug("Dummy spectrum acquired")

        return self.wavelengths, intensities
