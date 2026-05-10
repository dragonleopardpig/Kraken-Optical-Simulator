# Kraken UI Future Roadmap

This document tracks KrakenOS capabilities that exist in the core library or
examples, but are not yet exposed as first-class workflows in the layout editor.
Use `KRAKEN_UI_CORE_COVERAGE.md` as the lower-level audit matrix that maps
KrakenOS modules, surface attributes, and examples to current UI coverage.
The provisional manual cross-check lives in
`docs/source/ui/phase5_manual_crosscheck.rst`.

The goal is not just "feature count". The goal is to expose the parts of
KrakenOS that are genuinely distinctive:

- exact tilted/decentered 3D optics
- non-sequential and folded systems
- user-defined surfaces
- CAD/STL-backed optical solids
- pupil, aberration, and wavefront tools
- atmospheric refraction / dispersion
- coating / polarization / metal workflows
- beam splitters, folded laser paths, and future coherent branch analysis

Status legend:

- `Complete at scope`: complete for the named phase/UI foundation scope
- `Implemented`: user-facing in the UI today
- `Partial`: supported internally or preserved on load/save, but not a proper UI workflow
- `Missing`: core capability exists, but the UI does not expose it in a useful way

Important distinction: the table below tracks individual KrakenOS capability
areas, not phase completion. Phase 1 through Phase 5 are complete at their
intended UI-foundation scopes; long-tail items below are future convenience
expansions, not hidden blockers for exposing KrakenOS core features.
Phase 7 is tracked as parallel workstreams A-E, not a strict linear ladder.


## What Is Already Strong Today

These are already useful in the current branch:

- editable surface table with tilted/decentered/folded systems
- 2D layout view and legacy 3D viewer
- STEP import/export and CAD overlays
- spot / PSF / RMS / field curvature-distortion / illumination / lateral color
- pupil / Seidel / wavefront / MTF plots
- optimization panel and merit operands
- many example surface attributes now survive import, save/load, and runtime rebuild

The remaining roadmap work is mainly post-Phase-6 refinement: a serious
scene-object expansion of the prism/CAD placement workflow, higher-order
Gaussian/diffraction propagation, fully oblique astigmatic surface matrices,
larger assembly helpers, and richer tolerance stack-up/compensator workflows.
The concrete next-phase execution plan for these refinements lives in
`KRAKEN_UI_PHASE7_PLAN.md`.
Traced `BRANCH_PATH` placement now supports single-row components, rigid
stock-catalog blocks, and branch-local X/Y offset plus local X/Y/Z tilt at
insertion time, dialog edit time, and direct numbered-Path-view table editing.
Detector rows now carry first-class active-area/bin settings used by DetMap and
CohDet.
Scene Source Manager now provides explicit multi-source authoring while keeping
illumination-source scene rows separate from KrakenOS surface indices.
Source Illumination Report now groups traced target-surface hits by physical
source, including hit/vignetted rays, hit power, centroid, RMS radius, and span.
For explicit scene-source layouts, the `Illum` analysis now renders a traced
target-surface source-illumination power map with per-source centroids.
Phase 7E now provides a deterministic tolerance Monte Carlo report, worst-sample
comparison, stack-up dashboard, worst-sample compensator sweep,
multi-compensator coordinate solve, explicit tolerance-only vs compensator
eligibility metadata, coupled tolerance sampling groups, saved tolerance solve
presets, nominal-vs-worst spot/MTF/wavefront overlays, and CSV export.


## Phase Status Snapshot

| Phase | Status | Notes |
| --- | --- | --- |
| Phase 1 | Complete at editor-foundation scope | Ray inspector, explicit trace modes, non-sequential preview bridge, advanced surface editing, and safe custom-surface replay are in place. Non-sequential branch/source inspection continues in later completed phases. |
| Phase 2 | Complete at UI-foundation scope | Off-the-shelf catalog import, coating/material workflow, metal CSV loading, polarization analysis, measured error-map import, source/pupil sampling controls, source throughput, and Phase 2 reporting are in place. Later phases add path/source power preservation, tolerance Monte Carlo, stack-up dashboard, compensator sweep, and multi-compensator coordinate solve. |
| Phase 3 | Complete at UI-analysis scope | Wide-field maps, atmospheric refraction/dispersion, current-optics atmospheric image residuals, Zernike fitting, advanced wavefront plot styles, and wavefront/Zernike CSV exports are in place. Future work can refine ADC element authoring. |
| Phase 4 | Complete at architecture-cleanup scope | 2D, embedded 3D, and legacy 3D now share `SceneBundle` ray paths; 3D optical and solid body meshes are carried as `SceneBundle.surface_meshes`; and UI optimization marks bridge to KrakenOS native `surf.Var`. |
| Phase 5 | Complete at core-completeness pass scope | `KRAKEN_UI_CORE_COVERAGE.md` and the audit tool are in place; UI now exposes non-sequential controls, Non-Sequential Scene Graph inspector/export, SourceRnd weighting, chief/r-theta pupil controls, Ray Inspector CSV export, Trace Path Inspector/export, paraxial matrix reporting/export, KrakenOS glass browsing, enhanced Zemax import preservation, wavefront/Zernike CSV export, 2D/3D ray click-to-inspect, and broader native optimization variables. |
| Phase 6 | Complete at non-sequential-first architecture scope | The UI is now documented and implemented as a scene/object editor where sequential tracing is the axial ordered-surface special case. `Scene trace` auto-selects `NsTraceLoop` for scene workflows; optical CAD/STL solids have diagnostics and 3D placement, with STEP/IGES meshed to cached STL for KrakenOS `Solid_3d_stl`; beam splitters have deterministic branch state, path-aware table/plot filtering, detector/coherent analyses, splitter-origin path-component insertion, and traced-`BRANCH_PATH` insertion for detector, aperture, thin lens, refractive surface, and mirror rows. `python -m KrakenOS.UI.validate_phase6_complete` is the aggregate closure check. |
| Phase 7 | Active parallel workstreams; 7A-7D complete at current validation scope, 7E started | 7A covers CAD/STL face anchors, path-frame placement, virtual planes, and hit-sequence validation; 7B covers coherent detector-bin and diffraction detector validation; 7C covers branch-local Gaussian frames/q/clipping and detector recombination; 7D covers source-row actions and placement helpers; 7E covers deterministic tolerance Monte Carlo, worst-sample comparison, stack-up dashboard, compensator eligibility, coupled tolerance groups, compensator sweep, multi-compensator coordinate solve, saved solve presets, spot/MTF/WFE overlays, and CSV export. Remaining work is richer manufacturing metadata, optional visual tolerance dashboards, optional compact source-row editing, higher-order field propagation, and richer arbitrary prism/CAD assembly helpers. |


