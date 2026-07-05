"""Display-free guard for bugs/0230 -- a PERISCOPE (two adjacent promoted RA mirrors, e.g. the
Pyrite-85 scene) must not crash the folded trace with `non-sequential surface N: int has no
ray_trace or extract_surface method`.

Root cause: two adjacent 90-degree folds compose to a NET-IDENTITY rotation with a lateral
OFFSET (periscope). The general flat-plate straight-equivalent path
(`_folded_optical_solid_straight_equivalent_rows`, bugs/0208) was gated by `has_rotating_fold`,
which only recognised a non-identity ROTATION, so it read the periscope as unfolded and returned
None. The scene fell through to the single-fold sequential-Mirror surrogate, which cannot compose
the 2nd free-placed fold (it rotation-folds the running beam the wrong way) and left the 2nd
mirror as a promoted mesh solid -- fed into a build=0 (dummy, EEE = int 0s) trace system, whose
non-sequential intersection of that solid read an int -> crash.

Fix: the gate now treats a DISPLACING fold (identity rotation + non-zero translation) as a fold
too, so the periscope routes to the flat-plate equivalent (both mirrors flattened, build=0, no
mesh solid, no crash).

  (A) GATE RECOGNISES A PERISCOPE: with a promoted-solid row and a periscope fold transform
      (identity rotation + lateral offset) the straight-equivalent builder returns rows
      (non-None); the OLD rotation-only gate would have returned None.
  (B) GATE STILL REJECTS A NO-OP: an identity transform with ZERO translation (no real fold)
      still returns None -- unfolded scenes stay untouched.
  (C) AZ85 ROTATING FOLD UNCHANGED: the two-mirror AZ85 still yields flat-plate equivalent rows
      and its preview still folds to the known detector (no regression from the gate change).
  (D) WIRED: the `displacing` translation branch is present in source.

This guard does NOT assert the periscope's detector/ray branch ALIGNMENT -- that (the
pose-override fold-sign follow-up) is tracked separately in bugs/0230 "Remaining"; here we pin
only that the crash is gone and AZ85 is preserved.

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_periscope_fold_crash
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import io
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

import KrakenOS.UI.validate_open3d_second_mirror_same_part_mirror_carryover as carryover
from KrakenOS.UI.surface_table_model import SurfaceRow
from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_PARAXIAL_SRC = PROJECT_ROOT / "KrakenOS" / "UI" / "services" / "paraxial_tools.py"

# The two-mirror AZ85 (carryover._promote_mirror2) folds to this detector (the bugs/0224
# _KNOWN_FOLDED_DETECTOR); the gate change must leave it byte-identical.
_KNOWN_AZ85_DETECTOR = np.asarray((181.374, 0.0, -13.552), dtype=float)


@dataclass
class Check:
    check: str
    ok: bool
    detail: str


def _quiet(fn, *args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        return fn(*args, **kwargs)


def _periscope_transform(row_index):
    """A periscope pose override: NET-IDENTITY rotation with a lateral +Y offset (the two
    adjacent 90-degree folds carry the downstream rows onto the parallel branch without
    rotating them). Applies from the second mirror onward."""
    if row_index is None or int(row_index) < 2:
        return None
    transform = np.eye(4, dtype=float)
    transform[:3, 3] = np.asarray((0.0, 188.0, 0.0), dtype=float)  # identity R, lateral offset
    return transform


def _identity_transform(row_index):
    """A no-op override: identity rotation AND zero translation -- not a real fold."""
    if row_index is None or int(row_index) < 2:
        return None
    return np.eye(4, dtype=float)


def _detector(bundle):
    for target in getattr(bundle, "targets", []) or []:
        if getattr(target, "is_detector", False):
            return np.asarray(target.center_world, dtype=float).reshape(3)
    return None


def validate_periscope_fold_crash() -> list[Check]:
    checks: list[Check] = []

    # Build a two-mirror AZ85 -- a real folded editor with promoted optical-solid rows -- then
    # drive the gate through its OWN `_optical_axis_fold_world_transform_for_row` by swapping in
    # a periscope / no-op transform. This isolates the gate change (bugs/0230) without needing
    # the gitignored Pyrite STL fixtures.
    editor = _quiet(_build_editor, _AZ85)
    _quiet(carryover._promote_mirror2, editor)
    original_fold = editor._optical_axis_fold_world_transform_for_row

    # ---- (A) periscope (identity R + lateral offset) is recognised as a fold --------------- #
    try:
        editor._optical_axis_fold_world_transform_for_row = _periscope_transform
        periscope_rows = _quiet(editor._folded_optical_solid_straight_equivalent_rows)
    finally:
        editor._optical_axis_fold_world_transform_for_row = original_fold
    checks.append(Check(
        "GATE recognises a periscope (identity rotation + lateral offset) as a fold",
        periscope_rows is not None and len(periscope_rows) == len(editor.rows),
        f"straight-equivalent rows={None if periscope_rows is None else len(periscope_rows)} "
        f"(expect {len(editor.rows)}; the old rotation-only gate returned None here -> crash)",
    ))

    # ---- (B) a true no-op (identity, zero translation) is still NOT a fold ------------------ #
    try:
        editor._optical_axis_fold_world_transform_for_row = _identity_transform
        noop_rows = _quiet(editor._folded_optical_solid_straight_equivalent_rows)
    finally:
        editor._optical_axis_fold_world_transform_for_row = original_fold
    checks.append(Check(
        "GATE still rejects a no-op transform (identity rotation, zero translation)",
        noop_rows is None,
        f"straight-equivalent rows={None if noop_rows is None else len(noop_rows)} "
        f"(expect None; a zero-displacement identity is not a real fold)",
    ))

    # ---- (C) the real AZ85 rotating fold is unchanged (no regression) ----------------------- #
    az_rows = _quiet(editor._folded_optical_solid_straight_equivalent_rows)
    checks.append(Check(
        "AZ85 rotating fold still yields flat-plate equivalent rows (unchanged)",
        az_rows is not None and len(az_rows) == len(editor.rows),
        f"equivalent rows={None if az_rows is None else len(az_rows)}",
    ))
    _s, _r, bundle = _quiet(editor._build_preview_system_rays_bundle, update_state=True)
    det = _detector(bundle)
    checks.append(Check(
        "AZ85 two-mirror preview still folds to its known detector (gate change is inert here)",
        det is not None and bool(np.allclose(det, _KNOWN_AZ85_DETECTOR, atol=0.5))
        and len(getattr(bundle, "ray_paths", []) or []) > 0,
        f"detector={None if det is None else np.round(det, 2)} "
        f"(expect ~{np.round(_KNOWN_AZ85_DETECTOR, 1)}) rays={len(getattr(bundle, 'ray_paths', []) or [])}",
    ))

    # ---- (D) wiring ------------------------------------------------------------------------- #
    try:
        src = _PARAXIAL_SRC.read_text(encoding="utf-8")
    except Exception:
        src = ""
    wired = (
        "bugs/0230" in src
        and "displacing" in src
        and "np.linalg.norm(translation)" in src
    )
    checks.append(Check(
        "the translating-fold (periscope) branch is wired in the straight-equivalent gate",
        wired,
        f"bugs/0230={'bugs/0230' in src} displacing={'displacing' in src}",
    ))
    return checks


def run_checks() -> "tuple[bool, list[str]]":
    checks = validate_periscope_fold_crash()
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


def main() -> int:
    checks = validate_periscope_fold_crash()
    failed = [c for c in checks if not c.ok]
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if failed:
        raise SystemExit(1)
    print("Periscope-fold-crash validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
