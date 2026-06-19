# 0096 — world_cone preview revolves the meridional fan (Ray Fan count not literal)

**Date:** 2026-06-19 (M90aPro)
**Branch:** nonseq-display-refactor
**Status:** FIXED — `validate_open3d_ray_fan_count` green; in-app confirm pending.
**Relates:** 0095 (same symptom, the *other* preview path).

## Symptom

After 0095 shipped, the user restarted and re-tested "Ray Fan count = 5" on the
machine-vision cube scene:
- 3-D (`flag_20260619_145434`): still **more than 5** rays per field.
- 2-D (`flag_20260619_145346`): still **3** per field.

## Root

0095 fixed the **full-pupil grid bundles** (`_build_grid_*` → `PupilCalc.Pattern`).
But this scene's `sampling_diagnostics` show `is_full_pupil_mode: false`,
`active_preview_mode: "world_cone"`, `source_model: "Pupil / field"` — it uses a
**different** sampler that 0095 never touched.

The world_cone path is `_trace_world_cone_rays` → `_build_world_cone_bundles` →
`_sample_ray_count_cone_points`, which **revolves** the meridional fan about the
axis: `n_rings = count // 2`, `n_az = _cone_azimuth_count()` (16–24, ×4). For
count=5 that is `1 + 2·16 = 33` rays per field in 3-D (a filled cone, bugs
0040/0041), and the 2-D layout is the X=0 ring-slice of it (≈3 distinct heights).

The revolve is correct for **non-sequential / folded** scenes (a branched
beam-splitter/mirror 3-D envelope needs sagittal width), which is exactly when
`_launch_pupil_prefers_meridional_fan()` returns False. But this scene is
sequential (`use_nonseq:false`, `use_folded:false`), so `prefers_meridional_fan`
is **True** and the fan should stay flat. The sibling
`_sample_ray_count_pupil_points` already honors that preference; the cone sampler
did not.

## Fix

In `_sample_ray_count_cone_points`, when `_launch_pupil_prefers_meridional_fan()`
is true, return a **flat fan of exactly N** samples on the display-slice meridian
(mirroring `_sample_ray_count_pupil_points`) instead of revolving. A flat fan sits
entirely at X=0, so the 3-D bundle draws N and the 2-D X=0 slice is the same N.
Non-seq/folded scenes (preference False) still revolve into the filled cone.

Verified (stub): meridional fan N → exactly N flat points (all X=0, N distinct
heights) for N=3,5,7,11; non-seq N=5 still revolves to 33.

## Test

`KrakenOS/UI/validate_open3d_ray_fan_count.py` — check (5) covers the world_cone
sampler (flat N for meridional fan, still-revolved for non-seq).
