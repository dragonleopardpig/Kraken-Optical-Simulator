# KrakenOS Non-Sequential UI Branch

Last updated: 2026-05-18

This document summarizes the `nonseq-display-refactor` branch. The upstream
`README.md` is intentionally left unchanged; this branch README is the public
entry point for the new UI architecture, current capabilities, installation
steps, validation commands, and remaining gaps.

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
| Native non-sequential tracing | Near complete | `█████████░ 98%` | Optical solids, branched paths, scatter, detectors, media state, source identity, and path metadata are represented as traced scene data. |
| Sequential ordered-path special case | Achieved | `██████████ 100%` | Conventional lens prescriptions, paraxial/wavefront workflows, and zero-field launch semantics remain reproducible as ordered paths. |
| 3D scene with 2D projections | Achieved | `██████████ 100%` | YZ, XZ, and XY views are generated from traced 3D scene data; Open 3D uses the same world trace envelope, categorized view/scene/carry control rows with a toolbar layout validator, direct STEP import, snapped cube-grid STEP carry placement with Auto/Fine/Coarse grid mode, visible Drop state, and Sphinx coverage, in-scene STEP rotation handles, status-aware detector-miss terminal markers, active detector footprints, miss crosshairs, hover/click terminal diagnostics, and row-sized Object/Image reference display. |
| Separate sources, objects, detectors | Achieved | `██████████ 100%` | Scene sources, scene targets, and row-backed 3D placement records are first-class scene data; target role, detector metadata, active target selection, snap/grid intent, placement anchors, the Open 3D placement grid, snap-aware click/drag translate-rotate handles, row-to-target snap constraints, row-to-target normal-orientation constraints, named detector/object/active-target normal previews, row-to-ray vector-orientation constraints, source-vector constraints, Path-view frame constraints, local CAD-axis constraints, and explicit Scene Source Manager constraints are preserved from KrakenOS row metadata and scene graph export. |
| Event-law physics and diagnostics | Achieved | `██████████ 100%` | Canonical ray events own detector reach by default and feed inspectors, per-ray detector aperture status, detector aperture hit/miss reports, source illumination, detector maps, path PSF/MTF, coherent/diffraction analyses, Gaussian-q, throughput, trace-path reports, detector-miss local geometry, folded-preview provenance, and CSV export. |
| Arbitrary prisms and CAD solids | Near complete | `█████████░ 99%` | Face identity, closed-solid media transitions, Image-as-detector terminal policy, detector-miss plane projection, and prism/CAD diagnostics are covered by regression validators. |

Overall branch direction: keep moving toward one scene/event truth source while
preserving exact sequential prescriptions as the ordered-path special case.

## Installation

### Regular Python Users

Use a normal virtual environment first. Python 3.10 to 3.12 is the safest
starting range for broad binary-wheel availability.

```bash
git clone https://github.com/Garchupiter/Kraken-Optical-Simulator.git
cd Kraken-Optical-Simulator
git checkout nonseq-display-refactor

python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip "setuptools<82" wheel
python -m pip install -e .
python -m pip install numpy scipy matplotlib pandas pyvista PyVTK vtk csv342
python -m KrakenOS.UI.layout_editor
```

Notes:

- The desktop UI uses Tkinter. If `import tkinter` fails, install the Tk package
  for your operating system, then recreate or refresh the virtual environment.
- STEP/IGES CAD import benefits from `pythonocc-core`; many users will find it
  easiest through conda-forge. STL import and cached STL workflows do not require
  STEP/IGES support.
- Optional developer extras used by this branch include `trimesh`, `meshio`,
  `sphinx`, `sphinx-rtd-theme`, `ruff`, and `basedpyright`.
- Optional GPU tracing requires a compatible CUDA/CuPy installation. CPU tracing
  remains the default reliable path.

### Nix Or Devenv Users

The branch also includes a `devenv.nix` environment for contributors who prefer
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

## Feature Overview

### Layout Editor And Table Workflow