## Roadmap Summary

| Area | Core Capability | Current UI Status | Priority | Effort |
| --- | --- | --- | --- | --- |
| A | True general non-sequential tracing/editor | Complete at KrakenOS scene-list/diagnostics scope | Very High | High |
| B | Advanced surface editor | Complete at Shape Builder/preview scope | Very High | Medium |
| C | User-defined/custom surfaces | Complete for safe preset authoring | High | High |
| D | Surface error maps / measured surfaces | Complete at Phase 2 scope plus Phase 7E tolerance overlays/compensator sweep | High | Medium |
| E | Source and illumination models | Complete at Phase 7D source-row action and placement-helper scope | High | Medium |
| F | Coatings, metals, polarization | Complete at Phase 2 scope | High | Medium |
| G | Atmospheric refraction / dispersion | Complete at Phase 3 residual scope | Medium | Medium |
| H | Wide-angle PSF / field maps | Complete at Phase 3 map scope | Medium | Medium |
| I | Deeper wavefront / Zernike tooling | Complete at Phase 5 export scope | Medium | Medium |
| J | Native optimization-variable workflow | Complete at Phase 5 breadth scope | Medium | Low |
| K | Ray data / per-surface diagnostics | Complete at Phase 5 diagnostics scope | Medium | Low |
| L | 3D scene unification | Complete at 3D viewer scope | Medium | High |
| M | Beam splitters and deterministic branch forking | Deterministic branching and Phase 2 path workflow implemented | Very High | High |
| N | Non-sequential-first UI architecture | Complete at Phase 6 scope | Very High | High |
| O | Phase 7 non-sequential refinements | Active; 7A-7D complete at current scope, 7E first workflow plus coupled sampling implemented | High | High |


## A. True General Non-Sequential Tracing/Editor

Status: `Complete at KrakenOS scene-list/diagnostics scope`

KrakenOS core supports:

- `system.NsTrace()`
- `Kos.NsTraceLoop()`
- non-sequential examples with tilted optics, prisms, mirrors, and CAD/STL solids

Relevant examples:

- `KrakenOS/Examples/Examp_Doublet_Lens_NonSec.py`
- `KrakenOS/Examples/Examp_Doublet_Lens_Tilt_non_sec.py`
- `KrakenOS/Examples/Examp_Prism_STL.py`
- `KrakenOS/Examples/Examp_Solid_Object_STL.py`

Current UI coverage:

- explicit non-sequential preview mode reaches KrakenOS `NsTraceLoop()`
- Controls panel exposes non-sequential target surface, `NsLimit`, and
  probabilistic coating split (`energy_probability`)
- `Actions -> Non-Sequential Scene Graph` exposes the active source settings,
  trace settings, grouped element blocks, individual surface/STL/mask/coating
  rows, target selection, and CSV export
- preview ray paths carry per-hit diagnostics and branch-segment metadata from
  KrakenOS `raykeeper`, including interaction labels, parent branch links, hit
  ranges, and branch termination reasons
- Ray Inspector shows hit data and exports the per-ray/per-hit table as CSV
- Trace Path Inspector shows ray/path hierarchy and exports flattened branch
  CSV data
- `nonseq_ray_diagnostics_example.py` and
  `branch_tree_diagnostics_example.py` demonstrate the trace/branch workflow
- `nonseq_scene_graph_example.py` demonstrates scene graph inspection, grouped
  component nodes, source settings, target selection, and CSV export

Why this matters:

- this is one of KrakenOS's biggest differentiators
- it is the foundation for beam splitters, image slicers, prisms, and realistic folded systems

Recommended implementation:

1. Add specialized authoring wizards for large STL/image-slicer assemblies only
   if row-level element grouping and the Scene Graph inspector are not enough.
2. Keep expanding CAD/STL-backed non-sequential examples beyond the current
   diagnostics and scene-graph reference layouts.
