# Kraken UI Phase 8 Plan

Phase 8 should be a bounded next phase, not an open-ended polish loop. Phase 7
closed the non-sequential refinement backlog at the current validation scope.
Phase 8 should target the remaining capabilities that materially improve laser,
interferometer, and complex folded-system design.

## Phase 8 Goal

Make branch-aware wave/field propagation and advanced folded-system authoring
usable enough that laser/interferometer layouts can be evaluated beyond ray
bundles and detector-bin power sums.

The practical target is:

1. carry a physically meaningful complex field through traced branch data,
2. compare field propagation against analytic Gaussian/q and detector-bin
   coherent results,
3. expose mode-overlap and diffraction results in the UI without breaking the
   existing ray-first workflows,
4. harden the UI architecture so future analysis panels are smaller, testable,
   and easier to maintain.

## What Phase 8 Is Not

Phase 8 is not a general rewrite of KrakenOS or the layout editor. It should not
try to solve every UI wishlist. It should also not replace the ray-tracing UI:
ray tracing remains the fast preview, diagnostic, and alignment workflow.

Defer these unless they directly support the chosen Phase 8 slice:

- general-purpose CAD assembly mating for every vendor solid format,
- complete physical optics for every arbitrary surface type,
- full commercial Zemax/Code V parity,
- cosmetic UI redesign not tied to measurable workflow speed or correctness.

## Workstreams

### 8A. Branch Field Propagation And Mode Overlap

Priority: highest.

Current foundation:

- Phase 7B provides detector-bin coherent accumulation and diffraction FFT.
- Phase 7C provides branch-local Gaussian frames, tangential/sagittal q traces,
  clipping loss, and Gaussian-q detector recombination.
- Ray Inspector and Trace Path Inspector already expose branch/hit records that
  can seed a branch field propagator.

Phase 8 target:

1. define a reusable branch-field data contract with complex Ex/Ey or scalar
   complex amplitude, local detector/grid coordinates, wavelength, power
   normalization, phase reference, and source coherence group,
2. implement first scalar Fresnel/angular-spectrum propagation from a selected
   branch or detector plane,
3. add Gaussian TEM00 mode-overlap against the propagated field,
4. expose a first `Field` or enhanced `Diffr` analysis view with power
   conservation, beam radius, centroid, phase, and overlap metrics,
5. export the propagated field summary and grid metadata to CSV/NPZ where
   practical.

Suggested validators:

- `validate_phase8_field_contract`
- `validate_scalar_field_propagation`
- `validate_gaussian_mode_overlap`
- compare propagated free-space Gaussian waist/radius against analytic q,
- compare detector FFT power against existing Phase 7B diffraction validator.

Stop condition:

- a Michelson or Mach-Zehnder Gaussian-source layout can show detector field
  intensity/phase and TEM00 overlap from traced branch data, with power
  conservation and analytic Gaussian sanity checks passing.

### 8B. Oblique Astigmatic Surface Matrices

Priority: high, after 8A has a field contract.

Status: complete at the Phase 8B Gaussian-q contract scope. Full thick tilted
plate and arbitrary CAD/prism wave propagation is intentionally deferred to a
later branch-field/physical-optics phase.

Current foundation:

- Phase 7C carries branch-local tangential/sagittal frames.
- `KrakenOS.propagate_branch_gaussian_q` already handles free space, flat
  folds, planar index changes, conservative first-order spherical power, and
  explicit q-only/TIR diagnostics for unsupported oblique cases.

Phase 8 target:

1. improve tangential/sagittal ABCD updates for oblique spherical surfaces,
   tilted plates, mirrors, and finite beam-splitter plates,
2. report where a surface falls back to conservative/flat behavior,
3. add examples that show astigmatic waist split after tilted plates and
   folded mirrors,
4. feed the improved q states into mode-overlap and detector-field diagnostics.

Validators:

- `validate_oblique_astigmatic_q`
- `validate_branch_gaussian_q_report`
- `validate_phase8b_complete`

Stop condition:

- reached for the q-contract scope: folded mirrors, oblique spherical
  refraction, real traced-layout hits, Branch Gaussian Q Report rows, q-only
  flat tilted-plate diagnostics, and TIR-deferred diagnostics are finite,
  deterministic, and validated by `python -m KrakenOS.UI.validate_phase8b_complete`.

