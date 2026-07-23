# 0431 — BS Phase 2: trace-driven placement (predecessor legs from the branched trace)

**Follows** bugs/0428 + bugs/0430 (Phase 1: the BS reflect axis is drawn, fold-aware). Phase 2 answers
the user's requirements 5 + 6 on `machine_vision_AZ85_RA_Mirror.py`: *replace the temporary first RA
mirror with the BS plate → the imaging lens + camera retain their placement, and every element follows
the component immediately before it (camera follows the 2nd RA mirror), the BS never re-aims the camera.*

The user chose the **trace-driven (physics-native)** approach: placement follows the branch leg the traced
rays actually put each element on — "display follows physics", the BRANCH_README North Star.

## Reproduction (headless, `bugs/probe_0431_predecessor_placement.py`)

Topology: Object(0) → RA-mirror-1(1,2) → lens group(3–7) → RA-mirror-2(8) → Image(9).

| scene | overrides | result |
|---|---|---|
| with RA-mirror-1 | 8 (chain folded onto +X) | correct |
| RA-mirror-1 removed (both surfaces) | **0** | lens + camera collapse to the straight axis |

Root: RA-mirror-2 is **free-placed off-beam at x≈236** (`free_placed_pinned=True`); with mirror-1 gone the
straight object beam misses it, so nothing folds the beam to the chain. The elements only made sense as
followers of mirror-1's fold. A purely *geometric* "are the followers on the reflect leg?" test fails
because removal reverts their positions to the straight stations — the leg membership has to come from the
**trace**, not from reverted positions.

## What the trace gives us (`bugs/probe_0431_branch_surface_map.py`)

A promoted BS makes `__NsTraceRequiresBranching()` true, so `NsTrace` populates `NS_BRANCH_RESULTS`: a list
of per-branch snapshots, each a full ray record with `SURFACE` (row indices hit, in order), `XYZ` (world
points), `R_LMN` (directions), `branch_path` (`S9:S9/transmit`, `S9:S9/reflect`), `branch_power`.

On AZ85 + BS (BS added near the object, row 9):
- branch 1 `S9/transmit`, power 0.467 → surfaces `[9,1,2,3,4,5,6,7,8,10]` — the whole folded imaging chain
  (its `XYZ` already encodes both mirror folds).
- branch 2 `S9/reflect`, power 0.473 → surfaces `[9]` — reflects into empty space.

So **per-element leg membership = which branch's `SURFACE` contains the row**, and each leg's world frame
comes from that branch's `XYZ`/`R_LMN` at the surface. When the user re-aims the BS + removes mirror-1, the
reflect branch will instead carry `[9, lens, mirror2, camera]` and placement follows it — no leg flag,
no re-aim of the camera by the BS (the camera follows its predecessor along whatever branch reaches it).

## Design

The existing `_trace_row_exit_frame` (`nonseq_output_ports.py:959`) **bails when `NS_BRANCH_RESULTS` is
non-empty** (line 981) — it only handles the single-path trace. Phase 2 makes placement branch-aware:

1. **`_branch_traced_row_frames(system, rows)`** (new, pure) — trace once; for every row hit by a branch,
   return `{row_index: {branch_id, branch_path, center, rotation, hit_order}}` computed from that branch's
   `XYZ`/`R_LMN` (reuse `_frame_rotation_from_normal`, and `_downstream_pose_from_frame` for the row's own
   local tilt/desp about the traced leg frame). A row hit by several branches keeps the highest-power one.
2. **`build_optical_solid_output_port_pose_overrides`** — when branches exist AND a system is supplied, take
   each follower's pose from `_branch_traced_row_frames` instead of the geometric fold-walk. **Gated on
   `NS_BRANCH_RESULTS` non-empty**, so every non-BS scene (0 branches) keeps the existing fold-walk exactly
   — all encoded penta behaviours (0022, 0084-0091, 0185, 0212-0224, mirror cascades …) are untouched.

### Validation strategy (headless)

Trace-driven placement must **reproduce the geometric fold-walk** for the transmit-leg chain (both describe
the same folded geometry). So the headless test asserts: on AZ85 + BS, the trace-driven follower centers for
rows 1-8,10 match the fold-walk centers (within tolerance). The reflect-leg-carries-the-chain case (re-aimed
BS + mirror-1 removed) is an in-app operation (gizmo) → owe an eyeball.

## Slices

- **2a — SHIPPED.** `_exit_frame_from_trace_arrays` (factored single-path read, no behaviour change) +
  `_branch_traced_row_frames(system, rows)` (new, additive) — one branched `NsTrace`, per-branch
  `SURFACE`/`XYZ`/`R_LMN` → `{row_index: {branch_id, branch_path, branch_power, center, rotation}}`,
  highest-power branch per row, `{}` when the trace doesn't branch. `_trace_row_exit_frame`'s branch-bail is
  left intact, so every non-BS scene keeps the existing walk. Guard `validate_open3d_bs_trace_driven_placement`
  (penta phase 347): NO-BS-EMPTY + REFACTOR-SAFE + BRANCH-COVERAGE, verified on the real AZ85 scene (no BS →
  `{}`; +BS → 10 imaging-chain rows covered via the traced branch). Neighbouring BS/multifold phases still pass.
- **2b — next.** Wire `_branch_traced_row_frames` into `build_optical_solid_output_port_pose_overrides`, gated
  on branches: at a BS whose REFLECT branch carries followers, fold them onto the reflect frame (reuse the
  existing mirror machinery for the pose; the trace makes only the fold-vs-skip DECISION). Parity check: the
  transmit-leg placement must match the current fold-walk on AZ85+BS (invisible there → safe).
- **2c — after 2b.** Convergence across mirror removal / re-aim (seed the settle-loop from the last-applied
  folded positions so the reflect branch keeps carrying the chain) → retain placement. In-app eyeball
  (folded VTK, headless-untestable).

## Files

- `KrakenOS/UI/nonseq_output_ports.py` — `_branch_traced_row_frames` (2a); branch-gated placement (2b).
- `bugs/probe_0431_predecessor_placement.py`, `bugs/probe_0431_branch_surface_map.py` — diagnostics.
- `KrakenOS/UI/validate_open3d_bs_trace_driven_placement.py` — guard (penta phase, 2a).
