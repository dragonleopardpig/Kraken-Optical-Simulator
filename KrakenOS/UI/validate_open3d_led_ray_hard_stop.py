"""Display-free guard for bugs/0356 -- drawn rays stop at the opaque flat LED.

Imaging rays reflected off the beam splitter toward the LED terminated at the
display bound and sailed PAST the display-only LED module -- not physical. The LED
plate now joins the bugs/0088 detector hard-stop planes: same
``(center, normal, radial_limit)`` contract, same clip
(``scene_projector._clip_polyline_at_detector_planes``), with the normal pointing
INTO the plate so the LED's own flood (starting on the plane, heading away) is
never clipped.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_led_ray_hard_stop
"""

from __future__ import annotations

import inspect

import numpy as np

from KrakenOS.UI.scene_projector import _clip_polyline_at_detector_planes
from KrakenOS.UI.services.led_ray_hard_stop import led_plate_hard_stop_plane


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []

    plane = led_plate_hard_stop_plane([80.0, 0.0, 229.6], [-1.0, 0.0, 0.0], 27.5, 37.0)
    if plane is None:
        failures.append("a valid emitter seat must yield a hard-stop plane")
    else:
        center, normal, limit = plane
        if not np.allclose(normal, [1.0, 0.0, 0.0], atol=1e-12):
            failures.append("the plane normal must point INTO the plate (against emission)")
        if not (limit >= np.hypot(27.5, 37.0)):
            failures.append("the stop board must cover at least the emitting window")
        # A BS-reflected imaging ray crossing toward the plate truncates AT the plate...
        ray = np.asarray([[0.0, 0.0, 229.6], [120.0, 0.0, 229.6]], dtype=float)
        clipped, was_bounded = _clip_polyline_at_detector_planes(ray, [plane])
        if not was_bounded or abs(float(clipped[-1, 0]) - 80.0) > 1e-6:
            failures.append(f"a ray toward the plate must stop at x=80, got {clipped[-1]}")
        # ...the LED's own flood (starting ON the plate, heading away) is untouched...
        flood = np.asarray([[80.0, 0.0, 229.6], [0.0, 0.0, 229.6]], dtype=float)
        kept, was2 = _clip_polyline_at_detector_planes(flood, [plane])
        if was2 or not np.allclose(kept, flood):
            failures.append("the LED's own flood must never be clipped by its plate")
        # ...and a ray far outside the board (beyond the radial limit) passes free.
        offside = np.asarray(
            [[0.0, 300.0, 229.6], [120.0, 300.0, 229.6]], dtype=float
        )
        kept3, was3 = _clip_polyline_at_detector_planes(offside, [plane])
        if was3:
            failures.append("a ray missing the plate board must not be clipped")
    if led_plate_hard_stop_plane([80.0, 0.0, 0.0], [0.0, 0.0, 0.0], 27.5, 37.0) is not None:
        failures.append("a degenerate emit direction must return None")

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services.open3d_scene_refresh import Open3DSceneRefreshService

    planes_src = inspect.getsource(KrakenLayoutEditor._led_plate_planes_for_hard_stop)
    for needle in (
        "_drawable_scene_source_descriptors",
        "scene_source_spec_is_face_bound_marker",
        "led_plate_hard_stop_plane",
    ):
        if needle not in planes_src:
            failures.append(f"_led_plate_planes_for_hard_stop lost its {needle} gate")
    refresh_src = inspect.getsource(Open3DSceneRefreshService)
    if "_led_plate_planes_for_hard_stop" not in refresh_src:
        failures.append("the refresh ray loop does not merge the LED plate hard stop")
    if "_detector_planes_for_hard_stop" not in refresh_src:
        failures.append("the 0088 detector hard stop went missing from the refresh")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("LED-plate ray hard-stop validation failed:")
        for name in failures:
            print(f"- {name}")
        return 1
    print(
        "LED-plate ray hard-stop validation passed: rays reflected toward the flat "
        "LED truncate AT the plate via the 0088 clip contract, the LED's own flood "
        "and off-board rays pass free, and the refresh merges the plate plane behind "
        "the non-marker source gate."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
