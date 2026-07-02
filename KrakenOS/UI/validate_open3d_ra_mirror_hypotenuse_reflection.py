"""Display-free guard for bugs/0192: on the folded RA-mirror scene the drawn rays must
REFLECT OFF the real mesh hypotenuse, not off the opposite (mid-air) diagonal.

The user built the minimal repro -- a plain Object + Image, then one promoted
right-angle mirror -- and re-flagged "reflection still wrong at hypotenuse" AFTER the
bugs/0191 fix was live (flag_20260701_120015_636). bugs/0191 was a misdiagnosis: it
truncated a retroreflection that only exists in the RAW non-sequential trace, never in
the live folded-sequential bundle, so it was a no-op on what the user sees.

Root cause: the bugs/0187 folded-sequential trace folds the running frame by a proper
ROTATION (sequential ``Mirror`` + AxisMove=2). A physical mirror is an improper
REFLECTION. Both agree on the chief direction but differ by a meridional flip, so every
off-axis ray kinked on the plane X+Z=const (the '\\', in mid-air) while the drawn mesh
cube reflects on X-Z=const (the '/'). The kink sat up to ~12 mm off the drawn face.

Fix: ``correct_folded_mirror_ray_points`` re-reflects each ray's post-mirror leg across
the flip plane (normal ``d_out x (d_in x d_out)``) and re-anchors its kink onto the real
face plane (through the mirror centre, normal = the mesh Mirror-face normal), so the kink
lands EXACTLY on the '/' face. This per-ray re-anchor (``tau``) is now the PATH-B tool
(the sequential-``Mirror`` fallback for a fold chain); the single-fold PATH A (AZ85)
switched to the bugs/0203 RIGID flip (``_apply_folded_mirror_rigid_reflection``), which
keeps the converged focus on the drawn detector for a 2D cone at the price of a ~mm kink
gap (the KrakenOS mirror station sits ~12.5mm before the mesh hypotenuse centre, so no
single rigid map lands the kink on the mesh face AND the focus on the detector -- focus
wins, per the user's flag). Both leave the optical trace untouched (rays reach the sensor).

This guard binds the REAL free functions (unit) and the REAL wired pipeline (to the live
AZ85 editor -- the same single-fold flip as the minimal repro), asserting:
  1. a synthetic rotation-folded polyline is re-folded so its kink lands ON the real '/'
     face, its downstream leg keeps +X, and its incoming leg is byte-identical;
  2. a monotonic-forward ray and a degenerate/short polyline are left untouched (None);
  3. the flip-plane normal for a +Z chief off a (0.707,0,-0.707) face is ~(0,0,1);
  4. INTEGRATION: on the REAL rotation-folded AZ85 bundle every off-axis kink sits OFF the
     '/' face (max residual > 1 mm); the free function re-folds each ONTO it (< 1e-6) with
     the correct '/' sign. The WIRED Path A now bends via the bugs/0203 rigid flip (every
     path tagged ``folded_mirror_rigid_reflected``; focus-on-detector guarded by bugs/0197
     & the cone by bugs/0203) -- so the per-ray free function is the Path-B tool this
     section still validates on real traced data;
  5. the fold is scoped: AZ85 yields exactly ONE fold record; the sequential flat_mirror
     scene yields NONE (the correction is inert on non-promoted mirrors).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_ra_mirror_hypotenuse_reflection

Exit: 0 = pass, 1 = regression.
"""

from __future__ import annotations

import contextlib
import io
import sys

import numpy as np

from KrakenOS.UI.services.folded_sequential_fold import (
    _unit,
    correct_folded_mirror_ray_points,
    fold_promoted_mirror_specs_to_sequential,
    mirror_reflection_flip_plane_normal,
    promoted_mirror_world_center,
)
from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _build_editor, _AZ85, _PLAIN


def _kink(points, center, normal, cos_fold_max=0.2):
    """(residual on the face plane, kink X) at the sharpest ~90 deg turn, or None."""
    coords = np.asarray(points, dtype=float)[:, :3]
    seg = np.diff(coords, axis=0)
    ln = np.linalg.norm(seg, axis=1)
    good = ln > 1e-9
    if int(good.sum()) < 2:
        return None
    u = np.zeros_like(seg)
    u[good] = seg[good] / ln[good, None]
    cos = np.sum(u[:-1] * u[1:], axis=1)
    ki = int(np.argmin(cos))
    if cos[ki] > cos_fold_max:
        return None
    K = coords[ki + 1]
    return float(np.dot(K - center, normal)), float(K[0])


