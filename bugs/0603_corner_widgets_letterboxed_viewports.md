# 0603 — Nav cube / XYZ axes still not pushed to their corners (FIXED)

Flag `flag_20260810_164247_396` (third complaint), the FOURTH flag on this corner:
*"Both XYZ axis indicator and Nav Cube are not pushed to corners. Blue arrow and orange
arrows are not reduced spaced to go closer to the cube."* Build `e1b2958f` — which
already CONTAINS the 7ccbaac8 constant changes, so this was not a stale app.

## Root cause — window-fraction viewports letterbox

Both corner widgets lived in viewports specified as WINDOW fractions:

- nav cube `(0.815, 0.78, 1.0, 1.0)` → on the flagged 2478×1264 window a 458×278 px
  rect, pixel aspect 1.65;
- axes marker `(0, 0, 0.13, 0.13)` → 322×164 px, aspect 2.

The corner cameras fit their content by HALF-HEIGHT and centre it horizontally, so on
any wide window the cube assembly floated ~100 px off the right edge and the axes ~80 px
off the left — however the constants were tuned. Shrinking fractions can never fix a
shape problem: the margin is the letterbox.

## Fix — pixel-square corner viewports, recomputed per render

`corner_square_viewport(w, h, side_fraction, ..., anchor)` in `nav_cube_widget.py`
computes an aspect-1 viewport whose square touches the anchored corner exactly
(side = fraction × window height, width-clamped, readable floor on tiny windows).

- `NavigationCube._apply_corner_viewport()` runs first in the render StartEvent
  observer and re-viewports the cube + arrow renderers when the size changed; the
  click hit-test uses the live viewport. With aspect 1 the arrow camera's fit is exact
  (`_ARROW_FIT_HALF` in every direction), so the arrows touch the corner and the arcs
  sit just outside the cube silhouette — the "closer to the cube" ask is the same
  letterbox: the spacing constants were already tight, the empty margin was viewport.
- The inspector's axes marker gets the same treatment (`anchor="bottom-left"`,
  side 0.15 × height) via a window StartEvent observer
  (`_square_orientation_marker_viewport`).

Both react to live window resizes (panels hidden/shown, maximise) — the class of flag
ends rather than the instance (the fraction constants only ever matched one window
shape).

Verified by rendered snapshot at the flagged window size. Guard: phase 456
(`validate_open3d_0602_0603_readout_and_corners`) — pixel-square + corner-touching
asserted for both anchors across window shapes, plus the render-observer wiring.
