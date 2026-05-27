# KrakenOS Non-Sequential UI Branch

Last updated: 2026-05-27

This document summarizes the `nonseq-display-refactor` branch. The upstream
`README.md` is intentionally left unchanged; this branch README is the public
entry point for the new UI architecture, branch capabilities, installation
steps, validation plan, and remaining gaps.

## North Star

The UI should be non-sequential by design. A KrakenOS layout is a scene of
optical objects, sources, detectors, coatings, masks, STL solids, STEP solids,
and path metadata. Sequential ray tracing remains important, but it should be
treated as the axial ordered-surface special case of the same scene workflow.

Six invariants define the target architecture:

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
   polarization, total internal reflection, beam splitting, or detector
   termination. Ambiguous geometry should produce diagnostics instead of
   silently drawing a plausible but wrong path.
5. The UI codebase must stay modular, production-ready, and human-maintainable.
   Large interaction surfaces should be split into services, panels, widgets,
   validators, and documented contracts with clear ownership boundaries, so
   future physics and CAD features do not accumulate inside one monolithic
   editor file.
6. Production-ready test plans are first-class branch artifacts. Each
   user-facing workflow or physics contract must have a named validator,
   snapshot/report fixture, or documented manual test. The validators count as
   executable test-plan evidence, but merge-ready work should also state the
   command, fixture, and risk covered so upstream reviewers can audit the plan
   without reading every script.

Practical rule:

- Use scene/non-sequential tracing whenever the user creates a physical source,
  beam splitter, target surface, probabilistic non-sequential coating, STL/STEP
  object, mirror fold, tilt/decenter scene, or detector/path workflow.
- Keep exact sequential tracing for conventional lens-design prescriptions and
  paraxial/wavefront analyses that explicitly depend on ordered surfaces.
- Never hide KrakenOS-native state behind a UI-only abstraction without
  preserving it in row metadata, scene graph diagnostics, raykeeper metadata, or
  CSV/export output.
- Treat validators as the executable part of the test plan. Every proposed
  merge should map changed behavior to at least one validator, snapshot
  diagnostic, or explicit manual check.

## Branch Status

The major North Star work items are complete for this branch: native
non-sequential scene tracing, sequential-as-special-case workflows, 3D scene
truth with YZ/XZ/XY projections, separate sources/objects/detectors, event-law
diagnostics, Open 3D authoring, STEP/CAD optical-solid placement, beam-splitter
and detector workflows, fabrication drawing export, optimization/tolerance
workflows, and the production-readiness refactor of the UI coordinator.

Completed work is no longer listed as 100% progress rows. The active status
table is reserved for items that are still incomplete or intentionally
deferred.

The upstream main integration gate and external merge readiness are complete.
Direct upstream merge was audited and intentionally avoided where it would
delete branch UI/CAD tooling; the safe replay now includes upstream-compatible
public API aliases, deterministic catalog ordering, `extract_ray_result`, pytest
smoke/API/invalid-trace/build-mode contracts, branch README validation commands,
and fast UI/non-sequential validators.

| Area | Status | Progress | Next action |
| --- | --- | --- | --- |
| Open 3D CAD responsiveness hardening | Complete | `100% [##########]` | The reported Machine Vision 150 mm plus imported Aspherized Achromatic Lens workflow now has structured action timing, single-refresh Open 3D imports, cached CAD/STL artifacts, display-only hidden-ray placement and undo, grouped smooth CAD face picking, round-lens axis-normal snapping, current-scene reuse for repeated Show Rays toggles, empty-gmsh-STL rejection, sidecar prescription warnings, per-bundle system/RayKeeper/mesh timing counters, and a repeated-mesh compatibility fast path. The headless replay reduced the first live STEP non-sequential trace from about 16.5 s to about 2.7 s, with the full Open 3D refresh around 3.6 s on the test machine; larger vendor assemblies should be treated as new performance fixtures rather than blocking this gate. |
| Final UI theming polish | Deferred outside this gate | `0% [..........]` | Keep the UI on native ttk for now. Revisit `sv-ttk` or another visual layer only after upstream review, CAD responsiveness, physics/display contracts, packaging, and docs are stable. |

