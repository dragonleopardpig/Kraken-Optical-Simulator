"""Display-free guard for bugs/0388 -- constraint-aware auto-refocus after a lens swap.

A swapped imaging lens focuses at a new plane, but bugs/0383 keeps the camera/mounts at
their absolute positions, so the image lands defocused on the fixed sensor. The swap now
re-solves best focus by moving ONLY the final gap (image distance) via
snap_detector_to_image_plane -- never the beam geometry -- then CLAMPS that gap to a
mechanical minimum so the sensor can't be solved INTO the upstream element (the RA mirror).

This guard pins the clamp/flag/no-op behaviour with a stub editor (no VTK, no trace):
  - snap can't compute (returns False)      -> no-op, no flag, no row mutation
  - snap moves the gap below the floor       -> gap clamped to the floor, user flagged
  - snap moves the gap to a safe distance     -> gap left exactly as solved, no flag
  - a thin fold-mirror reserve below the floor -> min-gap follows the reserve (never over-demands)
  - a layout with no terminal Image row       -> auto-refocus refuses to touch it

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_lens_swap_auto_refocus
"""

from __future__ import annotations

from types import SimpleNamespace


def _editor(rows):
    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin

    ed = LayoutTableWorkbenchMixin.__new__(LayoutTableWorkbenchMixin)
    ed.rows = rows
    ed._status_messages = []
    ed.status_var = SimpleNamespace(set=ed._status_messages.append)
    return ed


