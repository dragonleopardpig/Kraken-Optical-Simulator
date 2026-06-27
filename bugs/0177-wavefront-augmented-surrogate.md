# 0177 — FEATURE: wavefront-augmented surrogate (real Zemax OPD spot in the Spot map)

## Goal (option 2, step 2)

An ideal Thin-Lens ("Blackbox") surrogate is aberration-free, so its ray-traced spot is a
sub-diffraction point — not the real lens (bugs/0175 added the Airy circle to make that
obvious). When the vendor ships a Zemax **wavefront (OPD) map** (e.g.
`Lens/15056/wavefront/Mag1.0.txt`), the surrogate can show the REAL spot without the hidden
prescription. The engine for this is `services/zemax_wavefront.py` (bugs/0176); this wires it
into the Spot map.

## What it does

- **Attach:** right-click the image plane → **"Attach wavefront map…"** (only shown for a
  surrogate) picks a Zemax wavefront `.txt`; the path is stored on the first Thin-Lens row's
  `advanced['WavefrontMap']`. `'WavefrontMap'` is registered in `ADVANCED_SURFACE_FIELD_GROUPS`
  so it survives a `.py` save/reload (the 0093/0165 allowlist trap). **"Clear wavefront map"**
  drops it (and suppresses auto-detect via a `disabled` flag). Auto-detect: a single
  unambiguous `wavefront/Mag1.0.txt` under the layout's folder / a sibling `Lens/<id>/` is
  used transiently when nothing is attached.
- **Apply** (`_compute_spot_field_map_spec`): `parse_zemax_wavefront_map` + `wavefront_to_spot`
  (ε = −R·∇W). `R` (exit-pupil→image) is read from the sibling Zemax prescription report's
  `Exit Pupil Position` (−290.97 → 290.97 mm), else falls back to `exit_pupil_radius /
  on-axis NA`. The per-field RMS + scatter are replaced with the wavefront spot (on-axis OPD,
  so the same blob rides every field), and the Airy uses the **real** NA (`exit_pupil_radius /
  R`). Cache-keyed on the map path+mtime.
- **Verdict flip:** `_scene_surrogate_optics_info().reason` and the Spot-map label read
  **"✓ Wavefront-augmented surrogate (Zemax OPD, RMS x λ, on-axis)"** instead of the ideal
  warning.

## Result (real MV-150 surrogate + the real wavefront)

Ideal (focused): spot RMS ~0.1–1 µm (sub-diffraction). Augmented: **1.97 µm**, sitting
**inside the 7.75 µm Airy radius** (real working NA 0.043) — i.e. the genuine near-
diffraction-limited on-axis spot of a 0.0288 λ wavefront, matching Zemax.

## Caveat

The maps are **on-axis only** (0.00 mm field), so it's an on-axis-accurate first cut applied
uniformly across the field. True field-edge coma/astigmatism needs the per-field `spot
radius/` + `MTF/` folders. Read the augmented spot AT focus (snap first) — the OPD is the
at-focus residual.

## Guard

`validate_open3d_wavefront_augmented_surrogate` (display-free): ideal (~0) → augmented (~2 µm,
inside the Airy), verdict flip, and the `WavefrontMap` allowlist round-trip. Penta phase 169.
In-app eyeball owed (the attach dialog + the real blob in the Airy circle).
