"""Guard: two usability refinements after the 0404 Replace feature (bugs/0405).

Both from flags on the AZ85 RA-mirror scene (build 7a4bedb9) confirming 0404 Replace + the defocus
snap WORK, but are inconvenient:

* flag_20260722_142908 -- "Replace the second RA mirror with a bigger one works, but need to manually
  align it to the optical axis." A resized replacement has a different intrinsic mesh center, so
  preserving only the overlay placement offset left it off-axis. FIX: the Replace now pins the
  replacement's TRANSVERSE decenter (``desp_x``/``desp_y``) to the old solid's, so a resized mirror
  keeps the optical-axis alignment the user set.
* flag_20260722_143106 -- "Remove defocus works. One thing not convenient, I need to hide the camera
  -> right click the detector to select defocus." The camera body occludes the detector in 3D. FIX:
  the detector (final ``Image`` row) now offers "Snap detector to image plane (remove defocus)" in the
  right-hand Scene Components BROWSER menu, reachable without hiding the camera.

Display-free (getsource wiring + ordering guards).

Checks
------
* REPLACE-AXIS -- ``replace_promoted_optical_solid_step`` captures ``old_desp_xy`` BEFORE unpromote
  (which deletes the row) and re-applies it to the replacement row's ``desp_x``/``desp_y`` AFTER the
  re-promote.
* DEFOCUS-MENU -- the browser element menu offers "Snap detector to image plane (remove defocus)"
  gated on the ``Image`` surface row, wired to the inspector's ``_snap_detector_to_image_plane``.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_replace_axis_and_defocus_menu

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect


def _check_replace_axis(failures, notes):
    from KrakenOS.UI.services.step_overlay_promotion import StepOverlayPromotionService

    src = inspect.getsource(StepOverlayPromotionService.replace_promoted_optical_solid_step)
    cap = src.find("old_desp_xy")
    unp = src.find("unpromote_optical_solid_to_overlay")
    prom = src.find("promote_imported_step_to_optical_solid_row")
    move = src.find("translate_scene_row_pose_vector")
    if not (0 <= cap < unp):
        failures.append("REPLACE-AXIS: old_desp_xy must be captured BEFORE unpromote (which deletes the row)")
    # bugs/0409: the decenter is re-applied via the SANCTIONED drag path (not a raw desp set) so the
    # hover outline follows the moved body.
    if move < 0 or not (prom < move):
        failures.append("REPLACE-AXIS: the decenter must be re-applied via translate_scene_row_pose_vector AFTER re-promote")
    if "old_desp_xy[0]" not in src or "old_desp_xy[1]" not in src:
        failures.append("REPLACE-AXIS: both transverse axes (x/y) must be pinned from the old pose")
    # bugs/0409: the re-promote must CLEAR the source overlay, else the leftover overlay's face hovers
    # offset from the promoted body (the ghost-highlight flag).
    if "clear_overlay=True" not in src:
        failures.append("REPLACE-AXIS/GHOST: re-promote must clear_overlay=True (leftover overlay hover ghosts)")
    if not [f for f in failures if f.startswith("REPLACE-AXIS")]:
        notes.append("replace-axis = transverse desp re-applied via drag path post-promote; overlay cleared (no ghost)")


def _check_defocus_menu(failures, notes):
    from KrakenOS.UI.panels.open3d_step_admin import Open3DStepAdminPanel

    menu = inspect.getsource(Open3DStepAdminPanel._show_element_context_menu)
    if "Snap detector to image plane (remove defocus)" not in menu:
        failures.append("DEFOCUS-MENU: the browser detector row has no 'remove defocus' entry")
    if "_snap_detector_to_image_plane" not in menu:
        failures.append("DEFOCUS-MENU: the defocus entry is not wired to _snap_detector_to_image_plane")
    # gated on the Image (detector) row so it only shows on the detector, not every element
    if '"Image"' not in menu or "is_detector_row" not in menu:
        failures.append("DEFOCUS-MENU: the entry must be gated on the final Image (detector) row")
    # the inspector wrapper the entry calls must exist
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    if not hasattr(Kraken3DInspector, "_snap_detector_to_image_plane"):
        failures.append("DEFOCUS-MENU: the inspector has no _snap_detector_to_image_plane wrapper")
    if not [f for f in failures if f.startswith("DEFOCUS-MENU")]:
        notes.append("defocus-menu = detector (Image) browser row offers 'remove defocus'; no camera-hide needed")


def _check_camera_defocus_menu(failures, notes):
    # bugs/0409: the CAMERA element menu also offers 'remove defocus' -- the user right-clicks the
    # camera (glued to the detector) to remove defocus, and "Reset Camera to Image Plane" doesn't.
    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService

    menu = inspect.getsource(Open3DFaceAssignmentService.append_element_context_actions)
    if "Snap detector to image plane (remove defocus)" not in menu:
        failures.append("CAMERA-DEFOCUS: the camera menu has no 'remove defocus' entry")
    if 'step_label == "camera"' not in menu or "_snap_detector_to_image_plane" not in menu:
        failures.append("CAMERA-DEFOCUS: the entry must be gated on the camera + wired to _snap_detector_to_image_plane")
    if not [f for f in failures if f.startswith("CAMERA-DEFOCUS")]:
        notes.append("camera-defocus = the camera menu offers 'remove defocus' (Reset-to-Image-Plane doesn't close the gap)")


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    for check in (_check_replace_axis, _check_defocus_menu, _check_camera_defocus_menu):
        try:
            check(failures, notes)
        except Exception as exc:
            failures.append(f"{check.__name__}: raised {type(exc).__name__}: {exc}")
    info = [n if "=" in n else n.replace(":", " =", 1) for n in notes]
    return (not failures), (failures + info)


def run() -> int:
    passed, notes = run_checks()
    print("=== validate_open3d_replace_axis_and_defocus_menu (bugs/0405) ===")
    for note in notes:
        print(f"  {'ok ' if '=' in note else 'XX '} {note}")
    if not passed:
        n = len([x for x in notes if "=" not in x])
        print(f"\n{n} failure(s).")
        return 1
    print("\nAll replace-axis + defocus-menu checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
