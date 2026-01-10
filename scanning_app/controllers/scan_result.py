from dataclasses import dataclass


@dataclass
class ScanResult:
    scan_meta: object
    spectrometer_meta: object
    heatmap_bounds: object
    spectra_df: object
    heatmap_grid: object
    heatmap_png: bytes
    camera_overview_png: bytes
    camera_raw_png: bytes
