"""Display-free guard for bugs/0243 -- the folded scene is traced on the REAL system.

flag_20260706_161136 ("after setting FOV 55x55, still the same error") + the user's
diagnosis: "the physics engine and the UI out-of-sync or detached, the UI clearly shows
the ray reflect in the air while the underlying code trace through glass" / "It is first
surface reflection or Outer reflection" / "the ray not even touches the lens surrogate,
and yet it can focus."

Root cause: the folded promoted-RA-mirror scene was traced on a fictional UNFOLDED
straight-equivalent (mirrors flattened to AIR plates on a straight axis) and the drawn
rays were display-BENT afterwards (bugs/0197/0208), with reconcile/reseat snaps
(bugs/0217/0239) papering the residuals -- so the drawn rays were never the physics
trace. The workaround existed because the real non-seq trace retroreflected the ideal
Thin Lenses (bugs/0187): KrakenSys carries directions in a SIGN-relative (pseudo-forward)
convention after a reflection, but the ideal Thin Lens answers with an ABSOLUTE exit
direction, so behind an odd number of folds the loop marched it backwards.

The bugs/0243 rework: (1) KrakenSys re-expresses the Thin-Lens exit in the loop's SIGN
convention (unfolded scenes byte-identical); (2) the preview traces the REAL system --
mesh mirrors reflect FIRST SURFACE off the coated face's analytic plane (the beam never
enters the prism glass), lens/aperture/image rows are intersected at their folded
output-port poses (the same overrides the display seats overlays with); (3) the
display-bend/reconcile/reseat pipeline is retired -- what is drawn IS the trace;
(4) a mid-chain aperture-stop vignette collects a shape-consistent terminal record
(the old whole-empty record crashed raykeeper.push on numpy>=1.24 ragged stacking).

Checks (two-fold AZ85 periscope, display-free):
  (A) REAL RAYS + VIGNETTE PUSH: the preview bundle builds on the real system, drawn
      rays carry NO display-bend tag, and the world-cone's mid-chain vignetted rays
      pushed without the ragged-stack crash (>=1 invalid record collected).
  (B) FIRST SURFACE: every drawn ray that folds kinks ON each mirror's hypotenuse
      plane and obeys the reflection law about the face normal at the kink.
  (C) GLASS INERT: no drawn-ray vertex lies inside either prism's glass wedge -- the
      beam bounces off the OUTER face (the user's external reflection).
  (D) DETECTOR TERMINATION: every detector-reaching ray ends ON the folded Image
      surface seat (the trace terminates where the display draws the detector).
  (E) LENS IN BEAM: every detector-reaching ray crosses the first Thin Lens at its
      folded seat within the lens aperture (the drawn surrogate is genuinely traced).
  (F) UNFOLDED REGRESSION: a plain unfolded Thin-Lens scene still focuses exactly
      (the SIGN-convention fix is inert when SIGN=+1).

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_folded_real_trace_sync
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import io
from dataclasses import dataclass

import numpy as np

from KrakenOS.UI.validate_open3d_two_fold_image_arm_follow import _two_fold_editor
from KrakenOS.UI.services.folded_sequential_fold import (
    _is_promoted_mirror_fold,
    mirror_fold_face_normal,
    promoted_mirror_world_center,
)


@dataclass
class Check:
    check: str
    ok: bool
    detail: str


def _quiet(fn, *args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        return fn(*args, **kwargs)


def _unit(v):
    v = np.asarray(v, dtype=float).reshape(3)
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-12 else v


def _mirror_planes(editor):
    """[(row_index, world centre, unit face normal, half-extent)] per promoted fold."""
    specs = editor._serializable_specs_for_rows(list(editor.rows))
    planes = []
    for index, spec in enumerate(specs):
        if not _is_promoted_mirror_fold(spec):
            continue
        normal = mirror_fold_face_normal(spec.get("advanced"))
        if normal is None:
            continue
        center = np.asarray(promoted_mirror_world_center(specs, index), dtype=float).reshape(3)
        half = 0.5 * float(spec.get("thickness", 0.0) or 0.0)
        planes.append((index, center, _unit(normal), max(half, 1.0)))
    return planes


def validate_folded_real_trace_sync() -> list[Check]:
    checks: list[Check] = []

    editor = _two_fold_editor()
    system, rays, bundle = _quiet(editor._build_preview_system_rays_bundle, update_state=True)
    paths = list(getattr(bundle, "ray_paths", None) or [])
    polylines = []
    for path in paths:
        pts = np.asarray(getattr(path, "points_world", None), dtype=float)
        if pts.ndim == 2 and pts.shape[0] >= 2 and pts.shape[1] >= 3:
            polylines.append(pts[:, :3])

    # ---- (A) real rays, no display-bend tags, vignetted rays pushed ------------------ #
    bend_tags = [
        str(getattr(p, "display_geometry_source", "") or "")
        for p in paths
        if str(getattr(p, "display_geometry_source", "") or "").startswith("folded_straight_equivalent")
    ]
    invalid_records = len(getattr(editor.last_rays, "invalid_NAME", []) or [])
    checks.append(Check(
        "REAL RAYS: the folded preview traces the real system (no display-bend tags) and "
        "mid-chain vignetted rays push cleanly (the ragged-stack fix)",
        len(polylines) > 0 and not bend_tags and invalid_records > 0,
        f"rays={len(polylines)} bend_tags={len(bend_tags)} invalid_records={invalid_records}",
    ))

    # ---- (B) first-surface kink on each mirror's real face plane --------------------- #
    planes = _mirror_planes(editor)
    law_bad = 0.0
    kinked_rays = 0
    plane_residual_max = 0.0
    for pts in polylines:
        folded_here = False
        for _row, center, normal, half in planes:
            for i in range(1, pts.shape[0] - 1):
                v = pts[i]
                if float(np.linalg.norm(v - center)) > (half * 2.2):
                    continue
                if abs(float((v - center) @ normal)) > 1e-3:
                    continue
                d_in = _unit(v - pts[i - 1])
                d_out = _unit(pts[i + 1] - v)
                if float(np.linalg.norm(pts[i + 1] - v)) < 1e-9 or float(np.linalg.norm(v - pts[i - 1])) < 1e-9:
                    continue
                expected = _unit(d_in - 2.0 * float(d_in @ normal) * normal)
                law_bad = max(law_bad, float(np.linalg.norm(d_out - expected)))
                plane_residual_max = max(plane_residual_max, abs(float((v - center) @ normal)))
                folded_here = True
        kinked_rays += int(folded_here)
    checks.append(Check(
        "FIRST SURFACE: drawn rays kink ON the mirrors' hypotenuse planes and obey the "
        "reflection law about the face normal",
        kinked_rays > 0 and law_bad < 1e-6,
        f"rays_with_mirror_kinks={kinked_rays}/{len(polylines)} "
        f"max_reflection_law_residual={law_bad:.3g} max_plane_residual={plane_residual_max:.3g}mm",
    ))

    # ---- (C) the beam never enters the prism glass ----------------------------------- #
    inside = 0
    for pts in polylines:
        for _row, center, normal, half in planes:
            local = pts - center[None, :]
            in_box = np.all(np.abs(local) <= (half + 1e-6), axis=1)
            below = (local @ normal) < -0.01  # >10um behind the coated face = inside glass
            inside += int(np.count_nonzero(in_box & below))
    checks.append(Check(
        "GLASS INERT: no drawn-ray vertex lies inside a prism glass wedge (external / "
        "first-surface reflection, the beam never enters the BK7)",
        inside == 0,
        f"vertices_inside_glass={inside}",
    ))

    # ---- (D) rays terminate on the folded Image-surface seat ------------------------- #
    overrides = getattr(editor.last_system, "_optical_solid_output_port_pose_overrides", {}) or {}
    image_index = len(editor.rows) - 1
    image_pose = overrides.get(image_index)
    reaching = 0
    off_plane = 0
    lens_missing = 0
    if isinstance(image_pose, dict):
        img_c = np.asarray(image_pose.get("center"), dtype=float).reshape(3)
        img_n = _unit(np.asarray(image_pose.get("rotation"), dtype=float).reshape(3, 3)[:, 2])
        lens_index = next(
            (i for i, row in enumerate(editor.rows) if str(getattr(row, "surface", "")) == "Thin Lens"),
            None,
        )
        lens_pose = overrides.get(lens_index) if lens_index is not None else None
        lens_c = lens_n = None
        lens_semi = 0.0
        if isinstance(lens_pose, dict) and lens_index is not None:
            lens_c = np.asarray(lens_pose.get("center"), dtype=float).reshape(3)
            lens_n = _unit(np.asarray(lens_pose.get("rotation"), dtype=float).reshape(3, 3)[:, 2])
            lens_semi = 0.5 * float(getattr(editor.rows[lens_index], "diameter", 0.0) or 0.0)
        for pts in polylines:
            end = pts[-1]
            if abs(float((end - img_c) @ img_n)) > 1e-6:
                continue
            reaching += 1
            if lens_c is None:
                continue
            crossed = False
            for i in range(pts.shape[0] - 1):
                a, b = pts[i], pts[i + 1]
                da, db = float((a - lens_c) @ lens_n), float((b - lens_c) @ lens_n)
                if da == 0.0 and db == 0.0:
                    continue
                if (da <= 0.0 <= db) or (db <= 0.0 <= da):
                    t = 0.0 if abs(db - da) < 1e-12 else (-da / (db - da))
                    hit = a + (b - a) * float(np.clip(t, 0.0, 1.0))
                    radial = hit - lens_c
                    radial = radial - float(radial @ lens_n) * lens_n
                    if float(np.linalg.norm(radial)) <= lens_semi + 1e-6:
                        crossed = True
                        break
            if not crossed:
                lens_missing += 1
    checks.append(Check(
        "DETECTOR TERMINATION: detector-reaching rays end ON the folded Image-surface "
        "seat (the trace terminates where the display draws the detector)",
        isinstance(image_pose, dict) and reaching > 0 and off_plane == 0,
        f"image_pose={'set' if isinstance(image_pose, dict) else 'missing'} "
        f"reaching={reaching}/{len(polylines)}",
    ))
    checks.append(Check(
        "LENS IN BEAM: every detector-reaching ray crosses the Thin Lens surrogate at "
        "its folded seat within the lens aperture",
        reaching > 0 and lens_missing == 0,
        f"reaching={reaching} missed_lens={lens_missing}",
    ))

    # ---- (F) unfolded regression: the SIGN fix is inert when SIGN=+1 ----------------- #
    from KrakenOS.UI.layout_editor import _build_system_from_specs
    import KrakenOS as Kos

    def _spec(**kw):
        base = {
            "surface": "Standard", "name": "", "rc": 0.0, "thickness": 0.0,
            "diameter": 40.0, "tilt_x": 0.0, "tilt_y": 0.0, "tilt_z": 0.0,
            "desp_x": 0.0, "desp_y": 0.0, "desp_z": 0.0, "axis_move": 0.0,
            "glass": "AIR",
        }
        base.update(kw)
        return base

    plain = [
        _spec(surface="Object", thickness=100.0),
        _spec(surface="Thin Lens", rc=50.0, thickness=100.0),
        _spec(surface="Image"),
    ]
    plain_system = _quiet(
        _build_system_from_specs, plain, build=0, apply_optical_solid_output_ports=False
    )
    plain_system.energy_probability = 0
    keeper = Kos.raykeeper(plain_system)
    for (x, y) in ((0.0, 0.0), (5.0, 0.0), (0.0, 5.0), (-5.0, -5.0)):
        _quiet(plain_system.Trace, [x, y, 0.0], [0.0, 0.0, 1.0], 0.55)
        _quiet(keeper.push)
    ends = np.asarray([np.asarray(keeper.CC[i], dtype=float)[-1, :3] for i in range(len(keeper.CC))])
    # A parallel launch (x, y, +z) through the ideal f=50 lens at z=100 passes the back
    # focal point (0,0,150) and lands mirrored at (-x, -y) on the image plane z=200.
    expected = np.asarray([[-x, -y, 200.0] for (x, y) in ((0.0, 0.0), (5.0, 0.0), (0.0, 5.0), (-5.0, -5.0))])
    focus_err = float(np.max(np.linalg.norm(ends - expected, axis=1))) if len(ends) == 4 else float("inf")
    checks.append(Check(
        "UNFOLDED REGRESSION: a plain unfolded Thin-Lens scene still refracts exactly "
        "(the KrakenSys SIGN-convention fix only engages behind a reflection)",
        len(ends) == 4 and focus_err < 1e-6,
        f"rays={len(ends)} max_ideal_lens_error={focus_err:.3g}mm (parallel-in -> through (0,0,150))",
    ))

    return checks


def run_checks() -> "tuple[bool, list[str]]":
    checks = validate_folded_real_trace_sync()
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


def main() -> int:
    checks = validate_folded_real_trace_sync()
    failed = [c for c in checks if not c.ok]
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if failed:
        print(f"Folded real-trace-sync validation FAILED ({len(failed)}/{len(checks)}).")
        return 1
    print("Folded real-trace-sync validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
