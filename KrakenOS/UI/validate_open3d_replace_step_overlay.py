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

from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin
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


class _ImportedCameraStub:
    name = "BC-OM25M"


class _StubFolderSvc:
    """Drive the REAL replace_camera_from_folder (the vendor FOLDER flow) display-free."""

    replace_camera_from_folder = LayoutTableWorkbenchMixin.replace_camera_from_folder

    def __init__(self):
        self.status_var = _Var()
        self._live_step_overlay_trace_plan_cache = {"stale": 1}
        self.invalidated = False
        self.refreshed = False
        self.folder_import_called = False
        self.camera_step_placement_offset_xyz = (7.0, 8.0, 9.0)  # the OLD transverse position

    def _step_placement_offset_xyz(self, label):
        return tuple(self.camera_step_placement_offset_xyz)

    def import_vendor_camera_from_folder(self, folder, *, dialog_parent=None, refresh_open_3d=True):
        # the folder flow prompts for the flange distance + resets the placement (axial from the glue)
        self.folder_import_called = True
        self.camera_step_placement_offset_xyz = (0.0, 0.0, 5.0)
        return _ImportedCameraStub()

    def _invalidate_preview_scene_trace(self):
        self.invalidated = True

    def _refresh_open_3d_views(self, **kwargs):
        self.refreshed = True


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


def _check_camera_rejected(failures, notes):
    # a STEP-path camera replace must be REJECTED (bugs/0408: the camera goes through the FOLDER flow,
    # which prompts for the flange distance -- a single STEP swap can't set front_to_sensor).
    svc = _StubImportSvc("camera", has_path=True)
    result = svc.replace_imported_step_overlay("camera", __file__)
    if result is not None:
        failures.append("CAMERA-REJECT: a STEP-path camera replace must be rejected (route to the folder flow)")
    if "Folder" not in svc.status_var.get():
        failures.append("CAMERA-REJECT: the rejection status must point at Replace Camera from Folder")
    if not [f for f in failures if f.startswith("CAMERA-REJECT")]:
        notes.append("camera-reject = a STEP-path camera swap is rejected -> Replace Camera from Folder")


def _check_camera_folder(failures, notes):
    # bugs/0612/0614: the SEAT (traced-beam, fold-aware, transverse-keep fallback) lives
    # inside import_vendor_camera_from_folder now -- the one flow both the toolbar import
    # and this replace share. The replace flow's contract is DELEGATION: run the folder
    # import and do NOT clobber whatever placement the import's seating produced (the old
    # behaviour restored stale transverse numbers over the seated position).
    svc = _StubFolderSvc()
    result = svc.replace_camera_from_folder(folder="dummy", refresh_open_3d=True)
    if result is None:
        failures.append("CAMERA-FOLDER: replace_camera_from_folder returned None on a successful import")
        return
    if not svc.folder_import_called:
        failures.append("CAMERA-FOLDER: did NOT run the vendor FOLDER import (flange prompt + front_to_sensor)")
    off = tuple(svc.camera_step_placement_offset_xyz)
    if not (abs(off[0] - 0.0) < 1e-9 and abs(off[1] - 0.0) < 1e-9 and abs(off[2] - 5.0) < 1e-9):
        failures.append(
            f"CAMERA-FOLDER: the replace flow must keep the import's seated placement (got {off}, "
            "want the stub-import's (0, 0, 5) untouched)"
        )
    if not svc.invalidated or not svc.refreshed:
        failures.append("CAMERA-FOLDER: did not invalidate/refresh after the folder import")
    if not [f for f in failures if f.startswith("CAMERA-FOLDER")]:
        notes.append("camera-folder = folder import (seat inside), replace keeps the seated placement")


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

    # flag_20260812_114828: the swap/replace entries live in append_element_context_actions
    # now, the branch SHARED by the 3D-canvas right-click AND the Scene Components tree --
    # both surfaces offer every STEP body's swap. Same routing contract as before, plus the
    # lens gains its own entry wired to the surrogate-rebuilding folder swap (bugs/0378).
    menu = inspect.getsource(Open3DFaceAssignmentService.append_element_context_actions)
    if "Replace {display} STEP..." not in menu:
        failures.append("MENU: the shared element menu has no 'Replace ... STEP...' entry")
    if "Replace Camera from Folder..." not in menu:
        failures.append("MENU: a camera must read 'Replace Camera from Folder...' (bugs/0408)")
    if 'step_label != "lens"' not in menu:
        failures.append("MENU: the Replace entry must EXCLUDE a lens (it needs Swap Imaging Lens)")
    if "Swap Imaging Lens from Folder" not in menu:
        failures.append("MENU: the lens body must offer 'Swap Imaging Lens from Folder' (flag_20260812_114828)")
    handler = inspect.getsource(Open3DFaceAssignmentService._replace_step_overlay_from_context)
    if "replace_imported_step_overlay" not in handler or "replace_camera_from_folder" not in handler:
        failures.append("MENU: the handler must route camera->folder flow and others->step swap")
    lens_handler = inspect.getsource(Open3DFaceAssignmentService._swap_imaging_lens_from_context)
    if "swap_imaging_lens_from_folder" not in lens_handler:
        failures.append("MENU: the lens swap entry must route to swap_imaging_lens_from_folder")
    if "Flip Camera Direction (front/rear)" not in menu:
        failures.append("MENU: the camera body must offer 'Flip Camera Direction' (bugs/0615)")
    flip_handler = inspect.getsource(Open3DFaceAssignmentService._flip_camera_step_direction_from_context)
    if "toggle_imported_camera_step_direction" not in flip_handler:
        failures.append("MENU: the camera flip entry must route to toggle_imported_camera_step_direction")
    canvas = inspect.getsource(Open3DFaceAssignmentService._show_surface_function_context_menu)
    if "append_element_context_actions" not in canvas:
        failures.append("MENU: the canvas menu no longer includes the shared element actions")
    if not [f for f in failures if f.startswith("MENU")]:
        notes.append("menu = camera->'from Folder', LED/BS->STEP swap, lens->folder swap, both surfaces")


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    for check in (
        _check_preserve, _check_camera_rejected, _check_camera_folder,
        _check_lens, _check_noop, _check_wrapper, _check_menu,
    ):
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