def _fold_geometry(editor):
    specs = editor._serializable_specs_for_rows(list(editor.rows))
    _folded, records = fold_promoted_mirror_specs_to_sequential(specs)
    if not records:
        return specs, records, None, None
    rec = records[0]
    normal = _unit(rec["face_normal"])
    center = promoted_mirror_world_center(specs, int(rec["row_index"]))
    return specs, records, center, normal


def main() -> int:
    failures: list[str] = []
    notes: list[str] = []

    C = np.array([0.0, 0.0, 71.9])
    N = _unit([0.7071067811865476, 0.0, -0.7071067811865476])

    # ---- (1) a synthetic rotation-folded ray re-folds onto the '/' face ----
    # Incoming +Z at X=+5 hits the ROTATION-folded (wrong '\\') kink Z=71.9-5=66.9,
    # then travels +X. The fix must move the kink to the real '/' face Z=71.9+5=76.9.
    rot_folded = np.asarray(
        ((5.0, 0.0, 0.0), (5.0, 0.0, 66.9), (40.0, 0.0, 66.9), (120.0, 0.0, 66.9)),
        dtype=float,
    )
    fixed = correct_folded_mirror_ray_points(rot_folded, C, N, [0.0, 0.0, 1.0])
    if fixed is None:
        failures.append("unit: the rotation-folded ray was NOT re-folded (expected a correction)")
    else:
        fixed = np.asarray(fixed, dtype=float)
        if not np.allclose(fixed[0], (5.0, 0.0, 0.0)):
            failures.append("unit: the incoming launch vertex was altered (must stay put)")
        if not np.allclose(fixed[1], (5.0, 0.0, 76.9), atol=1e-6):
            failures.append(f"unit: kink not moved onto the '/' face; got {np.round(fixed[1],3).tolist()} expected (5,0,76.9)")
        if abs(float(np.dot(fixed[1] - C, N))) > 1e-9:
            failures.append("unit: the re-folded kink does not lie ON the real '/' face plane")
        if not np.allclose(fixed[-1], (120.0, 0.0, 76.9), atol=1e-6):
            failures.append(f"unit: downstream leg not on the '/' side +X; got {np.round(fixed[-1],3).tolist()} expected (120,0,76.9)")

    # ---- (2) monotonic-forward + degenerate polylines untouched (None) ----
    monotonic = np.asarray(((0.0, 0.0, 0.0), (0.0, 0.0, 30.0), (0.0, 0.0, 60.0)), dtype=float)
    if correct_folded_mirror_ray_points(monotonic, C, N, [0.0, 0.0, 1.0]) is not None:
        failures.append("regression: a straight (no-fold) ray was re-folded")
    if correct_folded_mirror_ray_points(np.zeros((2, 3)), C, N, [0.0, 0.0, 1.0]) is not None:
        failures.append("regression: a degenerate 2-point polyline was not handled safely (expected None)")

    # ---- (3) flip-plane normal ----
    m = mirror_reflection_flip_plane_normal([0.0, 0.0, 1.0], N)
    if m is None or not np.allclose(np.abs(m), (0.0, 0.0, 1.0), atol=1e-6):
        failures.append(f"unit: flip-plane normal {None if m is None else np.round(m,4).tolist()} != +/-Z for a +Z chief off a '/' face")

    # ---- (4) INTEGRATION: real AZ85 -- free fn re-folds the rotation fold onto the '/'
    #          face; the WIRED Path A now bends via the bugs/0203 rigid flip (tagged) ----
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            editor = _build_editor(_AZ85)
            specs, records, center, normal = _fold_geometry(editor)
            # Rotation fold ONLY: shadow the bugs/0203 rigid flip -> raw wrong-'/' bundle.
            editor._apply_folded_mirror_rigid_reflection = lambda bundle, ft: None
            _s0, _r0, raw_bundle = editor._build_preview_system_rays_bundle(update_state=True)
            raw_paths = list(getattr(raw_bundle, "ray_paths", []))
            # The REAL wired Path A (bugs/0203 rigid flip) inside a fresh preview build.
            del editor._apply_folded_mirror_rigid_reflection
            _s1, _r1, fixed_bundle = editor._build_preview_system_rays_bundle(update_state=True)
            fixed_paths = list(getattr(fixed_bundle, "ray_paths", []))

        if center is None or normal is None:
            failures.append("AZ85 integration: no promoted-mirror fold record (precondition gone)")
        else:
            before, freefn_after, freefn_badsign = [], [], 0
            for path in raw_paths:
                info = _kink(getattr(path, "points_world", np.empty((0, 3))), center, normal)
                if info is not None:
                    before.append(abs(info[0]))
                fx = correct_folded_mirror_ray_points(getattr(path, "points_world", None), center, normal, [0.0, 0.0, 1.0])
                if fx is None:
                    continue
                fi = _kink(fx, center, normal)
                if fi is not None:
                    freefn_after.append(abs(fi[0]))
                K = np.asarray(fx, float)
                # '/' sign: for the re-folded off-axis kink sign(x) must equal sign(z - Cz)
                seg = np.diff(K[:, :3], axis=0); ln = np.linalg.norm(seg, axis=1); g = ln > 1e-9
                u = np.zeros_like(seg); u[g] = seg[g] / ln[g, None]
                cos = np.sum(u[:-1] * u[1:], axis=1); kk = int(np.argmin(cos)) + 1
                kx, kz = float(K[kk, 0]), float(K[kk, 2])
                if abs(kx) > 0.5 and np.sign(kx) != np.sign(kz - center[2]):
                    freefn_badsign += 1
            tagged, total = 0, 0
            for path in fixed_paths:
                info = _kink(getattr(path, "points_world", np.empty((0, 3))), center, normal)
                if info is None:
                    continue
                total += 1
                if str(getattr(path, "display_geometry_source", "")) == "folded_mirror_rigid_reflected":
                    tagged += 1
            before = np.array(before) if before else np.array([0.0])
            freefn_after = np.array(freefn_after) if freefn_after else np.array([9.9])
            if before.max() <= 1.0:
                failures.append(f"AZ85 integration: max kink residual (rotation fold) only {before.max():.3f} mm -> flip precondition gone, guard vacuous")
            if freefn_after.max() >= 1e-6:
                failures.append(f"AZ85 integration: free-fn AFTER max residual {freefn_after.max():.3e} (rays still off the '/' face)")
            if freefn_badsign != 0:
                failures.append(f"AZ85 integration: {freefn_badsign} free-fn re-folded off-axis kink(s) on the WRONG '/' sign")
            if total > 0 and tagged != total:
                failures.append(f"AZ85 integration: only {tagged}/{total} wired Path-A paths tagged folded_mirror_rigid_reflected (bugs/0203)")
            notes.append(
                f"AZ85 kinked rays {total} | rotation-fold '/' residual max {before.max():.3f} mm "
                f"-> free-fn {freefn_after.max():.2e} (badsign {freefn_badsign}) | wired rigid-flip tagged {tagged}"
            )
    except Exception as exc:  # noqa: BLE001
        failures.append(f"AZ85 integration raised {exc!r}")

    # ---- (5) scope: one fold record for AZ85, none for the sequential flat_mirror ----
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            _s, az_records, _c, _n = _fold_geometry(_build_editor(_AZ85))
            _s2, plain_records, _c2, _n2 = _fold_geometry(_build_editor(_PLAIN))
        if len(az_records) != 1:
            failures.append(f"AZ85 scope: expected exactly 1 fold record, got {len(az_records)}")
        if len(plain_records) != 0:
            failures.append(f"regression: {_PLAIN} yielded {len(plain_records)} fold record(s) -> correction would touch a non-promoted mirror")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"fold-scope check raised {exc!r}")

    if failures:
        print("FAIL bugs/0192 folded RA-mirror hypotenuse reflection (rays off the wrong diagonal):")
        for line in failures:
            print(f"  - {line}")
        for note in notes:
            print(f"  - note: {note}")
        return 1
    print("PASS bugs/0192 folded RA-mirror hypotenuse reflection (rays reflect off the real mesh face):")
    print("  - a synthetic rotation-folded ray re-folds onto the '/' face, +X downstream, incoming untouched")
    print("  - straight + degenerate polylines are left untouched (None); flip-plane normal is +/-Z")
    print("  - AZ85 real trace: rotation-fold kinks OFF the '/' face, free fn re-folds them ON it (correct sign)")
    print("  - wired Path A bends via the bugs/0203 rigid flip (tagged); focus-on-detector guarded by bugs/0197")
    print(f"  - scope: 1 fold record for AZ85, 0 for {_PLAIN} (correction inert on sequential mirrors)")
    for note in notes:
        print(f"  - {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
