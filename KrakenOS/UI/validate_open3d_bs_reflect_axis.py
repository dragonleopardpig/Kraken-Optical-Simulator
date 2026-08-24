"""Guard: a beam splitter draws its REFLECT-branch optical axis, fold-aware (bugs/0428 Phase 1 + follow-up).

Flag flag_20260723_141437 ("No second optical axis is created for the BS plate"): a promoted BS transmits
straight (``axis:global``) but the reflected branch had no optical-axis guide. Phase 1 draws it:
``beam_splitter_coating_world_frames`` returns each BS's coating (centroid, normal) in world coords, and
``_bs_reflect_axis_guide_records`` reflects the INCOMING leg off that coating to emit an ``axis:global:split``
guide reaching to the scene extent.

FOLD-AWARE (flag_20260723_155614 "no optical axis generated from BS plate" on a mirror-folded scene): the
incoming to each BS is the axis segment its coating SITS ON -- found by ``_incoming_axis_leg_for_point`` over
the already-assembled axis records. A BS before any fold reads the object leg (+Z); a BS downstream of an RA
mirror reads the folded leg direction. This replaces the earlier scene-wide ``not scene_is_folded`` gate that
suppressed the axis whenever ANY mirror was present.

DISPLAY ONLY: the follower placement still skips the BS (bugs/0396-0399) -- this only adds the second axis
line, it does not re-aim anything. Placement is Phase 2.

Checks
------
* REFLECT-MATH -- specular reflection ``d - 2(d.n)n`` off a 45-deg coating is symmetric: +Z -> +X AND the
  folded +X incoming -> +Z (so a folded-incoming BS reflects correctly).
* FOLD-AWARE   -- ``_incoming_axis_leg_for_point`` returns the NEAREST axis segment's direction: a BS on the
  object leg reads +Z, a BS on a folded leg reads the folded +X (what the old gate wrongly suppressed).
* NO-BS        -- ``beam_splitter_coating_world_frames`` returns ``[]`` when there is no promoted BS.
* MECHANISM    -- ``_bs_reflect_axis_guide_records`` uses ``beam_splitter_coating_world_frames`` +
  ``_incoming_axis_leg_for_point`` and emits ``axis:global:split``; ``_optical_axis_records_for_3d`` calls it
  with the assembled records and is NOT gated on ``scene_is_folded``.
* PLACEMENT-UNCHANGED -- the follower builder still skips the BS (display-only).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_bs_reflect_axis

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect

import numpy as np


def _reflect(incoming, normal):
    """Specular reflection ``d - 2(d.n)n`` (the per-BS reflect math)."""
    n = np.asarray(normal, dtype=float) / np.linalg.norm(normal)
    d = np.asarray(incoming, dtype=float)
    reflected = d - 2.0 * float(np.dot(d, n)) * n
    return reflected / np.linalg.norm(reflected)


def _check_reflect_math(failures, notes):
    # a 45-deg coating whose normal bisects +Z and -X: +Z reflects to +X, and (symmetrically) the folded
    # +X incoming reflects back to +Z -- so a BS on a folded leg reflects correctly, not just +Z incoming.
    normal = (-1.0, 0.0, 1.0)
    if not np.allclose(_reflect((0.0, 0.0, 1.0), normal), (1.0, 0.0, 0.0), atol=1e-9):
        failures.append(f"REFLECT-MATH: +Z off a 45-deg coating must reflect to +X (got {_reflect((0.0,0.0,1.0),normal).round(3)})")
    if not np.allclose(_reflect((1.0, 0.0, 0.0), normal), (0.0, 0.0, 1.0), atol=1e-9):
        failures.append(f"REFLECT-MATH: folded +X incoming off the same coating must reflect to +Z (got {_reflect((1.0,0.0,0.0),normal).round(3)})")
    if not [f for f in failures if f.startswith("REFLECT-MATH")]:
        notes.append("reflect-math = specular d-2(d.n)n is symmetric (+Z<->+X off a 45-deg coating)")


def _check_fold_aware(failures, notes):
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    pick = Kraken3DInspector._incoming_axis_leg_for_point
    axis_records = [
        {"points": np.array([(0.0, 0.0, 0.0), (0.0, 0.0, 100.0)])},      # object leg +Z
        {"points": np.array([(0.0, 0.0, 100.0), (100.0, 0.0, 100.0)])},  # folded leg +X
    ]
    _, d_obj = pick((0.0, 0.0, 40.0), axis_records)
    if d_obj is None or not np.allclose(d_obj, (0.0, 0.0, 1.0), atol=1e-9):
        failures.append(f"FOLD-AWARE: a BS on the object leg must read incoming +Z (got {None if d_obj is None else d_obj.round(3)})")
    _, d_fold = pick((60.0, 0.0, 100.0), axis_records)  # this is what the old scene_is_folded gate suppressed
    if d_fold is None or not np.allclose(d_fold, (1.0, 0.0, 0.0), atol=1e-9):
        failures.append(f"FOLD-AWARE: a BS on a folded leg must read the folded incoming +X (got {None if d_fold is None else d_fold.round(3)})")
    if not [f for f in failures if f.startswith("FOLD-AWARE")]:
        notes.append("fold-aware = incoming leg is the nearest axis segment (object leg -> +Z, folded leg -> +X)")


def _check_no_bs(failures, notes):
    from KrakenOS.UI.nonseq_output_ports import beam_splitter_coating_world_frames
    if beam_splitter_coating_world_frames([]) != []:
        failures.append("NO-BS: no promoted BS must yield no coating frames")
    else:
        notes.append("no-bs = a scene without a promoted BS emits no reflect axis")


def _check_mechanism(failures, notes):
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    guide = inspect.getsource(Kraken3DInspector._bs_reflect_axis_guide_records)
    # bugs/0643: the drawer now takes the EXTENT-carrying source (beam_splitter_coating_world_records,
    # which beam_splitter_coating_world_frames wraps) so it can bound the fold point to the real
    # coating face. Either name satisfies the contract: coating geometry from nonseq_output_ports.
    if ("beam_splitter_coating_world_records" not in guide and "beam_splitter_coating_world_frames" not in guide) or "axis:global:split" not in guide:
        failures.append("MECHANISM: _bs_reflect_axis_guide_records must use the BS coating world geometry + emit axis:global:split")
    if "_incoming_axis_leg_for_point" not in guide:
        failures.append("MECHANISM: _bs_reflect_axis_guide_records must derive the incoming from the nearest axis leg")
    assembler = inspect.getsource(Kraken3DInspector._optical_axis_records_for_3d)
    if "self._bs_reflect_axis_guide_records(bounds, list(records))" not in assembler:
        failures.append("MECHANISM: _optical_axis_records_for_3d must append the BS reflect guides with the assembled records")
    # fold-aware: the axis must NOT be gated on scene_is_folded any more (that suppressed it on a folded scene)
    if "if not scene_is_folded:\n            records.extend(self._bs_reflect_axis_guide_records" in assembler:
        failures.append("MECHANISM: the BS reflect guides must NOT be gated on scene_is_folded (fold-aware now)")
    if not [f for f in failures if f.startswith("MECHANISM")]:
        notes.append("mechanism = the assembler appends the fold-aware BS reflect guide(s) unconditionally")


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
    for check in (_check_reflect_math, _check_fold_aware, _check_no_bs, _check_mechanism, _check_placement_unchanged):
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
