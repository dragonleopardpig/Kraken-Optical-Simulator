# `nonseq-display-refactor` Branch README

Last updated: 2026-05-17

This is the single branch-level Markdown document for `nonseq-display-refactor`.
The upstream project `README.md` is intentionally left unchanged. Historical
branch plans, phase notes, gap lists, and status pages have been consolidated
here so the browser view has one authoritative branch summary.

## North Star

The UI should be non-sequential by design. A KrakenOS layout is a scene of
optical objects, sources, detectors, coatings, masks, STL solids, and path
metadata. Sequential ray tracing remains important, but it should be treated as
the axial ordered-surface special case of the same scene workflow.

Four invariants define the target architecture:

1. True non-sequential tracing is the native model; sequential tracing is a
   reproducible ordered-path special case.
2. Optical elements and ray tracing are represented in 3D behind the scene; 2D
   plots are slice/projection views of traced 3D data, not separate simulations.
3. Object/reference geometry and illumination sources are separate scene
   entities. Multiple sources should be placeable at arbitrary positions and
   angles, and illumination analysis should report uniformity and vignetting on
   the selected object or detector surface.
4. Every ray/surface event must obey the configured physics law: reflection,
   transmission, absorption, dispersion, diffraction, coating response,
   polarization, total internal reflection, or detector termination. Ambiguous
   geometry should produce diagnostics instead of silently drawing a plausible
   but wrong path.

Practical rule:

- Use scene/non-sequential tracing whenever the user creates a physical source,
  beam splitter, target surface, probabilistic non-sequential coating, STL
  object, mirror fold, tilt/decenter scene, or detector/path workflow.
- Keep exact sequential tracing for conventional lens-design prescriptions and
  paraxial/wavefront analyses that explicitly depend on ordered surfaces.
- Never hide KrakenOS-native state behind a UI-only abstraction without
  preserving it in row metadata, scene graph diagnostics, raykeeper metadata, or
  CSV export.

## Progress Snapshot

Estimated branch status:

| North Star area | Status | Progress | Current movement |
| --- | --- | --- | --- |
| Native non-sequential tracing | Partially achieved | `█████████░ 98%` | `NsTrace`, optical solids, beam splitting, diffuse scatter, terminal policy, media state, and branch metadata are present; remaining work is removing scalar-index compatibility mirrors. |
| Sequential ordered-path special case | Achieved for current UI/export path | `██████████ 100%` | Sequential `Pupil / field` previews preserve ray-count semantics, use 3D section traces for 2D projections, collapse zero-field samples to one effective launch, and export requested/effective launch metadata. |
| 3D scene with 2D projections | Improving | `█████████░ 99%` | 2D YZ/XZ/XY views are projections or slices of traced 3D data; Open 3D asks for world-envelope traces. |
| Separate sources, objects, detectors | Partially achieved | `███████░░░ 70%` | Scene sources are first-class records and reports preserve source identity plus launch intent; object/reference geometry is still partly row-driven. |
| Event-law physics and diagnostics | Partially achieved | `█████████░ 99%` | Raykeeper emits typed trace events; inspectors, path reports, CSV exports, detector analyses, Gaussian-q records, launch sampling metadata, and direct Ray Inspector collection now consume canonical event-backed records when scene data is available. |
| Arbitrary prisms/solids regression coverage | Improving | `█████████░ 99%` | Optical-solid media state, face identity, terminal policy, detector misses, and event-backed analysis paths are covered by validators. |

Main remaining architectural gap:

- Finish replacing the remaining legacy scalar `PrevN` compatibility mirrors at
  KrakenOS/UI boundaries.
- Finish lifting plot annotations, object/detector semantics, and remaining
  compatibility display flags behind canonical scene/event records.
- Replace folded-preview-specific YZ compatibility paths with physical scene
  geometry where feasible.

## Current Branch Capabilities

### Layout Editor

`KrakenOS/UI/layout_editor.py` is the main branch surface:

