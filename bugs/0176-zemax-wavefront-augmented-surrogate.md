# 0176 — Zemax wavefront -> Zernike -> real spot (wavefront-augmented surrogate engine)

## Why

A first-order Thin-Lens surrogate (the "Blackbox Group" lens) is aberration-free, so its
geometric spot collapses below the diffraction floor — not the real lens. But the real
black-box vendor lens ships **Zemax wavefront-map (OPD) exports**
(`attachment/Lens/15056/wavefront/Mag1.0.txt`, `Mag05X.txt`). That OPD *is* the real
aberration. This is the engine to turn it into a real spot, so the surrogate can be made to
blur like the real lens (option 2).

## Engine — `KrakenOS/UI/services/zemax_wavefront.py` (pure numpy)

- `parse_zemax_wavefront_map(path)` — reads the UTF-16 "Listing of Wavefront Map Data"
  export: the N×N OPD grid (waves), a circular pupil mask from the reported centre, plus
  wavelength / field / exit-pupil-diameter / RMS / PV. Zero-mean over the pupil. On the real
  map: **RMS 0.0288 waves (report 0.0286), PV 0.0893 (report 0.0893)** — verified.
- `fit_zernike(opd, mask, n_terms=37)` — least-squares Zernike fit (orthonormal, OSA radial
  polynomials, Noll-ish ordering). The unreliable outermost mask ring (partial-pixel pupil
  edge) is **excluded from the fit** (`rho<=edge_keep`), which drops the real lens's residual
  from 56% to **0.1%** (the wavefront is genuinely smooth — defocus +0.0284 + spherical
  +0.0038 dominate, on-axis).
- `wavefront_to_spot(opd, mask, *, wavelength_um, exit_pupil_radius_mm,
  exit_pupil_to_image_mm)` — transverse ray aberration **ε = -R·∇W**, taken on the smooth
  Zernike RECONSTRUCTION (so edge cells don't inflate the marginal-ray slopes). Real lens:
  **spot RMS 1.97 µm < Airy 7.70 µm** — physically sane (a 0.029-wave near-diffraction-
  limited wavefront gives a sub-Airy geometric spot, as it must).

## Guard / phase

`validate_open3d_zemax_wavefront`: a synthetic pure-defocus recovery (file-free) + the real
Lens/15056 map (parse RMS/PV match the report, ~0 residual, sane sub-Airy spot). Penta phase
168.

## Caveat (field dependence)

The wavefront maps are **on-axis only** (0.00 mm field). The interesting field aberrations
(coma/astigmatism at the edge) need per-field data — the `spot radius/`, `MTF/`, `field
curvature/`, `distortion/`, `lateral color/` folders carry that. A full field-dependent
augmented surrogate would interpolate the off-axis spot from those; this engine delivers the
on-axis wavefront -> spot today.

## Next step (UI wiring — not in this commit)

Associate a wavefront file with the surrogate row and feed `wavefront_to_spot` into the Spot
map so the augmented surrogate shows the real ~2 µm spot *inside* the Airy circle. See the
worker report for the proposed hook.