3. Redesign arbitrary prism/CAD authoring as a visual scene-object workflow,
   not as raw table pose editing. The user should import the solid, see it in
   3D immediately, choose optical entry/exit faces or local axes visually, snap
   it to a traced ray/path, and only then write stable `TiltX/Y/Z` and
   `DespX/Y/Z` values back to the KrakenOS surface row.

Prism/CAD workflow redesign target:

- Treat the imported prism as a manipulable scene object with explicit local
  axes, face normals, bounds, material, and source CAD provenance.
- Let the user assign optical face roles: `Input`, `Output`, `TIR`, `Mirror`,
  `Beam Splitter`, and `Absorber/Mechanical`. Beam-splitter faces need split
  ratio/loss/phase metadata; future P/S/Jones behavior should reuse the existing
  splitter coating model.
- Do not rely on input/output face choice alone for pose. A 3D solid still needs
  an anchor point and roll constraint, such as a clicked input-ray hit point,
  desired output ray, target point, or local up axis.
- Provide pickable 3D handles for face selection, axis fit, face-on-row
  placement, centering on a traced ray, and ray/path-frame snapping.
- Support virtual internal optical planes for cube beam splitters and other
  vendor CAD where mechanical geometry does not encode the coated interface.
- Show entry/exit hit diagnostics directly on the selected solid, including
  incident medium, outgoing medium, surface normal, TIR/refraction/reflection
  decision, split branch, and stop reason.
- Keep the existing `Solid_3d_stl` row as the KrakenOS execution primitive, but
  hide most manual pose math behind the 3D scene-object placement workflow.
- Validate against canonical prism cases: BK7 wedge deviation, right-angle TIR,
  prism dispersion pose, missed-ray clipping, beam-splitter cube branching, and
  exported 2D/3D/STEP envelope consistency.

Implementation slices:

1. Face-role metadata authoring on file-backed STL/CAD rows. Done: assigned
   roles are preserved as `OpticalSolidFaces` advanced metadata.
2. 3D normal visualization for assigned roles. Done: the embedded 3D inspector
   and CAD/STL placement preview draw coloured face-centre/normal markers for
   saved `Input`, `Output`, `TIR`, `Mirror`, `Beam Splitter`, and absorber roles.
3. Pickable 3D face selection. Done: the face-role editor renders the actual
   row-posed mesh and lets users click planar face candidates directly before
   assigning roles.
4. Anchor visualization and snap selected input face to a traced ray/path.
5. Solve roll from output
   target or local-up constraint.
6. Hit-sequence validator that compares actual traced events with assigned
   face roles.


## A2. Beam Splitters And Future Folded Laser Paths

Status: `Implemented for deterministic ray paths, path-aware detector analysis,
ray-binned coherent detector analysis, detector FFT diagnostics, analytic
interferometer fallback diagnostics, and first branch-carried Gaussian q
propagation with centered aperture/obscuration clipping estimates, plus
detector-bin Gaussian-q recombination for Gaussian-source interferograms`

Detailed source-driven bundle, path-aware table, and path-analysis planning is
tracked in `BEAM_SPLITTER_PHASE2_PLAN.md`.

Current UI coverage:

- `Beam Splitter` is a table surface type.
- right-click `Beam splitter settings...` edits reflectance, absorption,
  transmitted/reflected phase metadata, minimum path power, and path depth.
- saved layouts preserve a `BeamSplitter` metadata dictionary.
- the runtime builder converts the settings into a KrakenOS coating table as a
  fallback while deterministic `NsTrace` mode spawns transmitted and reflected
  child paths.
- `Deterministic coating table` mode preserves a custom `Coating = [R, A, W,
  THETA]` table and derives deterministic reflected/transmitted path powers
  from the traced wavelength and incidence angle; fixed R/A settings remain the
  fallback.
- `Deterministic Fresnel P/S` mode derives deterministic splitter path powers
  from KrakenOS core `RP`, `RS`, `TP`, and `TS` Fresnel coefficients, weighted
  by a scalar `polarization_p_fraction` where `1` is pure P, `0` is pure S, and
  `0.5` is an equal P/S input. `polarization_s_phase_deg` stores the relative
  S-component Jones phase.
- `raykeeper` stores branch ID, parent ID, power, phase metadata, label, and
  source-ray identity for deterministic splitter children.
- physical-source splitter previews can launch exact-count collimated disk
  bundles or 2-D Gaussian bundles, and ray records carry source position,
  direction, model, power, weight, and wavelength metadata.
- `Beam Splitter 50/50 Example` demonstrates a finite BK7 plate workflow with a
  coated front face and rear AIR exit face.
- `Michelson Interferometer (Interferogram)` demonstrates an Edmund Optics
  68551-sized 25 mm cube-beam-splitter primitive, four physical path labels,
  path-filtered table workflows, deterministic return/recombination branch
  histories, and a path-average analytic fringe diagnostic. The vendor STEP/IGES
  body remains a mechanical CAD reference; the internal `Beam Splitter` row
  remains the optical prescription.
- `Twyman-Green Interferometer (Interferogram)` reuses the validated return-path
  recombination workflow with explicit test-optic/reference-flat semantics.
