"""Guard: the trackball drag-orbit (`_rotate_camera_fixed_drag`) orbits CONTINUOUSLY
THROUGH the pole -- a sustained vertical drag never stops and never flips.

Flag 20260702_152020 (issue 2, "drag from top to bottom, it will stop somewhere,
unable to orbit indefinitely in this direction"): the old orbit clamped elevation at
+/-79 deg to dodge a discrete view-up swap (the earlier flag-20260701_201224 "assembly
flip"). That traded the flip for a dead-stop. The trackball fix carries the view-up
RIGIDLY with the camera offset -- both Rodrigues-rotated by the same increments -- so
the up vector rolls smoothly OVER the pole: no discrete swap (= no flip) AND no clamp
(= orbits indefinitely).

The requirements are complementary, and this guard asserts all of them:
  - "orbits indefinitely" : a sustained vertical drag passes THROUGH 79 deg and OVER
    the pole -- the view-up's y-component goes negative (the camera hangs upside down,
    a true trackball) -- and the orbit radius is preserved (a rigid rotation).
  - "no flip" : the motion is CONTINUOUS -- the step-to-step view-up dot stays ~1.
    A flip is a DISCONTINUITY (dot -> 0, a ~90 deg jump), NOT the up vector leaving +Y.
  - below the pole it is pose-IDENTICAL to the old VTK Azimuth/Elevation path, so the
    familiar drag feel is unchanged.

Display-free: drives the REAL method against a standalone ``vtkCamera``.
Run: ``.devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_drag_orbit_no_flip``
"""
from __future__ import annotations

import types

import numpy as np
import vtk

from KrakenOS.UI.open3d_inspector import Kraken3DInspector

_DPP = 0.10


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
    s._orbit_camera_pose = Kraken3DInspector._orbit_camera_pose
    return s, cam


def _offset(cam) -> np.ndarray:
    return np.asarray(cam.GetPosition(), float) - np.asarray(cam.GetFocalPoint(), float)


def _cam_elev(cam) -> float:
    d = _offset(cam)
    r = float(np.linalg.norm(d))
    return float(np.degrees(np.arcsin(np.clip(d[1] / r, -1.0, 1.0)))) if r > 0 else 0.0


def _sweep(dx: float, dy: float, steps: int) -> dict:
    """Drive the real drag handler ``steps`` times and gather continuity metrics."""
    s, cam = _make_harness()
    off0 = _offset(cam)
    r0 = float(np.linalg.norm(off0))
    prev_up = np.asarray(cam.GetViewUp(), float)
    max_elev, min_elev = -1e9, 1e9
    min_up_dot, max_up_step_deg = 1.0, 0.0
    min_vy = 1.0
    for _ in range(steps):
        s._rotate_camera_fixed_drag(dx, dy)
        e = _cam_elev(cam)
        max_elev, min_elev = max(max_elev, e), min(min_elev, e)
        up = np.asarray(cam.GetViewUp(), float)
        min_vy = min(min_vy, float(up[1]))
        denom = (float(np.linalg.norm(prev_up)) * float(np.linalg.norm(up))) or 1.0
        d = float(np.dot(prev_up, up) / denom)
        min_up_dot = min(min_up_dot, d)
        max_up_step_deg = max(max_up_step_deg, float(np.degrees(np.arccos(np.clip(d, -1.0, 1.0)))))
        prev_up = up
    offN = _offset(cam)
    return dict(
        max_elev=max_elev, min_elev=min_elev, min_up_dot=min_up_dot,
        max_up_step_deg=max_up_step_deg, min_vy=min_vy, r0=r0,
        rN=float(np.linalg.norm(offN)),
        azimuth_moved=float(np.linalg.norm((offN - off0)[[0, 2]])),
    )