- Spreadsheet-style optical prescription table with undo/redo, copy/paste,
  grouped elements, right-click surface actions, advanced surface editing, and
  cell-local optimization variable markers.
- Text entries and editable table cells commit on focus loss, Tab, Enter, and
  normal selection changes.
- `Field Samples` is disabled and shown as `NA` when the active field span is
  zero; the requested count is restored when the field span becomes nonzero.
- Conventional sequential lens workflows keep `Field Samples` for field
  positions/angles and `Ray Count` for pupil or fan sampling.

### Scene And Display Pipeline

- The live 2D plot supports YZ, XZ, and XY projections of the traced 3D scene.
- The 2D projection selector sits with the plot controls so a design can remain
  editable while switching slice/projection views.
- The Open 3D inspector shows traced scene geometry, STL/CAD placement,
  source-target picking, face anchors, and STEP overlay inspection.
- Open 3D top controls are split into a `View` row and a compact `Scene` row
  with CAD/target, placement, and orientation category menus, so camera and
  placement tools remain reachable when the window is not wide enough for one
  long button row.
- Lens, camera, and LED STEP overlays can now be imported directly from the
  Open 3D `CAD / target -> Import STEP` submenu; the imported component is
  selected immediately and gets the same in-scene rotation handles.
- Open 3D imported STEP overlays can be carried on an automatically sized
  cube-grid overlay. Dragging in the canvas applies discrete grid-step
  translations to persistent 3D STEP placement metadata, so the component can
  be walked toward traced rays before orientation is adjusted with the colored
  handles. The 3D hardware-alignment Sphinx case study now includes a captured
  Open 3D screenshot of this carry workflow. A visible `Carry -> STEP grid`
  selector switches Auto/Fine/Coarse movement, and the `Drop` button exits
  carry mode without reopening a menu.
- Imported lens, camera, and LED STEP overlays now rotate through selected
  in-scene colored handles instead of a separate floating STEP rotation popup.
  The handles use the same pickable 3D interaction style as row placement
  rotation controls, write the existing STEP rotation state, and are covered by
  a non-GUI handle-generation/write-through validator.
- Ray display filters show all rays, detector hits, missed detector paths,
  absorbed paths, escaped paths, diagnostic stops, and beam-splitter branches.
- When an escaped non-sequential ray has a configured detector/Image plane, the
  scene event layer projects the terminal marker to that detector plane and
  marks it as a detector miss without setting detector-reach flags.
- Dense 2D plots keep non-hit terminal glyphs visible even when detector-hit
  endpoint markers are suppressed; missed detector/Image terminals use a
  distinct orange marker in 2D and Open 3D.
- Hovering or selecting a ray in the 2D plot, embedded 3D viewer, or legacy 3D
  viewer reports the canonical terminal status. Detector misses show the
  detector surface, projected plane distance, radial miss, active half-aperture,
  local detector-plane coordinates, active detector width/height, and original
  kernel terminal reason when available.
- Active detector/Image footprints are drawn from `SceneTarget3D` detector
  metadata in 2D, embedded 3D, and legacy 3D. Missed-detector terminal events
  add an orange crosshair at the projected detector-plane intercept, so the
  miss can be compared directly with the active aperture.
- Object/Image reference rows remain scene targets but no longer create default
  Open 3D placement grids or rotation handles, so the 3D reference size tracks
  the editable row diameter instead of placement-helper extent.

### Non-Sequential Physics And Metadata

- Scene/non-sequential tracing is selected for physical sources, beam splitters,
  probabilistic coatings, STL/CAD solids, mirror folds, tilted/decentered scenes,
  detectors, and path workflows.
- Ray events preserve reflection, transmission, absorption, split, scatter,
  diffraction, coating response, polarization, total internal reflection,
  detector termination, media transitions, and diagnostics.
- Launch metadata preserves requested versus effective field sampling, field
  basis/span, field-active state, ray count, pupil sampling label, trace intent,
  and sampling mode.
