from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QVBoxLayout, QWidget

import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from config import HEATMAP_CMAP, PLOT_DPI, RAMAN_MAX_LIMIT, RAMAN_MIN_LIMIT


class HeatmapPreviewWidget(QWidget):
    scan_point_selected = pyqtSignal(object)

    def __init__(self):
        super().__init__()

        self.fig = Figure(dpi=PLOT_DPI, facecolor="#fafafa")
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)

        self._raman_min = RAMAN_MIN_LIMIT
        self._raman_max = RAMAN_MAX_LIMIT

        self._xs = None
        self._ys = None
        self._z = None
        self._im = None
        self._grid_points = None

        self._scan_data = []

        self._init_ui()
        self._show_empty()

        self.canvas.mpl_connect("button_press_event", self._on_click)
        self.canvas.mpl_connect("motion_notify_event", self._on_mouse_move)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self.canvas)

    def _show_empty(self):
        self.ax.clear()
        self.ax.text(
            0.5,
            0.5,
            "No Scan Data",
            transform=self.ax.transAxes,
            ha="center",
            va="center",
            color="#999",
            fontsize=11,
        )
        self.ax.set_xlabel("X (µm)")
        self.ax.set_ylabel("Y (µm)")
        self.canvas.draw_idle()

    def _on_mouse_move(self, event):
        if event.inaxes == self.ax:
            self.canvas.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.canvas.setCursor(Qt.CursorShape.ArrowCursor)

    def initialize_grid(self, planned_points):
        self._scan_data = []
        self._xs = sorted({p.x for p in planned_points})
        self._ys = sorted({p.y for p in planned_points})

        self._z = np.full((len(self._ys), len(self._xs)), np.nan)
        self._grid_points = [[None for _ in self._xs] for _ in self._ys]

        self.ax.clear()

        self._im = self.ax.imshow(
            self._z,
            cmap=HEATMAP_CMAP,
            origin="lower",
            extent=[
                min(self._xs),
                max(self._xs),
                min(self._ys),
                max(self._ys),
            ],
            aspect="auto",
        )

        self.ax.set_xlabel("X (µm)")
        self.ax.set_ylabel("Y (µm)")
        self.ax.set_title(
            f"Integrated Intensity "
            f"[{self._raman_min:.0f}–{self._raman_max:.0f} cm⁻¹]"
        )

        self._im.set_data(self._z)
        self.fig.colorbar(self._im, ax=self.ax)
        self.canvas.draw_idle()

    def add_scan_point(self, point):
        if self._z is None:
            self.initialize_grid([point])
            return

        if point.x not in self._xs:
            self._xs.append(point.x)
            self._xs.sort()
            self._z = np.pad(self._z, ((0, 0), (0, 1)), constant_values=np.nan)
            for row in self._grid_points:
                row.append(None)

        if point.y not in self._ys:
            self._ys.append(point.y)
            self._ys.sort()
            self._z = np.pad(self._z, ((0, 1), (0, 0)), constant_values=np.nan)
            self._grid_points.append([None for _ in self._xs])

        x_idx = self._xs.index(point.x)
        y_idx = self._ys.index(point.y)

        self._scan_data.append(point)
        self._grid_points[y_idx][x_idx] = point

        mask = (point.raman_shifts >= self._raman_min) & (
            point.raman_shifts <= self._raman_max
        )

        self._z[y_idx, x_idx] = float(np.sum(point.intensities[mask]))

        self._im.set_data(self._z)
        self._im.set_extent(self._compute_extent())

        finite = self._z[np.isfinite(self._z)]
        if finite.size > 0:
            self._im.set_clim(
                vmin=float(finite.min()),
                vmax=float(finite.max()),
            )

        self.canvas.draw_idle()

    def set_raman_range(self, rmin, rmax):
        self._raman_min = rmin
        self._raman_max = rmax

        if self._z is None:
            return

        for point in self._scan_data:
            x_idx = self._xs.index(point.x)
            y_idx = self._ys.index(point.y)

            mask = (point.raman_shifts >= rmin) & (point.raman_shifts <= rmax)

            self._z[y_idx, x_idx] = float(np.sum(point.intensities[mask]))

        self._im.set_data(self._z)
        self.canvas.draw_idle()

    def _on_click(self, event):
        if event.inaxes != self.ax:
            return
        if self._grid_points is None:
            return
        if event.xdata is None or event.ydata is None:
            return

        x_idx = np.argmin(np.abs(np.array(self._xs) - event.xdata))
        y_idx = np.argmin(np.abs(np.array(self._ys) - event.ydata))

        point = self._grid_points[y_idx][x_idx]
        if point:
            self.scan_point_selected.emit(point)

    def _compute_extent(self):
        if len(self._xs) > 1:
            dx = (self._xs[1] - self._xs[0]) / 2
        else:
            dx = 0.5

        if len(self._ys) > 1:
            dy = (self._ys[1] - self._ys[0]) / 2
        else:
            dy = 0.5

        return [
            self._xs[0] - dx,
            self._xs[-1] + dx,
            self._ys[0] - dy,
            self._ys[-1] + dy,
        ]