- Spreadsheet-style prescription table with undo/redo, copy/paste, grouped
  elements, right-click surface actions, advanced surface editing, and cell-local
  optimization variable markers.
- Live 2D plot with projection selector, ray display filters, source labels,
  detector/end-state markers, path labels, and explicit update flow.
- Open 3D inspector for traced scene geometry, STL/CAD placement, source-target
  picking, face anchors, and STEP overlay inspection.
- Analysis panes for spot, PSF, MTF, wavefront, Zernike, Seidel, pupil,
  field curvature, lateral color, polarization, illumination, detector maps,
  coherent/diffraction detector workflows, branch fields, and source reports.
- Scene diagnostics: Ray Inspector, Trace Path Inspector, Branch Throughput,
  Branch Gaussian Q, Source Illumination, and Non-Sequential Scene Graph.
- Import/catalog tools for common optical layouts, stock lenses, AGF glass
  names, Zemax prescriptions, STEP/IGES-to-STL CAD meshes, measured error maps,
  and optical CAD/STL solids.

Recent UI contract fixes:

- Left-panel text entries commit on focus loss as well as Enter.
- Editable prescription table cells commit on focus loss as well as Enter.
- `Field Samples` becomes disabled and displays `NA` when the active field span
  is zero; the previous requested sample count is restored when the field span
  becomes nonzero.
- Zero-field sequential preview traces one effective field launch instead of
  drawing duplicate coincident field bundles.
- Raykeeper trace events, scene events, saved ray records, and CSV exports carry
  launch metadata: requested field samples, effective field launches, field
  basis/span, field-active state, ray count, pupil sampling label, trace intent,
  and sampling mode.

### Scene And Display Pipeline

The display pipeline is split into testable scene stages:

| Module | Role |
| --- | --- |
| `KrakenOS/UI/scene_geometry.py` | Pure dataclasses for surfaces, rays, events, source records, boundary faces, volumes, and projected scene data. |
| `KrakenOS/UI/scene_builder.py` | Converts traced KrakenOS systems/rays into `SceneBundle` data and canonical `RayEvent3D` records. |
| `KrakenOS/UI/scene_projector.py` | Projects traced 3D scene data into YZ/XZ/XY or auxiliary 2D views. |
| `KrakenOS/UI/scene_renderer_2d.py` | Renders projected scene data on matplotlib axes. |
| `KrakenOS/UI/layout_plot_controller.py` | Coordinates plot refresh, projection filters, and status labeling outside the editor monolith. |

2D is treated as a view of 3D trace data:

- YZ and XZ are physical section views.
- XY is a top-view footprint.
- Sequential `Pupil / field` 2D uses a shared 3D section trace, then filters
  the traced data into the selected projection.

### Non-Sequential Physics And Metadata

Implemented architecture pieces:

- Shared trace-intent resolver in `KrakenOS/UI/trace_intent.py` chooses
  sequential or non-sequential intent for live UI and saved/exported layouts.
- `NsTrace`, `NsTraceLoop`, and raykeeper metadata carry terminal target,
  detector, source, branch, and media-state fields.
- Optical-solid hits carry mesh cell id, original cell id, face id, face-match
  method, diagnostics, volume identity, material, ambient medium, and media
  transitions.
- Non-STL refractive hits update the same ray-state bridge as STL solids.
- Absorbers, detectors, final target planes, splitters, and scatter children use
  shared terminal/media-event helpers.
- Terminal and branch snapshots preserve final medium, refractive index,
  inside-volume stack, state method, termination reason, and diagnostics.
- Launch snapshots preserve requested versus effective field sampling so live
  previews, saved scripts, Ray Inspector, path analysis, and ray-event CSV export
  explain zero-field/on-axis collapses without hiding the requested UI state.
- Canonical ray events feed inspectors, display paths, 2D event markers, source
  illumination, detector/path analyses, Gaussian q/frame reports, and CSV export.

### Sources, Objects, And Detectors

