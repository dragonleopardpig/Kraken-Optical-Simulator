# 0095 — "Ray Fan count" is a sampling density, not a literal ray count

**Date:** 2026-06-19 (M90aPro)
**Branch:** nonseq-display-refactor
**Status:** FIXED — `validate_open3d_ray_fan_count` green; in-app confirm pending.

## Symptom (user flags, while testing bugs/0094 Phase 1)

- 2-D layout (`flag_20260619_134927`, the no-cube datasheet scene): "Ray Fan
  count = 5, only showing **3** per field sample."
- 3-D view (`flag_20260619_135*`, the beam-splitter-cube scene): the same
  setting (5) draws "**more than 5**" — ~50 rays per field.

So one setting (`5`) produced 3 in 2-D and ~50 in 3-D, and neither equalled 5.

## Root

"Ray Fan count" feeds KrakenOS's `PupilCalc.Samp`, which is a per-**axis sampling
density**, not a ray count: `Pattern()` multiplies it (meridional fan → `2*Samp+1`,
hexapolar → `1+3*Samp*(Samp+1)`, …).

Worse, the **default** pattern label `"Meridional fan"` was missing from
`PUPIL_PATTERN_TO_KRAKEN` (`source_trace_helpers.py`), so
`_current_kraken_pupil_pattern()` returned `None` and
`_current_analysis_pupil_pattern()` silently fell back to **Hexapolar**. With
`Samp = max(3, 5) = 5` that is `1+3·5·6 = 91` rays (~50 after aperture clipping)
in 3-D — *not* the flat meridional fan the user selected. In the 2-D **YZ
projection** those 91 hexapolar rays (different X, same Y) overlap onto a handful
of meridional lines, so only ~3 are visually distinct → the "3 per field".

Both the finite and angular display bundles
(`_build_grid_finite_object_bundles`, `_build_grid_angular_bundles` in
`trace_preview_sampling.py`) set `Samp = max(3, ray_count)` + the hexapolar-fallback
`Ptype`, then `Pattern2Field`. (`Pattern2Field` re-runs `Pattern()`, so the count
can only be controlled through `Samp`/`Ptype`, not by injecting pupil coords.)

## Fix

1. **Map the pattern** — add `"Meridional fan": "fany"` to
   `PUPIL_PATTERN_TO_KRAKEN` (a meridional fan *is* a fan in the tangential Y-Z
   plane). Stops the silent Hexapolar fallback; the launch + analysis now honor
   the selected pattern.
2. **Invert Samp** — `kraken_pattern_samp_for_count(kraken_pattern, ray_count)`
   returns the `Samp` whose `Pattern()` emits ~`ray_count` rays (`fany` → exact;
   filled patterns → ≥ N, ring/grid-quantised). Both display grid bundles set
   `Ptype` first, then `Samp = kraken_pattern_samp_for_count(Ptype, ray_count)`.

Result: "Ray Fan count = N" draws exactly **N** rays per field for a fan, all at
`Cordx == 0` (meridional), so the 3-D bundle and its 2-D YZ projection both show N
distinct lines. Filled patterns (Hexapolar/Square) honor the count instead of a
~5× blow-up. Analysis paths keep their own (dense) `Samp` — only the *display*
bundles invert it — but now use the user's pattern (`fany`) instead of silent
Hexapolar.

## Test

`KrakenOS/UI/validate_open3d_ray_fan_count.py` (display-free): the map, exact
N-and-meridional for fans, ≥ N for filled patterns, monotone inversion.

`.devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_ray_fan_count`