def _lens_image_rows(gap):
    return [
        SimpleNamespace(surface="Object", thickness=10.0, name="Object"),
        SimpleNamespace(surface="Standard", thickness=gap, name="Rear Datum"),
        SimpleNamespace(surface="Image", thickness=0.0, name="Image"),
    ]


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []

    # 1. snap can't compute -> no-op (no mutation, no flag)
    ed = _editor(_lens_image_rows(100.0))
    ed.snap_detector_to_image_plane = lambda: False
    ed._swap_auto_refocus_to_best_focus()
    if ed.rows[-2].thickness != 100.0:
        failures.append("no-op: a snap that can't compute must not move the gap")
    if ed._status_messages:
        failures.append("no-op: a snap that can't compute must not flag the user")

    # 2. snap moves BELOW the floor -> clamp to floor + flag
    ed = _editor(_lens_image_rows(100.0))
    floor = ed._swap_refocus_min_gap()
    ed.snap_detector_to_image_plane = lambda: (
        setattr(ed.rows[-2], "thickness", 0.5) or True
    )
    ed._swap_auto_refocus_to_best_focus()
    if abs(ed.rows[-2].thickness - floor) > 1e-9:
        failures.append(f"clamp: a sub-floor solve must clamp to {floor} (got {ed.rows[-2].thickness})")
    if not any("focus limited" in m for m in ed._status_messages):
        failures.append("clamp: a clamped refocus must flag the user")

    # 3. snap moves to a SAFE distance -> left as solved, no flag
    ed = _editor(_lens_image_rows(100.0))
    ed.snap_detector_to_image_plane = lambda: (
        setattr(ed.rows[-2], "thickness", 47.0) or True
    )
    ed._swap_auto_refocus_to_best_focus()
    if abs(ed.rows[-2].thickness - 47.0) > 1e-9:
        failures.append("safe: a safe solve must be left exactly as computed")
    if any("focus limited" in m for m in ed._status_messages):
        failures.append("safe: a safe refocus must NOT flag the user")

    # 4. thin fold-mirror reserve below the floor -> min-gap follows the reserve
    rows = [
        SimpleNamespace(surface="Object", thickness=10.0, name="Object"),
        SimpleNamespace(surface="Standard", thickness=120.0, name="Front Datum"),
        SimpleNamespace(surface="Standard", thickness=0.8, name="Promoted RA Mirror"),
        SimpleNamespace(surface="Image", thickness=0.0, name="Image"),
    ]
    ed = _editor(rows)
    if abs(ed._swap_refocus_min_gap() - 0.8) > 1e-9:
        failures.append("reserve: a thin promoted mirror's reserve must cap the min-gap (never over-demand)")

    # 5. no terminal Image row -> refuse
    rows = [
        SimpleNamespace(surface="Object", thickness=10.0, name="Object"),
        SimpleNamespace(surface="Standard", thickness=100.0, name="Rear Datum"),
        SimpleNamespace(surface="Standard", thickness=5.0, name="Detector"),
    ]
    ed = _editor(rows)
    ed.snap_detector_to_image_plane = lambda: (_ for _ in ()).throw(AssertionError("snap must not run"))
    try:
        ed._swap_auto_refocus_to_best_focus()
    except AssertionError as exc:
        failures.append(f"guard: {exc}")

    # 6. bugs/0391: a GLUED CAMERA reserves its whole body -- min-gap = clearance + the
    # flange-to-sensor depth, so the body (not just the sensor plane) clears the upstream
    # element. The camera-body depth must WIN over a thin fold-mirror reserve (the 0388 bug).
    STANDOFF = 11.48  # hr25MCX flange-to-sensor
    clearance = float(_editor(_lens_image_rows(100.0))._SWAP_REFOCUS_MIN_CLEARANCE_MM)
    cam_rows = [
        SimpleNamespace(surface="Object", thickness=10.0, name="Object"),
        SimpleNamespace(surface="Standard", thickness=120.0, name="Front Datum"),
        SimpleNamespace(surface="Standard", thickness=0.8, name="Promoted RA Mirror"),
        SimpleNamespace(surface="Image", thickness=0.0, name="Image"),
    ]
    ed = _editor(cam_rows)
    ed._current_camera_front_to_sensor_mm = lambda: STANDOFF
    want = clearance + STANDOFF
    got = ed._swap_refocus_min_gap()
    if abs(got - want) > 1e-9:
        failures.append(
            f"camera-body: min-gap must reserve the flange depth ({want} = {clearance}+{STANDOFF}); "
            f"got {got} (thin-mirror reserve wrongly capped the camera body)"
        )
    # the clamp must actually pull a too-close best-focus back to the body-clearance gap
    ed2 = _editor(_lens_image_rows(100.0))
    ed2._current_camera_front_to_sensor_mm = lambda: STANDOFF
    ed2.snap_detector_to_image_plane = lambda: (setattr(ed2.rows[-2], "thickness", 3.0) or True)
    ed2._swap_auto_refocus_to_best_focus()
    if abs(ed2.rows[-2].thickness - want) > 1e-9:
        failures.append(
            f"camera-body: a 3mm best-focus (sensor-safe but body-colliding) must clamp to {want}; "
            f"got {ed2.rows[-2].thickness}"
        )
    if not any("camera body" in m for m in ed2._status_messages):
        failures.append("camera-body: the clamp must flag that the camera body limited focus")

    # 7. bugs/0392: the REAL fix -- MESH-geometry camera-body clearance. The 0391 flange floor
    # measured from the mirror CENTRE and used the flange (not physical body-front) depth, so
    # the body still crashed. Uses the actual flag geometry as the fixture (camera body AABB,
    # promoted RA-mirror AABB, folded leg = +x).
    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin as _M
    CAM = (200.9, 270.9, -35.0, 35.0, -22.6, 51.0)          # camera body world AABB (flag)
    MIRROR = (193.7, 218.7, -12.5, 12.5, 59.4, 84.4)        # promoted RA mirror world AABB (flag)
    LEG = (1.0, 0.0, 0.0)                                   # folded leg axis
    deficit = _M._camera_body_clearance_deficit_pure(CAM, MIRROR, LEG, clearance)
    # camera front 200.9, mirror rear 218.7, clearance 2 -> deficit = 218.7 + 2 - 200.9 = 19.8
    if abs(deficit - 19.8) > 1e-6:
        failures.append(f"mesh-clearance: flag geometry must need 19.8mm; got {deficit}")
    # HONEST post-bump check: moving the camera +deficit along the leg clears the mirror by exactly clearance
    post_clearance = (CAM[0] + deficit) - MIRROR[1]
    if abs(post_clearance - clearance) > 1e-6:
        failures.append(f"mesh-clearance: after the bump the body must clear by {clearance}mm; got {post_clearance}")
    # sign/scale invariance + already-clear
    if abs(_M._camera_body_clearance_deficit_pure(CAM, MIRROR, (-3, 0, 0), clearance) - 19.8) > 1e-6:
        failures.append("mesh-clearance: deficit must be invariant to leg-axis sign/scale")
    if _M._camera_body_clearance_deficit_pure((300, 370, -35, 35, -22, 51), MIRROR, LEG, clearance) != 0.0:
        failures.append("mesh-clearance: an already-clear camera must need 0")
    # WIRED end-to-end: the full auto-refocus bumps the gap past the floor by the mesh deficit + flags
    mirror_row = SimpleNamespace(
        name="Promoted RA Mirror", surface="Standard", thickness=13.48,
        advanced={"StepOverlayPromotion": {"bounds_min_world": [193.7, -12.5, 59.4],
                                            "bounds_max_world": [218.7, 12.5, 84.4]}},
    )
    ed3 = _editor([SimpleNamespace(surface="Object", thickness=10.0, name="Object"),
                   mirror_row,
                   SimpleNamespace(surface="Image", thickness=0.0, name="Image")])
    ed3._current_camera_front_to_sensor_mm = lambda: STANDOFF
    ed3._camera_body_world_bounds = lambda: (CAM, "ok")   # (bounds, reason) per bugs/0393
    ed3._folded_leg_axis_unit = lambda: LEG
    ed3._current_camera_record = lambda: {"camera_front_to_sensor_mm": STANDOFF}
    # best focus lands the sensor at the floor (13.48); the mesh deficit must push it to ~33.28
    ed3.snap_detector_to_image_plane = lambda: (setattr(ed3.rows[-2], "thickness", 13.48) or True)
    ed3._swap_auto_refocus_to_best_focus()
    want_gap = 13.48 + 19.8
    if abs(ed3.rows[-2].thickness - want_gap) > 1e-6:
        failures.append(
            f"mesh-clearance: the swap must bump the gap to {want_gap} (floor + mesh deficit); "
            f"got {ed3.rows[-2].thickness}"
        )
    if not any("camera body" in m for m in ed3._status_messages):
        failures.append("mesh-clearance: the mesh-deficit bump must flag the camera-body limit")

    # 8. bugs/0393b: the mirror obstacle centre must come from the LIVE scene-bundle placement,
    # not the STALE promotion metadata. The real flag: a moved RA mirror's stored centre put the
    # obstacle 30 mm off (Z-separated from the camera) -> deficit 0 -> camera stayed crashed.
    STALE = {"bounds_min_world": [193.65, -12.5, 59.4], "bounds_max_world": [218.65, 12.5, 84.4]}
    mrow = SimpleNamespace(name="Promoted OPTICAL STEP optical solid", surface="Standard",
                           thickness=13.48, advanced={"StepOverlayPromotion": STALE})
    rows8 = ([SimpleNamespace(surface="Object", thickness=10.0, name="Object")]
             + [SimpleNamespace(surface="Standard", thickness=1.0, name=f"r{i}") for i in range(5)]
             + [mrow, SimpleNamespace(surface="Image", thickness=0.0, name="Image")])
    CAM_CUR = (200.9, 270.9, -35.0, 35.0, -22.6, 51.0)
    LEG_Z = (0.0, 0.0, -1.0)
    # (a) STALE centre (no bundle) -> the obstacle is Z-separated from the camera -> deficit 0
    ed_stale = _editor(list(rows8))
    ed_stale._camera_body_world_bounds = lambda: (CAM_CUR, "ok")
    ed_stale._folded_leg_axis_unit = lambda: LEG_Z
    ed_stale._current_camera_record = lambda: {"x": 1}
    if ed_stale._swap_camera_body_clearance_deficit() != 0.0:
        failures.append("live-centre: with stale (Z-separated) bounds the deficit must be 0 (the bug)")
    # (b) LIVE bundle centre at the mirror's REAL position -> deficit ~12.5, camera clears
    ed_live = _editor(list(rows8))
    ed_live._camera_body_world_bounds = lambda: (CAM_CUR, "ok")
    ed_live._folded_leg_axis_unit = lambda: LEG_Z
    ed_live._current_camera_record = lambda: {"x": 1}
    ed_live._last_scene_bundle = SimpleNamespace(placements=[
        SimpleNamespace(source_kind="optical_solid", row_index=len(ed_live.rows) - 2,
                        center_world=[236.0, 0.0, 53.0])])
    d_live = ed_live._swap_camera_body_clearance_deficit()
    if not (12.0 < d_live < 13.0):
        failures.append(f"live-centre: the LIVE placement centre must give ~12.5mm; got {d_live}")
    dbg = getattr(ed_live, "_swap_clearance_debug", {}) or {}
    if dbg.get("obstacle_center_source") != "live_bundle":
        failures.append(f"live-centre: must report obstacle_center_source=live_bundle; got {dbg.get('obstacle_center_source')}")
    # the re-centred obstacle must match the REAL actor bounds (x[223.3,248.6] z[40.4,65.7])
    ob = dbg.get("obstacle_bounds") or []
    if not (ob and abs(ob[0] - 223.5) < 0.6 and abs(ob[5] - 65.5) < 0.6):
        failures.append(f"live-centre: re-centred obstacle bounds must match the real mirror; got {ob}")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("Lens-swap auto-refocus validation failed:")
        for name in failures:
            print(f"- {name}")
        return 1
    print(
        "Lens-swap auto-refocus validation passed: snap-can't-compute no-ops, a sub-floor "
        "solve clamps + flags, a safe solve is untouched, a thin fold-mirror reserve caps the "
        "min-gap, an Image-less layout is refused, a glued camera reserves its whole body "
        "depth (bugs/0391), and the MESH-geometry clearance clears the real camera body past "
        "the mirror on the flag geometry (bugs/0392)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
