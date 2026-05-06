# KrakenOS UI Core Coverage Audit

Audit date: 2026-05-01

This document tracks KrakenOS core features that should be exposed by the UI.
It complements `KRAKEN_UI_FUTURE_ROADMAP.md`: the roadmap groups work by
phase, while this file maps engine capabilities to current UI coverage so
KrakenOS-specific features are not missed.

Manual cross-check: `docs/source/ui/phase5_manual_crosscheck.rst` maps the
2021 provisional user manual topics to current Phase 5 UI coverage.

## Coverage Status

- `First-class`: editable or runnable through a dedicated UI workflow.
- `Partial`: preserved, imported, displayed, or used internally, but not a full
  user workflow.
- `Passthrough`: saved or replayed as native data, with limited validation.
- `Missing`: core capability exists but is not exposed usefully.

Run `python tools/audit_ui_core_coverage.py` after changing `surf`, examples,
or the layout editor. The tool is source-based, so it does not require GUI
dependencies to be importable.

## Current Coverage Matrix

| Core area | KrakenOS source | Current UI status | Gap / next action |
| --- | --- | --- | --- |
| Sequential exact tracing | `system.Trace`, `TraceLoop`, `BatchTrace` | First-class | Keep regression tests for tilted/decentered and folded layouts. |
| Non-sequential tracing | `system.NsTrace`, `NsTraceLoop` | First-class at KrakenOS scene-list scope | UI exposes explicit non-sequential mode, `energy_probability`, `NsLimit`, target surface, Scene Graph inspector/export, branch path display, Branch Tree Inspector/export, and hit diagnostics. KrakenOS uses an ordered `surf`/STL object list rather than a separate editable node graph; future work is convenience wizards for larger assemblies. |
| Beam splitters | UI `BeamSplitter` metadata plus coating tables and deterministic `NsTrace` branches | First-class for ideal/finite-plate ray branching | The table has a `Beam Splitter` type, right-click settings, saved metadata, generated coating fallback, deterministic transmitted/reflected child branches, branch metadata in `raykeeper`, a finite BK7 plate preset, and a Python example. Coherent Gaussian/interference analysis remains future work. |
| Ray diagnostics | `raykeeper` arrays and `pick()` | First-class at Phase 5 diagnostics scope | Ray Inspector shows per-ray/per-hit data, exports CSV, and can be opened from 2D or 3D ray clicks. Branch-tree inspection/export is first-class; branches are trace results, not manually-authored scene nodes. |
| Standard surface geometry | `Rc`, `k`, `AspherData`, `ZNK`, `Cylinder_Rxy_Ratio`, `Axicon`, shifts | First-class at Shape Builder scope | Main scalar columns are first-class; `Shape...` previews sag/departure from asphere, Zernike, and safe custom-surface presets. |
| Gratings | `Diff_Ord`, `Grating_D`, `Grating_Angle`, diffraction physics | First-class for basic tracing | Keep advanced grating settings out of the main table; add diffraction-order analysis/reporting later. |
| Thin lenses | `Thin_Lens`, paraxial physics | First-class | Current `Thin Lens` row maps the focal length through the `Rc` column. Document this in examples. |
| STL optical solids | `Solid_3d_stl`, non-sequential examples | First-class for import, diagnostics, and tracing; prism authoring deferred | `Shape...` imports/clears optical STL paths; CAD/STL import meshes STEP/IGES to cached STL, diagnostics inspect topology, 2D/3D render the solid, and Scene Graph exposes STL rows as KrakenOS non-sequential object-list nodes. Row tilt/decenter fields remain the execution representation, but arbitrary-prism placement needs a future visual scene-object workflow. |
| Masks and UDA apertures | `Mask_Type`, `Mask_Shape`, `UDA` | First-class at Shape Builder preset scope | `Shape...` previews UDA polygons and Ronchi/spider mask presets, and stores replayable mask preset dictionaries. |
| Custom surface functions | `ExtraData`, `SPECIAL_SURF_FUNC` | First-class for safe preset authoring | `Shape...` previews and edits safe `ExtraData` presets; imported callable/object surfaces are preserved but arbitrary Python authoring remains intentionally unsupported. |
| Surface error maps | `Error_map = [X, Y, Z, SPACE]` | First-class at Phase 2 scope | Add nominal-vs-perturbed overlays and tolerance sweeps only when needed. |
| Coatings and polarization | `Coating`, `CoatingMet`, Fresnel energy arrays | First-class at Phase 2 scope | Add more coating examples and CSV export for per-surface polarization summaries. |
| Source models | `SourceRnd`, UI Monte Carlo sources | First-class at Phase 5 source scope | UI exposes SourceRnd circle/square sources, UI line/point-cone sources, power/origin/seed fields, and `SourceRnd.fun` angular weighting presets. Future analysis enhancement: preserve ray weights end-to-end in PSF/MTF accumulation. |
| Pupil models | `PupilCalc.Ptype` | First-class at Phase 5 source scope | UI covers fan, fan-x, fan-y, hexapolar, square, random disk, `chief`, and `rtheta` with r/theta controls. |
| Atmospheric refraction | atmosphere fields in `PupilCalc` | First-class at Phase 3 scope | Add ADC authoring only if current optics residual workflow is not enough. |
| Wavefront and Zernike | `Phase`, `Phase2`, `WavefrontFit`, `WavePlot` | First-class at Phase 5 export scope | WFront defaults to a Zemax-style Wavefront Function 3D wireframe OPD surface; wavefront maps, Zernike plots, fit report copy, and CSV exports are available. Add plot-linked coefficient selection only if needed later. |
| PSF and MTF | `PSFCalc`, `PSFMap`, UI FFT/geometric workflows | First-class at Phase 3 scope | Add weighted PSF/MTF accumulation for nonuniform sources. |
| Seidel and paraxial analysis | `Seidel`, `Parax`, `ParaxMatrices` | First-class at Phase 5 diagnostics scope | Seidel and calculator exist; `Actions -> Paraxial Matrix Report` exposes the matrix chain with CSV export. |
| Native optimization variables | `surf.Var`, optimizer examples | First-class at Phase 5 breadth scope | UI mirrors `Rc`/`Thickness` flags and native `Var` entries for `k`, tilts, decenters, axis move, and grating pitch/angle. `VarBounds` stores UI bounds for native variables. |
| Glass catalogs | AGF loading in `Setup`, material lookup | First-class at Phase 5 catalog scope | `File -> Glass Catalog Browser` searches KrakenOS AGF glass names and applies selected glasses to table rows. |
| Stock lens catalogs | `zmf2dict`, `cat2surf` | First-class for Edmund/Thorlabs import | Add richer metadata display and catalog glass validation. |
| Zemax text prescriptions | UI `.zmx` parser, `LensCat.zmx_read` | First-class at enhanced parser scope | UI import preserves sequential radii, thicknesses, glass, conic constants, asphere `PARM` data, coatings, and embedded `n/V` fallback glasses. Unsupported aperture/transform tokens are kept in surface notes so they are not silently lost; full coordinate-break/multiconfiguration Zemax semantics remain a future importer expansion. |
| 2D/3D display architecture | `SceneBundle`, 2D, embedded 3D, legacy 3D | First-class at Phase 4 scope | Continue removing legacy-only display helpers after validation. |

