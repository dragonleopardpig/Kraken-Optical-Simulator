# 0488 — rotating a fold mirror turned the beam but not the arm (bugs/0485 rule 4)

> 4) Same as (3), if the elements that introduce a fold axis is now flipped, then all snapped
>    elements should also follow the flipped snap axis.

Asked directly: *"If user do funny thing like rotating the mirror to some other angle, the fold
axis and the camera should follow (or does it?)"*

## Measured before

Rotating the RA mirror **+10°** about y on `attachment/machine_vision_AZ85_RA_Mirror_BS.py`:

    emitted leg   [0, 0, -1] -> [-0.342, 0, -0.9397]      = 20.000 deg
    sensor        (229.93, 0, 2.30)   unchanged  ->  17.614 mm OFF the new leg
    camera        (229.93, 0, -23.03) unchanged

So the **axis already followed perfectly** — a mirror rotated by θ turns the beam by 2θ, and the
bugs/0485 derivation produced that for free, with no rotation-specific code. What did not follow
was everything bolted to the leg: the beam swung 20° and the detector stayed where it was.

## Fix: rules 3 and 4 are one operation

A rigid transform about the fold point:

    new = fold_after + R (old - fold_before)

A **slide** is the case `R = I` (the origin moves, the direction does not). A **rotation** leaves
the fold point alone and turns the leg. A drag doing both gets both, with no extra code — and the
guard asserts that composition directly (D4: a pure rotation leaves the fold point at
`[0, -0, 0]`).

Carried rows also have their **own orientation** turned, `R @ R_row` written back through
`kraken_tilts_from_rotation_matrix`. A sensor that lands in the right place still facing the old
direction is just as wrong, and reusing the existing convention rather than deriving a second one
is the bugs/0448 lesson.

## The entry-point trap, three times

"Move a row" has **four** parallel implementations, each historically carrying its own copy of the
BS↔LED glue block:

| | |
|---|---|
| `translate_scene_row_pose` | axis form, `optical_solid_workflow.py` — **what the drag gizmo uses** |
| `translate_scene_row_pose_vector` | `scene_placement_commands.py` |
| `rotate_scene_row_pose` | local-axis rotate |
| `rotate_scene_row_pose_world_axis` | world-axis rotate |

Rule 3 went into the vector form first and fired on nothing a user does. Rule 4 then went in
without either rotate form, so a rotation still left the arm behind — the same trap, twice more.
Guard section B now asserts all four at source level, which is the only thing that will catch a
fifth.

## Verification

    emitted leg turned 20.0000 deg
    sensor  (229.93, 0, 2.30) -> (212.32, 0, 5.41)   transverse 17.614 -> 0.0000 mm
    camera  (229.93, 0, -23.03) -> (203.65, 0, -18.40)
    fold point unchanged, [0, -0, 0]

Guard `validate_open3d_0487_fold_slide_carries_its_leg.py` (sections A/B display-free, C slide,
D rotate), penta **phase 394**. Rule 3 re-checked unchanged: transverse 0.0000, camera (−20, 0, 0);
glued LED+BS drag still carries BS, mirror and camera +20 each. 0437 BS drag glue, LED/BS glue
after promotion and gap-to-solid slide all PASS; 54/54 pytest.

## Still open

A drag or rotation is a **constraint** the solver must honour — see the note at the end of
bugs/0487. Rotating the mirror changes which way the arm points but the solver will still re-run
its own default distribution and discard it, exactly as measured for the slide (residual −20.0000
→ −25.5266 after Solve for Thickness). That is the next piece.
