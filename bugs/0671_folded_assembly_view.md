# 0671 — Folded Assembly View: the straight trace in the real CAD world

"proceed" on the 0670 follow-up: show the om05a's REAL folded geometry over the
verified straight trace. Generalises the two-arm display-fold (one +Y fold) to an
ordered list of fold planes per arm.

## Shipped

- `services/folded_display_compose.py`: `fold_polyline` places a chain-coordinate
  polyline by the arm's start frame (the device face's pose) then reflects the tail
  at each fold plane in order (crossing vertex inserted — the 0103 lesson, per ray,
  about the ACTUAL plane). Reflections are isometries: the folded display IS the
  traced physics, re-arranged (guard pins length equality to 1e-6).
- The fold spec is DATA (`display_fold_spec` in the layout settings, round-tripped):
  per-arm origin/frame/y_center/y_range/aperture_half + folds[{point, normal}] +
  `body_step` (the assembly STEP drawn as-is). om05a: 2 arms x 5 folds (outer
  prism, lower prism, centre prism, RA mirror 1+2 shared), all planes CAD-derived.
- **Aperture honesty:** the 54 mm FOV fields launch up to ±26.8 mm, but the prisms
  are 10.5 mm tall — `aperture_half` drops rays outside the device face, so the
  folded view carries only light the assembly physically can (567 of 819 rays
  dropped on the om05a; the straight view still shows the full-sensor sweep).
- UI: Actions → *Folded Assembly View…* (`open_folded_assembly_view`; pyvista
  window, the 0663-v1 pattern). Status reports rays/arms/body.

## Flag flag_20260831_135413_727 (same session), resolved

- **Camera orientation wrong** — REAL: my extracted SV25 STEP kept the assembly
  pose (mount facing −y); the glue expects the vendor convention (mount → −z).
  Re-extracted rotated; body now sits behind the sensor, mount toward the rays.
- **"Lens surrogate not matching lens body"** — measured NOT a defect: body z
  272.1–319.9 vs datums 275.4/314.9 = the symmetric 4.3 mm overhang of the real
  48.1 mm housing over the 39.5 mm optical span (0417 doctrine). The "stray disc"
  behind the barrel is the 48-926 FILTER (Ø50.8, visually identical to a datum disc).
- **"Image not covering the whole sensor" → "let's do a FOV 54x54"** — field set to
  the full sensor (±11.52 image = 53.6×53.6 object at the measured m 0.4298 ≈ the
  54×54 nominal; exactly 54.0 needs the object leg +2 mm — mechanical). 13 fields so
  the faces are sampled (±4.5/±8.9 land on the 9 mm faces). Physics finding: the
  sensor FOV is 54×54 but the PRISMS pass only ~10 mm of height per side — the two
  faces occupy two bands on the sensor; the rest sees fixture/background.

## Verified

Guard `validate_open3d_0671_folded_assembly_view` (penta phase 504): exact fold
sequences both arms, isometry, fold vertices at their components, aperture filter,
scene spec round-trip, real-ray compose (126+126 folded), sensor inside the camera
column, menu/verb/settings wiring. Renders eyeballed: the head-on view reproduces
the user's Prism_Assembly.png light path from the real traced rays.
