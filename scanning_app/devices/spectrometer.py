from .base_device import BaseDevice
import numpy as np


class Spectrometer(BaseDevice):
    """Spectrometer device stub"""
    
    def __init__(self):
        super().__init__()
        self.wavelength_range = np.linspace(0, 4000, 1000)
    
    def connect(self):
        self._is_connected = True
        return True
    
    def disconnect(self):
        self._is_connected = False
    
    def capture_spectrum(self):
        """Return a dummy spectrum array"""
        spectrum = np.random.rand(len(self.wavelength_range)) + 0.1
        return spectrum