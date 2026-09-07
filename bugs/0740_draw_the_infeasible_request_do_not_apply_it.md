# 0740 -- draw an infeasible field request; never apply it

> "the solve evolved from No Crash + Image in front of sensor to Crash + No image formed. I don't
> know what to trust now."

## What had happened

Three changes composed into a trap:

* **0731** stopped refusing on an image-location shift -- only a real collision refuses.
* **0732** ("There is no need to have additional click on Force, just do it") made a COLLISION
  refusal apply the forced move automatically.
* **0737** stopped drawing a focus plane when no ray lands.

So an infeasible request now drove the lens into vendor hardware, the crashed geometry blocked the
rays, and the viewer -- correctly -- drew no focus plane. "Crash + no image formed", from a scene
that traced a moment earlier. Each step was right on its own; together they destroyed the thing the
user was working on.

And it persisted: `attachment/om05a_folded_80mm.py` was **saved** in that state, with its lens
**11.03 mm inside RA mirror 1's glass** (4418 of 13387 lens mesh points enclosed, measured against
the real triangles). Every later solve then started from a crash, so every collision report carried
a constant 13.03 mm the solve had not caused:

| requested | lens moved | reported penetration | difference |
|---|---|---|---|
| 10 x 10 mm | 0.62 mm | 13.65 mm | 13.03 mm |
| 5 x 5 mm | 8.50 mm | 21.53 mm | 13.03 mm |

The scene was repaired separately (+13.030 mm back along the leg, thickness pair, total track
unchanged: gap 8.504 -> 21.534, rear 189.896 -> 176.866, 0 lens points in glass, deepest +2.000 mm
= exactly the clearance). Backup: `attachment/om05a_folded_80mm.prerepair_20260907.py`. With the
geometry sane, penetration equals the move exactly (13.6509 = 13.6509), and a real limit appears:
**the smallest square field this om05a build can deliver is about 13.6 x 13.6 mm** (|m| ~ 1.6).

## The fix

A room refusal no longer forces. The geometry is left alone and the REQUEST is drawn instead.

The user rejected a text-only version of this before it was built:

> "if the lens stay + Object FOV changed + Image detached, what is visually wrong, am I right?
> Although there might be some banner clarifying but human being is influence by picture stronger
> than words."

That is the design constraint. An unchanged scene with a calm banner reads as success, so the
picture has to carry the failure:

1. **A ghost lens** (`_add_infeasible_fov_ghost`) -- the lens barrel outlined in collision red at
   the position the field demands, sitting visibly inside the vendor body that blocks it, labelled
   with the requested field, the depth of the overlap, and what the lens delivers where it stands.
2. **The delivered object field** (`_add_delivered_object_field`) -- setting the device face
   redraws the object FOV band whether or not the solve succeeded, so after a refusal the scene was
   showing the REQUESTED field as though it were being imaged. The delivered field is now drawn
   concentric with it in the same red, so the shortfall is a visible gap. On om05a: a red 14.32 mm
   rectangle around the green 10.5 mm band.
3. The banner keeps its numbers, and Force stays available for when you DO want the collision.

Both are drawn on every scene refresh beside the solve banner, and deliberately NOT behind the
detector-overlay toggle: a refusal the user has to switch on is a refusal they will not see.

## Two defects found while building it

* **The forced retry targeted the DIAGONAL.** 0735 moved the plain attempt to the rectangular
  target (`image_semi`) but left the forced retry on `float(sensor)`. Any non-square field that
  needed forcing overshot to a larger magnification than the request warranted and showed a deeper
  crash than asked for. Square fields hid it (the two coincide). Removed with the escalation.
* **The room refusal was detected by matching its own prose.** Rewording the sentence (below)
  silently stopped the ghost being stashed -- caught by a render, not by a test. The solve now
  matches a structured `_lens_move_refusal_info` stamped by the move primitive, cleared at entry
  like every other per-attempt channel.

## Wording

An AABB clearance that lands on zero printed as `1.203e-11 mm`, which reads like a measurement
rather than "there is none". Below a micron both the refusal text and the banner now say so
outright ("no physical room is left at all" / "no room at all").

## Guard

`KrakenOS/UI/validate_open3d_0740_draw_the_infeasible_request.py` (penta phase 537).
bugs/0732's A2-A4 are re-scoped to this contract; bugs/0731's D1 now pins the gate structurally
rather than by its sentence.
