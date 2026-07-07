# 0250 — Navigation cube: text still overflows, roll arc too long, add hover highlight

User flag (`attachment/recorded_bug_repros/flag_20260707_162641_923/description.txt`):

> Text still overflow. The curve segment of the rotation arrow is too much. Refer to
> attachment/freecad.png for reference.

Follow-up (same session): *"In addition, mouse hover each Cube selectable face or edge
or corner should highlight."*

This is a second pass on the nav cube after bugs/0249 — the 0249 shrink/curve wasn't
enough, plus a new hover ask. Three items:

1. **Text still overflows the facet** — 0249 took the label scale `0.42 -> 0.22`, still
   too big; a 5-char word (FRONT/RIGHT) spilled past the flat face.
2. **Roll arc too long** — 0249's curved roll handle swept ~230° (nearly a full loop);
   FreeCAD's is a short ~110° arc flanking the top. Shorten it.
3. **Hover highlight** — hovering any clickable facet (face / edge / corner) should
   highlight it so the user sees the click target before clicking.

## Root cause

1. **Text.** `vtkAnnotatedCubeActor.SetFaceTextScale` sizes the letters to the FULL cube
   face, but the chamfered flat facet is only `_FACE_FRACTION` (0.72) of it. `0.22` is
   still ~30 % of the face, so a wide word ran to the (now cut-away) edge. The scale has
   to stay well under `_FACE_FRACTION` to fit.
2. **Arc.** The roll-arc sweep in `_build_arrow_renderer` was `(-34° -> 196°)` and
   `(214° -> -16°)` — ~230° each, a near-complete circle. Nothing anchored it to
   FreeCAD's short flanking arc.
3. **Hover.** The cube had no passive-hover path at all — only the click path
   (`handle_left_press`). Nothing recoloured a facet on `<Motion>`.

## Fix

**Text (`services/nav_cube_widget.py`).** `_FACE_TEXT_SCALE` `0.22 -> 0.15` — comfortably
inside the 0.72 flat facet, so FRONT/RIGHT/TOP fit with margin.

**Roll arcs (`_build_arrow_renderer`, `_roll_arrow_actor`).** Sweep shortened to a
FreeCAD-style short arc: `roll_ccw = (cx -0.46, cy 0.88, 18° -> 128°)`,
`roll_cw = (0.46, 0.88, 162° -> 52°)` — ~110° each, tucked at the top flanking the
up-orbit triangle. Glyph also scaled down to match (`radius,width 0.28,0.10`; `n=14`
arc segments; `head_len,head_half 0.20,0.13`). Still a curved ribbon + tangential
arrowhead (the 0249 rotation-glyph shape), just shorter.

**Hover highlight (widget + host + bindings).** The cube mesh already carries a per-cell
colour array (bugs/0249). Hover mutates it:

* `_build_chamfered_actor` now keeps the `vtkUnsignedCharArray` (`self._cell_colors`) and
  each cell's base RGB (`self._base_colors`).
* `handle_hover(x, y)` cell-picks the cube (same `vtkCellPicker` as the click path); the
  hovered cell is recoloured to `_COLOR_HOVER` (bright blue) via `_set_hover`, which
  restores the previously-hovered cell's base colour and re-renders **only on a change**
  (a bare move over one facet doesn't spin the render loop). `clear_hover()` drops it.
* Host `Kraken3DInspector._handle_navigation_cube_hover` reads the interactor event
  position (like the click companion) and forwards to `cube.handle_hover`;
  `_clear_navigation_cube_hover` forwards the clear.
* `Open3DMouseBindingsService.hover_motion` (bound to `<Motion>`) pushes the live cursor
  into the interactor (`set_event_info`), asks the cube first, and **returns early** when
  the cube is highlighting (so the scene's thickness-handle hover doesn't also fire);
  otherwise it clears the cube highlight and falls through to the normal scene hover.

## Guard

`validate_open3d_nav_cube_hover` (display-free, penta **Phase 226**) checks — with a tiny
fake per-cell colour array standing in for VTK, so no display is needed:

* **A** — a fresh `NavigationCube.__init__` exposes hover state (`_cell_colors`,
  `_base_colors`, `_hover_cell == -1`).
* **B** — `_set_hover(cid)` recolours cell `cid` to `_COLOR_HOVER` and leaves the rest at
  their base colour.
* **C** — moving the hover (`_set_hover(other)`) restores the previous cell's base colour
  and highlights the new one (exactly one highlighted at a time).
* **D** — `_set_hover(-1)` / `clear_hover()` restores everything (no cell highlighted).
* **E** — re-hovering the SAME cell is a no-op (no redundant re-render).
* **F** — `_COLOR_HOVER` is visually distinct from every base kind colour
  (face/edge/corner), so the highlight actually reads.
* **G** — `_FACE_TEXT_SCALE <= 0.18` (comfortably inside `_FACE_FRACTION`) and each roll
  arc sweep is a short arc (`|a1 - a0| <= 150°`), so a future edit can't silently regrow
  the label or the loop.
* **H** — source contract: the widget defines `handle_hover`/`clear_hover`/`_set_hover`
  and stores `_cell_colors`/`_base_colors`; the host defines
  `_handle_navigation_cube_hover`/`_clear_navigation_cube_hover`; the bindings
  `hover_motion` calls `_handle_navigation_cube_hover` before the scene hover.

## Notes

* Verified from an offscreen Xvfb render: base (`/tmp/nc_base_z.png`) shows the short
  roll arcs + fitted labels; hover-face (cell 4 = +Z FRONT) and hover-corner
  (cell 18 = (1,1,1)) render the hovered facet bright blue. Headless can't drive the
  embedded-VTK `<Motion>`, so the live hover feel is still owed an in-app eyeball, but the
  pick + recolour math is proven headless.
* Hover reuses the click path's `vtkCellPicker`, so a highlighted facet is exactly the one
  a click would snap — no second classification path to drift.
* Separate follow-on (not in this bug): view-change zoom level shouldn't depend on the
  stray optical-axis length (`_on_navigation_cube_snap` zoom-to-extent includes the long
  axis overlay). Tracked for a later fix.
