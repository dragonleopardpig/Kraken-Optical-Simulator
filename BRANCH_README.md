# KrakenOS Non-Sequential UI Branch

Last updated: 2026-06-07

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

Completed work is summarized in prose where possible. The short status table
keeps the current gate signal visible for the just-finished STEP milestone,
CAD responsiveness, and intentionally deferred visual theming.

The upstream main integration gate and external merge readiness are complete.
Direct upstream merge was audited and intentionally avoided where it would
delete branch UI/CAD tooling; the safe replay now includes upstream-compatible
public API aliases, deterministic catalog ordering, `extract_ray_result`, pytest
smoke/API/invalid-trace/build-mode contracts, branch README validation commands,
and fast UI/non-sequential validators.

| Area | Status | Progress | Next action |
| --- | --- | --- | --- |
| Native STEP analytic reconstruction | Complete for supported axisymmetric lenses | `100% [##########]` | STEP topology is now imported before STL conversion, split/duplicated vendor faces are grouped into native optical surfaces, supported sphere/plane/B-spline surfaces are rebuilt as KrakenOS `SurfaceRow` prescriptions, B-spline faces are fitted into native asphere coefficients with residual diagnostics, cemented duplicate interfaces are collapsed into one internal surface, and geometry-only STEP files remain non-trace-ready until glass/materials are supplied. |
| Native STEP Open 3D promotion | Complete for supported axisymmetric lenses | `100% [##########]` | Imported STEP overlays can now be promoted directly from Open 3D into native KrakenOS analytic rows with an explicit glass/material sequence, while applying the Open 3D overlay placement/orientation as row `Tilt`/`Desp` values. If the user snapped a selected STEP face center to an optical axis, that stored face-center anchor is preserved exactly during promotion. Show Rays/Trace Now also prefer the same native analytic rows for transient axisymmetric lens previews, and saved single-row STEP/STL optical-solid lenses now get a trace-only native analytic expansion when the source STEP is reconstructable. STL optical-solid promotion remains available for prisms, beam splitters, and freeform solids that should stay mesh-backed. Source/fit diagnostics remain in metadata. |
| Open 3D CAD responsiveness hardening | Complete | `100% [##########]` | The reported Machine Vision 150 mm plus imported Aspherized Achromatic Lens workflow now has structured action timing, single-refresh Open 3D imports, cached CAD/STL artifacts, display-only hidden-ray placement and undo, grouped smooth CAD face picking, analytic face-ID edge/hover/pick routing for native STEP meshes, VTK-cell-to-grouped-face picking, axisymmetric lens patch grouping for split vendor optical faces, exterior-cap picking for round lens STEP bodies, round-lens axis-normal snapping, current-scene reuse for repeated Show Rays toggles, empty-gmsh-STL rejection, sidecar prescription warnings, per-bundle system/RayKeeper/mesh timing counters, repeated-mesh compatibility, batched slide-along-axis dragging, and pickable row-placement rotation arcs. Large camera CAD overlays now use a lightweight display proxy in Open 3D, and missing STEP display/axis caches warm in a subprocess instead of parsing in the Tk refresh path. Display-backed Pyrite 85 mm/120 mm replays now avoid foreground STEP parsing once the cache is ready; mesh transforms measured about 0.29 s/0.07 s for the 85/120 mm lens overlays and about 0.04 s for the proxied camera overlay on the test machine. Larger vendor assemblies should be treated as new performance fixtures rather than blocking this gate. |
| Final UI theming polish | Deferred outside this gate | `0% [..........]` | Keep the UI on native ttk for now. Revisit `sv-ttk` or another visual layer only after upstream review, CAD responsiveness, physics/display contracts, packaging, and docs are stable. |

