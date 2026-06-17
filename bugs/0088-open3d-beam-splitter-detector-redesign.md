# 0088 — Open 3D: beam-splitter detector redesign (hard-stop detectors + per-branch detectors)

## Request (user, 2026-06-17)

Triggered by `flag_20260617_215355_478` (machine-vision 150mm): a promoted coated
beam splitter splits, but selecting a Camera placed ONE detector on the
sequential/transmit focus and ignored the reflected arm — so the reflected rays
escaped to the display radius and diverged forever. The user asked to redesign
detectors:

- Place a detector on **every** beam-splitter exit arm (transmit + reflect),
  generalized to **cascading** splitters.
- A detector is a **hard stop**: no ray drawn past it (incl. missed rays) unless
  the existing **Miss** toggle is on.
- Detectors are **generic** planes (camera assignment + per-branch solve come
  later), **auto-positioned at the arm focus**.
- An **absorbing output face** collapses that branch → no detector there.

## Phase A — global hard-stop ray display (commit `bb145a2f`)

Display-only. `scene_projector.bounded_ray_points_for_scene_display` gained
`detector_planes` + `_clip_polyline_at_detector_planes`; the drawn ray (2D
`_project_rays` and 3D `open3d_scene_refresh` via `_bounded_3d_ray_points_for_display`
/ `_detector_planes_for_hard_stop`) is truncated at the first detector/Image
plane it crosses within the detector's radial limit. `detector_planes_for_hard_stop`
derives the planes from the bundle's `is_detector` targets. No-op when there are
no detector planes. Guard `validate_open3d_detector_hard_stop_clip`, penta Phase 81.

## Phase B1 — branch detector entity (this commit)

`KrakenOS/UI/services/branch_detectors.py`: a first-class **display** entity,
`BranchDetector`, derived per **terminal leaf branch** of the traced ray tree:
- `derive_branch_detectors(ray_paths, …)` groups paths by `branch_path`, finds
  **leaves** by component-prefix (split on `" -> "`; `"primary"` = empty root) so a
  branch that is a proper prefix of another (an intermediate arm feeding the next
  splitter) is **never** a detector — **cascading-correct** for N chained
  splitters. A leaf that already reaches the Image (the transmit/sequential path)
  is skipped. **Absorbing** falls out free: an absorbed output face yields no exit
  rays → no leaf → no detector.
- **Focus** per leaf = the least-squares closest-approach point of that branch's
  exit rays (the converging waist); collimated/ill-conditioned bundles fall back
  to a visible default distance along the branch.
- Each becomes an `is_detector` `SceneTarget3D` appended to the bundle targets
  (`build_scene_bundle`, after `ray_paths`) so it **displays** (a `SurfaceCurve3D`
  rectangle) and **feeds Phase A's hard-stop** (reflect/leaf rays terminate at it).
  The sequential Image detector is untouched (not duplicated). Only genuine
  SPLITS create branches, so sequential/folded (penta/mirror) scenes get none.

Guard `validate_open3d_beam_splitter_branch_detectors` (display-free: single BS →
1 reflect detector at the converging focus; cascading → detector per terminal leaf
only, intermediate pruned; absorbing → none; no-splitter → none; derived detector
appears in the hard-stop planes). Penta **Phase 82**; baseline → 83. Regressions
`beam_splitter_transmit_and_second_axis`, `traced_rays_always_visible` (incl. the
real machine-vision cube), `clipped_vignetting_parity` still pass.

## Deferred (next)

- **B2:** right-click "register STEP camera" per detector (decorative overlay) +
  per-detector camera assignment. `BranchDetector.assigned_camera_label` slot is
  reserved (left None).
- **B3 / C:** per-branch quick-estimation / quick-solve / optimization + spot-RMS
  auto-solve refinement of the focus. `branch_path` is carried so a per-branch
  solve can target the branch's rays.

## In-app confirmation

PENDING — ray-display + branch-detector visuals can't be render-verified headlessly
(VTK SIGSEGVs on llvmpipe). Confirm in-app: rays stop at detectors; the reflected
arm now shows a detector at its focus and the beam terminates there.

## Status: Phase A SHIPPED; Phase B1 SHIPPED; B2/B3 deferred