The CadQuery/OCP topology study milestone is now complete for this branch
(`100%`). The branch keeps CadQuery/OCP as an optional future adapter, not a
runtime dependency, because the immediate responsiveness issue is addressed in
the current mesh path: `CadSceneCache` reuses STEP-derived triangle and face
outline artifacts across ordinary Open 3D refreshes, ordinary Open 3D passive
hover uses a rotation-handle actor pick list instead of dense CAD body picking,
right-click CAD face assignment defers feature scans until an explicit user
action, Open 3D-originated STEP imports refresh the 3D scene once instead of
through both the editor and inspector, hidden-ray transient STEP placement/drop
does not trigger a physics trace until the user enables rays, Live Mode, or
Trace Now, repeated Show Rays toggles reuse the current traced scene instead of
rebuilding transient STEP physics, first-trace timing now records live STEP row
planning, system build, ray tracing, SceneBundle projection, and per-bundle
trace backend/ray-count durations, the world-envelope sampler keeps the first
successful non-sequential trace instead of retracing the same bundle into the
display raykeeper, optical-solid mesh face metadata is cached inside the built
non-sequential system, the chooser skips a second identical ray trace on the
selected mesh, intersection-normal lookup reuses the chooser's selected mesh
ray result for the same segment, axial external optical-solid exit segments
remain pickable as Open 3D optical axes for prism cascades, non-sequential
trace timing now includes per-bundle system-trace, RayKeeper-push, and mesh
ray-intersection duration summaries, repeated non-sequential mesh chooser calls
skip PyVista normal-extraction compatibility checks once a mesh has been
prepared, and
`python -m KrakenOS.UI.diagnose_open3d_hover_latency` reports the cache and
passive-hover contract for large vendor STEP-derived STL files.

Open 3D responsiveness timing is written to:

```text
~/.cache/krakenos/logs/open3d_timing_latest.jsonl
```

The reported Machine Vision 150 mm / Aspherized Achromatic Lens workflow can be
replayed under Xvfb or a real display:

```bash
python -m KrakenOS.UI.diagnose_open3d_action_timing --output /tmp/kraken_open3d_action_timing_report.json
```

The replay loads the Machine Vision 150 mm measured layout, opens Open 3D,
hides rays and thickness overlays, adds the optical STEP component, selects it,
verifies hidden-ray imported STEP rotation without a full scene/physics
rebuild, simulates a small display-only placement drop, applies Ctrl-Z undo,
deselects it, and prints the slowest timed stages.

## KrakenOS Base Features

These are the core capabilities KrakenOS already provides as an optical
simulation library and that this branch builds on:

- Exact sequential and non-sequential ray tracing through ordered optical
  systems, tilted/decentered surfaces, off-axis layouts, and 3D geometry.
- Surface definitions for spherical, conic/aspheric, Zernike, user-defined, and
  mathematically described optical shapes, with apertures, masks, coatings, and
  diffraction/scatter hooks.
- Glass catalog support through AGF/ZMF catalog data, wavelength-dependent
  refractive index handling, material names, and atmospheric dispersion tools.
- STL solid support for optical/mechanical geometry, including optical
  properties attached to 3D solid elements.
- RayKeeper storage for traced ray coordinates and directions, plus Matplotlib,
  VTK, PyVTK, and PyVista based 2D/3D display utilities.
- Pupil sampling, field sampling, Gaussian beam helpers, random source
  generation, paraxial matrix tools, entrance/exit pupil calculations, and
  classic lens-design calculations.
- Wavefront, Zernike, Seidel, PSF, spot, phase, and RMS analysis utilities.
- Stock lens catalog data, examples, provisional user manuals, and Python
  scripting workflows for building optical systems directly with the KrakenOS
  API.

## Branch Feature Additions

### UI And Scene Workflow

- A Tk/ttk layout editor with spreadsheet-style optical prescriptions, undo,
  redo, copy/paste, grouping, surface dialogs, context menus, and immediate
  commit behavior for text entries and table cells.
- A non-sequential scene pipeline where sources, targets, detectors, optical
  solids, face roles, placement anchors, path metadata, and ray events survive
  in row metadata, SceneBundle records, raykeeper/event records, diagnostics,
  and CSV/export output.
- YZ, XZ, and XY 2D projections generated from the traced 3D scene. The
  projection policy is user-selectable, and 2D/Open 3D use the same bounded ray
  display logic for escaped tails and detector misses.
- Open 3D authoring with direct view buttons, live controls, ray visibility
  toggles, explicit ray-pick mode, bottom-status ray terminal summaries, optical
  axis guides, hover diagnostics, selectable STEP/CAD faces, and docked STEP
  scene component browser categories for editable-table rows, transient STEP
  imports, promoted optical solids, grouped table elements with expandable
  surface children, Optical Element, Imaging Lens, and Camera/Detector entries.
