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

## Note for whoever re-pins om05a

Phase 505's A8b compares the live cover strip against constants measured BEFORE bugs/0760. Once the
two big RA mirrors are re-pinned and the scene re-saved after a trace, those constants are the ones
to re-derive -- the strips move with the mirrors, by the same 3.563 mm.
