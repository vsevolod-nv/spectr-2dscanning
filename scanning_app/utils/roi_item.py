from PyQt6.QtWidgets import QGraphicsRectItem
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPen, QBrush
from config import RECT_BORDER_WIDTH, RECT_CORNER_RADIUS


class ROIItem(QGraphicsRectItem):
    """Resizable Rectangle of Interest item"""
    
    def __init__(self, rect, parent=None):
        super().__init__(rect, parent)
        pen = QPen(Qt.GlobalColor.red, RECT_BORDER_WIDTH)
        brush = QBrush(Qt.GlobalColor.transparent)
        self.setPen(pen)
        self.setBrush(brush)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.setZValue(1)
    
    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        path = painter.clipPath()
        path.addRoundedRect(self.rect(), RECT_CORNER_RADIUS, RECT_CORNER_RADIUS)
        painter.setClipPath(path)