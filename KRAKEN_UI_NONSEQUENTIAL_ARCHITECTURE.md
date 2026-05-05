# Kraken UI Non-Sequential-First Architecture

This document records the post-Phase-5 direction for the layout editor.

## North Star

The UI should be non-sequential by design. A KrakenOS layout is a scene of
optical objects, sources, detectors, coatings, masks, STL solids, and path
metadata. Sequential ray tracing remains important, but it should be treated as
the axial ordered-surface special case of the same scene workflow.

The practical rule is:

- use scene/non-sequential tracing whenever the user creates a physical source,
  beam splitter, target surface, probabilistic non-sequential coating, STL
  object, mirror fold, tilt/decenter scene, or detector/path workflow;
- keep exact sequential tracing for conventional lens-design prescriptions and
  paraxial/wavefront analyses that explicitly depend on ordered surfaces;
- never hide KrakenOS-native state behind a UI-only abstraction without
  preserving it in row metadata, scene graph diagnostics, raykeeper metadata, or
  CSV export.

## Current Architecture

The UI already has the necessary foundations:

- one editable surface/object table backed by KrakenOS `surf` rows;
- physical Source panel independent of the Object row;
- `SceneBundle` as the shared 2D/3D display data model;
- Non-Sequential Scene Graph inspector/export;
- Trace Path Inspector/export from KrakenOS `raykeeper` branch/hit metadata;
- deterministic beam-splitter child paths with power, phase, and polarization
  metadata;
- path-aware table filtering, detector-map, path PSF/MTF, throughput, and
  first coherent detector binning;
- source metadata on traced rays.

## Phase 6A: Scene Trace Semantics

Status: complete at Phase 6 scope.

Implemented in this slice:

- the left control label is now `Scene trace`;
- `Auto` prefers KrakenOS `NsTraceLoop` for scene-style requests:
  physical source, beam splitter, STL optical solid, off-axis/tilted geometry,
  target surface, or probabilistic non-sequential coating;
- the status bar shows a `Scene: requested -> active` badge so `Auto` resolution
  is visible after selection changes and after Update;
- `Sequential` remains explicit and available, but is no longer the implied
  architecture for scene workflows.

Post-Phase-6 refinements:

- expose the same trace-state summary in exported scene graph headers;
- add regression snapshots for an off-axis physical-source scene that must
  resolve to `NsTraceLoop`.

## Phase 6B: Scene Object Model

Goal: make sources, detectors, beam splitters, mirrors, lenses, STL solids, and
path components feel like scene objects while preserving KrakenOS's ordered
`surf`/object list.

Current optical-solid slice:

- `File -> Import Optical STL Solid...` inserts a KrakenOS `surf` row with
  `advanced["Solid_3d_stl"]` preserved as the native core attribute;
- imported optical solids default to BK7, `Thickness=40 mm`, `AxisMove=2`, and
  a single-row element label so the user can immediately edit Material, Tilt,
  Decenter, Thickness, and AxisMove;
- `Auto` scene tracing detects `Solid_3d_stl` and resolves to KrakenOS
  `NsTraceLoop`, even when the STL row is otherwise axial;
- `Actions -> Inspect Optical STL Solids` reports triangle count, bounds,
  open/non-manifold edges, degenerate triangles, signed volume, and likely face
  winding for file-backed STL rows;
- `Actions -> 3D Place/Orient Selected STL Solid` opens the current 3D view in
  STL placement mode for the selected file-backed STL. Both the embedded VTK/Tk
  inspector and the legacy PyVista fallback expose STL placement controls, so
  the user watches the solid in 3D, rotates it, fits a local axis to layout
  `+Z`, centres X/Y, places the front face on the row plane, then closes the 3D
  view or presses `Done -> 2D`; the pose is stored in row `Tilt*`/`Desp*`
  fields and the 2D layout reuses those same row values;
- 2D layout rendering projects file-backed STL solid meshes to a visible
  footprint outline instead of only drawing the row plane;
- non-sequential STL hits use the STL row material for entry/exit state instead
  of trusting the neighbouring side reported by the hit chooser. This prevents
  tilted dispersion-prism poses from being traced as `n=1 -> 1` air;
- ordinary `NsTrace` now keeps a terminal escape segment after the last optical
  hit, so an STL ray that exits away from the axial Image is drawn in its
  outgoing direction instead of visually stopping on the prism boundary;
