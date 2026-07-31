# 0487 — sliding a fold mirror left its whole arm behind (bugs/0485 rule 3)

The first of the user's four rules to be implemented on the bugs/0485 derivation:

> 3) If the user slide the elements that introduce a fold axis, then all the snapped elements
>    should follow the fold axis.

## Measured before

Dragging the RA mirror 20 mm along its incoming leg on
`attachment/machine_vision_AZ85_RA_Mirror_BS.py`:

    fold point   (229.930, 0, 53.803) -> (209.930, 0, 53.803)
    sensor       transverse 0.0000 mm -> 20.0000 mm     left behind, OFF the beam
    camera       did not move at all

The mirror moved and its arm did not, so the sensor ended 20 mm off the leg that feeds it — the
scene silently became one that cannot image.

Note the criterion: **transverse offset from the emitted leg**, not arc-length. Measuring `s`
alone said "unchanged" and looked fine, because the projection onto the (moved) leg is still
51.5 mm — the element had simply stopped being on it. Stating rule 3 in the tree's terms is what
made the defect visible.

## Why the sanctioned writer never showed this

`_apply_folded_image_split` re-seats the sensor and the camera itself (bugs/0447) — but it is a
different intent. It trades `near` against `far` holding the TOTAL, so on the same 20 mm slide the
sensor stays on the leg while its arc-length CHANGES, 51.5 → 71.5 mm, and the camera moves
(−20, 0, −20). That is the conjugate-preserving slide, and it already exists as the leg-split
constraint. A free drag has no total to preserve: rule 3 is the rigid carry.

## Fix

Two helpers on the placement mixin:

* `_fold_slide_carry_before(row)` — read BEFORE the pose moves, because afterwards the elements
  that were on the leg are off it and no longer look like members. Returns the rows riding on the
  folder's emitted leg (via `optical_axis_tree.rows_on_emitted_leg`, which includes the legs
  emitted further down the chain — slide a periscope's first mirror and the second mirror's arm
  comes too) plus the fold point.
* `_fold_slide_carry_apply(row, captured)` — translates them by however far the fold point
  actually went, and carries the camera body bolted to that arm.

A pure translation, deliberately: a slide moves the leg's origin and leaves its direction alone,
so every element keeps its own arc-length and transverse offset. Rotating a folder is rule 4 and
needs the DIRECTION carried too; it is not attempted here.

**The consequence, recorded rather than hidden:** a rigid carry changes the optical path length,
and so the focus. Sliding a fold mirror away from the lens with the camera bolted to its arm
genuinely lengthens lens → sensor. If the intent is "move the mirror but keep focus", that is the
leg-split constraint, not a drag.

### Both entry points

`translate_scene_row_pose` (axis form, `optical_solid_workflow.py`) and
`translate_scene_row_pose_vector` (`scene_placement_commands.py`) are two implementations of the
same operation, each carrying its own copy of the BS↔LED glue block. The drag gizmo goes through
the **axis** form, so a carry wired only into the vector form fires on nothing a user does — which
is exactly what happened on the first attempt, and why guard section B asserts both.

## Verification

    fold point moved (-20, 0, 0)
    sensor transverse 0.0000 -> 0.0000 mm     (was 20.0000)
    sensor arc-length 51.5000 -> 51.5000 mm   (rigid, not the leg-split trade)
    camera moved (-20, 0, 0)                  (was: did not move)

`KrakenOS/UI/validate_open3d_0487_fold_slide_carries_its_leg.py`, penta **phase 394**. Sections A
(membership: the chain below a folder is carried, the folder and the Object anchor are not) and B
(both slide entry points hooked) are display-free; C drives the real scene and SKIPs when the
attachment is absent.

Unchanged and re-checked: 0437 BS drag glue, 0433 rubber band, gap-to-solid slide, 0484, 0485,
0486; 54/54 pytest.
