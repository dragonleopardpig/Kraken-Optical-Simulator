# 0236 — Two-fold folded solve throws the trailing mirror off-axis; carry it onto the beam

## Symptom
flag_20260706_083512_730, on the promoted two-fold AZ85 periscope:

- "Why 2-fold periscope can't specify object segment constraint? Where is the a+b=c request earlier?"
  — the object-distance (a+b=c) split section was **gated off** on a two-fold (bugs/0234).
- "I click the solve thickness, 2nd RA mirror seems thrown out of the optical axis." — running
  *Solve for Thickness* slid the beam but left the drawn 2nd (trailing) mirror pinned off the axis.

Both are the same underlying defect that bugs/0234 gated around instead of fixing: an upstream gap
change on a two-fold does not carry the free-placed trailing fold mirror with the beam.

## Root cause
The trailing mirror is a **free-placed** promoted solid (bugs/0213/0218): it is pinned by
`_free_placed_solid_pinned_pose` at `center = [desp_x, desp_y, z_station + desp_z]`, where
`z_station = row_z_positions[i] = Σ thickness[0..i-1]`. Its station advance therefore feeds **only
global +Z**.

A folded conjugate solve changes a gap on a leg **after** the first fold:

- *Solve for Thickness* (`_apply_conjugate_pair` → `_folded_conjugate_gaps_for_magnification`) writes
  the object gap (row 0, pre-fold) **and** the image gap (row `gap_start`, post-fold).
- the object-split (`_apply_folded_object_split`) trades the object gap against the trailing air
  spacer (post-fold).

The post-fold gap delta walks the beam along the **first fold's reflected direction** r̂ (=+X on this
fixture), not +Z. So the pinned mirror advanced in +Z while the beam walked r̂ → the mirror was left
`|delta|·√2` off the beam ("2nd RA mirror thrown out of the optical axis"). The detector, a plain
follower, re-derives from the folded-axis walk and already tracked the beam correctly; only the
free-placed mirror was stranded. bugs/0234 gated the object split OFF on a two-fold for exactly this,
and warned the folded *Solve for Thickness* would desync the same way.

## Fix
`carry_free_placed_followers_after_fold(rows, gap_deltas)` (`nonseq_output_ports`) runs after a folded
solve writes its gaps. It finds the first fold, forms r̂ = reflect(ẑ, mirror1_world_normal), and for
each free-placed follower **downstream of the first fold** adds

    post_fold_delta · (r̂ − ẑ)

to its desp, where `post_fold_delta` is the sum of applied gap deltas strictly between the first fold
and that follower. This redirects the post-fold portion of the walk off global +Z and onto the
reflected leg r̂, re-seating the mirror on the beam. A **pre-fold** delta (row 0, before the first
fold) is not summed into `post_fold_delta`, so it correctly stays a global-+Z fold-vertex slide; a
plain (non-free-placed) follower is never touched; and if the reflected leg is still +Z (no real
fold) the carry is a no-op.

Wired into both solve paths:

- `_apply_conjugate_pair` (quick_estimation) — `[(obj_gap_row, object_delta), (img_gap_row, image_delta)]`.
- `_apply_folded_object_split` (paraxial_tools) — `[(near_gap_row, delta), (far_gap_row, -delta)]`.

The bugs/0234 two-fold gate (`if any(int(f) > int(mirror_row) for f in folds): return None` in
`_folded_object_conjugate_split`) is removed, so the object-segment split is now offered on a
two-fold, and the obsolete "fold-mirror repositioning unavailable on a two-fold" dialog note is gone.

## Verification
`KrakenOS/UI/validate_open3d_two_fold_image_arm_follow.py` (penta phase 213), measured headless via
`build_optical_solid_output_port_pose_overrides` (drawn-pose centres without VTK):

- **THICKNESS ON BEAM** — the folded `_apply_conjugate_pair(30, 21)` moves the trailing mirror
  (Δ≈78 mm) but preserves its axial offset from the lens arm (`-1.2987 → -1.2987`), i.e. it stays on
  the beam instead of frozen off-axis.
- **SPLIT UN-GATED + ON BEAM** — `_folded_object_conjugate_split()` is now non-None on the two-fold,
  and `_apply_folded_object_split("near", near+15)` carries the mirror (Δ≈21 mm) with the same beam
  offset preserved (`-1.2987 → -1.2987`).
- **PRE-FOLD NO-OP** — a delta on row 0 (before the first fold) carries nothing; a plain air-gap
  follower is never moved.
- **WIRED** — the carry is called from both solve paths, defined in `nonseq_output_ports`, and the
  bugs/0234 gate string is gone from `paraxial_tools`.

**Supersedes bugs/0234** (its gate + dialog note are removed; penta phase 211 retired with its guard).
Single-fold coverage is unchanged and still guarded by `validate_open3d_folded_conjugate_split.py`
(phase 207) and `validate_open3d_folded_fov_solve.py` (phase 209). Overlays/3D are a VTK render and
can't be pixel-validated headless (llvmpipe SIGSEGV); this guard checks the geometry the renderer
consumes. In-app visual confirm owed (restart the app onto this build).
