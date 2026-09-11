# 0780 -- stray light that reached the sensor by another route draws faint

> "I still see many stray rays flying around."

Flag `20260911_160208_046`, captured on build 40d35e2f -- the bugs/0779 fix. The measurement was
already right. The banner read:

```
FOCUS: the image forms 0.09252 mm in front of the sensor -- spot 0.463 um there vs 2.27 um on the sensor
Landed: the blur on the sensor (2.27 um) is inside one pixel (4.5 um) -- nothing to move
STRAY LIGHT: 6 ray(s) reach the sensor by another optical route and land up to 1.9 mm outside the
image (0.9% of the landing rays) -- not part of the image, left out of the focus measurement
```

But the scene still drew those cross-arm rays exactly like image light: same field colour, same
opacity, same width. "Show clipped rays" OFF keeps every ray that reaches the sensor, and these do.

## Why weighted, not hidden

- **bugs/0530 doctrine:** true light is never hidden, only weighted. The rays are real paths in the
  model as built (bugs/0779's review traced them), so removing them would draw a scene the trace
  does not contain.
- **bugs/0604 precedent:** beam-splitter ghost forests already fade by power, with a floor of 0.15
  so even the faintest stays traceable. Stray light uses that same floor.
- **The user's own definition (bugs/0554):** "a clipped ray is any ray not reaching the sensor".
  Stray rays DO reach the sensor, so the Clipped toggle is the wrong switch for them.
- **Closer to the physics, not further:** the ghost reflects off three cube cement planes where
  image light reflects off one, and the trace draws those planes as full mirrors, so even in the
  real cell it would be at most a quarter as bright as image light.

## The fix

- `_iter_3d_scene_ray_records` (three_d_scene_tools.py) classifies each draw's landing rays with
  `split_stray_routes` -- the rule the focus measurement uses -- over the whole bundle, BEFORE the
  draw budget thins it (a subsample would change which routes look dominant). It keeps the stray
  path objects alongside their ids, so an id can never be recycled onto a later bundle's path.
- `_ray_stray_route_display_weight(path)` returns `_STRAY_ROUTE_DISPLAY_WEIGHT` (0.15) for a stray
  ray and 1.0 for image light or no path.
- Both scene draw loops in `open3d_scene_refresh.py` (`_refresh_rays_only`, `refresh_scene`)
  multiply the ray's opacity by it, next to the bugs/0604 power weight, and the Normal-to-Sensor
  view (bugs/0606), which shows the light that forms the image, leaves stray rays out.
- A stray ray's terminal status is untouched, so the bounding and clipping that key on status draw
  its path exactly as before.
- The banner line now ends "... left out of the focus measurement and drawn faint in the 3D scene".

Not changed: the legacy 3D plotter loop (it never got the bugs/0604 weight either) and the 2D
layout view.

Known and accepted: the fade follows the ROUTE, so the few off-route rays that land ON the image --
bugs/0779's stop-rim bookkeeping class, which records no aperture-stop event but is ordinary image
light -- are faded too. They lie on top of the dense image fans, so nothing visible changes, and
the proper fix is that tracer bookkeeping bug, not a footprint test in the draw path.

## Verified

Rendered headless through the real inspector in the APP's order -- 3D window open, then Apply and
Solve FOV 22.5 on a 15x15x1 device, the flag's setting -- with the camera framed on the sensor leg,
once at the shipped weight and once forced back to 1.0:

| | display rays | classified stray | picture |
|---|---|---|---|
| weight 1.0 (the old look) | 2206 | 18 | thin separate lines beside the image fans on the mirror-2-to-sensor leg and across the prism gap |
| weight 0.15 | 2206 | 18 | those lines barely visible; image fans unchanged |

Both carry the banner stack SOLVE / FOCUS / "Landed: the blur on the sensor (2.27 um) is inside one
pixel" / STRAY LIGHT.

A first render pair solved BEFORE opening the 3D window. The inspector then reused the solve's
226-ray fan trace, classified 0 stray rays, and the two weights produced identical pictures -- a
check that could not fail. The same flaw applied to the bugs/0779 render.

## Guard

`KrakenOS/UI/validate_open3d_0780_stray_rays_draw_faint.py`, penta phase **563**, 14 checks, on the
bugs/0779 synthetic split field through the REAL `_iter_3d_scene_ray_records` and
`_ray_stray_route_display_weight`: exactly the stray-route rays are classified, across the whole
bundle even when the draw budget draws only part of it, a clean bundle classifies nothing and a
new draw clears the old classification (A); terminal status unchanged (B); weight 0.15, equal to
bugs/0604's floor, and 1.0 otherwise (C); both draw loops apply it and drop stray rays in the
Normal-to-Sensor view (D); the banner wording (E).

## Still the user's call

Whether real hardware blocks the ghost (bugs/0779, "Is the ghost real?"). If a vendor body is made
opaque, those rays stop being traced at all and nothing is left to fade.
