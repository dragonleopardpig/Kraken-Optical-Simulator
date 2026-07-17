# bugs/0336 — The right-click popup menu can't be dismissed by clicking elsewhere in the 3D scene

Follow-up directive on the same recording: *"I also notice the right click pop up
menu can't be destroyed by clicking elsewhere in 3D scene."*

## Root cause — the grab is released before the menu is dismissed

`_show_surface_function_context_menu` posted its menu with:

```python
menu.tk_popup(int(event.x_root), int(event.y_root))
menu.grab_release()          # <- in a finally, runs immediately
```

On X11 `tk_popup` is **non-blocking** — it posts the menu and returns straight
away — so the `grab_release()` in the `finally` tears down the pointer grab
**immediately**. With no grab, Tk never sees the next click as "outside the
menu", so it never auto-unposts. Worse, the heavyweight VTK/OpenGL render window
is a native child that swallows the click before Tk's menu machinery could react
anyway. The menu just sits there.

## Fix — post through a shared helper that binds an explicit dismissal

Every context menu now posts through `_popup_context_menu(menu, event)`
(`open3d_face_assignment.py`), which:

- stores the live menu on `_active_context_menu` (+ the temporary bindings on
  `_active_context_menu_binds`),
- binds the **VTK Tk widget's** `<Button-1>` / `<Button-2>` / `<Button-3>`
  (additively) to `_dismiss_active_context_menu`, so a click anywhere in the 3D
  scene unposts the popup,
- also binds the menu's own `<Unmap>` / `<FocusOut>` to the same teardown,
- then `tk_popup`s and releases the grab as before.

`_dismiss_active_context_menu` unbinds the temporary canvas bindings, unposts +
destroys the menu, and clears `_active_context_menu`. It clears the state
**before** touching the menu, so an `<Unmap>` fired by its own `unpost` re-enters
as a harmless no-op (re-entrancy safe).

This is applied at the **helper**, not at one call site — so it covers the new
opening menu (0335) **and** the existing body/face menu, and any future context
menu that routes through the helper. (Guard the invariant, not the instance.)

Because the dismissal binding is a normal left-click on the canvas, it *also*
runs the usual `_on_left_button_press`, whose empty/body branch funnels through
`_clear_open3d_selection` — so a single click-elsewhere both dismisses the menu
**and** clears the 0334 opening selection, exactly the "click elsewhere to
disable it" behaviour.

## Guard & regression

`KrakenOS/UI/validate_open3d_led_ca_persistent_select.py` (penta **Phase 293**),
display-free, **Section 3**:
- `_popup_context_menu` `tk_popup`s the menu, records it on
  `_active_context_menu`, and binds three canvas button-press dismissals;
- `_dismiss_active_context_menu` unposts + unbinds all three and clears the live
  reference, and a **second** dismiss is a harmless no-op (re-entrancy);
- source contract: the body menu posts through `_popup_context_menu` and no
  longer calls `menu.tk_popup` directly.

## Files touched
- `KrakenOS/UI/open3d_inspector.py` — `_active_context_menu` /
  `_active_context_menu_binds` init.
- `KrakenOS/UI/services/open3d_face_assignment.py` — `_popup_context_menu` +
  `_dismiss_active_context_menu`; the body menu routed through the helper.
- `KrakenOS/UI/validate_open3d_led_ca_persistent_select.py` — new guard (Section 3).
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — Phase 293.
- `tools/penta_validator_baseline.json` — Phase 293 = pass.
