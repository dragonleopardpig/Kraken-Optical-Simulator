# KrakenOS UI Core Coverage Audit

Audit date: 2026-05-01

This document tracks KrakenOS core features that should be exposed by the UI.
It complements `KRAKEN_UI_FUTURE_ROADMAP.md`: the roadmap groups work by
phase, while this file maps engine capabilities to current UI coverage so
KrakenOS-specific features are not missed.

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
| Non-sequential tracing | `system.NsTrace`, `NsTraceLoop` | Partial / first-class trace controls | UI exposes explicit non-sequential mode, `energy_probability`, `NsLimit`, target surface, branch path display, and hit diagnostics. Remaining gap: full source/object scene graph and interactive branch-tree editing. |
| Ray diagnostics | `raykeeper` arrays and `pick()` | Partial / first-class inspector export | Ray Inspector shows per-ray/per-hit data and exports CSV. Remaining gap: click-to-pick rays directly from 2D/3D plots. |
| Standard surface geometry | `Rc`, `k`, `AspherData`, `ZNK`, `Cylinder_Rxy_Ratio`, `Axicon`, shifts | First-class / Partial | Main scalar columns are first-class; arrays are advanced-dialog workflows. Add better sag previews. |
| Gratings | `Diff_Ord`, `Grating_D`, `Grating_Angle`, diffraction physics | First-class for basic tracing | Keep advanced grating settings out of the main table; add diffraction-order analysis/reporting later. |
| Thin lenses | `Thin_Lens`, paraxial physics | First-class | Current `Thin Lens` row maps the focal length through the `Rc` column. Document this in examples. |
| STL optical solids | `Solid_3d_stl`, non-sequential examples | Partial | Add import/alignment workflow where STL is an optical element, not only CAD context. |
| Masks and UDA apertures | `Mask_Type`, `Mask_Shape`, `UDA` | Passthrough / Partial | Add graphical mask/UDA editor, Ronchi/spider presets, and mask preview. |
| Custom surface functions | `ExtraData`, `SPECIAL_SURF_FUNC` | Partial | Safe presets exist; add richer profile/faceted/Fresnel authoring without unsafe arbitrary Python in table cells. |
| Surface error maps | `Error_map = [X, Y, Z, SPACE]` | First-class at Phase 2 scope | Add nominal-vs-perturbed overlays and tolerance sweeps only when needed. |
| Coatings and polarization | `Coating`, `CoatingMet`, Fresnel energy arrays | First-class at Phase 2 scope | Add more coating examples and CSV export for per-surface polarization summaries. |
| Source models | `SourceRnd`, UI Monte Carlo sources | First-class at Phase 5 source scope | UI exposes SourceRnd circle/square sources, UI line/point-cone sources, power/origin/seed fields, and `SourceRnd.fun` angular weighting presets. Remaining gap: preserve ray weights end-to-end in PSF/MTF accumulation. |
| Pupil models | `PupilCalc.Ptype` | First-class at Phase 5 source scope | UI covers fan, fan-x, fan-y, hexapolar, square, random disk, `chief`, and `rtheta` with r/theta controls. |
| Atmospheric refraction | atmosphere fields in `PupilCalc` | First-class at Phase 3 scope | Add ADC authoring only if current optics residual workflow is not enough. |
| Wavefront and Zernike | `Phase`, `Phase2`, `WavefrontFit`, `WavePlot` | First-class at Phase 3 scope | Add CSV export for wavefront/Zernike data products. |
| PSF and MTF | `PSFCalc`, `PSFMap`, UI FFT/geometric workflows | First-class at Phase 3 scope | Add weighted PSF/MTF accumulation for nonuniform sources. |
| Seidel and paraxial analysis | `Seidel`, `Parax`, `ParaxMatrices` | First-class at Phase 5 diagnostics scope | Seidel and calculator exist; `Actions -> Paraxial Matrix Report` exposes the matrix chain with CSV export. |
| Native optimization variables | `surf.Var`, optimizer examples | First-class at Phase 5 breadth scope | UI mirrors `Rc`/`Thickness` flags and native `Var` entries for `k`, tilts, decenters, axis move, and grating pitch/angle. `VarBounds` stores UI bounds for native variables. |
| Glass catalogs | AGF loading in `Setup`, material lookup | First-class at Phase 5 catalog scope | `File -> Glass Catalog Browser` searches KrakenOS AGF glass names and applies selected glasses to table rows. |
| Stock lens catalogs | `zmf2dict`, `cat2surf` | First-class for Edmund/Thorlabs import | Add richer metadata display and catalog glass validation. |
| Zemax text prescriptions | UI `.zmx` parser, `LensCat.zmx_read` | Partial | Unify import with `LensCat` parsing to preserve conics/aspheres/coatings more completely. |
| 2D/3D display architecture | `SceneBundle`, 2D, embedded 3D, legacy 3D | First-class at Phase 4 scope | Continue removing legacy-only display helpers after validation. |

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

