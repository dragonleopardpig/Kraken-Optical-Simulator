"""Validate the finite machine-vision focus case-study artifacts and spot scaling."""

from __future__ import annotations

import inspect
from pathlib import Path

import numpy as np
from matplotlib.figure import Figure

from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.panels.main_path_detector_analysis import MainPathDetectorAnalysis


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = PROJECT_ROOT / "docs" / "source" / "tutorials" / "machine_vision_focus.rst"
INDEX_PATH = PROJECT_ROOT / "docs" / "source" / "tutorials" / "index.rst"
CAPTURE_SCRIPT = PROJECT_ROOT / "KrakenOS" / "UI" / "capture_machine_vision_case_study_screenshots.py"
STATIC_DIR = PROJECT_ROOT / "docs" / "source" / "_static" / "tutorials" / "machine_vision_focus"
EXPECTED_IMAGES = (
    "01_loaded_machine_vision_ui.png",
    "01_loaded_machine_vision_plot.png",
    "02_defocused_spot_aoi.png",
    "03_defocused_mtf_aoi.png",
    "04_focus_variable_setup_ui.png",
    "05_refocused_spot_aoi.png",
    "06_refocused_mtf_aoi.png",
    "07_wide_field_spot_aoi.png",
)


def _text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _spot_helper_keeps_equal_limits() -> bool:
    figure = Figure(figsize=(4.0, 4.0))
    axis = figure.add_subplot(111)
    KrakenLayoutEditor._apply_equal_spot_axis_scaling(axis, np.asarray([-2.0, 2.0]), np.asarray([-1.0, 1.0]))
    x_min, x_max = axis.get_xlim()
    y_min, y_max = axis.get_ylim()
    data_spans_match = abs((x_max - x_min) - (y_max - y_min)) < 1e-12
    aspect_is_equal = axis.get_aspect() == 1.0
    box_is_square = abs(float(axis.get_box_aspect()) - 1.0) < 1e-12
    return bool(data_spans_match and aspect_is_equal and box_is_square)


def main() -> int:
    doc = _text(DOC_PATH)
    index = _text(INDEX_PATH)
    capture = _text(CAPTURE_SCRIPT)
    helper_source = inspect.getsource(KrakenLayoutEditor._apply_equal_spot_axis_scaling)
    analysis_source = inspect.getsource(KrakenLayoutEditor._plot_analysis)
    branch_spot_source = inspect.getsource(MainPathDetectorAnalysis._plot_branch_detector_spot_analysis)
    spot_block = analysis_source.split('if self.analysis_mode == "spot":', 1)[1].split(
        'if self.analysis_mode == "psf":', 1
    )[0]

    checks = [
        ("case-study page exists", DOC_PATH.exists()),
        ("case-study in tutorials toctree", "machine_vision_focus" in index),
        ("capture script exists", CAPTURE_SCRIPT.exists() and "DEFAULT_OUTPUT_DIR" in capture),
        ("case-study documents equal X/Y scale", "equal X/Y" in doc),
        ("spot helper sets equal aspect", 'set_aspect("equal"' in helper_source),
        ("spot helper sets square box", "set_box_aspect(1.0)" in helper_source),
        ("spot helper equalizes data limits", _spot_helper_keeps_equal_limits()),
        ("main spot analysis uses equal helper", "_apply_equal_spot_axis_scaling(analysis_ax, X_plot, Y_plot)" in spot_block),
        ("main spot block avoids auto aspect", 'set_aspect("auto")' not in spot_block),
        ("path spot analysis uses equal helper", "_apply_equal_spot_axis_scaling(analysis_ax, plot_x, plot_y)" in branch_spot_source),
        ("path spot analysis avoids auto aspect", 'set_aspect("auto")' not in branch_spot_source),
    ]
    for image_name in EXPECTED_IMAGES:
        path = STATIC_DIR / image_name
        checks.append((f"image exists: {image_name}", path.exists() and path.stat().st_size > 2048))

    failed = [name for name, ok in checks if not ok]
    if failed:
        print("Machine-vision case study validation failed:")
        for name in failed:
            print(f"- {name}")
        return 1
    print("Machine-vision case study validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