- `Mach-Zehnder Interferometer (Interferogram)` adds a physical two-splitter,
  two-fold-mirror sequence where both paths reach the second splitter, produce
  cross/return output paths, expose editable physical `Path 1` through
  `Path 5` table assignment, and feed the same path-average interferogram
  diagnostic used by the other current interferometer presets. Branch histories
  remain available separately in the Trace Path Inspector.
- Arbitrary beam-splitter layouts now get an automatic post-trace physical-path
  graph: source/splitter/terminal hits become vertices, ray segments between
  vertices become paths, shared physical paths are merged across branch
  histories, and manual `leg_id` assignments remain available as overrides.
- `Actions -> Path Throughput Report` provides the first path-aware
  downstream analysis slice by grouping traced leaf rays by output/path, selector
  code, trace path, and terminal detector/surface, then reporting weighted
  power and normalized throughput with path/output/terminal filtering plus
  copy/CSV export.
- The plot controls include an `Analysis path` selector for path-filtered
  Spot/RMS/PSF/MTF diagnostics. A non-`All paths` selection plots traced
  terminal detector-hit points for that output/code/terminal using
  detector-local coordinates when available, power-weighted RMS, geometric PSF,
  and geometric detector MTF.
- `Actions -> Export Path PSF CSV...` and `Actions -> Export Path MTF
  CSV...` export the same path-filtered PSF grid and geometric MTF curves
  used by the 2D analysis panel.
- `DetMap` adds the first detector-plane spatial binning pass: traced hits for
  one selected detector terminal are accumulated into a power-per-pixel map.
- `Actions -> Export Detector Map CSV...` exports the same path-filtered
  detector bins for downstream analysis and regression checks.
- `CohDet` adds the first ray-binned coherent detector sum: detector hits on
  one terminal plane accumulate complex field samples using traced optical path
  length, wavelength, path power, source weight, and deterministic
  `BRANCH_PHASE`.
- deterministic splitter branches now carry normalized `BRANCH_JONES_P`,
  `BRANCH_JONES_S`, and `BRANCH_POLARIZATION_XYZ` metadata; `CohDet` uses the
  global vector sum (`|sum(Ex)|^2 + |sum(Ey)|^2 + |sum(Ez)|^2`) so orthogonal
  branch states do not interfere.
- `Actions -> Export Coherent Detector CSV...` exports the same complex
  detector grid with field real/imaginary components, intensity, incoherent
  power, wavelength, reference optical path, path filter, and detector
  metadata.
- Plot Controls include `Detector bins` (`Auto` or 4-512) for reproducible
  `DetMap`/`CohDet` detector sampling and exports.
- `python -m KrakenOS.UI.validate_branch_analysis` provides a lightweight
  regression fixture for detector-bearing path layouts. It verifies terminal
  path detection plus DetMap, path PSF, path MTF, path PSF/MTF CSV row
  builders, and CohDet finite outputs, with optional JSON output for
  automation.
- `KrakenOS/Examples/Examp_Beam_Splitter_50_50.py` demonstrates fixed-ratio
  direct API use.
- `KrakenOS/Examples/Examp_Beam_Splitter_Coating_Table.py` demonstrates
  coating-table-derived deterministic path powers.
- `KrakenOS/Examples/Examp_Beam_Splitter_Fresnel_Polarization.py` demonstrates
  Fresnel P/S-weighted deterministic path powers for a finite BK7 splitter.
- `KrakenOS/Examples/Examp_Michelson_Interferometer.py`,
  `KrakenOS/Examples/Examp_Twyman_Green_Interferometer.py`, and
  `KrakenOS/Examples/Examp_Mach_Zehnder_Interferometer.py` document direct API
  usage for the current interferometer path diagnostics.
- `docs/source/manual/beam_splitters.rst` documents current behavior, saved
  metadata, internal branch data, finite plate setup, simple splitter retardance, and
  future Gaussian work.

What remains:

1. Add coating-stack vector behavior and detailed polarization retardance.
   The current P/S mode converts splitter-local Jones amplitudes to a global
   branch vector and keeps it transverse along traced directions. Simple
   per-output S-vs-P retardance is implemented through
   `transmit_s_phase_deg` and `reflect_s_phase_deg`; it does not solve
   multilayer coatings or birefringence.
2. Retire or demote the analytic Michelson/Twyman-Green/Mach-Zehnder fringe
   diagnostic once CohDet has validated branch position, phase, optical path
   length, polarization, binning/interpolation, and export behavior.

Tilted/folded Gaussian optics now have the first branch-level contract:
Ray Inspector hit records expose local T/S/K frames and
`KrakenOS.propagate_branch_gaussian_q()` carries separate tangential/sagittal q
state along deterministic branch records. Each q step also carries centered
Gaussian aperture/obscuration transmission and cumulative branch loss from row
`Diameter`/`InDiameter`. Detector-bin coherent accumulation can apply those
branch-q envelope and clipping weights, and `Interf` auto-enables that path for
Gaussian beam sources when detector-bin promotion is reliable. Remaining work is
higher-order FFT/mode-overlap validation and full oblique astigmatic surface
matrices. Gaussian Beam Report remains documented as a centered paraxial
laser-design tool.


## B. Advanced Surface Editor

Status: `Complete at Shape Builder/preview scope`

