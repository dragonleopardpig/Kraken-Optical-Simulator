"""Guard: Field Curvature / Distortion renders as the Zemax two-panel layout.

KrakenOS used to draw field curvature and distortion as a single axis with the
distortion overlaid on a ``twinx`` (focus shift on the left spine, distortion on
the right), field on the horizontal axis. Zemax instead draws two side-by-side
panels -- FIELD CURVATURE (tangential T + sagittal S, in mm) beside DISTORTION
(percent) -- with the field on the vertical axis (its +Y convention). This guards
bug 0037: the field-curvature analysis must produce that two-panel layout.

All checks are display-free (Agg backend, no Xvfb / GPU needed):

A. Two panels are drawn, titled FIELD CURVATURE and DISTORTION.
B. The distortion panel shares the field (y) axis with the field-curvature panel.
C. The field is on the vertical axis (the shared y-range spans 0..max field),
   and each panel has a vertical x=0 reference line.
D. The field-curvature panel carries both the tangential (T) and sagittal (S)
   curves.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_field_curvature_distortion_panels

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
from matplotlib.figure import Figure

from KrakenOS.UI.layout_editor import (
    LAYOUTS_DIR,
    KrakenLayoutEditor,
    _load_python_data,
    _load_python_title,
)
from KrakenOS.UI.render_layout_snapshot import _build_runtime_system, _snapshot_editor

LAYOUT_TITLE = "Double Gauss PSF MTF Wavefront Zernike Case Study"


def _layout_path_by_title(title: str) -> "Path | None":
    for path in sorted(LAYOUTS_DIR.glob("*.py")):
        if path.name.startswith("_") or path.name == "__init__.py":
            continue
        try:
            if str(_load_python_title(path)).strip() == title:
                return path
        except Exception:
            continue
    return None


def _panel_by_title(axes, title: str):
    for axis in axes:
        if str(axis.get_title()).strip().upper() == title:
            return axis
    return None


def run_checks(verbose: bool = False) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    passed = True

    layout_path = _layout_path_by_title(LAYOUT_TITLE)
    if layout_path is None:
        notes.append("SKIP: double-gauss analysis layout unavailable")
        return passed, notes

    info = _load_python_data(layout_path)
    settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
    rows = [KrakenLayoutEditor._row_from_layout_item(item) for item in info["surfaces"]]
    rows[0].surface = "Object"
    rows[-1].surface = "Image"
    editor = _snapshot_editor(rows, settings)
    editor.current_layout_file = layout_path
    editor._normalize_special_rows()
    system = _build_runtime_system(layout_path, editor.rows)

    editor.figure = Figure(figsize=(6.0, 3.2))
    analysis_ax = editor.figure.add_subplot(111)
    editor.analysis_mode = "field_curvature"
    editor._analysis_ax = analysis_ax
    editor._analysis_axes = [analysis_ax]
    editor._plot_analysis(analysis_ax, system, None, 0.55)

    if any("unavailable" in str(getattr(t, "get_text", lambda: "")()) for t in analysis_ax.texts):
        notes.append("SKIP: field-curvature analysis unavailable on this clone")
        return passed, notes

    axes = list(editor.figure.axes)

    # A. Two titled panels.
    fc_panel = _panel_by_title(axes, "FIELD CURVATURE")
    dist_panel = _panel_by_title(axes, "DISTORTION")
    if fc_panel is None:
        notes.append("FAIL: no FIELD CURVATURE panel")
        passed = False
    if dist_panel is None:
        notes.append("FAIL: no DISTORTION panel")
        passed = False
    if fc_panel is None or dist_panel is None:
        return False, notes

    # B. The distortion panel shares the field (y) axis with the FC panel.
    if dist_panel not in list(fc_panel.get_shared_y_axes().get_siblings(fc_panel)):
        notes.append("FAIL: distortion panel does not share the field (y) axis")
        passed = False

    # C. Field on the vertical axis: shared y spans 0..max field, and each panel
    #    has a vertical x=0 reference line.
    y_lo, y_hi = fc_panel.get_ylim()
    if not (abs(y_lo) < 1e-6 and y_hi > 0):
        notes.append(f"FAIL: field axis is not vertical 0..max (ylim={y_lo:.3g}..{y_hi:.3g})")
        passed = False
    for name, panel in (("field-curvature", fc_panel), ("distortion", dist_panel)):
        has_axis_line = any(
            len(line.get_xdata()) == 2 and abs(float(line.get_xdata()[0])) < 1e-9
            and abs(float(line.get_xdata()[1])) < 1e-9
            for line in panel.lines
        )
        if not has_axis_line:
            notes.append(f"FAIL: {name} panel has no vertical x=0 reference line")
            passed = False

    # D. Both T and S curves are present in the FC panel.
    fc_curves = [line for line in fc_panel.lines if len(line.get_xdata()) > 2]
    if len(fc_curves) < 2:
        notes.append(f"FAIL: field-curvature panel has {len(fc_curves)} curves, expected T and S")
        passed = False

    if verbose:
        notes.append(
            f"panels={len(axes)}, fc_curves={len(fc_curves)}, "
            f"ylim=({y_lo:.3g},{y_hi:.3g})"
        )
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        print(note)
    if passed:
        print("[PASS] Field Curvature / Distortion renders the Zemax two-panel layout")
        return 0
    print("[FAIL] Field-curvature two-panel layout guard")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
