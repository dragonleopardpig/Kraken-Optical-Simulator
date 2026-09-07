"""Guard for bugs/0730 -- the imaging launch must come from the DEVICE, not from empty space.

Flag 20260907_095208_913: "rays are not launched from 6 points. The blue rays seems go hay
wired." Censused on om05a: the imaging source launched from a 3x3 grid at (+-29.38, +-29.38, 0)
-- sensor/|m| in BOTH axes -- while the inspected face is a 50 x 1 mm strip. Two thirds of the
field points sat 29 mm above and below a 1 mm-tall device, and their rays wandered through the
tower geometry. Only 35 of 4332 traced paths reached the sensor.

After the fix the launch is clamped to the physical face and a thin axis is sampled once, so the
grid becomes the 3 points along each face the user expected -- 6 across the two faces -- and 477
rays reach the sensor.

Checks (display-free):
  A  _object_face_half_extents reads the inspected face; None when there is no part.
  B  _clamp_launch_to_object_face intersects the FOV rectangle with the face, and passes the
     rectangle through untouched when the scene declares no part (every ordinary scene).
  C  _sample_imaging_field_grid_pairs samples a THIN axis once (a 50 x 1 strip gives 3 points,
     not 9) while a square field -- including a SMALL square one -- keeps the full grid.
  D  the field points all lie ON the face.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0730_launch_on_the_object_face
"""

from __future__ import annotations

import numpy as np


class _Sampler:
    """The sampling mixin over a stub editor: face spec + field count only."""

    from KrakenOS.UI.services.trace_preview_sampling import TracePreviewSamplingMixin as _Mixin

    _object_face_half_extents = _Mixin._object_face_half_extents
    _clamp_launch_to_object_face = _Mixin._clamp_launch_to_object_face
    _sample_imaging_field_grid_pairs = _Mixin._sample_imaging_field_grid_pairs

    def __init__(self, part=None, half=None, count=3):
        self.inspection_part_spec = part
        self._half = half
        self._count = int(count)
        self._folded_field_center_state = None

    def _imaging_fov_half_extents(self):
        return self._half

    def _current_field_count(self):
        return self._count

    def _sample_field_grid_pairs(self, maximum):  # only reached when there is no rectangle
        return [(0.0, 0.0)]

    def _launch_field_radial_max(self):
        return 1.0


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    om05a_part = {"enabled": True, "width_mm": 50.0, "height_mm": 1.0, "depth_mm": 50.0,
                  "active_face": "front", "axis_reach_mm": 0.0, "axis_offset_mm": 0.0, "step_path": ""}

    # ---- A: the face ---------------------------------------------------------------------------
    face = _Sampler(part=om05a_part)._object_face_half_extents()
    ok(
        face is not None and abs(face[0] - 25.0) < 1e-9 and abs(face[1] - 0.5) < 1e-9,
        f"A1: the inspected 50 x 1 mm front face gives half-extents (25.0, 0.5) ({face})",
    )
    ok(
        _Sampler(part=None)._object_face_half_extents() is None
        and _Sampler(part=dict(om05a_part, enabled=False))._object_face_half_extents() is None,
        "A2: no part (or a disabled one) declares no face -- ordinary scenes are unaffected",
    )

    # ---- B: the clamp ---------------------------------------------------------------------------
    clamped = _Sampler(part=om05a_part)._clamp_launch_to_object_face((29.38, 29.38))
    ok(
        abs(clamped[0] - 25.0) < 1e-9 and abs(clamped[1] - 0.5) < 1e-9,
        f"B1: the 29.38 x 29.38 sensor/|m| rectangle is intersected with the face ({clamped})",
    )
    inside = _Sampler(part=om05a_part)._clamp_launch_to_object_face((10.5, 0.4))
    ok(
        abs(inside[0] - 10.5) < 1e-9 and abs(inside[1] - 0.4) < 1e-9,
        f"B2: a FOV smaller than the face is kept as it is (a solved 21 mm field) ({inside})",
    )
    passthrough = _Sampler(part=None)._clamp_launch_to_object_face((29.38, 29.38))
    ok(
        abs(passthrough[0] - 29.38) < 1e-9 and abs(passthrough[1] - 29.38) < 1e-9,
        "B3: with no declared part the rectangle passes through untouched",
    )
    ok(_Sampler(part=om05a_part)._clamp_launch_to_object_face(None) is None, "B4: None in, None out")

    # ---- C: the grid ------------------------------------------------------------------------------
    strip = _Sampler(part=om05a_part, half=(25.0, 0.5), count=3)._sample_imaging_field_grid_pairs()
    ok(
        len(strip) == 3 and sorted(round(p[0], 3) for p in strip) == [-25.0, 0.0, 25.0]
        and all(abs(p[1]) < 1e-9 for p in strip),
        f"C1: a 50 x 1 strip is sampled at 3 points ALONG it, none off the device ({strip})",
    )
    square = _Sampler(part=None, half=(20.0, 20.0), count=3)._sample_imaging_field_grid_pairs()
    ok(len(square) == 9, f"C2: a square field keeps the full 3x3 grid ({len(square)} points)")
    small = _Sampler(part=None, half=(0.75, 0.75), count=3)._sample_imaging_field_grid_pairs()
    ok(
        len(small) == 9,
        f"C3: a SMALL square field (1.5 x 1.5 mm microscope) still gets the full grid -- the rule "
        f"is the aspect, not the size ({len(small)} points)",
    )
    tall = _Sampler(part=None, half=(0.5, 25.0), count=3)._sample_imaging_field_grid_pairs()
    ok(
        len(tall) == 3 and all(abs(p[0]) < 1e-9 for p in tall),
        f"C4: the rule works on either axis (a tall thin field samples along y) ({tall})",
    )

    # ---- D: every point is on the face ---------------------------------------------------------------
    face_half = _Sampler(part=om05a_part)._object_face_half_extents()
    ok(
        all(abs(x) <= face_half[0] + 1e-9 and abs(y) <= face_half[1] + 1e-9 for x, y in strip),
        "D1: every sampled field point lies ON the inspected face",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0730 launch-on-the-object-face validation PASSED")
        return 0
    print("0730 launch-on-the-object-face validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
