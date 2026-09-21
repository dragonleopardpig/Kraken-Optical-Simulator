# 0844 -- a lens blocked by what the camera stage carries is not a refusal

> *"device size changed to 50x50x1, solver rejected. I think this is not correct, contradict to
> actual production."*
>
> *"i don't think asking user every time a device size is changed, the apps should know how to
> do it, not the user. Please solve the actual underlying algorithm problem."*
>
> *"this sliding problem bound to minimum and maximum. The algorithm can get both values ...
> the algorithm should be able to solve any values in between, thus eliminating false solve
> refusal."*

`om05a_folded.py` ships with a 50 mm device and renders it. Set 20 mm and solve; set 50 mm
again and solve -- **refused**, with "a different lens / working distance". Same machine, same
request the file loads at. The answer depended on the path taken to ask.

## What was measured

A row-by-row ledger of the 21 mm solve on the shipped scene:

    row  7  RA mirror 1 -> lens     180.470 ->  50.234     lens  130.236 mm toward the object
    row 12  lens -> Filter           21.600 ->  79.681
    row 13  Filter 48-926            drawn  +72.154 mm     } the camera STAGE (bugs/0759):
    row 15  RA mirror 2  desp_x            +72.154 mm      } Filter + mirror 2 + camera, rigid

The solve drives **two motors** -- the lens, and the stage that carries the Filter, RA mirror 2
and the camera. It books them lens FIRST, and measures the lens's room against where the stage
stands at that moment. Going back:

    lens needs                +116.389 mm  toward the Filter
    room right now               74.47 mm  -> REFUSED
    the same solve would then move the stage +60.339 mm the same way
    final lens -> Filter gap     23.64 mm  (the file ships at 21.60)

**The state that collides never exists.** The rows are written together and drawn once. On the
real bench a motion controller would move the stage out of the way and then the lens; the
solve judged a snapshot halfway through its own booking.

Going toward the object the lens moves *away* from the Filter, so the forward solve never hits
this. That asymmetry is the whole path dependence.

## The experiment, before any production change

On the path-dependent state: stage first by `image_delta + object_delta`, then the lens.

    FRESH-load 52.5 solve            rows 7/12/14 = 166.6231 / 23.6414 / 42.9155   |m| 0.43886
    after 21, stage FIRST            rows 7/12/14 = 166.6231 / 23.6316 / 42.9253   |m| 0.43886
        lens +116.389: OK, thickness pair, room 134.81 mm
        conjugate re-measured: object_delta -0.000000   image_delta -0.000000

(The 0.01 mm left is the traced-focus snap the experiment skipped.)

`image_delta + object_delta` is not a new formula: bugs/0575 measured that the thickness pair
leaves the sensor's station alone, so that sum is exactly the image correction outstanding once
the lens has moved. It is used as the ORDER of two moves the solve makes anyway. The booking
still re-measures the conjugate afterwards and books whatever is left through the normal image
path -- which here is nothing.

## The fix

`_lens_move_with_camera_stage_first` in `quick_estimation.py`, called when the lens move is
still refused after the bugs/0573 rescue:

1. same gates as the normal image path -- a declared stage arm, the vendor-hardware lock, the
   stage's own travel;
