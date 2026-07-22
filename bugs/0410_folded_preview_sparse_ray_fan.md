# 0410 — sparse 3D-preview ray fan on expensive folded/prism scenes

**Flag:** `flag_20260722_155930` (part of a 4-flag recording, build f4c0d09b — the other 3 flags confirm
0408 + 0409 work): "with Ray On. (really long ray tracing time)."

## Why it's slow

A folded RA-mirror scene traces the **real** system through the BK7 fold prisms (bugs/0243), which is
~10 ms/ray in the non-seq engine. Timing on the AZ85 scene: the full Ray-On trace is **~30 s** — ~9 ray
bundles × ~3.7 s, ~3249 rays. It's already cached (only re-runs on a scene change), Ray-Off is
bodies-only (0400), and drags/promotes use a sparse fan — but a full-density **Ray-On** trace is
inherently slow through the prisms.

Chosen approach (via AskUserQuestion): **sparse 3D preview fan** — cap the SHOWN 3D preview ray count on
the expensive folded path; the analysis modes keep the user's full density.

## Fix

`_trace_preview_rays_folded_aware` (the folded 3D-preview trace) sets a **transient**
`_folded_preview_ray_count_override` around its `_trace_preview_rays` call and **pops it in the
`finally`**. `_current_ray_count` honours that override (after the existing promote/drag overrides, which
still win). So:

- The **folded 3D preview** traces a sparse fan → seconds instead of ~30 s.
- The override is set ONLY on the folded path (`folded_trace_rows` present) and cleared before the
  method returns, so it **never leaks**. The analysis modes (spot / heatmap / MTF), which call
  `_current_ray_count` through their **own** sampling paths at other times, keep the user's full density.

`_folded_preview_ray_count_cap()` returns `min(user_ray_count, 10)` — it **only lowers**, never raises a
user who already set a low count. Tunable for the eyeball via `KRAKEN_FOLDED_PREVIEW_RAY_CAP` (higher =
denser + slower).

**Default calibrated in-app (measured, not modelled):** at full density the AZ85 folded scene was ~6K
rays / ~60 s. cap 15 → **2475 rays / ~20 s** (`flag_162155`); default **cap 10 → 1827 rays / 17.9 s**
(`flag_163101`, user closed it there). **KEY: the ray count is fairly INSENSITIVE to the cap in this
range** (15→10 only dropped 2475→1827 rays, 20→17.9 s) — my "~quadratic, ~9 s" estimate was wrong. So
~18 s is near a STRUCTURAL floor for this folded scene (the 9-bundle cascade + per-bundle mesh setup),
which ray-count reduction alone can't break; the remaining levers (NS bbox cull, cut the 9-bundle
cascade, defer-retrace) are what would push it lower.

## Verification (`validate_open3d_folded_preview_ray_cap`, penta phase 334)

| check | asserts |
|---|---|
| CAP-LOGIC | caps a high count (45 → 15); never raises a low one (8 → 8) |
| OVERRIDE | `_current_ray_count` honours the folded override; promote/drag override still wins |
| TRANSIENT | the folded trace sets the override then POPS it in a `finally`, only on the folded path (analysis modes unaffected) |

3/3 pass; baseline records phase 334 = pass.

## Files

- `KrakenOS/UI/services/three_d_scene_tools.py` — the transient cap around the folded preview trace + `_folded_preview_ray_count_cap`.
- `KrakenOS/UI/services/trace_preview_sampling.py` — `_current_ray_count` honours the folded override.
- `KrakenOS/UI/validate_open3d_folded_preview_ray_cap.py` — guard (phase 334).

## In-app eyeball still owed

CONFIRMED + CLOSED in-app: on the AZ85 folded scene with Ray On the 3D preview traces a **sparse** fan
in **17.9 s** (default cap 10, 1827 rays) — down from ~60 s / ~6K rays at full density. The user accepted
this. The fan is visibly thinner; raise `KRAKEN_FOLDED_PREVIEW_RAY_CAP` (default 10) for a denser fan.
Spot / heatmap / MTF analyses are unchanged (full density).

## Scope / next

Only the folded/prism preview path is capped (the expensive one). The other perf ideas from the flag —
running the folded trace in the background (responsive UI) and deferring traces during multi-step edits
— remain available if the sparse fan isn't enough.
