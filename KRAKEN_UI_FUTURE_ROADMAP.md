# Kraken UI Future Roadmap

This document tracks KrakenOS capabilities that exist in the core library or
examples, but are not yet exposed as first-class workflows in the layout editor.

The goal is not just "feature count". The goal is to expose the parts of
KrakenOS that are genuinely distinctive:

- exact tilted/decentered 3D optics
- non-sequential and folded systems
- user-defined surfaces
- STL-backed optical solids
- pupil, aberration, and wavefront tools
- atmospheric refraction / dispersion
- coating / polarization / metal workflows

Status legend:

- `Complete at scope`: complete for the named phase/UI foundation scope
- `Implemented`: user-facing in the UI today
- `Partial`: supported internally or preserved on load/save, but not a proper UI workflow
- `Missing`: core capability exists, but the UI does not expose it in a useful way

Important distinction: the table below tracks individual KrakenOS capability
areas, not phase completion. Phase 1 and Phase 2 are complete at their intended
UI-foundation scopes; several related capability areas remain `Partial` only
because their long-tail expansion continues in later phases.


## What Is Already Strong Today

These are already useful in the current branch:

- editable surface table with tilted/decentered/folded systems
- 2D layout view and legacy 3D viewer
- STEP import/export and CAD overlays
- spot / PSF / RMS / field curvature-distortion / illumination / lateral color
- pupil / Seidel / wavefront / MTF plots
- optimization panel and merit operands
- many example surface attributes now survive import, save/load, and runtime rebuild

The remaining gaps are mainly about making more KrakenOS-native features visible,
editable, and analyzable from the UI.


## Phase Status Snapshot

| Phase | Status | Notes |
| --- | --- | --- |
| Phase 1 | Complete at editor-foundation scope | Ray inspector, explicit trace modes, non-sequential preview bridge, advanced surface editing, and safe custom-surface replay are in place. Remaining non-sequential branching/source-object work is a later roadmap expansion, not a Phase 1 blocker. |
| Phase 2 | Complete at UI-foundation scope | Off-the-shelf catalog import, coating/material workflow, metal CSV loading, polarization analysis, measured error-map import, source/pupil sampling controls, source throughput, and Phase 2 reporting are in place. Weighted nonuniform PSF/MTF accumulation and full tolerance sweeps are deferred analysis enhancements. |
| Phase 3 | In progress | Wide-field spot RMS, PSF, relative illumination, wavefront RMS maps, and atmospheric refraction/dispersion plots with site presets are started. Remaining work is full ADC residual workflow and deeper wavefront/Zernike tooling. |
| Phase 4 | Not started | 3D scene unification and architecture cleanup. |


## Roadmap Summary

| Area | Core Capability | Current UI Status | Priority | Effort |
| --- | --- | --- | --- | --- |
| A | True general non-sequential tracing/editor | Partial | Very High | High |
| B | Advanced surface editor | Partial | Very High | Medium |
| C | User-defined/custom surfaces | Partial | High | High |
| D | Surface error maps / measured surfaces | Complete at Phase 2 scope | High | Medium |
| E | Source and illumination models | Complete at Phase 2 scope | High | Medium |
| F | Coatings, metals, polarization | Complete at Phase 2 scope | High | Medium |
| G | Atmospheric refraction / dispersion | Partial - plot/preset workflow added | Medium | Medium |
| H | Wide-angle PSF / field maps | Complete at Phase 3 map scope | Medium | Medium |
| I | Deeper wavefront / Zernike tooling | Partial | Medium | Medium |
| J | Native optimization-variable workflow | Partial | Medium | Low |
| K | Ray data / per-surface diagnostics | Partial | Medium | Low |
| L | 3D scene unification | Partial | Medium | High |


## A. True General Non-Sequential Tracing/Editor

Status: `Partial`

KrakenOS core supports:

- `system.NsTrace()`
- `Kos.NsTraceLoop()`
- non-sequential examples with tilted optics, prisms, mirrors, and STL solids

Relevant examples:

- `KrakenOS/Examples/Examp_Doublet_Lens_NonSec.py`
- `KrakenOS/Examples/Examp_Doublet_Lens_Tilt_non_sec.py`
- `KrakenOS/Examples/Examp_Prism_STL.py`
- `KrakenOS/Examples/Examp_Solid_Object_STL.py`

Current UI coverage:

- the layout editor still needs a full non-sequential scene model rather than
  just a preview bridge
- the explicit non-sequential preview path reaches KrakenOS `NsTraceLoop()`, but
  there is not yet a proper scene model with branching paths, target surfaces,
  source objects, and hit-tree inspection
- preview ray paths now carry per-hit diagnostics and branch-segment metadata
  from KrakenOS `raykeeper`, including interaction labels, parent branch links,
  hit ranges, and branch termination reasons

