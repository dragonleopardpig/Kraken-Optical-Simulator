# 0817 -- a seat that moved on purpose can be re-recorded

The third of the three things bugs/0815 turned up. bugs/0816 made an accidental slide announce
itself; this is the other half -- a move that was deliberate and correct, which the scene had no way
to accept.

## The stuck snapshot

`StepOverlayPromotion.center_world` is written once, at promotion. bugs/0760 measured the clearance
on the production assembly `om05a_26_1_r03_2s_lr_asm.stp` -- its one 50 mm RA-mirror solid stands
**7.596 mm** clear of the part above it, against **4.033 mm** in the scene -- and moved the mirror
3.563 mm onto it, in both scenes, with |m| agreeing to seven figures before and after. The row has
sat at the vendor's clearance ever since, and the snapshot it carries still says where it used to be.

Nothing could refresh it, so everything anchored on it stayed 3.563 mm behind:

* the bugs/0750 audit reads 3.563 mm of "drift" on a row that is exactly where it belongs;
* phase 505's A8b reports the same 3.563 mm on the measured cover strip (the authored strips were
  measured before the move);
* bugs/0816's notice has to special-case nothing, but only because its DELTA form ignores a stale
  snapshot -- the absolute reading is unusable on this scene.

## Fix -- the user records it, the app never does

`ScenePlacementMixin.pin_row_placement_as_authored(row_index)`:

* refuses a row with no promotion snapshot, no walked pose, an index outside the scene, or one
  already on its seat -- each with a reason, writing nothing;
* otherwise records the LIVE pose as `center_world`, keeps the old one as
  `center_world_repinned_from` so the change stays auditable in the saved scene, captures history
  (undoable) and syncs the table (bugs/0815);
* **moves nothing**: thickness, decentres, tilts and the live pose are untouched. That is the whole
  point on vendor hardware ([[vendor hardware is immutable]]) -- the row is where the user put it and
  the scene now says so.

`Open3DFaceAssignmentService`:

* `_append_placement_seat_action` adds **"Pin Current Placement as Authored (3.563 mm off)..."** to a
  promoted row's right-click -- the 3D canvas AND the Scene Components tree, since both go through
  `append_element_context_actions` -- and only when the row is actually off its seat, because an
  entry that is always there invites a click that does nothing;
* `_pin_row_placement_from_context` shows both poses, asks, and on yes applies through the editor and
  redraws through `_apply_model_change` (which then sees the drift go DOWN, so bugs/0816 says
  nothing -- it only reports growth).

## Measured

On the user's scene, row 7 "RA mirror 1 (50 mm)":

| | before | after |
|---|---|---|
| drift from the authored placement | 3.563 mm | **0.000000 mm** |
| thickness / desp / tilt | 180.470, (0, 52.8, -119.93), tilt_z -90 | unchanged |
| live pose | (0, 56.363, -25) | unchanged |
| `center_world_repinned_from` | -- | [0.0, 52.8, -25.0] |

A second re-pin of the same row declines: "already sits on its authored placement (0.000000 mm)".

## Guard

`validate_open3d_0817_a_seat_that_moved_can_be_re_recorded` (penta phase 596):

* A (live, SKIP without the Filen-synced scene): the drift goes 3.563 -> 0.000000, nothing moved,
  the old placement is kept, a second re-pin declines;
* B: the three refusals on a fake editor, and a declined re-pin writes nothing;
* C: the verb appears on a drifted row with the amount in its label and not at all on a seated one;
  the command confirms, applies through the editor and redraws through the chokepoint; both
  promoted-row branches of the element menu offer it.

## Done on the user's scene (2026-09-18, at their request)

Both big RA mirrors re-pinned headlessly, backup `attachment/om05a_folded.pre0817_repin_backup.py`:

| row | drift before | after | geometry |
|---|---|---|---|
| 7 RA mirror 1 (50 mm) | 3.5630 | **0.000000** | unchanged |
| 15 RA mirror 2 (40 mm) | 5.0388 | **0.000000** | unchanged |

Every promoted row in the scene now reads 0.000 -- the first time the whole thing sits on its
recorded placement -- and the old values stay as `center_world_repinned_from` ([0.0, 52.8, -25.0]
and [-272.7, 52.75, -25.0]). No row field moved: thickness, decentres and tilts are identical to the
backup.

**Phase 505 is green.** Two of its checks were reading the pre-bugs/0760 snapshot:

* **A2** asserted mirror 2's "part-anchored CAD pose" as (-272.7, 52.75, -25) -- the place it sat
  before 0760 put it on the vendor clearance. It passed only because the stale snapshot agreed with
  it; the LIVE pose never did. Re-derived to (-269.137, 56.313, -25).
* **A8b** compared the live cover strip against constants measured before the same move, missing by
  exactly 3.563 mm and nothing else. Re-derived to centre (-269.087, 1.822), half-width 10.311, and
  the two arms mirrored in v.

The strips' v-RANGE is deliberately not pinned. A trace re-measures the strip from the LIVE launch,
which samples one field row in v, so it reports a 0.047 mm slice rather than the strip's height; the
authored 3.0 mm comes from bugs/0692's dedicated field sweep. That sweep was re-run on the re-pinned
scene (arm A lands z -29.88 .. -19.83, arm B -30.17 .. -20.12, sensor x ~ -269.1, object x +-30 ->
sensor x -281.45 .. -256.74), and the authored bands were restored into the scene afterwards so the
saved strips keep their measured height instead of the live slice.

## Note for whoever re-pins om05a

Phase 505's A8b compares the live cover strip against constants measured BEFORE bugs/0760. Once the
two big RA mirrors are re-pinned and the scene re-saved after a trace, those constants are the ones
to re-derive -- the strips move with the mirrors, by the same 3.563 mm.