The CadQuery/OCP topology study milestone is now complete for this branch
(`100%`). The branch keeps CadQuery/OCP as an optional future adapter, not a
runtime dependency, because the immediate responsiveness issue is addressed in
the current mesh path: `CadSceneCache` reuses STEP-derived triangle and face
outline artifacts across ordinary Open 3D refreshes, ordinary Open 3D passive
hover uses a rotation-handle actor pick list instead of dense CAD body picking,
right-click CAD face assignment defers feature scans until an explicit user
action, Open 3D-originated STEP imports refresh the 3D scene once instead of
through both the editor and inspector, transient STEP import/carry/drop remains
display-only and preserves the existing ray family while the component is being
placed, and an explicit optical-axis snap marks the transient optical STEP as a
physics-preview solid, exits carry mode, and keeps the full traced launch family
visible even when defocus means some rays miss the detector, while hidden-clipped
mode suppresses long missed/escaped terminal tails so the viewport does not turn
into a diagnostic fan. Show Rays and Trace Now include the placed transient STEP
without requiring row promotion first. When the placed optical STEP is a
supported axisymmetric lens, the transient preview is rebuilt as native
KrakenOS analytic rows before tracing so refractive rays see analytic
sphere/asphere normals instead of coarse STL triangle normals. Unsupported
solids still fall back to the established mesh-backed optical-solid path.
Saved layouts that already contain single-row promoted STEP/STL optical-solid
lenses use the same native analytic reconstruction as a trace-only expansion
when the original STEP path is available and reconstructable; the expansion
preserves total table track length and falls back to the saved mesh row if the
STEP is not trace-ready. This covers reopened vendor DCV/DCX lens rows that
would otherwise display as glass but trace against faceted STL normals or no
usable optical prescription. Open 3D display rows and placement handles remain
bound to the saved editable-table rows while those hidden analytic rows feed the
ray kernel, so a reopened STEP lens does not draw a duplicate analytic body or
rotate against shifted trace-only row indices. The saved-native display path
also discards trace-bundle surface meshes and rebuilds the visible CAD bodies
from the original promoted STEP/STL rows, preventing stale trace row indices
from being picked during Center Row -> Optical Axis. Saved-native row-face
hover outlines, assigned-face overlays, and virtual-plane overlays use the same
original file-backed row transform as the visible body, so a face highlight
cannot be drawn at a shifted trace-only row location. Stale transient STEP
overlays whose source path already exists as a promoted row are suppressed in
Open 3D and legacy 3D refreshes, so a saved lens is not drawn twice as both an
editable row and an imported-overlay ghost.
Trace Now also turns ray visibility on before rendering, and Undo/Redo clears
stale transient STEP physics-preview and rotation/carry state so a successful
trace cannot leave invisible geometry or floating handles behind. The
display-only STEP suppression check is tied to the current rendered mesh rows,
not stale live-trace row labels, and the transient STEP ray-tail trimming path
is now contract-checked as a local Open 3D service method call so it cannot
regress into a runtime-only editor name lookup.
Saved layout files now serialize in-repository camera, lens, optical, and LED
STEP assets as project-relative paths, keeping browser-loadable examples
portable across machines. The Open 3D Live Controls and Scene Components
side panels are now horizontal paned-window panes, so users can drag their
widths or hide either panel from the View toolbar while keeping the 3D viewport
expanded. The 2D layout projection control was removed: all 2D planes are now
always projections of the full traced 3D ray bundle, including saved layouts
that still carry the older projection-mode setting.
Repeated Show Rays toggles reuse the current traced scene instead of rebuilding
transient STEP physics. First-trace timing records live STEP row planning,
system build, ray tracing, SceneBundle projection, per-bundle trace
backend/ray-count durations, system-trace time, RayKeeper-push time, and mesh
ray-intersection duration summaries. The world-envelope sampler keeps the first
successful non-sequential trace instead of retracing the same bundle into the
display raykeeper. Optical-solid mesh face metadata is cached inside the built
non-sequential system; the chooser skips a second identical ray trace on the
selected mesh; intersection-normal lookup reuses the chooser's selected mesh ray
result for the same segment; and repeated non-sequential mesh chooser calls skip
PyVista normal-extraction compatibility checks once a mesh has been prepared.
Open 3D suppresses traced optical-axis guides for segments that remain on the
global axial direction while keeping genuinely bent post-surface axes for prism
cascades. Blank axial scenes keep only the global guide; saved penta cascades
intentionally show downstream exit-axis guides; refractive optical volumes and
source cone/fan spread do not create extra downstream guides from marginal
chief-ray tilt.
`python -m KrakenOS.UI.diagnose_open3d_hover_latency` reports the cache and
passive-hover contract for large vendor STEP-derived STL files. Round-lens
STEP hover/click/right-click selection now resolves grouped analytic lens-cap
records before raw VTK cells, so transparent achromats do not select side/rim
tessellation when the cursor is over an optical cap; the hover tooltip includes
the selected face ID before falling back to raw triangle features, and passive
hover over an imported STEP actor now displays the selected analytic face as a
translucent surface overlay instead of only a rim outline. Grouped analytic lens
face picking is also checked through an actual VTK actor/cell screenshot replay
at `attachment/open3d_lens_face_selection_snap/`. Promoted row-backed optical
STEP solids now preserve those analytic face groups in local row coordinates
instead of re-clustering the promoted STL into many small mesh fragments, so
Center Row, hover selection, and face-role editing still select the whole
front/rear/side face after promotion. Promoted prism rows now also use their
saved promoted mesh face IDs instead of stale runtime trace-mesh triangle
indices, hidden-ray views keep only one canonical global optical-axis guide,
Center Row mode clears transient/row placement handles, and Center Row face
picking ranks transparent overlapping CAD row faces by the projected face
anchor rather than the nearest actor. The mixed-prism validator also requires
row-face hover outlines to overlap the visible promoted row body, catching the
saved-layout shifted-outline regression shown by `attachment/mxied.py`. These
regressions are covered by
`python -m KrakenOS.UI.validate_open3d_center_row_face_visual` and
`python -m KrakenOS.UI.validate_open3d_mxied_prism_selection`, which save
face-hover and mixed-prism selection snapshots under
`attachment/open3d_center_row_face_visual/` and
`attachment/open3d_mxied_prism_selection/`. Open 3D left-drag camera rotation is
contract-checked with the restored screen-following sign convention.

