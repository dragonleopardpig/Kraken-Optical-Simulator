# Kraken UI Phase 7 Plan

This document turns the post-Phase-6 refinement backlog into an execution plan.
Phases 1 through 6 already exposed KrakenOS core features at useful UI scope.
Phase 7 is not about basic feature parity. It is about closing the biggest
remaining gaps between the current editor and the long-term target:

1. true non-sequential-first scene authoring
2. 3D optical execution behind the scene, with 2D as a slice or report view
3. strict source/object separation for illumination workflows
4. surface interactions that obey physics without hidden workflow exceptions

## Scope

Phase 7 focuses on the remaining high-value areas that still limit serious
non-sequential and folded-system work:

1. prism/CAD scene-object authoring
2. coherent detector and diffraction-grade branch analysis
3. oblique Gaussian beam propagation through folded/non-sequential paths
4. direct multi-source scene editing and source/object placement helpers
5. manufacturing/tolerance workflow expansion

These are parallel workstreams. The recommended order below is an architectural
preference, not a gate: tolerance work in 7E can advance while small 7D
source-row polish is still being closed.

## What Phase 7 Is Not

Phase 7 is not a rewrite of Phases 1 to 6. Existing table editing, branch-path
filtering, detector analysis, source controls, CAD/STL import, and current
coherence/diffuse workflows remain the base. Phase 7 refines the hardest
remaining workflows on top of that base.

## Gap Summary

### A. Prism/CAD scene-object workflow

Current state:

- CAD/STL optical solids import, trace, diagnose, and render in embedded 3D.
- Face-role metadata can be assigned visually and stored as
  `OpticalSolidFaces`.
- CAD/STL solids can be moved with `TiltX/Y/Z`, `DespX/Y/Z`, visual placement,
  and `Center Row->Ray`.

Remaining gap:

- arbitrary prisms and imported vendor solids still rely too much on manual
  pose editing
- face-role assignment now supports the current anchor/path/roll workflow, but
  broader arbitrary-prism assembly helpers are still future work
- users still need richer assembly-scale helpers for complex vendor solids and
  nested prism trains

Execution slices:

1. Face-anchor snap to traced ray/path
2. explicit anchor/roll constraints in the placement workflow
3. path-frame snap helpers for imported solids
4. virtual internal optical planes for cube beam splitters and similar solids
5. hit-sequence validator against assigned face roles

### B. Coherent detector / interferometry

Current state:

- deterministic splitter branches carry power, phase, and Jones metadata
- `CohDet` performs the first detector-binned coherent accumulation
- Michelson, Twyman-Green, and Mach-Zehnder workflows are usable today

Remaining gap:

- current interferograms are still partly analytic/path-average
- the UI does not yet provide a full detector-pixel field propagation workflow
- diffraction-grade branch propagation remains unfinished

Execution slices:

1. retire analytic fringe shortcuts where detector-bin field sums are reliable
2. unify detector-port coherent accumulation and export
3. add diffraction-oriented detector propagation where branch metadata is already available
4. extend validation for interference, polarization, and detector sampling stability

### C. Oblique Gaussian beam propagation

Current state:

- centered paraxial Gaussian/q propagation is available
- representative 2D source bundles are shown in the layout

Remaining gap:

- no full oblique Gaussian q propagation through splitter/folded paths
- no branch-local tangential/sagittal propagation through non-sequential hits
- no coherent Gaussian recombination through split branches

Execution slices:

1. branch-local tangential/sagittal frames at each hit
2. branch-carried q propagation through deterministic splitter trees
3. branch-local clipping/loss accumulation
4. detector-side Gaussian recombination checks

### D. Direct multi-source scene editing

Current state:

- scene sources are first-class scene objects
- source rows are visible in the table
- source illumination reports and target illumination maps exist
- Scene Source Manager handles add/edit/delete/duplicate workflows and now has
  an `Aim Direction At Row` helper that points a physical source at Object,
  surface, Image, or file-backed CAD/STL row centers by computing normalized
  source `L/M/N` direction cosines
- Scene Source Manager also has `Place Origin At Standoff`, which places
  source `X/Y/Z` a positive distance upstream of the target row along the
  current source direction