Implemented:

- Source panel and Scene Source Manager create explicit scene-source records.
- Physical source workflows trigger non-sequential scene tracing in Auto mode.
- Source identity, role, model, wavelength, power, branch power, and source
  weighting are preserved in trace and analysis records.
- Source-object aiming supports row targets and CAD/STL face anchors.
- Source Illumination Report summarizes hit power, vignetting, and target
  coverage by source.

Still partial:

- The prescription table remains row-first. Source/object/detector semantics are
  first-class in scene metadata and reports, but not yet a fully separate
  editable scene graph.

### Beam Splitter And Path Workbench

Implemented:

- `Beam Splitter` rows carry deterministic and probabilistic split metadata.
- Branch paths preserve transmitted/reflected child state.
- Path-aware placement helpers can add detectors, apertures, mirrors, thin
  lenses, refractive surfaces, and stock lenses along traced paths.
- Path-filtered analysis and reports cover detector, PSF, MTF, coherent detector,
  diffraction detector, source illumination, branch throughput, and Gaussian q.

Direction:

- Beam-splitter workflows are treated as non-sequential scene workflows.
- The table should avoid pretending that reflected/transmitted arms are just a
  single axial sequence.

### CAD, STL, And Prism Workflows

Implemented:

- Optical CAD/STL solids can be inserted, rendered, diagnosed, placed, and
  assigned boundary-face roles.
- STEP/IGES meshes are cached as STL for KrakenOS tracing.
- Face anchors, snap-to-ray/path-frame placement, virtual internal planes, and
  hit-sequence validators support prism and beam-splitter case studies.
- Optical-solid media state and face-law diagnostics are recorded per hit.

Important rule:

- Prism fixes should be architecture-level. A ray that hits a surface should
  transmit, reflect, absorb, split, scatter, diffract, or terminate at a detector
  according to the configured physics law; it should not stop silently halfway.

### Sequential Lens Workflow

Sequential tracing remains important and should stay exact where the workflow is
truly ordered:

- Conventional prescriptions, paraxial solves, wavefront analysis, field maps,
  and classic lens diagnostics continue to use ordered surfaces where needed.
- `Field Samples` sample field positions or angles, not pupil rays.
- `Ray Count` controls the fan/pupil sampling.
- When field span is zero, multiple requested field samples collapse to one
  physical on-axis launch and the UI now shows this explicitly.
- Finite-object mode derives its launch cone from object distance and entrance
  pupil, not from the physical Source cone angle.

### Optimization

Implemented:

- `KrakenOS/Optimization/` contains variables, operands, merit functions,
  evaluators, and a pygmo adapter.
- UI supports merit operand setup, variable selection, bounds, worker count,
  SciPy/pygmo backend checks, tolerance Monte Carlo, compensator sweeps, and
  saved solve presets.

Known local reproduction notes:

- On the X299-SSD environment, use `devenv shell` first.
- Install editable KrakenOS inside the devenv when needed.
- Build optional pagmo/pygmo locally only if the global optimization backend is
  required; SciPy remains the safer fallback.

### GPU And Batch Tracing

Implemented but optional:

- `KrakenOS/gpu_backend.py` provides a NumPy/CuPy namespace abstraction.
- Batch tracing and GPU paths are available behind safe fallbacks.
- CPU remains the default reliable execution path when CUDA/CuPy is unavailable.

### Core KrakenOS Algorithm Notes

Stable core model:

- `surf` is the optical primitive.
- The sequential trace path transforms rays into local surface coordinates,
  solves exact intersections, evaluates local normals, applies refraction,
  reflection, diffraction, coatings, bulk transmission, optical path, material
  dispersion, and paraxial bookkeeping.
- Total internal reflection is a physics result of the incident medium,
  transmitted medium, and angle. It should not require a user to label a surface
  as TIR.
- Non-sequential tracing selects the next hit geometrically rather than by table
  order, then applies the same event-law discipline.

## Validation Commands

