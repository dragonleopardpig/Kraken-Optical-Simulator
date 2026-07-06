"""Display-free guard for bugs/0239 -- the "still 2 image and detector plane" MESH twin.

flag_20260706_130527_037 on the two-fold AZ85: after a 55x55 FOV solve-for-thickness the user still
saw TWO image/detector planes. bugs/0238 removes the stale kind="image" CURVE left on the unfolded
+Z axis, but the drawn sensor DISC is a kind="image" surface MESH, built at the LENS-only paraxial
image plane (`_paraxial_image_plane_z`). The flattened mirror plates add a glass path the lens-only
first order ignores, so the real ray waist -- where `_fold_promoted_mirror_table_row_targets` seats
the detector target and where the cone actually converges -- sits ~a plate-thickness (AZ85: ~20 mm)
beyond it. The disc then floats off the beam: the SECOND image/detector plane, the MESH sibling of
the curve 0238 drops.

Fix: after `_reconcile_folded_image_to_ray_convergence` finalises the detector on the ray waist,
re-seat every diverged kind="image" MESH onto that folded detector
(`_reseat_superseded_image_meshes_to_folded_detector`). Re-seating (not dropping) keeps the solid
sensor disc the unfolded scene draws, now coincident with the detector + rays -- display follows
physics. It runs only on a FOLDED scene (detector carried off +Z) for a disc that has diverged, so
plain / sequential layouts keep every mesh byte-identical, and it recomputes the shift from the live
centroid each pass so it is idempotent (cache-safe across a Show-Rays rebuild).

  (A) COINCIDENT: on the two-fold after fov_solve(object,thickness,55,55) the single kind="image"
      MESH centroid coincides (<=1 mm) with the folded off-axis detector target and the ray waist.
  (B) RESEAT SYNTH: the method moves a diverged image mesh onto an off-axis detector and leaves a
      coincident one untouched (returns 1).
  (C) ON-AXIS NO-OP: with an ON-axis detector (plain sequential) the reseat touches nothing.
  (D) STILL IMAGES: rays still reach the single folded detector / disc.
  (E) WIRED: `_build_preview_system_rays_bundle` calls the reseat AFTER
      `_reconcile_folded_image_to_ray_convergence`, and the method is defined on the mixin.

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_folded_image_mesh_reseat
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import inspect
import io
from dataclasses import dataclass
from types import SimpleNamespace

import numpy as np

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


class _FakeMesh:
    """Minimal stand-in for a pyvista PolyData: a settable ``points`` array."""

    def __init__(self, points):
        self.points = np.asarray(points, dtype=float)


def _image_meshes(bundle):
    return [m for m in (getattr(bundle, "surface_meshes", None) or [])
            if str(getattr(m, "kind", "") or "").strip().lower() == "image"]


def _mesh_centroid(item):
    mesh = getattr(item, "mesh", None)
    pts = getattr(mesh, "points", None) if mesh is not None else None
    arr = np.asarray(pts, dtype=float).reshape(-1, 3)
    return arr.mean(axis=0) if arr.size else None


def validate_folded_image_mesh_reseat() -> list[Check]:
    checks: list[Check] = []
    editor = _two_fold_editor()
    qe = QuickEstimationService(SimpleNamespace(
        editor=editor, quick_estimation_var=SimpleNamespace(get=lambda: True)))

    _quiet(qe.fov_solve, "object", "thickness", 55.0, 55.0, None)
    _s, _r, bundle = _quiet(editor._build_preview_system_rays_bundle, update_state=True)

    dets = [t for t in (getattr(bundle, "targets", None) or []) if getattr(t, "is_detector", False)]
    det_c = np.asarray(dets[0].center_world, dtype=float).reshape(3) if dets else None
    off_axis = det_c is not None and float(np.hypot(det_c[0], det_c[1])) > 5.0
    img_meshes = _image_meshes(bundle)
    centroid = _mesh_centroid(img_meshes[0]) if img_meshes else None
    gap = (float(np.linalg.norm(centroid - det_c))
           if centroid is not None and det_c is not None else float("inf"))

    checks.append(Check(
        "COINCIDENT: the single image MESH sits on the folded off-axis detector",
        len(img_meshes) == 1 and off_axis and gap <= 1.0,
        f"image_meshes={len(img_meshes)} off_axis={off_axis} "
        f"gap={round(gap, 3)}mm detector={None if det_c is None else np.round(det_c, 1)}",
    ))

    # ---- (B) synthetic reseat: diverged moves, coincident untouched ------------------------- #
    reseat = getattr(editor, "_reseat_superseded_image_meshes_to_folded_detector", None)
    det = SimpleNamespace(is_detector=True, center_world=np.array([100.0, 0.0, 50.0]))
    coincident = SimpleNamespace(kind="image", mesh=_FakeMesh([[100.0, -5.0, 50.0], [100.0, 5.0, 50.0]]))
    diverged = SimpleNamespace(kind="image", mesh=_FakeMesh([[0.0, -5.0, 60.0], [0.0, 5.0, 60.0]]))
    synth = SimpleNamespace(targets=[det], surface_meshes=[coincident, diverged])
    if callable(reseat):
        moved = reseat(synth)
        new_div = _mesh_centroid(diverged)
        new_coin = _mesh_centroid(coincident)
        diverged_on_det = new_div is not None and float(np.linalg.norm(new_div - np.array([100.0, 0.0, 50.0]))) <= 1.0
        coincident_still = new_coin is not None and float(np.linalg.norm(new_coin - np.array([100.0, 0.0, 50.0]))) <= 1.0
    else:
        moved, diverged_on_det, coincident_still = 0, False, False
    checks.append(Check(
        "RESEAT SYNTH: the diverged image mesh moves onto the off-axis detector, coincident untouched",
        moved == 1 and diverged_on_det and coincident_still,
        f"reseated={moved} diverged_on_det={diverged_on_det} coincident_still={coincident_still}",
    ))

    # ---- (C) on-axis detector => plain sequential => NO-OP ----------------------------------- #
    axis_det = SimpleNamespace(is_detector=True, center_world=np.array([0.0, 0.0, 50.0]))
    plain = SimpleNamespace(kind="image", mesh=_FakeMesh([[0.0, -5.0, 60.0], [0.0, 5.0, 60.0]]))
    synth_axis = SimpleNamespace(targets=[axis_det], surface_meshes=[plain])
    if callable(reseat):
        moved_axis = reseat(synth_axis)
        untouched = float(np.linalg.norm(_mesh_centroid(plain) - np.array([0.0, 0.0, 60.0]))) <= 1e-9
    else:
        moved_axis, untouched = 1, False
    checks.append(Check(
        "ON-AXIS NO-OP: an on-axis (plain sequential) detector leaves every image mesh byte-identical",
        moved_axis == 0 and untouched,
        f"reseated={moved_axis} untouched={untouched}",
    ))

    # ---- (D) the scene still images ---------------------------------------------------------- #
    ends = (np.asarray([np.asarray(p.points_world, dtype=float)[-1][:3] for p in bundle.ray_paths])
            if bundle.ray_paths else np.zeros((0, 3)))
    reach = int((np.linalg.norm(ends - det_c, axis=1) < 5.0).sum()) if det_c is not None and len(ends) else 0
    checks.append(Check(
        "STILL IMAGES: rays still reach the single folded detector after the reseat",
        det_c is not None and reach >= 8,
        f"rays={len(bundle.ray_paths)} within5mm={reach}",
    ))

    # ---- (E) wiring -------------------------------------------------------------------------- #
    # bugs/0243: the preview traces the REAL folded system, so the drawn image disc and
    # the traced Image surface coincide NATIVELY (checks A-D above) -- the reconcile and
    # the reseat calls are retired from the pipeline; the helper stays defined for tools.
    from KrakenOS.UI.services.layout_scene_bundle_display import LayoutSceneBundleDisplayMixin
    from KrakenOS.UI.services.three_d_scene_tools import ThreeDSceneToolsMixin

    preview_src = inspect.getsource(ThreeDSceneToolsMixin._build_preview_system_rays_bundle)
    reconcile_at = preview_src.find("self._reconcile_folded_image_to_ray_convergence(")
    reseat_at = preview_src.find("self._reseat_superseded_image_meshes_to_folded_detector(")
    wired = (
        reconcile_at < 0 and reseat_at < 0
        and hasattr(LayoutSceneBundleDisplayMixin, "_reseat_superseded_image_meshes_to_folded_detector")
    )
    checks.append(Check(
        "WIRED: the preview no longer reseats/reconciles (bugs/0243: disc == trace natively); helper still defined",
        wired,
        f"reconcile_call_at={reconcile_at} reseat_call_at={reseat_at} (expect both -1) "
        f"defined={hasattr(LayoutSceneBundleDisplayMixin, '_reseat_superseded_image_meshes_to_folded_detector')}",
    ))
    return checks


def run_checks() -> "tuple[bool, list[str]]":
    checks = validate_folded_image_mesh_reseat()
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


def main() -> int:
    checks = validate_folded_image_mesh_reseat()
    failed = [c for c in checks if not c.ok]
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if failed:
        raise SystemExit(1)
    print("Folded image-mesh reseat validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
