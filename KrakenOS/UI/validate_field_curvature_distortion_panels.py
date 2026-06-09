"""Guard: Field Curvature and Distortion render as two SEPARATE single-panel items.

Field curvature and distortion are distinct optical concepts. KrakenOS used to draw
them together as one Zemax-style two-panel cell (FIELD CURVATURE beside DISTORTION,
sharing the field axis -- bug 0037). Packing both panels into a single analysis cell
made the left panel slide under the right one at the UI's aspect ratio, so they were
split into two independent analysis items: ``field_curvature`` (tangential T +
sagittal S best focus, in mm) and ``distortion`` (percent vs field). Each draws a
single full-cell panel with the field on the vertical axis (Zemax +Y). This guards
that split (and, by asserting a single panel per mode, that the two no longer overlap).

All checks are display-free (Agg backend, no Xvfb / GPU needed):

A. ``field_curvature`` renders exactly one analysis panel, titled FIELD CURVATURE,
   with no DISTORTION panel beside it.
B. ``distortion`` renders exactly one analysis panel, titled DISTORTION, with no
   FIELD CURVATURE panel beside it.
C. Field is on the vertical axis (ylim 0..max) with a vertical x=0 reference line,
   in both panels.
D. The field-curvature panel carries both the tangential (T) and sagittal (S)
   curves; the distortion panel carries its distortion curve.

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

LAYOUT_TITLE = "Zemax Double Gauss 28 Degree Field"


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


def _has_axis_line(panel) -> bool:
    return any(
        len(line.get_xdata()) == 2
        and abs(float(line.get_xdata()[0])) < 1e-9
        and abs(float(line.get_xdata()[1])) < 1e-9
        for line in panel.lines
    )


def _render_mode(editor, system, mode):
    """Render one analysis mode into a fresh figure; return (figure, analysis_ax)
    or (None, None) if the analysis is unavailable on this clone."""
    figure = Figure(figsize=(5.0, 4.0))
    analysis_ax = figure.add_subplot(111)
    analysis_ax.set_box_aspect(0.62)
    editor.figure = figure
    editor.analysis_mode = mode
    editor._analysis_ax = analysis_ax
    editor._analysis_axes = [analysis_ax]
    editor._plot_analysis(analysis_ax, system, None, 0.55)
    if any("unavailable" in str(getattr(t, "get_text", lambda: "")()) for t in analysis_ax.texts):
        return None, None
    return figure, analysis_ax


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

    fc_fig, fc_ax = _render_mode(editor, system, "field_curvature")
    dist_fig, dist_ax = _render_mode(editor, system, "distortion")
    if fc_fig is None or dist_fig is None:
        notes.append("SKIP: field-curvature/distortion analysis unavailable on this clone")
        return passed, notes

    fc_axes = list(fc_fig.axes)
    dist_axes = list(dist_fig.axes)

    # A. field_curvature: exactly one panel, FIELD CURVATURE, no DISTORTION sibling.
    if len(fc_axes) != 1:
        notes.append(f"FAIL: field_curvature drew {len(fc_axes)} panels, expected 1 (concepts are split)")
        passed = False
    if _panel_by_title(fc_axes, "FIELD CURVATURE") is None:
        notes.append("FAIL: no FIELD CURVATURE panel in field_curvature mode")
        passed = False
    if _panel_by_title(fc_axes, "DISTORTION") is not None:
        notes.append("FAIL: field_curvature mode still draws a DISTORTION panel (not split)")
        passed = False

    # B. distortion: exactly one panel, DISTORTION, no FIELD CURVATURE sibling.
    if len(dist_axes) != 1:
        notes.append(f"FAIL: distortion drew {len(dist_axes)} panels, expected 1 (concepts are split)")
        passed = False
    if _panel_by_title(dist_axes, "DISTORTION") is None:
        notes.append("FAIL: no DISTORTION panel in distortion mode")
        passed = False
    if _panel_by_title(dist_axes, "FIELD CURVATURE") is not None:
        notes.append("FAIL: distortion mode still draws a FIELD CURVATURE panel (not split)")
        passed = False

    if not passed:
        return False, notes

    # C. Field on the vertical axis (0..max) with a vertical x=0 reference line.
    for name, panel in (("field-curvature", fc_ax), ("distortion", dist_ax)):
        y_lo, y_hi = panel.get_ylim()
        if not (abs(y_lo) < 1e-6 and y_hi > 0):
            notes.append(f"FAIL: {name} field axis not vertical 0..max (ylim={y_lo:.3g}..{y_hi:.3g})")
            passed = False
        if not _has_axis_line(panel):
            notes.append(f"FAIL: {name} panel has no vertical x=0 reference line")
            passed = False

    # D. FC panel has both T and S curves; distortion panel has its curve.
    fc_curves = [line for line in fc_ax.lines if len(line.get_xdata()) > 2]
    if len(fc_curves) < 2:
        notes.append(f"FAIL: field-curvature panel has {len(fc_curves)} curves, expected T and S")
        passed = False
    dist_curves = [line for line in dist_ax.lines if len(line.get_xdata()) > 2]
    if len(dist_curves) < 1:
        notes.append(f"FAIL: distortion panel has {len(dist_curves)} curves, expected 1")
        passed = False

    if verbose:
        notes.append(
            f"fc_axes={len(fc_axes)}, dist_axes={len(dist_axes)}, "
            f"fc_curves={len(fc_curves)}, dist_curves={len(dist_curves)}"
        )
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        print(note)
    if passed:
        print("[PASS] Field Curvature and Distortion render as two separate single-panel items")
        return 0
    print("[FAIL] Field-curvature/distortion split-panel guard")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
