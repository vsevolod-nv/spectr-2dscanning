from PyQt6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
from config import (
    PLOT_DPI,
    HEATMAP_CMAP,
    HEATMAP_ORIGIN,
    HEATMAP_ASPECT,
    SAMPLE_X_RANGE,
    SAMPLE_Y_RANGE,
    SAMPLE_GRID_SIZE,
    X_LABEL_TEXT,
    Y_LABEL_TEXT,
    SAMPLE_TITLE,
    LIVE_TITLE,
)


class HeatmapPreviewWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.fig = Figure(dpi=PLOT_DPI)
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)
        self.colorbar = None
        self.init_ui()
        self.show_sample_heatmap()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def show_sample_heatmap(self):
        if self.colorbar:
            self.colorbar.remove()
            self.colorbar = None

        x = np.linspace(SAMPLE_X_RANGE[0], SAMPLE_X_RANGE[1], SAMPLE_GRID_SIZE)
        y = np.linspace(SAMPLE_Y_RANGE[0], SAMPLE_Y_RANGE[1], SAMPLE_GRID_SIZE)
        X, Y = np.meshgrid(x, y)
        Z = np.exp(-(X**2 + Y**2))

        self.ax.clear()
        im = self.ax.imshow(
            Z,
            cmap=HEATMAP_CMAP,
            origin=HEATMAP_ORIGIN,
            extent=[SAMPLE_X_RANGE[0], SAMPLE_X_RANGE[1], SAMPLE_Y_RANGE[0], SAMPLE_Y_RANGE[1]],
            aspect=HEATMAP_ASPECT,
        )
        self.ax.set_xlabel(X_LABEL_TEXT)
        self.ax.set_ylabel(Y_LABEL_TEXT)
        self.ax.set_title(SAMPLE_TITLE)
        self.colorbar = self.fig.colorbar(im, ax=self.ax)
        self.canvas.draw()

    def update_heatmap(self, scan_data):
        if self.colorbar:
            self.colorbar.remove()
            self.colorbar = None

        if not scan_data:
            return

        x_coords = [point[0] for point in scan_data]
        y_coords = [point[1] for point in scan_data]
        intensities = [point[2] for point in scan_data]

        if not x_coords or not y_coords:
            return

        unique_x = sorted(set(x_coords))
        unique_y = sorted(set(y_coords))

        x_grid, y_grid = np.meshgrid(unique_x, unique_y)
        z_grid = np.full_like(x_grid, np.nan, dtype=float)

        for x, y, intensity in scan_data:
            x_idx = unique_x.index(x)
            y_idx = unique_y.index(y)
            z_grid[y_idx, x_idx] = intensity

        self.ax.clear()
        im = self.ax.imshow(
            z_grid,
            cmap=HEATMAP_CMAP,
            origin=HEATMAP_ORIGIN,
            extent=[min(unique_x), max(unique_x), min(unique_y), max(unique_y)],
            aspect=HEATMAP_ASPECT,
        )
        self.ax.set_xlabel(X_LABEL_TEXT)
        self.ax.set_ylabel(Y_LABEL_TEXT)
        self.ax.set_title(LIVE_TITLE)
        self.colorbar = self.fig.colorbar(im, ax=self.ax)
        self.canvas.draw()