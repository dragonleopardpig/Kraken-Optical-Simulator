"""Display-free guard for bugs/0238 -- the "two image and detector plane" on a folded periscope.

flag_20260706_113107_413 on the two-fold AZ85: after a folded object-distance solve the user saw
TWO image/detector planes on the sensor arm. Root: in Non-Sequential Preview (use_folded=False) the
surface curves are built on the UNFOLDED +Z axis, but `_fold_promoted_mirror_table_row_targets`
(bugs/0188) carries the detector TARGET onto the promoted-mirror branch. The stale unfolded
kind="image" curve is then left behind on the straight axis -- a SECOND image/detector plane off
the beam. The two-arm splitter path already drops its superseded terminal curves; the single
promoted-mirror fold did not.

Fix: after the single-mirror fold carries the detector target, drop any kind="image" surface curve
that no longer coincides with a folded detector (`_drop_unfolded_superseded_image_curves`). A curve
that STILL sits on its detector -- a plain sequential scene, or a folded-sequential curve built
folded -- is within tolerance and kept, so only the genuine off-beam duplicate is removed.

  (A) NO DUPLICATE: on the two-fold after fov_solve(object,thickness,55,55) the bundle has exactly
      ONE detector target and NO stale kind="image" curve off the folded detector.
  (B) COINCIDENT KEPT: the drop keeps an image curve that sits on the detector and removes only the
      diverged (off-beam) one.
  (C) STILL IMAGES: rays still reach the (single) detector after the drop.
  (D) WIRED: `_build_scene_bundle` calls `_drop_unfolded_superseded_image_curves` and the method is
      defined on the mixin.

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_folded_duplicate_image_plane
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


def _image_curves(bundle):
    return [c for c in (getattr(bundle, "surface_curves", None) or [])
            if str(getattr(c, "kind", "") or "").strip().lower() == "image"]


def _centroid(curve):
    pts = getattr(curve, "points_world", None)
    if pts is None:
        pts = getattr(curve, "points", None)
    arr = np.asarray(pts, dtype=float).reshape(-1, 3)
    return arr.mean(axis=0)


def validate_folded_duplicate_image_plane() -> list[Check]:
    checks: list[Check] = []
    editor = _two_fold_editor()
    qe = QuickEstimationService(SimpleNamespace(
        editor=editor, quick_estimation_var=SimpleNamespace(get=lambda: True)))

    _quiet(qe.fov_solve, "object", "thickness", 55.0, 55.0, None)
    _s, _r, bundle = _quiet(editor._build_preview_system_rays_bundle, update_state=True)

    dets = [t for t in (getattr(bundle, "targets", None) or []) if getattr(t, "is_detector", False)]
    det_c = np.asarray(dets[0].center_world, dtype=float).reshape(3) if dets else None
    # a "stale" image curve is a kind="image" curve sitting far from the folded detector
    stale = [c for c in _image_curves(bundle)
             if det_c is not None and float(np.linalg.norm(_centroid(c) - det_c)) > 1.0]
    off_axis = det_c is not None and float(np.hypot(det_c[0], det_c[1])) > 5.0  # detector is folded off +Z

    checks.append(Check(
        "NO DUPLICATE: one detector target, no stale kind=image curve off the folded detector",
        len(dets) == 1 and not stale and off_axis,
        f"detectors={len(dets)} stale_image_curves={len(stale)} "
        f"detector={None if det_c is None else np.round(det_c, 1)} off_axis={off_axis}",
    ))

    # ---- (B) the drop keeps a coincident curve, removes the diverged one -------------------- #
    det = SimpleNamespace(is_detector=True, center_world=np.array([100.0, 0.0, 50.0]))
    coincident = SimpleNamespace(kind="image", row_index=9,
                                 points_world=np.array([[100.0, -5.0, 50.0], [100.0, 5.0, 50.0]]))
    diverged = SimpleNamespace(kind="image", row_index=9,
                               points_world=np.array([[0.0, -5.0, 60.0], [0.0, 5.0, 60.0]]))
    synth = SimpleNamespace(targets=[det], surface_curves=[coincident, diverged])
    drop = getattr(editor, "_drop_unfolded_superseded_image_curves", None)
    if callable(drop):
        dropped = drop(synth)
        kept = list(synth.surface_curves)
        kept_coincident = any(c is coincident for c in kept)
        removed_diverged = not any(c is diverged for c in kept)
    else:
        dropped, kept_coincident, removed_diverged = 0, False, False
    checks.append(Check(
        "COINCIDENT KEPT: the drop removes the diverged image curve and keeps the coincident one",
        dropped == 1 and kept_coincident and removed_diverged,
        f"dropped={dropped} kept_coincident={kept_coincident} removed_diverged={removed_diverged}",
    ))

    # ---- (C) the scene still images ---------------------------------------------------------- #
    ends = (np.asarray([np.asarray(p.points_world, dtype=float)[-1][:3] for p in bundle.ray_paths])
            if bundle.ray_paths else np.zeros((0, 3)))
    reach = int((np.linalg.norm(ends - det_c, axis=1) < 5.0).sum()) if det_c is not None and len(ends) else 0
    checks.append(Check(
        "STILL IMAGES: rays still reach the single folded detector after the drop",
        det_c is not None and reach >= 8,
        f"rays={len(bundle.ray_paths)} within5mm={reach}",
    ))

    # ---- (D) wiring -------------------------------------------------------------------------- #
    from KrakenOS.UI.services.layout_scene_bundle_display import LayoutSceneBundleDisplayMixin

    build_src = inspect.getsource(LayoutSceneBundleDisplayMixin._build_scene_bundle)
    wired = (
        "_drop_unfolded_superseded_image_curves" in build_src
        and hasattr(LayoutSceneBundleDisplayMixin, "_drop_unfolded_superseded_image_curves")
    )
    checks.append(Check(
        "WIRED: _build_scene_bundle calls the drop and the method is defined on the mixin",
        wired,
        f"called={'_drop_unfolded_superseded_image_curves' in build_src} "
        f"defined={hasattr(LayoutSceneBundleDisplayMixin, '_drop_unfolded_superseded_image_curves')}",
    ))
    return checks


def run_checks() -> "tuple[bool, list[str]]":
    checks = validate_folded_duplicate_image_plane()
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


def main() -> int:
    checks = validate_folded_duplicate_image_plane()
    failed = [c for c in checks if not c.ok]
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if failed:
        raise SystemExit(1)
    print("Folded duplicate-image-plane validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
