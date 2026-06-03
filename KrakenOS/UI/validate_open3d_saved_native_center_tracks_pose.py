#!/usr/bin/env python3
"""Display-free regression for bugs/0012 (revert on release): the world centre
of a promoted optical-solid row must follow the *live* row pose, not the cached
promotion-time ``StepOverlayPromotion.center_world``.

A promoted optical-solid row's 3-D body is positioned by
``_saved_step_native_center_world`` (via ``_file_backed_row_display_transform``).
It used to return the cached ``center_world`` snapshot, so dragging the placement
Move handle updated ``desp`` (and the gap overlay) but the body stayed pinned and
reverted on release (flags 21:14 / 21:16: body bounds identical before/after a
slide while "the distance overlay change value"). The live world centre is
``(desp_x, desp_y, z_station + desp_z)`` -- equal to the cache at promotion, but
it tracks later slides.

This runs without a display: it calls the static method on a synthetic row.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_saved_native_center_tracks_pose
"""
from __future__ import annotations

import numpy as np

from KrakenOS.UI.services.three_d_scene_tools import ThreeDSceneToolsMixin


class _Row:
    def __init__(self, desp, advanced):
        self.desp_x, self.desp_y, self.desp_z = (float(v) for v in desp)
        self.advanced = advanced


def main() -> int:
    fn = ThreeDSceneToolsMixin._saved_step_native_center_world
    failures: list[str] = []
    z_station = 100.0
    # Promotion snapshot matches the live pose: desp_z=-87.5, z_station=100 ->
    # world z = 12.5 == cached center_world (mirrors the real flag's numbers).
    advanced = {"StepOverlayPromotion": {"center_world": [0.0, 0.0, 12.5]}}
    row = _Row((0.0, 0.0, -87.5), advanced)

    c0 = np.asarray(fn(row, z_station), dtype=float).reshape(-1)[:3]
    print("at promotion:", [round(float(v), 3) for v in c0])
    if abs(float(c0[2]) - 12.5) > 1e-6:
        failures.append(f"at promotion expected world z=12.5, got {c0[2]:.3f}")

    # Slide +10 mm along the axis (desp_z -87.5 -> -77.5): the body must follow.
    row.desp_z = -77.5
    c1 = np.asarray(fn(row, z_station), dtype=float).reshape(-1)[:3]
    print("after +10 axial slide:", [round(float(v), 3) for v in c1])
    if abs(float(c1[2]) - 22.5) > 1e-6:
        failures.append(
            f"after a +10 mm slide expected world z=22.5, got {c1[2]:.3f} -- the body is "
            "pinned to the cached center_world (bugs/0012 revert)"
        )

    # Lateral slide too (desp_x 0 -> 3).
    row.desp_x = 3.0
    c2 = np.asarray(fn(row, z_station), dtype=float).reshape(-1)[:3]
    print("after +3 lateral slide:", [round(float(v), 3) for v in c2])
    if abs(float(c2[0]) - 3.0) > 1e-6:
        failures.append(f"after a +3 mm x-slide expected world x=3.0, got {c2[0]:.3f}")

    # With no usable live pose, the cache is still honoured (no crash, no drift).
    nan_row = _Row((float("nan"), 0.0, 0.0), advanced)
    c3 = np.asarray(fn(nan_row, z_station), dtype=float).reshape(-1)[:3]
    if not np.all(np.isfinite(c3)) or abs(float(c3[2]) - 12.5) > 1e-6:
        failures.append(f"with a non-finite live pose, expected the cached center_world, got {c3}")

    if failures:
        print("\nFAIL: bugs/0012 saved-native centre tracks pose")
        for f in failures:
            print(f"  ! {f}")
        return 1
    print("\nPASS: promoted optical-solid body centre follows the live row pose")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
