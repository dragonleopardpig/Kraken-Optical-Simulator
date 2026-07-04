"""Display-free guard for bugs/0222 -- the promoted RA mirror is an EXTERNAL (first-surface)
reflection, so its glass is optically inert: the first-order MODEL must be AIR (a pure fold), in
SYNC with the drawn external reflection, and the 1:1 relay must read magnification exactly 1.0.

Background (flag_20260704_195234, the user): the UI clearly draws an EXTERNAL reflection (the ray
bounces off the coated hypotenuse and never enters the glass), but the code modelled the mirror as
a 40 mm BK7 plate the ray transits (INTERNAL) -- out of sync. That glass shift moved the conjugate
and made the 1:1 AZ85 relay read ~1.16-1.40X. bugs/0222: ``_ra_mirror_fold_is_external_reflection``
decides the case from the GEOMETRY (which face the beam reaches first -- a Mirror entry face =
external, a Transmit entry face = internal), and the flat-plate equivalent + the paraxial reference
use AIR for an external fold (keeping glass only for a genuine internal-reflection prism). The
magnification is then read at the CONJUGATE (not the overshot prescription Image row).

  (A) EXTERNAL: the detection returns True for the AZ85 RA mirrors (the coated hypotenuse faces the
      beam -- the beam bounces off it without entering glass).
  (B) MAG = 1.0: the folded 1:1 relay reports paraxial magnification 1.0 (was ~1.4), matching a RAY
      TRACE of the straight-equivalent at the focus (1.000, external air; not 1.16 as BK7 glass).
  (C) IN SYNC: the first-order straight-equivalent's RA-mirror plate is AIR, not the BK7 substrate --
      the same pure reflection the display draws (no rays through glass).
  (D) WIRED: the detection + the external->air branches + the conjugate-magnification are present.

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_ra_mirror_external_reflection
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import io
from dataclasses import dataclass
from pathlib import Path

import numpy as np

import KrakenOS as Kos
from KrakenOS.UI.layout_editor import _build_system_from_specs
from KrakenOS.UI.services.paraxial_tools import _row_is_promoted_mirror_fold
from KrakenOS.UI.validate_open3d_second_mirror_incoming_axis_placement import (
    _build_single_mirror,
    _build_two_mirror,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_PARAXIAL_SRC = PROJECT_ROOT / "KrakenOS" / "UI" / "services" / "paraxial_tools.py"
_MAG_SRC = PROJECT_ROOT / "KrakenOS" / "UI" / "services" / "layout_scene_bundle_display.py"


@dataclass
class Check:
    check: str
    ok: bool
    detail: str


def _editor(builder):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor, _ = builder()
        editor._build_preview_system_rays_bundle(update_state=True)
    return editor


def _ray_traced_mag(editor):
    """Trace off-axis chief rays through the straight-equivalent and read the mag at the focus."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        focus = float(editor._paraxial_image_plane_z())
        eq = editor._folded_optical_solid_straight_equivalent_rows()
        specs = editor._serializable_specs_for_rows(eq)
        system = _build_system_from_specs([dict(s) for s in specs], apply_optical_solid_output_ports=False)
        system.energy_probability = 0
        rays = Kos.raykeeper(system)
        heights = [4.0, 8.0]
        for h in heights:
            system.Trace([0.0, float(h), 0.0], [0.0, 0.0, 1.0], 0.55)
            rays.push()
        X, Y, Z, L, M, N = [np.asarray(v, float) for v in rays.pick(-1)]
    yf = [float(y + (focus - z) * (m / n)) for y, z, m, n in zip(Y, Z, M, N)]
    return abs(yf[0] / heights[0]) if len(yf) >= 1 and np.isfinite(yf[0]) else float("nan")


