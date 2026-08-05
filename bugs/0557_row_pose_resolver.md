# 0557 — one resolver for "where is this row"

Step 2 of `docs/design_row_placement_space.md`, for the consumers that do **not** need the
folded-display frame.

## The class, not the instance

`SurfaceRow.desp_x/desp_y/desp_z` carries two incompatible meanings and nothing in the type says
which is in force:

* **SEQUENTIAL** — an offset from the row's station, the chain straight, the fold applied later.
* **WORLD** — an absolute placement, already final, baked by the 0433 freeze / axis snap / a
  promotion.

Five consumers inferred that privately, and every one of them got it wrong on a frozen scene:

| bug | consumer | symptom |
|---|---|---|
| 0517 | branch camera frame | camera framed on the straight axis |
| 0519 | FOV solve gate | gate read the wrong plane |
| 0525 | acceptance-cone crease | cone creased at the wrong place |
| 0547 | lens-swap block placement | the swapped block snapped to the global axis |
| 0556 | Normal-to-Sensor anchor | aimed 194 mm off the sensor → an **empty view** |

Each was patched in isolation, so the class survived every fix. The sixth was only ever a
question of which consumer would be asked to do it next.

## Fix

`row_placement.world_pose(editor, row_index)` and `world_frame(editor, row_index)` are the single
answer:

* a **WORLD** row's baked numbers *are* its world pose — returned as-is;
* a **SEQUENTIAL** row returns the straight-equivalent, and `Pose.space` says so, so a caller can
  never silently mistake one for the other;
* `world_frame` adds the row's own orientation matrix (normal = column 2, height = column 1) —
  keeping it beside the resolver is deliberate, since deriving a normal from tilts by hand is
  exactly how bugs/0556 came to hardcode `(0, 0, 1)` for a flipped sensor.

Re-pointed in this commit (one consumer per commit, as the design prescribes):

* `LayoutTableWorkbenchMixin._swap_frozen_block_frame` (bugs/0547)
* `ThreeDSceneToolsMixin._imaging_detector_row_anchor_target` (bugs/0556)

Both guards pass unchanged, so the re-point is behaviour-preserving.

## What this deliberately does NOT do

The display fold is **not** applied inside the resolver yet. That is the other half of Step 2 and
it is blocked on an unfinished investigation, recorded in the design doc:

1. `_compute_folded_layout_geometry_for_rows` was patched with option (a) — the audit came back
   **byte-identical**, so the edit was inert and that function is not the producer. Reverted.
2. `_build_folded_surface_curves` / `_build_sequential_surface_curves` — instrumented, **never
   called** for this scene.

So the producer of the drawn folded geometry is still unidentified, and `world_pose` says
`SEQUENTIAL` rather than pretending to fold. Honest boundary beats a plausible-looking patch: the
doc records three reverts from fixes written before a reproduction existed.

## Guard

`KrakenOS/UI/validate_open3d_0557_row_pose_resolver.py` (penta phase 439): a WORLD row resolves to
its baked placement and reports `WORLD`; a SEQUENTIAL row resolves to station + desp and reports
`SEQUENTIAL`; `world_frame` returns the row's own normal (not a bare `+Z`) and agrees with
`world_pose`; and both re-pointed consumers are asserted to call the resolver rather than
re-derive `station + desp`.

Non-vacuity: substituting an axial-assumption resolver fails it immediately with the 194 mm error
from the flagged empty view.

## Next

The remaining Step-2 work is to find the actual producer of the drawn folded geometry by
instrumenting candidates and measuring with `tools/pose_audit.py` (row 8's 51.50 mm going to zero
is the pass condition, ~2 minutes per attempt), then apply option (a) — an explicit
world → display frame map — at the site that genuinely runs.
