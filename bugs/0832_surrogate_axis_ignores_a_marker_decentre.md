# 0832 -- a marker's decentre is not the lens's optical axis

Two flags, 2026-09-20, `om05a_folded` after a lens swap + solve:

* `flag_20260920_174941_901` -- "lens and surogate not aligned, not sure it is after flipped."
* `flag_20260920_175110_525` -- "is the lens hit the Edmund filter?"

Same scene, two camera angles, **one defect**.

## What the capture measures

The drawn scene is unambiguous. Every lens surrogate row is co-axial:

    row  8  Front Optical Vertex Datum   x = -160.08   (y, z) centre = (56.365, -25.000)
    row 10  Aperture Stop                x = -187.58   (y, z) centre = (56.365, -25.000)
    row 12  Rear Optical Vertex Datum    x = -215.08   (y, z) centre = (56.365, -25.000)
    row 13  Filter 48-926  O50.8 x 1     x = -217.10 .. -216.10

and the rays agree with them -- `ray_actor_extents` crosses x = -160.08, -187.58, -215.08 on
exactly those transverse centres. **The trace was never wrong.**

The lens CAD body was:

    lens STEP bounds   x -216.41 .. -157.22   y 28.86 .. 83.86   z -58.77 .. -3.77
    -> (y, z) centre = (56.36, -31.27)

`y` matches the axis to 0.005 mm. `z` is **6.27 mm** off. That is flag 1, and it equals
`lens_step_placement_offset_xyz = (-6.2694, 0, 0.9938)` -- a placement offset the saved scene
does not carry (`[0, 0, 0]` on disk), so this session wrote it.

And the body's rear tip at x = -216.41 sits **0.31 mm past** the filter's upstream face at
x = -216.10, laterally inside its O50.8 clear aperture. That is flag 2: yes, it hits.

## Root cause

`_lens_surrogate_optical_axis_line()` drew the **chord** between the Front and Rear Optical
Vertex Datum rows. In a SEQUENTIAL scene `desp_x/desp_y` mean *"how far this surface sits OFF
the axis"*, not *"where the axis is"* -- so one marker's decentre becomes a tilt of the whole
lens. `om05a_folded` carries exactly that:

    row  8  Front Optical Vertex Datum   desp = (-8.78, 0, -0.3885)   rc 0, AIR
    row  9  Blackbox Group 1             desp = ( 0,    0,  0)
    row 10  Aperture Stop                desp = ( 0,    0,  0)
    row 11  Blackbox Group 2             desp = ( 0,    0,  0)
    row 12  Rear Optical Vertex Datum    desp = ( 0,    0,  0)

The front datum is a pure marker -- flat, AIR, no power -- so the -8.78 does nothing to the
trace. It only tilts the derived axis. Measured on the scene, and the decisive experiment:

    as authored    off-axis  7.0128 mm   tilt 12.4076 deg
    desp_x zeroed  off-axis  0.0000 mm   tilt  0.0000 deg

100% of the reading came from that one number.

`center_lens_body_on_surrogate_axis` then **acts** on it. It runs on every lens swap
(`layout_table_workbench.py:2288`) and moves the CAD body transversely onto the line. With a
tilted line, "transverse" is tilted too: the applied offset `(-6.2694, 0, 0.9938)` points
`atan(0.9938 / 6.2694) = 9.01 deg` away from the true transverse direction -- **the recorded
tilt itself**, `optical_axis_tilt_deg = 9.0074`. So the correction

* pushed the barrel **6.27 mm sideways** off the axis (flag 1), and
* leaked **0.9938 mm along** the axis. Pre-fold `+z` maps to world `-x` here (rows advance
  275 -> 337 in z while x runs -185 -> -247), so that leak moved the body *toward* the filter.
  Back it out and the rear tip sits at x = -215.42, clear of the filter's -216.10 face by
  **0.68 mm** (flag 2).

The function's own post-correction re-measure still read 4.0845 mm off. It could not converge:
projecting onto a tilted axis cannot reach zero.

## The fix

Branch on the ONE placement resolver, because `desp` genuinely means different things:

* **WORLD** -- the 0433 freeze bakes the folded leg into `desp`, so a datum's pose *is* its
  absolute position and the chord is the only right answer. `machine_vision_ELS85`'s matched
  (55, 0, -55) datum pair is a real 45 deg leg and still reads `(1, 0, 0)`. Untouched.
* **SEQUENTIAL** -- the direction is the chain's own (a decentre cannot tilt the chain), and
  the transverse position is the **median** `(desp_x, desp_y)` over the whole datum-to-datum
  span. A lens that really is decentred has every row sharing one offset and the median
  returns it; a single mis-set marker is outvoted.
* **Mixed** -- refused, with the two spaces named. A chord between two coordinate systems is
  not a number, and the caller *moves the lens body* onto it.

The median matters. A mean would split -8.78 across five rows and leave the body 4.39 mm off
-- which is also what a direction-only repair leaves, since the chord's midpoint inherits half
the decentre.

## Result

    om05a_folded          7.0128 mm / 12.4076 deg  ->  0.0000 mm / 0.0000 deg
    machine_vision_ELS85  axis (1, 0, 0)           ->  axis (1, 0, 0)

The swap now applies nothing at all on this scene, so both the 6.27 mm sideways push and the
0.99 mm creep into the filter are gone.

## Still open (not this bug)

`swap_clearance_diagnostics` in both captures reads:

    "obstacle_bounds": null,
    "result": "0 mm: missing obstacle"

The clearance check **did not run**, and reported a number -- `0 mm` -- that looks like a
measurement but is an absence. Nothing warned about the 0.31 mm interference. That is the
`bugs/0777` / `result_diagnostics` failure mode and the user's standing rule ("a refused solve
must ALERT ... never auto-pick the remedy"). Separate fix.

## Guard

`KrakenOS/UI/validate_open3d_0832_surrogate_axis_ignores_a_marker_decentre.py`, penta phase
611. It asserts the OLD chord really did read 7.01 mm / 12.41 deg on this scene, so a revert
cannot pass; that the WORLD scene is unchanged, so the fix is not "always use +z"; and that a
genuine 12.5 mm decentre shared by every span row survives, so the median follows a real
decentre rather than zeroing one.
