# 0110 — Right-click on an imported BS-cube face lost its direct per-face promote menu

**Report (2026-06-22):**
> "Now I right click selected surface of the imported BS cube, the direct
> promotion of each face is gone." … "It is now giving the Thickness arrow
> right click option."

Right-clicking a face of the imported beam-splitter (BS) cube used to open the
direct **"Promote and set &lt;face function&gt;"** per-face menu. After the bugs/0108
work it instead pops the **Thickness dimension** arrow menu (turn off /
re-anchor / hide), so the per-face promotion is unreachable.

---

## Root cause — a too-greedy bugs/0108 proximity fallback

The right-click dispatcher
(`Open3DFaceAssignmentService._show_surface_function_context_menu`) tries each
menu hook in order and the first to claim the event `return "break"`s:

1. `_maybe_show_measure_menu`
2. **`_maybe_show_thickness_dimension_menu`**  ← claims the BS-cube click
3. `_maybe_show_quick_estimation_role_menu`
4. `_right_click_pick_context` → the face-promotion menu

Hook 2 claims the event whenever `_thickness_dimension_row_under_cursor(event)`
returns a row. That resolver works in two stages
(`open3d_inspector.py:12446`):

- **Exact hit:** cell-pick the actor; if its key is in
  `_actor_thickness_dimension_map`, return that row. (Correct — a real arrow.)
- **bugs/0108 proximity fallback:** otherwise call
  `_thickness_dimension_row_near_display_xy`, which returns the row of any
  registered Thickness arrow/label whose screen-space segment or billboard sits
  within **26 px** of the click. This was added so an *arrow-less* overlay's thin
  billboard label/leader — which the cell picker can't hit — is still resolvable
  for hiding.

The bug: the proximity fallback fired **even when the cell picker had landed
squarely on a real optical body**. A right-click on the BS-cube face cell-picks
the cube actor (registered in `_actor_step_map`), which is *not* a thickness
actor, so stage 1 fell through to stage 2 — and because a Thickness label/arrow
happened to sit within 26 px of the clicked face, stage 2 returned that arrow's
row. Hook 2 then claimed the event and showed the thickness menu, so the
dispatcher never reached the face-promotion menu.

(The same `_right_click_pick_context` resolves that very cube actor to its
`step_label`/`row_index` via `_actor_step_map`/`_actor_row_map` — so the body is
unambiguously a promotable target; the proximity fallback simply jumped the
queue.)

---

## Fix (`open3d_inspector.py` — `_thickness_dimension_row_under_cursor`)

Gate the proximity fallback on the body actor maps. When the cell picker hit a
promotable body — an actor registered in `_actor_step_map` (imported STEP
overlay) or `_actor_row_map` (optical / STL row) — and it is **not** itself a
thickness-dimension actor, return `None` so the dispatcher falls through to the
face-promotion menu:

```python
if actor_key is not None:
    row_index = self._actor_thickness_dimension_map.get(actor_key)
    if row_index is not None:
        return int(row_index)
    # bugs/0110: a direct hit on a promotable body defers to the face menu.
    if actor_key in (getattr(self, "_actor_step_map", {}) or {}) or actor_key in (
        getattr(self, "_actor_row_map", {}) or {}
    ):
        return None
```

The proximity fallback now only fires for clicks that resolve to **no
promotable body** — empty space or a non-body decoration — which is exactly the
arrow-less-overlay case bugs/0108 was for, so hiding a thin/label-only overlay
still works. A real arrow is still claimed first by the exact-hit branch (even
when an actor is both a body and a thickness arrow, the explicit-arrow branch
wins).

---

## Tests

- `python -m KrakenOS.UI.validate_open3d_step_body_promote_right_click` —
  display-free. Borrows the real unbound `_thickness_dimension_row_under_cursor`
  onto a fake whose proximity fallback always reports a nearby arrow, and checks:
  STEP-overlay body hit → `None` (defer); optical/STL row hit → `None`; direct
  thickness-actor hit → that row; a body that is *also* a thickness actor → the
  arrow row (exact branch wins); empty space → the proximity row (0108 intact);
  non-body decoration → the proximity row (0108 intact); plus a source check the
  gate is present.
- Penta **phase 96** (new; baseline → 97 phases).
- `validate_open3d_thickness_dimension_visibility` (the 0108 guard) still passes.

In-app eyeball owed: headless can't drive the live VTK right-click pick — confirm
in-app that right-clicking a BS-cube face again shows the per-face "Promote and
set …" menu, while right-clicking a Thickness arrow (or near an arrow-less
overlay's label on empty background) still opens the thickness menu.