2. open a savepoint (bugs/0843's `GeometryTransaction`);
3. move the stage; 4. ask the lens move again -- **its own room gate measures the final state**;
5. commit only if the lens moved as the live-chain thickness pair this order is measured on;
   otherwise both go back, exactly.

Nothing is assumed about *which* body rides the stage. If the blocker is not on it, the retry
refuses and the savepoint puts the stage back.

This is the user's min/max framing made operational: feasibility is a property of the FINAL
configuration, which is a function of the requested field alone. Inside the machine's travel
every field is solved; outside it the refusal now names the limit that actually binds:

    ... This field would also put the camera stage at -395.9 mm, outside its -290.7 to
    -88.67 mm travel -- nothing was moved.

    ... Moving the camera stage +60.35 mm first was tried, and the lens move was still refused
    (... only 110 mm ...). The stage was put back -- nothing was moved.

The wording is neutral on purpose. A lens travelling toward the OBJECT is blocked by RA mirror 1,
which no stage move clears; the first draft said "out of the way" there, which was untrue.

The success message quotes what the sensor TRAVELLED (the re-measured `image_delta` is ~0 once
the stage has gone first) and says the stage moved first.

## The real scene, end to end

`bugs/diag_0844_path_independence.py`, through the real `fov_solve`, starting from the user's
SAVED refusal scene (needs bugs/0845 as well -- see that note for why):

    solve 52.5   ok    rows 7/12/14/seat  vs a FRESH-load solve:  +0.0000 +0.0000 +0.0000 +0.0000
                       "the sensor moved +75.35 mm ... The camera stage moved first"
    solve 21     ok                                               +0.0000 -0.0014 +0.0015 +0.0015
    solve 52.5   ok    (stage first, +60.34)                      +0.0000 -0.0112 +0.0112 +0.0112
    solve 4.2    REFUSED, scene byte-identical   lens blocked by RA mirror 1; stage would need -508.5
    solve 94.5   REFUSED, scene byte-identical   stage would need -395.9
    solve 52.5   "Already delivering 52.5 x 52.5 mm -- nothing to move."

The 0.011 mm is the traced-focus snap (its own residual is 0.0226 mm).

## What this is NOT

Not the axis tree. bugs/0843's note blamed `optical_axis_tree.snap_rows` for snapping om05a's
lens to `axis:root`. Re-reading `translate_lens_block_along_leg` showed `_lens_leg_slide_plan()[2]`
is the **branch selector** between two scene classes -- frozen desp-leg scenes slide, live-chain
scenes like om05a take the pure thickness pair *by design* (bugs/0719). "Fixing" the snap sent
om05a down the wrong primitive, which is precisely what slid the arm 197 mm in the scratch tree.
The stash holding that work stays labelled UNSAFE and is not the way forward.

## Guard

`validate_open3d_0844_camera_stage_goes_first.py`, display-free, penta phase 623: a geometric
miniature of the bench. The lens's room is `rows[rear].thickness - overhang` -- never scripted --
so it changes because the REAL `_apply_camera_arm_move` (with the real stage reader, seat-axis
measurement and vendor lock) really moved the Filter. The REAL `_apply_conjugate_pair` drives it,
unwrapped and wrapped. Expectations are derived in the guard from `s_o = f(1+1/m)`,
`s_i = f(1+m)`, not read back from the code -- and they land on the real scene's fresh-load
numbers (166.6231 / 23.6413 / -257.3315).

- **Z** CONTROL: rescue neutered, the booking refuses with the banner's numbers (+116.389 / 74.469)
- **A** the fix: call order, final rows, nothing left to book, honest message, move recorded
- **P1** a zig-zag 52.5 -> 21 -> 60 -> 12 -> 45 -> 30 -> 52.5 lands every field where a direct
  solve lands (worst 3e-14 mm); **P2** CONTROL: lens-first only, the same path refuses 52.5, 60, 52.5
- **R** a fat barrel that does not fit the FINAL state: refused, byte-identical, first numbers back
- **T** stage past its travel: nothing attempted, reason names the travel
- **M** lens moved by another primitive: put back, first refusal untouched
- **V** vendor lock gates the rescue; **F** a partial fake falls through

`bugs/diag_0844_path_independence.py` re-measures the real scene end to end.

## Possible follow-up (not measured, not claimed)

The mirror case: when both fields magnify (m1*m2 > 1) the stage moves TOWARD the lens after the
lens has been judged against its old position, so a final-state collision could pass the
lens-first gate. The stage's own travel limits may already cover it on om05a; worth a
measurement before anyone calls it a bug.
