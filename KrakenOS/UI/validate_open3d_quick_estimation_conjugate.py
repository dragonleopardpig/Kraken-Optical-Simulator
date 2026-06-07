"""Guard for Quick Estimation -- live object/image conjugate + FOV solve.

Checks
------
Source contracts (always run):
A. ``QuickEstimationService`` exposes the role model + ``solve_dependent`` +
   ``current_state`` + ``update_readout``.
B. ``apply_dimension_value`` invokes the Quick Estimation solve.
C. the inspector owns ``quick_estimation_var`` + ``_quick_estimation_service``.

Engine (needs a display; SKIP otherwise):
D. for each machine-vision layout, with Quick Estimation on: sweeping the
   Object Thickness and solving the dependent Image Thickness keeps the image
   in focus (the solved image gap reproduces the paraxial conjugate), the
   magnification matches sensor/FOV, and FOV grows monotonically as the object
   moves away. The reverse direction (drive Image Thickness) solves the object.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_quick_estimation_conjugate

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""
from __future__ import annotations

import inspect
import os
from pathlib import Path

os.environ.pop("WAYLAND_DISPLAY", None)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LAYOUT_DIR = PROJECT_ROOT / "KrakenOS" / "common_optical_layouts"
LAYOUTS = [
    "machine_vision_150mm_datasheet_1x.py",
    "machine_vision_150mm_datasheet_0_5x.py",
    "machine_vision_120mm_pyrite_datasheet_1x.py",
    "machine_vision_85mm_pyrite_datasheet_1x.py",
    "machine_vision_150mm_measured.py",
]


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    passed = True

    from KrakenOS.UI.services.quick_estimation import QuickEstimationService
    from KrakenOS.UI.services.open3d_thickness_dimensions import Open3DThicknessDimensionService

    # A
    for attr in ("solve_dependent", "current_state", "update_readout", "set_role", "is_enabled"):
        if not hasattr(QuickEstimationService, attr):
            notes.append(f"FAIL: QuickEstimationService missing {attr}")
            passed = False
    # B
    try:
        adv_src = inspect.getsource(Open3DThicknessDimensionService.apply_dimension_value)
    except Exception as exc:
        adv_src = ""
        notes.append(f"FAIL: cannot read apply_dimension_value: {exc!r}")
        passed = False
    if "_quick_estimation_service" not in adv_src or "solve_dependent" not in adv_src:
        notes.append("FAIL: apply_dimension_value does not invoke the Quick Estimation solve")
        passed = False
    # C -- inspector wiring + right-click role menu (Phase B).
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    for attr in (
        "_quick_estimation_service",
        "_maybe_show_quick_estimation_role_menu",
        "_show_quick_estimation_role_menu",
        "_set_quick_estimation_role",
        "_thickness_dimension_row_under_cursor",
    ):
        if not hasattr(Kraken3DInspector, attr):
            notes.append(f"FAIL: inspector missing {attr}")
            passed = False
    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService
    try:
        menu_src = inspect.getsource(Open3DFaceAssignmentService._show_surface_function_context_menu)
    except Exception:
        menu_src = ""
    if "_maybe_show_quick_estimation_role_menu" not in menu_src:
        notes.append("FAIL: right-click menu does not offer Quick Estimation roles")
        passed = False
    # Live drag feedback (Phase D).
    try:
        drag_src = inspect.getsource(Open3DThicknessDimensionService.apply_drag_motion)
    except Exception:
        drag_src = ""
    if "preview_state" not in drag_src:
        notes.append("FAIL: apply_drag_motion lacks the Quick Estimation live preview")
        passed = False
    if not hasattr(QuickEstimationService, "preview_state"):
        notes.append("FAIL: QuickEstimationService missing preview_state")
        passed = False

    # D -- engine behaviour across the machine-vision layouts.
    from KrakenOS.UI.validate_open3d_analytic_lens_selection_snapshot import _ensure_display

    reuse = app is not None and inspector is not None
    xvfb_proc = None
    if not reuse:
        xvfb_proc, env_err = _ensure_display()
        if env_err is not None:
            notes.append(f"SKIP: cannot construct UI ({env_err})")
            return passed, notes

    own_app = False
    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.render_layout_snapshot import _load_layout_module, _rows_from_layout_info

        if not reuse:
            from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _open_inspector

            app = KrakenLayoutEditor()
            inspector = _open_inspector(app)
            own_app = True

        qe = inspector._quick_estimation_service()
        inspector.quick_estimation_var.set(True)

        for fname in LAYOUTS:
            path = LAYOUT_DIR / fname
            if not path.exists():
                notes.append(f"SKIP: {fname} missing")
                continue
            module = _load_layout_module(path)
            surfaces = list(getattr(module, "SURFACES", []) or [])
            app.rows = _rows_from_layout_info({"surfaces": surfaces})
            app._apply_layout_settings(dict(getattr(module, "SETTINGS", {}) or {}))
            app._sync_table()

            nom_obj = float(app.rows[0].thickness)
            img_row = qe.image_thickness_row()

            # forward sweep: drive Object Thickness, solve Image Thickness.
            fovs = []
            for factor in (0.8, 1.0, 1.25, 1.6):
                app.rows[0].thickness = nom_obj * factor
                ok, _note = qe.solve_dependent(0)
                if not ok:
                    notes.append(f"FAIL[{fname}]: solve_dependent(object) failed at factor {factor}")
                    passed = False
                    continue
                # the solved image gap must reproduce the paraxial conjugate.
                result = app._compute_paraxial_solve_result("image")
                solved = float(result["solved_distance"])
                applied = float(app.rows[img_row].thickness)
                if abs(applied - solved) > max(0.05, 1e-3 * abs(solved)):
                    notes.append(f"FAIL[{fname}]: image gap {applied:.5g} != conjugate {solved:.5g}")
                    passed = False
                state = qe.current_state()
                if state["in_focus"] is not True:
                    notes.append(f"FAIL[{fname}]: not in focus after solve (factor {factor})")
                    passed = False
                # FOV must equal sensor / |m|.
                mag = state["magnification"]
                sensor = state["sensor_semi"]
                if mag and sensor and state["fov_semi"] is not None:
                    expect = sensor / abs(mag)
                    if abs(expect - state["fov_semi"]) > 1e-6 * max(1.0, expect):
                        notes.append(f"FAIL[{fname}]: FOV {state['fov_semi']:.5g} != sensor/|m| {expect:.5g}")
                        passed = False
                fovs.append((nom_obj * factor, state["fov_semi"]))

            # FOV grows as the object moves away (monotonic).
            clean = [f for _o, f in fovs if f is not None]
            if len(clean) >= 2 and any(b <= a for a, b in zip(clean, clean[1:])):
                notes.append(f"FAIL[{fname}]: FOV not monotonic with object distance: {clean}")
                passed = False

            # live drag preview must NOT mutate the committed thicknesses.
            app.rows[0].thickness = nom_obj
            qe.solve_dependent(0)
            committed_obj = float(app.rows[0].thickness)
            committed_img = float(app.rows[img_row].thickness)
            preview = qe.preview_state(0, nom_obj * 1.3)
            if preview is None:
                notes.append(f"FAIL[{fname}]: preview_state returned None")
                passed = False
            else:
                if abs(float(app.rows[0].thickness) - committed_obj) > 1e-9 or abs(
                    float(app.rows[img_row].thickness) - committed_img
                ) > 1e-9:
                    notes.append(f"FAIL[{fname}]: preview_state mutated the committed thicknesses")
                    passed = False
                if preview.get("image_distance") is None or preview.get("fov_full") is None:
                    notes.append(f"FAIL[{fname}]: preview_state missing image/FOV values")
                    passed = False

            # reverse direction: drive Image Thickness, solve Object Thickness.
            img_now = float(app.rows[img_row].thickness)
            app.rows[img_row].thickness = img_now * 1.1
            ok_rev, _note = qe.solve_dependent(img_row)
            if not ok_rev:
                notes.append(f"FAIL[{fname}]: reverse solve_dependent(image) failed")
                passed = False
            else:
                obj_after = float(app.rows[0].thickness)
                if not (obj_after > 0 and obj_after != nom_obj):
                    notes.append(f"FAIL[{fname}]: reverse solve did not move the object distance")
                    passed = False

            if verbose:
                notes.append(f"{fname}: forward FOV semi sweep = {[round(f, 3) if f else None for _o, f in fovs]}")

        if own_app:
            try:
                app.destroy()
            except Exception:
                pass
        return passed, notes
    finally:
        if xvfb_proc is not None:
            xvfb_proc.terminate()
            try:
                xvfb_proc.wait(timeout=5)
            except Exception:
                xvfb_proc.kill()


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        print(note)
    if passed:
        print("[PASS] Quick Estimation conjugate + FOV solve across machine-vision layouts")
        return 0
    print("[FAIL] Quick Estimation conjugate guard")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
