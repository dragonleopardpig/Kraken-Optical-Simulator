# 0190 — BUG: after 0189 the folded RA-mirror scene STILL shows a faint line at the mirror — the REFLECTED optical-axis guide ("Optical Axis 2") extends ~250 mm BACKWARD through the 45° hypotenuse

**Status: RESOLVED (one source-level fix, scoped to promoted-mirror FOLDED scenes only via the
same `scene_is_folded` gate bugs/0189 uses, so unfolded / plain / penta / beam-splitter layouts
stay byte-identical).**

Bug 0189 (commit `7353bdff`) removed TWO of the three "faint +Z line" contributors: the 29 blocked
pupil/field reference-ray stubs (Fix A) and the over-extended +Z **global** guide `axis:global`
(Fix B, clamped to the mirror at Z≈77). The user re-flagged the same visual ONE more time —
`attachment/recorded_bug_repros/flag_20260701_092025_358/`, captured 09:20, 9 min AFTER the 0189
commit at 09:11 — with description **"reflection still wrong at the hypotenuse."** The residual is a
THIRD, different display actor that 0189 never touched: the **reflected chief ray's traced optical
axis** ("Optical Axis 2").

## Root cause — measured headlessly on the live AZ85 bundle + confirmed against the flag's state.json

The flag's `state.json` records exactly two optical-axis actors (`optical_axis_actor_count: 2`):

```
axis:global            dotted_global_guide      X[0,0]      Z[-236.8, 76.9]   <- 0189 Fix B: correctly clamped to the mirror
axis:ray:124:segment:3 traced_chief_ray_segment X[-248.4, 370.8] Z[71.9, 71.9] <- THE RESIDUAL: a horizontal line at the
                                                                                  fold plane running 248 mm PAST the mirror
                                                                                  vertex (X=0) into empty space BEHIND it (-X)
```

`axis:ray:124:segment:3` is the reflected chief ray's folded optical axis. It runs along +X at the
fold-plane Z=71.9 — correct forward toward the detector (to X=+370) — but ALSO extends 248 mm to
**−X, out the BACK of the 45° hypotenuse**. That backward half is a faint dash-dot line crossing the
mirror surface: "reflection wrong at the hypotenuse."

**Why:** every traced `Optical Axis N` is drawn by `_dotted_axis_records_from_ray_path`, which calls
`_extended_axis_points(origin, direction, bounds)` → `origin ± 0.85·scene-span` in **BOTH**
directions. On a promoted-mirror fold the reflected +X branch makes X the largest scene extent
(span≈369 mm), so the reflected axis inflates ±≈314 mm about its origin — the backward half pokes
~250 mm behind the mirror. Measured on the real AZ85 bundle: all 418 reflected +X traced segments
carry a backward overhang of **−305 mm** behind their reflection point (`segment_start`).

Note the KEPT/drawn segment in the app is `axis:ray:124:segment:3`, whose `axis_role` is
**`between_surfaces`** (not `post_surface`) — so a fix must clamp ALL folded traced segments, not
just the terminal ones, or it would miss the exact flagged segment.

## Fix (one source-level change, folded-scene-scoped)

`KrakenOS/UI/open3d_inspector.py`:

- new `Kraken3DInspector._folded_traced_axis_forward_points(segment)` — projects the segment's two
  extended endpoints onto its propagation direction relative to `segment_start` (the reflection
  point); if one end runs BEHIND `segment_start` (negative projection) it replaces that end with
  `segment_start`, so the axis becomes a forward ray from the mirror. Returns `None` (leave
  untouched) for a segment already entirely forward of its start, or a degenerate zero-direction
  segment.
- `_optical_axis_records_for_3d` now computes `scene_is_folded` (the 0189 Fix B gate:
  `_folded_axis_incoming_fold_point_z()` is not None) and, right after the traced segments are
  deduped, clamps each one with the helper **only when `scene_is_folded`**. The clamped `points`
  propagate to both the drawn records and the rays-off cache. Unfolded scenes skip the block
  entirely, so penta / beam-splitter `Optical Axis 2` stay byte-identical.

AZ85 result: `axis:ray:124:segment:3` X[−252.7, 375.1] → **X[40.0, 375.1]** (starts at the prism
exit, X=40, and runs forward; the −X phantom behind the mirror is gone). Worst backward overhang
across all 418 reflected segments: −305.1 mm → **0.000 mm**.

## Guard

`KrakenOS/UI/validate_open3d_ra_mirror_reflected_axis_backward_extension.py` (standalone, NOT penta)
— binds the REAL helper (to a stub) and the REAL folded gate (to the live editor):

1. a synthetic reflected +X segment with a backward overhang clamps to its reflection point
   (0 overhang, no point behind it, forward end preserved);
2. a forward-only segment + a zero-direction segment are left untouched (`None`);
3. INTEGRATION: on the real traced AZ85 bundle every reflected +X segment overhangs ~305 mm behind
   the mirror BEFORE, and the real helper clamps every one to 0 mm AFTER;
4. the folded gate is not None for AZ85 (clamp runs) and None for `flat_mirror_45_deg.py` (clamp
   gated OFF → unfolded scenes byte-identical).

Sibling AZ85 guards (0185–0189) + `validate_machine_vision_azure_85_ra_mirror` /
`_surrogate` still PASS; `validate_open3d_optical_axis_guides` and
`validate_open3d_beam_splitter_transmit_and_second_axis` (the non-folded scenes most sensitive to
`_optical_axis_records_for_3d`) still PASS — confirming the folded gate leaves them byte-identical.

## In-app eyeball owed

The optical-axis guide is a VTK-only 3-D overlay (headless VTK render of this scene is
segfault-prone). The geometry is proven display-free: the reflected traced axis now starts at the
mirror/prism exit and runs only forward (+X) to the detector, with 0 mm poking behind the
hypotenuse. The user should fully quit + relaunch, confirm the faint line crossing the mirror is
gone (only the folded +X optics + the incoming +Z axis-to-the-mirror remain), and re-flag if not.
The separate "FOV 19.3, not 1×" magnification observation (from the 0189 flags) is not addressed
here.
