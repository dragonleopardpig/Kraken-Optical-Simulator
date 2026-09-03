# 0700 — "Ctrl-Z to undo the rotation is super slow"

User report (om05a, after the 0698 rotation work): undoing a rotation takes
minutes. Reproduced headlessly (`bugs/0700_undo_profile.py`): the rotate command
itself is 0.66 s (it defers its refresh — `_mark_plot_update_pending` + a
delayed 3D live refresh), but `editor.undo()` took **245 s wall**.

## Profile (cProfile over the undo)

- `_trace_preview_rays_folded_aware` ran **twice** — 333 s cumulative. Two full
  non-sequential traces of the same scene in one undo.
- Trace #1: `refresh_plot()`'s own build (system + folded-aware trace + scene
  bundle).
- Trace #2: `refresh_plot` hands those products to
  `_refresh_3d_inspector_if_open(system=…, rays=…, scene_bundle=…)` →
  `sync_open_inspector` → `current_or_rebuild_scene`, which **discarded them**
  and re-ran `_build_preview_system_rays_bundle` (193 s) because
  `has_promoted_step_optical_solid_rows()` is True — om05a has twelve promoted
  STEP optical-solid rows.
- Remainder: `_active_ray_analysis_records` ×3 (69 s, each rebuilding a scene
  bundle), `_refresh_analysis_branch_choices` 34 s — follow-on refreshes, left
  for a future pass.

## Root cause

The discard rule dates to f35ffdec (2026-05-25): back then the 2D preview
bundle could mark escaped CAD rays as detector-miss image-plane continuations,
so Open 3D always rebuilt through its own trace path on promoted-STEP scenes.
Since bugs/0201/0243 the 2D preview runs the SAME folded-aware trace on the
REAL system that Open 3D would rebuild (the profile shows both passes inside
`_trace_world_cone_rays` — byte-for-byte the same computation), so the defence
now only doubles every history restore. Display follows physics also argues the
3D view must show the trace the 2D view just drew, not a separately built one.

## Fix (`open3d_trace_refresh.current_or_rebuild_scene`)

Products passed EXPLICITLY (the fresh handoff from `refresh_plot`, its only
caller) are now trusted even on promoted-STEP scenes. Unchanged protections:

- the CACHED-trace path (`_current_preview_scene_trace`) is still refused for
  promoted-STEP rows — first-open of Open 3D still rebuilds (the f35ffdec
  case);
- the sampling-mode gate (`_active_trace_can_feed_open3d`) still rejects a
  supplied bundle whose launch mode cannot feed the 3D scene (a flat 2D fan is
  rebuilt as the cone, per the 0166-era cone-not-reused-as-fan guard).

## Second fix (`analysis_reports._active_ray_analysis_records`)

The profile also showed `_ray_analysis_records_for_trace` running 3× per
refresh (~23 s each — every call rebuilds a full scene bundle from the
raykeeper) for the branch choices + the detector-aperture / throughput /
illumination refreshes. Now memoised per trace, identity-anchored on the live
`(last_system, last_rays)` pair (strong refs, so `is` cannot alias a recycled
id) plus the keeper's stored-ray count so an in-place additive append
invalidates. The builder's `_last_scene_bundle` side effect is idempotent for
identical inputs.

## Measurement

om05a rotate + undo (`bugs/0700_undo_profile.py`), rotate steady at ~0.65 s:

| build | undo wall |
| --- | --- |
| before | 245.3 s |
| + trust explicit handoff (one trace) | 155.5 s |
| + records memo | **132.2 s** |

The remaining ~130 s is dominated by the ONE legitimate full non-sequential
trace (~90 s on this scene) plus the 2D draw and analysis refreshes — the
structural NS-trace levers (perf memory topic) or deferring the undo trace
like a 0646 load (user's call) are the only ways lower.

## Guards

`validate_open3d_promoted_step_refresh` re-pinned: explicit fresh bundle
trusted (0700), no-args sync still rebuilds, mode-incompatible supplied bundle
still rebuilt. (Its `_FakeEditor` also gained the `trace_rays` kwarg the 0646
service change introduced — the fake had drifted.) Re-run green:
`validate_3d_interaction_contract`, `validate_open3d_overlay_toggle_no_rebuild`,
`validate_open3d_cone_not_reused_as_fan`, `validate_open3d_promoted_row_slide`,
`validate_open3d_live_transient_step`, `validate_open3d_promote_ray_clamp`.

## Open follow-ups (not in this fix)

- An undo could arguably defer the trace entirely like a load (0646 fast-load)
  and let "Trace Now"/the 3D view pull it — that would make undo near-instant,
  but rays would vanish until the next trace. Semantics change, needs the user.
- `_refresh_analysis_branch_choices` still costs ~15 s of its own beyond the
  shared records.