Why this matters:

- this is one of KrakenOS's biggest differentiators
- it is the foundation for beam splitters, image slicers, prisms, and realistic folded systems

Recommended implementation:

1. Introduce an explicit non-sequential mode in the editor
2. Add source objects and target controls
3. Represent ray history as a path tree, not just a single polyline
4. Add a non-sequential diagnostics panel:
   - hit surfaces
   - misses
   - clipping
   - optical path
   - transmission/reflection energy


## B. Advanced Surface Editor

Status: `Partial`

Common KrakenOS surface attributes are now editable through the Advanced Surface
dialog. The dialog validates high-risk literal inputs such as coatings, error
maps, UDA polygons, and custom `ExtraData` presets before applying; the UI still
needs richer importers and graphical previews for the most complex cases.

Core surface attrs worth exposing:

- `AspherData`
- `ZNK`
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

Relevant files:

- `KrakenOS/SurfClass.py`
- `KrakenOS/MathShapesClass.py`

Recommended implementation:

1. Add an "Advanced Surface..." editor dialog per selected row
2. Split it into tabs:
   - Shape
   - Aperture/Mask
   - Transform
   - Coating/Material
   - Diagnostics/Notes
3. Keep the main table simple; move complex arrays and special objects into dialogs


## C. User-Defined / Custom Surface Functions

Status: `Partial`

Core capability:

- `ExtraData`
- `UDA`
- `SPECIAL_SURF_FUNC`

Relevant examples:

- `KrakenOS/Examples/Examp_ExtraShape_XY_Cosines.py`
- `KrakenOS/Examples/Examp_ExtraShape_XY_Cosines_UDA.py`
- `KrakenOS/Examples/Examp_ExtraShape_UserFacets.py`
- `KrakenOS/Examples/Examp_ExtraShape_Radial_Sine.py`

Current UI gap:

- literal/list-based `ExtraData` and `UDA` cases can be edited in the Advanced
  Surface dialog
- safe preset dictionaries are supported for replayable `ExtraData` and UDA
  authoring, with `custom_surface_preset_example.py` as a working UI example
- callable/object custom surfaces imported from examples are preserved in memory,
  but unrestricted arbitrary Python object authoring is intentionally not exposed
  as a generic table workflow

Why this matters:

- this is another KrakenOS-specific strength
- it enables micro-lens arrays, custom phase plates, special sag functions, and faceted surfaces

Recommended implementation:

1. Add a "Custom Shape..." editor
2. Support three modes:
   - coefficient-driven built-ins
   - Python UDA hooks
   - mesh/faceted generators
3. Add a preview pane showing the sag/profile before rebuilding the system


## D. Surface Error Maps / Measured Surfaces

Status: `Partial - import workflow added`

Core capability:

- `Error_map = [X, Y, Z, SPACE]`

Current UI gap:

- per-surface `Error Map...` import/clear/validate workflow exists for text,
  `.npy`, and `.npz` measured maps
- the Information panel and `Actions -> Copy Phase 2 Report` summarize
  measured-map surfaces with PV/RMS
- full tolerance sweeps and nominal-vs-perturbed MTF/wavefront overlays are
  deferred analysis enhancements

Why this matters:

- this is how KrakenOS becomes useful for metrology-driven troubleshooting

Recommended implementation:

1. Add optional full tolerance sweeps if Phase 3 analysis scope expands.
2. Add nominal-vs-perturbed MTF/wavefront overlays if a dedicated tolerance
   module is introduced.


## E. Source and Illumination Models

Status: `Complete at Phase 2 scope`

Core capability:

- `KrakenOS/SourceRand.py`
- rich pupil pattern generation in `KrakenOS/PupilTool.py`

Current UI gap:

- a Source panel exposes `PupilCalc` pattern choices: meridional fan, cross fan,
  fan-x, fan-y, hexapolar, square, and random disk
- random circle/square extended-source bundles are available through
  `KrakenOS.SourceRnd`; line and point-cone Monte Carlo source bundles are
  available through deterministic UI-side sampling
- random-source power, per-ray weight statistics, illumination throughput, and
  X/Y/Z launch-plane offsets are available
- nonuniform weighted PSF/MTF/spot accumulation is deferred until the analysis
  pipeline preserves per-ray weights end-to-end

Why this matters:

- many real systems are source-limited rather than field-fan limited
- especially relevant for illumination optics and non-sequential scenes

Recommended implementation:

1. Add weighted PSF/MTF/spot accumulation if later source models produce
   nonuniform ray weights.
2. Add source-object placement helpers tied to imported LED/STEP geometry if
   STEP source geometry becomes part of Phase 4 scene unification.


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

Status: `Partial - plot/preset workflow added`

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
- `atmospheric_dispersion_example.py` demonstrates the analysis workflow

