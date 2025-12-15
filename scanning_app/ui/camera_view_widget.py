from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QGraphicsView, 
    QGraphicsScene, QHBoxLayout, QLabel
)
from PyQt6.QtCore import Qt, QRectF, QPoint
from PyQt6.QtGui import QPixmap, QImage, QPen, QBrush, QPainter
from config import (
    MIN_WIDGET_HEIGHT, BUTTON_HEIGHT, GRAPHICS_VIEW_MIN_HEIGHT
)
from devices.camera import Camera
import numpy as np


class CustomGraphicsView(QGraphicsView):
    """Custom graphics view with pan, zoom, and mouse position tracking"""
    
    def __init__(self, scene, coord_label):
        super().__init__(scene)
        self.coord_label = coord_label
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setInteractive(True)
        self._zoom = 0
        self.setMouseTracking(True) 
        self._panning = False
        self._pan_start_pos = QPoint()
        self._selecting_roi = False
        self._roi_start_pos = QPoint()
        self._temp_rect = None
        self.roi_callback = None 
    
    def set_roi_callback(self, callback):
        """Set callback to handle ROI creation"""
        self.roi_callback = callback
    
    def mousePressEvent(self, event):
        """Handle mouse press events"""
        if event.button() == Qt.MouseButton.RightButton or event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._pan_start_pos = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        elif event.button() == Qt.MouseButton.LeftButton:
            self._selecting_roi = True
            self._roi_start_pos = event.position().toPoint()
            event.accept()
        else:
            super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Handle panning, ROI selection, and coordinate display"""

        pos = self.mapToScene(event.position().toPoint())
        self.coord_label.setText(f"X: {pos.x():.2f}, Y: {pos.y():.2f}")
        
        if self._panning:
            current_pos = event.position().toPoint()
            diff = current_pos - self._pan_start_pos
            self._pan_start_pos = current_pos
            
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - diff.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - diff.y())
        elif self._selecting_roi:
            current_pos = event.position().toPoint()
            
            if self._temp_rect:
                self.scene().removeItem(self._temp_rect)
            
            x = min(self._roi_start_pos.x(), current_pos.x())
            y = min(self._roi_start_pos.y(), current_pos.y())
            w = abs(current_pos.x() - self._roi_start_pos.x())
            h = abs(current_pos.y() - self._roi_start_pos.y())
            
            if w > 5 and h > 5:
                start_scene = self.mapToScene(self._roi_start_pos)
                current_scene = self.mapToScene(current_pos)
                
                x_scene = min(start_scene.x(), current_scene.x())
                y_scene = min(start_scene.y(), current_scene.y())
                w_scene = abs(current_scene.x() - start_scene.x())
                h_scene = abs(current_scene.y() - start_scene.y())
                
                pen = QPen(Qt.GlobalColor.red, 2)
                brush = QBrush(Qt.GlobalColor.transparent)
                self._temp_rect = self.scene().addRect(x_scene, y_scene, w_scene, h_scene, pen, brush)
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release events"""
        if (event.button() == Qt.MouseButton.RightButton or event.button() == Qt.MouseButton.MiddleButton) and self._panning:

            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        elif event.button() == Qt.MouseButton.LeftButton and self._selecting_roi:
            current_pos = event.position().toPoint()
            
            x = min(self._roi_start_pos.x(), current_pos.x())
            y = min(self._roi_start_pos.y(), current_pos.y())
            w = abs(current_pos.x() - self._roi_start_pos.x())
            h = abs(current_pos.y() - self._roi_start_pos.y())
            
            if self._temp_rect:
                self.scene().removeItem(self._temp_rect)
                self._temp_rect = None
            
            if w > 5 and h > 5:
                start_scene = self.mapToScene(self._roi_start_pos)
                current_scene = self.mapToScene(current_pos)
                
                x_scene = min(start_scene.x(), current_scene.x())
                y_scene = min(start_scene.y(), current_scene.y())
                w_scene = abs(current_scene.x() - start_scene.x())
                h_scene = abs(current_scene.y() - start_scene.y())

                if self.roi_callback:
                    self.roi_callback(QRectF(x_scene, y_scene, w_scene, h_scene))
            
            self._selecting_roi = False
            event.accept()
        else:
            super().mouseReleaseEvent(event)
    
    def wheelEvent(self, event):
        """Handle zoom with mouse wheel"""
        if event.angleDelta().y() > 0:
            factor = 1.25
            self._zoom += 1
        else:
            factor = 0.8
            self._zoom -= 1
        
        if self._zoom > 10:
            self._zoom = 10
        elif self._zoom < -10:
            self._zoom = -10
        else:
            self.scale(factor, factor)