- When a CAD/STL row has assigned `OpticalSolidFaces`, both helpers can target
  an individual transformed face centroid instead of only the row/mesh center
- The CAD/STL face assignment dialog has `Use Face As Source Target`, which
  saves the selected face metadata and opens Scene Source Manager with that face
  preselected
- The 3D Inspector has `Source Target` pick mode, which opens Scene Source
  Manager from a clicked row and resolves the nearest assigned CAD/STL face
  anchor when available

Remaining gap:

- direct source-row editing is still lighter than surface editing
- source/object placement supports row-center direction, source-origin standoff
  helpers, assigned CAD face anchors, a face-dialog shortcut, and 3D row/face
  pick handoff; arbitrary picked-point source targets remain deferred

Execution slices:

1. direct source-row editing/workbench: implemented through Scene Source
   Manager plus source-row duplicate/delete/move actions
2. source-to-object and source-to-CAD placement helpers: direction aiming
   and source-origin standoff placement implemented for row centers and assigned
   CAD/STL face anchors; face assignment dialog can preselect source targets;
   3D Inspector can pick a row/face source target
3. mixed illumination/imaging scene templates: `Mixed Source/Object Imaging
   Template`, `KrakenOS/Examples/Examp_Mixed_Source_Object_Imaging_Template.py`,
   and `python -m KrakenOS.UI.validate_mixed_source_object_template`
   implemented as the source-first starter layout
4. tighter source-path diagnostics for vignetting and uniformity: Source
   Illumination Report now records per-source missed power, dominant loss
   terminal, terminal-count breakdown, CSV columns, and Illum plot loss summary
5. source rows in the editable table now expose direct right-click actions for
   duplicate, delete, and move up/down while keeping sources outside the
   KrakenOS `surf` list; `python -m
   KrakenOS.UI.validate_scene_source_row_contract` covers the source-row action
   contract

### E. Manufacturing and tolerance workflow

Current state:

- error maps, optimization variables, ISO-style PDF export metadata, and reports
  are available
- tolerance Monte Carlo report uses marked optimization/native variables as
  sampled tolerance variables, evaluates the selected merit operands, preserves
  the nominal table, and exports the batch schema to CSV

Remaining gap:

- single-compensator sweeps, deterministic multi-compensator coordinate solves,
  and saved solve presets exist; production stack-up dashboards are still
  deferred
- richer coupled variable constraints and compensator eligibility rules are
  still limited
- nominal-vs-perturbed overlays exist for worst-sample spot, MTF, and WFE;
  broader comparison UX can still be expanded

Execution slices:

1. tolerance sweep engine and report schema: first deterministic Monte Carlo
   report and CSV implemented through `Actions -> Tolerance Monte Carlo
   Report...` and `python -m KrakenOS.UI.validate_tolerance_monte_carlo`
2. nominal-vs-perturbed detector/MTF/wavefront comparison: first
   worst-sample comparison report/CSV implemented for total merit, tolerance
   variables, and operand value/residual/weighted deltas; first visual
   `TolCmp` analysis overlays implemented for nominal-vs-worst image-plane
   spot samples, geometric MTF curves, and piston/tilt-removed wavefront delta
   maps without mutating the editable table; active `TolCmp` spot/MTF/WFE data
   can be exported through `Actions -> Export Tolerance Overlay CSV...`
3. richer fabrication-property authoring workflows

## Recommended Execution Order

1. Prism/CAD scene-object workflow
2. Coherent detector and diffraction branch analysis
3. Oblique Gaussian propagation
4. Direct multi-source editing
5. Tolerance/manufacturing expansion

This order matches the main architectural goal: sequential optics should become
the easy special case of a stronger 3D scene editor, not the other way around.
It does not mean later workstreams must wait for every polish item in an
earlier workstream. The current history legitimately starts 7E tolerance after
7A-7C closure while finishing remaining 7D source-row editing ergonomics.

## Phase 7A: First Implementation Slice

Status: `Completed at current face-anchor/path-frame/virtual-plane validation scope`

The first slice is the least risky, highest-value improvement to the current
prism/CAD workflow:

