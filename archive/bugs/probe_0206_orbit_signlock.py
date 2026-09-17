"""Lock the trackball orbit signs against VTK's Azimuth/Elevation so the new
_orbit_camera_pose feels IDENTICAL below the pole. Compare, for a small below-pole
drag, the OLD essence (SetViewUp(+Y); Azimuth(-dx*dpp); Elevation(dy*dpp)) against a
candidate Rodrigues orbit, and print the residual for each elevation-sign choice."""
from __future__ import annotations

import numpy as np
import vtk

DPP = 0.10


def _rodrigues(v, k, theta):
    v = np.asarray(v, float)
    k = np.asarray(k, float)
    k = k / (np.linalg.norm(k) or 1.0)
    c, s = np.cos(theta), np.sin(theta)
    return v * c + np.cross(k, v) * s + k * float(np.dot(k, v)) * (1.0 - c)


def _orbit(pos, foc, up, dx, dy, elev_sign):
    pos = np.asarray(pos, float); foc = np.asarray(foc, float); up = np.asarray(up, float)
    offset = pos - foc
    r = np.linalg.norm(offset)
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
        el = np.radians(elev_sign * float(dy) * DPP)
        offset = _rodrigues(offset, right, el)
        up = _rodrigues(up, right, el)
    return foc + offset, up / (np.linalg.norm(up) or 1.0)


def _old(pos, foc, dx, dy):
    cam = vtk.vtkCamera()
    cam.SetPosition(*pos); cam.SetFocalPoint(*foc); cam.SetViewUp(0.0, 1.0, 0.0)
    cam.Azimuth(-dx * DPP)
    cam.Elevation(dy * DPP)
    return np.asarray(cam.GetPosition(), float), np.asarray(cam.GetViewUp(), float)


def main() -> int:
    pos = (300.0, 200.0, 800.0)
    foc = (0.0, 0.0, 0.0)
    up = (0.0, 1.0, 0.0)
    for dx, dy in [(10.0, 0.0), (0.0, 10.0), (10.0, 10.0), (-8.0, 6.0)]:
        op, ou = _old(pos, foc, dx, dy)
        print(f"\n(dx,dy)=({dx},{dy})  OLD pos={np.round(op,4).tolist()} up={np.round(ou,4).tolist()}")
        for sign in (+1.0, -1.0):
            np_, nu = _orbit(pos, foc, up, dx, dy, sign)
            dpos = float(np.linalg.norm(np_ - op))
            dup = float(np.linalg.norm(nu - ou))
            print(f"   elev_sign={sign:+.0f}: pos_resid={dpos:.5f} up_resid={dup:.5f}  new pos={np.round(np_,4).tolist()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
