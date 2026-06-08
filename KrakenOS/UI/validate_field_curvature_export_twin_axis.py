"""Guard: the high-res click-export keeps the field-curvature distortion panel.

Clicking the analysis plot exports it to a high-resolution image via
``_open_high_res_plot_in_system_viewer``. To isolate the clicked axis the export
used to hide *every other* axis in the figure -- but the distortion lives on a
second axis (the "different after click" report). The field-curvature plot now
draws the Zemax two-panel layout (FIELD CURVATURE | DISTORTION) where the
distortion panel shares the *field* (y) axis with the host panel. This guards
bug 0035: any axis that shares an axis with the clicked one must stay visible in
the export, so the distortion panel can never be dropped on click.

All checks are display-free (Agg backend, no Xvfb / GPU needed):

A. The field-curvature analysis builds a second (distortion) panel axis.
B. That panel shares the primary's field (y) axis.
C. ``_high_res_export_kept_axes(primary)`` keeps BOTH panels.
D. The export hide-pass (hide everything not kept) leaves the panel visible.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_field_curvature_export_twin_axis

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
    wavelength = 0.55

    editor.figure = Figure(figsize=(6.0, 3.2))
    analysis_ax = editor.figure.add_subplot(111)
    editor.analysis_mode = "field_curvature"
    editor._analysis_ax = analysis_ax
    editor._analysis_axes = [analysis_ax]
    editor._plot_analysis(analysis_ax, system, None, wavelength)

    # If the analysis itself could not run on this clone, that is not bug 0035.
    if any("unavailable" in str(getattr(t, "get_text", lambda: "")()) for t in analysis_ax.texts):
        notes.append("SKIP: field-curvature analysis unavailable on this clone")
        return passed, notes

    fig_axes = list(editor.figure.axes)

    # A. A second (distortion) panel axis was created.
    panels = [ax for ax in fig_axes if ax is not analysis_ax]
    if not panels:
        notes.append("FAIL: field-curvature plot created no second (distortion) panel")
        return False, notes
    distortion_panel = panels[0]

    # B. The distortion panel shares the primary's field (y) axis.
    siblings = list(analysis_ax.get_shared_y_axes().get_siblings(analysis_ax))
    if distortion_panel not in siblings:
        notes.append("FAIL: distortion panel does not share the field (y) axis")
        passed = False

    # The panel actually carries the plotted distortion curve, so keeping it matters.
    if not (list(distortion_panel.lines) or list(distortion_panel.collections)):
        notes.append("FAIL: distortion panel has no plotted artists")
        passed = False

    # C. The export keep-set includes BOTH panels (regression: old code kept only the clicked axis).
    kept = editor._high_res_export_kept_axes(analysis_ax)
    if analysis_ax not in kept:
        notes.append("FAIL: export keep-set is missing the clicked axis")
        passed = False
    if distortion_panel not in kept:
        notes.append("FAIL: export keep-set drops the distortion panel (bug 0035)")
        passed = False

    # D. The export hide-pass (hide everything not kept) leaves the panel visible.
    would_hide = [ax for ax in fig_axes if ax not in kept]
    if distortion_panel in would_hide:
        notes.append("FAIL: distortion panel would be hidden by the export hide-pass")
        passed = False

    if verbose:
        notes.append(
            f"axes={len(fig_axes)}, panel lines={len(list(distortion_panel.lines))}, "
            f"kept={len(kept)}, would_hide={len(would_hide)}"
        )
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        print(note)
    if passed:
        print("[PASS] Field-curvature high-res export keeps the distortion panel")
        return 0
    print("[FAIL] Field-curvature export distortion-panel guard")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
