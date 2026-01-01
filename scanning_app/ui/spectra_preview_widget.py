from PyQt6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
from config import PLOT_DPI
from loguru import logger


class SpectraPreviewWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.fig = Figure(dpi=PLOT_DPI)
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)
        self.init_ui()
        self.show_sample_spectrum()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def show_sample_spectrum(self):
        wavelengths = np.linspace(0, 4000, 1000)
        spectrum = (
            np.exp(-((wavelengths - 1000) / 200) ** 2)
            + 0.5 * np.exp(-((wavelengths - 1600) / 150) ** 2)
            + 0.3 * np.random.rand(len(wavelengths))
        )

        self.ax.clear()
        self.ax.plot(wavelengths, spectrum)
        self.ax.set_xlabel("Wavenumber (cm⁻¹)")
        self.ax.set_ylabel("Intensity")
        self.ax.set_title("Spectrum Preview")
        self.canvas.draw()
        logger.debug("Displayed sample spectrum")

    def update_spectrum(self, spectrum_data):
        wavelengths = np.linspace(0, 4000, len(spectrum_data))
        self.ax.clear()
        self.ax.plot(wavelengths, spectrum_data)
        self.ax.set_xlabel("Wavenumber (cm⁻¹)")
        self.ax.set_ylabel("Intensity")
        self.ax.set_title("Spectrum Preview")
        self.canvas.draw()
        logger.debug("Updated spectrum plot with new data")