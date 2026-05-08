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
- face-role assignment does not yet solve full placement intent by itself
- users still need a better anchor, path, and roll workflow to place a prism on
  the correct beam

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

Remaining gap:

- direct source-row editing is still lighter than surface editing
- source/object placement against imported mechanical CAD is still manual

Execution slices:

1. direct source-row editing dialog/workbench
2. source-to-object and source-to-CAD placement helpers
3. mixed illumination/imaging scene templates
4. tighter source-path diagnostics for vignetting and uniformity

### E. Manufacturing and tolerance workflow

Current state:

- error maps, optimization variables, ISO-style PDF export metadata, and reports
  are available

Remaining gap:

- full tolerance sweeps are deferred
- coupled variables/constraints are still limited
- nominal-vs-perturbed overlays need a stronger workflow

Execution slices:

1. tolerance sweep engine and report schema
2. nominal-vs-perturbed detector/MTF/wavefront comparison
3. richer fabrication-property authoring workflows

## Recommended Execution Order

1. Prism/CAD scene-object workflow
2. Coherent detector and diffraction branch analysis
3. Oblique Gaussian propagation
4. Direct multi-source editing
5. Tolerance/manufacturing expansion

This order matches the main architectural goal: sequential optics should become
the easy special case of a stronger 3D scene editor, not the other way around.

## Phase 7A: First Implementation Slice

Status: `In progress`

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

## Validators

Phase 7 should add focused validators instead of relying only on manual UI
inspection. The first slice starts with:

- `python -m KrakenOS.UI.validate_optical_solid_snap_to_ray`
- `python -m KrakenOS.UI.validate_optical_solid_face_fit`
- `python -m KrakenOS.UI.validate_optical_solid_path_fit`
- `python -m KrakenOS.UI.validate_optical_solid_virtual_plane`

Future slices should add:

- prism pose/entry/exit role validation
- coherent detector regression beyond analytic fringe plots
- branch-local Gaussian propagation checks
- multi-source scene editing contract checks
