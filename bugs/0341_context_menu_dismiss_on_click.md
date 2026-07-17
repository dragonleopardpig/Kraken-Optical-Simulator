# bugs/0341 — right-click popup won't dismiss when you click elsewhere

**Flag `flag_20260717_142431_888`** (latest live test, imported LED):

> "clicking elsewhere still not destroying right click pop up menu."

## The defect

bugs/0336 tried to make a posted right-click menu dismiss on a click-elsewhere by
binding the VTK Tk widget's mouse buttons to a teardown callback:

```python
# _popup_context_menu (bugs/0336)
for sequence in ("<Button-1>", "<Button-2>", "<Button-3>"):
    bind_id = widget.bind(sequence, _dismiss, add="+")   # add-on handler
```

But the same widget already has the app's **primary** press handlers bound first
(`open3d_mouse_bindings.py`):

```python
self._vtk_widget.bind("<ButtonPress-1>", left_press)
self._vtk_widget.bind("<ButtonPress-2>", middle_press)
self._vtk_widget.bind("<ButtonPress-3>", right_press)
```

`left_press` / `middle_press` / `right_press` **`return "break"`** on nearly every
path (pick, orbit, nav-cube, carry, …). In Tk, a binding that returns `"break"`
**aborts the rest of the binding script for that tag** — including the `add="+"`
`_dismiss` handler bound afterward. So the dismiss callback never ran, and the
popup stuck exactly as the user reports.

The flag's own diagnostics confirm the right-click resolved the LED normally
(`hovered_label='led'`, `vtk_step_label='led'`); the popup posted fine — it just
would not go away on the next click.

## Fix — dismiss from the primary press handlers (`open3d_mouse_bindings.py`)

The primary press handlers always fire on a scene click, so they are the reliable
place to tear the popup down. `left_press` and `middle_press` now dismiss any live
context menu at the very top, before any pick / orbit / nav-cube snap:

```python
def left_press(event):
    record_mouse("mouse_press", event, 1)
    set_event_info(event)
    self._face_assignment_service()._dismiss_active_context_menu()   # bugs/0341
    ...
```

(A right-click elsewhere already replaced the popup — `_popup_context_menu` calls
`_dismiss_active_context_menu` before posting the new one.) The 0336 widget-button
binds stay as a harmless backup for any press path that does *not* `"break"`, and
the `_popup_context_menu` docstring now states the real mechanism.

## Why 0336's guard didn't catch it

`validate_open3d_led_ca_persistent_select.py` (Phase 293) asserted the *primitive*
(`_dismiss_active_context_menu` unposts) and the *wiring* (`_popup_context_menu`
binds), but never that a real **click handler invokes** the dismiss. It guarded
the instance, not the invariant — so the shadowed bind passed the test while the
live behaviour failed.

## Guard & regression

`KrakenOS/UI/validate_open3d_context_menu_dismiss_on_click.py` (penta **Phase 297**),
display-free:
- source contract: BOTH `left_press` and `middle_press` closures call
  `_dismiss_active_context_menu`;
- behavioural: the `_dismiss_active_context_menu` primitive unposts the live menu,
  clears `_active_context_menu` / `_active_context_menu_binds`, and is re-entrancy
  safe (a second call is a no-op).

## Files touched
- `KrakenOS/UI/services/open3d_mouse_bindings.py` — `left_press` / `middle_press`
  dismiss any live popup.
- `KrakenOS/UI/services/open3d_face_assignment.py` — `_popup_context_menu`
  docstring notes the primary-handler dismiss path.
- `KrakenOS/UI/validate_open3d_context_menu_dismiss_on_click.py` — new guard.
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — Phase 297.
- `tools/penta_validator_baseline.json` — Phase 297 = pass.