- Direct STEP import from Open 3D, transient placement, hold-drag movement,
  Esc cancellation, blank-click deselection, middle-drag CAD-style pan,
  surface-normal-to-optical-axis snapping, centered surface-to-axis snapping,
  face-role assignment by right-click, and promotion into persistent
  row-backed optical-solid rows.
- Transparent optical STEP bodies with stronger feature edges, face tint
  overlays for assigned functions, optional rotation/placement handles, and
  editable Open 3D thickness dimension arrows linked back to the table.
- Sphinx tutorials and case studies for vendor prism placement, right-angle
  prism TIR, Mach-Zehnder and Michelson workflows, Gaussian beam expansion,
  lens drawing export, tolerance Monte Carlo, Double Gauss analysis, Machine
  Vision and F-theta galvo scanner workflows, and 3D hardware alignment.

### Non-UI, Core, And Analysis Additions

- A formal optimization package under `KrakenOS/Optimization` with variables,
  operands, merit functions, evaluators, pygmo adapters, and an example
  doublet optimizer. The UI exposes this through an optimization panel, but the
  backend is usable as normal Python code.
- Tolerance analysis services for Monte Carlo runs, compensator sweeps,
  multi-compensator solves, tolerance stack-up reports, dashboards, and CSV
  export.
- Lens Fabrication Drawing export with editable drawing surface properties,
  PDF drawing packages, assembly documentation, and JSON sidecars for repeatable
  fabrication metadata.
- Hardened non-sequential physics contracts: signed outgoing ray directions,
  scalar Snell finite-vector handling near critical angles, scene-scaled
  near-hit rejection, same-surface self-hit handling, closed-solid media
  transitions, detector/Image terminal policy, and ray-event diagnostics.
- Beam-splitter and path workbench support for reflected/transmitted child
  branches, split ratio/loss/phase metadata, throughput, Gaussian q, detector
  maps, coherent detector fields, diffraction detector fields, path PSF, and
  path MTF.
- Source/object/detector analysis for multi-source illumination, detector
  aperture hit/miss reporting, vignetting, source power summaries, footprint
  coverage, and detector miss geometry.
- CAD/STEP services for STEP overlay import, row-backed promotion, face
  metadata, native STEP export where available, faceted fallback export, ray
  tube export, and prism/cascade diagnostics.
- Metadata services for error maps, coatings, metal catalogs, beam-splitter
  settings, scatter/BRDF settings, stock-lens catalogs, Zemax prescription
  import, Zemax wavefront/rayfile workflows, source modeling, and layout file
  writing.
- A fast validation runner and many targeted validators that exercise these
  contracts without opening the full UI unless a display-backed smoke test is
  specifically required.

## Installation

### Regular Python Users

Use a normal virtual environment first. Python 3.10 to 3.12 is the safest
starting range for broad binary-wheel availability; Python 3.13 is used in the
current local Nix environment but may have fewer third-party CAD wheels.

```bash
git clone https://github.com/Garchupiter/Kraken-Optical-Simulator.git
cd Kraken-Optical-Simulator
git checkout nonseq-display-refactor

python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip "setuptools<82" wheel
python -m pip install -e ".[ui]"
python -m KrakenOS.UI.validate_ui_install_runtime
python -m KrakenOS.UI.layout_editor
```

Before a packaged branch release exists, an editable Git install is also
supported:

```bash
python -m pip install -e "git+https://github.com/Garchupiter/Kraken-Optical-Simulator.git@nonseq-display-refactor#egg=KrakenOS[ui]"
```

Notes:

- The desktop UI uses Tkinter. If `import tkinter` fails, install your
  operating system's Tk package and refresh the virtual environment.
- The `ui` extra installs UI/runtime dependencies and the optional optimizer
  backend dependency `pygmo`. The custom ttk visual theme is deferred to the
  final polish milestone and is not part of the current `ui` extra.
- `Start Optimization` performs the optimizer backend preflight automatically.
  While running the same button changes to `Stop Optimization`; if the backend
  is unavailable, confirm the active environment with
  `python -m KrakenOS.UI.validate_optimization_backend`.
- STEP/IGES CAD import benefits from an OpenCascade/pythonocc-style backend.
  STL import and cached STL workflows remain available without STEP/IGES
  support.
- CPU tracing remains the default reliable path. Optional GPU tracing requires
  a compatible CUDA/CuPy environment.

### Nix Or Devenv Users

The branch includes a `devenv.nix` environment for contributors who prefer
Nix-managed VTK/Tk, CAD, and documentation dependencies.