The Tier 3 native STEP reconstruction path is now implemented for supported
axisymmetric optical lenses. `KrakenOS.UI.services.step_analytic_geometry`
imports STEP files with the available OpenCascade backend, walks solids and
faces before STL conversion, extracts analytic descriptors such as sphere,
cylinder, plane, and B-spline faces, removes duplicated cemented interior faces
from the outer pick set, and builds a face-tagged tessellation for display and
selection. Open 3D now consumes analytic face cell metadata for visible feature
edges, hover outlines, and display-mesh ray picking, and it adds a grouped
selection face index for axisymmetric lenses so split vendor B-spline patches
select as one optical face with a lens-axis normal. Analytic STEP bodies no
longer fall back to stale gmsh STL triangles for face selection; successful
analytic loads also invalidate the old STL cache entry.
`KrakenOS.UI.services.step_native_reconstruction` then reloads the same topology
with interior interfaces retained, groups split vendor patches into one optical
surface, collapses duplicated cemented faces into one native interface, fits
supported B-spline optical faces into KrakenOS-native `AspherData`
coefficients, and emits ordinary `SurfaceRow` prescriptions. The validator
`python -m KrakenOS.UI.validate_step_native_reconstruction` checks the
aspherized achromat STEP fixture: it rebuilds the front sphere, cemented sphere,
and split B-spline/asphere back surface as three native rows, while refusing
trace-ready status unless a material sequence such as `BK7`, `F2`, `AIR` is
supplied. Open 3D exposes the same path as `Promote STEP to Native Rows` in the
CAD/target menu and as `Native Rows` in the STEP element browser. The validator
`python -m KrakenOS.UI.validate_step_native_promotion` checks the interactive
promotion boundary: a display-only achromat STEP overlay becomes native analytic
KrakenOS rows, the overlay placement/orientation is applied to the generated row
`Tilt`/`Desp` values, a stored snapped face-center/axis anchor is used instead
of the looser overlay bounds center when available, the overlay is cleared when
requested, and the source path/material/reconstruction
diagnostics are preserved in row metadata.
Open 3D transient Show Rays/Trace Now now uses the same analytic reconstruction
for supported imported lens STEP overlays before falling back to mesh-backed
STL optical solids. `python -m KrakenOS.UI.diagnose_open3d_lens_ray_outlier`
captures the aspherized achromat fixture, snaps its front face to the global
axis, turns rays on, confirms the live trace backend is `native_analytic_rows`,
and fails if a large single-ray bend reappears.
This keeps the North Star rule intact: imported STEP state may become a native
optical prescription, but missing material data or poor surface fits produce
diagnostics instead of plausible wrong physics.

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
verifies imported STEP rotation without a full scene/physics rebuild, simulates
a small display-only placement drop, applies Ctrl-Z undo,
deselects it, and prints the slowest timed stages.

The same timing tool is also used for the PYRITE machine-vision surrogate
layouts:

