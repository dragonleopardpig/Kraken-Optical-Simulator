"""Display-free guard for bugs/0240 -- the "lens surrogate shifted" off the folded beam.

flag_20260706_130527_037 on the two-fold AZ85: after a 55x55 FOV solve-for-thickness the imaging
lens (Blackbox Group 1/2, drawn as Thin Lens rows) appeared shifted OFF the ray path while its lens
surface MESH sat on the beam. Root: in Non-Sequential Preview every surface curve is built through
`_row_layout_polylines`; the Standard/Aperture rows return their FULL 3-D world outline (folded by the
system transform), but the Thin-Lens branch routes through `thin_lens_glyph_polyline(..., project_fn=
_project_xy)`, which applied the folded world transform and then DISCARDED the folded world X (it kept
only ``(world_z, world_y)`` and lifted the 2-D projection back at x=0). The glyph was therefore
stranded on the straight +Z axis while the mesh + rays folded onto the +X branch.

Fix: when the glyph's transform genuinely folds it off the +Z axis (max |world_x| > 1 mm) and a
project_fn is supplied (the real 3-D display path), return the FULL 3-D world outline -- exactly as the
Standard-surface curve path does -- so the drawn lens follows the beam. On-axis layouts keep the
byte-identical 2-D projection, and the 2-D controller callers (no project_fn) are untouched.

  (A) LENS ON BEAM: on the two-fold after fov_solve(object,thickness,55,55) every kind="thin_lens"
      surface CURVE is off the +Z axis and coincides with its own row's folded surface MESH.
  (B) GLYPH 3-D WHEN FOLDED: `thin_lens_glyph_polyline` with an off-axis fold transform + a project_fn
      returns a 3-column world outline whose folded X is preserved.
  (C) GLYPH 2-D ON-AXIS: with a project_fn but an on-axis transform the glyph stays on the 2-column
      projection path (plain layouts unchanged).
  (D) STILL IMAGES: rays still reach the single folded detector.

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_folded_thin_lens_curve_on_beam
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import io
from dataclasses import dataclass
from types import SimpleNamespace

import numpy as np

from KrakenOS.UI.layout_plot_controller import thin_lens_glyph_polyline
from KrakenOS.UI.services.quick_estimation import QuickEstimationService
from KrakenOS.UI.validate_open3d_two_fold_image_arm_follow import _two_fold_editor


@dataclass
class Check:
    check: str
    ok: bool
    detail: str


def _quiet(fn, *args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        return fn(*args, **kwargs)


def _curve_centroid(curve):
    pts = getattr(curve, "points_world", None)
    if pts is None:
        return None
    arr = np.asarray(pts, dtype=float).reshape(-1, 3)
    return arr.mean(axis=0) if arr.size else None


def _row_mesh_centroid(bundle, row_index):
    for m in (getattr(bundle, "surface_meshes", None) or []):
        if getattr(m, "row_index", None) == row_index and not getattr(m, "is_body", False):
            mesh = getattr(m, "mesh", None)
            pts = getattr(mesh, "points", None) if mesh is not None else None
            if pts is not None:
                arr = np.asarray(pts, dtype=float).reshape(-1, 3)
                if arr.size:
                    return arr.mean(axis=0)
    return None


def validate_folded_thin_lens_curve_on_beam() -> list[Check]:
    checks: list[Check] = []
    editor = _two_fold_editor()
    qe = QuickEstimationService(SimpleNamespace(
        editor=editor, quick_estimation_var=SimpleNamespace(get=lambda: True)))

    _quiet(qe.fov_solve, "object", "thickness", 55.0, 55.0, None)
    _s, _r, bundle = _quiet(editor._build_preview_system_rays_bundle, update_state=True)

    thin_curves = [c for c in (getattr(bundle, "surface_curves", None) or [])
                   if str(getattr(c, "kind", "") or "").strip().lower() == "thin_lens"]
    per_lens = []
    for c in thin_curves:
        ri = getattr(c, "row_index", None)
        cc = _curve_centroid(c)
        mc = _row_mesh_centroid(bundle, ri) if isinstance(ri, int) else None
        off_axis = cc is not None and float(np.hypot(cc[0], cc[1])) > 5.0
        coincident = cc is not None and mc is not None and float(np.linalg.norm(cc - mc)) <= 3.0
        per_lens.append((ri, off_axis, coincident,
                         None if cc is None else np.round(cc, 1),
                         None if mc is None else np.round(mc, 1)))
    all_on_beam = len(per_lens) >= 2 and all(o and k for _ri, o, k, _cc, _mc in per_lens)
    checks.append(Check(
        "LENS ON BEAM: every thin_lens curve is off the +Z axis and sits on its own folded mesh",
        all_on_beam,
        "; ".join(f"row={ri} off_axis={o} on_mesh={k} curve={cc} mesh={mc}"
                  for ri, o, k, cc, mc in per_lens) or "no thin_lens curves",
    ))

    # ---- (B) glyph returns full 3-D world when the transform folds it off-axis -------------- #
    lens = SimpleNamespace(diameter=20.0, rc=50.0, desp_z=0.0, desp_y=0.0)
    fold = np.eye(4)
    fold[:3, :3] = np.array([[0.0, 0.0, 1.0], [0.0, 1.0, 0.0], [-1.0, 0.0, 0.0]])  # local z-axis -> world +x
    fold[:3, 3] = np.array([90.0, 0.0, 200.0])
    folded_glyph = thin_lens_glyph_polyline(lens, 0.0, transform=fold, project_fn=lambda z, y: (z, y))
    folded_3d = folded_glyph is not None and folded_glyph.ndim == 2 and folded_glyph.shape[1] == 3
    folded_x = float(np.max(np.abs(folded_glyph[:, 0]))) if folded_3d else 0.0
    checks.append(Check(
        "GLYPH 3-D WHEN FOLDED: an off-axis fold transform yields a 3-column outline with the folded X",
        folded_3d and folded_x > 5.0,
        f"shape={None if folded_glyph is None else folded_glyph.shape} max_abs_x={round(folded_x, 1)}",
    ))

    # ---- (C) on-axis transform + project_fn stays on the 2-D projection path ----------------- #
    axis_tf = np.eye(4)
    axis_tf[2, 3] = 125.0  # translate along +Z only -> world_x stays 0
    axis_glyph = thin_lens_glyph_polyline(lens, 0.0, transform=axis_tf, project_fn=lambda z, y: (z, y))
    axis_2d = axis_glyph is not None and axis_glyph.ndim == 2 and axis_glyph.shape[1] == 2
    checks.append(Check(
        "GLYPH 2-D ON-AXIS: an on-axis transform keeps the 2-column projection (plain layouts unchanged)",
        axis_2d,
        f"shape={None if axis_glyph is None else axis_glyph.shape}",
    ))

    # ---- (D) the scene still images ---------------------------------------------------------- #
    dets = [t for t in (getattr(bundle, "targets", None) or []) if getattr(t, "is_detector", False)]
    det_c = np.asarray(dets[0].center_world, dtype=float).reshape(3) if dets else None
    ends = (np.asarray([np.asarray(p.points_world, dtype=float)[-1][:3] for p in bundle.ray_paths])
            if bundle.ray_paths else np.zeros((0, 3)))
    reach = int((np.linalg.norm(ends - det_c, axis=1) < 5.0).sum()) if det_c is not None and len(ends) else 0
    checks.append(Check(
        "STILL IMAGES: rays still reach the single folded detector",
        det_c is not None and reach >= 8,
        f"rays={len(bundle.ray_paths)} within5mm={reach}",
    ))
    return checks


def run_checks() -> "tuple[bool, list[str]]":
    checks = validate_folded_thin_lens_curve_on_beam()
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


def main() -> int:
    checks = validate_folded_thin_lens_curve_on_beam()
    failed = [c for c in checks if not c.ok]
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if failed:
        raise SystemExit(1)
    print("Folded thin-lens curve-on-beam validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
