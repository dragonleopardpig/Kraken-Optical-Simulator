# 0369 — Measure E/E clicks still not working: hover lag drops clicks + fallback skipped on throw

**Flag:** 20260720_113337_847 (build d6cc8b4c, which HAS the 0367 fix) — "After clicking Measure E/E,
both edges clicked, with or without Alt, are not working." Screenshot: one armed orange edge on the
camera, no dimension. **Status:** FIXED 2026-07-20 (measure-edge guard, phase 306).

## Two root causes (0367 only half-fixed it)

1. **Hover lag drops the clicks (primary).** The 0359 E/E hover resolved the edge on EVERY mouse move
   — `_step_component_edge_outline` merges the whole drawn-edge set + `nearest_display_edge` projects
   every segment via `_world_to_display_2d` + a full `self.render()` — per move. On the 591k-triangle
   camera that is ~hundreds of ms/move, so the cursor lagged and a click's press→release spanned >8 px
   (`drag_threshold_px`), registering as a camera DRAG → `should_pick=False` → `_on_left_button_press`
   never fired → no measurement. This is why "both edges... not working" despite the 0367 completion
   logic being correct.

2. **Point fallback skipped on a throw.** The 0367 fallback sat INSIDE the same `try` as
   `_measure_resolve_edge`, so if the edge resolve *threw* (not just returned None) the fallback never
   ran and the second click stranded.

## Fix

1. **Cheap hover:** the E/E hover now only sets the snap cursor (a widget property — no scene work, no
   render, no edge resolve). The edge is resolved once, on CLICK; the armed first edge stays
   highlighted by its own persistent actor. Moves are cheap → clicks register cleanly.
2. **Bulletproof click:** the point fallback (`_measure_resolve_snap`) lives in its OWN try, after the
   edge resolve's, so it runs even when `_measure_resolve_edge` throws — the second click ALWAYS
   completes (edge→edge, or edge→point on a face).

Tradeoff: the pre-click WYSIWYG edge highlight is gone (it was the lag source); the armed edge is
still highlighted after the first click. A cached/throttled live preview is a possible future
enhancement. Guard: the E/E hover must NOT resolve edges per move; the click fallback must be in its
own try.