1. keep the existing `Center Row->Ray` workflow
2. when the selected row is a file-backed optical CAD/STL solid and
   `OpticalSolidFaces` metadata exists, use the best assigned optical face as
   the snap anchor instead of the generic row origin
3. score candidate faces by optical function, 2D side assignment, facing
   direction against the picked ray, and proximity to the traced ray
4. keep ordinary sequential surface rows unchanged
5. add a regression validator for the snap-anchor selection logic

Why start here:

- it improves a real user pain point immediately
- it reuses today’s metadata instead of waiting for a full new scene-object UI
- it is directly on the path toward future anchor + roll + path-frame placement

Implemented so far:

1. `Center Row->Ray` now prefers a saved optical-face anchor for file-backed
   CAD/STL solids when face metadata exists.
2. The visual CAD/STL placement dialog now exposes `Anchor face`,
   `Roll constraint`, `Face -> +Z`, `Face -> -Z`, `Face -> Ray`,
   `Face <- Ray`, `Face -> Path`, `Face <- Path`, `Anchor X/Y`, and
   `Anchor On Row` controls.
3. `python -m KrakenOS.UI.validate_optical_solid_snap_to_ray` covers anchor
   selection against a traced ray.
4. `python -m KrakenOS.UI.validate_optical_solid_face_fit` covers the
   face-normal fit and side-label roll helper.
5. `python -m KrakenOS.UI.validate_optical_solid_path_fit` covers face-fit
   placement against a selected traced ray and the current Path-view frame.
6. `OpticalSolidFaces` can now carry a virtual internal beam-splitter plane for
   cube-style CAD. The face-role dialog can auto-build that diagonal from saved
   Left/Right/Up/Down labels and preview it in 3D.
7. `python -m KrakenOS.UI.validate_optical_solid_virtual_plane` covers the
   virtual cube-splitter plane builder and world transform.
8. Traced optical-solid hits can now be classified back onto saved assigned
   faces, and segment crossings can be checked against saved virtual internal
   planes.
9. `python -m KrakenOS.UI.validate_optical_solid_hit_sequence` covers a real
   prism hit sequence plus a synthetic cube virtual-plane crossing order.

Remaining post-7A work:

1. richer arbitrary-prism assembly helpers beyond the current row pose,
   assigned-face, snap-to-ray, path-frame, and virtual-plane workflows
2. higher-level multi-solid CAD placement wizards if vendor assemblies become
   common enough to justify them

## Validators

Phase 7 should add focused validators instead of relying only on manual UI
inspection. The first slice starts with:

- `python -m KrakenOS.UI.validate_optical_solid_snap_to_ray`
- `python -m KrakenOS.UI.validate_optical_solid_face_fit`
- `python -m KrakenOS.UI.validate_optical_solid_path_fit`
- `python -m KrakenOS.UI.validate_optical_solid_virtual_plane`
- `python -m KrakenOS.UI.validate_optical_solid_hit_sequence`
- `python -m KrakenOS.UI.validate_gaussian_branch_frames`
- `python -m KrakenOS.UI.validate_gaussian_branch_q`
- `python -m KrakenOS.UI.validate_gaussian_detector_recombination`

Future slices should add:

- diffraction propagation through branch-local field states beyond detector FFT
- arbitrary picked-point source-target contract checks if that UX is added

## Phase 7B: Coherent detector slice

Status: `Completed at current detector-plane scope`

Implemented so far:

1. Detector-bearing interferometer layouts can now let ``Interf`` reuse the
   detector-bin coherent accumulation path instead of always forcing the older
   path-average analytic fringe shortcut.
2. Promotion is automatic and conservative: sparse single-ray detector samples
   still fall back to the analytic diagnostic, while denser bundles switch to
   detector-bin coherent accumulation on the selected detector output port.
3. ``CohDet`` now exposes per-branch-code self terms and complementary branch
   pair interference terms on the same detector grid, so the displayed
   interferogram can be reconstructed from the same accumulated pixel data.
