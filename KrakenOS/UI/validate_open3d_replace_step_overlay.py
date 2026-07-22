"""Guard: Replace an imported STEP OVERLAY in place (bugs/0406).

The camera / BS / LED half of "delete/import on the spot" (the promoted-solid half is bugs/0404).
Right-click an imported STEP overlay -> "Replace {Camera/BS/LED/Optical} STEP..." swaps its geometry
for a new STEP file while PRESERVING the pose (rotation / axis offset / placement offset) and glue --
the pose-keeping counterpart to a fresh import, which RESETS the pose. A camera replacement also
re-couples the surrogate sensor when the new STEP is a recognised vendor camera.

Display-free: a behavioural stub test drives the REAL service method (pose preserved; no-op when
nothing imported) + getsource wiring on the editor wrapper and the menu.

Checks
------
* PRESERVE  -- driving ``replace_imported_step_overlay`` with an imported overlay swaps the path,
  KEEPS a pre-set pose attribute (not reset), invalidates the preview, and returns the new path.
* NO-OP     -- with no STEP of that label imported it returns None and does not touch the path.
* WRAPPER   -- the editor exposes ``replace_imported_step_overlay`` and delegates to the service
  (mixin-wrapper trap).
* MENU      -- the overlay right-click offers "Replace ... STEP..." wired to
  ``_replace_step_overlay_from_context``, whose handler calls the editor's replace method.
* NO-RESET  -- the service source never zeroes the pose (that would move the replacement).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_replace_step_overlay

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect

from KrakenOS.UI.services.step_overlay_import import StepOverlayImportService


class _Var:
    def __init__(self):
        self._v = ""

    def get(self):
        return self._v

    def set(self, v):
        self._v = str(v)


class _RefreshStub:
    def clear_step_overlay_physics_preview(self, label):
        pass


class _StubImportSvc:
    replace_imported_step_overlay = StepOverlayImportService.replace_imported_step_overlay

    @staticmethod
    def _step_overlay_display_label(label):
        return str(label).title()

    def __init__(self, label, has_path):
        self.status_var = _Var()
        self._selected_step_label = None
        self._live_step_overlay_trace_plan_cache = {"stale": 1}
        self.invalidated = False
        self.refreshed = False
        setattr(self, f"imported_{label}_step_path", "old.step" if has_path else None)
        # a pose attribute that a fresh import WOULD reset -- Replace must keep it
        self.camera_step_rotation_z_deg = 42.0
        self.camera_step_placement_offset_xyz = (1.0, 2.0, 3.0)

    def _begin_history_capture(self):
        pass

    def _commit_history_capture(self):
        pass

    def _couple_camera_model_from_step(self, path):
        return None

    def _open3d_trace_refresh_service(self):
        return _RefreshStub()

    def _invalidate_preview_scene_trace(self):
        self.invalidated = True

    def _refresh_open_3d_views(self, **kwargs):
        self.refreshed = True


def _check_preserve(failures, notes):
    svc = _StubImportSvc("camera", has_path=True)
    # any existing file passes the exists() check (content is irrelevant -- coupling is stubbed)
    result = svc.replace_imported_step_overlay("camera", __file__, refresh_open_3d=True)
    if result is None:
        failures.append("PRESERVE: replace returned None for an imported overlay + valid path")
        return
    if str(getattr(svc, "imported_camera_step_path", "")) != str(__file__):
        failures.append("PRESERVE: the imported path was not swapped to the replacement")
    if abs(float(svc.camera_step_rotation_z_deg) - 42.0) > 1e-9:
        failures.append("PRESERVE: pose (rotation) was RESET -- Replace must keep the pose")
    if tuple(svc.camera_step_placement_offset_xyz) != (1.0, 2.0, 3.0):
        failures.append("PRESERVE: placement offset was RESET -- Replace must keep the pose")
    if not svc.invalidated or not svc.refreshed:
        failures.append("PRESERVE: replace did not invalidate/refresh the preview")
    if not [f for f in failures if f.startswith("PRESERVE")]:
        notes.append("preserve = path swapped, pose kept, preview invalidated/refreshed")


def _check_noop(failures, notes):
    svc = _StubImportSvc("camera", has_path=False)
    result = svc.replace_imported_step_overlay("camera", __file__)
    if result is not None:
        failures.append("NO-OP: replace should return None when no STEP of that label is imported")
    if getattr(svc, "imported_camera_step_path", None) is not None:
        failures.append("NO-OP: replace touched the path despite nothing imported")
    if not [f for f in failures if f.startswith("NO-OP")]:
        notes.append("no-op = nothing imported -> None, path untouched")


def _check_no_reset(failures, notes):
    src = inspect.getsource(StepOverlayImportService.replace_imported_step_overlay)
    if "rotation_x_deg = 0.0" in src or "placement_offset_xyz = (0.0" in src:
        failures.append("NO-RESET: the replace source zeroes the pose (must preserve it)")
    if "imported_" not in src or "setattr" not in src:
        failures.append("NO-RESET: the replace does not set the imported STEP path")
    if not [f for f in failures if f.startswith("NO-RESET")]:
        notes.append("no-reset = the service never zeroes the pose")


def _check_wrapper(failures, notes):
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    if not hasattr(KrakenLayoutEditor, "replace_imported_step_overlay"):
        failures.append("WRAPPER: the editor has no replace_imported_step_overlay wrapper (service-only no-ops)")
        return
    wrap = inspect.getsource(KrakenLayoutEditor.replace_imported_step_overlay)
    if "_step_overlay_import_service().replace_imported_step_overlay" not in wrap:
        failures.append("WRAPPER: the editor wrapper does not delegate to the service")
    if not [f for f in failures if f.startswith("WRAPPER")]:
        notes.append("wrapper = editor wrapper delegates to the service")


def _check_menu(failures, notes):
    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService

    menu = inspect.getsource(Open3DFaceAssignmentService._show_surface_function_context_menu)
    if "Replace {display} STEP..." not in menu:
        failures.append("MENU: the overlay right-click has no 'Replace ... STEP...' entry")
    if "_replace_step_overlay_from_context" not in menu:
        failures.append("MENU: the Replace entry is not wired to _replace_step_overlay_from_context")
    handler = inspect.getsource(Open3DFaceAssignmentService._replace_step_overlay_from_context)
    if "replace_imported_step_overlay" not in handler:
        failures.append("MENU: the handler does not call the editor's replace method")
    if not [f for f in failures if f.startswith("MENU")]:
        notes.append("menu = 'Replace ... STEP...' -> handler -> editor.replace_imported_step_overlay")


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    for check in (_check_preserve, _check_noop, _check_no_reset, _check_wrapper, _check_menu):
        try:
            check(failures, notes)
        except Exception as exc:
            failures.append(f"{check.__name__}: raised {type(exc).__name__}: {exc}")
    info = [n if "=" in n else n.replace(":", " =", 1) for n in notes]
    return (not failures), (failures + info)


def run() -> int:
    passed, notes = run_checks()
    print("=== validate_open3d_replace_step_overlay (bugs/0406) ===")
    for note in notes:
        print(f"  {'ok ' if '=' in note else 'XX '} {note}")
    if not passed:
        n = len([x for x in notes if "=" not in x])
        print(f"\n{n} failure(s).")
        return 1
    print("\nAll replace-step-overlay checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
