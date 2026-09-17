"""0692: render-verify the split-field display fixes with the USER'S saved layout.

Loads om05a exactly as the user does (their preference layout lives in the scene
file -- do not touch any toggle), traces, opens 3D, restores the flag's camera,
and snapshots: (1) the user's own view, (2) a sensor close-up. Eyeball targets:
no big green QE circle at face A, no "Image circle/Needs" rings or labels, a
clean orthogonal dotted axis with the seat jog, and the four dashed cover-strip
edges on the sensor die.
"""
import json
from pathlib import Path

import numpy as np

FLAG = Path("attachment/recorded_bug_repros/flag_20260902_103541_991/state.json")
OUT = Path("bugs")


def main():
    from KrakenOS.UI.capture_open3d_step_workflow_screenshots import _save_vtk_snapshot, _settle
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["p"] = Path("attachment/om05a_folded.py").resolve()
    editor.load_layout_by_name("p")
    editor._preview_trace_deferred_until_requested = False
    editor._build_preview_system_rays_bundle(trace_rays=True)
    editor.open_3d_view()
    editor.update_idletasks()
    editor.update()
    inspector = editor._three_d_inspector
    # populate actors via the tracked rebuild (the LIVE refresh path spun at 99%
    # CPU for 23+ min headless -- killed; refresh_from_editor is the validator route)
    inspector.refresh_from_editor(
        sampling_mode=editor._preview_3d_sampling_mode(), force_retrace=True
    )
    _settle(editor, 1.0)

    cam = inspector._renderer.GetActiveCamera()
    state = json.loads(FLAG.read_text()).get("scene_state") or {}
    pos = state.get("camera_position")
    foc = state.get("camera_focal")
    up = state.get("camera_view_up")
    if pos and foc and up:
        cam.SetPosition(*[float(v) for v in pos])
        cam.SetFocalPoint(*[float(v) for v in foc])
        cam.SetViewUp(*[float(v) for v in up])
        inspector._renderer.ResetCameraClippingRange()
    _settle(editor, 0.5)
    _save_vtk_snapshot(inspector, OUT / "0692_verify_user_view.png")

    # sensor close-up: look at the die from +x, strip axis (z) horizontal
    cam.SetFocalPoint(-272.65, -9.9, -25.0)
    cam.SetPosition(-200.0, -9.9, -25.0)
    cam.SetViewUp(0.0, 1.0, 0.0)
    inspector._renderer.ResetCameraClippingRange()
    _settle(editor, 0.5)
    _save_vtk_snapshot(inspector, OUT / "0692_verify_sensor.png")

    # face-A close-up: the object plane where the big green circle used to sit
    cam.SetFocalPoint(0.0, 0.0, 0.0)
    cam.SetPosition(60.0, 25.0, 45.0)
    cam.SetViewUp(0.0, 1.0, 0.0)
    inspector._renderer.ResetCameraClippingRange()
    _settle(editor, 0.5)
    _save_vtk_snapshot(inspector, OUT / "0692_verify_faceA.png")
    print("snapshots written")
    editor.destroy()


if __name__ == "__main__":
    main()