4. ``python -m KrakenOS.UI.validate_interferogram_detector_accumulation``
   covers Michelson and Mach-Zehnder promotion from analytic fallback to
   detector-bin coherent accumulation and verifies the displayed intensity
   matches the self-plus-pair decomposition.
5. The analysis toolbar now includes ``Diffr``. It computes a vector
   Fraunhofer/angular-spectrum FFT from the same branch-filtered coherent
   detector field used by ``CohDet``.
6. ``python -m KrakenOS.UI.validate_diffraction_detector`` covers Michelson and
   Mach-Zehnder diffraction-detector spectra and validates finite angular axes,
   positive intensity, source-ray coherent grouping, and unitary FFT power
   conservation.
7. ``python -m KrakenOS.UI.validate_detector_sampling_stability`` covers
   Michelson and Mach-Zehnder detector-bin stability across coherent and
   diffraction analyses. It verifies that detector bin changes do not change
   the traced sample set, source-ray coherence groups, branch-code set,
   incoherent power accounting, all-rays Jones-vector intensity, or FFT power
   conservation.

## Phase 7C: Oblique Gaussian propagation slice

Status: `Completed at detector-bin Gaussian-q scope`

Implemented so far:

1. Ray Inspector hit records now expose branch-local Gaussian frame columns:
   ``GB K`` is the local propagation axis, ``GB T`` is the tangential axis in
   the local plane of incidence, and ``GB S`` is the sagittal axis. The frame
   is right-handed, with ``T x S = K``.
2. The same frame fields are exported through Ray Inspector CSV and Trace Path
   Inspector CSV, so future branch-carried q propagation can consume the same
   traced-hit contract outside the UI.
3. ``python -m KrakenOS.UI.validate_gaussian_branch_frames`` covers the Galvo
   F-Theta Gaussian laser scanner, Beam Splitter Two Path Doublets, and
   Michelson Interferometer layouts. It verifies frame presence, orthonormality,
   right-handedness, sagittal plane-of-incidence alignment, propagation-axis
   agreement with outgoing branch direction, and folded-path direction changes.
4. ``KrakenOS.propagate_branch_gaussian_q`` now propagates independent
   tangential/sagittal Gaussian q states through Ray Inspector / Trace Path hit
   records. It handles branch-local free-space path length, flat splitter and
   mirror folds, planar index changes, and conservative first-order spherical
   surface power when the trace and row data are sufficient.
5. ``python -m KrakenOS.UI.validate_gaussian_branch_q`` covers the Galvo
   F-Theta Gaussian laser scanner, Beam Splitter Two Path Doublets, and
   Michelson Interferometer layouts. It verifies finite/stable final branch q
   states, exact flat-path ``q + distance`` propagation where applicable,
   deterministic branch-path separation, and independent tangential/sagittal q
   evolution.
6. ``KrakenOS/Examples/Examp_Branch_Gaussian_Q_Propagation.py`` demonstrates
   consuming traced Michelson branch records and printing final q/radius values
   for each deterministic branch path.
7. Branch q steps now include a centered Gaussian aperture/obscuration loss
   estimate from row ``Diameter`` and ``InDiameter``. Each hit carries
   ``clip_transmission``, ``clip_loss``, ``cumulative_clip_transmission``, and
   ``cumulative_clip_loss`` so downstream detector propagation can include
   branch-local Gaussian throughput.
8. Detector-bin coherent accumulation can now apply branch-carried Gaussian q
   envelope weights plus cumulative clipping. ``Interf`` enables this
   automatically for ``Gaussian beam`` sources once detector-bin promotion is
   reliable, so Michelson/Mach-Zehnder detector pixels use branch q, branch
   phase, Jones/polarization vectors, and detector-bin self/pair recombination
   together.
9. ``python -m KrakenOS.UI.validate_gaussian_detector_recombination`` covers
   Michelson and Mach-Zehnder Gaussian-source recombination. It verifies finite
   non-uniform Gaussian detector weights, bounded clipping terms, detector
   power accounting, self-plus-pair reconstruction, and automatic ``Interf``
   promotion to Gaussian-q detector recombination.

Remaining post-7C work:

1. higher-order mode/FFT field propagation beyond the current detector-bin
   Gaussian-q envelope model