```bash
devenv shell
kraken-install
python -m KrakenOS.UI.layout_editor
```

Useful optional commands:

```bash
kraken-install-docs
kraken-install-notebooks
kraken-vtk-tk-check
```

## Production Test Plan

Yes: the branch validators count as test-plan evidence. They are the executable
part of the plan. For upstream-quality merge review, each change should still
state which validator or manual check covers which risk.

Test-plan tiers:

| Tier | Purpose | Example commands |
| --- | --- | --- |
| Fast contracts | Fixture-light, no-display checks for normal code changes. | `python -m KrakenOS.UI.validate_fast_contracts` |
| Upstream-compatible pytest | Public API, package data, invalid traces, and build-zero contracts from upstream main adapted to the branch. | `python -m pytest tests/test_public_api.py tests/test_smoke.py tests/test_invalid_trace_results.py tests/test_build_modes.py` |
| Focused contracts | Single-risk checks during development or review. | `python -m KrakenOS.UI.validate_fast_contracts --only ui-modular-maintainability`, `python -m KrakenOS.UI.validate_fast_contracts --only optimization-controls`, `python -m KrakenOS.UI.validate_fast_contracts --only open3d-lens-step-face-pick`, or `python -m KrakenOS.UI.validate_fast_contracts --only five-penta-with-lens-layout` |
| Display-backed smoke | Open 3D, VTK, screenshots, STEP face picking, and visual regressions. | `python -m KrakenOS.UI.validate_step_carry_open3d_smoke` |
| Open 3D responsiveness replay | Timed replay of Machine Vision 150 mm + imported optical STEP import/select/deselect. | `python -m KrakenOS.UI.diagnose_open3d_action_timing --output /tmp/kraken_open3d_action_timing_report.json` |
| CAD/prism physics | Real STEP/STL geometry, prism cascades, face roles, and ray-event audits. | `python -m KrakenOS.UI.validate_five_penta_prism_cascade` |
| Install/package | Public `.[ui]` metadata and runtime dependency checks. | `python -m KrakenOS.UI.validate_ui_install_runtime` |
| Docs/tutorials | Sphinx pages and generated tutorial assets. | `sphinx-build -b html docs/source docs/build/html` |
| Manual review | Interactions that still need human CAD/UI judgment. | Record layout, screenshots, commands, and observed behavior in the merge note. |

Minimum merge checklist:

- List the user-facing behavior changed.
- List the command(s) run and whether they passed.
- Link or name any generated screenshot/report artifact.
- State what was not tested and why.
- For physics/display work, confirm that ray events, 2D projection, Open 3D
  display, Ray Inspector/CSV metadata, and saved layout reload all agree or
  explicitly document the remaining gap.

## Validation Commands

Start here for most changes:

```bash
python -m KrakenOS.UI.validate_fast_contracts
python -m KrakenOS.UI.validate_fast_contracts --list
python -m KrakenOS.UI.validate_fast_contracts --subprocess
python -m pytest tests/test_public_api.py tests/test_smoke.py tests/test_invalid_trace_results.py tests/test_build_modes.py
python -m py_compile KrakenOS/UI/layout_editor.py
```

Frequently useful targeted checks:

```bash
python -m KrakenOS.UI.validate_ui_modular_maintainability
python -m KrakenOS.UI.validate_ui_install_metadata
python -m KrakenOS.UI.validate_optimization_backend
python -m KrakenOS.UI.validate_cad_scene_cache
python -m KrakenOS.UI.validate_3d_interaction_contract
python -m KrakenOS.UI.validate_native_nonseq_closure
python -m KrakenOS.UI.validate_2d_3d_projection_sync
python -m KrakenOS.UI.validate_infinity_field_launch
python -m KrakenOS.UI.validate_row_spec_contracts
python -m KrakenOS.UI.validate_open3d_step_face_direction
python -m KrakenOS.UI.validate_open3d_thickness_dimensions
python -m KrakenOS.UI.validate_lens_drawing_properties
python -m KrakenOS.UI.validate_lens_drawing_pdf_case_study
python -m KrakenOS.UI.validate_folded_mirror_projection_parity
python -m KrakenOS.UI.validate_five_penta_prism_cascade
python -m KrakenOS.UI.validate_five_penta_native_step_export
```

Display-backed Open 3D checks require a real X display or Xvfb:

