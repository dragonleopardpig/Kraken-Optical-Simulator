"""Display-free guard for bugs/0233 -- on a TWO-mirror periscope whose image row overshoots the
focus, the detector must snap onto the ray waist (where the camera STEP already sits), not stay
at the overshot image plane.

The flag (flag_20260705_180738, "Camera STEP and detector detached. Camera STEP at correct focus
position. Detector and image plane in defocus location."): the reconcile
(`_reconcile_folded_image_to_ray_convergence`, bugs/0217) that snaps the folded detector onto the
ray convergence NO-OPPED. Root: its axis orientation used ``mean((ends - ref) @ axis)``, which is
~0 when the rays END ON the detector plane (a periscope images a full plate past the focus, so
the endpoints ARE on the detector plane). With the projection ~0 its sign is float noise and
FLIPPED the axis against the beam; the outgoing-leg walk then captured nothing (legs == 0) and the
reconcile bailed, leaving the detector ~100 mm PAST the waist while the camera-track focus (camera
STEP) sat ON the waist.

Fix: orient the axis by the BEAM's FINAL-SEGMENT direction (``mean(pw[-1] - pw[-2])``), which is
robust regardless of where the endpoints land.

  (A) ROBUST ORIENTATION: for rays ending on the detector plane, the endpoint-vs-ref projection
      is ~0 (noise) while the final-segment direction is clearly signed along the beam.
  (B) INTEGRATED: a synthetic overshoot bundle (waist 50 mm before the endpoints, endpoints ~on
      the detector plane, normal along the beam so the OLD check would flip) -- the real reconcile
      now MOVES the detector onto the waist.
  (C) AZ85 UNCHANGED: the two-mirror AZ85 (images at its endpoints, no overshoot) is not spuriously
      moved -- its detector stays on the known folded focus.
  (D) WIRED: the final-segment orientation is present in source.

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_two_fold_detector_snaps_to_focus
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import inspect
import io
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import numpy as np

import KrakenOS.UI.validate_open3d_second_mirror_same_part_mirror_carryover as carryover
from KrakenOS.UI.services.three_d_scene_tools import ThreeDSceneToolsMixin
from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SRC = PROJECT_ROOT / "KrakenOS" / "UI" / "services" / "three_d_scene_tools.py"
# bugs/0243: the as-built two-fold AZ85 detector sits at the PRESCRIPTION seat -- the
# reconcile snap is retired from the preview (the fixture's stored gaps are honestly
# defocused until the user solves/snaps; after `snap_detector_to_image_plane` the cone
# focuses stigmatically ON the detector, guarded by validate_open3d_folded_image_snaps).
_KNOWN_AZ85_DETECTOR = np.asarray((181.374, 0.0, -62.05), dtype=float)


@dataclass
class Check:
    check: str
    ok: bool
    detail: str


def _quiet(fn, *args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        return fn(*args, **kwargs)


def _overshoot_bundle():
    """A converging cone that waists at z=50 and diverges to endpoints ~on the detector plane at
    z=100. A pre-fold vertex at z=-30 keeps the object launch out of the outgoing leg. Endpoints
    sit 0.1 mm BEFORE the plane so the OLD ``mean((ends-ref)@axis)`` is negative -> would flip the
    axis against the beam; the final-segment orientation must not."""
    rays = []
    n = 24
    for k in range(n):
        th = 2.0 * np.pi * k / n
        a, b = np.cos(th), np.sin(th)
        pts = np.asarray([
            [0.0, 0.0, 0.0],          # object launch (near origin)
            [0.0, 0.0, -30.0],        # a fold-back so the launch is excluded from the outgoing leg
            [2.0 * a, 2.0 * b, 40.0], # spread before the waist
            [0.0, 0.0, 50.0],         # the WAIST (all rays converge here)
            [-9.98 * a, -9.98 * b, 99.9],  # endpoint ~on the detector plane (z=100), 0.1mm before
        ], dtype=float)
        rays.append(SimpleNamespace(points_world=pts))
    detector = SimpleNamespace(
        center_world=np.asarray([0.0, 0.0, 100.0], dtype=float),
        normal_world=np.asarray([0.0, 0.0, 1.0], dtype=float),  # along the beam (OLD-flip risk)
        is_detector=True,
    )
    return SimpleNamespace(targets=[detector], ray_paths=rays), detector


def validate_two_fold_detector_snaps_to_focus() -> list[Check]:
    checks: list[Check] = []
    editor = _quiet(_build_editor, _AZ85)

    # ---- (A) robust orientation: endpoint projection ~0, segment direction clearly signed ---- #
    bundle, detector = _overshoot_bundle()
    ref = np.asarray(detector.center_world, dtype=float)
    axis = np.asarray(detector.normal_world, dtype=float)
    ends = np.asarray([r.points_world[-1] for r in bundle.ray_paths])
    endpoint_proj = float(np.mean((ends - ref) @ axis))
    seg_dir = np.mean(np.asarray([r.points_world[-1] - r.points_world[-2] for r in bundle.ray_paths]), axis=0)
    seg_proj = float(np.dot(seg_dir, axis))
    checks.append(Check(
        "ROBUST: endpoint-vs-ref projection is ~0 (noise) while the final-segment direction is clearly signed",
        abs(endpoint_proj) < 1.0 and abs(seg_proj) > 10.0,
        f"endpoint_proj={endpoint_proj:.3f} (~0, was the unreliable orient) seg_proj={seg_proj:.2f} (robust)",
    ))

    # ---- (B) integrated: the real reconcile MOVES the detector onto the waist --------------- #
    moved = editor._reconcile_folded_image_to_ray_convergence(bundle)
    det_after = np.asarray(detector.center_world, dtype=float)
    checks.append(Check(
        "INTEGRATED: the reconcile snaps the overshot detector onto the ray waist (z~50)",
        moved == 1 and abs(det_after[2] - 50.0) < 1.0,
        f"moved={moved} detector_after={np.round(det_after, 2)} (expect ~[0,0,50]; a no-op leaves it at 100)",
    ))

    # ---- (C) AZ85 (no overshoot) not spuriously moved --------------------------------------- #
    _quiet(carryover._promote_mirror2, editor)
    _s, _r, az_bundle = _quiet(editor._build_preview_system_rays_bundle, update_state=True)
    az_det = next(
        (np.asarray(t.center_world, dtype=float).reshape(3) for t in az_bundle.targets if getattr(t, "is_detector", False)),
        None,
    )
    checks.append(Check(
        "AZ85 UNCHANGED: the two-mirror AZ85 detector stays on its prescription seat (no spurious move)",
        az_det is not None and bool(np.allclose(az_det, _KNOWN_AZ85_DETECTOR, atol=0.5)),
        f"detector={None if az_det is None else np.round(az_det, 2)} (expect ~{np.round(_KNOWN_AZ85_DETECTOR, 1)})",
    ))

    # ---- (D) wiring ------------------------------------------------------------------------- #
    try:
        src = inspect.getsource(ThreeDSceneToolsMixin._reconcile_folded_image_to_ray_convergence)
    except Exception:
        src = ""
    wired = (
        "bugs/0233" in src
        and "pw[-1, :3] - pw[-2, :3]" in src
        and "seg_dir" in src
    )
    checks.append(Check(
        "WIRED: the reconcile orients its axis by the final-segment beam direction",
        wired,
        f"bugs/0233={'bugs/0233' in src} seg_dir={'seg_dir' in src}",
    ))
    return checks


def run_checks() -> "tuple[bool, list[str]]":
    checks = validate_two_fold_detector_snaps_to_focus()
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


def main() -> int:
    checks = validate_two_fold_detector_snaps_to_focus()
    failed = [c for c in checks if not c.ok]
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if failed:
        raise SystemExit(1)
    print("Two-fold-detector-snaps-to-focus validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
