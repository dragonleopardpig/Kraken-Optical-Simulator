"""Prove the locked trackball orbit (elev_sign=-1) sweeps a sustained vertical drag
THROUGH the pole continuously: elevation passes 79 deg and 90 deg (over the top) with
NO discrete view-up flip (step-to-step dot stays ~1), where the OLD clamp froze at 79."""
from __future__ import annotations

import numpy as np

DPP = 0.10


def _rodrigues(v, k, theta):
    v = np.asarray(v, float); k = np.asarray(k, float)
    k = k / (np.linalg.norm(k) or 1.0)
    c, s = np.cos(theta), np.sin(theta)
    return v * c + np.cross(k, v) * s + k * float(np.dot(k, v)) * (1.0 - c)


def _orbit(pos, foc, up, dx, dy):
    pos = np.asarray(pos, float); foc = np.asarray(foc, float); up = np.asarray(up, float)
    offset = pos - foc
    up = up / (np.linalg.norm(up) or 1.0)
    world_up = np.array([0.0, 1.0, 0.0])
    az = np.radians(-float(dx) * DPP)
    offset = _rodrigues(offset, world_up, az)
    up = _rodrigues(up, world_up, az)
    view_dir = -offset / np.linalg.norm(offset)
    right = np.cross(view_dir, up)
    rn = np.linalg.norm(right)
    if rn > 1e-9:
        right = right / rn
        el = np.radians(-1.0 * float(dy) * DPP)  # locked sign
        offset = _rodrigues(offset, right, el)
        up = _rodrigues(up, right, el)
    return foc + offset, up / (np.linalg.norm(up) or 1.0)


def _elev(pos, foc):
    d = np.asarray(pos, float) - np.asarray(foc, float)
    r = np.linalg.norm(d)
    return float(np.degrees(np.arcsin(np.clip(d[1] / r, -1.0, 1.0)))) if r > 0 else 0.0


def main() -> int:
    foc = np.array([0.0, 0.0, 0.0])
    pos = np.array([0.0, 0.0, 1000.0])  # level, elevation 0, looking -Z
    up = np.array([0.0, 1.0, 0.0])
    dy = 8.0  # ~0.8 deg/step

    max_elev = -1e9
    min_step_dot = 1.0
    max_step_up_deg = 0.0
    crossed_79 = crossed_top = False
    prev_up = up.copy()
    prev_offset = pos - foc
    max_offset_jump = 0.0
    r0 = np.linalg.norm(pos - foc)
    for i in range(220):
        pos, up = _orbit(pos, foc, up, 0.0, dy)
        e = _elev(pos, foc)
        max_elev = max(max_elev, e)
        if e > 79.0:
            crossed_79 = True
        d = np.dot(prev_up, up) / ((np.linalg.norm(prev_up)) * (np.linalg.norm(up)))
        min_step_dot = min(min_step_dot, float(d))
        max_step_up_deg = max(max_step_up_deg, float(np.degrees(np.arccos(np.clip(d, -1, 1)))))
        offset = pos - foc
        # once past the top, the camera's +Y offset starts decreasing while it swings
        # to the far side -- detect the top crossing by the up vector's y going negative
        if up[1] < 0:
            crossed_top = True
        max_offset_jump = max(max_offset_jump, float(np.linalg.norm(offset - prev_offset)))
        prev_up = up.copy()
        prev_offset = offset

    # radius must be preserved (rigid rotation)
    rN = np.linalg.norm(pos - foc)

    print(f"steps=220 dy={dy} (~0.8 deg/step)")
    print(f"max elevation reached      = {max_elev:.2f} deg   (OLD clamp stopped at 79)")
    print(f"crossed 79 deg             = {crossed_79}")
    print(f"went over the top (up.y<0) = {crossed_top}")
    print(f"min step-to-step up dot    = {min_step_dot:.6f}  (flip would drop toward 0)")
    print(f"max step-to-step up change = {max_step_up_deg:.4f} deg (should be ~0.8, never a 90 jump)")
    print(f"max single-step offset jump= {max_offset_jump:.3f} mm (continuous, no teleport)")
    print(f"radius preserved           = {r0:.3f} -> {rN:.3f}")
    ok = crossed_79 and crossed_top and min_step_dot > 0.99 and max_step_up_deg < 2.0 and abs(rN - r0) < 1e-6
    print("RESULT:", "PASS (through the pole, continuous, no flip)" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
