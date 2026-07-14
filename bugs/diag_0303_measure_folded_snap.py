"""0303 diag: does the Measure axis-snap project correctly on a FOLDED layout?

Reproduces the pure numeric core of the Measure tool's optical-axis snap using
the real folded geometry captured in the flagged recording
(flag_20260714_145421_497): two RA-mirror folds send the axis along +X (z=87.3)
where the imaging lens sits, then down -Z to the camera.

We bind the real inspector methods to a fake ``self`` (no Tk / VTK) and check:

* a lens-edge world pick (off-axis, y=+27) projects onto the +X reflected arm at
  the lens's axial position -> an ON-AXIS point, so the mirror->lens distance is
  measured ALONG the optical axis (the user's requirement);
* the snap only fires when the picked actor is RECOGNISED (in _actor_step_map /
  _actor_row_map) -- an unrecognised edge pick returns None (the raw off-axis
  point is kept), which is the reported bug.

Pure numpy; safe headless.
"""

from __future__ import annotations

import numpy as np

from KrakenOS.UI.open3d_inspector import Kraken3DInspector

# Real folded axis branches from the recording's state.json.
AXIS_RECORDS = [
    {"points": [[0.0, 0.0, -230.283], [0.0, 0.0, 87.3]]},              # incoming -Z..+Z
    {"points": [[0.0, 0.0, 87.3], [267.0755, 0.0, 87.3]]},            # +X reflected arm (lens here)
    {"points": [[267.0755, 0.0, 87.3], [267.0755, 0.0, -24.66]]},     # -Z camera arm
]

# Lens STEP overlay world centre from state.json step_actor_bounds["lens"].
LENS_CENTER = np.array([194.545, 0.158, 87.312], dtype=float)
# A pick on the lens TOP edge: off the axis in +Y (the "wrong place" the raw
# point-to-point would record).
LENS_EDGE_PICK = np.array([194.545, 27.66, 87.312], dtype=float)
# The first click: the RA mirror fold centre where the axes cross.
MIRROR_CENTER = np.array([267.0755, 0.0, 87.3], dtype=float)


class _Fake:
    """Minimal stand-in carrying just the attrs the snap methods read."""

    _project_world_onto_optical_axis = Kraken3DInspector._project_world_onto_optical_axis

    def __init__(self, recognised: bool):
        self._optical_axis_pick_records = AXIS_RECORDS
        # 'lens' recognised as a STEP overlay (or not, to show the bug).
        self._actor_step_map = {"lens-body": "lens"} if recognised else {}
        self._actor_row_map = {}


def main() -> int:
    failures: list[str] = []
    proj = Kraken3DInspector._project_world_onto_optical_axis
    snap = Kraken3DInspector._measure_axis_snap_for_pick

    # 1) The lens-edge pick projects onto the +X arm at the lens axial x, y=0.
    on_axis = np.asarray(proj(_Fake(True), LENS_EDGE_PICK), dtype=float)
    print("lens edge pick        :", LENS_EDGE_PICK.tolist())
    print("projected onto axis   :", np.round(on_axis, 3).tolist())
    if abs(on_axis[1]) > 1e-6:
        failures.append(f"projected point is not on the axis (y={on_axis[1]:.3f} != 0)")
    if abs(on_axis[2] - 87.3) > 1e-3:
        failures.append(f"projected z drifted off the +X arm: {on_axis[2]:.3f} != 87.3")
    if abs(on_axis[0] - LENS_EDGE_PICK[0]) > 1e-3:
        failures.append("projection did not KEEP the lens axial position (x)")

    # 2) The measured distance is ALONG the axis (mirror centre -> lens on-axis).
    mirror_on_axis = np.asarray(proj(_Fake(True), MIRROR_CENTER), dtype=float)
    axial = float(np.linalg.norm(on_axis - mirror_on_axis))
    raw = float(np.linalg.norm(LENS_EDGE_PICK - MIRROR_CENTER))
    print(f"axial distance (snap) : {axial:.3f} mm")
    print(f"raw point-to-point    : {raw:.3f} mm  (off-axis, the reported 'wrong place')")
    if not (abs(axial - abs(267.0755 - 194.545)) < 1e-2):
        failures.append(f"axial distance wrong: {axial:.3f}")
    if raw <= axial:
        failures.append("raw distance should exceed the axial one (edge is off-axis)")

    # 3) Recognition gate: recognised -> snaps; unrecognised -> None (the bug).
    got_recognised = snap(_Fake(True), "lens-body", LENS_EDGE_PICK)
    got_unrecognised = snap(_Fake(False), "lens-edge-unmapped", LENS_EDGE_PICK)
    print("snap when recognised  :", None if got_recognised is None else np.round(got_recognised, 3).tolist())
    print("snap when unrecognised:", got_unrecognised)
    if got_recognised is None:
        failures.append("recognised lens pick did not snap")
    if got_unrecognised is not None:
        failures.append("unrecognised pick unexpectedly snapped")

    print()
    if failures:
        print("RESULT: FAIL")
        for f in failures:
            print(" -", f)
        return 1
    print("RESULT: ALL PASS -- projection is correct on the folded arm; the bug is")
    print("that the lens-edge actor is unrecognised, so the snap never fires.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
