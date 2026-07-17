# bugs/0343 — the `s` flag-bug hotkey dies after a right-click popup is dismissed

**Flag `flag_20260717_145231_845`** (imported LED, app running the bugs/0341 fix):

> "right click elsewhere closes the pop up, but shortcut 's' no longer woring. I right
> click again and click the menu grayed out item, it closes, then the 's' shorcut can
> flag again."

This flag **confirms bugs/0341 works** ("right click elsewhere closes the pop up") but
exposes a follow-up regression from it.

## The defect

The `s` flag-bug hotkey is bound at BOTH the Toplevel and the render pane
(`open3d_inspector.py`):

```python
self.bind("<KeyPress-s>", self._flag_bug_event)          # Toplevel
self._vtk_widget.bind("<KeyPress-s>", self._flag_bug_event, add="+")  # render pane
```

For either binding to fire, **some widget inside the Toplevel must hold keyboard
focus**. When a right-click posts a menu, `menu.tk_popup(...)` grabs the pointer **and
takes keyboard focus for the menu**. bugs/0341 dismisses a live popup on a scene click
by calling `_dismiss_active_context_menu` → `menu.destroy()`.

But **destroying a focused menu ourselves does not restore focus** the way a normal
menu-item click does. Tk's menu machinery only returns focus to the pre-popup widget
when the menu is dismissed through its own event flow (clicking an item, Escape). Our
programmatic `destroy()` leaves keyboard focus in limbo — no widget in the Toplevel is
focused — so the Toplevel-level `<KeyPress-s>` never fires. "shortcut 's' no longer
woring."

The user's own workaround is the tell: **"I right click again and click the menu grayed
out item, it closes, then the 's' shorcut can flag again."** Dismissing the second menu
by *clicking an item* (even the disabled title) routes through Tk's normal menu
teardown, which restores focus to the render pane — and `s` works again.

## Fix — restore render-pane focus after tearing down a live menu

`_dismiss_active_context_menu` (`open3d_face_assignment.py`) now hands keyboard focus
back to the render pane after it destroys a **live** menu:

```python
if menu is not None:
    ...  # unpost / grab_release / destroy
    widget = getattr(self._inspector, "_vtk_widget", None)   # bugs/0343
    if widget is not None:
        try:
            widget.focus_set()
        except Exception:
            pass
```

Focus is restored **only when a menu was actually dismissed** — the pre-post clear
(`_popup_context_menu` calls `_dismiss_active_context_menu` before posting a new menu,
with no live menu) leaves focus alone, so we never steal focus away from a widget the
user is typing in.

Invariant: **a dismissed right-click popup always returns keyboard focus to the render
pane**, so the `s` flag hotkey keeps firing without the reopen-and-click-an-item dance.

## Guard & regression

`KrakenOS/UI/validate_open3d_context_menu_focus_restore.py` (penta **Phase 299**),
display-free:
- a live menu dismissed → `_vtk_widget.focus_set()` is called (menu unposted +
  destroyed, state cleared);
- no live menu → `focus_set` is **not** called (the pre-post clear leaves focus alone);
- source contract: `_dismiss_active_context_menu` references both `_vtk_widget` and
  `focus_set`.

## Files touched
- `KrakenOS/UI/services/open3d_face_assignment.py` — `_dismiss_active_context_menu`
  restores render-pane focus after destroying a live menu.
- `KrakenOS/UI/validate_open3d_context_menu_focus_restore.py` — new guard.
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — Phase 299.
- `tools/penta_validator_baseline.json` — Phase 299 = pass.