### 8C. CAD/Prism Assembly Workflow

Priority: medium. This is important, but should not block 8A.

Current foundation:

- CAD/STL solids import, diagnose, render, trace, and snap to ray/path.
- Optical face roles and virtual splitter planes are saved as metadata.
- Phase 7A validates face anchors, path frames, virtual planes, and hit
  sequence classification.

Phase 8 target:

1. add a compact assembly workflow for common prism/cube workflows, not a full
   CAD system,
2. let users duplicate/mate imported solids to traced paths with saved anchor
   face, roll constraint, and material provenance,
3. make face-role summaries easier to audit in the table and Scene Graph,
4. add examples for a prism train and a cube splitter assembly using the same
   validated metadata.

Suggested validators:

- `validate_prism_assembly_workflow`
- `validate_cube_splitter_solid_workflow`
- `validate_cad_face_role_roundtrip`

Stop condition:

- a user can build a small prism/cube assembly from imported solids using
  visual face-role and snap/path helpers without hand-editing every tilt/decenter
  number.

### 8D. UI Architecture And Product Hardening

Priority: continuous, but only when it reduces concrete risk.

Current issue:

- `KrakenOS/UI/layout_editor.py` is now very large. The feature surface is
  broad, and regressions are increasingly likely if analysis logic, UI dialogs,
  persistence, and plotting stay tightly coupled.

Landed slices:

- Branch Gaussian q report collection, summary formatting, copy text, table
  values, and CSV columns now live in `KrakenOS/UI/branch_gaussian_q_report.py`.
  `layout_editor.py` keeps the Tk dialog and compatibility wrappers only.
  `python -m KrakenOS.UI.validate_branch_gaussian_q_report` checks service/UI
  parity and the exported column contract.
- Coherent detector constants, grouping/pair keys, coherent CSV row export,
  FFT vector-field intensity, and diffraction-detector angular-spectrum data
  now live in `KrakenOS/UI/coherent_detector_analysis.py`. `layout_editor.py`
  keeps plotting, dialogs, progress, and trace collection. `validate_diffraction_detector`
  and `validate_detector_sampling_stability` check service/UI parity and export
  row contracts.
- Path-throughput aggregation, path filter choices/matching, report
  summary/table/copy text, branch path labels, and CSV export now live in
  `KrakenOS/UI/branch_throughput_analysis.py`. `layout_editor.py` keeps the Tk
  report dialog and row-specific terminal/detector adapters.
  `validate_branch_analysis` checks service/UI parity for the throughput report
  and export contracts.
- Branch-field detector promotion, scalar propagation, TEM00 overlap data, and
  branch-field CSV export now live in `KrakenOS/UI/branch_field_analysis.py`.
  `layout_editor.py` keeps the `BField` controls, plotting, progress, and
  trace collection. `validate_phase8_field_contract` checks service/UI parity
  and the CSV row contract.
- Detector map, path PSF, and path MTF data assembly, histogram/FFT
  calculations, CSV schemas, and row generation now live in
  `KrakenOS/UI/detector_path_analysis.py`. `layout_editor.py` keeps detector
  ray collection, plotting, and dialogs. `validate_branch_analysis` checks
  service/UI parity plus DetMap/PSF/MTF export row contracts.
- Source-illumination record grouping, target-hit sample assembly, map
  extent/binning/density, per-source centroid calculations, report
  summary/detail/table text, and CSV export now live in
  `KrakenOS/UI/source_illumination_analysis.py`. `layout_editor.py` keeps target
  selection, local-coordinate adapters, plotting, and the Tk report window.
  `validate_multi_scene_sources` checks service/UI parity for the record,
  sample, map, and report contracts.
- Scene-source spec normalization/deduping, setting serialization, source-object
  construction, visible source feature/detail text, and Source panel/Scene
  Source Manager summaries now live in
  `KrakenOS/UI/scene_source_analysis.py`. `layout_editor.py` keeps Tk state,
  table synchronization, and compatibility wrappers. `validate_scene_row_mapping`
  checks service/UI parity for source rows and source-summary text.
