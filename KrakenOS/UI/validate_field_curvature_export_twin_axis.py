"""Guard: the high-res click-export keeps twin-axis overlays (bug 0035).

Clicking an analysis plot exports it to a high-resolution image via
``_open_high_res_plot_in_system_viewer``. To isolate the clicked axis the export
used to hide *every other* axis in the figure -- but a secondary-axis series
lives on a second ``twinx``/``twiny`` axis (the "different after click" report),
so the overlay was dropped on click. The fix (``_high_res_export_kept_axes``)
keeps any axis that *shares an axis* with the clicked one.

This used to be guarded through the field-curvature plot, whose distortion panel
shared the field axis. Field curvature and distortion are now two separate
single-panel modes (neither carries a twin), so this guard exercises the same
export logic through the atmosphere analysis, whose dispersion series is drawn on
a real ``twinx`` overlay sharing the primary's x-axis. An unrelated standalone
axis is added to the figure so the keep-set is shown to discriminate shared-axis
siblings (kept) from unrelated axes (hidden), not merely keep everything.

All checks are display-free (Agg backend, no Xvfb / GPU needed):

A. The atmosphere analysis builds a second (dispersion) twin axis.
B. That twin shares the primary's x-axis and carries a plotted artist.
C. ``_high_res_export_kept_axes(primary)`` keeps the primary and its twin but
   NOT an unrelated standalone axis.
D. The export hide-pass (hide everything not kept) leaves the twin visible and
   hides the unrelated axis.

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
    editor.analysis_mode = "atmosphere"
    editor._analysis_ax = analysis_ax
    editor._analysis_axes = [analysis_ax]
    editor._plot_analysis(analysis_ax, system, None, wavelength)

    # If the analysis itself could not run on this clone, that is not bug 0035.
    if any("unavailable" in str(getattr(t, "get_text", lambda: "")()) for t in analysis_ax.texts):
        notes.append("SKIP: atmosphere analysis unavailable on this clone")
        return passed, notes

    # An unrelated standalone axis: it shares no axis with the clicked one, so the
    # export must drop it. Without it the hide-pass check is vacuous.
    unrelated_ax = editor.figure.add_axes([0.0, 0.0, 0.01, 0.01])
    unrelated_ax.plot([0, 1], [0, 1])

    fig_axes = list(editor.figure.axes)

    # A. A second (dispersion) twin axis was created by the analysis.
    twins = [ax for ax in fig_axes if ax not in (analysis_ax, unrelated_ax)]
    if not twins:
        notes.append("FAIL: atmosphere plot created no second (dispersion) twin axis")
        return False, notes
    twin_ax = twins[0]

    # B. The twin shares the primary's x-axis and carries a plotted artist.
    siblings = list(analysis_ax.get_shared_x_axes().get_siblings(analysis_ax))
    if twin_ax not in siblings:
        notes.append("FAIL: dispersion twin does not share the primary x-axis")
        passed = False
    if not (list(twin_ax.lines) or list(twin_ax.collections)):
        notes.append("FAIL: dispersion twin has no plotted artists")
        passed = False

    # C. The export keep-set includes the primary + twin but not the unrelated axis.
    kept = editor._high_res_export_kept_axes(analysis_ax)
    if analysis_ax not in kept:
        notes.append("FAIL: export keep-set is missing the clicked axis")
        passed = False
    if twin_ax not in kept:
        notes.append("FAIL: export keep-set drops the twin axis (bug 0035)")
        passed = False
    if unrelated_ax in kept:
        notes.append("FAIL: export keep-set wrongly keeps an unrelated axis")
        passed = False

    # D. The export hide-pass keeps the twin visible and hides the unrelated axis.
    would_hide = [ax for ax in fig_axes if ax not in kept]
    if twin_ax in would_hide:
        notes.append("FAIL: dispersion twin would be hidden by the export hide-pass")
        passed = False
    if unrelated_ax not in would_hide:
        notes.append("FAIL: unrelated axis would survive the export hide-pass")
        passed = False

    if verbose:
        notes.append(
            f"axes={len(fig_axes)}, twin lines={len(list(twin_ax.lines))}, "
            f"kept={len(kept)}, would_hide={len(would_hide)}"
        )
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        print(note)
    if passed:
        print("[PASS] High-res export keeps twin-axis overlays")
        return 0
    print("[FAIL] High-res export twin-axis guard")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
