# 0846 -- after a solve the banner says where the focus landed and what the stage did

> *"50x50x1mm works. I notice the banner is less verbose."* -- flag_20260921_162154, the first
> 50 x 50 solve bugs/0844 made possible. Then flag_20260921_162616 (20 x 20) and
> flag_20260921_163121 (back to 50 x 50): all three solved.

The 50 x 50 banner, in full:

    SOLVE  delivering 52.5 x 52.5 mm (|m| 0.4389); the lens moved +131.4 mm along its leg

The 20 x 20 banner had six rows -- SOLVE, FOCUS, both faces, Landed, STRAY LIGHT.

## Why it went quiet

Both omissions happen **because the outcome was good**.

1. **Focus.** The whole FOCUS block -- the line, the per-face lines, and the bugs/0767 Landed /
   Move verdict -- sat behind `abs(offset) >= 0.05` mm. The 52.5 mm solve landed **0.023 mm**
   off the sensor, so the best result said nothing at all. Silence cannot be told apart from
   "not measured". The 21 mm solve landed 0.116 mm off and got the full block.

2. **The second motor.** The camera stage carried the Filter, RA mirror 2 and the camera
   **+75.35 mm** -- the largest visible move in the scene, and since bugs/0844 made *first*, to
   clear the lens's way -- under a SOLVE line that named only the lens. The bugs/0783
   working-distance restore already recorded `group_move_mm`; nothing printed it.

## The fix

**Focus, after a solve:** when the image is within the 0.05 mm gate and a solve ran, the banner
says so --

    FOCUS  the image forms on the sensor (0.023 mm in front of it) -- spot 1.2 um on the sensor
    Landed the blur on the sensor (1.2 um) is inside one pixel (4.5 um) -- nothing to move

-- through the SAME pixel verdict as before (hoisted into `_landed_or_move_line`, so a blur
beyond a pixel still gets "Move the device stage" or "THE BLUR IS NOT DEFOCUS", never a blanket
"landed"). **With no solve an in-focus scene still says nothing** (bugs/0728 D3: a banner on
every load is clutter). Above the gate the text is byte-identical to before.

**The stage:** `fov_solve` records the stage seat when it starts; the summary gets the NET
travel along the beam over the whole solve -- every booking and refinement pass -- measured, not
accumulated. Signed like the lens (positive = away from the object) using the bugs/0782
measured seat axis; when that axis cannot be measured the distance is given with no direction.

    Camera stage  moved +75.35 mm along the beam, carrying everything on it -- first, to clear
                  the lens's way

The stage-first note comes from `_fov_solve_stage_first_mm`, set only when the 0844 rescue
commits, and listed in the booking-wide net's `also=` so a booking refused later takes the claim
back with the geometry.

## A wrong turn, recorded

The three flags showed the lens moving **+/-131.4 mm** between 21 and 52.5 mm, where my
end-to-end run said 116.4. It looked like the real-ray field-fill refinement had applied a 24%
correction at 21 mm and none at 52.5 mm -- impossible for a thin-lens model, so a suspected
measurement bug. It was my harness: the real `set_inspection_part_spec` moves the object row
with the device face (20 mm: face A at z=-15; 50 mm: z=0), and my probes assigned
`inspection_part_spec` directly. Replayed with the real callback, headless reproduces all three
flags exactly (lens gap 166.6231 / 35.2344 / 166.6231, seat -257.33 / -181.98 / -257.33).
The 0844 note's two 21 mm end-to-end rows carry a correction; `bugs/diag_0844_path_independence.py`
now uses the callback.

## Guard

`validate_open3d_0846_banner_reports_a_landed_solve.py`, display-free, penta phase 625.

- **F1** the 0.023 mm solve now reports its landing with the pixel verdict; **F2** no solve ->
  nothing (0728 D3), no measurement -> nothing invented; **F3** in focus by distance but blurred
  beyond a pixel gets the aberration / defocus verdicts; **F4** above the gate byte-identical to
  the user's 20 x 20 flag text
- **S1-S5** the stage line: signed + order, not-first, the 0783 group move, unsigned when the
  axis is unmeasured, nothing on a lens-only scene or a zero move
- **B1** the travel is measured by the REAL stage motor on the bugs/0844 bench (sensor
  +60.339 mm along the beam = reported +60.339); **B3** the stage-first claim is recorded only
  when the stage really went first; **B4** a booking refused after the stage went first takes
  the claim back -- with **B4-Z** CONTROL: strip the net's `also=` and the claim survives
- **W** fov_solve starts the measurement and writes it (executable lines)