class CameraViewWidget(QWidget):
    """Camera view widget with pan, zoom, ROI drawing, and coordinate rulers"""
    
    def __init__(self):
        super().__init__()
        self.camera = Camera()
        self.scene = QGraphicsScene()
        self.coord_label = QLabel("X: 0.00, Y: 0.00")
        self.view = CustomGraphicsView(self.scene, self.coord_label)
        self.roi_item = None
        self.zoom_factor = 1.0
        self.init_ui()

        self.load_test_image()
        
        self.view.set_roi_callback(self.handle_roi_creation)
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        button_layout = QHBoxLayout()
        self.capture_button = QPushButton("Capture Image")
        self.capture_button.setFixedHeight(BUTTON_HEIGHT)
        self.clear_roi_button = QPushButton("Clear ROI")
        self.clear_roi_button.setFixedHeight(BUTTON_HEIGHT)
        self.zoom_in_button = QPushButton("+")
        self.zoom_in_button.setFixedWidth(40)
        self.zoom_out_button = QPushButton("-")
        self.zoom_out_button.setFixedWidth(40)
        
        button_layout.addWidget(self.capture_button)
        button_layout.addWidget(self.clear_roi_button)
        button_layout.addWidget(self.zoom_in_button)
        button_layout.addWidget(self.zoom_out_button)
        button_layout.addStretch()

        coord_layout = QHBoxLayout()
        coord_layout.addWidget(QLabel("Mouse Position:"))
        coord_layout.addWidget(self.coord_label)
        coord_layout.addStretch()

        self.view.setMinimumHeight(GRAPHICS_VIEW_MIN_HEIGHT)
        self.view.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        layout.addLayout(button_layout)
        layout.addLayout(coord_layout)
        layout.addWidget(self.view)
        
        self.setLayout(layout)

        self.capture_button.clicked.connect(self.on_capture_clicked)
        self.clear_roi_button.clicked.connect(self.clear_roi)
        self.zoom_in_button.clicked.connect(self.zoom_in)
        self.zoom_out_button.clicked.connect(self.zoom_out)
    
    def handle_roi_creation(self, rect):
        """Handle ROI creation from view"""
        self.add_roi(rect)
    
    def zoom_in(self):
        """Zoom in the view"""
        self.view.scale(1.25, 1.25)
        self.zoom_factor *= 1.25
    
    def zoom_out(self):
        """Zoom out the view"""
        self.view.scale(0.8, 0.8)
        self.zoom_factor *= 0.8
    
    def reset_zoom(self):
        """Reset zoom level"""
        self.view.resetTransform()
        self.view.scale(self.zoom_factor, self.zoom_factor)
    
    def load_test_image(self):
        """Load a sample test image"""

        width, height = 800, 600
        data = np.zeros((height, width, 3), dtype=np.uint8)
    
        for y in range(height):
            for x in range(width):
                data[y, x, 0] = (x * 255 // width) % 256 
                data[y, x, 1] = (y * 255 // height) % 256
                data[y, x, 2] = ((x + y) * 255 // (width + height)) % 256
        
        image = QImage(data.tobytes(), width, height, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(image)
        self.scene.clear()
        self.scene.addPixmap(pixmap)
        self.view.setSceneRect(self.scene.itemsBoundingRect())
    
    def on_capture_clicked(self):
        if self.camera.is_connected:
            image = self.camera.capture_image()
            pixmap = QPixmap.fromImage(image)
            self.scene.clear()
            self.scene.addPixmap(pixmap)
            self.view.setSceneRect(self.scene.itemsBoundingRect())
    
    def add_roi(self, rect):
        if self.roi_item:
            self.scene.removeItem(self.roi_item)
        
        pen = QPen(Qt.GlobalColor.red, 2)
        brush = QBrush(Qt.GlobalColor.transparent)
        self.roi_item = self.scene.addRect(rect, pen, brush)
        print(f"ROI added: X={rect.left():.2f}, Y={rect.top():.2f}, "
              f"W={rect.width():.2f}, H={rect.height():.2f}")
    
    def clear_roi(self):
        if self.roi_item:
            self.scene.removeItem(self.roi_item)
            self.roi_item = None
    
    def get_roi_rect(self):
        if self.roi_item:
            return self.roi_item.rect()
        return None