def run_checks() -> tuple[bool, list[str]]:
    """Return ``(passed, notes)``; notes are failures on fail, else the summary."""
    failures: list[str] = []
    steps = 220

    up = _sweep(0.0, 8.0, steps)     # sustained drag-up  (~0.8 deg/step, 176 deg swing)
    down = _sweep(0.0, -8.0, steps)  # sustained drag-down

    for tag, m in (("drag-up", up), ("drag-down", down)):
        pole_elev = m["max_elev"] if tag == "drag-up" else m["min_elev"]
        # (1) orbits indefinitely: sweeps PAST the old 79 deg clamp, up to the pole.
        if abs(pole_elev) < 85.0:
            failures.append(
                f"{tag}: elevation only reached {pole_elev:.1f} deg -- the old ~79 deg clamp is still stopping the orbit"
            )
        # (2) goes OVER the pole (up vector inverts): a genuine indefinite trackball.
        if m["min_vy"] > -0.05:
            failures.append(
                f"{tag}: never went over the pole (min view_up.y={m['min_vy']:.3f}) -- orbit is not indefinite"
            )
        # (3) NO FLIP: the view-up stays CONTINUOUS (no discrete ~90 deg jump).
        if m["min_up_dot"] < 0.99:
            failures.append(
                f"{tag}: view-up jumped discontinuously (min step dot={m['min_up_dot']:.4f}) -- the assembly flip is back"
            )
        if m["max_up_step_deg"] > 2.0:
            failures.append(
                f"{tag}: view-up step change {m['max_up_step_deg']:.2f} deg (a flip is a ~90 deg jump)"
            )
        # (4) rigid rotation: the orbit radius is preserved.
        if abs(m["rN"] - m["r0"]) > 1e-4:
            failures.append(
                f"{tag}: orbit radius drifted {m['r0']:.3f}->{m['rN']:.3f} mm (not a rigid rotation)"
            )

    # (5) below the pole, pose-IDENTICAL to the old VTK Azimuth/Elevation path.
    s, cam = _make_harness()
    pos0, foc0, up0 = cam.GetPosition(), cam.GetFocalPoint(), cam.GetViewUp()
    s._rotate_camera_fixed_drag(10.0, 6.0)  # a moderate below-pole drag
    new_pos = np.asarray(cam.GetPosition(), float)
    ref = vtk.vtkCamera()
    ref.SetPosition(*pos0)
    ref.SetFocalPoint(*foc0)
    ref.SetViewUp(*up0)
    ref.Azimuth(-10.0 * _DPP)
    ref.Elevation(6.0 * _DPP)
    pose_resid = float(np.linalg.norm(new_pos - np.asarray(ref.GetPosition(), float)))
    if pose_resid > 1e-3:
        failures.append(
            f"below-pole drag diverged from VTK Azimuth/Elevation (pos_resid={pose_resid:.5f} mm) -- feel changed"
        )

    # (6) a pure horizontal drag orbits in azimuth without tilting or flipping.
    horiz = _sweep(8.0, 0.0, 30)
    if horiz["azimuth_moved"] < 1.0:
        failures.append("horizontal drag did not orbit the camera (azimuth dead)")
    if abs(horiz["max_elev"] - horiz["min_elev"]) > 1.0:
        failures.append("horizontal drag leaked into elevation (cross-coupled tilt)")
    if horiz["min_up_dot"] < 0.99:
        failures.append("horizontal drag flipped/jumped the view-up")

    # (7) bugs/0229: in a ROLLED view (the 0228 rotate buttons, e.g. view-up (0,0,-1))
    # a horizontal drag must orbit about the CURRENT view-up (screen-vertical), not the
    # old hard-coded world +Y -- the flagged "dragging left to right does not orbit as
    # intended". Screen-relative contract: the up is untouched (a rotation about
    # itself) and the offset's component along the up is invariant (the rotation plane
    # is perpendicular to the screen-vertical axis).
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector as _I

    rolled_up = np.asarray((0.0, 0.0, -1.0))
    pos0 = np.asarray((-600.0, 100.0, 25.0))
    foc0 = np.asarray((0.0, 100.0, 25.0))
    new_pos, new_up = _I._orbit_camera_pose(tuple(pos0), tuple(foc0), tuple(rolled_up), dx=120, dy=0)
    off0 = pos0 - foc0
    off1 = np.asarray(new_pos) - foc0
    up_kept = bool(np.allclose(new_up, rolled_up, atol=1e-9))
    along_up_invariant = abs(float(np.dot(off1, rolled_up)) - float(np.dot(off0, rolled_up))) < 1e-9
    moved = float(np.linalg.norm(off1 - off0)) > 1.0
    if not (up_kept and along_up_invariant and moved):
        failures.append(
            "rolled-view horizontal drag is not screen-relative (bugs/0229): "
            f"up_kept={up_kept} along_up_invariant={along_up_invariant} moved={moved} -- "
            "azimuth must rotate about the CURRENT view-up, not world +Y"
        )

    if failures:
        return False, failures
    notes = [
        f"sustained drag-up reaches elev {up['max_elev']:.1f} deg, over the top "
        f"(min view_up.y={up['min_vy']:.3f}), continuous (min step dot={up['min_up_dot']:.4f})",
        f"sustained drag-down reaches elev {down['min_elev']:.1f} deg, over the pole "
        f"(min view_up.y={down['min_vy']:.3f}), continuous (min step dot={down['min_up_dot']:.4f})",
        f"max step-to-step view-up change {max(up['max_up_step_deg'], down['max_up_step_deg']):.3f} deg "
        f"(never a ~90 deg flip); radius preserved to <1e-4 mm",
        f"below the pole pose-identical to VTK Azimuth/Elevation (pos_resid={pose_resid:.2e} mm)",
        "horizontal drag orbits in azimuth without tilt or flip",
    ]
    return True, notes


def main() -> int:
    passed, notes = run_checks()
    if not passed:
        print("FAIL bugs/0206 trackball drag-orbit through the pole:")
        for note in notes:
            print("  -", note)
        return 1
    print("PASS bugs/0206 trackball drag-orbit (continuous, through the pole, no flip):")
    for note in notes:
        print("  -", note)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
