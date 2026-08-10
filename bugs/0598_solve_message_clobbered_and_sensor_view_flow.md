# 0598 — the solve's outcome was unreadable, and the sensor-view flow polish (FIXED)

Five flags in one morning, one investigation.

## Flag `flag_20260810_103406`: "section 4 constraint set to 30 — not working"

**The constraint machinery is NOT broken.** Replayed headless through the REAL dialog entry
(`_apply_quick_estimation_fov_solve("object","thickness",55,55,None,image_segment=("far",30))`)
on the as-loaded Apo75 — with two overlays on, then with all six — the world sensor leg lands at
**exactly 30.000 mm** every time (`near` absorbs: 279.06/323.44), through
`_apply_folded_image_split` after the solve.

What IS broken, measured: **the user cannot see what the solve said.** Immediately after the
solve sets its status ("Solved (folded): … the sensor moved −46.08 mm … Made room first …"),
the async tracing badge overwrites BOTH status bars with "Tracing 999 rays in the background…".
Any refusal would vanish the same way. With no readable outcome and the 3D view mid-retrace,
"the constraint is not working" is a fair reading of a blank.

**Fix**: the FOV apply path stashes its outcome as a sticky message; `_set_async_status` keeps
it IN FRONT of the badge ("Solved … 30 mm  |  Tracing 999 rays…") for two minutes, dropping
stale ones. Unit-verified both ways (sticky rides; stale clears).

**Unexplained residue**: the flag's recorded geometry equals the AS-LOADED scene — in the
user's session nothing moved at all, while every replay applies. The recorded FOV label reads
55×55 (the target updated). With the outcome message now visible, the next occurrence will
name itself; if it recurs, flag it with the RECORDER on so the dialog command is captured.

## Flags `104827 / 104855 / 104925 / 104937`: the sensor-view zoom/rotate flow

The first three document the (now-working) overlay suite in the sensor view — the `104827`
screenshot is the full payload: per-field Zemax spot shapes, pixel lattice, distortion grid,
illumination fill. Note for bugs/0591: the edge-field spots land visibly OUTSIDE the sensor
square — the delivered-magnification error, photographed by the user.

`104937` ("zoom in again: blocked by other elements"): rotating away restores the hidden
components BY DESIGN (`flag_20260709_162334` demanded exactly that), so zooming back in lands
inside the camera body. Not a defect — a discoverability hole: nothing said why everything
returned. **Fix**: leaving the view on rotation now sets the status: *"Left Normal to Sensor
(rotation restores the scene) — click Normal to Sensor again to isolate the sensor."*

## Flag (verbal): "a brief flash of optical elements after enabling each analysis overlay"

Real, and mechanical: the toggle rebuild re-creates EVERY actor visible, renders, and only then
re-applies the sensor isolation — one visible frame of the whole scene. **Fix**: the toggle path
freezes buffer swaps (`SetSwapBuffers(0)`) for the rebuild, so intermediate renders land in the
back buffer; the single final render swaps a finished frame. IN-APP EYEBALL OWED — flicker
cannot be judged headless.

Guards: 0597/isolation/gesture-leave all pass with these changes; the sticky-status behaviour
is unit-tested in-line (see the `_set_async_status` docstring for the measured story).
