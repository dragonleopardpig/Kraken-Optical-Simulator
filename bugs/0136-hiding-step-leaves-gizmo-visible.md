# 0136 — hiding a STEP element leaves its move/rotate gizmo visible

## Symptom

Recording `recording_20260625_073038.json`, flag `flag_20260625_072723_861`:

> *"Hiding LED leave the gizmo visible."*

The user hid the LED in the Scene Components browser. The body disappeared, but its
selection **gizmo** — the green rotate ring and the translate arrows — stayed on screen,
floating where the LED used to be (visible in the flag screenshot).

## Root cause

`open3d_inspector.py::set_step_label_hidden`, hide branch:

```python
self._hidden_step_labels.add(label)
self._set_actor_keys_visible(self._all_actor_keys_for_step_label(label), False)
self.render()
```

`_all_actor_keys_for_step_label(label)` collects the body, the feature edges, the follow
actors, and the **rotate-ring** handles (`_actor_step_rotate_map`) — but **not** the
**translate arrows** (`_actor_step_translate_map`) nor the **ring visual**
(`_actor_step_rotate_visual_keys`). So:

- the translate arrows + ring visual were never even touched by the hide, and
- the rotate-ring handles were only set *invisible* (`SetVisibility 0`) — the handle
  *objects* survived in the maps, still pickable.

The gizmo lifecycle is owned by the rotation-handle service + `_reconcile_step_rotation_handles`
(which is what selection changes call), **not** by the body visibility sweep. `set_step_label_hidden`
simply never told the gizmo to reconcile, so it outlived the body. (Compare bugs/0027, which
stopped a *hidden* element from *gaining* a gizmo on select; this is the mirror case — a
*shown* gizmo not dropping when its element is hidden.)

## Fix

Reconcile the rotation handles in the hide branch (`open3d_inspector.py`):

```python
self._set_actor_keys_visible(self._all_actor_keys_for_step_label(label), False)
self._reconcile_step_rotation_handles(self._selected_step_labels)
self.render()
```

`_reconcile_step_rotation_handles` builds `visible = selected − hidden`; the label was just
added to `_hidden_step_labels`, so it drops out of the target and the service's
`remove_for_label` deletes its **full** gizmo (`_actor_step_rotate_map`,
`_actor_step_translate_map`, `_actor_step_rotate_visual_keys`, `_actor_step_follow_map`).
Other selected, visible elements keep their handles (`ensure_for_label` is idempotent).

The hide/unhide round-trip stays symmetric without extra code: the unhide branch's
`refresh_imported_step_overlay(label)` already re-adds the gizmo when the label is the
selected step (`open3d_step_overlay_refresh.py:223` gates `_add_step_rotation_handles` on
`_selected_step_label == label`).

## Test

- `KrakenOS/UI/validate_open3d_hidden_step_drops_gizmo.py::run_checks` — display-free:
  - **Logic**: the real `_reconcile_step_rotation_handles`, run against a stub, drops a
    hidden label from the reconcile target (`{led(hidden), optical}` → `{optical}`) and
    clears a hidden-only selection to the empty set.
  - **Source**: `set_step_label_hidden`'s hide branch calls
    `_reconcile_step_rotation_handles(self._selected_step_labels)` (and it is in the hide
    branch, not the unhide one).
  - **Mechanism**: `remove_for_label` clears `_actor_step_translate_map` and
    `_actor_step_rotate_visual_keys`, so the translate arrows + ring visual go with the body.
- Penta phase **126**.

## Status

Fixed; guard green standalone and in the penta harness (phase 126, display-free). In-app
eyeball owed — the embedded-VTK gizmo cannot be rendered headless; the user should confirm
that hiding the LED (with it selected) removes the ring + arrows, and unhiding it while still
selected brings the gizmo back.