- CAD/STL optical-solid face-role metadata normalization, function/side
  coercion, auto side-label assignment, virtual cube-splitter plane construction,
  role colors, face-summary text, world face/virtual-plane transforms, face
  matching, segment-plane crossing, hit-sequence classification, face-fit pose
  solving, auto-roll reference selection, and snap-to-ray anchor scoring now live in
  `KrakenOS/UI/optical_solid_metadata.py`. `layout_editor.py` keeps STL face
  clustering, 3D/Tk previews, placement dialogs, and compatibility wrappers.
  `validate_optical_solid_face_roles`, `validate_optical_solid_face_fit`,
  `validate_optical_solid_virtual_plane`, and
  `validate_optical_solid_hit_sequence` check service/UI parity for face
  metadata, world transforms, face-fit/snap helpers, virtual splitter-plane
  helpers, and hit-sequence classification.
- STL byte parsing, mesh diagnostics/formatting, transformed bounds/points, and
  reusable 2-D hull helpers now live in `KrakenOS/UI/stl_geometry.py`.
  `layout_editor.py` keeps compatibility wrappers and higher-level CAD import,
  face clustering, plotting, and 3D placement behavior. `validate_optical_solid_face_roles`
  checks service/UI parity for STL diagnostics and transform/hull contracts.
- CAD cache-path construction, STEP/IGES-to-STL conversion, source-to-mesh
  resolution, and external CAD helper-tool subprocess wrappers now live in
  `KrakenOS/UI/cad_import_service.py`. `layout_editor.py` keeps file dialogs,
  CAD/STEP overlay state, progress reporting, and compatibility wrappers.
  `validate_optical_cad_solid_import` checks service/UI parity for cache and
  source-to-mesh resolution without requiring a vendor STEP fixture.
- Embedded 3D selection no longer starts camera rotation on plain left click.
  Plain left click selects/picks objects and rays; left hold-drag rotates
  around the current view focal point with fixed sensitivity and no inertial
  acceleration. `Ctrl` + left drag follows the same rotation path for
  compatibility. Imported lens/LED/camera STEP overlays now share the same
  selected-object `X/Y/Z +/-90` rotation convention through a click-near
  `STEP rotation handler`; the older duplicate toolbar `STEP Rotate` menu was
  removed. This replaces the older partial `Z +/-90` plus `X 180` controls and
  adds one `Center STEP Axis` workflow for feature centering, active 3D
  workflow badges for armed pick modes, plus a long dotted optical-axis guide
  at `X=0, Y=0`.
- The embedded 3D CAD/STL placement buttons no longer occupy a persistent
  second toolbar row. Selecting a file-backed CAD/STL solid row, or launching
  `Actions -> 3D Place/Orient Selected CAD/STL Solid`, now opens a contextual
  `CAD/STL placement handler` popup with local-axis fit, repeated `X/Y/Z +/-90`
  rotations, `Center X/Y`, `Front On Row`, `Done -> 2D`, and inline
  "What this does" guidance. `Case Study 14: 3D Hardware Alignment Workflows`
  documents the embedded 3D inspector, optical-axis/face overlays, placement
  handler, mode badges, STEP rotation handler, and source-target pick mode with
  generated screenshots and `validate_3d_hardware_alignment_case_study`.
- `python -m KrakenOS.UI.validate_demo_readiness --full` runs the pre-demo
  validator set, including the embedded 3D interaction contract, STEP-axis
  centering workflow, case-study checks, menu smoke test, and Sphinx
  docs build.
- `Case Study 15: Cooke Triplet Optimization From A Bad Start` ports the
  Optiland-inspired poor-to-optimized triplet workflow into a menu-backed
  layout, generated Spot/MTF screenshots, a runnable Python example, and
  `python -m KrakenOS.UI.validate_cooke_triplet_case_study`.
- `Case Study 16: One Lens, Many Analyses` ports Optiland-inspired
  PSF/MTF and Zernike workflows into a stable Double Gauss UI layout with
  Spot, PSF, MTF, Wavefront Function, Zernike, generated screenshots, a
  runnable Python example, and
  `python -m KrakenOS.UI.validate_double_gauss_analysis_case_study`.
- A low-risk modern ttk theme helper exists in
  `KrakenOS.UI.modern_ttk_theme`, but it is intentionally not applied to the
  main editor yet. UI theming is deferred to a separate future phase so the
  existing Tk/ttk controls are refreshed consistently rather than mixed with
  partial modern styles; see `KRAKEN_UI_PHASE9_THEME_PLAN.md`.
