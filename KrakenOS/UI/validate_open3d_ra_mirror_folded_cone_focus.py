"""Display-free guard for bugs/0203: the folded RA-mirror preview must launch a DENSE 3D
CONE (not the sparse area-filling envelope that reads as a flat fan, bug #2) AND fold it to a
tight focus at the REFLECTED image, ON the drawn optical axis, without shearing (bug #5).

The user re-flagged the working (bugs/0197-converging) folded AZ85 scene twice:
  #2  "the rays are fan, not cone. Old bug resurface." -- the folded AZ85 resolves to
      ``use_nonseq`` (its promoted mesh mirror reads as an "STL optical solid"), so BOTH
      ``_preview_scene_sampling_mode`` and ``_preview_3d_sampling_mode`` returned
      "world_envelope": only ``Ray Count`` (~31) golden-angle pupil points. Over the slender
      f/13 fold that sparse disk foreshortens to a wireframe sheet and reads as a flat FAN,
      not the dense cone a mirror-less sequential AZ85 shows.
  #5  "the focusing rays vary from left to right. Some before / at / after focus." -- the
      bugs/0192 per-ray ``tau`` re-anchor is a SHEAR on the 2D cone: it lands the kink on the
      '/' face but drags the focus short and blows the on-axis waist to ~mm.

Fix #2 (this bug): a NON-branching promoted-mirror fold is traced through its straight-
equivalent SEQUENTIAL rows (bugs/0197), so a revolved launch cone is exactly the rotated
sequential cone -- each pupil ray is still traced individually through the fold, so nothing is
lost and the converged focus is preserved. ``_folded_scene_prefers_launch_cone`` routes such a
scene to "world_cone" (the dense ``count//2`` rings x ``_cone_azimuth_count`` spokes revolve,
~361 on-axis rays) instead of the sparse envelope. The envelope is kept only for genuinely
BRANCHING scenes (beam splitter / diffuse / probabilistic split), whose per-branch sagittal
width it must preserve.
Fix #5 (bugs/0197): ``_apply_folded_mirror_rigid_reflection`` replaces the per-ray ``tau`` with
ONE rigid reflection across the flip plane (normal ``d_out x s``) through the FOLDED fold
point -> the converged cone keeps its tight waist. This map survives only for the check (4)
rigid-vs-tau contrast below.

NOTE (bugs/0205): the PRODUCTION display fold (checks 2 & 3) was later replaced by a single
REFLECTION of the straight-equivalent rays about the mirror-face CENTRE plane
(``_reflect_straight_equivalent_display_rays``) -- an isometry, so the incoming leg keeps its
cone and the kink lands ON the '/' hypotenuse. The focus lands at the REFLECTED image, ON the
drawn optical axis (Z). That reflected image sits ``desp_z`` (~12.5mm) SHORT of the
rotation-folded drawn detector along +X: the detector/overlays are folded by the ROTATION ``F``
(which MUST stay a rotation so the lens/camera CAD is not mirrored), so a reflection-folded ray
bundle and a rotation-folded detector differ by that meridional flip -- an overlay-fold gap
deferred to a follow-up (nearly invisible over this f/13 fold: ~1mm blur). So check (3) targets
the PHYSICS (the reflected image on-axis), not the mis-folded detector X.

Asserts (all display-free, on the live AZ85 editor):
  1. #2 routing: ``_folded_scene_prefers_launch_cone()`` is True and BOTH
     ``_preview_scene_sampling_mode()`` and ``_preview_3d_sampling_mode()`` == "world_cone";
  2. #2 density+shape: the production (world_cone) on-axis bundle is DENSE (>= 100 rays) where
     the forced "world_envelope" gives only the sparse <= 40, AND the world_cone cross-section
     mid-arm is a 2D DISK (2nd singular value substantial), not a collinear fan;
  3. #5: the wired on-axis cone lands at the REFLECTED image -- endpoint X AND Z match the
     mirror-centre reflection of the straight focus (|dX|,|dZ| < 0.05 mm; the Z-match is the
     on-axis check the user flagged) -- and CONVERGES (endpoint transverse RMS < 0.05 mm);
  4. #5 contrast: on the SAME rotation-folded bundle the RIGID flip keeps that tight waist
     while the OLD per-ray ``tau`` SHEARS it (endpoint transverse RMS > 0.5 mm) -- guards
     against a revert to the shearing correction.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_ra_mirror_folded_cone_focus

Exit: 0 = pass, 1 = regression.
"""

from __future__ import annotations

import contextlib
import io
import sys

