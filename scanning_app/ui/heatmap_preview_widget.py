import io

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from config import HEATMAP_CMAP, PLOT_DPI, RAMAN_MAX_LIMIT, RAMAN_MIN_LIMIT


class HeatmapPreviewWidget(QWidget):
    scan_point_selected = pyqtSignal(object)

    def __init__(self):
        super().__init__()

        self.fig = Figure(dpi=PLOT_DPI, facecolor="#fafafa")
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)

        self._fallback_label = QLabel("")
        self._fallback_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._fallback_label.setStyleSheet("color:#777;font-size:12px;")
        self._fallback_label.hide()

        self._raman_min = RAMAN_MIN_LIMIT
        self._raman_max = RAMAN_MAX_LIMIT

        self._xs = []
        self._ys = []
        self._z = None
        self._im = None
        self._grid_points = None
        self._source_points = []

        self._colorbar = None
        self._has_2d_heatmap = False

        self._init_ui()
        self._show_qt_message("No Scan Data")

        self.canvas.mpl_connect("button_press_event", self._on_click)
        self.canvas.mpl_connect("motion_notify_event", self._on_mouse_move)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self.canvas)
        layout.addWidget(self._fallback_label)

    def _show_qt_message(self, text: str):
        self.canvas.hide()
        self._fallback_label.setText(text)
        self._fallback_label.show()
        self._has_2d_heatmap = False

    def _show_matplotlib(self):
        self._fallback_label.hide()
        self.canvas.show()

    def initialize_grid(self, points):
        self._grid_points = None
        self._z = None
        self._im = None
        self._remove_colorbar()
        self.ax.clear()
        self._has_2d_heatmap = False

        if not points:
            self._show_qt_message("No Scan Data")
            return

        self._xs = sorted({p.x for p in points})
        self._ys = sorted({p.y for p in points})

        if len(self._xs) < 2 or len(self._ys) < 2:
            self._show_qt_message("Line / sparse scan\n(no 2D heatmap)")
            return

        self._z = np.full((len(self._ys), len(self._xs)), np.nan)
        self._grid_points = [[None for _ in self._xs] for _ in self._ys]

        self._im = self.ax.imshow(
            self._z,
            cmap=HEATMAP_CMAP,
            origin="lower",
            aspect="auto",
            extent=self._compute_extent(),
        )

        cmap = self._im.get_cmap().copy()
        cmap.set_bad(alpha=0.0)
        self._im.set_cmap(cmap)

        self.ax.set_xlabel("X (µm)")
        self.ax.set_ylabel("Y (µm)")
        self._update_title()

        self._colorbar = self.fig.colorbar(self._im, ax=self.ax)
        self._show_matplotlib()
        self.canvas.draw()

        self._has_2d_heatmap = True

    def populate_from_points(self, points, raman_min, raman_max):
        self._source_points = list(points)

        if not self._has_2d_heatmap:
            return

        self._raman_min = raman_min
        self._raman_max = raman_max

        self._z[:] = np.nan
        self._grid_points = [[None for _ in self._xs] for _ in self._ys]

        xs = np.asarray(self._xs)
        ys = np.asarray(self._ys)

        for point in points:
            x_idx = int(np.argmin(np.abs(xs - point.x)))
            y_idx = int(np.argmin(np.abs(ys - point.y)))

            mask = (point.raman_shifts >= raman_min) & (point.raman_shifts <= raman_max)

            value = float(point.intensities[mask].sum())
            self._z[y_idx, x_idx] = value
            self._grid_points[y_idx][x_idx] = point

        self._im.set_data(self._z)

        finite = self._z[np.isfinite(self._z)]
        if finite.size:
            self._im.set_clim(float(finite.min()), float(finite.max()))

        self._update_title()
        self.canvas.draw()

    def set_raman_range(self, rmin, rmax):
        self._raman_min = rmin
        self._raman_max = rmax

        if not self._has_2d_heatmap or not self._source_points:
            return

        self.populate_from_points(self._source_points, rmin, rmax)

    def _on_click(self, event):
        if not self._has_2d_heatmap:
            return
        if event.inaxes != self.ax or event.xdata is None or event.ydata is None:
            return

        x_idx = int(np.argmin(np.abs(np.asarray(self._xs) - event.xdata)))
        y_idx = int(np.argmin(np.abs(np.asarray(self._ys) - event.ydata)))

        point = self._grid_points[y_idx][x_idx]
        if point:
            self.scan_point_selected.emit(point)

    def _on_mouse_move(self, event):
        if self._has_2d_heatmap and event.inaxes == self.ax:
            self.canvas.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.canvas.setCursor(Qt.CursorShape.ArrowCursor)

    def _update_title(self):
        self.ax.set_title(
            f"Integrated Intensity "
            f"[{self._raman_min:.0f}–{self._raman_max:.0f} cm⁻¹]"
        )

    def _compute_extent(self):
        dx = (self._xs[1] - self._xs[0]) / 2
        dy = (self._ys[1] - self._ys[0]) / 2
        return [
            self._xs[0] - dx,
            self._xs[-1] + dx,
            self._ys[0] - dy,
            self._ys[-1] + dy,
        ]

    def _remove_colorbar(self):
        if self._colorbar:
            try:
                self._colorbar.ax.remove()
            except Exception:
                pass
            self._colorbar = None

    def export_png(self) -> bytes:
        if not self._has_2d_heatmap:
            return b""
        buf = io.BytesIO()
        self.fig.savefig(buf, format="png", dpi=PLOT_DPI, bbox_inches="tight")
        buf.seek(0)
        return buf.read()
    
    def clear(self):
        self.ax.clear()
        self._remove_colorbar()
        self._source_points = []
        self._has_2d_heatmap = False
        self._show_qt_message("No Scan Data")
        self.canvas.draw_idle()
        self._xs = []
        self._ys = []
        self._z = None
        self._grid_points = None
        self._im = None