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

| Area | Status | Progress | Next action |
| --- | --- | --- | --- |
| Upstream main integration | Triaged | `40%` | Continue selective integration. Packaging metadata and attachment cleanup are merged; runtime tracing/display cleanups from upstream need adapted validators before landing. |
| CadQuery/OCP topology study | Ready to start | `10%` | The CAD/STEP boundary is clean enough to begin a separate study. Use CadQuery/OCP only as an optional reference for STEP topology, face/edge selectors, tessellation, assembly traversal, and fixture generation; do not add it as a runtime dependency until package weight and topology preservation are proven. |
| External merge readiness | In progress | `70%` | Keep this README, Sphinx docs, validation commands, and generated reports aligned so a reviewer can evaluate scope and test coverage without following the entire development history. |

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
  element browser categories for Optical Element, Imaging Lens, and
  Camera/Detector.
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
- The `ui` extra installs UI/runtime dependencies, the optional optimizer
  backend dependency `pygmo`, and the optional `sv-ttk` theme dependency.
- If the Optimization panel reports that the backend is unavailable, confirm the
  active environment with `python -m KrakenOS.UI.validate_optimization_backend`.
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
| Focused contracts | Single-risk checks during development or review. | `python -m KrakenOS.UI.validate_fast_contracts --only ui-modular-maintainability` |
| Display-backed smoke | Open 3D, VTK, screenshots, STEP face picking, and visual regressions. | `python -m KrakenOS.UI.validate_step_carry_open3d_smoke` |
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
python -m py_compile KrakenOS/UI/layout_editor.py
```

Frequently useful targeted checks:

```bash
python -m KrakenOS.UI.validate_ui_modular_maintainability
python -m KrakenOS.UI.validate_ui_install_metadata
python -m KrakenOS.UI.validate_optimization_backend
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
- The optional `sv-ttk` theme adapter and public `.[ui]` install metadata.

The refactor is protected by `validate_ui_modular_maintainability`, widget
commit validators, row-spec contract validation, saved-layout literal
validation, CadQuery-readiness boundary validation, STEP face-direction service
validation, install metadata validators, and the fast contract runner. The next
maintainability work should remove transitional late-bound constants and helper
lookups, not move behavior back into `layout_editor.py`.

## Known Risks And Future Work

- Upstream main integration is selective. Runtime tracing, display, and test
  improvements from upstream should be merged only behind branch validators so
  non-sequential UI behavior is not overwritten.
- Some legacy compatibility paths remain for sequential/table workflows. New
  scene features should prefer SceneBundle, ray-event, row metadata, and CSV
  diagnostics instead of display-only state.
- CAD/STEP face topology remains a hard area. The branch supports face
  grouping, assignment, native export, and diagnostics, but future work should
  keep improving robust face/edge identity for vendor STEP files.
- Large-CAD Live Mode performance can still improve through mesh reuse and
  tighter invalidation. The debounce/cancellation contract exists; the next
  work should tune performance without changing physics state.
- White-beam prism dispersion is feasible but not yet complete as a polished
  workflow. It needs a wavelength-sampled source model, wavelength-aware display
  colors, detector spread analysis, and a validator for an equilateral prism.
- Full 3D CAD-style placement can continue to improve. The current branch has
  direct STEP import, placement, face assignment, snapping, handles, and browser
  state; future work can study CadQuery/OCP for better topology tools without
  adding a required dependency prematurely.

## Historical Notes

Older planning files were consolidated into this branch README to reduce
root-level document sprawl. Detailed day-by-day movement is preserved in git
history, validator names, Sphinx tutorials, and generated diagnostic reports
instead of being repeated here as a long progress table.

## Next Pipeline Step

Start the CadQuery/OCP topology study in a separate optional spike while
continuing to remove transitional late-bound service helper lookups. Keep the
runtime dependency graph unchanged until a small validator proves CadQuery adds
better STEP topology identity than the current PyVista/STL fallback path.