## Highest-Value Missing Gems

1. General non-sequential scene editing: the Phase 5 UI pass now exposes
   `energy_probability`, `NsLimit`, target surfaces, and ray/hit diagnostics.
   The remaining larger gap is a source/object scene graph for arbitrary
   non-sequential assemblies.
2. Custom surface authoring: add guided workflows for profile CSV, Fresnel
   curves, faceted surfaces, UDA polygons, Ronchi/spider masks, and safe preset
   extension.
3. Ray data products: CSV export now covers `SURFACE`, `XYZ`, `LMN`, `OP`,
   `N0/N1`, `RP/RS/TP/TS`, and transmission arrays; plot ray-picking remains.
4. Paraxial matrix chain: `system.ParaxMatrices()` is now inspectable and
   exportable from the UI.
5. Material/catalog browser: KrakenOS AGF glass names and `n/V` values are now
   searchable and can be applied to selected rows.
6. Native optimization breadth: Phase 5 now covers conic, transform, and
   grating pitch/angle variables through native `Var` storage; remaining future
   work is richer per-surface variable management and constraints.

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
- Done at inspector scope: branch/hit data display and CSV export in Ray
  Inspector.
- Done: add a non-sequential diagnostics reference layout.
- Deferred: add a full STL-backed non-sequential scene-authoring example when
  the source/object scene graph exists.

### Phase 5C: Custom Surface Completeness

- Existing scope: safe `ExtraData`/UDA preset dictionaries are validated and
  replayed through the Advanced Surface dialog and examples.
- Deferred: add a dedicated Custom Shape editor with profile/faceted/Fresnel
  modes and preview plots.

### Phase 5D: Data Export and Diagnostics

- Done: CSV export for Ray Inspector.
- Done: `ParaxMatrices()` report and CSV export.
- Deferred: add CSV export for wavefront/Zernike reports if text-copy reports
  become insufficient.

### Phase 5E: Catalog and Optimization Breadth

- Done: glass catalog browser.
- Existing scope: grating-only settings were moved into a row-level additional
  settings dialog, and catalog glass names can be applied from the browser.
- Done: expand optimization variables beyond `Rc` and `Thickness` for conic,
  tilts, decenters, axis move, and grating pitch/angle.

## Phase 5 UI Examples

The common-layout dropdown now includes Phase 5-focused examples:

| Example | Demonstrates |
| --- | --- |
| `Non-Sequential Ray Diagnostics Example` | Explicit non-sequential mode, `NsLimit`, target-surface workflow, Ray Inspector CSV export. |
| `R-Theta Pupil Diagnostic Example` | `PupilCalc.Ptype = "rtheta"` with editable normalized pupil radius and azimuth. |
| `Weighted SourceRnd Example` | `SourceRnd.fun` angular weighting preset through the Source panel. |
| `Native Variable Breadth Example` | Native `Var` / `VarBounds` optimization marks for conic and tilt variables. |
