"""Guard for bugs/0621 — the launch grid samples the DELIVERED field.

flag_20260815: after a 55x55 solve the 3x3 pencils launched at ~90% of the drawn FOV
square — the launch-grid extents divided the sensor by the RAW paraxial |m|, the third
raw-reader after the FOV plate (bugs/0602) and the field converter (bugs/0610). The
sampler now routes its object-plane FOV extents through
`_delivered_finite_magnification()` (raw x folded_m_correction).

Checks (display-free):
  A  CONTRACT — the three FOV-extent sites + the auto-image-diameter candidate use
     the delivered helper; the helper applies folded_m_correction.
  B  BEHAVIOUR — with a synthetic correction c, `_imaging_fov_half_extents` returns
     sensor/(2*m*c) (the drawn-square numbers); with the correction unset it returns
     sensor/(2*m) exactly (neutrality — sequential scenes and stub guards unchanged).

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0621_launch_grid_delivered_field
"""

from __future__ import annotations

import inspect

import numpy as np


def run_checks():
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services import trace_preview_sampling as sampling_module

    mixin = None
    for name, cls in vars(sampling_module).items():
        if isinstance(cls, type) and hasattr(cls, "_imaging_fov_half_extents"):
            mixin = cls
            break
    if mixin is None:
        return False, ["FAIL: A: no sampling mixin with _imaging_fov_half_extents found"]

    # ---------------------------------------------------------------- A: contract
    # SELF-CONTAINED per site (no cross-method helper): several display-free guards
    # bind these methods alone onto tiny editor doubles, so a shared helper broke
    # them (launch_within_camera_fov went None). Each site inlines the correction.
    sites = {
        "_imaging_fov_half_extents": inspect.getsource(mixin._imaging_fov_half_extents),
        "_camera_fov_object_half_extents": inspect.getsource(mixin._camera_fov_object_half_extents),
        "_camera_fov_inscribed_object_radius": inspect.getsource(mixin._camera_fov_inscribed_object_radius),
    }
    not_delivered = [name for name, src in sites.items() if "folded_m_correction" not in src]
    if not_delivered:
        ok = False
        notes.append(
            f"FAIL: A (bugs/0621): launch-extent sites read raw m again "
            f"(missing folded_m_correction: {not_delivered}) -- pencils launch "
            "inside the drawn FOV square"
        )
    else:
        notes.append("PASS: A: all launch-extent sites inline the delivered magnification")

    # ---------------------------------------------------------------- B: behaviour
    class _Stub(mixin):
        def __init__(self, correction):
            self._folded_m_correction_state = correction

        def _current_finite_paraxial_magnification(self):
            return -0.4618

        def _current_camera_sensor_active_mm(self):
            return (23.0, 23.0)

        def _coupled_imaging_launch_half_extents(self):
            return None

    corrected = _Stub(0.906)._imaging_fov_half_extents()
    neutral = _Stub(None)._imaging_fov_half_extents()
    want_corrected = 23.0 / (0.4618 * 0.906) / 2.0
    want_neutral = 23.0 / 0.4618 / 2.0
    if corrected is None or abs(corrected[0] - want_corrected) > 1e-6:
        ok = False
        notes.append(
            f"FAIL: B (bugs/0621): corrected extents {corrected} != sensor/(2*m*c) "
            f"({want_corrected:.3f}) -- the grid does not land on the drawn square"
        )
    elif neutral is None or abs(neutral[0] - want_neutral) > 1e-6:
        ok = False
        notes.append(
            f"FAIL: B (bugs/0621): neutral extents {neutral} != sensor/(2*m) "
            f"({want_neutral:.3f}) -- unmeasured scenes moved"
        )
    else:
        notes.append(
            f"PASS: B: extents {corrected[0]:.2f} (corrected, the drawn-square number) / "
            f"{neutral[0]:.2f} (neutral) as derived"
        )

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for line in notes:
        print(line)
    print("Launch-grid-delivered-field validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
