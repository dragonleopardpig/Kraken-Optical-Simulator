"""Validate the Double Gauss analysis-suite case-study docs, assets, and optics."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
from matplotlib.figure import Figure
import numpy as np

from KrakenOS.UI.layout_editor import LAYOUTS_DIR, KrakenLayoutEditor, _load_python_data, _load_python_title
from KrakenOS.UI.render_layout_snapshot import _build_runtime_system, _snapshot_editor


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = PROJECT_ROOT / "docs" / "source" / "tutorials" / "double_gauss_analysis_suite.rst"
INDEX_PATH = PROJECT_ROOT / "docs" / "source" / "tutorials" / "index.rst"
BOSS_DEMO_PATH = PROJECT_ROOT / "docs" / "source" / "tutorials" / "boss_demo_walkthrough.rst"
CHECKLIST_PATH = PROJECT_ROOT / "docs" / "source" / "tutorials" / "presentation_checklist.rst"
BACKLOG_PATH = PROJECT_ROOT / "docs" / "source" / "tutorials" / "optiland_port_backlog.rst"
EXAMPLE_PATH = PROJECT_ROOT / "KrakenOS" / "Examples" / "Examp_Double_Gauss_Analysis_Suite.py"
CAPTURE_SCRIPT = PROJECT_ROOT / "KrakenOS" / "UI" / "capture_double_gauss_analysis_case_study_screenshots.py"
LAYOUT_TITLE = "Double Gauss PSF MTF Wavefront Zernike Case Study"
STATIC_DIR = PROJECT_ROOT / "docs" / "source" / "_static" / "tutorials" / "double_gauss_analysis_suite"
EXPECTED_IMAGES = (
    "01_double_gauss_analysis_ui.png",
    "01_double_gauss_layout.png",
    "02_spot_aoi.png",
    "03_psf_aoi.png",
    "04_mtf_aoi.png",
    "05_wavefront_aoi.png",
    "06_zernike_aoi.png",
)


def _text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _layout_path_by_title(title: str) -> Path:
    for path in sorted(LAYOUTS_DIR.glob("*.py")):
        if path.name.startswith("_") or path.name == "__init__.py":
            continue
        try:
            if str(_load_python_title(path)).strip() == title:
                return path
        except Exception:
            continue
    raise ValueError(f"Common layout not found: {title}")


def _analysis_checks(path: Path) -> list[tuple[str, bool]]:
    info = _load_python_data(path)
    settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
    rows = [KrakenLayoutEditor._row_from_layout_item(item) for item in info["surfaces"]]
    rows[0].surface = "Object"
    rows[-1].surface = "Image"
    editor = _snapshot_editor(rows, settings)
    editor.current_layout_file = path
    editor._normalize_special_rows()
    system = _build_runtime_system(path, editor.rows)
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
    x_centered, y_centered = editor._center_image_plane_samples(x_local, y_local)
    spot_rms = float(np.sqrt(np.mean(x_centered * x_centered + y_centered * y_centered))) if x_centered.size else float("nan")
    span = max(float(np.ptp(x_centered)) if x_centered.size else 0.0, float(np.ptp(y_centered)) if y_centered.size else 0.0, 1e-3) * 1.25
    psf_hist, _xedges, _yedges, _accelerator = editor._compute_psf_histogram(x_local, y_local, 96, span)
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
    mtf_average = 0.5 * (tan + sag) if tan.size and sag.size else np.asarray([])
    mtf_20 = float(np.interp(20.0, freq, mtf_average)) if freq.size and mtf_average.size else float("nan")

    editor.figure = Figure(figsize=(4.0, 3.0))
    wave_ax = editor.figure.add_subplot(111)
    editor.analysis_mode = "wavefront"
    editor.wavefront_style_var.set("Wavefront Function")
    editor._plot_analysis(wave_ax, system, None, wavelength)
    wavefront_samples = list(getattr(editor, "_last_wavefront_samples", []) or [])
    wavefront_values = np.asarray([row.get("phase_waves", np.nan) for row in wavefront_samples], dtype=float)

    editor.figure = Figure(figsize=(4.0, 3.0))
    zernike_ax = editor.figure.add_subplot(111)
    editor.analysis_mode = "zernike"
    editor._plot_analysis(zernike_ax, system, None, wavelength)
    zernike_rows = list(getattr(editor, "_last_zernike_coefficients", []) or [])
    residual_values = np.asarray([row.get("residual_rms_waves", np.nan) for row in zernike_rows[:1]], dtype=float)

    return [
        ("layout has object/image plus Double Gauss surfaces", len(rows) >= 10),
        ("spot analysis returns finite image samples", int(x_centered.size) >= 20 and np.isfinite(spot_rms)),
        ("spot RMS is non-zero and bounded", 0.0 < spot_rms < 5.0),
        ("PSF histogram has ray energy", float(np.sum(psf_hist)) >= 20.0),
        ("MTF curve includes finite values", freq.size > 8 and np.all(np.isfinite(mtf_average[: min(8, mtf_average.size)]))),
        ("MTF at 20 cyc/mm is bounded", np.isfinite(mtf_20) and 0.0 <= mtf_20 <= 1.05),
        ("wavefront analysis stores exportable samples", len(wavefront_samples) >= 20),
        ("wavefront phase samples are finite", wavefront_values.size >= 20 and np.all(np.isfinite(wavefront_values[:20]))),
        ("Zernike fit stores exportable coefficients", len(zernike_rows) >= 6),
        ("Zernike residual is finite", residual_values.size == 1 and np.all(np.isfinite(residual_values))),
    ]


def main() -> int:
    path = _layout_path_by_title(LAYOUT_TITLE)
    doc = _text(DOC_PATH)
    index = _text(INDEX_PATH)
    boss = _text(BOSS_DEMO_PATH)
    checklist = _text(CHECKLIST_PATH)
    backlog = _text(BACKLOG_PATH)
    example = _text(EXAMPLE_PATH)
    capture = _text(CAPTURE_SCRIPT)
    checks = [
        ("case-study page exists", DOC_PATH.exists()),
        ("case-study in tutorials toctree", "double_gauss_analysis_suite" in index),
        ("case-study in boss demo walkthrough", "double_gauss_analysis_suite" in boss),
        ("case-study in presentation checklist", "double_gauss_analysis_suite" in checklist),
        ("optiland backlog marks PSF/MTF and Zernike ports landed", "double_gauss_analysis_suite" in backlog),
        ("runnable example exists", EXAMPLE_PATH.exists() and "spot_rms_mm" in example),
        ("capture script exists", CAPTURE_SCRIPT.exists() and "DEFAULT_OUTPUT_DIR" in capture),
        ("case-study documents Optiland source notebooks", "Tutorial_4b" in doc and "Tutorial_4c" in doc),
        ("case-study documents all analysis modes", all(term in doc for term in ("Spot", "PSF", "MTF", "Wavefront", "Zernike"))),
    ]
    for image_name in EXPECTED_IMAGES:
        image_path = STATIC_DIR / image_name
        checks.append((f"image exists: {image_name}", image_path.exists() and image_path.stat().st_size > 2048))
    checks.extend(_analysis_checks(path))

    failed = [name for name, ok in checks if not ok]
    if failed:
        print("Double Gauss analysis-suite validation failed:")
        for name in failed:
            print(f"- {name}")
        return 1
    print("Double Gauss analysis-suite validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
