# 0005 — "ghost red edges": STEP face hover highlight painted red, reads edge-on as a red bar through the lens

**Status:** Fixed. The imported-STEP face mouse-over highlight now uses the
shared hover-gold accent `(1.0, 0.78, 0.08)` instead of red, with a thinner
tube. Hovering a lens face no longer paints a red bar/sliver through the glass.
**Component:** Open 3D inspector — STEP face hover outline.
**Reported via:** in-app recorder, two flags in the 2026-06-03 11:28 session:
`attachment/recorded_bug_repros/flag_20260603_112845_081/` ("ghost red edges
detected") and `flag_20260603_112915_602/` ("another ghost red edges
detected"). Event log `recording_20260603_113235.json`.

## Symptoms (user's words)

> "ghost red edges detected"

> "another ghost red edges detected"

Both screenshots show a lens viewed from the side with a bright red-orange
vertical bar / block at the glass and the hover label `OPTICAL STEP S00n/F002
face` by the cursor reticle. Both flag states: `interaction_mode: idle`,
`picked_step_label: "optical"`, `selected_step_label: null`, all handle counts
0 — i.e. no gizmo, just a face under the cursor.

## Behaviour before

`_set_step_hover_outline_impl` (the mouse-over highlight for an imported STEP
face, driven from `_on_mouse_move`) hard-coded a red style:

* fill+edges branch: `SetColor(1.0, 0.26, 0.0)`, opacity 0.58, line width 6
* edges-only branch: `SetColor(1.0, 0.18, 0.0)`, opacity 1.0, line width 8

plus `RenderLinesAsTubesOn()`. A lens face viewed edge-on (the default side
view) collapses to a vertical line, so that thick red tube rendered as a solid
red bar straight through the glass — the "ghost red edges". Red also clashes
with the rest of the inspector's colour language (pink `(1.0, 0.45, 0.65)` =
selection, gold `(1.0, 0.78, 0.08)` = hover on handles), so it read as an
error/ghost rather than a hover affordance. This is the same family as the
all-red (0001) and ghost-red-block (0002) reports, but on the *face hover*
path, which the analytic-lens *selection* guard (Phase 10) never exercised.

## Root cause

The hover highlight colour was the lone red in the inspector's STEP path
(confirmed: the only `SetColor` reds in `open3d_inspector.py` were these two
lines; everything else is pink selection or gold hover). The diagnosis was
verified by rendering each face's hover overlay off-screen at the recorded
side-view camera: the rim face produced a fat red vertical bar through the
lens, the caps a red sliver — matching the two flagged screenshots.

## Fix

`KrakenOS/UI/open3d_inspector.py`:

* New pure seam `Kraken3DInspector._step_hover_outline_style(has_surface)`
  (staticmethod) returns `(rgb, opacity, line_width)` — the shared hover-gold
  `(1.0, 0.78, 0.08)` for both branches, opacity 0.42 (fill+edges) / 0.9
  (edges-only), line width 4 (down from 6/8). Documents *why* it must never be
  red.
* `_set_step_hover_outline_impl` now pulls its style from that seam instead of
  the inline red literals; the `EdgeVisibilityOff()` call stays gated on the
  fill branch. No change to geometry, clearing, or the `_on_mouse_move`
  trigger — purely the painted style.

Re-rendered the rim/cap hovers: the bar is now gold, blended over the cyan
glass, clearly a highlight and not a red ghost (visually confirmed PNG).

## Tests

* **`validate_open3d_step_face_hover_not_red`** (display-free, 11 checks) —
  pins `_step_hover_outline_style`: both branches return the hover-gold accent
  (large green channel ⇒ not red, low blue ⇒ warm), share one colour, and have
  a sane opacity and a thin (≤5) line width.
* **`validate_open3d_step_face_hover_not_red_snapshot`** (image-snapshot, boots
  its own Xvfb) — imports the first available lens STEP, renders the no-hover
  baseline plus one hover frame per face, and asserts (a) no hover frame adds
  meaningful red over the baseline (worst red stays at the ~9-pixel axis
  marker, limit < 80) and (b) at least one face's highlight visibly changes the
  frame (> 120 px), so the gold tint is actually drawn. The fixer opened the
  PNG and confirmed gold, not red.
* **Regression / end-to-end** — `Phase 12` in
  `validate_open3d_penta_telescope_comprehensive.py`: on a real imported
  optical STEP, builds the hover overlay for a face via
  `_hover_overlay_for_step_face`, sets it through `_set_step_hover_outline`, and
  asserts the live hover-outline actor's property colour is the gold accent
  (green channel high, not red). SKIP-passes when no lens fixture is checked
  out under `attachment/Lens/`.
