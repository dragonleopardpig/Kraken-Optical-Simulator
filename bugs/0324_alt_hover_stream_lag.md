# 0324 — Alt-hover edge mode never fired live (Tk `<Motion>` vs VTK `MouseMoveEvent` stream lag)

## Flag
Direct follow-up to 0323. After 0323 shipped, the user re-recorded three flags and reported
**"I don't see any change."** — and, decisively, **"I quited Kitty and relaunched the app before I
filed those flags"** (so it was not a stale process). The third recording
(`flag_20260716_102615_837`) says: *"default hover still show edge highlight, selectable edges are not
improved. **Alt hover does not work.**"*

0323's whole-face/edge gate and every display-free check were correct, yet holding **Alt** in the
running app did nothing.

## Root cause — the flag and the pick live on two different event streams
The scene FEATURE hover (the "LED STEP F012 face" highlight) is driven by the **VTK
`MouseMoveEvent` observer** `Open3DInteractionService._on_mouse_move`. That observer is fired by the
**`vtkTkRenderWindowInteractor`'s own `<Motion>` Tk binding**, installed when the widget is
constructed (`open3d_inspector.py` builds it at what is now ~line 750).

0323 recorded the Alt flag (`_edge_pick_alt_active`) in a **separate** Tk `<Motion>` binding,
`hover_motion`, added with `add="+"` (`open3d_mouse_bindings.py`) — i.e. **after** the interactor's
binding. So on any single physical motion the order is:

1. interactor `<Motion>` → `MouseMoveEvent()` → `_on_mouse_move` runs the feature pick, reading
   `_edge_pick_alt_active`;
2. **then** `hover_motion` runs and updates `_edge_pick_alt_active`.

Two consequences, both matching *"Alt hover does not work"*:
- **One-frame lag.** The pick always read the flag value from the **previous** motion. On the frame
  Alt first changes, the pick still used the stale value.
- **Stationary press does nothing.** Pressing Alt with the mouse held still generates **no** `<Motion>`
  at all → neither the flag update nor a re-pick runs. The natural gesture — point at an edge, then
  press Alt — produced no change whatsoever.

The probe `bugs/probe_0323_modifier_bits.py` had already ruled out the two tempting wrong theories:
Alt **is** detected in Tk (`state & 0x0008` → `ALT=YES`), so neither the compositor nor
`_event_alt_pressed` was at fault. Detection was fine; **timing** was the bug.