Common KrakenOS surface attributes are now editable through the Advanced Surface
dialog. The dialog validates high-risk literal inputs such as coatings and error
maps before applying. The `Shape...` builder provides previewable workflows for
asphere and Zernike arrays, UDA polygons, Ronchi/spider masks, safe custom
`ExtraData` presets, and optical CAD/STL path staging. The main prescription table
is intentionally compact: uncommon scalar row-shape controls such as conic `k`
and `Axicon` are edited in `Advanced... -> Shape Params`, while imported
layouts, KrakenOS system construction, export, and conic optimization still
preserve those fields.

Core surface attrs worth exposing:

- `AspherData`
- `ZNK`
- `k`
- `Axicon`
- `ShiftX`, `ShiftY`
- `Cylinder_Rxy_Ratio`
- `SubAperture`
- `Mask_Type`, `Mask_Shape`
- `Error_map`
- `Color`
- `Note`
- `Nm_Pos`
- `Order`
- `Coating`, `CoatingMet`
- `DerPres`
- `NumLabel`

Relevant files:

- `KrakenOS/SurfClass.py`
- `KrakenOS/MathShapesClass.py`

Deferred refinements:

1. Add specialized faceted/Fresnel/profile builders only if users need more
   than safe presets.
2. Add plot-linked coefficient selection if array editing becomes too dense.
3. Keep the main table simple; continue moving complex or surface-specific
   settings into dialogs.


## C. User-Defined / Custom Surface Functions

Status: `Complete for safe preset authoring`

Core capability:

- `ExtraData`
- `UDA`
- `SPECIAL_SURF_FUNC`

Relevant examples:

- `KrakenOS/Examples/Examp_ExtraShape_XY_Cosines.py`
- `KrakenOS/Examples/Examp_ExtraShape_XY_Cosines_UDA.py`
- `KrakenOS/Examples/Examp_ExtraShape_UserFacets.py`
- `KrakenOS/Examples/Examp_ExtraShape_Radial_Sine.py`

Current UI coverage:

- literal/list-based `ExtraData` and `UDA` cases can be edited in the Advanced
  Surface dialog
- safe preset dictionaries are supported for replayable `ExtraData` and UDA
  authoring, with `custom_surface_preset_example.py` as a working UI example
- `Shape...` previews and edits safe `ExtraData` presets, UDA polygons, and
  Ronchi/spider masks before rebuilding the optical system
- callable/object custom surfaces imported from examples are preserved in memory,
  but unrestricted arbitrary Python object authoring is intentionally not exposed
  as a generic table workflow

Why this matters:

- this is another KrakenOS-specific strength
- it enables micro-lens arrays, custom phase plates, special sag functions, and faceted surfaces

Deferred refinements:

1. Add specialized faceted/Fresnel/profile builders if those examples become
   common UI authoring tasks.
2. Keep arbitrary Python callables import-only/preserved unless a sandboxed
   plugin workflow is designed.


## D. Surface Error Maps / Measured Surfaces

Status: `Complete at Phase 2 measured-map scope plus Phase 7E tolerance-overlay/compensator scope`

Core capability:

- `Error_map = [X, Y, Z, SPACE]`

Current UI coverage:

- per-surface `Error Map...` import/clear/validate workflow exists for text,
  `.npy`, and `.npz` measured maps
- the Information panel and `Actions -> Copy Phase 2 Report` summarize
  measured-map surfaces with PV/RMS
- Phase 7E adds a deterministic tolerance Monte Carlo report using marked
  optimization/native variables as sampled tolerances
- Phase 7E adds worst-sample comparison, stack-up dashboard, worst-sample
  compensator sweep, multi-compensator coordinate solve, compensator
  eligibility metadata, coupled tolerance sampling groups, saved solve presets,
  and nominal-vs-worst spot, MTF, and piston/tilt-removed wavefront-delta
  overlays with CSV export

Why this matters:

- this is how KrakenOS becomes useful for metrology-driven troubleshooting

Recommended implementation:

1. Add richer visual tolerance dashboards once the current report/CSV solve
   contract has enough user feedback.
2. Add richer manufacturing metadata and covariance-aware summaries for
   tolerance groups and compensator eligibility presets.


## E. Source and Illumination Models

Status: `Complete at Phase 7D source-row action and placement-helper scope`

Core capability:

- `KrakenOS/SourceRand.py`
- rich pupil pattern generation in `KrakenOS/PupilTool.py`

Current UI coverage:

- a Source panel exposes `PupilCalc` pattern choices: meridional fan, cross fan,
  fan-x, fan-y, hexapolar, square, random disk, `chief`, and `rtheta`
- `R-theta` uses editable normalized pupil radius and azimuth fields
- random circle/square extended-source bundles are available through
  `KrakenOS.SourceRnd`; line and point-cone Monte Carlo source bundles are
  available through deterministic UI-side sampling
- `SourceRnd.fun` is exposed through angular weighting presets: uniform solid
  angle, cosine-weighted, Gaussian center, and edge-weighted
- random-source power, per-ray weight statistics, illumination throughput, and
  X/Y/Z launch-plane offsets are available
- saved layouts can declare multiple physical ``SceneSource3D`` records through
  ``SETTINGS["scene_sources"]``; each source traces independently, renders as a
  source marker, appears in the Non-Sequential Scene Graph, and stamps its own
  ``SOURCE_ID``/``SOURCE_NAME`` onto raykeeper records
