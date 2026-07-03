"""Display-free guard for bugs/0218 -- the incoming +Z optical-axis guide (``axis:global``)
must terminate EXACTLY at the promoted-mirror fold vertex, where the reflected/middle guide
begins, so the fold ELBOW sits on the mirror centre.

Background (flag_20260703_162409 "3 Optical Axis are there", follow-up observation): on the
two-mirror AZ85 the user saw the optical axis "not centered at the first RA mirror" -- every
other element (lenses, the 2nd RA mirror) shows the axis through its centre, only mirror-1's
fold corner looked offset. Cause: ``_optical_axis_records_for_3d`` clamped the incoming +Z
guide to ``fold_point_z + _AXIS_FOLD_POINT_GUIDE_MARGIN_MM`` (bugs/0189's anti-over-extension
allowance), so it ended at Z=76.9 -- ~5 mm PAST the 71.9 fold vertex the +X middle guide starts
from. Mirror-2's elbow (a clean vertex meet of middle->outgoing) had no such margin, so only
mirror-1 read as off-centre. ``_folded_axis_incoming_fold_point_z()`` already returns the true
vertex (71.9); the fix drops the ``+margin`` so the incoming guide ends at the vertex and
incoming -> middle -> outgoing form one connected polyline through the mirror centres.

This guard is display-free (the 0216 record harness, rays OFF -- the recording state).
  (A) TWO-MIRROR: incoming ``axis:global`` END coincides with the middle
      ``axis:global:reflected:1`` START at the fold vertex (gap < 0.05 mm), both at (0,0,~71.9),
      and the incoming guide rises +Z from below to reach it.
  (B) SINGLE-MIRROR: incoming END coincides with the outgoing ``axis:global:reflected`` START
      (gap < 0.05 mm) -- the same clean elbow, no ``:1`` middle.
  (C) CAUSAL: the OLD ``fold_point_z + _AXIS_FOLD_POINT_GUIDE_MARGIN_MM`` clamp would have ended
      the incoming guide ~5 mm (== the margin) PAST the vertex -- the exact off-centre poke.
  (D) WIRED: the production clamp is ``min(z1, float(fold_point_z))`` with the ``+margin`` gone.

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_incoming_axis_meets_fold_vertex
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from KrakenOS.UI.open3d_inspector import (
    _AXIS_FOLD_POINT_GUIDE_MARGIN_MM,
    Kraken3DInspector,
)
from KrakenOS.UI.validate_open3d_multifold_reflected_axis_segments import _by_id, _records, _seg
from KrakenOS.UI.validate_open3d_second_mirror_incoming_axis_placement import (
    _build_single_mirror,
    _build_two_mirror,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_INSPECTOR_SRC = PROJECT_ROOT / "KrakenOS" / "UI" / "open3d_inspector.py"

_Z_HAT = np.asarray((0.0, 0.0, 1.0))
_TOL = 0.05  # mm -- the two axes must meet at the vertex


@dataclass
class Check:
    check: str
    ok: bool
    detail: str


def validate_incoming_axis_meets_fold_vertex() -> list[Check]:
    checks: list[Check] = []

    # ===================== (A) TWO-MIRROR: incoming meets the +X middle ============== #
    editor2, bundle2 = _build_two_mirror()
    insp2, recs2 = _records(editor2, bundle2, show_rays=False)  # recording state: rays OFF
    vertex_z = float(Kraken3DInspector._folded_axis_incoming_fold_point_z(insp2))

    incoming2 = _by_id(recs2, "axis:global")
    middle2 = _by_id(recs2, "axis:global:reflected:1")

    two_ok = False
    two_detail = "axis:global or axis:global:reflected:1 absent"
    if incoming2 is not None and middle2 is not None:
        i_s, i_e, i_d, _iL = _seg(incoming2)
        m_s = _seg(middle2)[0]
        gap = float(np.linalg.norm(i_e - m_s))
        two_ok = (
            gap < _TOL                                             # incoming END == middle START
            and abs(float(i_e[2]) - vertex_z) < _TOL              # ... at the fold vertex Z
            and abs(float(i_e[0])) < _TOL and abs(float(i_e[1])) < _TOL  # on the +Z axis (x=y=0)
            and float(i_d @ _Z_HAT) > 0.99                        # incoming rises +Z
            and float(i_s[2]) < vertex_z - 20.0                   # ... from below the mirror
        )
        two_detail = (
            f"incoming END=({i_e[0]:.3f},{i_e[1]:.3f},{i_e[2]:.3f}) middle START=({m_s[0]:.3f},{m_s[1]:.3f},{m_s[2]:.3f}) "
            f"gap={gap*1000:.1f}um vertexZ={vertex_z:.3f} incoming.dirZ={float(i_d @ _Z_HAT):+.2f} "
            f"(expect gap<{_TOL}mm, END at the vertex, +Z from below)"
        )
    checks.append(Check(
        "two-mirror incoming axis:global ends AT the fold vertex where the +X middle begins (clean elbow)",
        two_ok, two_detail,
    ))

    # ===================== (B) SINGLE-MIRROR: incoming meets the reflected leg ======= #
    editor1, bundle1 = _build_single_mirror()
    insp1, recs1 = _records(editor1, bundle1, show_rays=False)
    incoming1 = _by_id(recs1, "axis:global")
    outgoing1 = _by_id(recs1, "axis:global:reflected")
    middle1 = _by_id(recs1, "axis:global:reflected:1")

    one_ok = False
    one_detail = "axis:global or axis:global:reflected absent"
    if incoming1 is not None and outgoing1 is not None:
        i_e = _seg(incoming1)[1]
        o_s = _seg(outgoing1)[0]
        gap = float(np.linalg.norm(i_e - o_s))
        one_ok = gap < _TOL and abs(float(i_e[2]) - vertex_z) < _TOL and middle1 is None
        one_detail = (
            f"incoming END=({i_e[0]:.3f},{i_e[1]:.3f},{i_e[2]:.3f}) reflected START=({o_s[0]:.3f},{o_s[1]:.3f},{o_s[2]:.3f}) "
            f"gap={gap*1000:.1f}um has_:1={middle1 is not None} (expect gap<{_TOL}mm, no :1 middle)"
        )
    checks.append(Check(
        "single-mirror incoming axis:global ends AT the fold vertex where the reflected leg begins",
        one_ok, one_detail,
    ))

    # ===================== (C) CAUSAL: the old +margin poked 5 mm past ============== #
    # The bug was the incoming END sitting at fold_point_z + _AXIS_FOLD_POINT_GUIDE_MARGIN_MM.
    # Prove the fix ends at the vertex (not the old margined value), and that the margin is the
    # exact 5 mm offset the user saw -- so a revert to the +margin clamp fails this guard.
    causal = False
    causal_detail = "axis:global absent"
    if incoming2 is not None:
        i_e_z = float(_seg(incoming2)[1][2])
        old_end_z = vertex_z + float(_AXIS_FOLD_POINT_GUIDE_MARGIN_MM)
        causal = (
            abs(i_e_z - vertex_z) < _TOL                          # fixed: END at the vertex
            and abs(i_e_z - old_end_z) > float(_AXIS_FOLD_POINT_GUIDE_MARGIN_MM) - _TOL  # NOT the old margined end
            and float(_AXIS_FOLD_POINT_GUIDE_MARGIN_MM) > 1.0     # the margin is a real (visible) offset
        )
        causal_detail = (
            f"incoming END z={i_e_z:.3f} == vertex {vertex_z:.3f}; old clamp would be vertex+margin="
            f"{old_end_z:.3f} (margin={float(_AXIS_FOLD_POINT_GUIDE_MARGIN_MM):.1f}mm poke, now gone)"
        )
    checks.append(Check(
        "CAUSAL: incoming END is the vertex, not the old fold_point_z + _AXIS_FOLD_POINT_GUIDE_MARGIN_MM (5mm poke)",
        causal, causal_detail,
    ))

    # ===================== (D) WIRED ================================================ #
    try:
        src = _INSPECTOR_SRC.read_text(encoding="utf-8")
    except Exception:
        src = ""
    wired = (
        "z1 = min(z1, float(fold_point_z))" in src
        and "z1 = min(z1, float(fold_point_z) + _AXIS_FOLD_POINT_GUIDE_MARGIN_MM)" not in src
    )
    checks.append(Check(
        "the fix is wired: the incoming clamp is min(z1, float(fold_point_z)) with the +margin removed",
        wired,
        f"vertex_clamp={'z1 = min(z1, float(fold_point_z))' in src} "
        f"old_margined_clamp_gone={'z1 = min(z1, float(fold_point_z) + _AXIS_FOLD_POINT_GUIDE_MARGIN_MM)' not in src}",
    ))

    return checks


def run_checks() -> tuple[bool, list[str]]:
    """Penta-phase entry point: ``(passed, notes)`` where notes are the failures."""
    checks = validate_incoming_axis_meets_fold_vertex()
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


def main() -> int:
    checks = validate_incoming_axis_meets_fold_vertex()
    failed = [c for c in checks if not c.ok]
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if failed:
        raise SystemExit(1)
    print("Incoming-axis-meets-fold-vertex validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
