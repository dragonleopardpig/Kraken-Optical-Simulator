"""Guard: Replace an imported STEP OVERLAY in place (bugs/0406 + 0407).

The camera / BS / LED half of "delete/import on the spot" (the promoted-solid half is bugs/0404).
Right-click an imported STEP overlay -> "Replace {Camera/BS/LED/Optical} STEP...". Behaviour is PER
LABEL because the placement semantics differ (bugs/0407, the user's catch):

* LED / BS (optical) -- a POSE-PRESERVING path swap (no sensor-location dependency), like Swap Imaging
  Lens keeps a lens's pose. A fresh import would RESET the pose.
* camera -- a raw pose swap would MISLOCATE the sensor: the sensor sits ``camera_front_to_sensor_mm``
  behind the body front, and the camera<->detector glue places the body so the sensor lands on the
  image plane; a different camera has a different front_to_sensor. So Replace runs the full Camera
  Import flow (re-establishes the sensor location) THEN restores the old TRANSVERSE position (the axial
  position is auto-driven by image_plane_z - front_to_sensor).
* lens -- REJECTED: an imaging lens needs its optical surrogate rebuilt via "Swap Imaging Lens from
  Folder" (a lens FOLDER), not a single-STEP path swap.

Display-free: behavioural stub tests drive the REAL service method + getsource wiring.

Checks
------
* PRESERVE  -- a LED/BS overlay replace swaps the path, KEEPS the pose, invalidates/refreshes, returns
  the new path.
* CAMERA    -- a camera replace runs ``import_camera_step`` then restores the old TRANSVERSE offset
  (x/y from the old pose, z from the import) -- it does NOT keep the raw old axial pose.
* LENS      -- a lens replace is rejected (returns None, status points at Swap Imaging Lens).
* NO-OP     -- nothing imported -> None, path untouched.
* WRAPPER   -- the editor exposes the method and delegates to the service (mixin-wrapper trap).
* MENU      -- the overlay right-click offers "Replace ... STEP..." (EXCLUDING lens) wired to
  ``_replace_step_overlay_from_context`` -> editor's replace method.

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
        self.import_camera_called = False
        setattr(self, f"imported_{label}_step_path", "old.step" if has_path else None)
        # pose attrs that a fresh import WOULD reset -- the pose-preserve (led/BS) case must keep them
        setattr(self, f"{label}_step_rotation_z_deg", 42.0)
        # camera two-step: an OLD placement offset the user set (x/y transverse, z axial)
        self.camera_step_placement_offset_xyz = (7.0, 8.0, 9.0)

    def _begin_history_capture(self):
        pass

    def _commit_history_capture(self):
        pass

    def _open3d_trace_refresh_service(self):
        return _RefreshStub()

    def _invalidate_preview_scene_trace(self):
        self.invalidated = True

    def _refresh_open_3d_views(self, **kwargs):
        self.refreshed = True

    def _step_placement_offset_xyz(self, label):
        return tuple(getattr(self, f"{label}_step_placement_offset_xyz", (0.0, 0.0, 0.0)))

    def import_camera_step(self, *, path=None, refresh_open_3d=True):
        # the full import flow RESETS the placement (fresh on-axis) + relocates the sensor axially
        self.import_camera_called = True
        self.imported_camera_step_path = path
        self.camera_step_placement_offset_xyz = (0.0, 0.0, 5.0)  # import's reset (z from the glue)
        return path


def _check_preserve(failures, notes):
    svc = _StubImportSvc("led", has_path=True)
    result = svc.replace_imported_step_overlay("led", __file__, refresh_open_3d=True)
    if result is None:
        failures.append("PRESERVE: led replace returned None for an imported overlay + valid path")
        return
    if str(getattr(svc, "imported_led_step_path", "")) != str(__file__):
        failures.append("PRESERVE: the imported path was not swapped to the replacement")
    if abs(float(svc.led_step_rotation_z_deg) - 42.0) > 1e-9:
        failures.append("PRESERVE: pose was RESET on a LED/BS replace -- must keep the pose")
    if not svc.invalidated or not svc.refreshed:
        failures.append("PRESERVE: led replace did not invalidate/refresh")
    if not [f for f in failures if f.startswith("PRESERVE")]:
        notes.append("preserve = LED/BS replace swaps path, keeps pose, invalidates/refreshes")


def _check_camera(failures, notes):
    svc = _StubImportSvc("camera", has_path=True)
    result = svc.replace_imported_step_overlay("camera", __file__, refresh_open_3d=True)
    if result is None:
        failures.append("CAMERA: camera replace returned None")
        return
    if not svc.import_camera_called:
        failures.append("CAMERA: replace did NOT run the Camera Import flow (sensor would be mislocated)")
    off = tuple(svc.camera_step_placement_offset_xyz)
    # transverse (x,y) restored from the OLD pose (7,8); axial (z) from the import (5)
    if not (abs(off[0] - 7.0) < 1e-9 and abs(off[1] - 8.0) < 1e-9):
        failures.append(f"CAMERA: transverse position not restored from the old pose (got {off})")
    if abs(off[2] - 5.0) > 1e-9:
        failures.append(f"CAMERA: axial z must come from the import glue, not the old pose (got {off})")
    if not [f for f in failures if f.startswith("CAMERA")]:
        notes.append("camera = import flow re-locates sensor, old transverse x/y restored, axial from glue")


def _check_lens(failures, notes):
    svc = _StubImportSvc("lens", has_path=True)
    result = svc.replace_imported_step_overlay("lens", __file__)
    if result is not None:
        failures.append("LENS: a lens replace must be rejected (surrogate rebuild via Swap Imaging Lens)")
    if "Swap Imaging Lens" not in svc.status_var.get():
        failures.append("LENS: the rejection status must point at Swap Imaging Lens from Folder")
    if not [f for f in failures if f.startswith("LENS")]:
        notes.append("lens = rejected -> Swap Imaging Lens from Folder (rebuilds the surrogate)")


def _check_noop(failures, notes):
    svc = _StubImportSvc("led", has_path=False)
    result = svc.replace_imported_step_overlay("led", __file__)
    if result is not None or getattr(svc, "imported_led_step_path", None) is not None:
        failures.append("NO-OP: nothing imported must return None + not touch the path")
    if not [f for f in failures if f.startswith("NO-OP")]:
        notes.append("no-op = nothing imported -> None, path untouched")


def _check_wrapper(failures, notes):
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    if not hasattr(KrakenLayoutEditor, "replace_imported_step_overlay"):
        failures.append("WRAPPER: the editor has no replace_imported_step_overlay wrapper")
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
    if 'step_label != "lens"' not in menu:
        failures.append("MENU: the Replace entry must EXCLUDE a lens (it needs Swap Imaging Lens)")
    handler = inspect.getsource(Open3DFaceAssignmentService._replace_step_overlay_from_context)
    if "replace_imported_step_overlay" not in handler:
        failures.append("MENU: the handler does not call the editor's replace method")
    if not [f for f in failures if f.startswith("MENU")]:
        notes.append("menu = 'Replace ... STEP...' (lens excluded) -> editor.replace_imported_step_overlay")


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    for check in (_check_preserve, _check_camera, _check_lens, _check_noop, _check_wrapper, _check_menu):
        try:
            check(failures, notes)
        except Exception as exc:
            failures.append(f"{check.__name__}: raised {type(exc).__name__}: {exc}")
    info = [n if "=" in n else n.replace(":", " =", 1) for n in notes]
    return (not failures), (failures + info)


def run() -> int:
    passed, notes = run_checks()
    print("=== validate_open3d_replace_step_overlay (bugs/0406 + 0407) ===")
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
