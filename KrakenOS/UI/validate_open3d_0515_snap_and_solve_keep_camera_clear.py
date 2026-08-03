"""bugs/0515 -- the camera anti-crash contract (design agreed 2026-07-29).

The user rejected warn-only twice: solving a field or removing defocus must
KEEP the camera body clear of the fold mirror by REDISTRIBUTING the deficit
into the lens->mirror leg (the optics pins section 1 and the SUM of sections
3+4, never the split), with glued companions carried.

Pinned here:
  * the FOV solve at the flagged crash fields (30x30 / 35x35,
    flag_20260730_103719 "the camera crash to RA mirror") leaves the REAL-MESH
    body clearance deficit at zero;
  * ``snap_detector_to_image_plane`` ("remove defocus") routes through the
    body-aware collision resolver and the frozen-aware sensor write instead of
    the raw last-gap write (the one writer with no floor), restores focus, and
    carries the camera body with the sensor;
  * the resolver's redistribution keeps the conjugate (mirror slide, not
    refusal) -- asserted via the solve succeeding at fields whose naive gap sits
    below the body floor.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0515_snap_and_solve_keep_camera_clear
"""
from __future__ import annotations

import inspect
from pathlib import Path
from types import SimpleNamespace

import numpy as np

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    ok = True

    def check(cond: bool, label: str) -> None:
        nonlocal ok
        notes.append(("PASS " if cond else "FAIL ") + label)
        if not cond:
            ok = False

    from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin

    snap_src = inspect.getsource(ScenePlacementMixin.snap_detector_to_image_plane)
    check(
        "_resolve_image_gap_collision" in snap_src and "apply_image_distance_frozen_aware" in snap_src,
        "S1: snap_detector routes through the collision resolver + the frozen-aware write",
    )

    if not SCENE.exists():
        notes.append("SKIP: the AZ85 BS scene is not checked out (gitignored attachment)")
        return ok, notes

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    def deficit(editor) -> float:
        return float(editor._swap_camera_body_clearance_deficit())

    def cam_z(editor) -> float:
        return float(np.asarray(editor._step_body_world_center("camera"), dtype=float).reshape(3)[2])

    # -- A: the flagged crash fields solve with the body CLEAR -------------------------
    editor = None
    try:
        editor = KrakenLayoutEditor()
        editor.layout_files["anticrash_probe"] = SCENE
        editor.load_layout_by_name("anticrash_probe")
        check(deficit(editor) <= 1e-6, "A0: baseline body clearance deficit is zero")
        svc = QuickEstimationService(SimpleNamespace(editor=editor))
        solved, message = svc.fov_solve("object", "thickness", 35, 35)
        check(bool(solved), f"A1: the 35x35 crash field SOLVES (redistribution, not refusal): {message[:90]}")
        check(
            deficit(editor) <= 1e-6,
            f"A2: after the 35x35 solve the camera body stays CLEAR of the mirror "
            f"(real-mesh deficit {deficit(editor):.3f} mm; the flagged crash buried it 5.3 mm)",
        )
        check(
            "camera carried" in str(message) or "re-seated" in str(message),
            "A3: the solve reports the frozen world re-seat + camera carry (glued companions ride)",
        )
    finally:
        try:
            if editor is not None:
                editor.destroy()
        except Exception:
            pass

    # -- B: remove-defocus round-trips through the floor and carries the camera -------
    editor = None
    try:
        editor = KrakenLayoutEditor()
        editor.layout_files["anticrash_probe_b"] = SCENE
        editor.load_layout_by_name("anticrash_probe_b")
        from KrakenOS.UI.services import optical_axis_tree as tree_mod

        def sensor_world_z() -> float:
            return float(
                np.asarray(
                    tree_mod.row_world_pose(editor.rows, len(editor.rows) - 1), dtype=float
                ).reshape(-1)[2]
            )

        gap0 = float(editor.rows[-2].thickness)
        # Frozen-aware defocus (+20 leg mm), exactly what a user drag produces. NOTE: on a
        # frozen chain the row .thickness is a STATION number, not a leg length -- the
        # apply re-bakes it (44.119 -> 38.881 here), so this guard asserts WORLD truths
        # (residual traced defocus, world sensor/camera motion), never thickness values.
        if not editor.apply_image_distance_frozen_aware(gap0 + 20.0):
            editor.rows[-2].thickness = gap0 + 20.0
        cam_defocused = cam_z(editor)
        sensor_defocused = sensor_world_z()
        moved = bool(editor.snap_detector_to_image_plane())
        check(moved, "B1: snap-detector reports a move from the defocused state")
        try:
            residual = editor._traced_bundle_best_focus_shift()
        except Exception:
            residual = None
        check(
            residual is not None and abs(float(residual)) <= 1.0,
            f"B2: after snap the RESIDUAL traced defocus is ~zero (got {residual})",
        )
        check(
            deficit(editor) <= 1e-6,
            f"B3: after snap the camera body stays CLEAR (deficit {deficit(editor):.3f} mm) -- "
            "the raw last-gap write had no floor",
        )
        cam_after = cam_z(editor)
        sensor_after = sensor_world_z()
        cam_move = cam_after - cam_defocused
        sensor_move = sensor_after - sensor_defocused
        check(
            abs(sensor_move) > 1.0 and abs(cam_move - sensor_move) <= 1.0,
            f"B4: the camera BODY rides the sensor through the snap "
            f"(sensor moved {sensor_move:+.2f}, camera moved {cam_move:+.2f})",
        )
    finally:
        try:
            if editor is not None:
                editor.destroy()
        except Exception:
            pass

    return ok, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
