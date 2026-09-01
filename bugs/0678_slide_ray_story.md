# 0678 — flag_094639 + "ray tracing same as Prism_Assembly.png"

## What delivers the slide's picture TODAY

**Actions → Folded Assembly View** on `attachment/om05a_two_side.py` — both device
faces' imaging paths (126 + 126 rays) folded through the REAL assembly CAD by the
verified trace: face → outer prism → down → inward → centre prism → down → mirror →
lens → filter → mirror → camera. `attachment/om05a_slide_view.png` is that render,
head-on like the slide. The in-scene REAL single-arm trace is
`om05a_folded_armA.py` (0676: all five folds traced through real glass).

## Fake lenses (item 1) — product fix

The tunnel scene's glassy cylinder stack was the plates' revolved BBB glass BODY,
drawn by `_iter_3d_side_body_meshes`, which ignored `Drawing=0` (bugs/0674 gated
only the surface caps). The side-body iterator now honors it. (Restart the app to
pick it up.)

## Both faces traced IN ONE SCENE (item 3) — two blockers found, documented

1. **Pinned B-side wedges folded arm A's frame**: the bugs/0224 hit-radius test is
   deliberately SIGN-AGNOSTIC in distance, so a pinned mirror plane BEHIND the
   launch (the B prisms, 60 mm before the object) still counts as a fold when the
   infinite beam line crosses it. Moving the rows to the chain end did not fully
   restore the chain either.
2. **A scene SOURCE alone kills the imaging chain**: adding one enabled source
   (face-B rectangle emitter) drops the chain's reach from 68 to 0 — the source
   machinery switches the launch/trace mode. Isolated with a clean A/B (no B rows,
   source only).

Both are real product frontiers (trace-mode integration), not scene bugs. Until
they are addressed, the slide-exact BOTH-sides picture is the Folded Assembly
View; the armA scene is the real-glass single-arm trace. The RED (LED
illumination) paths of the slide are a future addition on the same foundations
(their Pyrite85 scene shows the LED-source machinery works in chain scenes -- the
conflict here is specific to this folded-solid scene type).

## flag_101659 "Ray tracing is wrong" + Prism_Assembly_Ray.png comparison

The user compared the TUNNEL scene's straight leg-1 rays against the slide: rays
must BEND through the prisms. Verdict accepted -- the tunnel fiction is retired
from the main scene:

- `attachment/om05a_folded.py` is now the REAL five-fold arm-A scene (rays bend
  at the outer prism, run inward, drop at the centre prism, fold at both mirrors
  -- the slide's green path, one arm, traced through real glass).
- The old straight-leg version is preserved as
  `attachment/om05a_unfolded_tunnel.py` (reference; its physics remain valid as
  the unfolded prescription).
- `attachment/om05a_bends_view.png` = the head-on render matching the user's
  comparison framing.

Remaining for the full slide picture in-scene: the second arm (blocked by the two
documented trace-mode frontiers) and the red LED illumination paths.
