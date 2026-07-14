"""Validate the Measure tool's optical-axis object-snap on a FOLDED layout.

The flagged recording (flag_20260714_145421_497): on a two-fold RA-mirror system
the user measured from an RA-mirror centre to the imaging lens; the first pick
snapped but the second -- aimed at the lens EDGE -- "wouldn't highlight, the
closest surface did, and the arrow landed in the wrong place". They want the
distance measured ALONG the optical axis (even though the lens edge is selected)
and an "X" cursor + snap feel while hovering (bugs/0303).

Root cause: the lens silhouette EDGE actor is drawn ``PickableOff``, so aiming at
it grazes the ray PAST the lens to whatever is behind -> the pick is not a
recognised component -> the always-on axis snap never fires -> the raw off-axis
edge point is recorded. The optical-axis projection itself is CORRECT on the
folded arm (it iterates every branch), so the fix is object-snap magnetism +
visible feedback, not new geometry.

This guard is display-free (no Tk / VTK render):

* the pure ``_measure_pick_offset_ring`` samples the exact cursor FIRST, then a
  symmetric ring (so a thin-edge miss still finds the body just inside);
* on the real folded axis branches, a lens-edge pick projects onto the +X
  reflected arm (on-axis: y=0, z=87.3, axial x kept) and the mirror->lens
  distance equals the axial separation -- NOT the longer off-axis raw distance;
* the recognition gate snaps a recognised component and returns ``None`` for an
  unrecognised edge pick (so the raw fallback is preserved);
* the hover + click + clear wiring (X cursor, snap marker, shared resolver) is
  asserted from source.

Exposes ``run_checks() -> (passed, failures)`` so it doubles as a penta phase.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import numpy as np

from KrakenOS.UI.open3d_inspector import Kraken3DInspector

# Real folded axis branches from the recording's state.json.
AXIS_RECORDS = [
    {"points": [[0.0, 0.0, -230.283], [0.0, 0.0, 87.3]]},           # incoming -Z..+Z
    {"points": [[0.0, 0.0, 87.3], [267.0755, 0.0, 87.3]]},          # +X reflected arm (lens)
    {"points": [[267.0755, 0.0, 87.3], [267.0755, 0.0, -24.66]]},   # -Z camera arm
]
LENS_EDGE_PICK = np.array([194.545, 27.66, 87.312], dtype=float)     # off-axis top edge
MIRROR_CENTER = np.array([267.0755, 0.0, 87.3], dtype=float)         # fold where axes cross


class _Fake:
    """Minimal stand-in binding just the pure snap methods under test."""

    _project_world_onto_optical_axis = Kraken3DInspector._project_world_onto_optical_axis
    _measure_axis_snap_for_pick = Kraken3DInspector._measure_axis_snap_for_pick
    _measure_recognised_component = Kraken3DInspector._measure_recognised_component

    def __init__(self, recognised: bool):
        self._optical_axis_pick_records = AXIS_RECORDS
        self._actor_step_map = {"lens-body": "lens"} if recognised else {}
        self._actor_row_map = {}


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []

    # --- 1) pure offset ring: exact cursor first, then a symmetric ring ---------
    ring = Kraken3DInspector._measure_pick_offset_ring(9.0)
    if not ring or ring[0] != (0.0, 0.0):
        failures.append("offset ring must sample the exact cursor (0,0) first")
    if len(ring) != 9:
        failures.append(f"offset ring should be centre + 8 samples, got {len(ring)}")
    radii = [round((dx * dx + dy * dy) ** 0.5, 3) for dx, dy in ring[1:]]
    if any(abs(r - 9.0) > 1e-3 for r in radii):
        failures.append(f"ring samples should all sit at the radius: {radii}")
    # symmetric ring: offsets cancel out
    sx = sum(dx for dx, _ in ring)
    sy = sum(dy for _, dy in ring)
    if abs(sx) > 1e-6 or abs(sy) > 1e-6:
        failures.append("offset ring is not symmetric about the cursor")

    # --- 2) folded projection: the lens-edge pick lands ON the +X arm -----------
    proj = _Fake(True)._project_world_onto_optical_axis(LENS_EDGE_PICK)
    proj = np.asarray(proj, dtype=float).reshape(-1)[:3]
    if abs(proj[1]) > 1e-6:
        failures.append(f"projected lens point is off-axis (y={proj[1]:.3f})")
    if abs(proj[2] - 87.3) > 1e-3:
        failures.append(f"projected lens point left the +X arm (z={proj[2]:.3f})")
    if abs(proj[0] - LENS_EDGE_PICK[0]) > 1e-3:
        failures.append("projection did not KEEP the lens axial position (x)")

    # measured distance is ALONG the axis, shorter than the raw off-axis span.
    mirror = np.asarray(_Fake(True)._project_world_onto_optical_axis(MIRROR_CENTER), dtype=float)
    axial = float(np.linalg.norm(proj - mirror))
    raw = float(np.linalg.norm(LENS_EDGE_PICK - MIRROR_CENTER))
    if abs(axial - abs(267.0755 - 194.545)) > 1e-2:
        failures.append(f"axial mirror->lens distance wrong: {axial:.3f}")
    if raw <= axial + 1e-6:
        failures.append("raw off-axis distance should exceed the on-axis one")

    # --- 3) recognition gate: recognised snaps, unrecognised falls back to raw --
    snapped = _Fake(True)._measure_axis_snap_for_pick("lens-body", LENS_EDGE_PICK)
    if snapped is None:
        failures.append("a recognised lens pick must snap to the axis")
    if _Fake(False)._measure_axis_snap_for_pick("lens-edge-unmapped", LENS_EDGE_PICK) is not None:
        failures.append("an unrecognised edge pick must NOT snap (keep the raw point)")
    if not _Fake(True)._measure_recognised_component("lens-body"):
        failures.append("_measure_recognised_component missed a mapped step actor")
    if _Fake(True)._measure_recognised_component(None):
        failures.append("_measure_recognised_component accepted a None key")

    # --- 4) hover / click / clear wiring (source asserts) -----------------------
    hover_src = inspect.getsource(Kraken3DInspector._update_measure_hover_highlight)
    for needle in ("_measure_resolve_snap", "_show_measure_snap_marker", "_set_measure_snap_cursor"):
        if needle not in hover_src:
            failures.append(f"hover does not call {needle}")

    press_src = inspect.getsource(Kraken3DInspector._on_left_button_press)
    if "_measure_resolve_snap" not in press_src:
        failures.append("the Measure click does not resolve through _measure_resolve_snap")
    if "_clear_measure_snap_marker" not in press_src:
        failures.append("the Measure click does not clear the snap marker before recording")

    cursor_src = inspect.getsource(Kraken3DInspector._set_measure_snap_cursor)
    if "X_cursor" not in cursor_src:
        failures.append("the snap cursor is not the 'X' pointer the user asked for")

    resolve_src = inspect.getsource(Kraken3DInspector._measure_resolve_snap)
    if "_measure_pick_offset_ring" not in resolve_src or "_measure_recognised_component" not in resolve_src:
        failures.append("_measure_resolve_snap does not use the ring + recognition gate")

    clear_src = inspect.getsource(Kraken3DInspector.clear_measurements)
    if "_clear_measure_snap_marker" not in clear_src:
        failures.append("clear_measurements does not clear the snap marker")

    marker_src = inspect.getsource(Kraken3DInspector._show_measure_snap_marker)
    if "PickableOff" not in marker_src:
        failures.append("the snap marker must be PickableOff (it must not be clickable)")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("Measure folded-axis object-snap validation failed:")
        for name in failures:
            print(f"- {name}")
        return 1
    print(
        "Measure folded-axis object-snap validation passed: on a folded RA-mirror "
        "layout a lens-edge pick projects onto the reflected arm so the mirror->lens "
        "distance is measured ALONG the optical axis, thin-edge picks are tolerated by "
        "the ring magnetism, and the hover shows an 'X' snap marker + cursor."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