import numpy as np

from KrakenOS.UI.services.folded_sequential_fold import (
    correct_folded_mirror_ray_points,
    fold_promoted_mirror_specs_to_sequential,
    mirror_reflection_flip_plane_normal,
    promoted_mirror_world_center,
    reflect_straight_equivalent_ray_points,
    rigid_reflect_folded_mirror_ray_points,
)
from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor


def _onaxis(bundle_or_paths) -> list[np.ndarray]:
    paths = getattr(bundle_or_paths, "ray_paths", None)
    raw = paths if paths is not None else bundle_or_paths
    out: list[np.ndarray] = []
    for path in list(raw or []):
        pw = path if isinstance(path, np.ndarray) else getattr(path, "points_world", None)
        pw = np.asarray(pw, dtype=float)
        if pw.ndim != 2 or pw.shape[0] < 2 or pw.shape[1] < 3:
            continue
        if float(np.linalg.norm(pw[0][:3])) <= 1.0 and float(pw[:, 0].max()) > 250.0:
            out.append(pw)
    return out


def _second_singular(coords2d: np.ndarray) -> float:
    """2nd singular value of centred 2D points: ~0 => collinear (fan), >0 => 2D (disk)."""
    a = np.asarray(coords2d, dtype=float)
    if a.ndim != 2 or a.shape[0] < 3 or a.shape[1] != 2:
        return 0.0
    c = a - a.mean(0)
    s = np.linalg.svd(c, compute_uv=False)
    return float(s[1]) if s.size >= 2 else 0.0


def _cross_at_x(paths: list[np.ndarray], x: float) -> np.ndarray:
    """Interpolate each on-axis ray's (Y,Z) where its outgoing +X leg crosses plane X=x."""
    rows: list[np.ndarray] = []
    for p in paths:
        xa = p[:, 0]
        for i in range(len(xa) - 1):
            x0, x1 = xa[i], xa[i + 1]
            if (x0 - x) * (x1 - x) <= 0 and abs(x1 - x0) > 1e-9:
                t = (x - x0) / (x1 - x0)
                rows.append(p[i, 1:3] + t * (p[i + 1, 1:3] - p[i, 1:3]))
                break
    return np.asarray(rows, dtype=float) if rows else np.empty((0, 2))


