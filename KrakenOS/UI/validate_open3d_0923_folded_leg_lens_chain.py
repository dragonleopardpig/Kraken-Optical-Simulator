"""bugs/0923 guard (display-free): lenses appended on a FOLDED leg trace where they are drawn.

The penta telescope chain (validate_open3d_penta_telescope_chain) appends a ball-lens pair, a
DCV, an achromat and a cylinder on the five-penta cascade's -X exit leg. Every ray stopped
before the first ball, through three independent breaks, and the chain's own measurements
projected the whole folded path onto the exit axis, so the cascade vouched for optics the rays
never reached. This guard pins the three rules the fix rests on; the end-to-end chain is its own
penta phase.

  R  a promoted STEP whose mesh was baked with an X/Y rotation does not take the native
     prescription (rebuilt from the UNROTATED STEP along +Z); a pure roll keeps it.
  S  a solid whose faces are all Transmit faces on one line, with faces on both sides, is a
     straight-through optic -- whichever way its axis points -- and nothing else is.
  P  the output-face pick measures "along the incoming axis" against the axis it is given (the
     follower walk's running beam), and against +Z when given none, as before.
  T  the chain's axis helper maps a TRACED direction (1e-6 residual) and refuses what it cannot
     map instead of silently returning no rotation.
"""
from __future__ import annotations

import sys

import numpy as np


def _face(face_id, normal, *, side="Down", function="Transmit/Port", area=100.0):
    return {"face_id": face_id, "function": function, "side_2d": side, "port_role": "Auto",
            "normal_world": list(normal), "centroid_world": [0.0, 0.0, 0.0], "area_mm2": area}


def run_checks() -> "tuple[bool, list[str]]":
    from KrakenOS.UI import nonseq_output_ports as ports
    from KrakenOS.UI.services.three_d_scene_tools import ThreeDSceneToolsMixin
    from KrakenOS.UI.validate_open3d_penta_telescope_chain import _tilts_to_align_local_axis_to_world

    notes: list[str] = []
    ok = True

    def check(label: str, passed: bool, detail: str) -> None:
        nonlocal ok
        ok = ok and bool(passed)
        notes.append(f"{label} = {detail}" if passed else f"{label} FAILED: {detail}")

    # R -- which baked rotations move the STEP axis
    moves = ThreeDSceneToolsMixin._baked_rotation_moves_step_axis
    cases = {
        (0.0, 270.0, 0.0): True, (90.0, 0.0, 0.0): True, (0.0, -90.0, 0.0): True,
        (0.0, 0.0, 90.0): False, (360.0, 0.0, 0.0): False, (0.0, 0.0, 0.0): False,
    }
    wrong = [angles for angles, expected in cases.items()
             if moves({"StepOverlayPromotion": {"step_rotation_deg": list(angles)}}) != expected]
    check("R_baked_rotation", not wrong and moves({}) is False and moves({"StepOverlayPromotion": {}}) is False,
          f"X/Y rotations skip the native plan, rolls and whole turns keep it (wrong: {wrong})")

    # S -- straight-through transmit optic
    straight = ports._is_straight_through_transmit_optic
    lens = [_face("F001", (1, 0, 0), side="Down"), _face("F002", (1, 0, 0), side="Right"),
            _face("F003", (-1, 0, 0), side="Left"), _face("F004", (-1, 0, 0), side="Up")]
    cube = [_face(f"F{i}", n) for i, n in enumerate(((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)))]
    mirrored = lens[:3] + [_face("F009", (-1, 0, 0), function="Mirror")]
    one_sided = [_face("F001", (1, 0, 0)), _face("F002", (1, 0, 0))]
    check("S_straight_through",
          straight(lens, (1, 0, 0)) and straight(lens, (-1, 0, 0)) and not straight(cube, (1, 0, 0))
          and not straight(mirrored, (1, 0, 0)) and not straight(one_sided, (1, 0, 0)),
          "a lens on the X line is straight-through both ways; a cube, a mirror-faced body and a one-sided body are not")

    # P -- incoming axis of the output pick
    picked = ports.select_optical_solid_output_face(lens, incoming_axis=(-1.0, 0.0, 0.0))
    side_pick = ports.select_optical_solid_output_face(lens)
    z_lens = [_face("A", (0, 0, 1), side="Right"), _face("B", (0, 0, -1), side="Down")]
    check("P_incoming_axis",
          picked is not None and picked["face_id"] in {"F003", "F004"}
          and side_pick is not None and side_pick["face_id"] == "F001"
          and ports.select_optical_solid_output_face(z_lens)["face_id"] == "A",
          f"a -X beam exits through a -X face ({None if picked is None else picked['face_id']}); "
          f"no axis keeps the +Z preference and the side pick ({None if side_pick is None else side_pick['face_id']})")

    # T -- the chain's axis helper
    traced = _tilts_to_align_local_axis_to_world((0.0, 0.0, 1.0), np.asarray([-1.0, -2.34e-6, -1.61e-6]))
    try:
        _tilts_to_align_local_axis_to_world((0.0, 0.0, 1.0), np.asarray([0.6, 0.8, 0.0]))
        refused = False
    except ValueError:
        refused = True
    check("T_axis_helper", traced == (0.0, -90.0, 0.0) and refused,
          f"a traced -X maps to {traced}; an unmappable direction raises")
    return ok, notes


if __name__ == "__main__":
    passed, lines = run_checks()
    for line in lines:
        print(line)
    print("PASS" if passed else "FAIL")
    sys.exit(0 if passed else 1)
