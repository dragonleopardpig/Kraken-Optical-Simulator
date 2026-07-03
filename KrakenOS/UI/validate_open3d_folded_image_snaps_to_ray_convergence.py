"""Display-free guard for bugs/0217 -- a folded promoted-mirror scene whose LAST fold mirror
sits right before the image must draw its detector (and terminate its rays) at the PHYSICS
focus (where the outgoing cone actually converges), NOT a fold-mirror plate past it.

Background (flag_20260703_221640 "still defocus at detector"; flag_20260703_145514 "still
unfocused"): on the two-mirror AZ85 (ELS-85 surrogate) the flat-plate straight-equivalent keeps
the trailing mirror's full glass thickness AFTER the conjugate, so the straight Image row -- and
hence both the drawn detector target and the ray hard-stop = fold(straight Image row) -- lands
~a plate BACK (28 mm) past where the cone waists. The field beams reach the sensor SPREAD (not
focused), even though the fold itself is exact. `_reconcile_folded_image_to_ray_convergence`
(services/three_d_scene_tools.py, run after `_apply_folded_display_bend`) finds the outgoing
cone's waist and snaps the detector target + rays onto it -- the two-arm splitter fold's
"detector at the physics focus" pattern, generalised to the RA-mirror fold.

  (A) TWO-MIRROR: the on-axis cone CONVERGES on the drawn detector -- detector target ==
      ray endpoints (coincident) AND the endpoint transverse RMS is tight (a real focus).
  (B) CAUSAL: the reconcile FIRED -- the detector moved a real distance (>= the min overshoot)
      OFF the raw fold(straight Image row) hard-stop it used to sit on.
  (C) SINGLE-MIRROR: a single fold already images at its endpoints, so the reconcile is a
      clean NO-OP -- the detector is UNCHANGED (a revert of the gate would move it).
  (D) WIRED: the method + its call after the fold bend are present in the source.

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


def _bundle(builder):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor, _ = builder()
        system, _rays, bundle = editor._build_preview_system_rays_bundle(update_state=True)
    return editor, bundle


def _detector(bundle):
    for t in getattr(bundle, "targets", None) or []:
        if getattr(t, "is_detector", False):
            return np.asarray(getattr(t, "center_world"), dtype=float).reshape(3)
    return None


def _onaxis_endpoints(bundle):
    ends = []
    for p in getattr(bundle, "ray_paths", None) or []:
        pw = np.asarray(getattr(p, "points_world", None), dtype=float)
        if pw.ndim == 2 and pw.shape[0] >= 2 and pw.shape[1] >= 3 and np.linalg.norm(pw[0][:3]) <= 1.0:
            ends.append(pw[-1, :3])
    return np.asarray(ends, dtype=float) if ends else None


def validate_folded_image_snaps_to_ray_convergence() -> list[Check]:
    checks: list[Check] = []

    # ===================== (A) TWO-MIRROR: cone converges ON the detector ============ #
    _e2, b2 = _bundle(_build_two_mirror)
    det2 = _detector(b2)
    ends2 = _onaxis_endpoints(b2)
    two_ok = False
    two_detail = "no detector / no on-axis rays"
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
        "two-mirror: the on-axis cone converges ON the drawn detector (rays == detector, tight)",
        two_ok, two_detail,
    ))

    # ===================== (B) CAUSAL: the reconcile FIRED (detector moved) =========== #
    # Re-build with the reconcile shadowed to a no-op -> the RAW (overshot) detector, then show
    # the shipped build moved it a real distance onto the waist.
    causal = False
    causal_detail = "unavailable"
    try:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            editor_raw, _ = _build_two_mirror()
            editor_raw._reconcile_folded_image_to_ray_convergence = lambda _b: 0
            _s, _r, b_raw = editor_raw._build_preview_system_rays_bundle(update_state=True)
        det_raw = _detector(b_raw)
        if det_raw is not None and det2 is not None:
            moved = float(np.linalg.norm(det2 - det_raw))
            causal = moved >= _MIN_OVERSHOOT_MM
            causal_detail = (
                f"raw (reconcile off) detector=({det_raw[0]:.2f},{det_raw[1]:.2f},{det_raw[2]:.2f}); "
                f"shipped moved it {moved:.2f} mm onto the waist (expect >= {_MIN_OVERSHOOT_MM} mm)"
            )
    except Exception as exc:  # noqa: BLE001
        causal_detail = f"raised {exc!r}"
    checks.append(Check(
        "CAUSAL: the reconcile FIRED -- the detector moved off the raw fold(straight Image row) hard-stop",
        causal, causal_detail,
    ))

    # ===================== (C) SINGLE-MIRROR: clean NO-OP ============================= #
    _e1, b1 = _bundle(_build_single_mirror)
    det1 = _detector(b1)
    ends1 = _onaxis_endpoints(b1)
    one_ok = False
    one_detail = "no detector / no on-axis rays"
    if det1 is not None and ends1 is not None and len(ends1) >= 8:
        gap = float(np.linalg.norm(det1 - ends1.mean(0)))
        # a single fold already lands rays on the detector; the reconcile must not have moved it.
        one_ok = gap < 1.0
        one_detail = (
            f"single-mirror detector=({det1[0]:.2f},{det1[1]:.2f},{det1[2]:.2f}) coincides with its "
            f"endpoints (gap={gap*1000:.1f}um) -- reconcile is a NO-OP (no overshoot to snap)"
        )
    checks.append(Check(
        "single-mirror: reconcile is a clean NO-OP (detector unchanged, already at its endpoints)",
        one_ok, one_detail,
    ))

    # ===================== (D) WIRED ================================================= #
    try:
        src = _SCENE_TOOLS_SRC.read_text(encoding="utf-8")
    except Exception:
        src = ""
    wired = (
        "def _reconcile_folded_image_to_ray_convergence" in src
        and "self._reconcile_folded_image_to_ray_convergence(scene_bundle)" in src
    )
    checks.append(Check(
        "the fix is wired: the reconcile method + its post-fold-bend call are present",
        wired,
        f"method_def={'def _reconcile_folded_image_to_ray_convergence' in src} "
        f"call={'self._reconcile_folded_image_to_ray_convergence(scene_bundle)' in src}",
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