2. full oblique astigmatic surface matrices and mode-overlap validation for
   tilted plates, thick beam-splitter cubes, and arbitrary non-sequential CAD

## Phase 7D: Direct multi-source scene editing slice

Status: `Completed at current source-row action and placement-helper scope`

Implemented so far:

1. Scene Source Manager handles add/edit/delete/duplicate workflows for
   explicit `SceneSource3D` records without turning sources into KrakenOS
   `surf` rows.
2. Source rows are visible in the editable table through the source-aware
   scene-row mapping layer.
3. Source rows have direct right-click duplicate, delete, move up, and move
   down actions.
4. Source/object/CAD placement helpers can aim a source at Object, Image,
   surface, file-backed CAD/STL row centers, or assigned CAD/STL optical-face
   anchors.
5. Source-origin standoff placement moves the source upstream from the selected
   target along the current source direction.
6. Source Illumination Report and `Illum` source maps report source-specific
   hit power, missed power, vignetting, centroid, RMS radius, span, terminal
   loss breakdown, and CSV data.
7. `python -m KrakenOS.UI.validate_scene_source_row_contract` covers the
   source-row action contract.

Remaining post-7D work:

1. a compact inline source-edit dialog directly from source rows, if the
   manager feels too heavy for common edits
2. arbitrary picked-point source targets beyond row centers and assigned
   CAD/STL face anchors

## Phase 7E: Manufacturing and tolerance slice

Status: `In progress; deterministic Monte Carlo, compensator solve, saved preset, and overlay workflows implemented`

Implemented so far:

1. `Actions -> Tolerance Monte Carlo Report...` samples marked
   optimization/native variables as tolerance variables, evaluates merit
   operands, preserves the nominal editable table, and exports the report/CSV
   schema.
2. Worst-sample comparison reports total merit, tolerance variable deltas, and
   operand value/residual/weighted deltas.
3. `Actions -> Tolerance Compensator Sweep...` holds the system at the worst
   valid sample, sweeps each marked tolerance variable across its bounds as a
   possible compensator, reports the best merit recovery, and exports the merit
   curve through `Actions -> Export Tolerance Compensator CSV...`.
4. `Actions -> Tolerance Multi-Compensator Solve...` repeats bounded
   one-variable sweeps as a deterministic coordinate solve, accepting only
   merit-improving updates across multiple compensators and exporting the
   coordinate trace through `Actions -> Export Tolerance Multi-Compensator
   CSV...`.
5. Marked tolerance variables can now be made tolerance-only or compensator
   eligible from the cell right-click `Optimization / Solves` menu. Eligibility
   persists as row advanced `ToleranceCompensators` metadata; no metadata keeps
   the backward-compatible behavior where every marked variable is a
   compensator.
6. `TolCmp` spot overlay compares nominal and worst-sample image-plane spots.
7. `TolCmp` MTF overlay compares nominal and worst-sample geometric MTF curves.
8. `TolCmp` WFE overlay compares piston/tilt-removed nominal-vs-worst
   wavefront delta maps.
9. `Actions -> Export Tolerance Overlay CSV...` exports the active spot, MTF,
   or WFE overlay data.
10. `Actions -> Save Tolerance Solve Preset...` and `Actions -> Apply
   Tolerance Solve Preset...` persist and restore Monte Carlo defaults, solve
   steps/passes, selected merit operands, `TolCmp` view, and
   tolerance-only/compensator roles without tracing.
11. `KrakenOS/Examples/Examp_Tolerance_Compensator_Sweep.py` demonstrates the
   programmatic Monte Carlo, saved preset, compensator sweep, and
   multi-compensator solve flow.
12. `python -m KrakenOS.UI.validate_tolerance_monte_carlo` covers deterministic
   sampling, report schema, nominal-table preservation, worst-sample
   comparison, compensator eligibility, saved solve preset round-trip,
   compensator sweep/solve, spot/MTF/WFE overlays, and CSV schemas.

Remaining post-7E work:

1. production-grade tolerance stack-up dashboards
2. richer coupled variable constraints and manufacturing metadata
3. optional visual tolerance dashboards once the sweep model stabilizes
