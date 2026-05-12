"""Headless example for the Double Gauss analysis-suite case study.

This mirrors the UI workflow:

1. load the menu-backed Double Gauss case-study layout,
2. trace a finite-object pupil bundle,
3. compute geometric Spot/PSF/MTF metrics,
4. run Wavefront and Zernike analysis hooks so CSV exports have data.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
from matplotlib.figure import Figure
import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor, _load_python_data
from KrakenOS.UI.render_layout_snapshot import _build_runtime_system, _snapshot_editor


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LAYOUT_PATH = PROJECT_ROOT / "KrakenOS" / "common_optical_layouts" / "double_gauss_analysis_suite_case_study.py"


def main() -> int:
    info = _load_python_data(LAYOUT_PATH)
    settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
    rows = [KrakenLayoutEditor._row_from_layout_item(item) for item in info["surfaces"]]
    rows[0].surface = "Object"
    rows[-1].surface = "Image"

    editor = _snapshot_editor(rows, settings)
    editor.current_layout_file = LAYOUT_PATH
    editor._normalize_special_rows()
    system = _build_runtime_system(LAYOUT_PATH, editor.rows)

    wavelength = 0.55
    x_local, y_local, _workers = editor._build_geometric_image_samples(
        system,
        wavelength,
        sample_count=64,
        pattern="hexapolar",
        surface_index=-1,
        aperture_type="EPD",
        aperture_value=4.0,
        field_type="angle",
        field_x=0.0,
        field_y=0.0,
    )
    centered_x, centered_y = editor._center_image_plane_samples(x_local, y_local)
    spot_rms = float(np.sqrt(np.mean(centered_x * centered_x + centered_y * centered_y)))
    span = max(float(np.ptp(centered_x)), float(np.ptp(centered_y)), 1e-3) * 1.25
    psf_hist, _xedges, _yedges, psf_backend = editor._compute_psf_histogram(x_local, y_local, 96, span)
    mtf = editor._compute_geometric_mtf_sample(
        system,
        wavelength=wavelength,
        surface_index=-1,
        aperture_type="EPD",
        aperture_value=4.0,
        field_type="angle",
        field_x=0.0,
        field_y=0.0,
        algorithm="psf_fft",
    )
    freq = np.asarray(mtf["plot_freq"], dtype=float)
    tan = np.asarray(mtf["plot_tan"], dtype=float)
    sag = np.asarray(mtf["plot_sag"], dtype=float)
    mtf_20 = float(np.interp(20.0, freq, 0.5 * (tan + sag))) if freq.size else 0.0

    editor.figure = Figure(figsize=(4.0, 3.0))
    wave_ax = editor.figure.add_subplot(111)
    editor.analysis_mode = "wavefront"
    editor.wavefront_style_var.set("Wavefront Function")
    editor._plot_analysis(wave_ax, system, None, wavelength)
    wavefront_samples = len(editor._last_wavefront_samples)

    editor.figure = Figure(figsize=(4.0, 3.0))
    zernike_ax = editor.figure.add_subplot(111)
    editor.analysis_mode = "zernike"
    editor._plot_analysis(zernike_ax, system, None, wavelength)
    zernike_terms = len(editor._last_zernike_coefficients)

    print("Double Gauss analysis-suite metrics")
    print(f"spot_rms_mm={spot_rms:.6g}")
    print(f"psf_rays={int(np.sum(psf_hist))} backend={psf_backend}")
    print(f"mtf_20_cyc_per_mm={mtf_20:.6g}")
    print(f"wavefront_samples={wavefront_samples}")
    print(f"zernike_terms={zernike_terms}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
