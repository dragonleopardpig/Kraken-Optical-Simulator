# 0348 — Right-click menu entry clicks silently dropped (Tk unmap dismiss destroys the menu before the command is delivered)

## Flag

`flag_20260717_204504_767` — *"still unable to right click and snap the CA to optical axis."*
Repo stamped `8cfb0aad` / `nonseq-display-refactor`. Scene: a lone imported LED STEP
(`attachment/LED/OPT-CO90-X-V1.6.2-H.STEP` — its transformed bounds match the recorded
`step_actor_bounds` exactly), nothing promoted, one `axis:global` record, not folded.
Full recording `recording_20260717_204931.json` (236 events).

## What the recording shows

| t | event | meaning |
|---|---|---|
| 3.8 s | left click (1161,472) | pins clear-aperture opening **F164** (0334 persistent select) |
| 4.5 s | right press (1161,472) | posts the pinned-opening menu (0335) — menu grabs, so its interactions are not recorded |
| ~5–14 s | *(nothing recorded)* | user browses the menu and clicks **"Snap Clear Aperture → Optical Axis"** — nothing happens |
| 14.0 s / 15.4 s | left clicks (1096,176), (1099,157) | **1.1 px / 3.6 px** from the dotted axis (camera-projected) — the old two-step habit; app is idle, clicks just select the axis |
| 19.1 s | `s` flag | `interaction_mode: idle`, `right_click_diagnostics: {}`, LED never moved |
| 44–56 s | three more right-click cycles | more dropped entry clicks |

The "green ring on the axis" in the screenshot is the recorder's own cursor annotation
(`open3d_inspector.py` flag-screenshot pipeline draws a green + magenta ring at the
cursor), not an armed-pick marker — the app was never armed.

`right_click_diagnostics: {}` is the discriminating witness: the pinned-opening menu
branch posts *before* `_right_click_pick_context` runs, so no diagnostics — the menu
**did** post; the failure is after that.

## Root cause

Tk delivers a clicked entry's command only **after** unposting the menu
(Tk `menu.tcl`, `tk::MenuInvoke`: `MenuUnpost $menu` first, then `$menu invoke $active`).

`_popup_context_menu` (bugs/0336) bound the menu's own `<Unmap>`/`<FocusOut>` to
`_dismiss_active_context_menu`, which calls `menu.destroy()`. That destroy landed
**between the unpost and the invoke**: the not-yet-delivered command died with the
widget as a background TclError (`invalid command name ".!menu"`) the user never sees.

**Every entry of every menu posted through `_popup_context_menu` — the STEP body/face
menu and the pinned-opening menu, i.e. exactly the two menus of the whole CA-snap
saga — has been a silent no-op since 0336 landed.** That is why 0339 ("Add BS not
working"), 0344 ("snap still not reachable"), 0346/0347 ("snapping still not working")
kept coming back no matter what the handlers were fixed to do: the handlers were never
invoked in the live app, while every probe that called `menu.invoke()` or the handler
directly bypassed Tk's unpost→invoke order and passed. The user's own datapoint
confirms the machinery was fine: toolbar **Place → Center Row → Optical Axis** (no
popup menu involved) snaps correctly in the same live app.

Reproduced end-to-end by `bugs/probe_0348_menu_entry_click_delivery.py`, which replays
Tk's exact internal order on the real posted menu:

```
pre-fix:  tk::MenuUnpost -> TclError 'bad window path name'   (destroyed mid-unpost)
          menu.invoke    -> TclError 'invalid command name'    -> moved=0.000
with fix: invoke_ok=True  moved=22.886  CA XY-off 22.886 -> 0.000
```

`bugs/probe_0348_led_only_snap_e2e.py` additionally proves the LED-only scene itself is
healthy: CA resolves (22.9 mm off axis), the menu handler auto-completes and centres it
(`error 0 deg`) — on all three vendor LEDs (ILS0202 / CO90 / COR85).

## Fix (`KrakenOS/UI/services/open3d_face_assignment.py`)

- `_popup_context_menu`: the **menu-bound** `<Unmap>`/`<FocusOut>` teardown is deferred
  one event-loop turn (`after_idle`) and identity-guarded (`_dismiss_if_current`) so a
  newer menu posted in the meantime is left alone. Tk's unpost→invoke completes, *then*
  the menu is destroyed and focus restored. Scene-click dismissal is unchanged and
  synchronous: the primary press handlers (open3d_mouse_bindings) and the widget
  `<Button-*>` backups still call `_dismiss_active_context_menu` directly — no entry
  invoke is pending on a scene click.
- `_dismiss_active_context_menu`: the bugs/0343 focus restore now skips `focus_set`
  while a modal grab is held, so a menu entry that opens a dialog keeps its keyboard
  focus (the dismiss now also runs after successful entry clicks).

## Guards

- `KrakenOS/UI/validate_open3d_context_menu_entry_delivery.py` — display-free; runs the
  real `_popup_context_menu`/`_dismiss_active_context_menu` on fake Tk objects: unmap
  must defer (not destroy), deferred teardown tears down + restores focus, identity
  guard protects a newer menu, scene-click backup stays synchronous, focus restore
  honours a modal grab, source contract (`after_idle`). Fails 4 ways pre-fix.
- Penta **phase 304** — runs the stub guard *and* replays Tk's real unpost→invoke order
  on a menu posted through the real `_popup_context_menu` inside the live validator
  app; asserts the command fired and the deferred teardown cleared the active menu.

## Notes for the saga

- 0346/0347 fixed real (probe-constructible) secondary conditions in
  `_single_optical_axis_pick_info`; they stay. The live killer all along was 0348.
- The 0345 build stamp fingerprints the *checkout at first-flag time*, not the running
  process — `git rev-parse` at flag time. A long-running app stamps whatever HEAD is
  when the first flag fires. Worth remembering when reading future bundles.
