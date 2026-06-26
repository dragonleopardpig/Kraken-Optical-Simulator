# 0166 — Open 3D: the optical solids re-mesh many times per refresh ("Creating solid objects for optical elements" prints ~46×)

> Status: **FIXED (primary + secondary wins shipped).** Performance/redundancy
> issue, not a correctness bug — the optics are right, the solids were just rebuilt
> far more often than necessary. Measured on `machine_vision_150mm_GN.py`:
> **overlay toggle rebuild → 0 solid builds** (re-render only), and **one genuine
> refresh 4 → 1 solid mesh.** Tertiary levers (broader `force_rebuild` relaxation,
> 2D/3D build sharing, NS bbox cull) are listed at the bottom as deferred.

## Symptom (user's words)

> the moment Open 3D is pressed, the terminal shows [16×] "Creating solid objects
> for optical elements" — is this number of times correct? Any duplicate?

…and then, running `python -m KrakenOS.UI.layout_editor` on
`machine_vision_150mm_GN.py`:

> This is the total number of times from Open 3D to enabling Detector, Refs and
> Thickness. [**46×** "Creating solid objects for optical elements"] Reasonable?
> I haven't touched anything else.

## Where the message comes from

`Prerequisites3DSolids()` (`KrakenOS/Prerequisites3D.py:434`, prints at line 437)
runs the pyVista solid-meshing pass for every surface. It fires once for **every**
full system build with `BUILD == 1`:

  * the `Kos.system(..., build=1)` constructor → `KrakenSys.py:363-364`;
  * **and again on every `system.build()`** — `KrakenSys.build()`
    (`KrakenSys.py:324`) re-runs the same init body, including the
    `if self.BUILD == 1: self.Pr3D.Prerequisites3DSolids()` at `KrakenSys.py:363`.

## Measured decomposition (one headless refresh of this scene)

Instrumenting `Prerequisites3DSolids` and driving one
`_build_preview_system_rays_bundle` for `machine_vision_150mm_GN.py` shows the
SAME prescription is built as a fresh `KrakenSys` several independent times, each
for a different calculation:

| count | call site | purpose |
|------:|-----------|---------|
| 1× | `layout_analysis_display.py:188` (`build_system`) | the display solids |
| 1× | `paraxial_tools.py:44` | paraxial / first-order reference |
| 2× | `analysis_compute_workflow.py:50` | **per-branch** pupil calc — the beam-splitter splits the ray tree into ≥2 arms, one build per arm |

≈4 builds in a minimal headless refresh. The **live** app does more on top of that:
it runs *both* the 2D plot refresh and the 3D-inspector refresh
(`open_3d_view` → `refresh_from_editor` → `build_inspector_refresh`,
`open3d_trace_refresh.py:239`), plus per-branch detector pupils inside the real
display bundle — so a real Open-3D press on a beam-splitter scene reaches the
teens. Then **each overlay toggle** (Detector, Refs, Thickness) fires a *whole
fresh refresh*, so 1 open + 3 toggles ≈ 4 refreshes → ≈46 cumulative. The count
is fully explained.

## Root causes of the avoidable work (all tied to the promoted beam-splitter)

1. **Cache bypass.** `build_system(..., force_rebuild=True)` is forced whenever the
   scene has promoted-STEP native rows: `_build_preview_system_rays_bundle`
   (`three_d_scene_tools.py:449`) computes
   `force_rebuild=bool(live_step_records or saved_native_records)` at
   `three_d_scene_tools.py:505`. This scene's promoted BS-cube makes
   `saved_native_records` non-empty, so the `_system_cache_signature` cache in
   `build_system` (`layout_analysis_display.py:166-196`) is skipped and the solids
   re-mesh even when nothing geometric changed.
2. **Build hook re-meshes every time.** The non-seq output-port hook
   `build_with_output_ports` (`nonseq_output_ports.py:1447`, installed by
   `_install_build_hook` / `apply_optical_solid_output_port_system_overrides`,
   `nonseq_output_ports.py:1440`/`1460`) calls `original_build()` on *every*
   `system.build()`, and that re-runs the entire `Prerequisites3DSolids` pyVista
   pass.
3. **Overlay toggles rebuild from scratch.** Toggling Detector / Refs / Thickness
   changes *no geometry*, yet each triggers a full scene refresh
   (`refresh_from_editor` → `build_inspector_refresh`) that rebuilds the optical
   solids from zero.