- the Non-Sequential Scene Graph includes a short mesh diagnostic summary for
  file-backed STL rows;
- the existing `Shape...` and Advanced Surface dialogs remain available for
  editing/staging raw `Solid_3d_stl` values.

Practical physics guardrails:

- the STL must be a closed/manifold optical boundary with sane face normals;
- mesh units are interpreted as millimetres in the KrakenOS scene;
- a ray can be physically valid and still miss the Image plane after leaving an
  arbitrary prism; inspect the terminal segment, Ray Inspector, or detector
  placement before assuming the ray was absorbed;
- the previous row `Thickness` sets the selected STL row station; visual
  placement writes `Tilt*` to rotate about the STL file origin, then `Desp*`
  translates it;
- material comes from the row `Glass` field, not from the STL file;
- a dispersion-prism pose should show material entry in the Ray Inspector
  (`n=1 -> n_glass`) before any visible bend can be trusted; validate this with
  `python -m KrakenOS.UI.validate_stl_prism_media`;
- very complex meshes may trace slowly or produce ambiguous intersections until
  Phase 6C adds path-local insertion and stronger placement diagnostics.

Recommended order:

1. Add a formal UI scene-object schema derived from rows and source settings.
2. Promote detector rows into a first-class detector element model.
3. Add source rows only if users need sources to be moved/reordered in the
   table; otherwise keep the Source panel as the scene source authority.
4. Add path-local component insertion using traced `BRANCH_PATH` frames.
5. Keep the table's row index as the KrakenOS surface/object index so imported
   examples and scripts remain debuggable.

## Phase 6C: Non-Sequential Path Workbench

Status: complete at splitter-origin component-placement scope.

Goal: users should add optics into a traced path without calculating global
decenter/tilt by hand.

Implemented:

- branch-local frame from the selected splitter world transform, splitter
  surface normal, and nominal global `+Z` incident source axis;
- right-click splitter insertion for detector plane, aperture stop, thin lens,
  refractive surface, and mirror components at a distance along transmitted or
  reflected paths;
- preservation of both global row pose and path-local metadata;
- compatibility detector shortcuts that call the same path-component helper;
- table filtering that shows common scene rows plus selected path objects;
- validation through `python -m KrakenOS.UI.validate_phase6_path_workbench`;
- API example `KrakenOS/Examples/Examp_Phase6_Path_Component_Placement.py`.

Post-Phase-6 extensions:

- compute placement frames from traced cumulative `BRANCH_PATH` records for
  tilted sources, nested splitters, and splitter-to-splitter paths;
- path-local placement of multi-row stock catalog elements as a rigid block;
- branch-local X/Y offset and local tilt editing in the placement dialog.

Seed example now available:

- `Galvo F-Theta Laser Scanner` demonstrates the user-facing target for this
  phase: source-defined laser rays, a beam expander, a 45 degree galvo fold,
  F-theta proxy lens, and scan plane. It uses folded ray layout metadata for
  the full scanner, while the splitter-origin path-component helper now covers
  common transmitted/reflected branch authoring without manual global pose math.

## Phase 6D: Coherent And Laser Branch State

Status: complete at geometric coherent-detector and Gaussian-input scope.

Goal: make interferometers and laser layouts physically honest.

Implemented:

- optical path length and phase through deterministic child paths;
- branch power and polarization vector/Jones metadata;
- detector-grid coherent field accumulation through the `CohDet` ray-bin
  analysis and CSV export;
- Gaussian waist or manufacturer diameter/divergence source input, q-envelope
  overlay for centered ABCD layouts, Gaussian Beam Report, and CSV export;
- validation against Michelson, Mach-Zehnder, and Twyman-Green reference
  layouts.

Post-Phase-6 extensions:

- fully oblique Gaussian `q` state with tangential/sagittal separation through
  tilted/folded non-sequential optics;
- diffraction/FFT propagation and physically sampled full-field interference
  beyond the current geometric ray-bin coherent detector.

## Guardrail

When exposing KrakenOS gems, prefer a first-class workflow over raw attribute
passthrough. If a raw attribute is exposed, document what it means, where it is
stored, and how a user can verify its effect through the scene graph, ray
inspector, plot, report, or CSV export.