```bash
python -m KrakenOS.UI.diagnose_open3d_action_timing --layout "Machine Vision 85 mm Pyrite (Datasheet 1X)" --step attachment/Lens/1072517_00165969_001.stp --output /tmp/kraken_open3d_pyrite85_timing.json
python -m KrakenOS.UI.diagnose_open3d_action_timing --layout "Machine Vision 120 mm Pyrite (Datasheet 1X)" --step attachment/Lens/1097277_00155156_002.stp --output /tmp/kraken_open3d_pyrite120_timing.json
```

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
- YZ, XZ, and XY 2D projections generated from the traced 3D scene. The 2D
  plane selector always projects the full traced 3D ray bundle, and 2D/Open 3D
  use the same bounded ray display logic for escaped tails and detector misses.
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
- Quick Estimation: a live object/image conjugate + FOV solver in Open 3D for
  finite-conjugate (machine-vision) imaging. The sensor is pinned via the
  left-panel ``Real Image Semi-Height`` field; dragging or typing a conjugate
  thickness handle re-solves its partner for focus, and FOV = sensor / |m|
  follows the magnification. Right-clicking the Object/Image plane or its arrow
  sets a target Object Height (showing sensor over/underfill), snaps both gaps
  to the unique conjugate pair for that FOV, or opens a configuration table.
  Dragging into a forbidden region (working distance below the focal length, no
  real image) flashes the arrow red; with Live Mode on the geometry retraces
  during the drag. See ``docs/source/manual/quick_estimation.rst`` and the
  ``validate_open3d_quick_estimation_conjugate`` validator (harness Phase 34).
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
| Focused contracts | Single-risk checks during development or review. | `python -m KrakenOS.UI.validate_fast_contracts --only ui-modular-maintainability`, `python -m KrakenOS.UI.validate_fast_contracts --only optimization-controls`, `python -m KrakenOS.UI.validate_fast_contracts --only step-native-reconstruction`, `python -m KrakenOS.UI.validate_fast_contracts --only step-native-promotion`, `python -m KrakenOS.UI.validate_fast_contracts --only open3d-lens-step-face-pick`, `python -m KrakenOS.UI.validate_open3d_saved_step_native_trace`, `python -m KrakenOS.UI.validate_axis_slide`, or `python -m KrakenOS.UI.validate_fast_contracts --only five-penta-with-lens-layout` |
| Display-backed smoke | Open 3D, VTK, screenshots, STEP face picking, and visual regressions. | `python -m KrakenOS.UI.validate_step_carry_open3d_smoke`, `python -m KrakenOS.UI.capture_open3d_lens_face_selection_snap`, `python -m KrakenOS.UI.validate_open3d_center_row_face_visual`, `python -m KrakenOS.UI.validate_open3d_mxied_prism_selection`, `python -m KrakenOS.UI.diagnose_open3d_lens_ray_outlier` |
| Open 3D responsiveness replay | Timed replay of Machine Vision 150 mm + imported optical STEP import/select/deselect, plus Pyrite 85 mm/120 mm vendor STEP overlays. | `python -m KrakenOS.UI.diagnose_open3d_action_timing --output /tmp/kraken_open3d_action_timing_report.json`, `python -m KrakenOS.UI.diagnose_open3d_action_timing --layout "Machine Vision 85 mm Pyrite (Datasheet 1X)" --step attachment/Lens/1072517_00165969_001.stp --output /tmp/kraken_open3d_pyrite85_timing.json`, `python -m KrakenOS.UI.diagnose_open3d_action_timing --layout "Machine Vision 120 mm Pyrite (Datasheet 1X)" --step attachment/Lens/1097277_00155156_002.stp --output /tmp/kraken_open3d_pyrite120_timing.json` |
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
python -m KrakenOS.UI.validate_attachment_paths
python -m KrakenOS.UI.validate_optimization_backend
python -m KrakenOS.UI.validate_cad_scene_cache
python -m KrakenOS.UI.validate_step_analytic_import
python -m KrakenOS.UI.validate_open3d_optical_import_carry_first
python -m KrakenOS.UI.validate_3d_interaction_contract
python -m KrakenOS.UI.validate_native_nonseq_closure
python -m KrakenOS.UI.validate_2d_3d_projection_sync
python -m KrakenOS.UI.validate_infinity_field_launch
python -m KrakenOS.UI.validate_row_spec_contracts
python -m KrakenOS.UI.validate_open3d_step_face_direction
python -m KrakenOS.UI.validate_open3d_face_assignment_sampling_stability --focused
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

