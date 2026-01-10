import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from controllers.scan_result import ScanResult


class Raman2DScanReader:
    def read(self, path: Path) -> ScanResult:
        path = Path(path)

        with zipfile.ZipFile(path, "r") as zf:
            info = json.loads(zf.read("info.json"))
            spectra_df = pd.read_csv(zf.open("spectra.csv"))

            heatmap_csv = next(
                name
                for name in zf.namelist()
                if name.startswith("heatmap_") and name.endswith(".csv")
            )

            heatmap_df = pd.read_csv(zf.open(heatmap_csv))

            heatmap_bounds = (
                info["heatmap"]["left_bound_cm1"],
                info["heatmap"]["right_bound_cm1"],
            )

            width = heatmap_df["x_index"].max() + 1
            height = heatmap_df["y_index"].max() + 1

            heatmap_grid = np.full((height, width), np.nan)
            for _, row in heatmap_df.iterrows():
                heatmap_grid[int(row.y_index), int(row.x_index)] = (
                    row.integrated_intensity
                )

            heatmap_png_name = f"heatmap_{heatmap_bounds[0]}_{heatmap_bounds[1]}.png"
            heatmap_png = (
                zf.read(heatmap_png_name) if heatmap_png_name in zf.namelist() else None
            )

            if "camera_overview.png" in zf.namelist():
                camera_overview_png = zf.read("camera_overview.png")
            elif "camera_view.png" in zf.namelist():
                camera_overview_png = zf.read("camera_view.png")
            else:
                camera_overview_png = None

            camera_raw_png = (
                zf.read("camera_raw.png") if "camera_raw.png" in zf.namelist() else None
            )

        return ScanResult(
            scan_meta=info["scan"],
            spectrometer_meta=info["spectrometer"],
            heatmap_bounds=heatmap_bounds,
            spectra_df=spectra_df,
            heatmap_grid=heatmap_grid,
            heatmap_png=heatmap_png,
            camera_overview_png=camera_overview_png,
            camera_raw_png=camera_raw_png,
        )