- Ray Inspector, Ray Events CSV, Trace Path Inspector, Branch Throughput,
  Detector Aperture Report, Branch Gaussian Q, Source Illumination, detector
  analyses, and path exports consume the active trace record set instead of
  relying on stale display state.
- Detector Aperture Report groups each detector/Image surface by ray/path count,
  detector hits, detector misses, stopped/other terminals, hit fraction, hit and
  miss power, worst miss margin, and dominant terminal reason. CSV export keeps
  the detector surface and worst-miss local X/Y/radial/active-aperture metadata.
- The normal results panel now shows detector aperture health after each trace,
  and the status bar adds a compact detector-miss warning when aperture clipping
  is present.
- Ray Inspector top rows now include per-ray detector aperture status and miss
  margin, and Ray Inspector CSV exports the same normalized aperture status
  fields beside the raw detector-miss event metadata.
- Ray-event and ray-analysis exports include detector-miss plane diagnostics:
  detector surface, projected miss distance, radial miss, active half-aperture,
  local detector-plane X/Y, active detector width/height, normal residual, and
  the original kernel terminal reason.
- Folded-preview detector reach is now an explicit policy. `Trace events`
  keeps KrakenOS terminal events authoritative and exports folded display
  status/residuals as diagnostics; `Display compatibility` preserves the legacy
  folded display detector rewrite for layouts that deliberately opt into it.

### Sources, Objects, And Detectors

- Scene Source Manager creates explicit physical illumination sources.
- Multiple sources can carry source id, role, model, wavelength, power, weight,
  ray count, position, aim direction, and target metadata.
- `SceneBundle.targets` records Object, Object Target, Aperture, Image/detector,
  and active analysis target rows as explicit scene targets without adding
  KrakenOS surface indices.
- `SceneBundle.placements` records movable target/CAD/STL placement anchors,
  row pose, grid visibility, linear snap spacing, and angular snap step as
  row-backed `ScenePlacement` metadata so 3D handles do not introduce a
  viewer-only transform.
- The Non-Sequential Scene Graph now includes a `Scene targets` namespace with
  target role, trace surface, detector metadata, center, normal, tangent, and
  active-target state.
- The Non-Sequential Scene Graph also includes a `3D placements` namespace for
  `ScenePlacement3D` records, and CSV export preserves those diagnostics beside
  sources, targets, volumes, and boundary faces.
- Open 3D renders a placement grid from the selected or first visible
  `ScenePlacement3D` record, including snap spacing, grid spacing, extent, and
  placement count as an in-view status overlay. Plain Object/Image reference
  targets do not become placement records; old placement metadata on those
  reference rows is ignored by the 3D handle layer.
- Open 3D placement handles can move the selected surface row along global
  X/Y/Z by the row's `ScenePlacement.snap_mm` when snap is enabled, or by the
  placement grid spacing when snap is off. The move writes `DespX/Y/Z` and
  `ScenePlacement` metadata through the same history/table path as other row
  pose edits.
- Open 3D placement rotation handles can rotate the selected surface row around
  global X/Y/Z by the row's `ScenePlacement.snap_deg` when snap is enabled, or
  by a coarse 15 degree step when snap is off. The rotation writes
  `TiltX/Y/Z` and `ScenePlacement` metadata through the same history/table path
  as other row pose edits.
- The same Open 3D placement handles also support drag-to-step authoring. Drag
  motion accumulates in screen space and repeatedly applies the same row-backed
  translation or rotation service once the motion crosses a snap-step
  threshold; clicking without dragging remains the precise one-step fallback.
- Open 3D `Snap Row->Target` lets the user select a movable surface/CAD row or
  face, then a target row or face. The solved translation writes `DespX/Y/Z`
  and records `target_surface` constraint metadata in the row's
  `ScenePlacement` state.
- Open 3D `Orient Row->Target` lets the user select a movable surface/CAD row
  or face, then a target row or face. The solved rotation writes `TiltX/Y/Z`
  and records `target_normal` constraint metadata in the same row-backed
  `ScenePlacement` state.