```bash
python -m KrakenOS.UI.validate_step_carry_open3d_smoke
python -m KrakenOS.UI.validate_open3d_ray_toggle_scene_retention
python -m KrakenOS.UI.capture_open3d_step_workflow_screenshots
python -m KrakenOS.UI.capture_penta_mirror_leak_diagnostic
```

The generated reports under `attachment/` are useful for local debugging, but
they are not automatically tracked unless a fixture is intentionally promoted.

## Production Readiness Refactor

The production-readiness pass is complete for the current branch goal. The main
`layout_editor.py` file has been reduced from a monolithic editor into a thin
Tk coordinator of roughly three thousand lines. Operational behavior now lives
in more than one hundred focused modules under `KrakenOS/UI/services`,
`KrakenOS/UI/panels`, and `KrakenOS/UI/widgets`.

The split now covers:

- Open 3D trace refresh, live refresh, scene refresh, mouse bindings,
  interaction routing, face assignment, STEP state, STEP rotation handles,
  carry grips, and thickness dimensions.
- Source modeling, trace preview sampling, scene-bundle display, 2D projection,
  folded preview geometry, layout plot interaction, table/workbench behavior,
  shell controls, import/export, file writing, settings, and results display.
- Optical-solid geometry/workflow, CAD/STEP export, prism fixtures, face
  direction, ray display geometry, non-sequential scene graph records, and ray
  inspector records.
- Analysis display, analysis reports, analysis compute workflow, geometric
  analysis, paraxial tools, optimization preflight, tolerance modeling,
  tolerance analysis, and tolerance stack-up reporting.
- Advanced surface attribute normalization, row-spec signatures, saved-layout
  literal serialization, CAD cache paths, STEP overlay labels, and scalar-trace
  decisions as reusable service contracts instead of editor-local helpers.
- Reusable Tk controls for commit bindings, commit-aware entry/combobox
  helpers, table cell editors, menu controls, and tooltips.
- A native ttk visual baseline, public `.[ui]` install metadata, and a dormant
  theme-adapter hook for the final polish milestone.

The refactor is protected by `validate_ui_modular_maintainability`,
`validate_3d_interaction_contract`, widget commit validators, row-spec contract
validation, saved-layout literal validation, CadQuery-readiness boundary
validation, STEP face-direction service validation, install metadata
validators, and the fast contract runner. The broad 3D interaction contract now
audits the modular Open 3D services directly, including decorated click
handlers, STEP rotation handles, placement handles, ray-pick gating, thickness
editing, and center-to-axis workflows. The next maintainability work should
remove transitional late-bound constants and helper lookups, not move behavior
back into `layout_editor.py`.

## Known Risks And Future Work

- Upstream main integration is selective. Runtime tracing, display, and test
  improvements from upstream should be merged only behind branch validators so
  non-sequential UI behavior is not overwritten.
- Some legacy compatibility paths remain for sequential/table workflows. New
  scene features should prefer SceneBundle, ray-event, row metadata, and CSV
  diagnostics instead of display-only state.
- CAD/STEP face topology remains a hard area, but the branch now has the
  current mesh-path responsiveness foundation in place. The branch supports
  face grouping, assignment, native export, diagnostics, cached display/pick
  artifacts, and the Sphinx ``Responsive STEP Handling Architecture`` note.
- Large-CAD Live Mode performance can still improve through mesh reuse and
  tighter invalidation. The debounce/cancellation contract exists; the next
  work should tune performance without changing physics state.
- White-beam prism dispersion is feasible but not yet complete as a polished
  workflow. It needs a wavelength-sampled source model, wavelength-aware display
  colors, detector spread analysis, and a validator for an equilateral prism.
- Full 3D CAD-style placement can continue to improve. The current branch has
  direct STEP import, placement, face assignment, snapping, handles, and browser
  state for both transient imports and row-backed editable-table components;
  CadQuery/OCP remains a long-horizon optional adapter if the current
  OpenCascade/mesh cache boundary proves insufficient for exact topology tools.

## Historical Notes

Older planning files were consolidated into this branch README to reduce
root-level document sprawl. Detailed day-by-day movement is preserved in git
history, validator names, Sphinx tutorials, and generated diagnostic reports
instead of being repeated here as a long progress table.

## Next Pipeline Step

The upstream integration and external merge-readiness gates are complete for
this branch milestone. The next sensible step is to prepare an upstream-facing
merge note that names the branch contracts, test commands, known deferred
items, and screenshots/reports a reviewer should inspect. Keep the CAD
scene-cache boundary, passive-hover handle-pick contract, and hover-latency
diagnostic intact during any follow-up cleanup.