(VTK's own key path can't paper over this either: `SetEventInformationFlipY(x,y,ctrl,shift,…)` carries
no Alt bit, so the interactor's `GetAltKey()` is always 0, and with default click-to-focus the widget
only grabs keyboard focus on a **left click**, not on hover — so a naive `<KeyPress-Alt_L>` on the VTK
widget wouldn't even fire during plain hover.)

## Fix — re-fire the hover pick on the Alt *transition*, from a focus-independent tracker
`open3d_inspector.py` (new):
- **`_refresh_edge_pick_alt_state(active)`** sets `_edge_pick_alt_active` and, **only when it actually
  changed**, calls `_refire_scene_hover_pick()`. No change ⇒ just store the value (no wasted re-pick).
- **`_refire_scene_hover_pick()`** resets the move throttle (`_mouse_move_last_ts = 0.0` so
  `_mouse_move_due()` can't swallow the synthetic move) and re-invokes `interactor.MouseMoveEvent()` at
  the cursor's last position, so `_on_mouse_move` re-picks **now** with the fresh flag. Guarded on
  **`_pointer_over_vtk_widget()`** so an Alt tap while the cursor rests on the tree/toolbar can't
  re-pick a stale scene position; a missing interactor is a no-op.
- **`_pointer_over_vtk_widget()`** — pointer-in-widget-rect test via `winfo_*`.

`open3d_mouse_bindings.py` (`_install_pick_only_left_click_bindings`):
- **`hover_motion`** now remembers the previous Alt state (`alt_changed = alt_now != …`), still records
  the live modifier (`alt_now = self._event_alt_pressed(event)`), and — once it has confirmed a passive
  scene hover (not dragging, not over the nav cube) — **re-fires the pick on a change**. This closes the
  one-frame lag for the moving-mouse case.
- **Toplevel Alt tracker** — `self.bind("<KeyPress-Alt_L>" / "<KeyPress-Alt_R>", …True)` and the
  matching `<KeyRelease-…>` (…False) are bound on the inspector **Toplevel** (`self`), which is in the
  VTK widget's bindtags, so they fire whether or not the widget holds keyboard focus. X11 modifier keys
  **don't auto-repeat**, so a held Alt is one clean KeyPress…KeyRelease pair — no flicker. This makes a
  **stationary** Alt press/release flip the mode with the mouse perfectly still. `<FocusOut>` drops the
  flag so an Alt-Tab that steals focus mid-hold can't wedge the mode on.

`left_press` still records the press-time Alt directly (a click commits immediately; no re-fire needed).

Per *"guard the invariant, not the instance"*: the invariant is **the modifier the user is holding must
be the one the live scene pick reads — independent of which Tk/VTK stream delivered it, and without
requiring a mouse move.**

## Verified (display-free)
`KrakenOS/UI/validate_open3d_alt_hover_refire.py` — **PASS**:
- **A** equal-value call sets the flag but does NOT re-fire (no synthetic `MouseMoveEvent`, throttle
  untouched).
- **B/B2** each transition (press → True, release → False) sets the flag, resets the throttle to 0, and
  fires exactly one `MouseMoveEvent`.
- **C** transition while the pointer is OFF the widget: flag flips, but no re-pick.
- **D** transition with no interactor: flag flips, no crash, no re-fire.
- **E** `_pointer_over_vtk_widget` geometry (inside True / outside False).
- **F** source wiring: `hover_motion` computes `alt_changed` and calls `_refire_scene_hover_pick`; the
  four `Alt_L/Alt_R` KeyPress/KeyRelease sequences are bound on the Toplevel and drive
  `_refresh_edge_pick_alt_state(True/False)`; `_refresh_edge_pick_alt_state` re-fires only on a change;
  `_refire_scene_hover_pick` guards on pointer-over, resets the throttle and re-invokes `MouseMoveEvent`.

Penta **phase 288** (`phase_288_alt_hover_refire`) delegates to the guard; baseline updated
(`"288": "pass"`). 0323's phase 287 still passes (its check F was updated to the new `hover_motion`
shape — it still asserts hover_motion records the live Alt, now via `alt_now`).

## Files
- `KrakenOS/UI/open3d_inspector.py` — `_refresh_edge_pick_alt_state`, `_refire_scene_hover_pick`,
  `_pointer_over_vtk_widget`.
- `KrakenOS/UI/services/open3d_mouse_bindings.py` — `hover_motion` re-fires on the Alt transition;
  Toplevel `<KeyPress/KeyRelease-Alt_L/Alt_R>` tracker + `<FocusOut>` reset.
- `KrakenOS/UI/validate_open3d_alt_hover_refire.py` — new display-free guard.
- `KrakenOS/UI/validate_open3d_led_edge_pick_modes.py` — check F updated for the reshaped `hover_motion`.
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — `phase_288`.
- `tools/penta_validator_baseline.json` — phase 288 baseline + title.

## Notes / remaining
- **In-app eyeball owed** (needs a GLX display, which this dev box lacks): import the LED STEP, point at
  an edge, and confirm (a) pressing **Alt with the mouse still** immediately promotes the whole-face
  highlight to the nearest drawn edge; (b) releasing Alt demotes it back to the whole face; (c) moving
  the mouse while holding Alt tracks the nearest edge with no face↔edge lag.
- Separate remaining defect (bugs/0325, not this fix): the whole-face outline itself can render skewed
  vs the visible rim ("phantom"), which reads as a stray edge on plain hover.
