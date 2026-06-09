"""Guard: Field Curvature / Distortion curves are physically correct (bug 0042).

Bug 0037 gave the analysis the right two-panel *layout*, but the curve values
were still wrong in two ways:

1. **Distortion did not pass through the origin.** It was referenced to a global
   least-squares slope through the image-height-vs-field samples, so the fitted
   "ideal" line did not match the paraxial chief-ray magnification. The percent
   distortion came out non-zero (and even non-monotone) near the axis. Distortion
   must be referenced to the *paraxial* magnification (h/f as field -> 0), which
   makes it identically zero on axis and grow with field.

2. **Tangential (T) and sagittal (S) field curvature were identical.** The two
   curves were sampled from two independent field scans -- one along +X and one
   along +Y -- and each measured the in-plane spread. On a rotationally symmetric
   lens those two scans are the same measurement (both tangential), so T and S
   coincided and the astigmatism vanished. The fix scans a single meridional (+Y)
   field and, at each field, traces *isolated* pupil fans: a pupil-Y fan gives the
   tangential focus from its in-plane (Y) convergence and a pupil-X fan gives the
   sagittal focus from its X convergence. Their separation is the astigmatism
   Zemax draws as the T/S gap. (Reading both spreads off one full 2D bundle let
   off-axis coma bleed into the tangential estimate and pulled T toward S, leaving
   the tangential curve jagged/"weird"; isolated fans keep each focus clean and
   the T curve smooth. The distortion image height is taken from the chief ray.)

This guard locks in the corrected *numbers* (the sibling
``validate_field_curvature_distortion_panels`` guards the layout). All checks are
display-free (Agg backend, no Xvfb / GPU needed):

A. Distortion passes through the origin: |distortion| at the on-axis field is ~0.
B. Distortion grows with field: |distortion| at the field edge clearly exceeds
   |distortion| at the smallest non-zero field (and is meaningfully non-zero).
C. Astigmatism is present: the tangential and sagittal best-focus curves differ
   (max |T - S| over the field is well above the numerical-noise floor).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_field_curvature_astigmatism_distortion

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

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
from KrakenOS.UI.services.analysis_plot import AnalysisPlotService

# The 28-degree Zemax double gauss has a real 14-deg half-field, so its chief-ray
# distortion (~1.1% at the edge) and astigmatic T/S split (~0.09 mm) are both
# meaningfully present -- it exercises every check. (The PSF/MTF case-study layout
# carries no field setting, so it falls back to a small field where the true
# distortion is sub-0.01% and cannot exercise the distortion checks.)
LAYOUT_TITLE = "Zemax Double Gauss 28 Degree Field"

# Numeric thresholds, chosen from the corrected curves with wide margins so the
# guard is robust to small sampling jitter but still fails the old behaviour
# (which had |edge distortion| < |near-axis distortion| and max|T - S| ~ 1e-4 mm).
ON_AXIS_DISTORTION_TOL = 0.05      # percent; corrected value is ~0.0
MIN_EDGE_DISTORTION = 0.3          # percent; corrected value is ~1.1
ASTIGMATISM_MIN_SPLIT = 0.03       # mm; corrected value is ~0.09, old bug ~1e-4


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


def _capture_axis_results(editor, system) -> "dict | None":
    """Render the field-curvature analysis and capture the sampled axis_results.

    Field curvature and distortion now render as two separate single-panel modes,
    but both draw from the same sampler ``_sample_field_curvature_distortion``,
    which returns ``(axis_results, field_type, field_limit)``. That sampler lives
    on ``AnalysisPlotService`` (the editor delegates to it), so the capture wrapper
    is installed at class level and always restored in the ``finally`` block.
    """
    captured: dict = {}
    original = AnalysisPlotService._sample_field_curvature_distortion

    def _wrap(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        if result is not None:
            captured["axis_results"] = result[0]
        return result

    AnalysisPlotService._sample_field_curvature_distortion = _wrap
    try:
        editor.figure = Figure(figsize=(6.0, 3.2))
        analysis_ax = editor.figure.add_subplot(111)
        editor.analysis_mode = "field_curvature"
        editor._analysis_ax = analysis_ax
        editor._analysis_axes = [analysis_ax]
        editor._plot_analysis(analysis_ax, system, None, 0.55)
        if any("unavailable" in str(getattr(t, "get_text", lambda: "")()) for t in analysis_ax.texts):
            return None
    finally:
        AnalysisPlotService._sample_field_curvature_distortion = original
    return captured.get("axis_results")


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

    axis_results = _capture_axis_results(editor, system)
    if not axis_results:
        notes.append("SKIP: field-curvature analysis unavailable on this clone")
        return passed, notes

    tangential = axis_results.get("Y")
    sagittal = axis_results.get("X")
    if tangential is None or sagittal is None:
        notes.append("FAIL: axis_results missing tangential (Y) or sagittal (X) series")
        return False, notes

    fields = np.asarray(tangential["fields"], dtype=float)
    distortion = np.asarray(tangential["distortion"], dtype=float)
    t_focus = np.asarray(tangential["focus"], dtype=float)
    s_focus = np.asarray(sagittal["focus"], dtype=float)
    if fields.size < 2:
        notes.append("FAIL: fewer than 2 field samples")
        return False, notes

    order = np.argsort(np.abs(fields))
    abs_fields = np.abs(fields)[order]
    distortion = distortion[order]
    t_focus = t_focus[order]
    s_focus = s_focus[order]

    on_axis = int(np.argmin(abs_fields))
    nonzero = np.flatnonzero(abs_fields > 1e-9)
    if nonzero.size < 1:
        notes.append("FAIL: no off-axis field samples")
        return False, notes
    near_axis = int(nonzero[0])
    edge = int(nonzero[-1])

    # A. Distortion passes through the origin.
    on_axis_dist = abs(float(distortion[on_axis]))
    if on_axis_dist > ON_AXIS_DISTORTION_TOL:
        notes.append(
            f"FAIL: distortion does not pass through origin "
            f"(|dist| at field {abs_fields[on_axis]:.3g} = {on_axis_dist:.4g}%, "
            f"tol {ON_AXIS_DISTORTION_TOL}%)"
        )
        passed = False

    # B. Distortion grows with field magnitude.
    near_dist = abs(float(distortion[near_axis]))
    edge_dist = abs(float(distortion[edge]))
    if edge_dist < MIN_EDGE_DISTORTION:
        notes.append(
            f"FAIL: edge distortion too small to be meaningful "
            f"(|dist| at field {abs_fields[edge]:.3g} = {edge_dist:.4g}%)"
        )
        passed = False
    if edge_dist <= near_dist:
        notes.append(
            f"FAIL: distortion does not grow with field "
            f"(near-axis |dist|={near_dist:.4g}% at {abs_fields[near_axis]:.3g}, "
            f"edge |dist|={edge_dist:.4g}% at {abs_fields[edge]:.3g})"
        )
        passed = False

    # C. Astigmatism: tangential and sagittal focus curves diverge.
    max_split = float(np.max(np.abs(t_focus - s_focus)))
    if max_split < ASTIGMATISM_MIN_SPLIT:
        notes.append(
            f"FAIL: no astigmatism -- tangential and sagittal coincide "
            f"(max|T-S|={max_split:.5g} mm, need >= {ASTIGMATISM_MIN_SPLIT} mm)"
        )
        passed = False

    if verbose:
        notes.append(
            f"on-axis dist={on_axis_dist:.4g}%, near={near_dist:.4g}%, "
            f"edge={edge_dist:.4g}%, max|T-S|={max_split:.4g}mm, "
            f"fields={np.round(abs_fields, 2).tolist()}"
        )
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        print(note)
    if passed:
        print("[PASS] Field Curvature / Distortion curves are physically correct")
        return 0
    print("[FAIL] Field-curvature distortion/astigmatism guard")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
