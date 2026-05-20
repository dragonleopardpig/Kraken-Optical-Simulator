# KrakenOS Non-Sequential UI Branch

Last updated: 2026-05-20

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
| Native non-sequential tracing | Achieved | `██████████ 100%` | Optical solids, branched paths, scatter, detectors, media state, source identity, source/object row separation, path metadata, branch-field propagation, and event accounting are covered by the native non-sequential closure validator. |
| Sequential ordered-path special case | Achieved | `██████████ 100%` | Conventional lens prescriptions, paraxial/wavefront workflows, and zero-field launch semantics remain reproducible as ordered paths. |
| 3D scene with 2D projections | Achieved | `██████████ 100%` | YZ, XZ, and XY views are generated from traced 3D scene data; Open 3D uses the same world trace envelope, categorized view/scene/carry control rows with a toolbar layout validator, direct optical/lens/camera/LED STEP import, a distinct arbitrary-optical STEP overlay slot that does not replace the lens overlay, immediate cursor-attached carry placement for new optical STEP imports, free STEP carry placement, press-hold or drag-to-lift STEP movement with an in-scene center grip, release-to-drop, no OS pointer warping, Esc cancellation with selection clearing, blank-click deselection, middle-drag CAD-style view pan, Ctrl-drag camera pause, default STEP-face hover outlines plus row-backed CAD/STL face hover previews, a persistent pickable dotted Optical Axis guide independent of ray visibility with a solid selected-axis overlay after normal snap, two-click STEP-face-normal-to-optical-axis snapping, face-specific row-to-optical-axis anchoring, promotion of positioned STEP overlays to file-backed optical solid rows, Open 3D right-click face-function assignment with physics-only interaction-surface semantics and persistent non-physical assigned-face outlines, structured Open3DTrace click/assignment/refresh diagnostics, double-sided scene surface actors plus transactional scene refresh that keeps prior valid surface meshes if a trace rebuild returns no or suspiciously incomplete surface meshes, ray-on surface opacity plus final wireframe retention for CAD/STL rows, display-bounded Open 3D ray actors that cannot expand the camera to escaped-ray coordinates, explicit CAD/STL placement side-panel entry instead of selection-triggered popups, and Sphinx coverage, hover-highlighted optional arrowheaded in-scene STEP rotation handles, status-aware detector-miss terminal markers, active detector footprints, miss crosshairs, hover/click terminal diagnostics, and row-sized Object/Image reference display. |
| Separate sources, objects, detectors | Achieved | `██████████ 100%` | Scene sources, scene targets, and row-backed 3D placement records are first-class scene data; target role, detector metadata, active target selection, snap/grid intent, placement anchors, Open 3D placement handles with visible grid planes suppressed, snap-aware click/drag translate-rotate handles, imported STEP snap-to-target placement, row-to-target snap constraints, row-to-target normal-orientation constraints, row-to-optical-axis centering with regular rays hidden during target pick, named detector/object/active-target normal previews, row-to-ray vector-orientation constraints, source-vector constraints, Path-view frame constraints, local CAD-axis constraints, and explicit Scene Source Manager constraints are preserved from KrakenOS row metadata and scene graph export. |
| Event-law physics and diagnostics | Achieved | `██████████ 100%` | Canonical ray events own detector reach by default and feed inspectors, per-ray detector aperture status, detector aperture hit/miss reports, source illumination, detector maps, path PSF/MTF, coherent/diffraction analyses, Gaussian-q, throughput, trace-path reports, detector-miss local geometry, folded-preview provenance, direct Open 3D mirror-face hits that stay inside closed optical solids until the next physical face, and CSV export. |
| Arbitrary prisms and CAD solids | Achieved | `██████████ 100%` | Face identity, geometry-derived uncoated face-intent suggestions, direct picked-face assignment without Left/Right/Up/Down side labels or inferred output ports, display-only STEP overlay promotion into traceable row-backed optical solids, cascaded row-scoped boundary/volume records, real multi-STL trace coverage, runtime output-port scene bounds, closed-solid media transitions, Image-as-detector terminal policy, detector-miss plane projection, and prism/CAD diagnostics are covered by regression validators. |

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
- Arbitrary optical STEP, lens, camera, and LED STEP overlays can now be
  imported directly from the Open 3D `CAD / target -> Import STEP` submenu. The
  generic optical STEP entry now uses a separate `optical` overlay slot, so it
  does not overwrite the existing lens STEP overlay in presets such as Machine
  Vision 150 mm. The imported optical component is selected immediately, enters
  cursor-carry placement until the next click drops it, and gets the same
  in-scene rotation handles. Hovering a handle highlights it before click, and
  clicking applies the rotation immediately around the selected STEP component
  center. If the pointer is not inside the 3D canvas when the
  file dialog closes, the first in-canvas pointer motion attaches the STEP
  center to the cursor plane so the component does not carry a large cursor
  offset. The generic optical STEP entry preserves all STEP components instead
  of reducing the import to the largest lens-like component.