### Slicer-pattern adoption (Phase 1-11)

The Open 3D inspector now adopts the core data-model / representation /
widget contracts from 3D Slicer's MRML stack. The patterns were ported
incrementally so each phase is a small commit that runs against the
existing validator set and adds a service class under
`KrakenOS/UI/services/`:

- `open3d_selection_model.SelectionModel` is the source of truth for
  row, ray, step-overlay, and optical-axis picks. The five
  `Kraken3DInspector._picked_*` fields are `@property` shims over the
  model, mirroring `vtkMRMLMarkupsNode`'s data role. Scene rebuilds no
  longer clear the picks; the model survives `RemoveAllViewProps()` and
  the refresh service reapplies highlights through
  `_set_ray_highlight` / `_set_optical_axis_highlight`. Stale picks for
  rays or axes that no longer exist in the rebuilt scene are dropped
  instead of haunting the model invisibly.
- `open3d_selection_view.SelectionView` is the observer hook on the
  model. `open3d_selection_representation.SelectionRepresentation`
  carries the actor-styling logic (`apply_row_selection`,
  `apply_ray_selection`, `apply_step_selection`,
  `apply_optical_axis_selection`); the inspector's
  `_set_*_highlight` methods are now thin facades over the
  representation, matching `vtkMRMLAbstractWidgetRepresentation`.
- `open3d_interaction_event.InteractionEventData` carries the
  pre-resolved display xy, world xyz, picker actor, pick target, and
  modifier keys for an interaction event. The companion
  `PickClassifier` collapses an actor key against every
  `_actor_*_map` dict the inspector keeps and emits a single
  `PickTarget` enum value plus payload, ported from
  `vtkMRMLInteractionEventData` + `CanProcessInteractionEvent`.
- `open3d_interaction_mode.InteractionMode` enumerates the 14
  mutually exclusive inspector modes; `InteractionModeState` is the
  observable holder. The nine `_*_pick_mode` booleans on the
  inspector are now `@property` facades backed by the state, so every
  set/clear notifies state observers. `current_interaction_mode()`
  reports the active mode in one place.
- `open3d_abstract_widget.AbstractWidget` + `WidgetRegistry`
  reproduce `vtkMRMLAbstractWidget`'s bidding interface. Concrete
  widgets ship for `THICKNESS_DIMENSION`,
  `PLACEMENT_ROTATE`/`PLACEMENT_TRANSLATE`, and
  `STEP_ROTATE_HANDLE`; each migrates the matching inline ladder from
  `Open3DInteractionService._on_left_button_press` (the four ladders
  are now removed; visual-only handle actors fall through to the
  remaining workflows by design).
- `open3d_camera_state.CameraState` plus
  `capture_camera_state` / `apply_camera_state` replace the dict of
  tuples that `Open3DSceneRefreshService` used to capture and restore
  the active VTK camera around a scene rebuild, matching
  `vtkMRMLCameraNode`'s persistence surface.
- `open3d_application_logic.Open3DApplicationLogic` is the
  `vtkMRMLApplicationLogic` counterpart: a small facade that exposes
  the inspector's high-level workflows (`current_mode`, `is_busy`,
  `cancel_active_operation`, `start_*_pick`, plus accessors for the
  Phase 1-7 services) so non-Tk callers can drive the 3D inspector
  without importing the 9000-line widget class.

Each phase preserves behaviour and was validated against
`validate_open3d_handle_anchor`, `validate_open3d_live_mode`,
`validate_open3d_step_state_service`, and the validator that exercises
the migrated handler. The follow-on opportunities are widget-based
manipulators for the placement handles (today they still pop the
inspector's `_apply_scene_placement_*_handle` methods rather than
moving the actors themselves), an observer-driven cursor/mode-badge
manager hooked to `InteractionModeState`, and a `DisplayableManager`
service that consolidates the actor-map ownership currently scattered
across `Open3DSceneRefreshService` and the inspector.

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

## Bug Tracking (added 2026-06-02)

