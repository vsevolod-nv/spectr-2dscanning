import io
import json
import zipfile
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


class Raman2DScanWriter:
    def write(
        self,
        path: Path,
        scan_meta: dict,
        spectrometer_meta: dict,
        heatmap_bounds: tuple[float, float],
        spectra_df: pd.DataFrame,
        heatmap_grid: np.ndarray,
        heatmap_png: bytes | None = None,
        camera_png: bytes | None = None,
    ) -> None:
        path = Path(path)
        if path.suffix != ".raman2dscan":
            path = path.with_suffix(".raman2dscan")

        left, right = heatmap_bounds

        info = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "scan": scan_meta,
            "spectrometer": spectrometer_meta,
            "heatmap": {
                "left_bound_cm1": float(left),
                "right_bound_cm1": float(right),
            },
        }

        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("info.json", json.dumps(info, indent=2))
            zf.writestr(
                "spectra.csv",
                self._dataframe_to_csv_bytes(spectra_df),
            )

            heatmap_df = self._heatmap_to_dataframe(heatmap_grid)
            zf.writestr(
                f"heatmap_{left}_{right}.csv",
                self._dataframe_to_csv_bytes(heatmap_df),
            )

            if heatmap_png is not None:
                zf.writestr(
                    f"heatmap_{left}_{right}.png",
                    heatmap_png,
                )

            if camera_png is not None:
                zf.writestr("camera_view.png", camera_png)

    @staticmethod
    def _dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
        buffer = io.StringIO()
        df.to_csv(buffer, index=False)
        return buffer.getvalue().encode("utf-8")

    @staticmethod
    def _heatmap_to_dataframe(grid: np.ndarray) -> pd.DataFrame:
        height, width = grid.shape
        return pd.DataFrame(
            {
                "x_index": x,
                "y_index": y,
                "integrated_intensity": float(grid[y, x]),
            }
            for y in range(height)
            for x in range(width)
        )
