from dataclasses import dataclass


@dataclass
class ScanResult:
    scan_meta: object
    spectrometer_meta: object
    heatmap_bounds: object
    spectra_df: object
    heatmap_grid: object
    heatmap_png: object = None
    camera_png: object = None
