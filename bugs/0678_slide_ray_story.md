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
