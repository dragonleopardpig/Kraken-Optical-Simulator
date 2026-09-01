# 0680 — Additive scene sources keep the imaging chain (the om05a face-B arm)

## User architecture (0678 flag chain)
"it is symmetry 2-sided: each side should have 3 mirror surface assigned" /
"one FOV is looking at two object plane which are located at the side of the
50x50x1mm object (the 50x1mm surface)" / "I want the ray tracing same as
illustrated in attachment/Prism_Assembly.png".

## Root causes (three, stacked)

1. **A physical scene source replaced the imaging launch.**
   `_collect_scene_sources` (source_modeling.py) short-circuits to source-driven
   tracing whenever any enabled physical non-marker, non-coupled source exists —
   correct for stray-light layouts, fatal here: adding the face-B emitter
   dropped the imaging reference entirely, so the chain traced ZERO rays. (The
   0678 "retraction" of this claim was itself wrong: the corrected accounting —
   chain rays carry `source_id='source:0'` — CONFIRMED the kill, cleanly, in
   stage 1 of `bugs/0680_symmetric_b.py`.)

2. **My insertion anchor was a substring.** `"RA mirror 2" in row.name` matched
   the VIRTUAL station `'to camera (unfolded RA mirror 2)'` first, parking the B
   wedges mid-chain — where the sign-agnostic 0224 backward-line test folds the
   frame walk (reach 68 → 2). True end-insertion (immediately before the Image
   row) leaves the chain untouched: the final leg's beam line misses the B
   planes by ~275 mm.

3. **A diffuse face can't feed a distant stop efficiently.** A rectangle source
   spraying a fixed cone reached 3/200; the pupil direction tilts ~7° across the
   50 mm face.

## The fix (general, opt-in per spec)

- **`additive: True`** (scene_source_analysis.py
  `scene_source_spec_is_additive_to_imaging`): the source never short-circuits
  `_collect_scene_sources` and is excluded from `_build_scene_source_bundles`.
  Instead `_trace_additive_imaging_source_rays` (three_d_scene_tools.py, called
  from `_trace_preview_rays_folded_aware` after the imaging trace) traces its
  bundles non-sequentially INTO the same preview keeper via the new
  `append=True` mode of `_trace_preview_bundles` (no `rays.clean()`, field
  mapping extended, `clean=0` from the first bundle). Both arms display, census
  and record as ONE live bundle; the chain is byte-identical to the source-free
  scene (guard C5).
- **`aim_x/aim_y/aim_z`**: random-family sources re-centre every sampled cone on
  one world aim point (vectorized Rodrigues z→axis rotation preserves the
  cone's angular distribution) — importance sampling of the diffuse emission
  the stop would select.
- **`mirror_launch_plane_z`**: the definitive route for a symmetric second arm.
  The trace service stashes every imaging launch
  (`_last_imaging_launch_bundles`); the additive builder reflects it through
  the plane (z → 2·zp − z, n → −n) and bounds it to the physical face
  (radius_x/radius_y). The om05a prism trains mirror about z = −28.9
  (outer +5.35/−63.15, lower +2.6/−60.4), so arm B launches the chain's own
  calibrated bundle.

## Scene result (attachment/om05a_folded.py, promoted from om05a_symB_work.py)

- Chain: 243 paths / 68 reach — unchanged with the source AND the three
  end-pinned B wedges present.
- Face B: 81 physical rays (the y=0 slice of the mirrored launch, bounded to
  the 50×1 face at z=−57.8), threading all five B folds; 4 complete to the
  sensor strip.
- Both arms land tight strips on the ONE image plane (y=−11): arm A at
  z≈−20.0, arm B at z≈−10 (spread 0.5 mm) — "one FOV, two object planes".

## Finding: the lens seat rides arm A's axis (follow-up)

Measured: the arm-A strip images ON-axis (lens axis z≈−19.6 = the chain's
column-entry z), arm B rides ~19.6 mm off-axis through the shared stop → heavy
vignetting (4 vs 68 reachers) and the B strip near the sensor edge. The vendor
design centres the lens on the CAD leg (z=−28.9) so BOTH arms ride ±9.8 mm
symmetrically. Re-seating the lens there needs the 0672 focus calibration
redone — the named next step for image-quality parity between arms. The
central-field waist (140 µm at the row) is pinned as the regression floor in
guard B2 until then.

## Guards

- `validate_open3d_0680_additive_imaging_source` (penta phase 507,
  display-free, synthetic scene): the additive contract C1–C8 (no
  short-circuit, exclusion from the replace path, byte-identical chain,
  same-bundle coexistence, aim-point convergence, mirrored+bounded launch).
- `validate_open3d_0672_om05a_folded_scene` (phase 505) re-pinned to the REAL
  five-fold scene (it still pinned the pre-0678-swap display-fold scene): A1–A5
  structure incl. the B train + faceB spec, B1–B5 trace incl. both strips.

## Files

- KrakenOS/UI/scene_source_analysis.py — `scene_source_spec_is_additive_to_imaging`
- KrakenOS/UI/services/source_modeling.py — collect/build exclusions,
  `_build_additive_imaging_source_bundles`, `_source_spec_aim_point`,
  `_aim_source_cone_directions`
- KrakenOS/UI/services/trace_preview.py — `append=` mode + launch stash
- KrakenOS/UI/services/trace_preview_sampling.py — mixin wrapper threads `append`
- KrakenOS/UI/services/three_d_scene_tools.py — the post-imaging additive trace
  hook; additive bundles join `_isolated_scene_source_records`
- bugs/0680_symmetric_b.py — staged experiment/builder;
  bugs/0680_probe_{frames,aim,census}.py — diagnostics