- Open 3D imported STEP overlays are carried with free movement. Imported STEP
  carry now uses a press-hold or drag-to-lift gesture on an existing STEP body:
  hold briefly, or start
  dragging on the body, until the carry anchor snaps to the STEP center and an
  in-scene grip cursor appears on that center. Dragging moves the center grip
  and component together, and release drops/commits. The OS pointer is deliberately
  not warped during the hold-drag gesture; Tk/VTK can feed synthetic pointer
  motion back into the drag loop and make the component jump unpredictably. The
  carry path projects the current cursor ray onto a drag plane through the STEP
  center and moves continuously on that plane. Hold `Ctrl` while left-dragging
  to rotate the 3D view; middle-drag pans the whole view laterally in the
  current camera plane. Press `Esc` to cancel active carry/pick operations,
  clear the selected STEP component, and revert uncommitted free carry movement;
  clicking blank viewport space also clears the current 3D selection. To make
  placement optical instead of grid-driven, click a planar STEP face. The
  inspector then enters a second
  click mode where only the persistent dotted `Optical Axis` guide is accepted.
  Axis selection uses a screen-space nearest-line test against the same guide
  record that is drawn in the viewport, so it does not depend on VTK hitting a
  second actor and it still works when regular ray drawing is
  hidden. The picked face center moves onto the clicked guide point, and the
  picked face normal is rotated parallel to the layout optical axis. If the sign
  is not the intended one, use the colored rotation handles to flip the STEP
  before assigning Uncoated, Reflective, or other optical face functions. Plain
  CAD/STL row selection no longer opens the placement panel by itself; pose
  controls open from explicit placement commands, while right-click face
  assignment remains available on the selected row. Hovering row-backed CAD/STL
  faces previews the picked face before right-click assignment. Assigned optical
  faces are tinted in the 3D scene so previously authored Uncoated, Reflective,
  splitter, and absorber surfaces remain visible before the next pick without
  turning the whole solid into a triangulated mesh. The CAD/target promote menu
  turns the current placed overlay into a cached file-backed optical solid row
  with source STEP path, overlay rotation/offsets, row placement, and promotion
  provenance preserved in row metadata. A validator checks that the promoted
  optical-solid row lands at the same Open 3D world center as the original STEP
  overlay and remains present after all faces are assigned and the trace scene
  rebuilds.
- Imported lens, camera, and LED STEP overlays now rotate through selected
  in-scene colored handles instead of a separate floating STEP rotation popup.
  The handles use the same pickable 3D interaction style as row placement
  rotation controls, write the existing STEP rotation state, and are covered by
  a non-GUI handle-generation/write-through validator.
- Ray display filters show all rays, detector hits, missed detector paths,
  absorbed paths, escaped paths, diagnostic stops, and beam-splitter branches.
  Open 3D bounds-caps display-only escaped/missed ray segments to the current
  scene envelope before adding VTK actors, so one divergent path cannot expand
  the camera bounds until normal CAD/STEP components appear to disappear. The
  canonical ray path, event metadata, raykeeper data, and CSV export remain
  unchanged.
- When an escaped non-sequential ray has a configured detector/Image plane, the
  scene event layer projects the terminal marker to that detector plane and
  marks it as a detector miss without setting detector-reach flags.