Useful smoke checks:

```bash
devenv shell python -m py_compile KrakenOS/UI/layout_editor.py KrakenOS/UI/validate_scene_sources.py
devenv shell python KrakenOS/UI/validate_scene_sources.py
devenv shell python KrakenOS/UI/validate_layout_plot_controller.py
devenv shell python -m KrakenOS.UI.render_layout_snapshot --layout attachment/doublet.py --output /tmp/kraken-doublet.png --mode 2d
```

Targeted non-sequential and source checks:

```bash
devenv shell python -m KrakenOS.UI.validate_source_object_split
devenv shell python -m KrakenOS.UI.validate_phase6_complete
devenv shell python -m KrakenOS.UI.validate_phase7_complete
devenv shell python -m KrakenOS.UI.validate_demo_readiness --full
```

## Current Bugs And Risks To Watch

- Future code paths may accidentally bypass `trace_intent.py` and reintroduce
  local sequential/non-sequential heuristics.
- Remaining scalar incident-index compatibility mirrors can drift from canonical
  ray-state media fields if a new physics path forgets to update both.
- Any new prism/CAD helper must preserve face identity, media state, and terminal
  diagnostics instead of adding case-specific display rays.
- Folded preview still contains compatibility display behavior that should be
  reduced as physical scene geometry becomes authoritative.
- Saved/exported CSV metadata should continue to expose requested versus
  effective launch counts, source identity, terminal policy, media state, and
  event diagnostics.

## Removed Historical Branch Notes

The following root-level branch-note files were consolidated into this document
and removed to reduce branch-doc sprawl:

- `BEAM_SPLITTER_PHASE2_PLAN.md`
- `FOLDED_NATIVE_ANALYSIS_CONTINUATION.md`
- `GPU_ACCELERATION.md`
- `KRAKENOS_CORE_ALGORITHMS.md`
- `KRAKEN_LAYOUT_EDITOR_USAGE.md`
- `KRAKEN_UI_CORE_COVERAGE.md`
- `KRAKEN_UI_FUTURE_ROADMAP.md`
- `KRAKEN_UI_LAYOUT_EDITOR_REFACTOR_PLAN.md`
- `KRAKEN_UI_NONSEQUENTIAL_ARCHITECTURE.md`
- `KRAKEN_UI_NONSEQ_NORTH_STAR_STATUS.md`
- `KRAKEN_UI_PHASE1_PLAN.md`
- `KRAKEN_UI_PHASE7_PLAN.md`
- `KRAKEN_UI_PHASE8_PLAN.md`
- `KRAKEN_UI_PHASE9_THEME_PLAN.md`
- `KRAKEN_VS_OPTILAND_GAP_CLOSURE.md`
- `OPTIMIZATION_PLAN.md`
- `REPRODUCING_OPTIMIZATION_ON_X299-SSD.md`
- `BEAM_SPLITTER_IMPLEMENTATION_PLAN.org`
- `CAD_IMPORT_OVERLAY_PLAN.org`
- `KRAKEN_3D_GEOMETRY_REFACTOR_NOTE.org`
- `NONSEQUENTIAL_DISPLAY_REFACTOR_PLAN.org`

Kept intentionally:

- `README.md`, because it belongs to the upstream project-facing README.
- `docs/README.md`, because it belongs to the Sphinx documentation tree.

## Next Pipeline Step

Promote the remaining legacy compatibility state behind canonical events:

- remove or narrow scalar `PrevN`/last-index mirrors at UI analysis boundaries;
- ensure folded-preview-only display annotations are either backed by scene
  geometry or explicitly labeled as compatibility display data;
- add one validator that exports ray-event CSV rows from a saved layout and
  checks launch, terminal, branch, media, and interaction columns together.
- continue narrowing scalar raykeeper-array fallbacks to no-scene legacy
  compatibility paths only.

This keeps the architecture moving toward one scene/event truth source while
preserving exact sequential prescriptions as the ordered-path special case.
