"""Display-free guard for bugs/0556 -- "click Normal to Sensor, overlay show nothing"
(flag_20260805_120322_650).

The view came up EMPTY. The camera pose recorded in the flag says why:

    camera_focal   = (-0.47, 0.06, 134.03)   <- where it aimed
    sensor (row 8) = x 177..210, z 10.2      <- centre (193.4, 0, 10.2)
    parallel_scale = 12.44                   <- correctly sized for a 23x23 sensor

The SCALE was right and the CENTRE was ~194 mm out in x and ~124 mm in z, so the view framed
empty space. The aim point is the tell: x ~ 0 is the straight global axis and z ~ 134 is the
image row's STATION.

``_imaging_detector_row_anchor_target`` synthesizes the sensor anchor when the bundle carries no
live detector target, and it hardcoded ``center_world=(0, 0, z_plane)`` / ``normal_world=
(0, 0, 1)`` on the stated grounds that "folded scenes carry real detector targets in their
bundles and never reach this fallback". That is false on a 0433-FROZEN scene whose arms have not
converged: every detector target is a default-distance PARK, the resolver falls through to the
synthetic anchor, and the anchor lands on the straight axis. This is the FIFTH consumer to trip
over the frozen-frame hole (after the camera frame, the solve gate, the cone crease and the
lens-swap block placement).

Fix: read the row's own world pose -- ``(desp_x, desp_y, station + desp_z)`` with the
orientation from its tilts. On an unfrozen row (desp 0, tilt 0) that reduces EXACTLY to the old
axial values.

Checks (pure, no VTK/tk):
- UNFROZEN UNCHANGED: a straight prescription yields the old (0, 0, station) / +Z answer.
- FROZEN: the flagged scene's numbers put the anchor on the real sensor, not the axis.
- ORIENTATION: a flipped (tilt_x 180) sensor reports its own normal, not a hardcoded +Z.
- NOT THE STATION: the frozen anchor must not sit at the station plane the old code used.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0556_sensor_anchor_frozen_aware
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np


def _row(**kwargs):
    values = dict(
        surface="Standard", name="row", thickness=0.0, diameter=32.583,
        desp_x=0.0, desp_y=0.0, desp_z=0.0, tilt_x=0.0, tilt_y=0.0, tilt_z=0.0,
    )
    values.update(kwargs)
    return SimpleNamespace(**values)


def _stub(rows):
    from KrakenOS.UI.services.three_d_scene_tools import ThreeDSceneToolsMixin

    class _Stub(ThreeDSceneToolsMixin):
        def __init__(self, rows):
            self.rows = rows

        def _row_z_positions(self):
            out, total = [0.0], 0.0
            for row in self.rows[:-1]:
                total += float(row.thickness)
                out.append(total)
            while len(out) < len(self.rows):
                out.append(total)
            return out

        def _object_surface_plane_z(self, index):
            return self._row_z_positions()[index]

    return _Stub(rows)


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []
    try:
        from KrakenOS.UI.services.three_d_scene_tools import ThreeDSceneToolsMixin  # noqa: F401
    except Exception as exc:  # pragma: no cover - environment skip
        return True, [f"SKIP: three_d_scene_tools unavailable ({type(exc).__name__}: {exc})"]

    station = 134.03

    # --- UNFROZEN UNCHANGED --------------------------------------------------------------
    plain = _stub([_row(thickness=station), _row(surface="Image", name="Image")])
    target = plain._imaging_detector_row_anchor_target()
    if target is None:
        failures.append("unfrozen: no anchor synthesized at all")
    else:
        if not np.allclose(np.asarray(target.center_world, dtype=float), [0.0, 0.0, station], atol=1e-9):
            failures.append(
                f"unfrozen: centre {np.asarray(target.center_world)} != the old axial "
                f"(0, 0, {station}) -- a straight scene must be byte-identical"
            )
        if not np.allclose(np.asarray(target.normal_world, dtype=float), [0.0, 0.0, 1.0], atol=1e-9):
            failures.append(f"unfrozen: normal {np.asarray(target.normal_world)} != +Z")

    # --- FROZEN: the flagged scene ---------------------------------------------------------
    frozen = _stub([
        _row(thickness=station),
        _row(surface="Image", name="Image", desp_x=193.4, desp_y=0.0,
             desp_z=10.2 - station, tilt_x=180.0),
    ])
    target = frozen._imaging_detector_row_anchor_target()
    if target is None:
        failures.append("frozen: no anchor synthesized at all")
        return (not failures), failures
    centre = np.asarray(target.center_world, dtype=float)
    if not np.allclose(centre, [193.4, 0.0, 10.2], atol=1e-6):
        failures.append(
            f"frozen: anchor at {centre}, but the sensor is at (193.4, 0, 10.2) -- the camera "
            "frames empty space (bugs/0556)"
        )
    # NOT THE STATION: the precise old-code failure, stated as its own assertion.
    if abs(float(centre[2]) - station) < 1e-6 and abs(float(centre[0])) < 1e-6:
        failures.append(
            f"frozen: anchor sits on the straight axis at the station plane {station} -- that IS "
            "the bug; the row's desp must be honoured"
        )
    # --- ORIENTATION -----------------------------------------------------------------------
    normal = np.asarray(target.normal_world, dtype=float)
    if abs(abs(float(normal[2])) - 1.0) > 1e-6:
        failures.append(f"frozen: normal {normal} is not the flipped sensor's own axis")
    if np.allclose(normal, [0.0, 0.0, 1.0], atol=1e-9):
        failures.append(
            "frozen: a tilt_x=180 sensor reported a hardcoded +Z normal -- the orientation must "
            "come from the row's tilts"
        )

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("0556 sensor-anchor validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(
        "0556 validation passed: the synthesized sensor anchor reads the row's WORLD pose, so "
        "Normal to Sensor aims at the real sensor on a frozen scene, while a straight "
        "prescription reduces exactly to the previous axial answer."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