## Phase 6 Architecture Guardrail

The post-Phase-5 direction is tracked in
`KRAKEN_UI_NONSEQUENTIAL_ARCHITECTURE.md`. The governing rule is that the UI is
a KrakenOS scene/object editor. Sequential tracing remains a first-class exact
workflow, but it is the axial ordered-surface special case of the scene model.

Coverage audits should therefore ask two questions for each newly exposed
KrakenOS feature:

- Can the feature be used in a scene/non-sequential workflow without forcing
  the user back into a sequential-only mental model?
- Can the user verify the feature through the scene graph, ray inspector, trace
  path inspector, analysis report, plot, or CSV export?

## Surface Attribute Audit

The current `surf` constructor defines the core surface state in
`KrakenOS/SurfClass.py`. The UI now explicitly covers the normal design
columns plus these advanced attributes:

| Attribute group | UI coverage |
| --- | --- |
| Shape | `AspherData`, `ZNK`, `Cylinder_Rxy_Ratio`, `ShiftX`, `ShiftY`, `Surface_type`, `Res` |
| Aperture / mask | `SubAperture`, `Mask_Type`, `Mask_Shape`, `Solid_3d_stl` |
| Coating / material | `Coating`, `CoatingMet`, `Color`, `Nm_Pos` |
| Diagnostics / native | `Note`, `Order`, `Var`, `VarBounds`, `Error_map`, `DerPres`, `NumLabel`, `SPECIAL_SURF_FUNC`, `Const` |
| Beam splitter metadata | `BeamSplitter` |
| Custom surface | `ExtraData`, `UDA` |

The 2026-05-01 audit found two real core attributes that were not explicitly in
the advanced editor:

| Attribute | Meaning | Examples using it | Action |
| --- | --- | --- | --- |
| `DerPres` | Numerical derivative precision for custom/extra surfaces. | `Examp_Fresnel.py`, `Examp_ExtraShape_UserFacets.py` | Added to Advanced Surface -> Diagnostics/Native. |
| `NumLabel` | Numeric label drawing toggle for display outputs. | `Examp_Refraction_Prism.py`, prism solid examples | Added to Advanced Surface -> Diagnostics/Native. |

The same audit found two example-only names that were not KrakenOS core attrs;
both have been corrected in the examples:

| Example attr | Source | Assessment |
| --- | --- | --- |
| `K` | `Examp_Axicon_And_Cylinder.py` | Fixed to `k`; Python examples assigning `K` do not affect core `surf.k`. |
| `Nm_Poss` | `Examp_Doublet_Lens_Pupil.py` | Fixed to `Nm_Pos`; `Nm_Poss` is not a core `surf` attribute. |

## High-Value Gems Exposed By Phase 5

1. General non-sequential scene editing: the Phase 5 UI pass now exposes
   `energy_probability`, `NsLimit`, target surfaces, the KrakenOS scene/object
   list, branch-tree inspection, and ray/hit diagnostics.
   Branches are generated by `NsTraceLoop()` and inspected after tracing rather
   than edited as source nodes.
