# 0135 — an empty-space click cancels the armed clear-aperture pick

## Symptom

Recording `recording_20260625_073038.json`, flag `flag_20260625_072827_750`:

> *"unable to deselect components."*

The user had armed **Set Clear Aperture** (right-click → "Set Clear Aperture (pick window
face)…", bugs/0134) on the LED. Once in that one-shot pick mode they could not get out:
clicking empty space — the universal "deselect / never mind" gesture — did nothing but
re-print the *"click the LED body's clear-aperture window face"* nag. Escape is bound but
the embedded-VTK canvas usually owns keyboard focus, so it rarely reaches the handler. The
modal trapped them. (All four flags in this session were filed while still stuck in
`step_clear_aperture_pick` mode — this trap is why.)

## Root cause

`open3d_interaction.py::_on_left_button_press`, the CA-pick guard block:

```python
if self._step_clear_aperture_pick_mode and (
    step_label is None
    or str(step_label).strip().lower() != ...pick_label...
):
    self.status_var.set("Set Clear Aperture: click the ... window face.")
    self.render()
    return
```

Any click that is **not** on the wanted body — including a click in empty space
(`actor_key is None`) — fell straight into the nag-and-return. There was no escape hatch
for "clicked nothing". Every other modal pick in this handler already has one: the
Center-Row→Optical-Axis block a few lines up does
`if actor_key is None and self.cancel_active_3d_operation(): return`, and
`cancel_active_3d_operation()` both clears the CA-pick flags
(`_step_clear_aperture_pick_mode`/`_label`) and clears the Open 3D selection. The CA block
simply never adopted that precedent.

## Fix

Prepend the same empty-space escape to the CA-pick block
(`open3d_interaction.py`):

```python
if actor_key is None and self.cancel_active_3d_operation():
    return
```

- A click in **empty space** (`actor_key is None`) cancels the armed pick and clears the
  selection — the user is no longer trapped.
- A click on the **wrong body** (`actor_key` set, `step_label` ≠ the pick label) still just
  nudges, because they are aiming at the scene, not bailing out.

`cancel_active_3d_operation()` already lists the CA-pick mode in
`_active_3d_operation_labels()`, so it takes the active-op path: it resets
`_step_clear_aperture_pick_mode`, refreshes, clears the selection, and returns `True`.

## Test

- `KrakenOS/UI/validate_open3d_clear_aperture_pick_cancel.py::run_checks` — display-free:
  - **Cancel contract**: `cancel_active_3d_operation` resets `_step_clear_aperture_pick_mode`
    and `_active_3d_operation_labels` reports the CA-pick flag (so an empty-space click takes
    the cancel path, not the no-op deselect).
  - **Source contract**: the CA-pick block in `_on_left_button_press` contains the
    `actor_key is None and self.cancel_active_3d_operation()` escape *before* the status nag,
    and it is gated on `actor_key is None` (a wrong-body click still nudges).
- Penta phase **125**.

## Status

Fixed; guard green standalone and in the penta harness (phase 125, display-free). In-app
eyeball owed — the embedded-VTK click cannot be driven headless; the user should confirm
that, while Set-Clear-Aperture is armed, a click on empty canvas exits the mode and clears
the selection, while a click on the wrong body still only nudges.