- Open 3D `Orient Row->Ray` lets the user select a movable surface/CAD row or
  face, then a traced ray. The solved rotation aligns the selected row or face
  normal to the clicked ray segment direction, writes `TiltX/Y/Z`, and records
  `target_ray` constraint metadata, ray index, branch path, source id, target
  point, target vector, and residual angle error in the same row-backed
  `ScenePlacement` state.
- Open 3D `Orient Row->Source` aligns the selected surface/CAD row or face
  normal to the Source panel aim vector. The solved rotation writes
  `TiltX/Y/Z` and records `source_vector` metadata, source origin, source
  direction, source model, target vector, and residual angle error in the same
  row-backed `ScenePlacement` state.
- Open 3D `Orient Row->Path` aligns the selected surface/CAD row or face normal
  to the selected Path-view frame near that row/face. The solved rotation
  writes `TiltX/Y/Z` and records `path_frame` metadata, branch path, sample
  count, origin surface, target point, target vector, and residual angle error
  in the same row-backed `ScenePlacement` state.
- Open 3D `Orient Row->CAD Axis` aligns the selected surface/CAD row or face
  normal to the selected local `+X/-X/+Y/-Y/+Z/-Z` axis after the row's current
  world transform is applied. The solved rotation writes `TiltX/Y/Z` and
  records `local_axis` metadata, the target axis row, axis label, axis vector,
  target vector, and residual angle error in the same row-backed
  `ScenePlacement` state.
- Open 3D `Orient Row->Scene Source` aligns the selected surface/CAD row or
  face normal to an explicit Scene Source Manager source. A selected source row
  in the editable table is used first; otherwise the first enabled physical
  scene source is used. The solved rotation writes `TiltX/Y/Z` and records
  `scene_source_vector` metadata, source id/name, origin, direction, source
  model, ray count, target vector, and residual angle error in the same
  row-backed `ScenePlacement` state.
- Open 3D named-normal placement uses the `Active target` / `Detector` /
  `Object` selector with `Preview Normal` and `Orient Row->Normal`. Preview
  reports the selected target row, role, normal vector, target point, and
  current angle error without mutating row pose. Apply writes `TiltX/Y/Z` and
  records `active_target_normal`, `detector_normal`, or `object_normal`
  metadata with the target row/id/name/role, target point, target normal, and
  residual angle error in the same row-backed `ScenePlacement` state.
- The scene graph `Edit Target` action writes row-backed `SceneTarget` metadata,
  detector active area, detector bins, pixel pitch, and active non-sequential
  `TargSurf` selection. Object Target, Diffuse Object, and Aperture choices use
  the existing surface-type defaults so tracing still sees normal KrakenOS
  prescription rows.
- Source-object aiming supports row targets and CAD/STL face anchors.
- Source Illumination reports hit power, vignetting, loss summaries, footprint
  coverage, centroid data, and per-source CSV rows.
- Detector workflows include detector maps, coherent detector fields,
  diffraction detector fields, path PSF, path MTF, and branch-field propagation.

### Beam Splitter And Path Workbench

- Beam splitter rows carry deterministic and probabilistic split metadata.
- Reflected/transmitted child states preserve branch power, phase, polarization,
  path labels, terminal state, and detector reach flags.
- Path-aware placement tools can add detectors, apertures, mirrors, thin lenses,
  refractive surfaces, and stock lenses along traced paths.
- Path-filtered reports cover detector maps, PSF, MTF, coherent detector,
  diffraction detector, source illumination, throughput, and Gaussian q.

### CAD, STL, And Prism Workflows

- Optical CAD/STL solids can be inserted, rendered, diagnosed, placed, and
  assigned boundary-face roles.
- STEP/IGES meshes can be converted and cached as STL for KrakenOS tracing when
  the optional CAD backend is available.
- Face anchors, snap-to-ray/path-frame placement, virtual internal planes, and
  hit-sequence validators support prism and beam-splitter case studies.
