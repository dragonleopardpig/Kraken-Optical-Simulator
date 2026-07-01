"""Guard: the CAD-style drag-orbit (`_rotate_camera_fixed_drag`) must never let the
scene "suddenly flip" mid-drag.

Flag 20260701_201224 ("I drag the scene, the scene rotate until suddenly the whole
assembly flips"): a sustained vertical drag tilted the camera past ~80 deg elevation,
where `_safe_view_up_for_camera` stops re-picking world +Y and discretely swaps the
view-up to +Z -- a 90 deg reorient that reads as the whole assembly flipping. The fix
clamps the drag elevation to +/-79 deg so world +Y stays a stable, valid up and the
swap can never happen.

Display-free: drives the REAL method against a standalone ``vtkCamera``.
Run: ``.devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_drag_orbit_no_flip``
"""
from __future__ import annotations

import types

import numpy as np
import vtk

from KrakenOS.UI.open3d_inspector import Kraken3DInspector

_ELEV_LIMIT = 79.0


class _FakeRenderer:
    def __init__(self, cam):
        self._cam = cam

    def GetActiveCamera(self):
        return self._cam


def _make_harness():
    cam = vtk.vtkCamera()
    # Prelude camera from recording_20260701_201300 (the flag's drag).
    cam.SetPosition(275.0243764837268, -296.5468845443834, -988.3237330426782)
    cam.SetFocalPoint(167.8515074321198, 0.0, 53.44856852930005)
    cam.SetViewUp(0.0, 1.0, 0.0)
    s = types.SimpleNamespace()
    s._renderer = _FakeRenderer(cam)
    s.render = lambda: None
    s._reset_camera_clipping_range_for_scene = lambda: None
    s.editor = types.SimpleNamespace(append_debug=lambda *a, **k: None)
    s._rotate_camera_fixed_drag = types.MethodType(
        Kraken3DInspector._rotate_camera_fixed_drag, s
    )
    s._safe_view_up_for_camera = Kraken3DInspector._safe_view_up_for_camera
    return s, cam


def _cam_elev(cam) -> float:
    pos = np.asarray(cam.GetPosition(), float)
    foc = np.asarray(cam.GetFocalPoint(), float)
    d = pos - foc
    r = float(np.linalg.norm(d))
    return float(np.degrees(np.arcsin(np.clip(d[1] / r, -1.0, 1.0)))) if r > 0 else 0.0


def _sustained_drag(dy: float, steps: int, failures: list[str], tag: str) -> None:
    s, cam = _make_harness()
    min_vy = 1.0
    for _ in range(steps):
        s._rotate_camera_fixed_drag(0.0, dy)
        min_vy = min(min_vy, abs(cam.GetViewUp()[1]))
    elev = _cam_elev(cam)
    # No flip: world +Y stays the up-axis (its y-component never collapses).
    if min_vy < 0.9:
        failures.append(f"{tag}: view-up flipped (min |view_up.y|={min_vy:.3f}) -- the assembly flip is back")
    # Elevation clamped just short of the pole/swap zone.
    if abs(elev) > _ELEV_LIMIT + 0.5:
        failures.append(f"{tag}: elevation {elev:.1f} exceeded the {_ELEV_LIMIT} deg clamp")
    return elev, min_vy


def main() -> int:
    failures: list[str] = []

    up_elev, up_vy = _sustained_drag(8.0, 120, failures, "drag-up")
    down_elev, down_vy = _sustained_drag(-8.0, 120, failures, "drag-down")

    # Below the clamp a normal drag still tilts (not frozen) and stays flip-free.
    s, cam = _make_harness()
    e0 = _cam_elev(cam)
    s._rotate_camera_fixed_drag(0.0, 50.0)  # ~5 deg tilt, well below the limit
    e1 = _cam_elev(cam)
    if not (2.0 < (e1 - e0) < 8.0):
        failures.append(f"below-limit tilt did not track the drag (delta={e1 - e0:.2f} deg, expected ~5)")
    if abs(cam.GetViewUp()[1]) < 0.9:
        failures.append("below-limit tilt flipped the view-up")

    # A pure horizontal drag orbits (azimuth) without tilting or flipping.
    s, cam = _make_harness()
    az_before = np.asarray(cam.GetPosition(), float) - np.asarray(cam.GetFocalPoint(), float)
    e_before = _cam_elev(cam)
    for _ in range(30):
        s._rotate_camera_fixed_drag(8.0, 0.0)
    az_after = np.asarray(cam.GetPosition(), float) - np.asarray(cam.GetFocalPoint(), float)
    moved = float(np.linalg.norm(az_after[[0, 2]] - az_before[[0, 2]]))
    if moved < 1.0:
        failures.append("horizontal drag did not orbit the camera (azimuth dead)")
    if abs(_cam_elev(cam) - e_before) > 1.0:
        failures.append("horizontal drag leaked into elevation (cross-coupled tilt)")
    if abs(cam.GetViewUp()[1]) < 0.9:
        failures.append("horizontal drag flipped the view-up")

    if failures:
        print("FAIL bugs/scene-flip drag-orbit:")
        for f in failures:
            print("  -", f)
        return 1
    print("PASS bugs/scene-flip drag-orbit clamp:")
    print(f"  - sustained drag-up clamps at elev={up_elev:.1f} deg, view-up stays +Y (|vy|>={up_vy:.3f})")
    print(f"  - sustained drag-down clamps at elev={down_elev:.1f} deg, view-up stays +Y (|vy|>={down_vy:.3f})")
    print("  - below the clamp the tilt still tracks the drag; horizontal drag orbits without tilt or flip")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
