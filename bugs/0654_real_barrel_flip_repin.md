# 0654 — Flipping a real-barrel lens STEP detached it from its surrogate

**Flags (2026-08-27):** `flag_20260827_131010` "Original: lens is flipped." +
`flag_20260827_131036` "Flipped the lens, lens surrogate and body detached." — the
user swapped their Pyrite90 scene to the freshly imported #67-304 telecentric (0653),
the body arrived mount-end-first (the front=axial-max guess — the known 0373
ambiguity), and the flip verb then slid the body +94.49 mm down the axis into the
camera, leaving the surrogate discs floating.

## Root cause: two fixes branching differently on the same geometry

* `_lens_step_display_front_z` (0377) classifies the barrel by `body_span >
  1.6 × glass_span`: a REAL barrel (Edmund 15056; this telecentric: 164 mm body
  around 65.5 mm of glass) is registered by its AUTHORED BODY FACE on the front
  datum; the 0374 glass-centre pin is only for close barrels that track their glass.
* `_lens_step_flip_axial_shift` (0500) applied the glass-centre-preserving mirror
  UNCONDITIONALLY. On a face-pinned real barrel that "correction" faithfully
  preserves the glass's WRONG pre-flip station — the exact thing the user flips to
  fix — and displaces the body by the overhang asymmetry:
  (body_hi−gc)−(gc−body_lo) = (274.0−144.8)−(144.8−110.0) = **+94.49 mm**.

Without the shift, the flip (front_face max→min) seats the opposite body face on the
datum and the glass lands 387.4..452.9 — dead on the surrogate datums 385.4..458.6.

## Fix (general)

One shared module constant `_CLOSE_BARREL_RATIO = 1.6` now drives BOTH branches:
close barrel ⇒ glass is the registration (0374 pin + 0500 flip mirror, unchanged);
real barrel ⇒ body face is the registration and the flip shift is 0 (the 0373
"re-pins the OPPOSITE barrel end" promise). Measured: flip leaves the body span
byte-identical (385.40..549.41) with the datums inside; the ELS-85-class close
barrel keeps its exact 0500 mirror.

## Verified

Guard `validate_open3d_0654_real_barrel_flip_repin` (penta phase 490): pure stub
checks (asymmetric close barrel keeps the mirror = 4.0; the #67-304 numbers give 0;
unflipped 0; both methods reference the ONE ratio) + the real swap+flip scene
(body span unmoved, datums inside). Render eyeballed.

## Side find

`validate_open3d_lens_step_flip_direction` (phase 314) had been failing at HEAD —
its source check chased `front_face = "min" if reverse else "max"` in
`_transformed_imported_lens_step_mesh`, but 0568 moved the mapping into
`_lens_step_alignment_params`. Check repointed; phase 314 passes again (one of the
46 known baseline failures resolved).