- Raw STL optical solids now keep a minimal closed-volume state even before
  face-role metadata is attached, so the ray event stream can distinguish
  entry, internal reflection/TIR, and exit instead of treating each STL hit as
  another entry.
- Optical-solid hits record mesh cell id, original cell id, face id, face-match
  method, face-match diagnostics, volume identity, material, ambient medium,
  inside-volume stack, and media transition.

Important rule:

A ray that hits a surface should transmit, reflect, absorb, split, scatter,
diffract, or terminate at a detector according to configured physics. It should
not stop silently halfway. Total internal reflection is a physics result of
incident medium, transmitted medium, and angle; it should not require the user to
label a surface as a special TIR surface.

### Sequential Lens Analysis

- Conventional prescriptions, paraxial solves, wavefront analysis, field maps,
  pupil maps, Zernike, Seidel, spot, PSF, MTF, lateral color, and classic lens
  diagnostics remain available.
- Sequential `Pupil / field` previews trace through a shared 3D section, then
  project that traced data into the selected 2D view.
- Finite-object mode derives launch geometry from object distance and entrance
  pupil rather than from the physical Source cone angle.

### Lens Fabrication Drawing Export

- Lens drawing surface properties can be edited from the UI.
- Lens fabrication drawing export produces PDF sheets for lens elements and
  assembly-level documentation.
- The export records drawing metadata, surface properties, diameters, thickness,
  material, radius, conic/asphere data where available, and manufacturing notes.
- A JSON sidecar preserves drawing settings for repeatable fabrication packages.
- Validators cover the drawing-property model and the PDF export case study.

### Optimization And Tolerancing

- Optimization variables, operands, merit functions, evaluators, and backend
  adapters are available.
- The UI supports merit operand setup, variable selection, bounds, worker count,
  SciPy/pygmo backend checks, saved solve presets, tolerance Monte Carlo,
  compensator sweeps, tolerance dashboards, and CSV export.
- SciPy remains the broadest default backend; pygmo is optional for global
  optimization workflows.

### Import, Examples, And Documentation

- Zemax prescription import, Zemax wavefront map import, AGF glass names, stock
  lens catalogs, common optical layouts, and saved layout snapshots are covered.
- Sphinx tutorials include sequential imaging, Gaussian beam expansion,
  interferometers, beam splitters, multi-source illumination, tolerance Monte
  Carlo, CAD/prism placement, lens drawing export, 3D hardware alignment, Cooke
  triplet optimization, Double Gauss analysis, and Galvo F-Theta scanning.
- SVG/PNG tutorial assets are generated from branch validators and capture
  scripts where practical.

## Validation

Regular Python environment:

```bash
python -m py_compile KrakenOS/UI/layout_editor.py
python -m KrakenOS.UI.validate_layout_plot_controller
python -m KrakenOS.UI.validate_branch_analysis
python -m KrakenOS.UI.validate_multi_scene_sources
python -m KrakenOS.UI.validate_mixed_source_object_template
python -m KrakenOS.UI.validate_ray_inspector_event_contract
python -m KrakenOS.UI.validate_detector_aperture_analysis
python -m KrakenOS.UI.validate_3d_interaction_contract
python -m KrakenOS.UI.validate_step_rotation_handles
python -m KrakenOS.UI.validate_open3d_toolbar_layout
python -m KrakenOS.UI.validate_optical_solid_hit_sequence
python -m KrakenOS.UI.validate_branch_gaussian_q_report
python -m KrakenOS.UI.validate_diffraction_detector
python -m KrakenOS.UI.validate_phase8_field_contract
python -m KrakenOS.UI.validate_galvo_f_theta_case_study
python -m KrakenOS.UI.validate_lens_drawing_properties
python -m KrakenOS.UI.validate_lens_drawing_pdf_case_study
```

Devenv users can run the same commands under `devenv shell`, for example:

```bash
devenv shell python -m KrakenOS.UI.validate_branch_analysis
```

Display-backed Open 3D smoke checks require a real X display or Xvfb:

