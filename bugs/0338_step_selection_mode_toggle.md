# bugs/0338 — "Move/Rotate whole body" checkbox becomes a selection-MODE switch

**Flag 2 of `recording_20260717_130459.json`**, which started as a question and
became a directive across three messages:

> "Left click a Face will cause whole body selected, is this intended?"

> "I think any click on a STEP will either pick edge or surface. So in order to
> select whole body with gizmo, the current checkbox should also disable selection
> of edges and surface once checked in addition to showing gizmo."

> "that means with the checkbox unchecked, user can either select face or edge, but
> not whole body."

It also completes the earlier constraint (bugs/0334): *"still want [the] gizmo to
move the body, but activate it with some other toggle."*

## The defect

After bug 0334, a left-click on a highlighted clear-aperture **opening** pins only
that opening. But a left-click on any other **face** of a STEP still ran the idle
body branch in `_on_left_button_press` (`open3d_interaction.py`) —
`select_step_component(step_label)` + `show_step_rotation_handler(step_label)` —
so the whole body lit up and the move/rotate gizmo appeared. The user wants a
**face** click to select only that face, and the whole-body + gizmo behaviour to be
an explicit, opt-in mode.

## Fix — the checkbox is now a selection-mode switch

The existing **"Move/Rotate handles"** checkbox (`show_rotation_handles_var`,
`_show_rotation_handles()`) is repurposed and relabeled **"Move/Rotate whole body"**:

- **UNCHECKED** (the new **default**) — a left-click on a STEP pins a **face** or a
  **clear-aperture opening** as a *persistent* selection. **No** whole-body select,
  **no** gizmo. This is the primary LED interaction, so it works out of the box.
- **CHECKED** — a left-click selects the **whole body** and shows its Move/Rotate
  handles; face/edge picking is **disabled**.

### Persistent face selection (`open3d_inspector.py`)

The surface analogue of the 0334 opening pin, in its own slot so it survives hover
changes:

- state `_selected_face_outline_actor` + `_selected_face_label` / `_selected_face_id`
  / `_selected_face_center` / `_selected_face_normal`;
- `_set_selected_step_face(label, face_id, center, normal, outline_mesh)` — stashes
  the geometry and draws a distinct **cyan** face outline (opaque, width 5,
  `RenderLinesAsTubesOn`, `PickableOff`), mirroring the pinned-opening rim so the
  pinned selection reads apart from the transient gold hover;
- `_clear_selected_step_face()` — removes the actor + clears state, returns whether
  anything changed;
- `_has_selected_step_face()` — true when a face is pinned.

`_clear_open3d_selection` now also calls `_clear_selected_step_face(render=False)`,
so **every** deselect path (click-elsewhere, mode change) drops the pinned face —
the same "click elsewhere to disable it" behaviour as the opening.

### The mode gate (`open3d_interaction.py`)

`_select_step_face_from_feature(step_label, feature_pick)` extracts the face centre
(`surface_center`), normal and outline, pins them via `_set_selected_step_face`,
**also** `_remember_selected_step_feature` (so the right-click face menu / axis snaps
keep their context), sets a status line, returns `True`; non-finite geometry returns
`False`.

The idle STEP branch now gates on the checkbox:

```python
if not self._show_rotation_handles():          # UNCHECKED: face/edge only
    if isinstance(feature_pick, dict) and feature_pick.get("opening"):
        if self._select_step_opening_from_feature(step_label, feature_pick):
            return
    if self._select_step_face_from_feature(step_label, feature_pick):
        return
    self.status_var.set("Could not resolve a face ...")   # never falls to body
    return
# CHECKED: whole-body select + gizmo (face/edge picking disabled)
...
self.editor.select_step_component(step_label)
self.show_step_rotation_handler(step_label, additive=shift_additive)
```

When unchecked, the face/opening pin returns **before** `select_step_component`, so
the body is never selected and no gizmo is drawn. When unchecked and no face
resolves, it stays in face/edge mode with a status hint rather than falling through
to a body select.

### Mode flips reset the selection (`open3d_inspector.py`)

`_toggle_rotation_handles` now calls `_clear_open3d_selection(render=False)` first, so
a pinned face/opening (meaningless in body mode) and a selected body + gizmo
(meaningless in face/edge mode) never cross when the user flips the checkbox. It
keeps removing the gizmo handle actors on uncheck, and gives a mode-appropriate
status.

## Why default UNCHECKED

The whole 0327–0337 arc made the CA opening the primary thing to select, and the
user explicitly asked (0334) to *"activate [the gizmo] with some other toggle"* —
i.e. body-move should be opt-in. Defaulting the box unchecked means a fresh app
picks faces/openings on click (what the user is doing), and the gizmo is a
deliberate check away. Validators that need the gizmo already set
`show_rotation_handles_var.set(True)` explicitly, so the flipped default doesn't
disturb them.

## Guard & regression

`KrakenOS/UI/validate_open3d_step_selection_mode_toggle.py` (penta **Phase 294**),
display-free:
- inspector persistent-face state round-trip (set stores label/face/centre,
  `_has_…` flips true→false across a clear, a second clear is idempotent);
- `_select_step_face_from_feature` pins finite geometry (centre = surface centre,
  remembers the feature, status names the face) and returns `False` for non-finite;
- source contracts: the idle branch gates on `_show_rotation_handles()` and routes
  the face/opening pin **before** `select_step_component`; `_clear_open3d_selection`
  folds in `_clear_selected_step_face`; `_toggle_rotation_handles` resets the
  selection on a flip; the checkbox defaults **unchecked**.

## Files touched
- `KrakenOS/UI/open3d_inspector.py` — persistent-face state + actor
  (`_set_/_clear_/_has_selected_step_face`), `_clear_open3d_selection` hook,
  `_toggle_rotation_handles` reset, checkbox default flipped to `value=False`.
- `KrakenOS/UI/services/open3d_interaction.py` —
  `_select_step_face_from_feature` + the checkbox-gated idle branch.
- `KrakenOS/UI/panels/open3d_top_controls.py` — checkbox relabeled
  "Move/Rotate whole body".
- `KrakenOS/UI/validate_open3d_step_selection_mode_toggle.py` — new guard.
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — Phase 294.
- `tools/penta_validator_baseline.json` — Phase 294 = pass.
