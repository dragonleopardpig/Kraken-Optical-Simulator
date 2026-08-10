# 0605 — The last 9 "stray pencils at the detector" were missed rays clipped in the pad ring (FIXED)

Flag `flag_20260810_164247_396` (second complaint, the SECOND flag on these pencils
after bugs/0601): *"still have some stray rays at detector"* — pencils reaching the
detector that are not at the 9 focused field points.

## Measured on the LIVE display bundle (the harness lesson)

The first analysis censused `_build_preview_system_rays_bundle(sampling_mode=None)` —
573 paths including a 2^8 = 256-branch TIR ghost forest inside the S6 splitter — and
concluded the pencils were deep ghosts (bugs/0604 weighted their display; kept as a
defensive invariant). **Wrong bundle.** The LIVE refresh
(`build_inspector_refresh`) traces 558 paths with ZERO re-split lineages — termination
census identical to the user's recorded flag state (282 no_next_intersection /
143 target_termination / 17 missed_image / 116 aperture_stop_vignette).

On that live bundle, post 55×55 solve, the drawn tails ending on the sensor plane:

- 143 × `target_termination`, r ≤ 14.9 — the 9 field foci. Real arrivals.
- **9 × `missed_image`, r 14.9–18.7 — one per field.** These are the flagged pencils.

## Root cause — TWO mechanisms produced the same fake arrival

1. **The 0601 pad-disc clip** truncated pass-through tails within `1.15 ×
   half-diagonal` of the centre — a DISC. The 23×23 sensor's half-side is 11.5 but
   its half-diagonal is 16.26, so the disc (18.74) swallows tails passing BESIDE the
   glass.
2. **The engine itself terminates a `missed_image` ray ON the image plane** — that is
   what the status means: it reached the plane outside the glass. The clip rightly
   never touches a ray that ENDS on the plane, so those 9 tails died on the plane
   natively, reading as arrival pencils however the clip behaved. (This is why the
   first fix attempt — rectangle clip alone — measured 143+9 unchanged.)

A ray the engine says MISSED must visibly miss.

## Fix

- `detector_planes_for_hard_stop` carries the target's in-plane axes and active
  half-extents; `_clip_polyline_at_detector_planes` tests pass-through crossings
  against the true RECTANGLE (2% + 0.05 mm slop), disc only as the no-dims fallback.
  `use_board_limit` callers (draw-suppressed branches, diffuse scatter —
  bugs/0182/0506) keep the generous radial board; arrivals keep their cap.
- `bounded_ray_points_for_scene_display` extends a `missed_image` terminal per the
  bugs/0553 escaped-tail doctrine (scene-envelope exit length, R_LMN sign
  reconciliation, 75 mm stub on suppressed branches) — gated to exactly the
  fake-arrival geometry: the terminal point lies on a known detector plane BESIDE its
  glass rectangle. An inside-the-glass termination or a plane-less miss is left alone.

Verified on the live bundle: on-sensor tails after the fix = 143 target_termination
only; the 9 missed rays fly visibly past the sensor edge. Rendered top-view snapshot
confirms.

Guard: phase 458 (`validate_open3d_0605_pass_by_rays_miss_the_glass`) — rectangle vs
pad-ring clip mechanics, arrival-cap immunity, board-limit fallback, and the plane
tuples carrying the rectangle fields.
