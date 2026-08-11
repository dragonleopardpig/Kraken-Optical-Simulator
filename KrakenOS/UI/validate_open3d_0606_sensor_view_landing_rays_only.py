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

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for line in notes:
        print(line)
    print("Sensor-view-landing-rays-only validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