2. Custom surface authoring: `Shape...` now provides guided, previewable
   workflows for safe `ExtraData`, UDA polygons, Ronchi/spider masks, and
   optical STL paths. Remaining future work is specialized faceted/Fresnel
   builders if users need them.
3. Ray data products: CSV export now covers `SURFACE`, `XYZ`, `LMN`, `OP`,
   `N0/N1`, `RP/RS/TP/TS`, and transmission arrays; 2D and 3D plot ray-picking
   route selected rays into Ray Inspector.
4. Paraxial matrix chain: `system.ParaxMatrices()` is now inspectable and
   exportable from the UI.
5. Material/catalog browser: KrakenOS AGF glass names and `n/V` values are now
   searchable and can be applied to selected rows.
6. Native optimization breadth: Phase 5 now covers conic, transform, and
   grating pitch/angle variables through native `Var` storage; remaining future
   work is richer per-surface variable management and constraints.
7. Zemax import preservation: `.zmx` imports now retain conics, asphere
   coefficients, coating names, embedded `n/V` fallback glasses, and notes for
   unsupported aperture/transform tokens.
8. Beam splitters: deterministic reflected+transmitted child branch spawning is
   in place with branch power, phase, path, source, and polarization metadata.
   Phase 6 adds path-component placement and geometric coherent detector
   accumulation. Post-Phase-6 work is full folded/non-sequential Gaussian `q`
   state and diffraction field propagation.

## Recommended Phase 5 Slices

Phase 5 is complete at the audit/core-controls scope. Items marked `Deferred`
are larger authoring or optimization expansions that should be scheduled as a
future breadth pass, not treated as hidden Phase 5 blockers.

### Phase 5A: Coverage Guardrails

- Keep this document current.
- Use `tools/audit_ui_core_coverage.py` to compare `surf` constructor attrs and
  example attrs against the UI registries.
- Fail loudly when a new core attr is not documented as first-class, partial,
  passthrough, or intentionally unsupported.

### Phase 5B: Non-Sequential Completeness

- Done: UI fields for `energy_probability` and `NsLimit`.
- Done: target-surface controls using `TargSurf()` / `TargSurfRest()`.
- Done: Non-Sequential Scene Graph inspector/export for the source settings,
  trace controls, element groups, surface rows, STL rows, masks, coatings, and
  target selection.
- Done at inspector scope: branch/hit data display and CSV export in Ray
  Inspector.
- Done: add a non-sequential diagnostics reference layout.
- Done: add a non-sequential scene graph reference layout.

### Phase 5C: Custom Surface Completeness

- Done: safe `ExtraData`/UDA preset dictionaries are validated and replayed
  through the Advanced Surface dialog and examples.
- Done: `Shape...` provides previewable asphere/Zernike/custom sag, UDA,
  Ronchi/spider mask, and optical STL path workflows.
- Deferred: add specialized faceted/Fresnel/profile builders only if users need
  more than the safe preset workflow.

### Phase 5D: Data Export and Diagnostics

- Done: CSV export for Ray Inspector.
- Done: `ParaxMatrices()` report and CSV export.
- Done: CSV export for wavefront samples and Zernike coefficients/residuals.
- Done: 2D and 3D ray picking opens/selects rays in Ray Inspector.

### Phase 5E: Catalog and Optimization Breadth

- Done: glass catalog browser.
- Existing scope: grating-only settings were moved into a row-level additional
  settings dialog, and catalog glass names can be applied from the browser.
- Done: expand optimization variables beyond `Rc` and `Thickness` for conic,
  tilts, decenters, axis move, and grating pitch/angle.
- Done: Zemax text imports preserve conics, asphere `PARM` data, coatings,
  embedded fallback glasses, and importer notes for unsupported tokens.

## Phase 5 UI Examples

The common-layout dropdown now includes Phase 5-focused examples:

| Example | Demonstrates |
| --- | --- |
| `Non-Sequential Ray Diagnostics Example` | Explicit non-sequential mode, `NsLimit`, target-surface workflow, Ray Inspector CSV export. |
| `Non-Sequential Scene Graph Example` | `Actions -> Non-Sequential Scene Graph`, SourceRnd source node, grouped element nodes, target selection, and scene CSV export. |
| `Branch Tree Diagnostics Example` | Branch Tree Inspector workflow with branch parent links, hit ranges, and CSV export. |
| `Surface Shape Builder Example` | `Shape...` workflow for asphere/custom sag preview, UDA polygon, mask preset, and optical STL path staging. |
| `R-Theta Pupil Diagnostic Example` | `PupilCalc.Ptype = "rtheta"` with editable normalized pupil radius and azimuth. |
| `Weighted SourceRnd Example` | `SourceRnd.fun` angular weighting preset through the Source panel. |
| `Native Variable Breadth Example` | Native `Var` / `VarBounds` optimization marks for conic and tilt variables. |
| `Beam Splitter 50/50 Example` | Deterministic `Beam Splitter` front face, BK7 substrate thickness, rear AIR face, and transmitted/reflected branch display. |
