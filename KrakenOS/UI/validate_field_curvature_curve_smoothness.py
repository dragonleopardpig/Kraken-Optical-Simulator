"""Guard: the Field Curvature T/S curves draw as smooth arcs (bug 0043).

The tangential (T) best-focus curve bends hard near the edge field. At the raw
~0.7 deg field-sample spacing that fast-curving region rendered as straight
chords with visible corners -- the user's "T-curve not smooth" report. The fix
resamples the aggregated samples onto a dense field grid with a shape-preserving
monotone cubic (PCHIP) in ``AnalysisPlotService._field_curve_xy`` so the drawn
line is a smooth arc that still passes through every real sample (the genuine
edge turnover is kept, not flattened).

This display-free guard renders the Field Curvature panel on the Double Gauss
case-study layout and asserts, on the *actually drawn* solid T line:
  A. it is densified (>> the raw field-sample count) -- proves PCHIP is active;
  B. it is smooth -- the maximum turning angle between consecutive segments,
     measured in panel-fraction space, is small (chords spike at the turnover);
  C. the edge turnover is preserved -- the dense value range matches the raw
     focus range (PCHIP did not flatten or wildly overshoot the inflection).

SKIPs cleanly if the analysis is unavailable on a given clone.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import numpy as np
from matplotlib.figure import Figure

from KrakenOS.UI.layout_editor import (
    LAYOUTS_DIR,
    KrakenLayoutEditor,
    _load_python_data,
    _load_python_title,
)
from KrakenOS.UI.render_layout_snapshot import _build_runtime_system, _snapshot_editor
from KrakenOS.UI.services.analysis_plot import AnalysisPlotService

LAYOUT_TITLE = "Zemax Double Gauss 28 Degree Field"

# A densified PCHIP curve has hundreds of points; the raw aggregated scan has
# ~21. Require clearly more than the raw count.
MIN_DENSE_POINTS = 100
# Maximum turning angle (deg) between consecutive segments in panel-fraction
# space. The smooth 480-point dense curve peaks ~3.8 deg at the edge turnover;
# the old 21-point chord rendering spiked to ~33 deg there. 12 deg sits with
# clear margin on both sides.
MAX_TURN_DEG = 12.0
# The dense curve must reproduce the raw focus range (turnover not flattened),
# without overshooting it by more than a little.
RANGE_LO, RANGE_HI = 0.9, 1.08


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


def _max_turn_deg(x: np.ndarray, y: np.ndarray, x_half: float, y_span: float) -> float:
    """Largest direction change (deg) between consecutive segments, measured in
    panel-fraction space so mm-vs-deg axis units do not skew the angle."""
    nx = x / max(x_half, 1e-12)
    ny = y / max(y_span, 1e-12)
    dx = np.diff(nx)
    dy = np.diff(ny)
    seg_len = np.hypot(dx, dy)
    keep = seg_len > 1e-12
    dirs = np.stack([dx[keep] / seg_len[keep], dy[keep] / seg_len[keep]], axis=1)
    if dirs.shape[0] < 2:
        return 0.0
    dots = np.clip(np.sum(dirs[:-1] * dirs[1:], axis=1), -1.0, 1.0)
    return float(np.degrees(np.max(np.arccos(dots))))


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

    captured: dict = {}
    original = AnalysisPlotService._sample_field_curvature_distortion

    def _wrap(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        if result is not None:
            captured["axis_results"] = result[0]
        return result

    AnalysisPlotService._sample_field_curvature_distortion = _wrap
    try:
        editor.figure = Figure(figsize=(6.0, 7.0))
        analysis_ax = editor.figure.add_subplot(111)
        editor.analysis_mode = "field_curvature"
        editor._analysis_ax = analysis_ax
        editor._analysis_axes = [analysis_ax]
        editor._plot_analysis(analysis_ax, system, None, 0.55)
        if any("unavailable" in str(getattr(t, "get_text", lambda: "")()) for t in analysis_ax.texts):
            notes.append("SKIP: field-curvature analysis unavailable on this clone")
            return passed, notes

        fc_axes = [
            ax for ax in editor.figure.axes
            if "FIELD CURVATURE" in str(ax.get_title()).upper()
        ]
        if not fc_axes:
            notes.append("FAIL: no FIELD CURVATURE panel was drawn")
            return False, notes
        fc_ax = fc_axes[0]
        x_lo, x_hi = fc_ax.get_xlim()
        y_lo, y_hi = fc_ax.get_ylim()
        x_half = 0.5 * (x_hi - x_lo)
        y_span = y_hi - y_lo

        # The solid line is T, the dashed line is S; both are curves (>2 points).
        curves = [ln for ln in fc_ax.lines if len(ln.get_xdata()) > 2]
        if len(curves) < 2:
            notes.append(f"FAIL: FC panel has {len(curves)} curves, expected T and S")
            return False, notes
        solid = [ln for ln in curves if ln.get_linestyle() in ("-", "solid")]
        t_line = solid[0] if solid else curves[0]
    finally:
        AnalysisPlotService._sample_field_curvature_distortion = original

    t_x = np.asarray(t_line.get_xdata(), dtype=float)
    t_y = np.asarray(t_line.get_ydata(), dtype=float)

    # A. Densified (PCHIP active).
    if t_x.size < MIN_DENSE_POINTS:
        notes.append(
            f"FAIL: T curve has {t_x.size} points (< {MIN_DENSE_POINTS}); "
            f"PCHIP densification appears to be off -- chords will show corners"
        )
        passed = False

    # B. Smooth (no sharp corners).
    max_turn = _max_turn_deg(t_x, t_y, x_half, y_span)
    if max_turn > MAX_TURN_DEG:
        notes.append(
            f"FAIL: T curve has a sharp corner (max turning angle {max_turn:.2f} deg "
            f"> {MAX_TURN_DEG} deg) -- not smooth"
        )
        passed = False

    # C. Edge turnover preserved (range matches the raw focus samples).
    axis_results = captured.get("axis_results")
    range_ratio = float("nan")
    if axis_results and axis_results.get("Y") is not None:
        raw_focus = np.asarray(axis_results["Y"]["focus"], dtype=float)
        raw_range = float(np.max(raw_focus) - np.min(raw_focus))
        dense_range = float(np.max(t_x) - np.min(t_x))
        if raw_range > 1e-9:
            range_ratio = dense_range / raw_range
            if not (RANGE_LO <= range_ratio <= RANGE_HI):
                notes.append(
                    f"FAIL: T curve range {dense_range:.4g} mm vs raw {raw_range:.4g} mm "
                    f"(ratio {range_ratio:.3f}); turnover flattened or overshot"
                )
                passed = False

    if verbose:
        notes.append(
            f"T points={t_x.size}, max_turn={max_turn:.2f}deg, "
            f"range_ratio={range_ratio:.3f}"
        )
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        print(note)
    if passed:
        print("[PASS] Field Curvature T/S curves draw as smooth arcs")
        return 0
    print("[FAIL] Field-curvature curve-smoothness guard")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