def _endpoint_stats(paths: list[np.ndarray]) -> tuple[float, float]:
    ends = np.asarray([p[-1][:3] for p in paths], dtype=float)
    x_mean = float(ends[:, 0].mean())
    trms = float(np.sqrt(((ends[:, 1:3] - ends[:, 1:3].mean(0)) ** 2).sum(1).mean()))
    return x_mean, trms


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []
    notes: list[str] = []

    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            editor = _build_editor(_AZ85)
            editor._build_preview_system_rays_bundle(update_state=True)
            editor.snap_detector_to_image_plane()

            # ---- #2 routing: the fix must classify this scene as a launch cone ----
            prefers_cone = bool(editor._folded_scene_prefers_launch_cone())
            has_fold = bool(editor._scene_has_promoted_mirror_fold())
            scene_mode = str(editor._preview_scene_sampling_mode())
            mode_3d = str(editor._preview_3d_sampling_mode())

            # ---- production (world_cone) bundle: #2 density + #5 convergence ----
            system, _rays, cone_bundle = editor._build_preview_system_rays_bundle(update_state=True)
            drawn_x = float(
                np.asarray(
                    editor._surface_reference_world_point(len(editor.rows) - 1, system=system),
                    dtype=float,
                ).reshape(3)[0]
            )
            cone_oa = _onaxis(cone_bundle)

            # ---- the OLD sparse envelope, forced explicitly for the density contrast ----
            _se, _re, env_bundle = editor._build_preview_system_rays_bundle(
                sampling_mode="world_envelope", update_state=False
            )
            env_oa = _onaxis(env_bundle)

            # ---- geometry for the #5 rigid-vs-tau contrast ----
            specs = editor._serializable_specs_for_rows(list(editor.rows))
            _f, recs = fold_promoted_mirror_specs_to_sequential(specs)
            ri = int(recs[0]["row_index"])
            face_normal = np.asarray(recs[0]["face_normal"], dtype=float).reshape(3)
            chief_in = np.asarray(recs[0].get("chief_in") or [0.0, 0.0, 1.0], dtype=float).reshape(3)
            center = np.asarray(promoted_mirror_world_center(specs, ri), dtype=float).reshape(3)
            flip = mirror_reflection_flip_plane_normal(chief_in, face_normal)

            # ---- the PHYSICAL folded focus target (bugs/0205): the straight-equivalent on-axis
            # focus REFLECTED about the mirror-face CENTRE plane (an isometry of the real '/'
            # hypotenuse). The production fold reflects too, so the wired cone must land here. The
            # rotation-folded drawn detector sits ~desp_z beyond this along +X (overlay-fold gap,
            # deferred) -- so we target the physics, not the mis-folded detector.
            editor._reflect_straight_equivalent_display_rays = lambda _b: None
            _ss, _sr, straight_bundle = editor._build_preview_system_rays_bundle(update_state=False)
            del editor._reflect_straight_equivalent_display_rays
            straight_terms = []
            for _p in (getattr(straight_bundle, "ray_paths", None) or []):
                _pw = np.asarray(getattr(_p, "points_world", None), dtype=float)
                if _pw.ndim == 2 and _pw.shape[0] >= 3 and float(np.linalg.norm(_pw[0, :3])) <= 1.0:
                    straight_terms.append(_pw[-1, :3])
            straight_focus = np.mean(straight_terms, axis=0) if straight_terms else np.full(3, np.nan)
            _refl = reflect_straight_equivalent_ray_points(
                np.vstack([[0.0, 0.0, 0.0], straight_focus]), center, face_normal
            )
            expected_focus = np.asarray(_refl[-1, :3], dtype=float) if _refl is not None else np.full(3, np.nan)

            # ---- rotation-fold-only bundle (shadow the rigid flip) for the contrast ----
            wl = float(editor._current_wavelength())
            mr = max((max(r.diameter / 2.0, 0.5) for r in editor.rows), default=1.0)
            sys_c = editor.build_system(require_solids=True)
            ftr = editor._folded_sequential_trace_rows(editor.rows)
            rays_c, ft = editor._trace_preview_rays_folded_aware(
                sys_c, wl, mr, sampling_mode=editor._preview_3d_sampling_mode(), folded_trace_rows=ftr
            )
            rot_bundle = editor._build_scene_bundle(sys_c, rays_c, mr)
            editor._fold_straight_equivalent_display_rays(rot_bundle, ft)
            rot_paths = [np.asarray(getattr(p, "points_world", None), dtype=float) for p in rot_bundle.ray_paths]
            M = np.asarray(ft, dtype=float).reshape(4, 4)
            anchor = M[:3, :3] @ center + M[:3, 3]
            rigid_paths = [p for p in (rigid_reflect_folded_mirror_ray_points(p, anchor, flip) for p in rot_paths) if p is not None]
            tau_paths = [p for p in (correct_folded_mirror_ray_points(p, center, face_normal, chief_in) for p in rot_paths) if p is not None]
    except Exception as exc:  # noqa: BLE001
        return False, [f"setup raised {exc!r}"]

    # (1) #2 routing: the non-branching promoted-mirror fold launches a cone, not an envelope
    if not has_fold:
        failures.append("#2 routing: _scene_has_promoted_mirror_fold() False on the AZ85 RA-mirror scene")
    if not prefers_cone:
        failures.append("#2 routing: _folded_scene_prefers_launch_cone() False (scene still routes to the sparse envelope)")
    if scene_mode != "world_cone":
        failures.append(f"#2 routing: _preview_scene_sampling_mode()={scene_mode!r} (expected 'world_cone')")
    if mode_3d != "world_cone":
        failures.append(f"#2 routing: _preview_3d_sampling_mode()={mode_3d!r} (expected 'world_cone')")
    if has_fold and prefers_cone and scene_mode == "world_cone" and mode_3d == "world_cone":
        notes.append("#2 routing: promoted-mirror fold -> world_cone (scene + 3D)")

    # (2) #2 density+shape: production cone is DENSE where the old envelope is sparse, and is a disk
    if len(cone_oa) < 100:
        failures.append(f"#2 density: production world_cone on-axis rays too few ({len(cone_oa)} < 100 -> still sparse)")
    if len(env_oa) > 40:
        failures.append(f"#2 density: forced world_envelope not sparse ({len(env_oa)} > 40) -> contrast is vacuous")
    if len(cone_oa) < 3 * max(len(env_oa), 1):
        failures.append(f"#2 density: cone ({len(cone_oa)}) is not >=3x the envelope ({len(env_oa)}) -> no real densification")
    if cone_oa:
        cross = _cross_at_x(cone_oa, 0.5 * drawn_x)
        s2 = _second_singular(cross)
        if cross.shape[0] < 20 or not (s2 > 0.5):
            failures.append(
                f"#2 shape: world_cone mid-arm cross-section is not a 2D disk at X={0.5*drawn_x:.1f} "
                f"(2nd singular {s2:.4f} <= 0.5, n={cross.shape[0]}) -> reads as a fan"
            )
        else:
            notes.append(
                f"#2 density+shape: cone {len(cone_oa)} vs envelope {len(env_oa)} on-axis rays; "
                f"cone cross-section disk s2={s2:.3f} ({cross.shape[0]} rays) at X={0.5*drawn_x:.1f}"
            )

    # (3) #5: wired (world_cone) on-axis cone converges at the REFLECTED image, ON the drawn
    #     optical axis (Z). bugs/0205: the fold is a reflection about the mirror-face centre, so
    #     the focus lands at the physical reflected image -- NOT on the rotation-folded drawn
    #     detector, which sits ~desp_z beyond along +X (an overlay-fold gap, deferred).
    ex, ez = float(expected_focus[0]), float(expected_focus[2])
    if len(cone_oa) < 6:
        failures.append(f"#5: too few on-axis folded rays to test convergence ({len(cone_oa)})")
    elif not (np.isfinite(ex) and np.isfinite(ez)):
        failures.append("#5: could not derive the physical reflected-focus target (straight trace/reflection failed)")
    else:
        x_mean, trms = _endpoint_stats(cone_oa)
        z_mean = float(np.mean([p[-1][2] for p in cone_oa]))
        if abs(x_mean - ex) > 0.05:
            failures.append(f"#5: wired on-axis focus X off the reflected image: X {x_mean:.3f} vs {ex:.3f} (dX {x_mean-ex:+.3f})")
        if abs(z_mean - ez) > 0.05:
            failures.append(f"#5: wired on-axis focus OFF the optical axis: Z {z_mean:.3f} vs {ez:.3f} (dZ {z_mean-ez:+.3f}; ~-desp_z means a front-datum fold -- 0205 offset regression)")
        if not (trms < 0.05):
            failures.append(f"#5: wired on-axis cone NOT converged: endpoint transverse RMS {trms:.4f} mm >= 0.05 (sheared?)")
        if abs(x_mean - ex) < 0.05 and abs(z_mean - ez) < 0.05 and trms < 0.05:
            notes.append(
                f"#5: on-axis focus ({x_mean:.3f},{z_mean:.3f}) at the reflected image "
                f"(rotation-folded detector X {drawn_x:.3f} sits +{drawn_x-x_mean:.3f} beyond -- overlay-fold gap); "
                f"transverse RMS={trms*1000:.2f} um"
            )

    # (4) #5 contrast: rigid keeps the waist, per-ray tau shears it
    rigid_oa = _onaxis(rigid_paths)
    tau_oa = _onaxis(tau_paths)
    if len(rigid_oa) < 6 or len(tau_oa) < 6:
        failures.append(f"#5 contrast: too few on-axis rays (rigid {len(rigid_oa)}, tau {len(tau_oa)})")
    else:
        _rx, rigid_trms = _endpoint_stats(rigid_oa)
        _tx, tau_trms = _endpoint_stats(tau_oa)
        if not (rigid_trms < 0.05):
            failures.append(f"#5 contrast: RIGID flip did not converge (endpoint transverse RMS {rigid_trms:.4f} mm >= 0.05)")
        if not (tau_trms > 0.5):
            failures.append(f"#5 contrast: per-ray tau did NOT shear (endpoint transverse RMS {tau_trms:.4f} mm <= 0.5) -> the guard is vacuous")
        if rigid_trms < 0.05 and tau_trms > 0.5:
            notes.append(f"#5 contrast: rigid endRMS {rigid_trms*1000:.2f} um vs per-ray tau {tau_trms*1000:.1f} um (shear)")

    if failures:
        return False, failures + [f"note: {n}" for n in notes]
    return True, notes


def main() -> int:
    ok, notes = run_checks()
    if ok:
        print("PASS bugs/0203 folded cone focus:")
        print("  - #2 non-branching promoted-mirror fold routes to world_cone (dense revolve), not the sparse envelope")
        print("  - #2 production on-axis bundle is a dense 2D disk (cone); forced envelope stays sparse")
        print("  - #5 wired on-axis cone converges at the reflected image ON the drawn optical axis; rigid flip keeps the waist where tau shears")
    else:
        print("FAIL bugs/0203 folded cone focus (fan-not-cone / sheared focus):")
    for note in notes:
        print(f"  - {note}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
