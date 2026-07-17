# bugs/0334 — Left-click on a highlighted CA opening must select ONLY the opening, persistently

**Flag 2 of a three-flag recording** (`recording_20260717_121101.json`, imported
vendor LED): *"Left click on the highlighted CA edge causing the whole STEP
selected. Should select only the highlighted edge."* Plus the follow-up
directive: *"Left click selection should make the selection permanent until user
click elsewhere to disable it. It is then easier for user to right click."* And
the constraint: *"still want [the] gizmo to move the body, but activate it with
some other toggle."*

Flag 1 (*"CA highlighted."*) confirms the 0327–0331 hover work is present and
good; this bug is the **click** step that follows it.

## The defect

The plain hover already resolves the clear-aperture (CA) opening and paints its
rim (0327–0331). But a **left-click** dropped that detection on the floor: the
idle STEP-body branch in `_on_left_button_press` (`open3d_interaction.py`) ran
`select_step_component(step_label)` + `show_step_rotation_handler(step_label)` —
i.e. it selected the **whole STEP body** and armed the move/rotate gizmo,
regardless of the fact that the cursor was over a see-through opening. The user
saw the entire LED light up and a gizmo appear, instead of the single rim.

## Fix — a persistent, opening-only selection

### New inspector state + actor (`open3d_inspector.py`)

A dedicated **persistent** selection distinct from the transient gold hover
outline (which is keyed by `_hover_step_cell_key` and replaced on every hover):

- `_selected_opening_outline_actor` + `_selected_opening_label` /
  `_selected_opening_face_id` / `_selected_opening_center` /
  `_selected_opening_normal`.
- `_set_selected_step_opening(label, face_id, center, normal, outline_mesh)` —
  stashes the geometry and draws a distinct **cyan** rim actor (opaque, width 5,
  `RenderLinesAsTubesOn`, `PickableOff`), mirroring `_set_step_hover_outline_impl`
  but in a separate slot so it **survives hover changes**.
- `_clear_selected_step_opening()` — removes the actor + clears state, returns
  whether anything changed (so `_clear_open3d_selection` folds it into its
  `changed` bookkeeping).
- `_has_selected_step_opening()` — true when a rim is pinned.

`_clear_open3d_selection` now calls `_clear_selected_step_opening(render=False)`,
so **every** deselect path (empty-click, body-click, mode changes) drops the
pinned rim — that is the "click elsewhere to disable it" behaviour.

### Left-click routes an opening away from the body path (`open3d_interaction.py`)

`_select_step_opening_from_feature(step_label, feature_pick)` extracts the
opening centre (`surface_center`), normal (`feature[2]`) and rim outline
(`feature[1]`), pins them via `_set_selected_step_opening`, **also** calls
`_remember_selected_step_feature` (so the right-click CA menu / axis-snap keep
their feature context), sets a status line and returns `True`. Non-finite
geometry returns `False`.

The idle STEP-body branch gains, right after it computes `feature_pick`:

```python
if isinstance(feature_pick, dict) and feature_pick.get("opening"):
    if self._select_step_opening_from_feature(step_label, feature_pick):
        return
```

The early `return` skips `select_step_component` **and**
`show_step_rotation_handler` — so an opening click never selects the body and
never arms the gizmo.

## The move gizmo stays — on the existing toggle

Per the constraint, the body move/rotate gizmo is **not** removed. It is already
gated by the **"Move/Rotate handles"** checkbox
(`show_rotation_handles_var` → `_show_rotation_handles`), which controls whether
the handle actors are drawn. That checkbox **is** the "other toggle": with it on,
the user still gets handles on a body selection; an opening click simply doesn't
select a body, so it doesn't draw them. No new control was invented.

## Staleness after a snap

A CA snap (0333) moves the body, which would leave the pinned rim floating at the
old world position. `_apply_step_feature_center_axis_pick` now calls
`_clear_selected_step_opening(render=False)` in its cleanup tail, so the stale
rim is dropped as the body moves.

## Guard & regression

`KrakenOS/UI/validate_open3d_led_ca_persistent_select.py` (penta **Phase 293**),
display-free, **Section 1**:
- inspector state round-trip: set stores label/face/centre, `_has_…` flips
  true→false across a clear, a second clear is idempotent;
- `_select_step_opening_from_feature` pins finite geometry (centre = surface
  centre, remembers the feature, status names the opening) and returns `False`
  for a non-finite centre (falls through to the body path);
- source contract: the left-click branch detects `feature_pick.get("opening")`
  and routes to `_select_step_opening_from_feature` **before**
  `select_step_component`.

## Files touched
- `KrakenOS/UI/open3d_inspector.py` — persistent-opening state + actor
  (`_set_/_clear_/_has_selected_step_opening`), `_clear_open3d_selection` hook,
  and the CA-snap-apply staleness clear.
- `KrakenOS/UI/services/open3d_interaction.py` —
  `_select_step_opening_from_feature` + the opening branch in
  `_on_left_button_press`.
- `KrakenOS/UI/validate_open3d_led_ca_persistent_select.py` — new guard (Section 1).
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — Phase 293.
- `tools/penta_validator_baseline.json` — Phase 293 = pass.
