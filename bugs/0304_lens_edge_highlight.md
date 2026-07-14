# 0304 — Measure hover highlights a round imaging-lens edge (not just the box camera)

Follow-up to 0303, flagged recording `flag_20260714_152932_363`. With the 0303 optical-axis object-snap live,
the second Measure arrow now snaps onto the axis (the 165 mm mirror→lens dimension in the screenshot). But:

> *the second arrow can snap on the optical axis, but there is no edge highlight on the Lens Edge, that makes
> me not sure whether snapping to the correct edge or not.*

and a decisive follow-up clue:

> *the Camera edge does highlight, I think only this particular Image Lens edge not highlighting.*

## Root cause — the per-face hover outline is empty for a round lens
The dimension-anchor hover highlight (`_set_dimension_anchor_snap_highlight`) draws the picked **face's**
outline: `_step_feature_pick_for_display_xy` → `_hover_overlay_for_feature` → `_set_step_hover_outline`. A
box-like **camera** STEP has planar faces the ray face-pick resolves cleanly, so its edge lights up. A smooth
round **imaging lens** is displayed from an STL **tessellation**, and the round-lens guard
(`_coarse_step_face_ray_pick_for_display_xy` → `_step_label_is_round_lens_like` → tessellation-patch → `None`)
deliberately returns no face. With `feature is None` the code sets `outline = None`, short-circuiting even the
sphere fallback in `_hover_overlay_for_feature`, so **nothing** highlights on the lens. That is exactly the
camera-vs-lens asymmetry the user saw.

(The 0303 axis-snap still fires — the recorded point is right; only the *visual confirmation* of which edge is
missing.)

## The fix — fall back to the component's own drawn edge/rim geometry
The lens's silhouette edges are already on screen (the imported STEP overlay registers its
`_display_feature_edges` output with `follow_step_label=label`, i.e. into `_step_follow_actor_map[label]`).
When the per-face outline comes back empty for a recognised STEP component, reuse that drawn geometry:

* **`_step_component_edge_outline(label)`** (new, `open3d_inspector.py`) merges the component's already-drawn
  **line** actors from `_step_follow_actor_map` (the solid body — polys, no lines — is skipped), copied so
  recolouring the gold hover outline never mutates the live actors. If a perfectly smooth singlet drew **no**
  sharp edges, it synthesises the rim via `_lens_rim_circle_polyline` (the same view-independent rim the
  round-lens overlay draws) — so round lenses *always* get an edge highlight, not just this barrel.
* `_set_dimension_anchor_snap_highlight` STEP branch: only when the per-face `outline` is `None`/empty does it
  substitute the fallback, keyed `(hit_key, "reanchor-component")` so the merged outline is not rebuilt every
  pixel of hover. The **camera path is untouched** — its face pick is non-empty, so the fallback never runs.

Localised to the dimension-anchor highlight (shared by the Measure hover and the re-anchor pick); no change to
picking, selection, or the STEP overlay draw.

## Files
- `KrakenOS/UI/open3d_inspector.py` — `_step_component_edge_outline` helper; `_set_dimension_anchor_snap_highlight`
  empty-outline fallback.

## Verified (display-free — headless VTK segfaults under Xvfb llvmpipe)
- `bugs/diag_0304_lens_edge_highlight.py` — real VTK actors, no render: an edge+body component yields a
  **line-only** outline (2 pts, 1 line; the solid body's polys excluded); an unknown label → `None`; a smooth
  singlet (only a solid body drawn) → the synthesised **rim circle** (144 pts, 1 line). **ALL PASS**.
- `KrakenOS/UI/validate_open3d_measure_lens_edge_highlight.py` (`run_checks()`) — the same three geometry
  checks plus source asserts (the hover falls back through `_step_component_edge_outline`, gated on an empty
  per-face outline, keyed at component level; the helper uses `_step_follow_actor_map` / `GetNumberOfLines` /
  `_lens_rim_circle_polyline`). **PASSED**.
- Penta **phase 267** (`phase_267_measure_lens_edge_highlight`) delegates to the guard; baseline
  `"267": "pass"`.

## Notes / remaining
- In-app eyeball owed: confirm the gold lens-edge outline appears on Measure hover over the round imaging lens
  (the render/hover path needs a GLX display).
