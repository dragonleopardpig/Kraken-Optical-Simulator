# 0021 — A missing promoted-solid cache blanked the entire Open 3D view

**Status:** Fixed (2026-06-05).
**Component:** CAD cache location (`KrakenOS/UI/services/cad_cache_paths.py`), the
optical system build (`KrakenOS/UI/layout_editor.py` `_build_system_from_specs`),
the layout-open flow + body-STL regeneration
(`KrakenOS/UI/services/layout_import_export.py`,
`KrakenOS/UI/services/step_overlay_promotion.py`), and the missing-assets
scan/dialog (`KrakenOS/UI/services/missing_assets_scan.py`,
`KrakenOS/UI/panels/missing_assets_dialog.py`).
**Reported via:** the user, opening
`attachment/machine_vision_150mm_measured_test.py` on a second machine
(laptop "M90aPro") where the beam-splitter cube's cached body STL was absent.

## Symptoms (user's words)

> the beam splitter cache is missing, I skip, now the open 3D become blank, this
> should not happen at all.

and, on the desired behaviour:

> don't put anything in .cache, put it in attachment folder, I use Filen to sync
> this folder.
> the missing pop up during startup should not complain about missing .cache
> STL, it should prompt user to load the original STEP location, then import and
> convert again.

## Root cause

A promoted optical solid (here the beam-splitter **cube**, promotion label
`"led"`, row 6) stores a *derived* body mesh in `advanced["Solid_3d_stl"]` and the
original CAD in `advanced["OpticalSolidSourcePath"]`. The derived mesh was cached
in `~/.cache/krakenos/cad/promoted_step_overlays/` — **machine-local and not
synced** — while the source STEP lives under the Filen-synced `attachment/`
folder. So on the second machine the source STEP was present but the cached STL
was gone. Three things then compounded:

1. **The whole scene collapsed, not just the cube.**
   `Prerequisites3D.PupilSurface` does `pv.read(self.SDT[j].Solid_3d_stl)`
   (`KrakenOS/Prerequisites3D.py:256`) with no existence guard. A missing file
   raises `FileNotFoundError`, which aborts the *entire* 3D-prerequisite system
   build — every surface vanished, so the Open 3D view rendered blank (with rays
   off, nothing at all).
2. **The cache lived where it could not survive a machine hop** (`~/.cache`).
3. **The missing-assets dialog complained about the derived `.stl`** (it is in
   the scanner's `_ROW_PATH_KEYS`), asking the user to relocate a *cache* file,
   and a plain Skip left the scene blank — the `MissingResourceState` skip marker
   only drives the 3D *placeholder*, never the system build.

## Fix

Treat the body STL as a regenerable derivative of the source STEP, keep it in the
synced folder, and make a still-missing cache degrade gracefully.

* **Cache under `attachment/` (synced).** `cad_cache_paths.CAD_CACHE_DIR` now
  resolves to `<project>/attachment/cad_cache` instead of `~/.cache/krakenos/cad`
  (override with `KRAKENOS_CAD_CACHE_DIR` for a read-only checkout). The dir is
  `.gitignore`d — Filen syncs it; git does not track the derived artefact.
* **Regenerate on open.** `open_layout` runs a new
  `_regenerate_missing_optical_solid_caches()` *before* the missing-assets
  prompt: for any promoted row whose derived cache (`Solid_3d_stl`, or the
  analytic `StepAnalyticBodyStlPath`) is missing but whose source STEP is present,
  it rebuilds the body STL from the source via the existing
  `regenerate_promoted_body_stl_from_source` pipeline and rewrites the row's path
  **project-relative** (`_portable_cache_path`) so it stays portable.
* **Scan targets the source, not the cache.** `scan_missing_assets` no longer
  flags a derived cache key when its source key is configured
  (`_DERIVED_CACHE_SOURCES`); the source STEP is flagged when *it* is gone. The
  dialog's `_maybe_regenerate_body_stl` now also rebuilds `Solid_3d_stl` when the
  user relocates `OpticalSolidSourcePath` (previously only the analytic body on a
  `*.source_step_path` relocate).
* **Safety net.** `_build_system_from_specs` neutralises a `Solid_3d_stl` whose
  file is missing to `"None"` on the built `Surf`, so `pv.read` never sees a dead
  path: the analytic single-face fallback runs, the system builds, and the 3D
  view draws the row's red missing-asset placeholder instead of going blank. The
  row's stored path is untouched (the relocate dialog can still find it).

## Tests

`KrakenOS/UI/validate_open3d_missing_solid_cache_regenerates.py`
(`python -m KrakenOS.UI.validate_open3d_missing_solid_cache_regenerates`):

* **A — scan (fixture-free):** a missing `Solid_3d_stl` with a present
  `OpticalSolidSourcePath` is NOT flagged (regenerable); a missing source STEP IS
  flagged, and the derived cache is not.
* **B — safety net:** `_build_system_from_specs` neutralises a missing
  `Solid_3d_stl` (no source) to `"None"` rather than carrying the dead path.
* **C — regenerate:** opening the cube prescription with the cache absent rebuilds
  `Solid_3d_stl` from the source STEP; the new path resolves, is project-relative,
  and is no longer a `~/.cache` path.
* **D — render:** the rebuilt scene is not blank (31 renderer actors; the
  file-backed cube row draws 10 actors). Pre-fix this was 0 actors / a blank
  view.

Render checks SKIP when the cube's source STEP (an un-versioned Open 3D fixture)
is unavailable. Verified fail-before / pass-after by stashing the fix: pre-fix the
guard fails every check (`scan flagged a regenerable Solid_3d_stl`, `missing
Solid_3d_stl not neutralised`, `'_regenerate_missing_optical_solid_caches'` does
not exist); post-fix `[PASS]`.

Wired into the comprehensive harness as `Phase 29`
(`phase_29_missing_solid_cache_regenerates`); gate baseline regenerated.

The safety net has one knock-on: making a missing-cube layout *load* (degraded
to the analytic single-face) would let the bugs/0017 + bugs/0018 beam-splitter
guards (Phases 26/27) assert splitter physics on that placeholder and fail,
where they previously SKIPped on the load error. Those guards now first try
`_regenerate_missing_optical_solid_caches()` and, if the cube body still can't be
resolved (`missing_assets_scan.any_solid_body_unresolved`), SKIP rather than test
the placeholder -- so they run for real where the cube body resolves and SKIP
cleanly where it does not.

## Follow-up

* New promotions (a freshly imported STEP, before any reopen) still store the
  cache path **absolute** under `attachment/cad_cache`. That works across the
  user's machines (same `$HOME`) and self-heals to relative when the layout is
  reopened, but for full portability to other users the live promote write sites
  (`_step_overlay_optical_solid_row_plan`, `_write_promoted_body_stl_from_mesh`)
  should store project-relative too. Deferred to keep this change focused on the
  reported blank-scene bug; the open-time path is already relative.
