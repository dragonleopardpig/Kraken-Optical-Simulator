"""Guard for bugs/0606 — the Normal-to-Sensor view draws ONLY landing rays.

After bugs/0605, rays ending on the sensor are all genuine arrivals, but 415 polylines
still CROSS the sensor plane beside the glass and visually overlap the square face-on.
While the sensor view is active, the ray draw keeps only `hit_detector` rays; every
other view draws the full set (misses keep flying visibly past per 0605).

Checks (display-free):
  A  The filter derives from the camera preset (single source of truth): the helper
     returns True exactly when `_camera_preset == "sensor_normal"`.
  B  BOTH draw loops in open3d_scene_refresh apply the filter and mark
     `_sensor_view_ray_filter_applied` when rays were skipped.
  C  Leaving the view (`_restore_sensor_isolation`) triggers a rays-only redraw when
     the marker is set — filtered rays are ABSENT, not hidden, so without the redraw
     they would stay missing in the restored scene.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0606_sensor_view_landing_rays_only
"""

from __future__ import annotations

import inspect


def run_checks():
    notes: list[str] = []
    ok = True

    from KrakenOS.UI import open3d_inspector as inspector_module
    from KrakenOS.UI.services import open3d_scene_refresh as refresh_module

    Inspector = inspector_module.Kraken3DInspector

    # ---------------------------------------------------------------- A: preset-derived
    class _Stub:
        _camera_preset = None

    helper = Inspector._sensor_view_hides_non_landing_rays
    stub = _Stub()
    on = []
    stub._camera_preset = "sensor_normal"
    on.append(bool(helper(stub)))
    stub._camera_preset = "+yz"
    on.append(bool(helper(stub)))
    stub._camera_preset = None
    on.append(bool(helper(stub)))
    if on != [True, False, False]:
        ok = False
        notes.append(
            f"FAIL: A (bugs/0606): helper states {on} != [True, False, False] -- the "
            "filter no longer derives from the sensor_normal preset"
        )
    else:
        notes.append("PASS: A: the filter derives from the camera preset alone")

    # ---------------------------------------------------------------- B: both loops
    src = inspect.getsource(refresh_module)
    applications = src.count("_sensor_view_hides_non_landing_rays()")
    markers = src.count("_sensor_view_ray_filter_applied = True")
    skips = src.count("filtered_non_landing += 1")
    if applications < 2 or markers < 2 or skips < 2:
        ok = False
        notes.append(
            f"FAIL: B (bugs/0606): filter applied in {applications} loop(s), marker set "
            f"in {markers}, skip in {skips} -- a draw path lost the landing-rays-only "
            "contract and plane-crossers overlap the sensor face-on again"
        )
    else:
        notes.append("PASS: B: both ray draw loops filter to landing rays and mark the state")
    if '!= "hit_detector"' not in src:
        ok = False
        notes.append(
            "FAIL: B (bugs/0606): the filter no longer keys on hit_detector -- either it "
            "hides arrivals or keeps crossers"
        )
    else:
        notes.append("PASS: B2: the kept class is hit_detector (the landing set)")

    # ---------------------------------------------------------------- C: exit redraw
    restore_src = inspect.getsource(Inspector._restore_sensor_isolation)
    if (
        "_sensor_view_ray_filter_applied" not in restore_src
        or "_refresh_rays_only" not in restore_src
    ):
        ok = False
        notes.append(
            "FAIL: C (bugs/0606): leaving the sensor view no longer redraws the rays -- "
            "filtered rays are ABSENT (not hidden), so the restored scene keeps missing them"
        )
    else:
        notes.append("PASS: C: leaving the view redraws the full ray set")

    # ---------------------------------------------------------------- D: no preset wipe
    # The first 0606 cut cleared `_camera_preset` inside the restore to stop the leaving
    # redraw from re-filtering. But set_camera_preset assigns the NEW preset BEFORE it
    # calls the restore, so that wiped the caller's own preset (every preset button and
    # nav-cube snap left `_camera_preset` None). The redraw must suppress the FILTER,
    # never the preset.
    if "_camera_preset = None" in restore_src:
        ok = False
        notes.append(
            "FAIL: D (bugs/0606): _restore_sensor_isolation clears _camera_preset -- "
            "set_camera_preset assigns its preset BEFORE calling it, so the caller's "
            "preset is wiped on every exit"
        )
    elif "_sensor_view_ray_filter_suppressed" not in restore_src:
        ok = False
        notes.append(
            "FAIL: D (bugs/0606): the leaving redraw no longer suppresses the filter -- "
            "it re-filters while the preset still reads sensor_normal, so the rays stay gone"
        )
    else:
        notes.append("PASS: D: the leaving redraw suppresses the filter, not the preset")

    # The suppression must actually win over a sensor_normal preset.
    stub2 = _Stub()
    stub2._camera_preset = "sensor_normal"
    stub2._sensor_view_ray_filter_suppressed = True
    if bool(helper(stub2)):
        ok = False
        notes.append("FAIL: D2 (bugs/0606): the suppression flag does not disable the filter")
    else:
        notes.append("PASS: D2: the suppression flag wins over the sensor_normal preset")

    # set_camera_preset must still assign the preset it was given (order-of-operations pin).
    preset_src = inspect.getsource(Inspector.set_camera_preset)
    if "_camera_preset = preset" not in preset_src:
        ok = False
        notes.append("FAIL: D3 (bugs/0606): set_camera_preset no longer records its preset")
    else:
        notes.append("PASS: D3: set_camera_preset records the preset it was given")

    # ------------------------------------------------------- E: swap leaves the view (0607)
    # A swap performed INSIDE the sensor view leaves a stale isolation: the old sensor
    # plane hides the incoming lens and the 0606 filter keeps hiding non-landing rays.
    leaver = getattr(Inspector, "leave_sensor_view_for_scene_change", None)
    if not callable(leaver):
        ok = False
        notes.append(
            "FAIL: E (bugs/0607): leave_sensor_view_for_scene_change is gone -- a swap "
            "inside the sensor view leaves the incoming optics invisible"
        )
    else:
        leaver_src = inspect.getsource(leaver)
        if "_restore_sensor_isolation" not in leaver_src or "_camera_preset = None" not in leaver_src:
            ok = False
            notes.append(
                "FAIL: E (bugs/0607): the scene-change exit no longer restores the isolation "
                "AND clears the view mode -- a stale preset keeps the ray filter on"
            )
        else:
            notes.append("PASS: E1: the scene-change exit restores the scene and clears the view mode")
        # It must be a no-op outside the view (never disturb an ordinary preset).
        stub3 = _Stub()
        stub3._camera_preset = "+yz"
        try:
            if bool(leaver(stub3)):
                ok = False
                notes.append("FAIL: E2 (bugs/0607): the scene-change exit fires outside the sensor view")
            else:
                notes.append("PASS: E2: the scene-change exit is a no-op outside the sensor view")
        except Exception as exc:
            ok = False
            notes.append(f"FAIL: E2 (bugs/0607): raised outside the view: {type(exc).__name__}: {exc}")

    from KrakenOS.UI.services import layout_table_workbench as workbench_module

    swap_src = inspect.getsource(workbench_module.LayoutTableWorkbenchMixin._switch_off_analysis_overlays_for_swap)
    if "leave_sensor_view_for_scene_change" not in swap_src:
        ok = False
        notes.append(
            "FAIL: E3 (bugs/0607): the swap no longer leaves the sensor view -- the user's "
            "confirmed expectation (flag_20260811_125507) regressed"
        )
    else:
        notes.append("PASS: E3: both swap paths leave the sensor view through the shared helper")
    # bugs/0599 had no guard of its own; pin it here since 0607 edits the same helper.
    if "switch_off_analysis_overlays" not in swap_src:
        ok = False
        notes.append(
            "FAIL: E4 (bugs/0599): the swap no longer switches the analysis overlays off -- "
            "swapping with them on re-runs every field scan (\"a super long time\")"
        )
    else:
        notes.append("PASS: E4: the swap still switches the analysis overlays off (bugs/0599)")

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for line in notes:
        print(line)
    print("Sensor-view-landing-rays-only validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
