# 0060 — Open 3D: mark thickness Variable, solve Best Focus / Best Collimation

## Reported (direct request)

> I want the most of the functions/features in 2D available in 3D. Can make
> thickness or multiple thicknesses set to Variable and solve for Best Focus or
> Best Collimate?

(Phase 1 of a two-phase plan; full 3D Optimization is Phase 2, deferred.) The 2D
editor lets a user flag one or more thicknesses **Variable** and run a 1-D solve
for the best image. The embedded Open 3D inspector had no equivalent — there was
no way to mark a gap Variable in 3D, and no Best Collimation objective existed in
either view.

## Design

Two things were needed: a **Best Collimation** merit (net-new) and a 3D
**Variable + solve** workflow that shares state with 2D.

**Best Collimation merit — paraxial output vergence, not real-ray spread.** The
first attempt measured the angular spread of the exit ray directions
(`_collimation_angular_spread_for_rows`). With a small ray fan it vignetted to
noise and behaved non-monotonically, so the solve wandered. Replaced with a
closed-form paraxial metric: the magnitude of the output ray vergence `|1/s'|`
computed from the system ABCD. `_exact_paraxial_solution_for_rows` zeroes the
object/back/image gaps so the ABCD is the optical block alone (object-independent),
then the current object distance `s = rows[0].thickness` is applied analytically —
finite mode `|a + b·s| / |c + d·s|`, infinity mode `|a|/|c|`. This goes smoothly to
**0 exactly at collimation** (image at infinity), is deterministic, and needs no
ray tracing, so the search is fast and V-shaped. Verified the collimated object
distance lands at the front focal distance (EFL − ppa ≈ 125 mm on the 150 mm 1×
machine-vision layout).

**The Variable flag is the shared one.** A gap is marked Variable by setting
`SurfaceRow.optimize_thickness` — the *same* flag the 2D optimization path reads —
so a thickness flagged in 3D is Variable in 2D and vice versa. No new state.

**Objective validity.** The terminal Image gap is the axial reference, never a
target. Best Focus excludes the object gap (an object move is not a focus knob),
but Best Collimation **includes** it — moving the source toward the focal point is
the canonical way to parallelise the exit beam.

## Fix

New service `KrakenOS/UI/services/open3d_solve.py` — `Open3DSolveService`:
- `thickness_gap_rows()` lists every gap except the Image row;
  `is_variable`/`set_variable`/`toggle_variable` read/write the shared
  `optimize_thickness`; `variable_rows()` + `_valid_rows_for(objective)` apply the
  validity rules above.
- `solve(objective)` runs the editor's 1-D minimiser per Variable gap. For a
  single Variable that is the 1-D solve; for several it runs up to 4
  coordinate-descent passes (solve each gap against the current layout, stop when
  every gap moves < 1e-4 mm). It mutates only `editor.rows[i].thickness` — the
  caller owns history capture + retrace.

Editor mixin `KrakenOS/UI/services/paraxial_tools.py`:
- `_collimation_output_vergence_for_rows` (paraxial_tools.py:1223) — the `|1/s'|`
  merit above.
- `_collimation_search_interval` (paraxial_tools.py:1252) — a focal-length-aware
  bracket `0 .. current + max(current, 2.5·|EFL|)`, since the collimated point can
  sit far from the current object distance.
- `_compute_best_collimation_result` (paraxial_tools.py:1267) — coarse 21-point
  scan + 3 local-refine passes over the vergence metric; rejects only the Image
  row. Mirrors the Best Focus result shape. Best Focus reuses the existing
  `_compute_best_focus_result` unchanged.

Inspector `KrakenOS/UI/open3d_inspector.py`:
- `_open3d_solve_service` (open3d_inspector.py:788) — lazy `Open3DSolveService`.
- `_open3d_toggle_variable_thickness` (open3d_inspector.py:11868) — syncs a gap's
  checkbox to `set_variable`.
- `_open3d_run_thickness_solve` (open3d_inspector.py:11879) — wraps the solve in
  the same history + retrace path as Snap to FOV: `_begin_history_capture` →
  `service.solve` → on success `_sync_table` → `_commit_history_capture` →
  `_invalidate_preview_scene_trace` → `_sync_trace_state_badge` →
  `refresh_from_editor(force_retrace=True)` → QE readout refresh; on failure it
  still commits the (empty) capture and reports the message.

Panel `KrakenOS/UI/panels/open3d_live_controls.py`:
- `build()` adds a **Solve (Variable thickness)** `LabelFrame` (panel row 4, after
  Quick Estimation); `build_solve_controls` (open3d_live_controls.py:202) draws an
  explanatory label, one checkbox per thickness gap (each wired to
  `_open3d_toggle_variable_thickness`), and **Solve Best Focus** /
  **Solve Best Collimation** buttons.

## Tests

`KrakenOS/UI/validate_open3d_thickness_solve.py` (new, display-free):
- Source contracts: the solve-service API, the editor mixin methods, the inspector
  hooks (and that the run hook keeps the `_begin_history_capture` /
  `_commit_history_capture` / `_sync_table` / `refresh_from_editor` retrace
  contract), and the panel's `build_solve_controls` section.
- Engine, via snapshot editors across all five machine-vision layouts: the shared
  `optimize_thickness` flag round-trips; Best Focus excludes the object gap while
  Best Collimation includes it; the Image gap is never listed; the collimation
  vergence is V-shaped and ~0 (< 1e-3 /mm) at the solved object distance, which
  lands near the front focal distance (EFL − ppa); and the service mutates the
  object gap toward the focal point while lowering the vergence.
- Best Focus **delegation** (variable flag → gap selection → thickness mutation +
  spot-RMS message) is exercised on the one fast 150 mm 1× layout. Best Focus is
  the pre-existing 2D solver, already guarded by `validate_nonseq_best_image_solve`
  + comprehensive phases 7/9; the sequential spot-RMS metric is expensive headless
  on the pyrite/measured layouts, so re-running it on all five is not the thing
  under test here.

UI confirmed by rendering the new Solve section to PNG: title, one checkbox per
gap (Object…Lens Rear, Image excluded), and the two solve buttons.

## Penta phase

**Phase 62** — `phase_62_variable_thickness_solve` wraps the guard's `run_checks`
(display-free, so it runs everywhere, unlike the renderer-bound machine-vision
phases). Baseline regenerated with phase 62 = pass.
