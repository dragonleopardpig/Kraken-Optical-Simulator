# 0150 — Right-click "Re-anchor" always moves the RIGHT (end) endpoint, ignoring which arrowhead was clicked

## Status

DOCUMENTED, fix not yet applied (logged as the next fix; in-app-only repro). Found
while eyeballing bugs/0149.

## Symptom

There are **two** ways to start a dimension re-anchor and they behave differently:

> *"I use right click pop up menu then select reanchor, it behave differently. I
> point to the Left Arrow, right click, select reanchor — the right arrow will
> reposition itself to the end of the left arrow first, effectively zero length,
> then slide. The left arrow follows. Ctrl-left click works as expected however."*

- **Ctrl-left-click** a dimension arrow → re-anchors the endpoint **nearest the
  cursor** (correct — bugs/0149 verified this path).
- **Right-click → "Re-anchor to a surface/edge…"** → **always re-anchors the RIGHT
  (`end`) endpoint**, no matter which arrowhead you pointed at. Right-clicking the
  LEFT arrow still grabs the RIGHT end; that end then snaps toward the cursor (which
  is sitting on the left arrow) → the dimension collapses to ~zero length, then the
  whole arrow tracks the mouse. Looks broken / "left arrow can't be re-anchored from
  the menu".

## Root cause

The menu command hardcodes the endpoint. `_show_thickness_dimension_menu`
(`KrakenOS/UI/open3d_inspector.py:13639`) wires:

```python
menu.add_command(
    label="Re-anchor to a surface/edge…",
    command=lambda idx=int(row_index): self._begin_dimension_anchor_pick_for_row(idx),
)
```

`_begin_dimension_anchor_pick_for_row(self, row_index, endpoint="end")`
(`open3d_inspector.py:13672`) **defaults `endpoint="end"`**, and the menu never
passes one — so the menu path **always** picks `moving=end`, `fixed=start`.

The Ctrl-click path does **not** have this bug: `_dimension_anchor_state_from_
current_pick` (`open3d_inspector.py:3596–3604`) projects both endpoints to display
space and chooses `endpoint = "start" if d_start <= d_end else "end"` from the
**cursor proximity**. The two entry points disagree because only one consults the
click location.

The "zero length first" artifact is a direct consequence: `_begin_dimension_anchor_
pick_for_row` immediately calls `_apply_dimension_anchor_pick_motion()`
(`open3d_inspector.py:13713`), which slides the **moving** (wrongly: right) endpoint
toward the cursor — and the cursor is on the LEFT arrow — so the right end jumps left
and the span collapses before the user moves the mouse.

## Fix (proposed — not yet applied)

Make the menu path match the Ctrl-click path: derive the endpoint from the
right-click position instead of defaulting to `"end"`.

`_show_thickness_dimension_menu(event, row_index)` already has the click `event`
(it uses `event.x_root`/`event.y_root` for the popup) and the inspector already has
the proximity helpers (`_world_to_display_2d`, and `_point_segment_distance_2d` /
the `_dimension_anchor_state_from_current_pick` proximity block). Compute the nearer
endpoint at menu-build time and forward it:

```python
endpoint = self._nearer_dimension_endpoint_for_event(event, int(row_index))  # "start"|"end"
menu.add_command(
    label="Re-anchor to a surface/edge…",
    command=lambda idx=int(row_index), ep=endpoint:
        self._begin_dimension_anchor_pick_for_row(idx, endpoint=ep),
)
```

where the new `_nearer_dimension_endpoint_for_event` reuses the **same** 2-D
proximity logic as `_dimension_anchor_state_from_current_pick` (look up the row's
drag record via `_thickness_dimension_actor_map` → `_thickness_dimension_drag_map`,
project `start`/`end` with `_world_to_display_2d`, compare to the click `(x, y)`,
default `"start"` when a projection is unavailable — matching line 3600). No change
to `_begin_dimension_anchor_pick_for_row` itself; it already honours the passed
endpoint and feeds the bugs/0149 per-endpoint store.

Alternative (more explicit UX): replace the single menu item with two —
"Re-anchor left end…" / "Re-anchor right end…" — each passing its endpoint. The
proximity approach is preferred because it matches the Ctrl-click feel.

## Guard (to add with the fix)

Display-free `run_checks()`: drive a fake inspector carrying a row drag record
(known `start`/`end` world points) + a stubbed `_world_to_display_2d`, then assert
the menu's chosen endpoint == `"start"` for a click near the left projection and
`"end"` near the right (and the default when a projection is None). Pin the menu
command actually forwards that endpoint into `_begin_dimension_anchor_pick_for_row`
(source marker that the call is no longer the bare `(idx)` form). Add as the next
penta phase (139) + hand-edit the baseline.

## Note

Both entry points share the downstream store/draw/persist chain from bugs/0149, so
once the menu forwards the right endpoint, independent per-endpoint anchoring +
feature tracking come for free. This is purely the **entry-point endpoint
selection** disagreeing — no change to the 0149 data model.
