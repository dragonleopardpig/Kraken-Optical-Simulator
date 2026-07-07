# 0251 — Navigation cube: long labels still overflow, arrows crowd the cube, hover the arrows

User flag (`attachment/recorded_bug_repros/flag_20260707_165347_376/description.txt`):

> B and M still overflow, F and T still overflow. Can make the arrow space out a bit from
> the cube body? Can make the arrows highlight when hover?

Third pass on the nav cube (after 0249/0250). Three items:

1. **Long words still overflow** — "B and M" = the ends of **BOTTOM**, "F and T" = the ends
   of **FRONT** (and RIGHT). The 0250 shrink (0.15) fit the short words but the 5/6-char
   words still spilled past the flat facet.
2. **Space the arrows out from the cube body** — the orbit triangles sat right on the cube
   silhouette; a rotated corner poked past them.
3. **Highlight the arrows on hover** — 0250 highlighted the cube *facets*; the arrow glyphs
   didn't react.

## Root cause

1. **Overflow.** `vtkAnnotatedCubeActor` uses ONE `SetFaceTextScale` for all six face words,
   sized to the *full* cube face — but the chamfered flat facet is only `_FACE_FRACTION`
   (0.72) of it, and the words differ in length. So any scale that keeps 3-char TOP looking
   right lets 6-char BOTTOM overflow. The scale has to clear the **longest** word, not the
   average.
2. **Crowding.** The cube camera framed the unit cube at parallel scale **0.92** — the cube
   nearly filled the corner viewport. The unit cube's corner radius (0.866) then projected
   to ~0.94 of the viewport half-height, *past* the orbit-triangle tips (~0.90), so a
   rotated corner overlapped the arrows. The arrows live in a separate fixed-size layer, so
   they can't be pushed further out without clipping the small viewport — the cube itself
   had to shrink.
3. **Arrow hover.** `handle_hover` only cell-picked the *cube*; the arrow actors had no
   hover path and no stored base colour to restore.

## Fix (`services/nav_cube_widget.py`)

**Labels.** `_FACE_TEXT_SCALE` `0.15 -> 0.115`, so 6-char BOTTOM (the worst case) sits
inside the 0.72 flat facet; the shorter words just render smaller. (Per-face scaling would
keep short words big, but `vtkAnnotatedCubeActor` has no per-face scale — that's a
billboard-text rewrite, deferred.)

**Arrow standoff.** The cube is now framed **small** inside a slightly larger corner
viewport, so the fixed arrows clear it:
* `_CUBE_FRAME_SCALE = 1.22` (new constant; was the inline `0.92`) — the cube camera's
  parallel half-height; bigger ⇒ cube smaller on screen ⇒ a rotated corner (now ~0.71 of
  the half-height) sits well inside the orbit tips (~0.90).
* `_CUBE_VIEWPORT` `(0.80,0.78,…) -> (0.78,0.75,…)` — a bit more corner area so the shrunk
  cube keeps readable text.

**Arrow hover.** Each arrow's base colour is remembered at build
(`_remember_arrow_color` → `_arrow_base_colors[address]`). `handle_hover` now cell-picks the
**arrows first** (they sit on top): a hit drops any facet highlight and brightens the arrow
via `_set_arrow_hover` (lerp its base colour `_ARROW_HOVER_MIX=0.5` toward white — blue → light
blue, orange → light orange, keeping the glyph's identity), restoring the previously-hovered
arrow and re-rendering only on a change. Miss ⇒ clear the arrow highlight and fall through to
the facet hover. `clear_hover` drops both. `_arrow_entry_for` resolves a picked prop back to
the stored actor (a pick can hand back a different wrapper); `_arrow_kind_for` now delegates
to it. The host + bindings wiring is unchanged from 0250 (the same `hover_motion`
→ `_handle_navigation_cube_hover` path).

## Guard

`validate_open3d_nav_cube_arrows` (display-free, penta **Phase 227**) — drives the arrow
hover against fake actors (each a `GetProperty().SetColor` recorder), no display:

* **A** — `NavigationCube.__init__` exposes the arrow-hover state (`_arrow_base_colors`,
  `_arrow_hover_actor`).
* **B** — `_set_arrow_hover(actor)` brightens that actor toward white and leaves the rest at
  their base colour; returns True and re-renders once.
* **C** — moving the arrow hover restores the previous actor's base colour (exactly one
  brightened at a time).
* **D** — `_set_arrow_hover(None)` / `_clear_arrow_hover()` restores every arrow.
* **E** — re-hovering the same arrow is a no-op (no redundant re-render).
* **F** — the brightened colour is distinctly lighter than the base (sum of channels up by a
  real margin), so the highlight reads.
* **G** — sizing constants: `_FACE_TEXT_SCALE <= 0.13` (6-char word fits) and
  `_CUBE_FRAME_SCALE >= 1.05` (cube framed small enough to clear the arrows).
* **H** — source contract: `handle_hover` picks arrows and calls `_set_arrow_hover`;
  `clear_hover` clears the arrow hover; `_arrow_entry_for` / `_remember_arrow_color` exist.

## Notes

* Verified from an offscreen Xvfb render at a BOTTOM/FRONT/RIGHT orientation
  (`/tmp/nc251_base.png` — the 5/6-char words fit and the arrows stand clear) plus arrow-hover
  snaps (`el_up` and `roll_cw` brighten). Headless can't drive the embedded-VTK `<Motion>`,
  so the live hover feel is still owed an in-app eyeball.
* Arrow hover reuses the click path's arrow picker, so the highlighted arrow is exactly the
  one a click would trigger.
* Still separate (not in this bug): view-change zoom shouldn't depend on the stray
  optical-axis length (`_on_navigation_cube_snap` zoom-to-extent).
