"""Display-free guard for bugs/0215 -- on a TWO-mirror fold the incoming +Z optical-axis
guide must clamp at the FIRST fold (the near mirror), not be flung far below the scene.

Background: a promoted full-mirror cube folds the downstream chain onto the reflected +X
branch (bugs/0185); ``_folded_axis_incoming_fold_point_z`` recovers the fold-plane Z by
applying each folded row's rigid fold transform to its straight +Z anchor. With ONE mirror
every folded row shares the SAME constant Z (the AZ85 RA mirror vertex, Z=+71.9), so the
choice of representative Z was irrelevant.

The bug (flag_20260703_150248_512, "the optical axis is away from the optical components"):
a SECOND promoted mirror re-folds the tail, so the rows no longer share one Z -- the fold-1
rows stay at Z=+71.9 but the twice-folded detector row lands at Z=-62 (0214's DOWN seat).
The old code returned ``min(fold_branch_zs)`` = -62 -- BELOW the object at Z=0 -- and clamped
the incoming +Z guide there, drawing the whole axis ~130 mm below the components that sit at
Z=+72. The incoming axis physically only reaches the FIRST fold, so the fix returns
``fold_branch_zs[0]`` (first fold in optical/row order), not the extremum.

This guard is display-free. It (A) builds the real two-mirror AZ85 scene and asserts the
incoming fold point is the first (positive, near-mirror) fold with a CAUSAL contrast that the
old ``min`` would have been the negative twice-folded detector Z, and that the drawn
``axis:global`` guide now reaches UP to the components; and (B) asserts a single-mirror AZ85
scene is byte-identical (all fold Zs equal, so first == min), so single-fold layouts are
untouched. (C) checks the fix is wired (returns the first fold, not ``min``).

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_second_mirror_incoming_axis_placement
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import io
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor, _trace
from KrakenOS.UI.validate_open3d_second_mirror_same_part_mirror_carryover import _promote_mirror2
from KrakenOS.UI.open3d_inspector import Kraken3DInspector

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_INSPECTOR_SRC = PROJECT_ROOT / "KrakenOS" / "UI" / "open3d_inspector.py"

# Mirror-1 (the near fold) vertex Z on the AZ85 RA mirror; the incoming axis must reach it.
_FIRST_FOLD_Z = 71.897
# The twice-folded detector Z on the two-mirror scene (0214's DOWN seat) -- the WRONG value the
# old ``min`` picked: below the object plane at Z=0.
_TWICE_FOLDED_DETECTOR_Z = -62.05


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


def _fold_branch_zs(editor) -> list[float]:
    """Replicate the fold-Z collection ``_folded_axis_incoming_fold_point_z`` walks, in row
    order, so the causal check can compare the FIRST fold against the ``min`` the bug used."""
    zs: list[float] = []
    z_positions = editor._row_z_positions()
    rows = getattr(editor, "rows", []) or []
    for row_index in range(len(rows)):
        try:
            transform = editor._optical_axis_fold_world_transform_for_row(row_index)
        except Exception:
            transform = None
        if transform is None or not (0 <= row_index < len(z_positions)):
            continue
        matrix = np.asarray(transform, dtype=float).reshape(4, 4)
        anchor = np.asarray((0.0, 0.0, float(z_positions[row_index]), 1.0), dtype=float)
        folded_center = (matrix @ anchor)[:3]
        if np.all(np.isfinite(folded_center)):
            zs.append(float(folded_center[2]))
    return zs


def _fake_inspector(editor, bundle):
    """A minimal ``Kraken3DInspector`` shell that ``_optical_axis_records_for_3d`` and
    ``_folded_axis_incoming_fold_point_z`` can run on, headless (mirrors the probe harness)."""
    rp = list(getattr(bundle, "ray_paths", []) or [])
    allpts = (
        np.concatenate(
            [
                np.asarray(getattr(p, "points_world", np.empty((0, 3))), dtype=float)
                for p in rp
                if getattr(p, "points_world", None) is not None
                and np.asarray(p.points_world).size
            ],
            axis=0,
        )
        if rp
        else np.zeros((1, 3))
    )

    class _R:
        def ComputeVisiblePropBounds(self_inner):
            return (
                float(allpts[:, 0].min()), float(allpts[:, 0].max()),
                float(allpts[:, 1].min()), float(allpts[:, 1].max()),
                float(allpts[:, 2].min()), float(allpts[:, 2].max()),
            )

    insp = object.__new__(Kraken3DInspector)
    insp.editor = editor
    insp._renderer = _R()
    insp.show_rays_var = _FakeBool(True)
    insp._cached_traced_axis_signature = None
    insp._cached_traced_axis_records = []
    return insp


def _incoming_global_record(records):
    for rec in records:
        if str(rec.get("axis_id")) == "axis:global":
            return rec
    return None


def _build_two_mirror():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor = _build_editor(_AZ85)
        _promote_mirror2(editor)
        _trace(editor)
        bundle = editor._build_scene_bundle(editor.last_system, editor.last_rays, 1.0)
    return editor, bundle


def _build_single_mirror():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor = _build_editor(_AZ85)
        _trace(editor)
        bundle = editor._build_scene_bundle(editor.last_system, editor.last_rays, 1.0)
    return editor, bundle


def validate_second_mirror_incoming_axis_placement() -> list[Check]:
    checks: list[Check] = []

    # ===================== (A) TWO-MIRROR: first fold, not the extremum ============= #
    editor2, bundle2 = _build_two_mirror()
    insp2 = _fake_inspector(editor2, bundle2)

    zs2 = _fold_branch_zs(editor2)
    first2 = zs2[0] if zs2 else None
    min2 = min(zs2) if zs2 else None
    fp2 = Kraken3DInspector._folded_axis_incoming_fold_point_z(insp2)

    # The fix returns the FIRST fold (near mirror, ABOVE the object), NOT the deepest.
    first_is_positive_near = (
        first2 is not None and first2 > 60.0 and abs(first2 - _FIRST_FOLD_Z) < 2.0
    )
    checks.append(Check(
        "two-mirror incoming fold point is the FIRST fold (near mirror ~+71.9, above the object)",
        first_is_positive_near and fp2 is not None and abs(float(fp2) - first2) < 1e-6,
        f"_folded_axis_incoming_fold_point_z={None if fp2 is None else round(float(fp2),3)} "
        f"fold_branch_zs[0]={None if first2 is None else round(first2,3)} "
        f"(expect ~{_FIRST_FOLD_Z}, and the fn returns [0])",
    ))

    # CAUSAL: the OLD ``min`` would be the twice-folded detector, BELOW the object -- proving
    # the extremum is exactly what dragged the guide away from the components.
    causal = (
        min2 is not None
        and min2 < -50.0
        and abs(min2 - _TWICE_FOLDED_DETECTOR_Z) < 3.0
        and first2 is not None
        and min2 < 0.0 < first2
        and abs(min2 - first2) > 100.0
    )
    checks.append(Check(
        "CAUSAL: the old min(fold_branch_zs) is the twice-folded detector ~-62 (below the object) -- the bug",
        causal,
        f"min={None if min2 is None else round(min2,3)} vs first={None if first2 is None else round(first2,3)} "
        f"(old min<0 dragged the guide ~{None if (min2 is None or first2 is None) else round(first2-min2,1)}mm below the components)",
    ))

    # The drawn incoming ``axis:global`` guide now REACHES UP to the components (its far end
    # is at the first fold ~+72), instead of being clamped down at the negative detector Z.
    records2 = Kraken3DInspector._optical_axis_records_for_3d(insp2, bundle2)
    glob = _incoming_global_record(records2)
    glob_pts = np.asarray(glob.get("points"), dtype=float) if glob else None
    reaches = (
        glob_pts is not None
        and glob_pts.size
        and float(glob_pts[:, 2].max()) > 60.0
    )
    checks.append(Check(
        "the drawn incoming 'axis:global' guide reaches UP to the components (far end near +72, not below)",
        bool(reaches),
        f"axis:global present={glob is not None} "
        f"z-endpoints={None if glob_pts is None else [round(float(z),1) for z in glob_pts[:,2]]} "
        f"(expect max-z > 60, i.e. up at mirror-1; bug clamped it to ~-57)",
    ))

    # ===================== (B) SINGLE-MIRROR: byte-identical ======================== #
    editor1, bundle1 = _build_single_mirror()
    insp1 = _fake_inspector(editor1, bundle1)
    zs1 = _fold_branch_zs(editor1)
    fp1 = Kraken3DInspector._folded_axis_incoming_fold_point_z(insp1)

    # One fold -> every folded row shares one constant Z, so first == min: the fix returns the
    # SAME value the old ``min`` did, and the single-mirror guide is left byte-identical.
    single_identical = (
        len(zs1) > 0
        and abs(min(zs1) - zs1[0]) < 1e-9
        and fp1 is not None
        and abs(float(fp1) - min(zs1)) < 1e-9
        and float(fp1) > 60.0
    )
    checks.append(Check(
        "single-mirror scene is byte-identical: all fold Zs equal, so first == min (fix leaves it unchanged)",
        single_identical,
        f"fold_branch_zs={[round(z,3) for z in zs1]} "
        f"first={None if not zs1 else round(zs1[0],3)} min={None if not zs1 else round(min(zs1),3)} "
        f"fn={None if fp1 is None else round(float(fp1),3)}",
    ))

    # ===================== (C) WIRED (returns first, not min) ======================= #
    try:
        src = _INSPECTOR_SRC.read_text(encoding="utf-8")
    except Exception:
        src = ""
    # Isolate the method body so the assertion is about THIS function.
    body = ""
    marker = "def _folded_axis_incoming_fold_point_z"
    if marker in src:
        after = src.split(marker, 1)[1]
        nxt = after.find("\n    def ")
        body = after if nxt < 0 else after[:nxt]
    wired = "return fold_branch_zs[0]" in body and "return min(fold_branch_zs)" not in body
    checks.append(Check(
        "the fix is wired: _folded_axis_incoming_fold_point_z returns fold_branch_zs[0], not min(...)",
        wired,
        f"returns_first={'return fold_branch_zs[0]' in body} "
        f"returns_min={'return min(fold_branch_zs)' in body}",
    ))

    return checks


def run_checks() -> tuple[bool, list[str]]:
    """Penta-phase entry point: ``(passed, notes)`` where notes are the failures."""
    checks = validate_second_mirror_incoming_axis_placement()
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


def main() -> int:
    checks = validate_second_mirror_incoming_axis_placement()
    failed = [c for c in checks if not c.ok]
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if failed:
        raise SystemExit(1)
    print("Second-mirror incoming optical-axis placement validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
