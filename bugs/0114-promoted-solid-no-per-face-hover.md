# 0114 — A promoted optical solid loses its per-face hover highlight

**Report (2026-06-23, flag_20260623_074821_585):**
> "After BS promoted, the whole body highlight pink, mouse over each surface does
> not highlight it."

The flag bundle was recorded after promoting the beam-splitter cube to an optical
solid. Ground truth from `state.json`: idle mode, nothing selected
(`picked_row_index = null`, `picked_row_indices = []`, `selected_step_label =
null`), all handle counts 0, `hover_outline_bounds = []`, yet `promoted_solid_rows`
holds the BS cube at **row 1** (BK7, 55 mm thick, 78 mm diameter). The screenshot
shows the cube as plain glass — the "whole body pink" is the **post-promote
selection** (the just-promoted row becomes the active selection, painted pink); by
capture time the user had moved off it, so nothing is selected. The actionable
defect is the second half: **mousing over the promoted body produces no per-face
gold outline.**

---

## Root cause — promoted bodies are rows, and idle hover only face-hovers overlays

A promoted optical solid is a CAD/STL **row** (`_actor_row_map`), not a STEP
**overlay** (`_actor_step_map`). The idle-hover branch in `open3d_interaction.py`
(`_on_passive_motion`, the `target_label is None and not axis_pick_any` block) runs
per-face hover **only for STEP overlays**:

- it picks rotation/move handles (`_passive_hover_pick_rotation_handle`), then
- looks up `_actor_step_map` (camera/led overlays) and, failing that, falls back to
  `_step_feature_pick_any_for_display_xy` — **both STEP-overlay-only**.

There was no branch for a promoted row, so each face of a promoted body stayed
un-highlightable on idle hover. (The machinery to do it already existed —
`_row_face_pick_any_for_display_xy` + `_hover_overlay_for_row_face` — but was only
wired into **Center Row → Optical Axis** mode, not idle hover.)

The "stays pink" is not a separate desync: it is the ordinary selection paint of
the freshly promoted row. The user's grievance is that they could not then inspect
the body's individual faces.

---

## Fix — mirror Center-Row's per-face hover into the idle-hover path

`KrakenOS/UI/services/open3d_interaction.py`, idle-hover branch: when no STEP
overlay claims the cursor (`step_label is None`), run the **same** file-backed
row-face pick Center-Row mode uses and build the gold outline:

```python
if step_label is None:
    row_any = self._row_face_pick_any_for_display_xy((x, y))
    if isinstance(row_any, dict):
        row_index = int(row_any["row_index"])
        face = getattr(row_any.get("row_face_pick"), "face", None)
        if isinstance(face, dict):
            ...
            outline = self._hover_overlay_for_row_face(row_index, face)
            self._set_step_hover_outline(outline, hover_key)
            self._update_hover_status(f"S{row_index} {row_name} {face_id} face", ...)
            return
```

`_row_face_pick_any_for_display_xy` iterates the **file-backed** rows
(`_file_backed_stl_row_at`), so a promoted optical solid (which keeps its source
STL path) is among the candidates; `_hover_overlay_for_row_face` builds the planar
outline from the body's STL triangles at the live runtime transform — so the gold
outline lands **on** the live body face.

Selection is **preserved**: unlike Center-Row mode (which clears the row highlight
on a face hover for its pick workflow), the idle branch does **not** call
`_set_row_highlight(None)`. A selected (pink) promoted body keeps its selection and
the gold face outline simply layers on top — hovering never deselects.

Blast radius is tight: the new branch only fires on idle hover, only when no STEP
overlay/handle is under the cursor, and only when a file-backed row-face ray pick
hits. Plain (non-CAD) surface rows are not file-backed, so they are unaffected.

---

## Tests

- `python -m KrakenOS.UI.validate_open3d_promoted_solid_face_hover` — two parts:
  - `run_checks()` (display-free, 5 assertions): the idle-hover path wires
    `_row_face_pick_any_for_display_xy` → `_hover_overlay_for_row_face` under the
    `step_label is None` branch (bugs/0114); the new branch preserves the selection
    (no `_set_row_highlight`); the inspector exposes the three row-face helpers;
    `_row_face_pick_any_for_display_xy` iterates file-backed rows and returns a
    `row_face_pick`; a planar face's outline is non-empty and sits **on** the face
    plane.
  - `render_face_outline_proof()` (geometry/PNG snapshot): a promoted cube-face quad
    yields a gold outline that encloses the 78 mm face footprint with z-gap < 1e-3
    mm (the highlight lands on the body).
- Penta **phase 104** (new; baseline → 105 phases) runs `run_checks()` only (no
  rendering — keeps the validator marathon headless-safe).

In-app eyeball owed: headless can't drive a live VTK hover pick. Confirm in-app
that, after promoting the beam-splitter cube, hovering each face of the promoted
body draws the gold outline on that face (and that a selected/pink promoted body
still shows the per-face gold outline on hover).
