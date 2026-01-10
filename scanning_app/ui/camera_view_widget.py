from typing import Optional

import numpy as np
import pyqtgraph as pg
from loguru import logger
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import QBuffer, QIODevice, QRectF, pyqtSignal

from devices.camera.base_camera import BaseCamera

MIN_ROI_SIZE = 5
DEFAULT_IMAGE_WIDTH = 1280
DEFAULT_IMAGE_HEIGHT = 1024


class CameraViewWidget(QtWidgets.QWidget):
    roi_changed = pyqtSignal(QRectF)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.camera: Optional[BaseCamera] = None
        self.roi = None
        self.drag_start = None
        self._temp_roi = None

        self.default_width = DEFAULT_IMAGE_WIDTH
        self.default_height = DEFAULT_IMAGE_HEIGHT

        self._setup_ui()
        self._setup_crosshair()
        self._show_no_image()

    def _setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.plot = pg.PlotWidget()
        self.plot.setAspectLocked(True)
        self.plot.showAxes(True, showValues=True)
        self.plot.showGrid(x=True, y=True, alpha=0.3)
        self.plot.setBackground("w")
        self.plot.getViewBox().setMouseMode(pg.ViewBox.PanMode)

        self.image_item = pg.ImageItem(axisOrder="row-major")
        self.plot.addItem(self.image_item)

        self.text_item = pg.TextItem(
            text="No photo taken\nConnect Camera -> Capture",
            color=(200, 200, 200),
            anchor=(0.5, 0.5),
        )
        self.plot.addItem(self.text_item)

        self.border_item = QtWidgets.QGraphicsRectItem(
            0,
            0,
            self.default_width,
            self.default_height,
        )
        self.border_item.setPen(
            pg.mkPen("w", width=1, style=QtCore.Qt.PenStyle.DashLine)
        )
        self.plot.addItem(self.border_item)

        self.coord_label = QtWidgets.QLabel("X: 0.00, Y: 0.00")
        self.coord_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.coord_label.setStyleSheet("font-weight: bold; color: #555;")

        layout.addWidget(self.plot)
        layout.addWidget(self.coord_label)

        self.plot.scene().installEventFilter(self)
        self.plot.scene().sigMouseMoved.connect(self._on_mouse_move)

    def _setup_crosshair(self):
        pen = pg.mkPen(
            color=(255, 255, 255, 100),
            width=1,
            style=QtCore.Qt.PenStyle.DashLine,
        )
        self.v_line = pg.InfiniteLine(angle=90, movable=False, pen=pen)
        self.h_line = pg.InfiniteLine(angle=0, movable=False, pen=pen)
        self.plot.addItem(self.v_line, ignoreBounds=True)
        self.plot.addItem(self.h_line, ignoreBounds=True)

    def _show_no_image(self):
        self.image_item.clear()
        self.text_item.show()
        self.border_item.show()
        self.plot.getViewBox().setRange(
            QRectF(0, 0, self.default_width, self.default_height),
            padding=0,
        )
        self.plot.getViewBox().invertY(True)

    def _hide_no_image(self):
        self.text_item.hide()
        self.border_item.hide()

    def eventFilter(self, source, event):
        if event.type() == QtCore.QEvent.Type.GraphicsSceneMousePress:
            if event.button() == QtCore.Qt.MouseButton.LeftButton:
                pos = event.scenePos()
                view_box = self.plot.getViewBox()
                if view_box.sceneBoundingRect().contains(pos):
                    self.drag_start = view_box.mapSceneToView(pos)
                    return True

        if event.type() == QtCore.QEvent.Type.GraphicsSceneMouseRelease:
            if event.button() == QtCore.Qt.MouseButton.LeftButton and self.drag_start:
                pos = event.scenePos()
                view_box = self.plot.getViewBox()
                mouse_point = view_box.mapSceneToView(pos)
                self._finalize_roi(mouse_point)
                self.drag_start = None

                if self._temp_roi:
                    self.plot.removeItem(self._temp_roi)
                    self._temp_roi = None

                return True

        return super().eventFilter(source, event)

    def _on_mouse_move(self, pos):
        view_box = self.plot.getViewBox()
        if not view_box or not view_box.sceneBoundingRect().contains(pos):
            self.coord_label.setText("X: ---, Y: ---")
            return

        mouse_point = view_box.mapSceneToView(pos)
        x = mouse_point.x()
        y = mouse_point.y()

        self.v_line.setPos(x)
        self.h_line.setPos(y)
        self.coord_label.setText(f"X: {x:.1f}, Y: {y:.1f}")

        if self.drag_start:
            self._update_temp_roi(mouse_point)

    def _update_temp_roi(self, current_point):
        x0 = self.drag_start.x()
        y0 = self.drag_start.y()
        x1 = current_point.x()
        y1 = current_point.y()

        x = min(x0, x1)
        y = min(y0, y1)
        w = abs(x1 - x0)
        h = abs(y1 - y0)

        if w < 1 or h < 1:
            return

        if self._temp_roi is None:
            self._temp_roi = pg.RectROI(
                [x, y],
                [w, h],
                pen=pg.mkPen(
                    "y",
                    width=1,
                    style=QtCore.Qt.PenStyle.DashLine,
                ),
                movable=False,
                resizable=False,
            )
            self.plot.addItem(self._temp_roi)
        else:
            self._temp_roi.setPos([x, y])
            self._temp_roi.setSize([w, h])

    def _finalize_roi(self, current_point):
        x0 = self.drag_start.x()
        y0 = self.drag_start.y()
        x1 = current_point.x()
        y1 = current_point.y()

        x = min(x0, x1)
        y = min(y0, y1)
        w = abs(x1 - x0)
        h = abs(y1 - y0)

        if w > MIN_ROI_SIZE and h > MIN_ROI_SIZE:
            self.add_roi(QRectF(x, y, w, h))

    def set_image(self, qimage: QtGui.QImage):
        if qimage is None or qimage.isNull():
            self._show_no_image()
            return

        if qimage.format() != QtGui.QImage.Format.Format_RGB32:
            qimage = qimage.convertToFormat(QtGui.QImage.Format.Format_RGB32)

        self._display_qimage = qimage.copy()

        width = qimage.width()
        height = qimage.height()

        ptr = qimage.constBits()
        ptr.setsize(height * width * 4)
        arr = np.frombuffer(ptr, dtype=np.uint8).reshape(height, width, 4)
        rgb_arr = arr[..., :3].copy()

        self.image_item.setImage(rgb_arr, autoLevels=False)

        logger.debug("Image set in image_item, size %s", rgb_arr.shape)

        self._hide_no_image()
        self.plot.getViewBox().setRange(QRectF(0, 0, width, height), padding=0)
        self.plot.getViewBox().invertY(True)

    def add_roi(self, rect: QRectF):
        self.clear_roi()

        self.roi = pg.RectROI(
            [rect.x(), rect.y()],
            [rect.width(), rect.height()],
            pen=pg.mkPen(color="r", width=2),
            rotatable=False,
            resizable=True,
        )
        self.roi.addScaleHandle([1, 1], [0, 0])
        self.roi.addScaleHandle([0, 0], [1, 1])
        self.roi.sigRegionChanged.connect(self._on_roi_changed)

        self.plot.addItem(self.roi)
        self.roi_changed.emit(rect)

    def clear_roi(self):
        if self.roi:
            try:
                self.plot.removeItem(self.roi)
            except RuntimeError:
                pass
            self.roi = None

    def get_roi_rect(self) -> QRectF | None:
        if self.roi is None:
            return None

        pos = self.roi.pos()
        size = self.roi.size()

        x = float(pos.x())
        y = float(pos.y())
        w = float(size.x())
        h = float(size.y())

        img_h = self.image_item.image.shape[0]
        y_flipped = img_h - (y + h)

        return QRectF(x, y_flipped, w, h)

    def _on_roi_changed(self):
        if self.roi:
            self.roi_changed.emit(self.roi.parentBounds())

    def export_raw_png(self) -> bytes:
        if not hasattr(self, "_display_qimage") or self._display_qimage.isNull():
            return b""

        image = self._display_qimage

        if self.roi is not None:
            roi_rect = self.get_roi_rect()
            if roi_rect is not None:
                x = int(round(roi_rect.x()))
                y = int(round(roi_rect.y()))
                w = int(round(roi_rect.width()))
                h = int(round(roi_rect.height()))

                x = max(0, min(x, image.width() - 1))
                y = max(0, min(y, image.height() - 1))
                w = min(w, image.width() - x)
                h = min(h, image.height() - y)

                image = image.copy(x, y, w, h)

        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(buffer, "PNG")
        return bytes(buffer.data())

    def export_overview_png(self) -> bytes:
        if not hasattr(self, "_display_qimage") or self._display_qimage.isNull():
            return b""

        image = self._display_qimage.copy()
        painter = QtGui.QPainter(image)

        if self.roi is not None:
            roi_rect = self.get_roi_rect()
            if roi_rect is not None:
                pen = QtGui.QPen(QtGui.QColor("red"))
                pen.setWidth(3)
                painter.setPen(pen)
                painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
                painter.drawRect(roi_rect)

        painter.end()

        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(buffer, "PNG")
        return bytes(buffer.data())
