# 0518 — detector redesign B3 (first piece): Quick Estimation answers PER ARM

## The gap

`quick_estimation.py` was single-chain: every quantity (focal length, magnification, FOV,
sensor) was read against THE terminal Image row and THE whole-row chain. On a tagged two-arm
splitter scene (per-arm lenses and sensors — e.g. `beam_splitter_dual_mv_150_120`, transmit =
MV150, reflect = MV120 folded +Y) the panel answered for one arm at best; the two-arm
magnification fallback in `_current_finite_paraxial_magnification` even documents itself as
"a representative value" (the first fold arm's). This was task #9 of the B2/B3 list: "wire QE
per branch detector using that arm's `_branch_leaf_rows` lens + the detector sensor →
per-arm FOV."

## Fix

- `_shared_first_order_reference` (0297) refactored into rows-parameterized
  `_first_order_reference_for_rows(rows, *, unfold_branch_tilts=False)` — the whole-layout
  call is byte-identical; a per-arm call passes one tagged arm's chain with
  `unfold_branch_tilts=True` (the folded arm's tilts are placement, not prescription — the
  same rule as the per-leaf pupil, DESIGN §5b).
- New `QuickEstimationService.branch_states()`: for each `_scene_branch_selectors` arm,
  extract `_branch_leaf_rows`, read that arm's own first order and derive f / working
  distance / conjugate magnification (`m = f/(s_o − f)`, the 0222 convention) / per-arm
  sensor semi (the arm's terminal detector row) / object FOV. `{}` on non-tagged scenes.
- `format_readout` gains a `branches` key (one compact line per arm); the Quick Estimation
  panel gains a "Per-arm" row. Untagged scenes show "--" and keep every other line untouched.

## Remaining B3/C

Per-branch SOLVE (target a chosen branch's detector in fov_solve / conjugate solve /
optimization) and the spot-RMS focus refinement stay open; this piece is the read-side.

## Guard

`validate_open3d_0518_per_branch_quick_estimation.py` (penta phase 417): SOURCE wiring; REAL
— on the dual scene both arms report their OWN first order with distinct focal lengths and a
per-arm FOV; NEG — the untagged 50/50 scene keeps the single-chain readout.