- source-row architecture is now documented and guarded by
  ``python -m KrakenOS.UI.validate_scene_source_row_contract``: physical
  illumination sources are visible scene rows in the main table, but they stay
  out of KrakenOS ``surf`` rows and use the source-aware row mapping layer
- the source-aware ``SceneRowMapping`` bridge is implemented and carried by
  ``SceneBundle``; it maps visible scene rows to current table rows
  and KrakenOS trace surfaces, with
  ``python -m KrakenOS.UI.validate_scene_row_mapping`` covering reset and
  multi-source scenes
- source/Object visible-row order is not fixed: layouts may use
  ``scene_row_order="before_object"`` for source-first illumination workflows
  while preserving KrakenOS trace surface indices
- the main editable table renders physical sources as read-only
  ``Illumination Source`` rows; these rows show source model/ray count, keep
  separate scene-row IDs, and are skipped when surface rows are read back for
  tracing
- source rows provide direct right-click duplicate, delete, move up, and move
  down actions without entering the KrakenOS ``surf`` list
- ``Actions -> Non-Sequential Scene Graph`` exposes the scene-row mapping
  directly with scene row, current table row, trace surface, and source ID
  columns
- ``Actions -> Source Illumination Report`` audits selected target hits by
  physical source, and the ``Illum`` analysis plots a traced target-surface
  power-density map with per-source centroids for explicit scene-source layouts
- `rtheta_pupil_diagnostic_example.py` and `weighted_sourcernd_example.py`
  demonstrate single-source controls; ``Multi-Source Illumination Example`` and
  ``KrakenOS/Examples/Examp_Multi_Source_Illumination.py`` demonstrate the
  layout-defined multi-source contract
- detector/path PSF, MTF, detector-map, coherent-detector, throughput, and
  source-illumination diagnostics preserve source/path power weights; remaining
  PSF/MTF refinement is full scalar diffraction and mode-overlap propagation

Why this matters:

- many real systems are source-limited rather than field-fan limited
- especially relevant for illumination optics and non-sequential scenes

Recommended implementation:

1. Add a compact inline source-row edit dialog only if the Scene Source Manager
   is too heavy for common source edits.
2. Add arbitrary picked-point source targets beyond row centers and assigned
   CAD/STL face anchors.
3. Continue scalar diffraction/mode-overlap work through the Phase 7B/7C
   detector and Gaussian field-propagation paths.


## F. Coatings, Metals, and Polarization

Status: `Complete at Phase 2 scope`

Core capability:

- `Coating`
- `CoatingMet`
- metal loading via `Setup.LoadMetal(...)`
- Fresnel terms and polarization outputs:
  - `RP`, `RS`, `TP`, `TS`, `TT`, `TTBE`

Relevant examples:

- `KrakenOS/Examples/Examp_Sphere.py`
- `KrakenOS/Examples/Examp_Prism_STL-AR_coating.py`

Current UI state:

- coating attrs are editable through the Advanced Surface dialog
- a dedicated `Coating...` dialog supports clear, broadband AR, and protected
  mirror presets and validates KrakenOS coating-table shape/ranges
- coating tables are sampled by wavelength/incidence-angle interpolation instead
  of nearest-neighbor lookup
- layout-level `metal_catalogs` settings can load metal CSV files for
  `CoatingMet` mirror Fresnel handling; the coating dialog can add CSVs and
  assign the corresponding index
- `Actions -> Copy Phase 2 Report` summarizes coating surfaces and loaded metal
  catalogs
- multilayer coating-stack solving remains outside the UI-foundation scope
- the Polarization analysis view exposes per-surface `TP`, `TS`, `RP`, `RS`,
  `TTBE`, and total throughput summaries from KrakenOS raykeeper data

Recommended implementation:

1. Add multilayer coating-stack solving only if KrakenOS core exposes a stack
   model that should be authored from the UI.
2. Add larger catalog browsing if more coating/metal datasets are added.


## G. Atmospheric Refraction and Dispersion

Status: `Complete at Phase 3 residual scope`

Core capability:

- `KrakenOS/AstroAtmosphere/*`
- examples use `Pup.AtmosRef = 1`

Relevant examples:

- `KrakenOS/Examples/Examp_Tel_2M_Atmospheric_Refraction_Corrector_Static.py`
- `KrakenOS/Examples/Examp_Tel_2M_Atmospheric_Refraction_Corrector_Adaptable.py`

Current UI coverage:

- Atmosphere panel captures wavelength range, zenith angle, pressure,
  temperature, humidity, CO2, latitude, and altitude
- Observatory presets from `KrakenOS/AstroAtmosphere/observatories.py` fill
  the weather/site fields
- `Atmos` analysis plots absolute refraction and chromatic dispersion using
  `KrakenOS/AstroAtmosphere`
- `Atmos plot -> Image residual (current optics)` traces atmospheric field
  bundles through the current prescription and plots image-plane centroid
  residuals, so prism/ADC surfaces already present in the table are included
- `atmospheric_dispersion_example.py` demonstrates the analysis workflow
- `atmospheric_image_residual_example.py` demonstrates current-optics residuals

Remaining UI gap:

- dedicated ADC element authoring is not implemented as a special wizard; use
  grouped tilted/prism surfaces in the editable table

Why this matters:

- unique value for telescope and long-path optics

Recommended implementation:

1. Add an ADC element wizard only if table-level grouped prism editing is not
   sufficient for practical designs.


