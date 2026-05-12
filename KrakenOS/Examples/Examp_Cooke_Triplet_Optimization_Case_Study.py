"""Cooke-triplet optimization case-study helper.

Run from the repository root:

    python -m KrakenOS.Examples.Examp_Cooke_Triplet_Optimization_Case_Study

The script evaluates the same primary-wavelength spot metrics used by the UI
case-study validator. It demonstrates how to consume the menu layout's
``SURFACES`` and ``OPTIMIZED_SURFACES`` prescriptions from Python.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from KrakenOS.common_optical_layouts import cooke_triplet_optimization_case_study as layout
from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.render_layout_snapshot import _build_runtime_system, _snapshot_editor


LAYOUT_PATH = Path(layout.__file__).resolve()


def build_rows(surface_items: list[dict[str, object]]):
    rows = [KrakenLayoutEditor._row_from_layout_item(item) for item in surface_items]
    rows[0].surface = "Object"
    rows[-1].surface = "Image"
    return rows


def primary_spot_rms(surface_items: list[dict[str, object]]) -> dict[float, float]:
    rows = build_rows(surface_items)
    editor = _snapshot_editor(rows, layout.SETTINGS)
    editor.current_layout_file = LAYOUT_PATH
    editor._normalize_special_rows()
    system = _build_runtime_system(LAYOUT_PATH, editor.rows)
    metrics: dict[float, float] = {}
    for field_y in (0.0, 14.0):
        x_local, y_local, _workers = editor._build_geometric_image_samples(
            system,
            0.55,
            sample_count=17,
            pattern="hexapolar",
            surface_index=-1,
            aperture_type="EPD",
            aperture_value=10.0,
            field_type="Angle",
            field_x=0.0,
            field_y=field_y,
        )
        x_vals = np.asarray(x_local, dtype=float)
        y_vals = np.asarray(y_local, dtype=float)
        finite = np.isfinite(x_vals) & np.isfinite(y_vals)
        x_vals = x_vals[finite]
        y_vals = y_vals[finite]
        metrics[field_y] = float(np.sqrt(np.mean((x_vals - np.mean(x_vals)) ** 2 + (y_vals - np.mean(y_vals)) ** 2)))
    return metrics


def main() -> int:
    starting = primary_spot_rms(layout.SURFACES)
    optimized = primary_spot_rms(layout.OPTIMIZED_SURFACES)
    print("Cooke triplet primary-wavelength RMS spot radius [mm]")
    print("field_deg | starting | optimized | improvement")
    print("--- | --- | --- | ---")
    for field_y in (0.0, 14.0):
        start = starting[field_y]
        opt = optimized[field_y]
        print(f"{field_y:.1f} | {start:.6f} | {opt:.6f} | {start / max(opt, 1e-12):.1f}x")
    mean_start = float(np.mean(list(starting.values())))
    mean_opt = float(np.mean(list(optimized.values())))
    print(f"mean | {mean_start:.6f} | {mean_opt:.6f} | {mean_start / max(mean_opt, 1e-12):.1f}x")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