- Direct Open 3D face-function assignment treats a `Full Reflecting` face as
  external only when the ray is outside the closed optical solid. Once the ray
  has entered the solid volume, reflected hits keep testing the same solid so a
  prism can naturally find its next mirror or exit face without requiring an
  explicit Input Port.
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
  Open 3D placement handles, so the 3D reference size tracks
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
- Open 3D uses the selected or first visible `ScenePlacement3D` record to drive
  placement handles and status text, but visible cube/grid planes are suppressed
  so face assignment and ray inspection are not obscured. Plain Object/Image
  reference targets do not become placement records; old placement metadata on
  those reference rows is ignored by the 3D handle layer.
- Open 3D placement handles can move the selected surface row along global
  X/Y/Z by the row's `ScenePlacement.snap_mm` when snap is enabled, or by the
  placement spacing when snap is off. The move writes `DespX/Y/Z` and
  `ScenePlacement` metadata through the same history/table path as other row
  pose edits.
- Open 3D placement rotation handles can rotate the selected surface row around
  global X/Y/Z by the row's `ScenePlacement.snap_deg` when snap is enabled, or
  by a coarse 15 degree step when snap is off. Rotation arcs have start/end
  arrowheads and can be hidden with the Open 3D `Rotation handles` checkbox.
  The rotation writes `TiltX/Y/Z` and `ScenePlacement` metadata through the same
  history/table path
  as other row pose edits.
- The same Open 3D placement handles also support drag authoring. Drag motion
  accumulates in screen space and repeatedly applies the same row-backed
  translation or rotation service; clicking without dragging remains the
  precise one-step fallback.
- Open 3D `Snap Row->Target` lets the user select a movable surface/CAD row or
  face, then a target row or face. The solved translation writes `DespX/Y/Z`
  and records `target_surface` constraint metadata in the row's
  `ScenePlacement` state.
- Open 3D `Orient Row->Target` lets the user select a movable surface/CAD row
  or face, then a target row or face. The solved rotation writes `TiltX/Y/Z`
  and records `target_normal` constraint metadata in the same row-backed
  `ScenePlacement` state.
- Open 3D `Center Row->Optical Axis` hides regular ray actors, lets the user
  select either a movable surface/CAD row or an imported STEP face with visible
  hover/selection highlighting. The optical-axis target is the persistent dotted
  `Optical Axis` guide itself, not an additional blue line; the guide is
  ignored by the first-click source picker so it cannot block surfaces/STEP
  faces, then only the guide is accepted as the second click. Imported STEP face
  picks transition to STEP normal-to-axis
  alignment, and cached/throttled STEP face picking avoids rescanning large STEP
  meshes on every mouse move. `Show rays` now controls traced rays only; the
  dotted optical-axis guide remains visible and pickable. Row centering writes
  `DespX/Y/Z` so the row center, or the best assigned CAD/STL optical-face
  anchor, lands on the selected optical-axis guide. If the first click lands on
  a specific row-backed CAD/STL face, that face becomes the centering anchor so
  the user can re-snap a different entrance, exit, or slanted surface without
  editing `Left`/`Right`/`Up`/`Down` labels.
- Open 3D right-click on a CAD/STL optical face opens a compact function menu:
  `Uncoated`, `Full Reflecting`, `Partial Reflecting / Transmitting`,
  `Absorbing / Mechanical`, or `Unassigned`. The menu writes the same
  `OpticalSolidFaces` metadata as the full face-role editor and immediately
  rebuilds the traced Open 3D scene; it does not wait for the older face-role
  dialog's `Save Roles` button. When the picked body is still a display-only
  imported STEP overlay, the command first promotes it into a row-backed
  `Solid_3d_stl` optical solid, clears the old display-only overlay, then stores
  the selected face function. This direct picked-face workflow does not require
  `Left`, `Right`, `Up`, `Down`, `+X`, or `-Y` labels for physics; those labels
  remain optional placement/roll aids. In this direct Open 3D workflow,
  `Uncoated` and `Full Reflecting` are stored as physical interaction surfaces
  rather than inferred output ports, so reassignment cycles do not create
  hidden output-port anchors or move the downstream `Image` row. Explicit
  input/output ports remain available in the full face-role editor for
  prescription-style port-chain placement.
