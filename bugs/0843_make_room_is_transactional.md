# 0843 -- making room at the fold and USING it are one transaction

> *"device size changed to 50x50x1, solver rejected. I think this is not correct, contradict to
> actual production."*

This is **not yet** the fix for that refusal. It is the fix for what happens the moment that
refusal is unblocked -- found by unblocking it, and severe enough that it has to ship first.

## What was measured

On `attachment/om05a_folded_refusal.py` the lens's leg is mis-classified as the root axis (the
real root cause, next bug). With that corrected in a scratch tree, the bugs/0573 make-room
rescue became reachable for the first time on this scene, and did this:

    1. first lens move refused      room 74.47 mm, shortfall recorded
    2. slide_fold_arm_along_leg     mirror + everything behind it + the camera  +197.138 mm
    3. retry the lens move          REFUSED again (a different body was now in the way)
    4. return the refusal           ... and leave step 2 in the scene

    gap row 12        79.681  ->  276.819 mm
    |m|               1.3601  ->  None  (no finite magnification left)
    message           "FOV out of range on this fold ... nothing was moved."

**The message said nothing was moved while the fold arm sat 197 mm from where it was.** The
rescue slid the machine to make room for a move that then never happened, and nothing took the
slide back. A refusal that alters the scene is worse than the refusal.

`slide_fold_arm_along_leg` cannot be un-done by sliding back: `79.681 + 197.138 - 197.138` is
`79.68100000000001`, and the camera carry runs through a setter that pops the camera's axis
anchor on the way. An inverse slide is a second edit, not a restore.

## The fix: a savepoint, not an inverse

`KrakenOS/UI/services/geometry_transaction.py` -- `GeometryTransaction(editor, label, also=())`.

    begin     snapshot the RAW objects: every row's thickness / desp / tilt / axis_move, every
              STEP placement offset (or "absent"), the axis-anchor table, plus `also` attributes
    commit    keep the work
    rollback  restore ONLY what differs (compared by repr, so -0.0, an int thickness and a None
              desp come back as themselves), route changed offsets through the real setter so
              its cache invalidation runs, rebind the exact captured object, restore the anchor
              table LAST, re-dirty the trace only if something was actually restored

If the row list changed identity since `begin`, rollback writes **nothing** and reports `stuck`
-- restoring onto rows that are not the captured ones would be a guess.

Wired in three places:

| where | what it protects |
|---|---|
| the bugs/0573 rescue in `_apply_conjugate_pair` | arm slide + retry commit together or not at all |
| `_refused_booking_moves_nothing` around the whole booking | any refusal path, present or future: `(False, msg)` or an exception leaves the scene byte-identical |
| the swap make-room in `layout_table_workbench` | exception-atomicity only (a swap keeps its slide on a normal return) |

## The explanation has to survive the put-back

The retry wipes the refusal channel on entry and re-measures it on the SLID scene. After the
put-back those numbers describe a scene that no longer exists (275.1 mm of room -- on a machine
197 mm longer than the one on screen). So the first attempt's channel is captured before the
rescue and restored after it, and the reason says what was tried:

    ... only 74.47 mm of physical room is left before its body reaches Filter 48-926. Making
    room was tried first -- the fold mirror and the camera +57.92 mm along the leg -- and the
    lens move was still refused (only 275.1 mm is left before RA mirror 2). The arm was put
    back -- nothing was moved.

The refusal stash carries `make_room_tried_mm` and `make_room_put_back` as values. When the
put-back is impossible (`stuck`) the message says so and points at Undo, instead of implying
nothing moved.

## Guard

`validate_open3d_0843_make_room_is_transactional.py`, display-free, penta phase 622. It binds
the REAL `slide_fold_arm_along_leg` and the REAL placement-offset setter onto a probe.

- **P** an inverse slide is not bit-exact here -- so the byte-identity checks cannot be met by
  sliding back
- **Z** CONTROL: without a transaction the real slide strands the scene (79.681 -> 276.819,
  anchor popped) -- the fixture reproduces the bug
- **T1-T7** the slide really happened mid-way; byte-identical after; same tuple object; anchor
  back; state + restored count; the rebuild flag is CONSUMED mid-slide and must be set again;
  the real setter ran twice
- **X / C / R / S / N** exception path; commit keeps the work; raw values; stuck writes nothing;
  a no-op put-back writes nothing, logs nothing
- **D** the booking-wide net: refuse / ok / raise / stuck, including the `also=` lens-move claim
- **E** the restated refusal: first numbers back, structured facts, ordering, untouched when the
  arm never moved
- **W** the REAL `_apply_conjugate_pair` with the real slide and a scripted refusing lens move,
  driven **unwrapped and wrapped**. Unwrapped matters: the booking-wide net would otherwise mask
  a rescue that stopped using its own savepoint. **W0** neuters only that savepoint and shows
  the unwrapped booking then strands the scene, so W2 is not vacuous.

An adversarial review (14 read-only agents) found 0 revert-completeness defects and 8
guard-quality defects, all fixed here -- among them a T6 whose first conjunct was always true
(the slide itself sets the flag), an `invalidated` list that was recorded and never read, and
zero coverage of `also=`.

Existing guards re-run: 0573 (including the real Apo75 make-room SUCCESS path -- the arm slide
still commits when the retry succeeds), 0594, 0626.

## Still open

The 50 x 50 refusal itself. `optical_axis_tree.row_world_pose` returns station + desp (the
straight frame) while the fold emissions are in WORLD, so the lens rows on om05a snap to
`axis:root` instead of `axis:fold:7`, `_lens_leg_slide_plan()[2]` is False, and
`slide_fold_arm_along_leg` returns None at its first line. Build order: (1) this, (2) the
axis-tree frame, (3) the travel range + rebalance so any field inside the deliverable range
(7.4 ... 69.1 mm on om05a) is solved rather than refused.
