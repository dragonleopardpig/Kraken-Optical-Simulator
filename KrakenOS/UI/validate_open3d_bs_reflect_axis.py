"""Guard: a beam splitter draws its REFLECT-branch optical axis (bugs/0428 Phase 1).

Flag flag_20260723_141437 ("No second optical axis is created for the BS plate"): a promoted BS transmits
straight (``axis:global``) but the reflected branch had no optical-axis guide. Phase 1 of the two-axis
proposal draws it: ``beam_splitter_reflect_axis_frames`` returns each BS's (fold_point, reflect_direction)
from the coating interaction face (same specular reflection as a mirror fold), and
``_bs_reflect_axis_guide_records`` emits an ``axis:global:split`` guide reaching to the scene extent.

DISPLAY ONLY: the follower placement still skips the BS (bugs/0396-0399) -- Phase 1 does not re-aim
anything; it only adds the second axis line. Placement is Phase 2.

Checks
------
* REFLECT-MATH -- specular reflection ``d - 2(d.n)n`` sends +Z off a 45-deg coating to +X, and the
  x=y=0 axis crosses the coating plane at ``t = (point.n)/n_z`` (reference reimplementation).
* NO-BS       -- ``beam_splitter_reflect_axis_frames`` returns ``[]`` when there is no promoted BS.
* MECHANISM   -- ``_bs_reflect_axis_guide_records`` uses ``beam_splitter_reflect_axis_frames`` and emits
  ``axis:global:split``; ``_optical_axis_records_for_3d`` calls it.
* PLACEMENT-UNCHANGED -- the follower builder still skips the BS (Phase 1 is display-only).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_bs_reflect_axis

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect

import numpy as np


def _reflect_axis(point, normal, incoming=(0.0, 0.0, 1.0)):
    """Reference reimplementation of beam_splitter_reflect_axis_frames' per-BS geometry."""
    n = np.asarray(normal, dtype=float) / np.linalg.norm(normal)
    d = np.asarray(incoming, dtype=float)
    t = float(np.dot(np.asarray(point, dtype=float), n)) / float(n[2])
    reflected = d - 2.0 * float(np.dot(d, n)) * n
    return np.array([0.0, 0.0, t]), reflected / np.linalg.norm(reflected)


def _check_reflect_math(failures, notes):
    # a 45-deg coating whose normal bisects +Z and +X -> +Z reflects to +X
    fold, refl = _reflect_axis(point=(0.0, 0.0, 53.0), normal=(-1.0, 0.0, 1.0))
    if not np.allclose(refl, (1.0, 0.0, 0.0), atol=1e-9):
        failures.append(f"REFLECT-MATH: +Z off a 45-deg coating must reflect to +X (got {refl.round(3)})")
    if not np.allclose(fold, (0.0, 0.0, 53.0), atol=1e-9):
        failures.append(f"REFLECT-MATH: the fold point must sit on the axis at the coating crossing (got {fold.round(3)})")
    if not [f for f in failures if f.startswith("REFLECT-MATH")]:
        notes.append("reflect-math = +Z off a 45-deg coating -> +X, fold point on the axis crossing")


def _check_no_bs(failures, notes):
    from KrakenOS.UI.nonseq_output_ports import beam_splitter_reflect_axis_frames
    if beam_splitter_reflect_axis_frames([]) != []:
        failures.append("NO-BS: no promoted BS must yield no reflect frames")
    else:
        notes.append("no-bs = a scene without a promoted BS emits no reflect axis")


def _check_mechanism(failures, notes):
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    guide = inspect.getsource(Kraken3DInspector._bs_reflect_axis_guide_records)
    if "beam_splitter_reflect_axis_frames" not in guide or "axis:global:split" not in guide:
        failures.append("MECHANISM: _bs_reflect_axis_guide_records must use beam_splitter_reflect_axis_frames + emit axis:global:split")
    assembler = inspect.getsource(Kraken3DInspector._optical_axis_records_for_3d)
    if "self._bs_reflect_axis_guide_records(bounds)" not in assembler:
        failures.append("MECHANISM: _optical_axis_records_for_3d must append the BS reflect guides")
    # bugs/0428: gate on the UNFOLDED case -- a mirror-folded incoming would draw the +Z-assumption axis
    # wrong (flag_20260723_151839 "RA mirror axis goes haywire"). The BS axis draws once the RA mirror is
    # removed (incoming becomes +Z); folded incoming is Phase 2.
    if "if not scene_is_folded:" not in assembler:
        failures.append("MECHANISM: the BS reflect guides must be gated on the unfolded (+Z incoming) case")
    if not [f for f in failures if f.startswith("MECHANISM")]:
        notes.append("mechanism = the assembler appends the BS reflect guide(s) only when incoming is straight +Z")


def _check_placement_unchanged(failures, notes):
    from KrakenOS.UI.nonseq_output_ports import build_optical_solid_output_port_pose_overrides
    src = inspect.getsource(build_optical_solid_output_port_pose_overrides)
    # Phase 1 must NOT fold the chain onto the BS -- the follower builder still skips it.
    if "_row_is_marked_beam_splitter(current) or _solid_has_beam_splitter_interaction_face(world_faces)" not in src:
        failures.append("PLACEMENT-UNCHANGED: the follower builder must still skip the BS (Phase 1 is display-only)")
    else:
        notes.append("placement-unchanged = the follower builder still skips the BS (placement is Phase 2)")


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    for check in (_check_reflect_math, _check_no_bs, _check_mechanism, _check_placement_unchanged):
        try:
            check(failures, notes)
        except Exception as exc:
            failures.append(f"{check.__name__}: raised {type(exc).__name__}: {exc}")
    info = [n if "=" in n else n.replace(":", " =", 1) for n in notes]
    return (not failures), (failures + info)


def run() -> int:
    passed, notes = run_checks()
    print("=== validate_open3d_bs_reflect_axis (bugs/0428 Phase 1) ===")
    for note in notes:
        print(f"  {'ok ' if '=' in note else 'XX '} {note}")
    if not passed:
        n = len([x for x in notes if "=" not in x])
        print(f"\n{n} failure(s).")
        return 1
    print("\nAll BS-reflect-axis checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