def validate_ra_mirror_external_reflection() -> list[Check]:
    checks: list[Check] = []
    e2 = _editor(_build_two_mirror)
    e1 = _editor(_build_single_mirror)

    # ===================== (A) EXTERNAL detection ================================== #
    mirror_rows = [i for i, r in enumerate(e2.rows) if _row_is_promoted_mirror_fold(r)]
    ext = [e2._ra_mirror_fold_is_external_reflection(i) for i in mirror_rows]
    a_ok = len(mirror_rows) == 2 and all(v is True for v in ext)
    checks.append(Check(
        "the AZ85 RA mirrors are detected as EXTERNAL reflection (coated hypotenuse faces the beam)",
        a_ok, f"mirror rows={mirror_rows} external={ext} (expect all True)",
    ))

    # ===================== (B) MAG = 1.0 (paraxial + ray) ========================== #
    mag2 = e2._current_finite_paraxial_magnification()
    mag1 = e1._current_finite_paraxial_magnification()
    ray2 = _ray_traced_mag(e2)
    b_ok = (
        mag2 is not None and abs(float(mag2) - 1.0) < 0.02
        and mag1 is not None and abs(float(mag1) - 1.0) < 0.02
        and np.isfinite(ray2) and abs(ray2 - 1.0) < 0.02
    )
    checks.append(Check(
        "the folded 1:1 relay reports magnification 1.0 (external air), matching the ray trace at the focus",
        b_ok,
        f"paraxial mag: single={None if mag1 is None else round(float(mag1),4)} two={None if mag2 is None else round(float(mag2),4)}; "
        f"ray-traced mag (two, at focus)={round(ray2,4)} (all expect 1.0 -- BK7 glass would be ~1.16-1.40)",
    ))

    # ===================== (C) IN SYNC: straight-equivalent plate is AIR =========== #
    eq = e2._folded_optical_solid_straight_equivalent_rows()
    mirror_glass = [str(r.glass).upper() for i, r in enumerate(eq) if _row_is_promoted_mirror_fold(e2.rows[i])] if eq else []
    # the flattened mirror rows keep the same index; check every non-object/image BK7-substrate row is now AIR
    bk7_plates = [str(r.glass).upper() for r in (eq or []) if str(r.glass).upper() not in ("AIR", "")]
    c_ok = eq is not None and len(bk7_plates) == 0
    checks.append(Check(
        "the first-order straight-equivalent draws the RA mirror as AIR (a pure fold), in sync with the external display",
        c_ok, f"non-AIR plates in the straight-equivalent={bk7_plates} (expect none -- the external mirror is air)",
    ))

    # ===================== (D) INTERNAL contrast (the flipped prism) =============== #
    # The user's worry: "if I flip the RA mirror so the hypotenuse faces down, will the code know to
    # enter the glass, reflect off the second surface, and account for the index?" Drive the REAL
    # method with only the incoming beam redirected so it DESCENDS onto mirror-2's +Z cathetus
    # (a Transmit entry face) instead of the coated hypotenuse -- a genuine internal reflection. The
    # geometry-driven detection must flip to False (keep the glass), proving the model follows the
    # drawing whichever way the prism sits (not hard-wired to "always external").
    import KrakenOS.UI.services.folded_sequential_fold as _fsf
    _orig_center = _fsf.promoted_mirror_world_center

    def _center_above_second(specs, i):
        if i == mirror_rows[0]:  # place the PREVIOUS fold vertex directly above mirror-2 -> beam goes -Z
            m2 = np.asarray(_orig_center(specs, mirror_rows[1]), dtype=float).reshape(3)
            return (float(m2[0]), float(m2[1]), float(m2[2]) + 1000.0)
        return _orig_center(specs, i)

    _fsf.promoted_mirror_world_center = _center_above_second
    try:
        internal = e2._ra_mirror_fold_is_external_reflection(mirror_rows[1])
    finally:
        _fsf.promoted_mirror_world_center = _orig_center
    d_ok = internal is False
    checks.append(Check(
        "a beam descending onto the cathetus (Transmit) face is detected as INTERNAL -- keep the glass (the flipped-prism case)",
        d_ok, f"internal-orientation detection={internal} (expect False -- the beam enters glass, index matters)",
    ))

    # ===================== (E) WIRED ============================================== #
    try:
        psrc = _PARAXIAL_SRC.read_text(encoding="utf-8")
    except Exception:
        psrc = ""
    try:
        msrc = _MAG_SRC.read_text(encoding="utf-8")
    except Exception:
        msrc = ""
    wired = (
        "def _ra_mirror_fold_is_external_reflection" in psrc
        and "_ra_mirror_fold_is_external_reflection(idx) is not False" in psrc  # straight-equivalent branch
        and "_ra_mirror_fold_is_external_reflection(index) is not False" in psrc  # reference-walk branch
        and "f / (object_principal - f)" in msrc  # conjugate magnification
    )
    checks.append(Check(
        "the external-reflection detection + the external->air branches + the conjugate magnification are wired",
        wired,
        f"detection={'def _ra_mirror_fold_is_external_reflection' in psrc} "
        f"straight_eq_branch={'_ra_mirror_fold_is_external_reflection(idx) is not False' in psrc} "
        f"ref_branch={'_ra_mirror_fold_is_external_reflection(index) is not False' in psrc} "
        f"conjugate_mag={'f / (object_principal - f)' in msrc}",
    ))

    return checks


def run_checks() -> tuple[bool, list[str]]:
    checks = validate_ra_mirror_external_reflection()
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


def main() -> int:
    checks = validate_ra_mirror_external_reflection()
    failed = [c for c in checks if not c.ok]
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if failed:
        raise SystemExit(1)
    print("RA-mirror-external-reflection validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