## H. Wide-Angle PSF / Field Maps

Status: `Complete at Phase 3 map scope`

Core capability:

- `KrakenOS/PSFMap.py`

Current UI gap:

- `FieldMap` analysis plots a wide-field geometric spot RMS heatmap from the
  current X/Y field grid
- `PSFMap` analysis plots a tiled wide-field geometric PSF image map from the
  same field grid
- `IllumMap` analysis plots a wide-field relative illumination heatmap from the
  same field grid
- `WfeMap` analysis plots a wide-field wavefront RMS heatmap from the same
  field grid
- `wide_field_spot_map_example.py` demonstrates the workflow on the Zemax
  Double Gauss 28 degree field lens
- `wide_field_psf_map_example.py` demonstrates wide-field PSF image mapping
- `wide_field_illumination_map_example.py` demonstrates relative illumination
  mapping
- `wide_field_wavefront_map_example.py` demonstrates wide-field wavefront RMS
  mapping

Why this matters:

- useful for image-quality maps and lens qualification across the full sensor

Recommended implementation:

1. Add direct map-data export if a dedicated analysis-data products workflow is
   needed beyond saved plot images.


## I. Deeper Wavefront / Zernike Tooling

Status: `Complete at Phase 5 export scope`

Core capability:

- `KrakenOS/WavefrontFit.py`
- `KrakenOS/WavePlot.py`

Current UI coverage:

- `Wavefront` defaults to a Zemax-style Wavefront Function 3D wireframe OPD
  surface
- `Wavefront style` also supports unwrapped phase, wrapped phase,
  interferogram, X/Y slope maps, and slope magnitude
- `F-Theta Lens 50mm Wavefront 0 Deg` provides a pure sequential on-axis
  validation target for the Figure 8 F-theta lens screenshots. The matching
  Zemax `AT 20.00 DEG` edge-field screenshot remains a KrakenOS `Phase()`
  core limitation: the phase routine currently fails before returning OPD
  samples for that nonzero-field F-theta prescription, so the UI does not
  publish a broken 20 degree Wavefront Function preset.
- `File -> Import Zemax Wavefront Map...` loads a Zemax Wavefront Map text
  export as a numerical reference for `WFront`/`Phase (unwrapped)` comparison;
  the UI samples the reference on the KrakenOS normalized pupil, removes the
  same piston/tilt plane, auto-selects the best export orientation, and reports
  residual RMS/P-V in waves and nm.
- `Zernike` analysis fits KrakenOS Zernike coefficients, plots the fitted
  coefficients, reports P-V/RMS and residual metrics, and writes coefficient
  rows into the `Information` panel
- `Actions -> Copy Wavefront Fit Report` copies the latest coefficient/metric
  report as text
- `Actions -> Export Wavefront CSV` exports the latest wavefront sample table,
  including Zemax reference/residual columns when a reference map is loaded
- `Actions -> Export Zernike CSV` exports the latest fitted coefficients and
  residual sample table
- `wavefront_function_example.py`, `wavefront_wrapped_phase_example.py`,
  `wavefront_interferogram_example.py`, and
  `wavefront_slope_map_example.py` demonstrate plot-style workflows
- `wavefront_zernike_fit_example.py` demonstrates the fitting workflow
- `KrakenOS/Examples/Examp_Zemax_Wavefront_Map_Import.py` demonstrates
  standalone Zemax Wavefront Map loading and normalized-pupil sampling
- `python -m KrakenOS.UI.validate_zemax_wavefront_import` validates the parser,
  wavelength-unit handling, sampling, orientation selection, and residual
  comparison path

Deferred refinement:

- Add richer plot-linked coefficient selection if needed later.

Recommended implementation:

1. Keep export schemas stable enough for external analysis scripts.


## J. Native Optimization-Variable Workflow

Status: `Complete at Phase 5 breadth scope`

Core capability:

- surface-local `Var = [...]`
- optimization examples that drive surface attrs directly

Relevant example:

- `KrakenOS/Examples/Examp_Tel_2M_Optimization_Variables.py`

Current UI coverage:

- the UI variable/operand framework is still the primary optimization workflow
- marked UI variables are mirrored into KrakenOS native `surf.Var` during
  system rebuild
- imported/native `Var` entries are preserved through the Advanced Surface
  dialog and are honored by the UI optimizer for supported variables such as
  `Rc`, `Thickness`, `k`, tilts, decenters, axis move, and grating pitch/angle
- visible table variables use a cell-local `V` marker instead of a star suffix
  or whole-row color, keeping element/path row colors readable
- `VarBounds` stores UI bounds for native `Var` entries that do not have
  dedicated legacy boolean fields
- `native_variable_breadth_example.py` demonstrates conic and tilt variables

Deferred refinements:

1. Add an "Optimization Variables" dialog per surface
2. Show both:
   - UI variable registry
   - native Kraken `Var` attrs
3. Add constraints/coupled variables if a future optimizer workflow needs them


## K. Ray Data / Per-Surface Diagnostics

Status: `Complete at Phase 5 diagnostics scope`

Core capability:

- `SURFACE`, `NAME`, `GLASS`
- `XYZ`, `OST_XYZ`
- `LMN`, `R_LMN`, `S_LMN`
- `N0`, `N1`
- `OP`, `TOP`, `TOP_S`
- `RP`, `RS`, `TP`, `TS`, `TT`