Remaining UI gap:

- full ADC residual plot/workflow is not implemented yet

Why this matters:

- unique value for telescope and long-path optics

Recommended implementation:

1. Add residual-after-ADC workflow once the UI has an ADC element workflow.


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

Status: `Partial`

Core capability:

- `KrakenOS/WavefrontFit.py`
- `KrakenOS/WavePlot.py`

Current UI gap:

- wavefront plot exists, but not the deeper fitting workflow
- no direct coefficient table / export / residual analysis

Recommended implementation:

1. Add a wavefront details panel:
   - fitted Zernike coefficients
   - term count
   - residual RMS
   - P-V and RMS values
2. Add plot styles:
   - wrapped phase
   - unwrapped phase
   - interferogram
   - slope maps
3. Add export to CSV / text


## J. Native Optimization-Variable Workflow

Status: `Partial`

Core capability:

- surface-local `Var = [...]`
- optimization examples that drive surface attrs directly

Relevant example:

- `KrakenOS/Examples/Examp_Tel_2M_Optimization_Variables.py`

Current UI gap:

- the UI has its own variable/operand framework
- but it does not expose the native Kraken-style per-surface variable assignment as a first-class view

Recommended implementation:

1. Add an "Optimization Variables" dialog per surface
2. Show both:
   - UI variable registry
   - native Kraken `Var` attrs
3. Add import/export compatibility between the two models


## K. Ray Data / Per-Surface Diagnostics

Status: `Partial`

Core capability:

- `SURFACE`, `NAME`, `GLASS`
- `XYZ`, `OST_XYZ`
- `LMN`, `R_LMN`, `S_LMN`
- `N0`, `N1`
- `OP`, `TOP`, `TOP_S`
- `RP`, `RS`, `TP`, `TS`, `TT`

Current UI gap:

- the Ray Inspector exposes structured preview-ray diagnostics
- the scene bundle carries per-hit surface, direction, optical path, Fresnel,
  and interaction data for each preview ray
- the scene bundle also carries branch-segment metadata for reflected and
  non-monotonic paths
- plot-picking and CSV export are not implemented yet

Recommended implementation:

1. Extend the Ray Inspector panel
2. Click a ray in 2D or 3D and show:
   - surface-by-surface hit table
   - incidence/refraction/reflection directions
   - optical path
   - transmission
3. Add export to CSV


## L. 3D Scene Unification

Status: `Partial`

Current state:

- 2D path is much more unified than before
- legacy 3D still has its own scene-building logic

Related document:

- `NONSEQUENTIAL_DISPLAY_REFACTOR_PLAN.org`

Recommended implementation:

1. Finish the shared scene bundle for 3D
2. Use the same geometry source for:
   - 2D plot
   - embedded 3D
   - legacy 3D
   - STEP export
3. Make picking and highlighting identical across 2D and 3D


## Suggested Execution Order

### Phase 1: Most Valuable Kraken Differentiators

Status: foundation complete for the planned UI scope. Remaining work in this
area is expansion toward full general non-sequential editing, not a Phase 1
blocker.

1. True non-sequential UI mode
2. Advanced surface editor
3. User-defined/custom surfaces
4. Ray inspector

### Phase 2: Real-World Optics / Fabrication

Status: complete at UI-foundation scope. Continue with Phase 3 next.

1. Error-map workflow: import/edit/clear/validate plus Phase 2 PV/RMS reporting.
2. Coating / metal / polarization workflow: coating editor, metal CSV loading,
   polarization analysis, and Phase 2 report summaries.
3. Off-the-shelf optics catalog import: Edmund/Thorlabs-style stock lens import
   into editable table rows.
4. Source and illumination models: pupil patterns, random circle/square/line
   and point-cone sources, source power/statistics, throughput reporting, and
   launch-plane offsets.

### Phase 3: High-End Imaging and Telescope Workflow

1. Wide-angle PSF / field maps
2. Atmospheric refraction / dispersion
3. Deeper wavefront/Zernike tooling

### Phase 4: Architecture Cleanup

1. 3D scene unification
2. Native optimization-variable bridge
3. remove old special-case display code that becomes redundant


## Short Version: Do Not Miss These

If only a few items are pursued, the biggest KrakenOS-specific wins are:

1. general non-sequential editing and tracing
2. custom surfaces (`UDA`, `ExtraData`, faceted/user functions)
3. measured surface error maps
4. coating / metal / polarization analysis
5. atmospheric refraction / dispersion
6. wide-angle PSF / field maps


## Notes

- Some of these features are already preserved internally in the current branch.
  "Partial" often means the data survives import/save/load, but the UI does not
  yet provide a proper editor, viewer, or analysis workflow.
- This roadmap is about first-class usability, not just attribute passthrough.