- Menu-backed layouts/examples now have a display smoke validator:
  `python -m KrakenOS.UI.validate_menu_smoke` loads the same UI-loadable
  Layouts, Machine Vision layouts, and Examples, builds a 2-D Agg render, and
  verifies an offscreen 3-D scene has actors. Use `--include-zemax` before
  release/demo preparation to cover testing Zemax prescriptions as well. The
  Examples menu deliberately excludes script-only tutorials that do not define a
  UI-loadable system and import-time file-writing tutorials.

Phase 8 target:

1. extract stable analysis services from `layout_editor.py` where there is a
   clear seam: tolerance, coherent detector/field, CAD face metadata, scene
   source management, and render/export helpers,
2. keep public UI behavior unchanged while moving code behind small testable
   functions,
3. add lightweight command/menu discoverability for dense menus,
4. add performance guardrails for expensive analyses: cancellation, progress,
   cache invalidation, and clear stale-result labels,
5. add screenshot/render smoke checks for important presets where feasible.

Suggested validators:

- keep `validate_phase6_complete` and `validate_phase7_complete` green during
  extraction,
- add small unit validators for any extracted service module,
- `validate_branch_gaussian_q_report` for the first Branch Gaussian q service
  extraction,
- `validate_diffraction_detector` and `validate_detector_sampling_stability`
  for coherent/diffraction detector service extraction,
- `validate_phase8_field_contract` for branch-field service extraction,
- `validate_menu_smoke` for menu-backed layout/example 2-D and offscreen 3-D
  smoke coverage,
- add render snapshots only for stable deterministic views.

Stop condition:

- at least one high-risk analysis area is extracted from the monolith with no
  validator regression, and expensive analyses have clearer progress/stale-data
  behavior.

### 8E. Documentation And Examples

Priority: required for every implemented Phase 8 slice.

Each Phase 8 feature should include:

1. one UI workflow section in Sphinx docs,
2. one runnable example under `KrakenOS/Examples`,
3. one validator or aggregate validator inclusion,
4. a concise explanation of assumptions and fallback behavior.

## Recommended Execution Order

1. Draft and agree this Phase 8 plan. Done in `e2cbf8b`.
2. Implement 8A branch-field data contract and a minimal scalar propagation
   validator. First slice implemented with `KrakenOS.BranchField`,
   `KrakenOS/Examples/Examp_Branch_Field_Propagation.py`,
   `python -m KrakenOS.UI.validate_phase8_field_contract`, and
   `python -m KrakenOS.UI.validate_phase8_complete`.
3. Add the first UI analysis surface for field intensity/phase and TEM00
   overlap. Done with the `BField` analysis mode, which promotes coherent
   detector data into `BranchFieldGrid`, displays normalized intensity plus
   phase contours, reports fitted TEM00 overlap, supports a user-entered
   paraxial propagation distance, and exports branch-field CSV data.
4. Improve oblique astigmatic q matrices only after the field contract is
   stable. Started with `validate_oblique_astigmatic_q`, which locks down the
   flat-fold, oblique mirror, near-normal refraction, and first oblique
   spherical-refraction contracts; the same validator now exercises a real
   traced `Galvo F-Theta Laser Scanner` UI layout for oblique refractive
   q-power terms plus flat tilted-plate and TIR-deferred diagnostics.
   `Actions -> Branch Gaussian Q Report` and
   `validate_branch_gaussian_q_report` expose the same per-hit q notes,
   powers, states, clipping, and stability flags for real traced layouts.
   Closed at the Phase 8B q-contract scope with
   `python -m KrakenOS.UI.validate_phase8b_complete`; full thick tilted-plate
   wave propagation is deferred beyond 8B.
5. Pick one CAD/prism assembly workflow only if real layouts need it.
6. Extract/refactor UI services opportunistically when touching the relevant
   analysis code.

## Phase 8 Closure Criteria

Phase 8 should close when:

- the aggregate Phase 8 validator exists and passes,
- the chosen field-propagation workflow has documentation and examples,
- existing Phase 6 and Phase 7 aggregate validators still pass,
- remaining wishlist items are explicitly moved to a later phase.

The initial aggregate validator is:

```bash
python -m KrakenOS.UI.validate_phase8_complete
```

It starts with the 8A branch-field contract and should grow only as real Phase
8 slices land.