- Open 3D writes structured `Open3DTrace` diagnostics to the Debug panel and
  `~/.cache/krakenos/logs/kraken_debug_latest.log`. The trace records left-click
  picks, right-click face context, matched face id/function, direct metadata
  writes, STEP promotion, `Show rays` toggles, scene-refresh mesh rows, actor
  counts, and row actors after refresh so a disappearing-component report can be
  reconstructed from the user's click sequence.
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
- The CAD/STL face-role editor shows geometry-derived optical intent
  suggestions. Suggestions prefer Uncoated boundary physics so Snell/Fresnel
  tracing decides transmission or total internal reflection; mirror,
  beam-splitter, absorber, and detector semantics remain explicit user-authored
  choices. Applying suggestions fills only empty fields and preserves existing
  authored face roles.
- Cascaded optical-solid validation now covers output-port chaining, row-scoped
  scene boundary records, independent optical-volume IDs/materials, duplicated
  face IDs across different solids, and preserved face-intent suggestion
  metadata across a multi-solid layout.
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
python -m KrakenOS.UI.validate_native_nonseq_closure
python -m KrakenOS.UI.validate_3d_interaction_contract
python -m KrakenOS.UI.validate_step_rotation_handles
python -m KrakenOS.UI.validate_step_promotion_optical_solid
python -m KrakenOS.UI.validate_open3d_face_context_assignment
python -m KrakenOS.UI.validate_step_carry_lightweight
python -m KrakenOS.UI.validate_open3d_toolbar_layout
python -m KrakenOS.UI.validate_optical_solid_face_roles
python -m KrakenOS.UI.validate_optical_solid_chained_ports
python -m KrakenOS.UI.validate_optical_solid_hit_sequence
python -m KrakenOS.UI.validate_optical_solid_direct_mirror_faces
python -m KrakenOS.UI.validate_optical_solid_multi_stl_trace
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
python -m KrakenOS.UI.validate_open3d_ray_toggle_scene_retention
python -m KrakenOS.UI.validate_step_carry_open3d_smoke --snapshot /tmp/kraken_step_carry.png
```

## Known Risks

- Some older compatibility paths still exist for legacy sequential/table
  workflows. New work should prefer active scene and ray-event records.
- Source, object, and detector editing now preserves separate scene/source/target
  identity, but some editor controls are still row-driven for compatibility with
  conventional prescriptions.
- Some display annotations are still compatibility labels. Folded-preview
  terminal provenance states whether it is diagnostic or authoritative; future
  annotations should continue moving behind scene geometry, event records, or
  explicit diagnostics.
- CAD/prism additions must preserve face identity, media state, terminal policy,
  runtime scene bounds, and event diagnostics instead of adding case-specific
  display rays.
- CSV exports must continue to preserve launch metadata, source identity,
  terminal policy, target/detector reach flags, media state, and event
  diagnostics.

## Future Improvements

- Simplify the remaining legacy compatibility state around canonical scene/event
  records at UI boundaries.
- Expand source/object/detector editing into a fuller direct scene graph while keeping
  exact ordered-surface prescriptions available for sequential lens design.
- Continue reducing display-only annotations by backing them with physical
  scene geometry or explicit diagnostics.
- Keep broadening prism, CAD solid, coating, detector, and cascading-component
  regression coverage with real traced fixtures.

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
`ScenePlacement3D` records for snap/grid/anchor intent, suppresses visible
placement grid planes inside Open 3D, and provides translate handles for
selected rows plus optional arrowheaded rotate handles for `TiltX/Y/Z`. Those
handles can now be clicked for one edit or dragged for repeated edits while
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
scene graph/CSV diagnostics. Chained optical-solid placement now refreshes
runtime boundary and optical-volume records after the output-port pose graph is
applied, so real multi-STL trace events, 2D/3D scene bounds, diagnostics, and
CSV/export consumers use the same placed geometry. The important constraint
remains that 3D placement must update the same scene state used by 2D
projection, tracing, scene graph diagnostics, and CSV export.

## Historical Notes

Older branch planning files were consolidated into this README to reduce
root-level document sprawl. The upstream project `README.md` and the Sphinx
documentation tree remain separate on purpose.

## Next Pipeline Step

Broaden the same real-trace contract from axial multi-STL solids into a folded
multi-prism path. The next slice should use file-backed prism/CAD solids with
non-normal input and at least one reflected or TIR segment, then verify that
runtime boundary records, optical-volume records, face identity, media state,
2D/3D projections, and detector/Image termination remain synchronized across
the folded assembly.