Current UI coverage:

- the Ray Inspector exposes structured preview-ray diagnostics
- the scene bundle carries per-hit surface, direction, optical path, Fresnel,
  and interaction data for each preview ray
- the scene bundle also carries branch-segment metadata for reflected and
  non-monotonic paths
- Ray Inspector exports flattened per-ray/per-hit CSV data
- Trace Path Inspector exports flattened ray/path/hit CSV data
- `Actions -> Paraxial Matrix Report` exposes `ParaxMatrices()` surface matrices
  and exports them as CSV
- `Actions -> Export Wavefront CSV` and `Export Zernike CSV` export numerical
  wavefront samples and fitted coefficients
- clicking a ray in the 2D plot opens/selects it in Ray Inspector
- clicking a ray in the embedded or legacy 3D viewer opens/selects it in Ray
  Inspector

Recommended implementation:

1. Keep Ray Inspector export schemas stable enough for external diagnostics.


## L. 3D Scene Unification

Status: `Complete at 3D viewer scope`

Current state:

- 2D layout, embedded 3D, and legacy 3D consume shared `SceneBundle.ray_paths`
- 3D optical surface meshes and solid side-body meshes are carried as typed
  `SceneBundle.surface_meshes`
- embedded and legacy 3D consume those shared mesh records instead of building
  parallel surface/body display lists

Related document:

- `NONSEQUENTIAL_DISPLAY_REFACTOR_PLAN.org`

Deferred refinements:

1. Move STEP export onto scene-bundle mesh records after export validation.
2. Keep reducing legacy-only display helpers when they become strict wrappers.


## Suggested Execution Order

### Phase 1: Most Valuable Kraken Differentiators

Status: foundation complete for the planned UI scope. Later phases added the
general non-sequential trace controls, scene-list inspector, branch inspector,
and diagnostics that were outside the original Phase 1 foundation.

1. True non-sequential UI mode
2. Advanced surface editor
3. User-defined/custom surfaces
4. Ray inspector

### Phase 2: Real-World Optics / Fabrication

Status: complete at UI-foundation scope.

1. Error-map workflow: import/edit/clear/validate plus Phase 2 PV/RMS reporting.
2. Coating / metal / polarization workflow: coating editor, metal CSV loading,
   polarization analysis, and Phase 2 report summaries.
3. Off-the-shelf optics catalog import: Edmund/Thorlabs-style stock lens import
   into editable table rows.
4. Source and illumination models: pupil patterns, random circle/square/line
   and point-cone sources, source power/statistics, throughput reporting, and
   launch-plane offsets.

### Phase 3: High-End Imaging and Telescope Workflow

Status: complete at UI-analysis scope. Continue with Phase 4 cleanup or
deferred refinements only if a design need appears.

1. Wide-angle PSF / field maps
2. Atmospheric refraction / dispersion
3. Deeper wavefront/Zernike tooling

### Phase 4: Architecture Cleanup

Status: complete at architecture-cleanup scope. Embedded and legacy 3D ray
display use the same `SceneBundle.ray_paths` as the 2D display path; both 3D
viewers consume typed `SceneBundle.surface_meshes` for optical surfaces and
solid side bodies; and UI optimization marks bridge into native KrakenOS
`surf.Var` records.

1. 3D scene unification: complete for embedded/legacy viewers
2. Native optimization-variable bridge: complete for UI-supported variables
3. Redundant 3D surface/body display code: removed from embedded and legacy
   render paths

### Phase 5: KrakenOS Core Completeness Pass

Status: complete at the audit/core-controls scope. This pass did not rewrite
Phases 1-4; it made the remaining high-value KrakenOS-native features visible
enough to be used, audited, and extended without relying on hidden code paths.

1. Coverage guardrails: `KRAKEN_UI_CORE_COVERAGE.md` and
   `tools/audit_ui_core_coverage.py` track core attrs and example attrs.
2. Non-sequential controls: `energy_probability`, `NsLimit`, target surfaces,
   Scene Graph inspector/export, branch paths, hit diagnostics, and Ray
   Inspector CSV export are exposed.
3. Source/pupil controls: `SourceRnd.fun` presets, `chief`, and `rtheta`
   sampling are exposed with reference common-layout examples.
4. Data products: Ray Inspector CSV, `ParaxMatrices()` table/CSV export,
   wavefront/Zernike CSV, and 2D ray click-to-inspect are implemented.
5. Catalog/import workflow: KrakenOS glass catalogs are searchable and can
   apply glass names to selected table rows; Zemax text imports preserve
   conics, asphere coefficients, coatings, embedded fallback glasses, and notes
   for unsupported tokens.
6. Native optimizer variables now cover conic, transform, and grating
   pitch/angle breadth.


## Short Version: Do Not Miss These

If only a few items are pursued, the biggest KrakenOS-specific wins are:

1. general non-sequential editing and tracing
2. custom surfaces (`UDA`, `ExtraData`, mask presets, faceted/user functions)
3. measured surface error maps
4. coating / metal / polarization analysis
5. atmospheric refraction / dispersion
6. wide-angle PSF / field maps
7. ray data products and paraxial matrix diagnostics


## Notes

- Some future convenience expansions may still preserve extra imported data
  before a specialized editor exists.
- This roadmap is about first-class usability, not just attribute passthrough.
