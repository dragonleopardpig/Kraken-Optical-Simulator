"""Guard for Open 3D Variable-thickness Best Focus / Best Collimation solve.

Brings the 2D "mark a thickness Variable, solve for best image" workflow into
the embedded Open 3D inspector and adds a net-new Best Collimation objective.
A thickness is flagged Variable through the shared
``SurfaceRow.optimize_thickness`` flag -- the same flag the 2D optimization path
uses -- so a gap flagged in 3D shows up Variable in 2D and vice versa.

Checks
------
Source contracts (always run, no display):
A. ``Open3DSolveService`` exposes the public API (gaps / Variable flag / solve).
B. the editor mixin exposes the collimation metric + result methods alongside
   the reused Best Focus solver.
C. the inspector wires ``_open3d_solve_service`` / toggle / run, and the run
   hook captures history and retraces.
D. the live-controls panel builds the Solve section.

Engine behaviour (display-free snapshot editor; machine-vision layouts):
E. the Variable flag is the shared ``optimize_thickness``; the terminal Image
   gap is never a target; Best Focus excludes the object gap while Best
   Collimation includes it.
F. the paraxial collimation vergence metric is V-shaped and ~0 at the solved
   object distance, which lands near the front focal distance (EFL - ppa).
G. solving Best Collimation via the service moves the object gap toward the
   focal point and lowers the output vergence.
H. solving Best Focus via the service moves the variable thickness and lowers
   the spot RMS.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_thickness_solve

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import dataclasses
import inspect
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LAYOUT_DIR = PROJECT_ROOT / "KrakenOS" / "common_optical_layouts"
LAYOUTS = [
    "machine_vision_150mm_datasheet_1x.py",
    "machine_vision_150mm_datasheet_0_5x.py",
    "machine_vision_120mm_pyrite_datasheet_1x.py",
    "machine_vision_85mm_pyrite_datasheet_1x.py",
    "machine_vision_150mm_measured.py",
]

# Best Focus reuses the existing 2D sequential spot-RMS solver, which is already
# guarded across layouts by validate_nonseq_best_image_solve + comprehensive
# phases 7/9. Here we only verify the *service delegation* (variable flag, gap
# selection, thickness mutation), so we exercise it on one fast layout -- the
# sequential metric is expensive headless on the pyrite/measured layouts and is
# not the thing under test for this feature.
_FOCUS_DELEGATION_LAYOUT = "machine_vision_150mm_datasheet_1x.py"

# An output vergence below this is collimated for all practical purposes
# (image distance > 1 m): |1/s'| < 1e-3 /mm.
_COLLIMATED_TOL = 1e-3


def _snapshot_for(fname: str):
    from KrakenOS.UI.render_layout_snapshot import (
        _load_layout_module,
        _rows_from_layout_info,
        _snapshot_editor,
    )

    path = LAYOUT_DIR / fname
    module = _load_layout_module(path)
    surfaces = list(getattr(module, "SURFACES", []) or [])
    settings = dict(getattr(module, "SETTINGS", {}) or {})
    rows = _rows_from_layout_info({"surfaces": surfaces})
    editor = _snapshot_editor(rows, settings)
    editor._normalize_special_rows()
    # The sequential Best Focus metric reads this Tk-backed filter attr; the
    # snapshot editor has no live Tk, so seed it (real inspector sets it itself).
    editor._best_image_last_filter_text = ""
    return editor


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    passed = True

    from KrakenOS.UI.services.open3d_solve import COLLIMATION, FOCUS, Open3DSolveService

    # --- A: solve service public API -------------------------------------
    for attr in (
        "thickness_gap_rows", "is_variable", "set_variable", "toggle_variable",
        "variable_rows", "_valid_rows_for", "solve",
    ):
        if not hasattr(Open3DSolveService, attr):
            notes.append(f"FAIL: Open3DSolveService missing {attr}")
            passed = False
    if (FOCUS, COLLIMATION) != ("focus", "collimation"):
        notes.append(f"FAIL: solve objective constants changed: {FOCUS!r}, {COLLIMATION!r}")
        passed = False

    # --- B: editor mixin methods -----------------------------------------
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    for attr in (
        "_collimation_output_vergence_for_rows", "_collimation_search_interval",
        "_compute_best_collimation_result", "_compute_best_focus_result",
    ):
        if not hasattr(KrakenLayoutEditor, attr):
            notes.append(f"FAIL: editor missing {attr}")
            passed = False

    # --- C: inspector wiring + retrace contract --------------------------
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    for attr in (
        "_open3d_solve_service", "_open3d_toggle_variable_thickness",
        "_open3d_run_thickness_solve",
    ):
        if not hasattr(Kraken3DInspector, attr):
            notes.append(f"FAIL: inspector missing {attr}")
            passed = False
    try:
        run_src = inspect.getsource(Kraken3DInspector._open3d_run_thickness_solve)
    except Exception as exc:
        run_src = ""
        notes.append(f"FAIL: cannot read _open3d_run_thickness_solve: {exc!r}")
        passed = False
    for marker in (
        "_begin_history_capture", "_commit_history_capture", "_sync_table",
        "refresh_from_editor",
    ):
        if marker not in run_src:
            notes.append(f"FAIL: solve run hook missing {marker} (history/retrace contract)")
            passed = False

    # --- D: live-controls panel section ----------------------------------
    from KrakenOS.UI.panels.open3d_live_controls import Open3DLiveControlsPanel
    if not hasattr(Open3DLiveControlsPanel, "build_solve_controls"):
        notes.append("FAIL: live-controls panel missing build_solve_controls")
        passed = False
    else:
        try:
            build_src = inspect.getsource(Open3DLiveControlsPanel.build)
        except Exception:
            build_src = ""
        if "build_solve_controls" not in build_src:
            notes.append("FAIL: panel build() does not place the Solve section")
            passed = False

    # --- E-H: engine behaviour across machine-vision layouts -------------
    class _Insp:
        def __init__(self, editor):
            self.editor = editor

    for fname in LAYOUTS:
        if not (LAYOUT_DIR / fname).exists():
            notes.append(f"SKIP: {fname} missing")
            continue
        try:
            editor = _snapshot_for(fname)
        except Exception as exc:
            notes.append(f"FAIL[{fname}]: cannot snapshot layout: {exc!r}")
            passed = False
            continue

        if editor._current_object_mode() != "Finite":
            notes.append(f"SKIP[{fname}]: object mode is not Finite (collimation N/A)")
            continue

        svc = Open3DSolveService(_Insp(editor))
        wl = editor._current_wavelength()
        gaps = [i for i, _label in svc.thickness_gap_rows()]

        # E: the Image gap is never a target; the flag is shared.
        if any(str(editor.rows[i].surface) == "Image" for i in gaps):
            notes.append(f"FAIL[{fname}]: thickness_gap_rows included the Image gap")
            passed = False
        if 0 not in gaps:
            notes.append(f"FAIL[{fname}]: object gap (row 0) missing from gaps")
            passed = False
            continue
        svc.set_variable(0, True)
        if editor.rows[0].optimize_thickness is not True:
            notes.append(f"FAIL[{fname}]: set_variable did not write the shared optimize_thickness flag")
            passed = False
        if svc._valid_rows_for(FOCUS):
            notes.append(f"FAIL[{fname}]: Best Focus accepted the object gap (should be collimation-only)")
            passed = False
        if svc._valid_rows_for(COLLIMATION) != [0]:
            notes.append(f"FAIL[{fname}]: Best Collimation did not accept the object gap")
            passed = False

        # F: collimation metric is V-shaped + ~0 at the solved object distance.
        start_obj = float(editor.rows[0].thickness)

        def _verg(obj_distance: float) -> float:
            trial = [dataclasses.replace(r) for r in editor.rows]
            trial[0].thickness = float(obj_distance)
            return float(editor._collimation_output_vergence_for_rows(trial, wl))

        v_start = _verg(start_obj)
        try:
            result = editor._compute_best_collimation_result(0)
        except Exception as exc:
            notes.append(f"FAIL[{fname}]: _compute_best_collimation_result raised: {exc!r}")
            passed = False
            continue
        solved = float(result["solved_distance"])
        v_solved = float(result["best_metric"])
        if not (np.isfinite(solved) and solved >= 0.0):
            notes.append(f"FAIL[{fname}]: collimation solved distance not valid: {solved}")
            passed = False
        if v_solved >= _COLLIMATED_TOL:
            notes.append(f"FAIL[{fname}]: collimation output vergence {v_solved:.4g} not ~0 (image not at infinity)")
            passed = False
        if v_solved >= v_start:
            notes.append(f"FAIL[{fname}]: collimation did not reduce vergence ({v_start:.4g} -> {v_solved:.4g})")
            passed = False
        # V-shape: stepping either side of the solved point raises the metric.
        bracket = max(10.0, 0.25 * solved)
        if not (_verg(max(0.0, solved - bracket)) > v_solved and _verg(solved + bracket) > v_solved):
            notes.append(f"FAIL[{fname}]: collimation metric is not V-shaped around the solved point")
            passed = False
        # The collimated object distance sits near the front focal distance.
        try:
            effl = float(editor._exact_paraxial_cardinals()[0])
            ppa = float(editor._exact_paraxial_solution_for_rows(editor.rows, wl)[5])
            front_focal = abs(effl) - ppa
            if abs(solved - front_focal) > max(2.0, 0.05 * abs(front_focal)):
                notes.append(
                    f"FAIL[{fname}]: collimation obj {solved:.4g} != front focal {front_focal:.4g}"
                )
                passed = False
        except Exception as exc:  # pragma: no cover - defensive
            notes.append(f"FAIL[{fname}]: front-focal cross-check raised: {exc!r}")
            passed = False

        # G: collimation solve through the service mutates the object gap.
        editor.rows[0].thickness = start_obj
        ok_c, msg_c = svc.solve(COLLIMATION)
        if not ok_c:
            notes.append(f"FAIL[{fname}]: service Best Collimation solve failed: {msg_c}")
            passed = False
        else:
            moved = float(editor.rows[0].thickness)
            if abs(moved - solved) > max(0.5, 1e-3 * abs(solved)):
                notes.append(f"FAIL[{fname}]: service collimation moved object to {moved:.4g}, expected ~{solved:.4g}")
                passed = False
            if _verg(moved) >= v_start:
                notes.append(f"FAIL[{fname}]: service collimation did not lower the vergence")
                passed = False

        if verbose:
            notes.append(
                f"{fname}: collimation obj {start_obj:.4g}->{solved:.4g} mm "
                f"(vergence {v_start:.3g}->{v_solved:.3g})"
            )

    # --- H: Best Focus delegation (single fast layout) -------------------
    # The object gap is collimation-only, so Best Focus drives the last gap
    # before Image (the back working distance) -- the classic focus knob.
    if (LAYOUT_DIR / _FOCUS_DELEGATION_LAYOUT).exists():
        try:
            editor = _snapshot_for(_FOCUS_DELEGATION_LAYOUT)
            svc = Open3DSolveService(_Insp(editor))
            gaps = [i for i, _label in svc.thickness_gap_rows()]
            focus_row = gaps[-1]
            start_focus = float(editor.rows[focus_row].thickness)
            svc.set_variable(focus_row, True)
            if svc._valid_rows_for(FOCUS) != [focus_row]:
                notes.append(f"FAIL[focus]: Best Focus did not accept gap {focus_row}")
                passed = False
            ok_f, msg_f = svc.solve(FOCUS)
            if not ok_f:
                notes.append(f"FAIL[focus]: service Best Focus solve failed: {msg_f}")
                passed = False
            else:
                moved_focus = float(editor.rows[focus_row].thickness)
                if abs(moved_focus - start_focus) <= 1e-6:
                    notes.append(f"FAIL[focus]: Best Focus did not move gap {focus_row}")
                    passed = False
                if "spot RMS" not in msg_f:
                    notes.append(f"FAIL[focus]: Best Focus message missing spot RMS: {msg_f}")
                    passed = False
                if verbose:
                    notes.append(
                        f"{_FOCUS_DELEGATION_LAYOUT}: focus gap {focus_row} "
                        f"{start_focus:.4g}->{moved_focus:.4g} mm"
                    )
        except Exception as exc:
            notes.append(f"FAIL[focus]: Best Focus delegation raised: {exc!r}")
            passed = False

    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        print(note)
    if passed:
        print("[PASS] Open 3D Variable-thickness Best Focus / Best Collimation solve")
        return 0
    print("[FAIL] Open 3D thickness-solve guard")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
