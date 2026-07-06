"""Display-free guard for bugs/0208: the folded display rays fold correctly through a
CHAIN of promoted-mirror cubes, not just a single fold.

bugs/0243 rework: the folded scene is traced on the REAL system, so the chain contract is
now physical instead of display-bent -- every drawn ray IS the trace, folding first-surface
at each promoted mirror FACE the beam reaches. The old guard's synthetic second mirror (a
copied sequential row) was seated OFF the folded arm by the pose machinery while the
display-bend painted a second fold mid-air -- fiction the real trace rightly refuses to
draw. The chain scene is therefore the REAL two-fold periscope fixture (the bugs/0236
`_two_fold_editor`: free-placed promoted 2nd mirror with an assigned Mirror face, in-app
confirmed), and the checks assert physics:

  1. fold detection: the two-fold scene reports 2 promoted mirror-fold rows, the stock
     AZ85 exactly 1 (`_promoted_mirror_fold_row_indices`);
  2. the drawn rays are the REAL trace -- no `folded_straight_equivalent_*` display-bend
     tag on either scene;
  3. the on-axis ray has one ~90 deg kink per REACHED mirror (2 on the two-fold, 1 on the
     single fold);
  4. on the shared +X leg the on-axis ray's vertices coincide with the drawn lens-row X's
     (rays == CAD on that leg -- the 0207 consistency, preserved through the second fold);
  5. the incoming leg stays a 2D disk (cone, not a flat fan) for the chain;
  6. rays TERMINATE on each scene's folded Image-surface seat (the trace ends where the
     display draws the sensor).

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_ra_mirror_chain_fold
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import io
import sys

import numpy as np

from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor
from KrakenOS.UI.validate_open3d_two_fold_image_arm_follow import _two_fold_editor

_AXIS_Z = 71.897137


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


def _bend_tags(bundle) -> int:
    return sum(
        1
        for p in (getattr(bundle, "ray_paths", None) or [])
        if str(getattr(p, "display_geometry_source", "") or "").startswith("folded_straight_equivalent")
    )


def _image_seat(editor):
    overrides = getattr(editor.last_system, "_optical_solid_output_port_pose_overrides", {}) or {}
    pose = overrides.get(len(editor.rows) - 1)
    if not isinstance(pose, dict):
        return None, None
    center = np.asarray(pose.get("center"), dtype=float).reshape(3)
    normal = np.asarray(pose.get("rotation"), dtype=float).reshape(3, 3)[:, 2]
    norm = float(np.linalg.norm(normal))
    return center, (normal / norm if norm > 1e-12 else normal)


def _on_seat_count(bundle, seat_c, seat_n) -> int:
    if seat_c is None:
        return 0
    count = 0
    for p in (getattr(bundle, "ray_paths", None) or []):
        pw = np.asarray(getattr(p, "points_world", None), dtype=float)
        if pw.ndim == 2 and pw.shape[0] >= 2 and abs(float((pw[-1, :3] - seat_c) @ seat_n)) < 1e-6:
            count += 1
    return count


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []
    notes: list[str] = []
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            # ---- two-mirror chain: the REAL two-fold periscope (bugs/0236 fixture) ----
            ed2 = _two_fold_editor()
            folds2 = list(ed2._promoted_mirror_fold_row_indices())
            sys2, _r2, b2 = ed2._build_preview_system_rays_bundle(update_state=True)
            oa2 = _onaxis(b2)
            tags2 = _bend_tags(b2)
            seat2_c, seat2_n = _image_seat(ed2)
            on_seat2 = _on_seat_count(b2, seat2_c, seat2_n)
            # drawn lens-row X on the +X leg (rows 2..7, before the free-placed 2nd mirror)
            lens_x = sorted(
                float(np.asarray(ed2._surface_reference_world_point(i, system=sys2), float).reshape(3)[0])
                for i in range(2, 8)
            )

            # ---- single-fold AZ85 ----
            ed1 = _build_editor(_AZ85)
            folds1 = list(ed1._promoted_mirror_fold_row_indices())
            sys1, _r1, b1 = ed1._build_preview_system_rays_bundle(update_state=True)
            oa1 = _onaxis(b1)
            tags1 = _bend_tags(b1)
            seat1_c, seat1_n = _image_seat(ed1)
            on_seat1 = _on_seat_count(b1, seat1_c, seat1_n)
    except Exception as exc:  # noqa: BLE001
        return False, [f"setup raised {exc!r}"]

    # (1) general fold detection
    if len(folds2) != 2:
        failures.append(f"two-fold scene reports {len(folds2)} promoted mirror-fold rows (expected 2)")
    if len(folds1) != 1:
        failures.append(f"single-fold scene reports {len(folds1)} promoted mirror-fold rows (expected 1)")

    # (2) the drawn rays are the REAL trace (bugs/0243: no display-bend tags)
    if tags2 != 0:
        failures.append(f"two-fold: {tags2} rays carry a display-bend tag (must be the raw trace)")
    if tags1 != 0:
        failures.append(f"single-fold: {tags1} rays carry a display-bend tag (must be the raw trace)")

    # (3) one ~90 deg kink per reached mirror
    if not oa2:
        failures.append("two-fold scene: no on-axis rays")
    else:
        k2 = _sharp_kinks(oa2[0])
        if k2 != 2:
            failures.append(f"two-fold on-axis ray has {k2} sharp folds (expected 2 -- one per mirror)")
    if not oa1:
        failures.append("single-fold scene: no on-axis rays")
    else:
        k1 = _sharp_kinks(oa1[0])
        if k1 != 1:
            failures.append(f"single-fold on-axis ray has {k1} sharp folds (expected 1)")

    # (4) rays coincide with the drawn lens chain on the shared +X leg
    if oa2:
        vx = oa2[0][:, 0]
        worst = 0.0
        for lx in lens_x:
            worst = max(worst, float(np.min(np.abs(vx - lx))))
        if worst > 0.05:
            failures.append(
                f"two-fold: on-axis ray strays {worst:.3f} mm from the drawn lens chain on the +X leg "
                f"(rays != CAD -- desp_z gap resurfaced)"
            )
        else:
            notes.append(f"two-fold: rays coincide with the drawn lens chain (worst {worst:.4f} mm)")

    # (5) incoming leg is a 2D disk (cone) for the chain
    if oa2:
        inc_pts = []
        for p in oa2:
            for v in p:
                if float(v[2]) < _AXIS_Z - 5.0 and float(v[2]) > 5.0:
                    inc_pts.append(v[:2])
                    break
        s2 = _second_singular(np.asarray(inc_pts, dtype=float)) if inc_pts else 0.0
        if not (s2 > 0.5):
            failures.append(f"two-fold incoming leg is a flat fan, not a cone (s2={s2:.4f} <= 0.5, n={len(inc_pts)})")
        else:
            notes.append(f"two-fold incoming leg is a 2D disk s2={s2:.3f} (cone, not fan)")

    # (6) rays terminate on each scene's folded Image-surface seat
    if on_seat2 < 8:
        failures.append(f"two-fold: only {on_seat2} rays terminate on the folded Image seat")
    else:
        notes.append(f"two-fold: {on_seat2} rays terminate on the folded Image seat {np.round(seat2_c, 2)}")
    if on_seat1 < 8:
        failures.append(f"single-fold: only {on_seat1} rays terminate on the folded Image seat")
    else:
        notes.append(f"single-fold: {on_seat1} rays terminate on the folded Image seat {np.round(seat1_c, 2)}")

    if failures:
        return False, failures + [f"note: {n}" for n in notes]
    return True, notes


def main() -> int:
    ok, lines = run_checks()
    if not ok:
        print("FAIL bugs/0208 folded RA-mirror chain fold (N mirrors):")
        for line in lines:
            print(f"  - {line}")
        return 1
    print("PASS bugs/0208 folded RA-mirror chain fold (real two-fold chain, real trace):")
    for line in lines:
        print(f"  - {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
