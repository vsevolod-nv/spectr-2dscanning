from .base_device import BaseDevice
from PyQt6.QtGui import QImage
import numpy as np


class Camera(BaseDevice):
    """Camera device stub"""
    
    def __init__(self):
        super().__init__()
        self.image_width = 800
        self.image_height = 600
        self.image_format = QImage.Format.Format_RGB888
    
    def connect(self):
        self._is_connected = True
        return True
    
    def disconnect(self):
        self._is_connected = False
    
    def capture_image(self):
        """Return a dummy QImage"""
        width = self.image_width
        height = self.image_height
        
        data = np.zeros((height, width, 3), dtype=np.uint8)
        
        for y in range(height):
            for x in range(width):
                data[y, x, 0] = (x * 255 // width) % 256 
                data[y, x, 1] = (y * 255 // height) % 256 
                data[y, x, 2] = ((x + y) * 255 // (width + height)) % 256
        
        image = QImage(data.tobytes(), width, height, self.image_format)
        
        return image