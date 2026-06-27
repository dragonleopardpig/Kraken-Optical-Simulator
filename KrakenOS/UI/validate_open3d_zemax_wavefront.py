"""Display-free guard for the Zemax wavefront -> Zernike -> spot engine (augmented surrogate).

A first-order Thin-Lens surrogate has no aberrations; the real (black-box) lens ships a
Zemax wavefront-map (OPD) export. ``services/zemax_wavefront.py`` reads it, fits Zernikes,
and turns the wavefront into the transverse ray aberration (the real geometric spot) -- the
engine that will let the surrogate blur like the real lens.

This guard pins (headless, numpy only):

  * SYNTHETIC (no file needed): a pure-defocus OPD is recovered by the fit (defocus is the
    dominant Zernike, ~0 residual) and gives a non-zero spot that scales with the defocus.
  * REAL DATA (``attachment/Lens/15056/wavefront/Mag1.0.txt``, skipped cleanly if absent):
    parse RMS == the report's RMS (0.0286 waves) and PV == 0.0893; the Zernike fit residual
    is small; the wavefront-derived spot is physically sane (0.5-30 um, sub-Airy, non-zero).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_zemax_wavefront

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from KrakenOS.UI.services.zemax_wavefront import (
    _zernike_term,
    fit_zernike,
    parse_zemax_wavefront_map,
    wavefront_to_spot,
)

_REAL_MAP = Path(__file__).resolve().parents[2] / "attachment" / "Lens" / "15056" / "wavefront" / "Mag1.0.txt"


def _circular_mask(n: int):
    yy, xx = np.mgrid[0:n, 0:n]
    c = (n - 1) / 2.0
    return np.hypot(yy - c, xx - c) <= (n / 2.0 - 0.5)


def _synthetic_defocus_opd(n: int, amp_waves: float):
    """A pure-defocus OPD (normalized Zernike Z(2,0)) over a circular pupil, in waves."""
    mask = _circular_mask(n)
    yy, xx = np.mgrid[0:n, 0:n]
    c = (n - 1) / 2.0
    half = n / 2.0 - 0.5
    rho = np.hypot(yy - c, xx - c) / half
    theta = np.arctan2(yy - c, xx - c)
    opd = amp_waves * _zernike_term(2, 0, rho, theta)
    return np.where(mask, opd, np.nan), mask


def _check_synthetic(failures: list[str], notes: list[str]) -> None:
    mask = _circular_mask(64)
    opd, mask = _synthetic_defocus_opd(64, 0.10)
    fit = fit_zernike(opd, mask, n_terms=15)
    di = next(i for i, t in enumerate(fit["terms"]) if t == (2, 0))
    if abs(float(fit["coeffs"][di]) - 0.10) > 0.01:
        failures.append(f"SYNTH: defocus coeff {float(fit['coeffs'][di]):.3g} != 0.10")
    if fit["terms"][int(np.argmax(np.abs(fit["coeffs"])))] != (2, 0):
        failures.append("SYNTH: defocus is not the dominant Zernike term")
    if fit["residual_rms_waves"] > 0.01:
        failures.append(f"SYNTH: pure-defocus fit residual too large ({fit['residual_rms_waves']:.4g})")

    spot_a = wavefront_to_spot(opd, mask, wavelength_um=0.55, exit_pupil_radius_mm=12.5, exit_pupil_to_image_mm=290.0)
    opd2, _ = _synthetic_defocus_opd(64, 0.20)
    spot_b = wavefront_to_spot(opd2, mask, wavelength_um=0.55, exit_pupil_radius_mm=12.5, exit_pupil_to_image_mm=290.0)
    if not (spot_a["rms_um"] > 1e-3):
        failures.append("SYNTH: defocus produced ~zero spot")
    if not np.isclose(spot_b["rms_um"], 2.0 * spot_a["rms_um"], rtol=0.05):
        failures.append(f"SYNTH: spot did not scale with defocus ({spot_a['rms_um']:.3g} -> {spot_b['rms_um']:.3g})")
    notes.append(f"synthetic: 0.10-wave defocus -> spot {spot_a['rms_um']:.2f} um, fit recovers it")


def _check_real(failures: list[str], notes: list[str]) -> None:
    if not _REAL_MAP.exists():
        notes.append("SKIP real data: Lens/15056 wavefront map unavailable")
        return
    wf = parse_zemax_wavefront_map(_REAL_MAP)
    if wf is None:
        failures.append("REAL: parse returned None")
        return
    if wf.get("header_rms_waves") is not None and abs(wf["rms_waves"] - wf["header_rms_waves"]) > 0.002:
        failures.append(f"REAL: parsed RMS {wf['rms_waves']:.4f} != header {wf['header_rms_waves']:.4f}")
    if wf.get("header_pv_waves") is not None and abs(wf["pv_waves"] - wf["header_pv_waves"]) > 0.002:
        failures.append(f"REAL: parsed PV {wf['pv_waves']:.4f} != header {wf['header_pv_waves']:.4f}")

    fit = fit_zernike(wf["opd_waves"], wf["mask"])
    if fit["residual_rms_waves"] > 0.1 * fit["input_rms_waves"]:
        failures.append(f"REAL: Zernike residual too high ({fit['residual_rms_waves']:.4g} of {fit['input_rms_waves']:.4g})")

    epd = float(wf.get("exit_pupil_diameter_mm") or 25.0)
    spot = wavefront_to_spot(
        wf["opd_waves"], wf["mask"], wavelength_um=float(wf["wavelength_um"]),
        exit_pupil_radius_mm=epd / 2.0, exit_pupil_to_image_mm=290.97,
    )
    airy_um = 0.61 * float(wf["wavelength_um"]) / 0.04324
    if not (0.5 < spot["rms_um"] < 30.0):
        failures.append(f"REAL: implausible wavefront spot RMS {spot['rms_um']:.3g} um")
    if spot["rms_um"] >= airy_um:
        failures.append(f"REAL: a 0.029-wave wavefront gave a SUPER-diffraction spot ({spot['rms_um']:.2g} >= Airy {airy_um:.2g})")
    di = next(i for i, t in enumerate(fit["terms"]) if t == (2, 0))
    notes.append(
        f"real: RMS {wf['rms_waves']:.4f}w PV {wf['pv_waves']:.4f}w | fit residual {100*fit['residual_rms_waves']/fit['input_rms_waves']:.1f}% "
        f"| defocus {float(fit['coeffs'][di]):+.4f}w | spot {spot['rms_um']:.2f}um < Airy {airy_um:.2f}um"
    )


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    _check_synthetic(failures, notes)
    _check_real(failures, notes)
    return (not failures), (failures + notes)


def main() -> int:
    passed, messages = run_checks()
    for message in messages:
        print(f"  - {message}")
    if not passed:
        print("[FAIL] Zemax wavefront -> Zernike -> spot engine")
        return 1
    print("[PASS] Zemax wavefront parses, fits Zernikes, and yields a real (sub-Airy) spot")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
