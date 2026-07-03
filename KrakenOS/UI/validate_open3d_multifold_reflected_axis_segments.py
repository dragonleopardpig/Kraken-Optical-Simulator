"""Display-free guard for bugs/0216 -- on a CHAIN of two promoted-mirror folds the reflected
optical axis must be drawn as THREE segments (incoming +Z, MIDDLE +X between the mirrors,
OUTGOING -Z down to the detector), not the single wrong DOWN line the old single-fold path
drew.

Background: ``axis:global`` covers only object -> mirror-1 (clamped at the first fold,
bugs/0215). With ONE mirror the outgoing leg is drawn by ``_folded_reflected_axis_guide_record``.
A SECOND promoted mirror re-folds the tail, but that method's ``Mirror``-surface fold count only
sees the SEQUENTIAL fold and under-counts the FREE-PLACED 2nd mirror, so it treated the scene as
single-fold and drew ONE segment along the twice-folded IMAGE direction -- straight DOWN from the
first fold, x pinned at 0. That is the flag_20260703_153616 report: "the 2nd optical axis
disappears after promotion, Optical Axis 3 is completely not visible."

The fix (``_folded_multifold_axis_guide_records`` + editor ``_promoted_mirror_fold_row_indices``)
reconstructs the folded axis POLYLINE: the promoted-mirror rows are the fold vertices; the
non-mirror rows between them lie on straight branches; consecutive branch lines intersect at the
clean fold vertices; the MIDDLE segments are bounded between two vertices and the OUTGOING segment
extends to the scene bounds. It reduces to the single-fold record for one mirror (byte-identical).

This guard is display-free. (A) On the two-mirror AZ85 scene with rays OFF (the recording state)
it asserts THREE ``dotted_global_guide`` axes with directions +Z / +X / -Z, the MIDDLE one turning
+X to mirror-2 and the OUTGOING one going -Z down toward the detector. (B) CAUSAL: the old
``_folded_reflected_axis_guide_record`` on the SAME scene returns ONE segment, dir -Z, with BOTH
endpoints at x~0 -- never the +X middle nor a distinct outgoing leg. (C) the single-mirror scene is
byte-identical (one ``axis:global:reflected``, no ``:1``, multi-fold returns []). (D) the fix is
wired.

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_multifold_reflected_axis_segments
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from KrakenOS.UI.open3d_inspector import Kraken3DInspector
from KrakenOS.UI.validate_open3d_second_mirror_incoming_axis_placement import (
    _build_single_mirror,
    _build_two_mirror,
    _fake_inspector,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_INSPECTOR_SRC = PROJECT_ROOT / "KrakenOS" / "UI" / "open3d_inspector.py"

_X_HAT = np.asarray((1.0, 0.0, 0.0))
_Z_HAT = np.asarray((0.0, 0.0, 1.0))


@dataclass
class Check:
    check: str
    ok: bool
    detail: str


class _FakeBool:
    def __init__(self, v):
        self._v = bool(v)

    def get(self):
        return self._v


def _records(editor, bundle, show_rays):
    insp = _fake_inspector(editor, bundle)
    insp.show_rays_var = _FakeBool(show_rays)
    return insp, Kraken3DInspector._optical_axis_records_for_3d(insp, bundle)


def _by_id(records, axis_id):
    for rec in records:
        if str(rec.get("axis_id")) == axis_id:
            return rec
    return None


def _seg(rec):
    pts = np.asarray(rec.get("points"), dtype=float).reshape(-1, 3)
    d = pts[-1] - pts[0]
    n = float(np.linalg.norm(d))
    return pts[0], pts[-1], (d / n if n > 1e-9 else d), n


def validate_multifold_reflected_axis_segments() -> list[Check]:
    checks: list[Check] = []

    # ===================== (A) TWO-MIRROR: three axis segments ====================== #
    editor2, bundle2 = _build_two_mirror()
    _insp2, recs2 = _records(editor2, bundle2, show_rays=False)  # recording state: rays OFF
    guides = [r for r in recs2 if str(r.get("axis_kind")) == "dotted_global_guide"]

    # Exactly three dotted optical-axis guides (the three folds' straight runs), rays OFF.
    checks.append(Check(
        "two-mirror draws THREE optical-axis guides with rays OFF (incoming + middle + outgoing)",
        len(guides) == 3,
        f"dotted_global_guide count={len(guides)} ids={[str(r.get('axis_id')) for r in guides]} (expect 3)",
    ))

    incoming = _by_id(recs2, "axis:global")
    middle = _by_id(recs2, "axis:global:reflected:1")
    outgoing = _by_id(recs2, "axis:global:reflected")

    # MIDDLE (axis 2): starts at the first fold (x~0, z~+72), runs +X toward mirror-2.
    mid_ok = False
    mid_detail = "axis:global:reflected:1 absent"
    if middle is not None:
        s, e, d, L = _seg(middle)
        mid_ok = (
            abs(float(s[0])) < 5.0 and float(s[2]) > 60.0            # starts at the first fold
            and abs(float(d @ _X_HAT)) > 0.99                        # runs along +/-X
            and float(e[0]) > 100.0 and L > 50.0                     # reaches out to mirror-2
        )
        mid_detail = (
            f"start=({s[0]:.1f},{s[1]:.1f},{s[2]:.1f}) end=({e[0]:.1f},{e[1]:.1f},{e[2]:.1f}) "
            f"dir.x={float(d @ _X_HAT):+.2f} len={L:.1f} (expect start x~0 z>60, dir~+X, end x>100)"
        )
    checks.append(Check(
        "MIDDLE axis (axis:global:reflected:1) turns +X from the first fold to mirror-2 -- axis 2 restored",
        mid_ok, mid_detail,
    ))

    # OUTGOING (axis 3): starts at the second fold (x>100, z~+72), goes -Z down to the detector.
    out_ok = False
    out_detail = "axis:global:reflected absent"
    if outgoing is not None:
        s, e, d, L = _seg(outgoing)
        out_ok = (
            float(s[0]) > 100.0 and float(s[2]) > 60.0               # starts at the 2nd fold
            and float(d @ _Z_HAT) < -0.99                            # goes -Z (down)
            and float(e[2]) < float(s[2]) - 20.0                     # descends toward the detector
        )
        out_detail = (
            f"start=({s[0]:.1f},{s[1]:.1f},{s[2]:.1f}) end=({e[0]:.1f},{e[1]:.1f},{e[2]:.1f}) "
            f"dir.z={float(d @ _Z_HAT):+.2f} len={L:.1f} (expect start x>100 z>60, dir~-Z, end z<start)"
        )
    checks.append(Check(
        "OUTGOING axis (axis:global:reflected) goes -Z from the 2nd fold down toward the detector -- axis 3 restored",
        out_ok, out_detail,
    ))

    # Incoming axis:global still points +Z and reaches up to the first fold (carries bugs/0215).
    in_ok = False
    in_detail = "axis:global absent"
    if incoming is not None:
        s, e, d, L = _seg(incoming)
        top = max(float(s[2]), float(e[2]))
        in_ok = abs(float(d @ _Z_HAT)) > 0.99 and top > 60.0
        in_detail = f"dir.z={float(d @ _Z_HAT):+.2f} max-z={top:.1f} (expect ~+Z, reaches up > 60)"
    checks.append(Check(
        "incoming axis:global still runs +Z up to the first fold (bugs/0215 preserved)",
        in_ok, in_detail,
    ))

    # ===================== (B) CAUSAL: old single-fold = one DOWN line =============== #
    insp_c = _fake_inspector(editor2, bundle2)
    bounds_c = insp_c._augment_bounds_with_scene_overlays(
        np.asarray(insp_c._renderer.ComputeVisiblePropBounds(), dtype=float), bundle2
    )
    fp = Kraken3DInspector._folded_axis_incoming_fold_point_z(insp_c)
    old_rec = Kraken3DInspector._folded_reflected_axis_guide_record(insp_c, bounds_c, float(fp))
    causal = False
    causal_detail = "old method returned None"
    if old_rec is not None:
        s, e, d, L = _seg(old_rec)
        # the bug: ONE segment, dir -Z, x pinned at ~0 the whole way (never turns +X to mirror-2).
        causal = (
            float(d @ _Z_HAT) < -0.99
            and abs(float(s[0])) < 5.0 and abs(float(e[0])) < 5.0
        )
        causal_detail = (
            f"old start=({s[0]:.1f},{s[1]:.1f},{s[2]:.1f}) end=({e[0]:.1f},{e[1]:.1f},{e[2]:.1f}) "
            f"dir.z={float(d @ _Z_HAT):+.2f} -- ONE down line, x~0 throughout (no +X middle, no distinct outgoing)"
        )
    checks.append(Check(
        "CAUSAL: old _folded_reflected_axis_guide_record drew ONE -Z line with x~0 (axis 2 gone, axis 3 the wrong dir)",
        causal, causal_detail,
    ))

    # Two-mirror fold count is 2 (the fix's reliable predicate), where the old Mirror-surface count was 1.
    n_mirrors2 = len(editor2._promoted_mirror_fold_row_indices())
    checks.append(Check(
        "two-mirror _promoted_mirror_fold_row_indices counts BOTH folds (2), not the under-counted 1",
        n_mirrors2 == 2,
        f"_promoted_mirror_fold_row_indices()={editor2._promoted_mirror_fold_row_indices()} (expect 2)",
    ))

    # ===================== (C) SINGLE-MIRROR: byte-identical ======================== #
    editor1, bundle1 = _build_single_mirror()
    insp1, recs1 = _records(editor1, bundle1, show_rays=False)
    n_mirrors1 = len(editor1._promoted_mirror_fold_row_indices())
    single_reflected = _by_id(recs1, "axis:global:reflected")
    single_middle = _by_id(recs1, "axis:global:reflected:1")
    # The multi-fold path must be inert for one fold (returns []), so the single-fold record stands.
    multifold_empty = (
        Kraken3DInspector._folded_multifold_axis_guide_records(insp1, insp1._renderer.ComputeVisiblePropBounds(), float(fp))
        == []
    )
    single_ok = (
        n_mirrors1 == 1
        and single_reflected is not None
        and single_middle is None
        and multifold_empty
    )
    checks.append(Check(
        "single-mirror is byte-identical: one axis:global:reflected, NO :1 middle, multi-fold path returns []",
        single_ok,
        f"folds={n_mirrors1} has_reflected={single_reflected is not None} "
        f"has_:1={single_middle is not None} multifold_empty={multifold_empty}",
    ))

    # ===================== (D) WIRED ================================================ #
    try:
        src = _INSPECTOR_SRC.read_text(encoding="utf-8")
    except Exception:
        src = ""
    wired = (
        "_folded_multifold_axis_guide_records" in src
        and "self._folded_multifold_axis_guide_records(bounds, float(fold_point_z))" in src
        and "def _promoted_mirror_fold_row_indices" not in src  # lives on the editor mixin, not here
    )
    checks.append(Check(
        "the fix is wired: _optical_axis_records_for_3d routes to _folded_multifold_axis_guide_records",
        wired,
        f"builder_defined={'def _folded_multifold_axis_guide_records' in src} "
        f"routed={'self._folded_multifold_axis_guide_records(bounds, float(fold_point_z))' in src}",
    ))

    return checks


def run_checks() -> tuple[bool, list[str]]:
    """Penta-phase entry point: ``(passed, notes)`` where notes are the failures."""
    checks = validate_multifold_reflected_axis_segments()
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


def main() -> int:
    checks = validate_multifold_reflected_axis_segments()
    failed = [c for c in checks if not c.ok]
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if failed:
        raise SystemExit(1)
    print("Multi-fold reflected optical-axis segments validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