```bash
python -m KrakenOS.UI.validate_step_carry_open3d_smoke
python -m KrakenOS.UI.validate_step_carry_open3d_smoke --snapshot /tmp/kraken_step_carry.png
```

## Known Risks

- Some older compatibility paths still exist for legacy sequential/table
  workflows. New work should prefer active scene and ray-event records.
- Source, object, and detector editing is not yet a fully separate scene graph;
  parts of the workflow still originate from prescription rows.
- Some display annotations are still compatibility labels. Folded-preview
  terminal provenance now states whether it is diagnostic or authoritative;
  remaining annotations should continue moving behind scene geometry, event
  records, or explicit diagnostics.
- CAD/prism additions must preserve face identity, media state, terminal policy,
  and event diagnostics instead of adding case-specific display rays.
- CSV exports must continue to preserve launch metadata, source identity,
  terminal policy, target/detector reach flags, media state, and event
  diagnostics.

## Future Improvements

- Complete the move from legacy compatibility state to canonical scene/event
  records at the remaining UI boundaries.
- Expand source/object/detector editing into a fuller scene graph while keeping
  exact ordered-surface prescriptions available for sequential lens design.
- Continue reducing display-only annotations by backing them with physical
  scene geometry or explicit diagnostics.
- Keep broadening prism, CAD solid, coating, detector, and cascading-component
  regression coverage.

### Feasibility Notes

White-beam prism dispersion is feasible as a native scene workflow, not as a
painted display effect. The right implementation is a spectral source bundle
that traces the same physical beam over multiple wavelengths, lets KrakenOS
material dispersion compute each wavelength's refraction through an equilateral
prism, and renders ray color from wavelength in both 2D and 3D. The required
work is a wavelength-sampled source model, per-wavelength ray metadata in the
active trace records, renderer color-by-wavelength support, and a prism case
study/validator that verifies wavelength-dependent detector positions.

Direct STEP optical-component placement in the 3D plot is also feasible. The
branch already imports STEP/IGES through cached STL, displays CAD/STL solids in
3D, stores face roles, supports path/face anchors, publishes row-backed
`ScenePlacement3D` records for snap/grid/anchor intent, draws the row-backed
placement grid inside Open 3D, and provides snap-aware translate handles for
selected rows plus snap-aware rotate handles for `TiltX/Y/Z`. Those handles can
now be clicked for one step or dragged for repeated snap-step edits while
immediately persisting back to row pose plus `ScenePlacement` metadata. Open 3D
also supports row-to-target snapping, where a movable row or face is translated
onto another row or face and the solved constraint is preserved as row-backed
metadata. It also supports row-to-target normal orientation, where a movable
row or face normal is aligned to a target row or face normal and the solved
tilt is preserved as row-backed metadata. It now includes row-to-ray
orientation, where a movable row or face normal is aligned to a clicked traced
ray segment, plus source-vector and Path-view-frame orientation, where the
same row or face normal is aligned to the Source panel aim vector or selected
Path view. Open 3D also supports local CAD-axis orientation through the
`+X/-X/+Y/-Y/+Z/-Z` selector and explicit Scene Source Manager orientation,
where a selected source row wins and the first enabled physical source is the
fallback. These vector constraints are preserved as row-backed metadata. The
named-normal selector now provides detector, object, and active-target normal
previews before applying the row pose, and the applied target is exported in
scene graph/CSV diagnostics. The important constraint remains that 3D
placement must update the same scene state used by 2D projection, tracing,
scene graph diagnostics, and CSV export.

## Historical Notes

Older branch planning files were consolidated into this README to reduce
root-level document sprawl. The upstream project `README.md` and the Sphinx
documentation tree remain separate on purpose.

## Next Pipeline Step

Broaden cascaded optical-solid regression coverage. The next slice should trace
two or more placed STL/CAD solids in series and verify that each component's
canonical ray-event sequence, closed-volume media state, face-role metadata, and
scene graph boundary records stay separated by row/component rather than leaking
state across the assembly.