User-flagged Open 3D bugs now get a tracked record under `bugs/` (see
`bugs/README.md` for the register and per-bug workflow). The cadence per bug:
document `bugs/NNNN-slug.md`, fix the root cause, write a small specific test,
add a numbered phase to
`KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py`, then regenerate
the pre-push gate baseline (`python tools/penta_validator_gate.py
--update-baseline`). The comprehensive validator is gated on push by
`.githooks/pre-push` -> `tools/penta_validator_gate.py`, which boots Xvfb and
blocks only a PASS->FAIL flip versus `tools/penta_validator_baseline.json`.

**Visual bugs require an image-snapshot test, not just vtkProperty assertions.**
The first all-red fix (0001) passed every property assertion yet a second actor
still painted a red block (0002) — only a rendered PNG caught it. So a visual
fix must render the scene off-screen to a PNG, count pixels (e.g. negligible
red / pink fill present), AND be visually confirmed by eye. Records so far:

- `bugs/0001` — selecting an analytic lens rendered solid red (red triangle
  wireframe over the pink fill). Fixed: flag glassy lens bodies and suppress
  their per-triangle edges on selection.
- `bugs/0002` — a selected analytic lens left a "ghost red block": selection
  was resurrecting a hidden, baseline-invisible companion surface (opacity 0)
  by bumping its opacity and painting red edges. Fixed: `_set_row_actor_selected`
  early-outs for any actor whose baseline opacity is ~0. Guarded by
  `validate_open3d_analytic_lens_selection_snapshot` and the Phase 10 image
  check.

## Requested UI Changes (2026-06-02)

User-requested behavior changes. Status: **#2 and #3 implemented; #1 pending.**

### 1. Slide-along-axis needs visible drag handles (approved to build — PENDING)

Today slide-along-axis is a *mode* (`slide_along_axis_mode_var` in
`open3d_inspector.py`), not a handle: with the mode on, the user clicks an
eligible promoted optical body and drags along Z (status line "click an optical
element body and drag along Z"). There is no on-screen grip, so the feature is
undiscoverable — the user expected a handle to "pop up" and saw nothing.
**Build:** a visible, draggable axial slide handle per eligible element (an
actor grip, in the same family as the existing placement/rotation handles in
the Slicer-pattern `open3d_abstract_widget` / `WidgetRegistry`), so sliding is
direct instead of a hidden drag mode. This is a *visual* change, so it must
follow the bug-tracking workflow above: image-snapshot test + a penta-validator
phase. (Context recorded in `bugs/0002`, "Issue 2".)

### 2. STEP import should start in carry mode, not auto-snap to the optical axis — DONE

**Root cause:** the auto-promote-on-import added with the glassy-analytic work
(`b046889`) ran a modal promote dialog *inside* `import_optical_step`; accepting
it promoted the overlay to analytic Standard rows and snapped the body onto the
optical axis before the inspector's carry-follow ever started — pre-empting the
carry-first orientation step. **Fix:** `import_optical_step` no longer
auto-promotes or auto-snaps; the overlay arrives in carry mode with rotation
handles (the inspector import handler starts `_start_step_carry_follow`), so the
user corrects orientation first. Promotion + axis-snap is now the explicit
"Promote STEP to Analytic Surfaces" action, whose glass-sequence prompt still
pre-fills from a Zemax `.zmx` sidecar when present. The now-dead import-time
dialog methods (`_offer_auto_promote_step_to_analytic`,
`_ask_analytic_promote_confirm`) were removed. Guarded by
`validate_open3d_optical_import_carry_first`.

### 3. Auto-promote glass prompt assumes a single element — DONE

Already implemented by the analytic-promote work (`b046889`): the promote dialog
asks for a comma-separated glass **sequence** ("N interior region(s)") matched
to the reconstructed surface count, pre-fills from a Zemax sidecar, and the
promote service **validates** the count against the detected interfaces
(`step_overlay_promotion.py` raises if fewer glasses than regions are given, so
a cemented doublet/triplet needs `N-BK7, N-SF2` / three names). The native
reconstruction (`step_native_reconstruction`) supplies the region count via
`required_glass_count`. (This item predated the implementation; recorded here as
closed.)

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

Active near-term UI work is the three items in **Requested UI Changes
(2026-06-02, pending)** above: visible slide-along-axis handles, carry-first
STEP import (no auto-snap to the optical axis), and a multi-glass promote prompt
for cemented doublets/triplets. The slide-handle work is approved; the other two
need confirmation of the exact behavior before implementation.
