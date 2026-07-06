"""Display-free guard for bugs/0217 -- a folded promoted-mirror scene whose LAST fold mirror
sits right before the image must draw its detector (and terminate its rays) at the PHYSICS
focus (where the outgoing cone actually converges), NOT a fold-mirror plate past it.

bugs/0243 rework: the outcome now holds NATIVELY. The preview traces the REAL folded system,
the folded Image-surface seat sits at the true prescription station (the off-beam exemption
keeps a reached fold mirror's thickness in the follower walk), and the paraxial machinery
solves on the matching straight-equivalent -- so after ``snap_detector_to_image_plane`` the
on-axis cone focuses stigmatically ON the drawn detector with NO reconcile snap involved.
`_reconcile_folded_image_to_ray_convergence` is retired from the pipeline (the method stays
for tooling).

  (A) TWO-MIRROR: after the paraxial snap the on-axis cone CONVERGES on the drawn detector
      (target == sensor-reaching endpoint centroid, tight RMS).
  (B) NATIVE: the shipped bundle is byte-identical with the reconcile shadowed to a no-op --
      nothing snaps the detector any more (the raw geometry is already right).
  (C) SINGLE-MIRROR: the sensor-reaching endpoints already sit on the drawn detector.
  (D) WIRED: the reconcile method still exists but the preview pipeline no longer calls it.

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_folded_image_snaps_to_ray_convergence
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import io
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from KrakenOS.UI.validate_open3d_second_mirror_incoming_axis_placement import (
    _build_single_mirror,
    _build_two_mirror,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SCENE_TOOLS_SRC = PROJECT_ROOT / "KrakenOS" / "UI" / "services" / "three_d_scene_tools.py"
_MIN_OVERSHOOT_MM = 2.0   # matches _FOLDED_FOCUS_MIN_OVERSHOOT_MM
_TIGHT_RMS_MM = 0.05      # a real on-axis point focus


@dataclass
class Check:
    check: str
    ok: bool
    detail: str


def _bundle(builder, *, snap=False):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor, _ = builder()
        if snap:
            editor._build_preview_system_rays_bundle(update_state=True)
            editor.snap_detector_to_image_plane()
        system, _rays, bundle = editor._build_preview_system_rays_bundle(update_state=True)
    return editor, bundle


def _detector(bundle):
    for t in getattr(bundle, "targets", None) or []:
        if getattr(t, "is_detector", False):
            return np.asarray(getattr(t, "center_world"), dtype=float).reshape(3)
    return None


def _image_seat(editor):
    overrides = getattr(editor.last_system, "_optical_solid_output_port_pose_overrides", {}) or {}
    pose = overrides.get(len(editor.rows) - 1)
    if not isinstance(pose, dict):
        return None, None
    center = np.asarray(pose.get("center"), dtype=float).reshape(3)
    normal = np.asarray(pose.get("rotation"), dtype=float).reshape(3, 3)[:, 2]
    norm = float(np.linalg.norm(normal))
    return center, (normal / norm if norm > 1e-12 else normal)


def _onaxis_endpoints(bundle, editor=None):
    """On-axis rays that actually REACH the sensor plane (the folded Image seat) --
    vignetted rays terminate mid-scene and must not pollute the focus statistics."""
    seat_c = seat_n = None
    if editor is not None:
        seat_c, seat_n = _image_seat(editor)
    ends = []
    for p in getattr(bundle, "ray_paths", None) or []:
        pw = np.asarray(getattr(p, "points_world", None), dtype=float)
        if pw.ndim == 2 and pw.shape[0] >= 2 and pw.shape[1] >= 3 and np.linalg.norm(pw[0][:3]) <= 1.0:
            end = pw[-1, :3]
            if seat_c is not None and abs(float((end - seat_c) @ seat_n)) > 1e-6:
                continue
            ends.append(end)
    return np.asarray(ends, dtype=float) if ends else None


def validate_folded_image_snaps_to_ray_convergence() -> list[Check]:
    checks: list[Check] = []

    # ============ (A) TWO-MIRROR: after the snap the cone converges ON the detector === #
    _e2, b2 = _bundle(_build_two_mirror, snap=True)
    det2 = _detector(b2)
    ends2 = _onaxis_endpoints(b2, editor=_e2)
    two_ok = False
    two_detail = "no detector / no sensor-reaching on-axis rays"
    if det2 is not None and ends2 is not None and len(ends2) >= 8:
        ctr = ends2.mean(0)
        # transverse RMS about the endpoint centroid (all 3 axes -- a point focus is tight in all)
        rms = float(np.sqrt(((ends2 - ctr) ** 2).sum(1).mean()))
        gap = float(np.linalg.norm(det2 - ctr))
        two_ok = gap < 1.0 and rms < _TIGHT_RMS_MM
        two_detail = (
            f"detector=({det2[0]:.2f},{det2[1]:.2f},{det2[2]:.2f}) ray-endpoint centroid="
            f"({ctr[0]:.2f},{ctr[1]:.2f},{ctr[2]:.2f}) gap={gap*1000:.1f}um endpoint RMS={rms*1000:.1f}um "
            f"(expect gap<1mm AND RMS<{_TIGHT_RMS_MM*1000:.0f}um -- the cone focuses ON the detector)"
        )
    checks.append(Check(
        "two-mirror: after the paraxial snap the on-axis cone converges ON the drawn detector",
        two_ok, two_detail,
    ))

    # ============ (B) NATIVE: the geometry needs NO reconcile snap ===================== #
    # Re-build with the reconcile shadowed to a no-op: bugs/0243 -- the detector must be
    # IDENTICAL, proving the outcome is native geometry, not a display snap.
    native = False
    native_detail = "unavailable"
    try:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            editor_raw, _ = _build_two_mirror()
            editor_raw._build_preview_system_rays_bundle(update_state=True)
            editor_raw.snap_detector_to_image_plane()
            editor_raw._reconcile_folded_image_to_ray_convergence = lambda _b: 0
            _s, _r, b_raw = editor_raw._build_preview_system_rays_bundle(update_state=True)
        det_raw = _detector(b_raw)
        if det_raw is not None and det2 is not None:
            moved = float(np.linalg.norm(det2 - det_raw))
            native = moved < 1e-6
            native_detail = (
                f"reconcile-shadowed detector=({det_raw[0]:.2f},{det_raw[1]:.2f},{det_raw[2]:.2f}) vs "
                f"shipped: moved {moved:.6f} mm (expect 0 -- nothing snaps the detector any more)"
            )
    except Exception as exc:  # noqa: BLE001
        native_detail = f"raised {exc!r}"
    checks.append(Check(
        "NATIVE: the detector position does not depend on the retired reconcile snap",
        native, native_detail,
    ))

    # ===================== (C) SINGLE-MIRROR: endpoints on the detector =============== #
    _e1, b1 = _bundle(_build_single_mirror)
    det1 = _detector(b1)
    ends1 = _onaxis_endpoints(b1, editor=_e1)
    one_ok = False
    one_detail = "no detector / no sensor-reaching on-axis rays"
    if det1 is not None and ends1 is not None and len(ends1) >= 8:
        gap = float(np.linalg.norm(det1 - ends1.mean(0)))
        one_ok = gap < 1.0
        one_detail = (
            f"single-mirror detector=({det1[0]:.2f},{det1[1]:.2f},{det1[2]:.2f}) coincides with its "
            f"sensor-reaching endpoints (gap={gap*1000:.1f}um)"
        )
    checks.append(Check(
        "single-mirror: the drawn detector coincides with the traced endpoints natively",
        one_ok, one_detail,
    ))

    # ===================== (D) WIRED ================================================= #
    try:
        src = _SCENE_TOOLS_SRC.read_text(encoding="utf-8")
    except Exception:
        src = ""
    wired = (
        "def _reconcile_folded_image_to_ray_convergence" in src
        and "self._reconcile_folded_image_to_ray_convergence(scene_bundle)" not in src
    )
    checks.append(Check(
        "WIRED: the reconcile method exists for tooling but the preview no longer calls it (bugs/0243)",
        wired,
        f"method_def={'def _reconcile_folded_image_to_ray_convergence' in src} "
        f"call_absent={'self._reconcile_folded_image_to_ray_convergence(scene_bundle)' not in src}",
    ))

    return checks


def run_checks() -> tuple[bool, list[str]]:
    """Penta-phase entry point: ``(passed, notes)`` where notes are the failures."""
    checks = validate_folded_image_snaps_to_ray_convergence()
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


def main() -> int:
    checks = validate_folded_image_snaps_to_ray_convergence()
    failed = [c for c in checks if not c.ok]
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if failed:
        raise SystemExit(1)
    print("Folded-image-snaps-to-ray-convergence validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
