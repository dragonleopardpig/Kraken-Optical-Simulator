# 0762 -- "delivered" needs BOTH residuals; and the solve banner sits beside the system HUD

Flag `20260909_202712_834`: *"Surprisingly, image still not landed on sensor."* The banner read
`the lens did not move -- the field was already delivered` with the image **5.932 mm** in front of
the sensor -- the shape bugs/0761 was supposed to close.

## What I ruled out, and how

| hypothesis | ruled out by |
|---|---|
| stale app | user had just powered on; and `d069c3c2` landed 13:13:51 against a 20:27:17 flag |
| fast-load deferred trace | both paths solve identically (\|m\| 0.4258 -> 0.7314, a real solve) |
| chained solves accumulating | 50 mm then 30 mm lands at -0.0216 then +0.0257, same as fresh |
| the scene file | on disk at defaults; the recording's geometry matches what my solve produces (C1 43.15 vs 42.65) |

**I could not reproduce the 5.932 mm.** From a fresh load a 30 mm solve lands at 0.0257 mm, twice.

## What was nonetheless wrong

bugs/0761 gated idempotence on the **first-order** residual -- precisely the reading that can
disagree with the real folded trace (bugs/0745). Whatever left the image 5.932 mm out, the gate
then declared the field delivered and refused to move, locking it there.

"Delivered" now requires **both** the first order and the MEASURED focus to say the image lands;
whichever is worse decides. That breaks the lock regardless of what caused the miss, and it is
correct on its own terms: a first order that disagrees with the trace must not be the sole
authority on whether the image is on the sensor.

## Banner placement (user request)

> "Can also position the solve banner beside the Magnification, Resolution banner, side by side?"

The solve banner now sits to the RIGHT of the system-info HUD instead of stacked under it. The
offset is the HUD's own **rendered width**, asked of VTK on every banner update -- the HUD grows
with its content (the bugs/0719 residual and the bugs/0754 way-out lines are long), so a fixed x
would overlap exactly when the text matters most. It falls back to the stacked anchor rather than
running off the right edge.

`vtkTextActor.GetSize` takes an **output array**; calling it with one argument raises, and the
`except` left the banner stacked with no sign of failure. Caught only by rendering a PNG and
looking at it -- the property assertions all passed
([[feedback_image_snapshot_tests]]).

## Guard

`validate_open3d_0762_delivered_needs_both_and_banner_beside_hud.py` (penta phase 550): the
flagged shape (first order lands, trace 5.932 out) is not delivered; the first-order gate still
refuses on its own; both-land still short-circuits; a missing measurement does not block; and the
banner uses the two-argument `GetSize` with a fallback.

## Still open

The mechanism that left the image 5.932 mm out in the user's session is **not identified**. The
gate now breaks out of it, but the underlying miss is unexplained. Next lead: the app runs the
full UI -- the 3D window's own Trace Now injects the imported optical STEP into the traced rows
([[reference_trace_now_live_step_overlay]], which once moved the sensor 600 mm) -- which the
headless reproduction never exercises.
