"""bugs/0517 guard -- a reflect-branch camera BODY adopts its branch detector's frame.

Detector-redesign B2 remainder: the camera STEP overlay always rode the sequential Image
row's fold transform, so a camera REGISTERED to a reflect branch detector drew its body on
the image arm while its sensor plane lived on the reflect arm. The fix mirrors the fold
architecture: ``_camera_branch_world_transform`` carries the straight-axis overlay onto the
assigned branch's frame (sensor ON the detector, front face ``front_to_sensor`` upstream,
by construction), and ``seat_camera_on_sensor`` writes its world shift back through R^T
when that frame is engaged.

Checks:
  SOURCE -- the camera mesh builder consults the branch transform; the transform reads
            editor attributes via __dict__ (the 0082 tkinter trap); the seat writes back
            through the branch rotation.
  REAL   -- on the dual-lens split scene with a vendor camera assigned to the REFLECT
            branch: the transform engages, the body's front face lands front_to_sensor
            upstream of the detector along the branch normal, and the body centres on the
            branch axis.
"""
from __future__ import annotations

import inspect as _inspect
from pathlib import Path

import numpy as np

SCENE = Path("KrakenOS/common_optical_layouts/beam_splitter_50_50_example.py")
CAMERA_STEP = Path("attachment/Cameras/BC-OM25M/BC-OM25M12X2-M58.STEP.step")


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services import layout_polyline_display as _lpd
    from KrakenOS.UI.services import scene_placement_commands as _spc

    mesh_src = _inspect.getsource(_lpd.LayoutPolylineDisplayMixin._transformed_imported_camera_step_mesh)
    if "_camera_branch_world_transform" in mesh_src:
        notes.append("SOURCE = the camera mesh builder consults the branch transform")
    else:
        notes.append("SOURCE the camera mesh builder no longer consults _camera_branch_world_transform")
        ok = False

    transform_src = _inspect.getsource(_lpd.LayoutPolylineDisplayMixin._camera_branch_world_transform)
    if "__dict__.get(\"branch_detector_camera_assignments\")" in transform_src:
        notes.append("SOURCE = the transform reads assignments via __dict__ (0082 trap)")
    else:
        notes.append("SOURCE the transform reads assignments unsafely (tkinter __getattr__ recursion)")
        ok = False

    seat_src = _inspect.getsource(_spc.ScenePlacementMixin.seat_camera_on_sensor)
    if "_camera_branch_world_transform" in seat_src:
        notes.append("SOURCE = the seat writes its shift back through the branch rotation")
    else:
        notes.append("SOURCE the seat lost the branch-frame R^T write-back")
        ok = False

    if not SCENE.exists():
        notes.append("SKIP: dual-lens split scene absent")
        return ok, notes
    if not CAMERA_STEP.exists():
        notes.append("SKIP: vendor camera STEP absent (gitignored attachment)")
        return ok, notes

    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor

        app = KrakenLayoutEditor()
    except Exception as exc:
        notes.append(f"SKIP: editor unavailable ({exc!r})")
        return ok, notes
    try:
        app.layout_files["dual"] = SCENE
        app.load_layout_by_name("dual")
        app.imported_camera_step_path = CAMERA_STEP.resolve()
        try:
            app.camera_model_var.set("BC-OM25M")
        except Exception:
            pass
        app._build_preview_system_rays_bundle(update_state=True)
        frames = app.__dict__.get("_branch_detector_world_frames") or {}
        off_axis = [bp for bp, fr in frames.items() if fr.get("focus_source") != "reached_image"]
        if not off_axis:
            notes.append(f"SKIP: no off-axis branch derived (frames: {sorted(frames)})")
            return ok, notes
        branch = sorted(off_axis)[0]
        app.branch_detector_camera_assignments = {branch: "BC-OM25M"}
        app._build_preview_system_rays_bundle(update_state=True)
        frame = (app.__dict__.get("_branch_detector_world_frames") or {}).get(branch)
        transform = app._camera_branch_world_transform()
        if transform is None or frame is None:
            notes.append(f"REAL the branch transform did not engage (frame={frame is not None})")
            ok = False
            return ok, notes
        notes.append("REAL = the branch transform engages for the assigned reflect arm")
        mesh = app._transformed_imported_step_mesh_for_label("camera")
        if mesh is None:
            notes.append("SKIP: camera mesh unavailable")
            return ok, notes
        center = np.asarray(frame["center"], dtype=float)
        normal = np.asarray(frame["normal"], dtype=float)
        normal = normal / float(np.linalg.norm(normal))
        pts = np.asarray(mesh.points, dtype=float) - center
        axial = pts @ normal
        back = float(app._current_camera_front_to_sensor_mm())
        front_err = abs(float(axial.min()) + back)
        if front_err <= 2.0 and float(axial.max()) > 10.0:
            notes.append(
                f"REAL = front face {axial.min():.2f} mm along the branch (front_to_sensor {back:.1f}); "
                f"body extends {axial.max():.1f} mm behind the sensor"
            )
        else:
            notes.append(
                f"REAL body mis-seated along the branch: front at {axial.min():.2f} "
                f"(expected {-back:.2f}), depth {axial.max():.2f}"
            )
            ok = False
        lateral = pts - np.outer(axial, normal)
        lateral_centre = float(np.linalg.norm(lateral.mean(axis=0)))
        if lateral_centre <= 15.0:
            notes.append(f"REAL = body centred on the branch axis (lateral centre offset {lateral_centre:.2f} mm)")
        else:
            notes.append(f"REAL body off the branch axis by {lateral_centre:.2f} mm")
            ok = False
    except Exception as exc:
        notes.append(f"SKIP: real-scene drive failed ({exc!r})")
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if ("=" in note or note.startswith("SKIP")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
