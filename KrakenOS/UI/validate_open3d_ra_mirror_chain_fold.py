"""Display-free guard for bugs/0208: the folded display rays fold correctly through an
ARBITRARY CHAIN of promoted-mirror cubes, not just a single fold.

The user's AZ85 has one RA-mirror between object and lens; adding a SECOND between lens and
camera used to drop the display off the cone-preserving reflection path
(`_reflect_straight_equivalent_display_rays` bailed at `len(records)!=1`) onto the older
sequential-Mirror trace, whose leg-2 rays sit ~desp_z off the drawn lenses (the 0207 gap
resurfacing). bugs/0208 generalises the reflection to reflect each straight ray about EVERY
mirror plane in reverse station order (R1(R2(...Rk(v)))), so the rays fold at every mirror and
each leg lands on the drawn chain.

Asserts (display-free), on a 2-mirror AZ85 variant (a second promoted mirror inserted on the
+X leg) AND the stock single-fold AZ85:
  1. general fold detection: the 2-mirror scene yields 2 fold records, the 1-mirror scene 1;
  2. the display rays take the cone-preserving REFLECTION path (tagged
     `folded_straight_equivalent_reflected`) for BOTH -- the chain no longer falls back;
  3. the on-axis ray folds ONCE (1 mirror) / TWICE (2 mirrors) -- one ~90 deg kink per mirror;
  4. on the shared +X leg the on-axis ray's vertices coincide with the drawn lens-row X's
     (rays == CAD on that leg -- the 0207 consistency, preserved through the second fold);
  5. the incoming leg stays a 2D disk (cone, not a flat fan) for the chain -- s2 substantial;
  6. backward-compat: the single-fold AZ85 still lands the on-axis focus on its drawn detector
     (gap < 0.05 mm).

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_ra_mirror_chain_fold
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import io
import sys
from dataclasses import asdict

import numpy as np

from KrakenOS.UI.layout_editor import SurfaceRow
from KrakenOS.UI.services.folded_sequential_fold import fold_promoted_mirror_specs_to_sequential
from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor

_AXIS_Z = 71.897137


def _two_mirror_editor():
    editor = _build_editor(_AZ85)
    rows = list(editor.rows)
    mirror2 = SurfaceRow(**asdict(rows[1]))
    mirror2.name = "Promoted OPTICAL STEP optical solid (2nd fold)"
    rows[7].thickness = 90.0
    mirror2.thickness = 60.0
    editor.rows = rows[:8] + [mirror2] + [rows[8]]
    editor._normalize_special_rows()
    return editor


def _onaxis(bundle):
    out = []
    for p in (getattr(bundle, "ray_paths", None) or []):
        pw = np.asarray(getattr(p, "points_world", None), dtype=float)
        if pw.ndim == 2 and pw.shape[0] >= 2 and pw.shape[1] >= 3 and float(np.linalg.norm(pw[0][:3])) <= 1.0:
            out.append(pw)
    return out


def _sharp_kinks(path: np.ndarray, cos_max: float = 0.2) -> int:
    seg = np.diff(path[:, :3], axis=0)
    ln = np.linalg.norm(seg, axis=1)
    ok = ln > 1e-6
    if int(ok.sum()) < 2:
        return 0
    u = np.zeros_like(seg)
    u[ok] = seg[ok] / ln[ok, None]
    cos_turn = np.sum(u[:-1] * u[1:], axis=1)
    return int(np.sum(cos_turn < cos_max))


def _second_singular(coords2d: np.ndarray) -> float:
    a = np.asarray(coords2d, dtype=float)
    if a.ndim != 2 or a.shape[0] < 3 or a.shape[1] != 2:
        return 0.0
    c = a - a.mean(0)
    s = np.linalg.svd(c, compute_uv=False)
    return float(s[1]) if s.size >= 2 else 0.0


def _tag(bundle) -> str:
    for p in (getattr(bundle, "ray_paths", None) or []):
        src = str(getattr(p, "display_geometry_source", "") or "")
        if src:
            return src
    return ""


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []
    notes: list[str] = []
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            # ---- two-mirror chain ----
            ed2 = _two_mirror_editor()
            specs2 = ed2._serializable_specs_for_rows(list(ed2.rows))
            _o2, recs2 = fold_promoted_mirror_specs_to_sequential(specs2)
            sys2, _r2, b2 = ed2._build_preview_system_rays_bundle(update_state=True)
            oa2 = _onaxis(b2)
            tag2 = _tag(b2)
            # drawn lens-row X on the +X leg (rows 2..7, before the 2nd mirror at row 8)
            lens_x = sorted(
                float(np.asarray(ed2._surface_reference_world_point(i, system=sys2), float).reshape(3)[0])
                for i in range(2, 8)
            )

            # ---- single-fold AZ85 ----
            ed1 = _build_editor(_AZ85)
            specs1 = ed1._serializable_specs_for_rows(list(ed1.rows))
            _o1, recs1 = fold_promoted_mirror_specs_to_sequential(specs1)
            sys1, _r1, b1 = ed1._build_preview_system_rays_bundle(update_state=True)
            oa1 = _onaxis(b1)
            tag1 = _tag(b1)
            drawn_det1 = float(
                np.asarray(ed1._surface_reference_world_point(len(ed1.rows) - 1, system=sys1), float).reshape(3)[0]
            )
    except Exception as exc:  # noqa: BLE001
        return False, [f"setup raised {exc!r}"]

    # (1) general fold detection
    if len(recs2) != 2:
        failures.append(f"2-mirror scene produced {len(recs2)} fold records (expected 2)")
    if len(recs1) != 1:
        failures.append(f"1-mirror scene produced {len(recs1)} fold records (expected 1)")

    # (2) both take the reflection path
    if tag2 != "folded_straight_equivalent_reflected":
        failures.append(f"2-mirror rays not on the reflection path (tag={tag2!r}) -- chain fell back")
    if tag1 != "folded_straight_equivalent_reflected":
        failures.append(f"1-mirror rays not on the reflection path (tag={tag1!r})")

    # (3) one ~90 deg kink per mirror
    if not oa2:
        failures.append("2-mirror scene: no on-axis rays")
    else:
        k2 = _sharp_kinks(oa2[0])
        if k2 != 2:
            failures.append(f"2-mirror on-axis ray has {k2} sharp folds (expected 2 -- one per mirror)")
    if not oa1:
        failures.append("1-mirror scene: no on-axis rays")
    else:
        k1 = _sharp_kinks(oa1[0])
        if k1 != 1:
            failures.append(f"1-mirror on-axis ray has {k1} sharp folds (expected 1)")

    # (4) rays coincide with the drawn lens chain on the shared +X leg
    if oa2:
        vx = oa2[0][:, 0]
        worst = 0.0
        for lx in lens_x:
            worst = max(worst, float(np.min(np.abs(vx - lx))))
        if worst > 0.05:
            failures.append(
                f"2-mirror: on-axis ray strays {worst:.3f} mm from the drawn lens chain on the +X leg "
                f"(rays != CAD -- desp_z gap resurfaced)"
            )
        else:
            notes.append(f"2-mirror: rays coincide with the drawn lens chain (worst {worst:.4f} mm)")

    # (5) incoming leg is a 2D disk (cone) for the chain
    if oa2:
        incoming = np.asarray([p[1, :2] for p in oa2 if p.shape[0] >= 2 and float(p[1, 2]) < _AXIS_Z - 1.0], dtype=float)
        # sample the incoming leg (Z below the mirror axis) across rays
        inc_pts = []
        for p in oa2:
            for v in p:
                if float(v[2]) < _AXIS_Z - 5.0 and float(v[2]) > 5.0:
                    inc_pts.append(v[:2])
                    break
        s2 = _second_singular(np.asarray(inc_pts, dtype=float)) if inc_pts else 0.0
        if not (s2 > 0.5):
            failures.append(f"2-mirror incoming leg is a flat fan, not a cone (s2={s2:.4f} <= 0.5, n={len(inc_pts)})")
        else:
            notes.append(f"2-mirror incoming leg is a 2D disk s2={s2:.3f} (cone, not fan)")

    # (6) backward-compat: single-fold focus on the drawn detector
    if oa1:
        end_x = float(np.mean([p[-1][0] for p in oa1]))
        gap = drawn_det1 - end_x
        if abs(gap) > 0.05:
            failures.append(f"single-fold AZ85 regressed: on-axis focus {end_x:.3f} vs drawn detector {drawn_det1:.3f} (gap {gap:+.3f})")
        else:
            notes.append(f"single-fold AZ85 unchanged: focus on the detector (gap {gap:+.3f} mm)")

    if failures:
        return False, failures + [f"note: {n}" for n in notes]
    return True, notes


def main() -> int:
    ok, notes = run_checks()
    print("PASS" if ok else "FAIL", "bugs/0208 folded RA-mirror chain fold (N mirrors):")
    for n in notes:
        print(f"  - {n}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
