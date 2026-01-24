from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QVBoxLayout, QWidget
from loguru import logger
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.widgets import SpanSelector

from config import PLOT_DPI, RAMAN_MAX_LIMIT, RAMAN_MIN_LIMIT


class SpectraPreviewWidget(QWidget):
    raman_range_selected = pyqtSignal(float, float)

    def __init__(self):
        super().__init__()

        self.fig = Figure(dpi=PLOT_DPI, facecolor="#fafafa")
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)

        self._suppress_span_signal = False
        self._raman_min = RAMAN_MIN_LIMIT
        self._raman_max = RAMAN_MAX_LIMIT

        self._init_ui()
        self._init_axes()
        self._show_empty_message()
        self.canvas.draw_idle()

        self._span = SpanSelector(
            self.ax,
            self._on_span_selected,
            direction="horizontal",
            useblit=True,
            props={"alpha": 0.25, "facecolor": "#1976D2"},
            interactive=False,
        )

        self.canvas.mpl_connect("button_press_event", self._on_click)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        layout.addWidget(self.canvas)

    def _init_axes(self):
        self.ax.clear()

        self.ax.set_facecolor("#fafafa")
        self.ax.spines["top"].set_visible(False)
        self.ax.spines["right"].set_visible(False)
        self.ax.spines["left"].set_color("#888")
        self.ax.spines["bottom"].set_color("#888")

        self.ax.tick_params(colors="#555", labelsize=9)
        self.ax.grid(True, which="major", alpha=0.25, linestyle="--")

        self.ax.set_xlabel("Raman shift (cm⁻¹)", fontsize=10)
        self.ax.set_ylabel("Intensity (a.u.)", fontsize=10)
        self.ax.set_xlim(RAMAN_MIN_LIMIT, RAMAN_MAX_LIMIT)

    def _show_empty_message(self):
        self.ax.text(
            0.5,
            0.5,
            "No spectrum acquired",
            transform=self.ax.transAxes,
            ha="center",
            va="center",
            color="#999",
            fontsize=11,
        )

    def update_spectrum(self, raman_shifts, intensities):
        if raman_shifts is None or intensities is None:
            return

        if len(raman_shifts) < 2 or len(intensities) < 2:
            return

        if len(raman_shifts) != len(intensities):
            return

        self._last_spectrum = (raman_shifts, intensities)

        self._suppress_span_signal = True
        try:
            self._init_axes()

            self.ax.plot(
                raman_shifts,
                intensities,
                color="#B0B0B0",
                lw=1.0,
                zorder=1,
            )

            mask = (raman_shifts >= self._raman_min) & (raman_shifts <= self._raman_max)

            self.ax.plot(
                raman_shifts[mask],
                intensities[mask],
                color="#1976D2",
                lw=1.6,
                zorder=2,
            )

            self.ax.relim()
            self.ax.autoscale(axis="y")
            self.canvas.draw_idle()
        finally:
            self._suppress_span_signal = False

    def _on_click(self, event):
        if event.inaxes != self.ax or event.xdata is None:
            return

        logger.debug(
            "Spectrum click: Raman=%.1f cm⁻¹, Intensity=%.3f",
            event.xdata,
            event.ydata,
        )

    def update_from_scan_point(self, point):
        self.update_spectrum(point.raman_shifts, point.intensities)

    def _on_span_selected(self, xmin, xmax):
        if self._suppress_span_signal:
            return

        if xmin > xmax:
            xmin, xmax = xmax, xmin

        self._raman_min = xmin
        self._raman_max = xmax

        if hasattr(self, "_last_spectrum"):
            self.update_spectrum(*self._last_spectrum)

        self.raman_range_selected.emit(xmin, xmax)

    def set_raman_range(self, raman_min: float, raman_max: float):
        self._raman_min = raman_min
        self._raman_max = raman_max

        if self._span is not None:
            self._suppress_span_signal = True
            try:
                self._span.extents = (raman_min, raman_max)
            finally:
                self._suppress_span_signal = False

        if hasattr(self, "_last_spectrum"):
            self.update_spectrum(*self._last_spectrum)

    def set_interactive(self, enabled: bool):
        if self._span is not None:
            self._span.set_active(enabled)

    def clear(self):
        self._init_axes()
        self._show_empty_message()
        if hasattr(self, "_last_spectrum"):
            delattr(self, "_last_spectrum")
        self.canvas.draw_idle()
