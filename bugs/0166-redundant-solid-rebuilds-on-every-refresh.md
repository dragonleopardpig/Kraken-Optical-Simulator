# 0166 — Open 3D: the optical solids re-mesh many times per refresh ("Creating solid objects for optical elements" prints ~46×)

> Status: **DOCUMENTED — fix deferred (next-priority perf fix).** No code change
> yet. This is a performance/redundancy issue, not a correctness bug — the optics
> are right, the solids are just rebuilt far more often than necessary.

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

## Recommended fix (in priority order)

1. **Primary win — overlay toggles must not re-mesh solids.** Detector / Refs /
   Thickness are *display overlays*; the geometry is unchanged. The toggle handlers
   should reuse the cached built `system` + `_last_scene_bundle` and only
   re-derive the overlay layer, instead of going through a full
   `_build_preview_system_rays_bundle`. This removes ~3 refreshes' worth of builds
   (roughly half of the 46).
2. **Secondary — share one built system across the per-refresh passes.** Within a
   single refresh, the display build (`build_system`), the paraxial reference
   (`paraxial_tools.py:44`), and the per-branch analysis pupils
   (`analysis_compute_workflow.py:50`) each construct their own `KrakenSys`. They
   could share one geometry-built system (the prescription is identical), or the
   paraxial/pupil passes could build with `build=0` (no solids) since they don't
   need the meshes.
3. **Tertiary — don't blanket-`force_rebuild` for saved promoted-STEP rows.** The
   `force_rebuild` at `three_d_scene_tools.py:505` exists so live/edited STEP
   overlays re-trace, but a *saved, unchanged* promoted solid does not need a
   re-mesh on every refresh. Gate `force_rebuild` on the native rows having
   actually changed (signature) rather than merely being present.

## When implemented (workflow reminder)

This is a perf optimization with **no optics behavior change**. Add a display-free
guard that pins the rebuild count: instrument `Prerequisites3DSolids` and assert
that toggling an overlay on an already-open scene performs **0** additional solid
builds, and that a single refresh stays within an expected small bound. Then a
penta phase + baseline entry as usual.