## Fix — shipped

### Primary: overlay toggles re-render the cached scene (0 builds)

The three checkboxes (`Refs` → `show_reference_surfaces_var`, `Det` →
`show_detector_overlays_var`, `Thickness` → `show_physical_distances_var`, plus
terminal-diagnostics and placement-handles) all fire
`Kraken3DInspector._on_scene_visibility_changed`
(`open3d_inspector.py`). It used to call `refresh_from_editor()`
**unconditionally** — and on a saved promoted beam-splitter scene that forces a
full retrace (`has_promoted_step_optical_solid_rows` →
`requires_open3d_retrace = True` in `build_inspector_refresh`), which re-meshes
every solid.

`refresh_scene` (`open3d_scene_refresh.py`) reads each of those visibility vars
**live at render time** from the passed `system`/`rays`/`scene_bundle` — toggling
one only changes which actors draw, never the geometry or the trace. So the handler
now mirrors the Show Rays fast toggle:

  * new gate `Open3DTraceRefreshService.can_reuse_current_scene_for_display_toggle`
    (`open3d_trace_refresh.py`) — reuse whenever the inspector holds a valid,
    non-dirty cached scene. Unlike `can_reuse_current_scene_for_show_rays` it has
    **no** show-rays / live-step-overlay coupling (that coupling would force a
    rebuild on the user's promoted-BS scene);
  * `_on_scene_visibility_changed` re-renders via `refresh_scene(_current_system,
    _current_rays, _current_row_names, scene_bundle=_current_scene_bundle)` when the
    gate passes, and only falls back to `refresh_from_editor()` when there is no
    cached scene yet or a geometry edit dirtied the preview trace.

### Secondary: paraxial-only systems skip the output-port force-mesh (4 → 1)

The real culprit behind the per-refresh multi-build was **not** separate `build=1`
constructions — it was `apply_optical_solid_output_port_system_overrides`
(`nonseq_output_ports.py:1494`, the `needs_build` path) **force-meshing every
system that lacks solids**, including the `build=0` paraxial systems that only run
`PupilCalc` / `Parax` and never NS-trace the meshes. On the BS scene that
force-meshed the cube once per branch pupil + once for the magnification solve.

`_build_system_from_specs` (`layout_editor.py`) gained
`apply_optical_solid_output_ports: bool = True`; the overrides are skipped when
False. The two paraxial-only callers pass False (threaded through the
`paraxial_tools` / `analysis_compute_workflow` wrappers):

  * `analysis_compute_workflow._pupil_model_inputs` (per-branch entrance pupil);
  * `paraxial_tools._exact_paraxial_solution_for_rows` (finite paraxial mag / EFL /
    cardinals).

The default stays True so the worker analysis trace (`_build_cached_system_from_specs`,
`build=0`) still force-meshes — it genuinely NS-traces through the solids.

### Verified (display-free)

`validate_open3d_overlay_toggle_no_rebuild`: a real refresh of the scene builds
solids (baseline), the display-toggle gate is reusable immediately after (toggle =
0 builds), dirtying the trace flips it back to rebuild, a missing cache → rebuild,
and `_on_scene_visibility_changed` + `refresh_scene` are render-only. The
`tools/probe_refresh_builds.py` solid counter shows one refresh **4 → 1** build.
Regression-clean: per-branch pupil, first-order reference, two-arm fold, camera-FOV
launch, aperture-stop NS vignette, inscribed-sensor, cooke-triplet / double-gauss
cardinals all still pass. Penta phase 157 + baseline added. The rendered scene
itself still needs an in-app eyeball (headless has no VTK).

## Deferred (further levers, not yet done)

* **Broader `force_rebuild` relaxation.** `_build_preview_system_rays_bundle`
  still sets `force_rebuild=True` whenever the scene merely *has* saved promoted
  solids (`three_d_scene_tools.py:505`), bypassing the `build_system` signature
  cache even when nothing changed — so two genuine refreshes (2D plot + 3D
  inspector) on open each rebuild. Gating it on the native rows actually changing
  would let them share one build. Riskier (the bugs/0085–0093 promoted/live-STEP
  desync history), so left for a focused follow-up.
* **NS broad-phase bbox cull** and the other trace-time levers in
  `reference_open3d_perf_profiling` remain open.
