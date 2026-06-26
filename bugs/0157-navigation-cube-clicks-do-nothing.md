# 0157 — navigation cube renders but clicks do nothing

User report (follow-up to bugs/0156): *"I see XYZ with additional -X, -Y and -Z,
How to use? I click the view never change."*

The FreeCAD-style navigation cube shipped in bugs/0156 draws correctly in the
upper-right corner — the user can see the +X/+Y/+Z and -X/-Y/-Z axis handles — but
clicking a handle does **not** snap or rotate the camera. The widget is present,
enabled, and anchored, yet functionally deaf.

## Root cause

The cube (`vtkCameraOrientationWidget`) does its work by observing the
interactor's `LeftButtonPressEvent` / `MouseMoveEvent` / `LeftButtonReleaseEvent`.
On `On()` it derives its interactor from
`ParentRenderer->GetRenderWindow()->GetInteractor()`, which is why it renders without
an explicit `SetInteractor` call — but it can only react to button events that are
actually *fired through that interactor*.

The Open 3D canvas never fires them. `_install_pick_only_left_click_bindings`
(in `open3d_mouse_bindings.py`) binds `<ButtonPress-1>` on the
`vtkTkRenderWindowInteractor` **without** `add="+"`, so it *replaces* the
interactor's own default Tk binding. A plain click is then dispatched by calling the
app's pick handler directly (`_on_left_button_press(...)`), and camera orbit is run
by the app's own drag math — neither path ever calls
`interactor.LeftButtonPressEvent()`. So the cube's handle observers never see a
press, and the gizmo sits there inert. (This is the same "the app owns the click"
architecture that lets the canvas do pick-only selection; the cube was simply added
on top of it without a route for its events.)

## Fix

Forward the press / button-held move / release to the cube **only when the cursor is
over its gizmo**, from inside the existing Tk closures, before the scene
pick/drag/orbit logic runs. Five helpers on `Open3DMouseBindingsService`:

* `_enabled_navigation_cube()` — the enabled widget, or `None` (feature absent / VTK
  unavailable / no interactor).
* `_navigation_cube_state_under_cursor(widget)` — fire one `MouseMoveEvent` (this
  drives the widget's hover machinery; a bare `ComputeInteractionState` does **not**
  resolve the handle — it returns 0 everywhere) then read
  `GetRepresentation().GetInteractionState()`: `0` == outside the gizmo, non-zero ==
  over a handle. The interactor position is already set by the closure's
  `set_event_info(event)` (`SetEventInformationFlipY`, so the upper-right cube maps
  correctly: Tk-y small/top → VTK-y large).
* `_press_navigation_cube_if_hit()` — gate on the state; if over the gizmo, fire
  `LeftButtonPressEvent()` (grabs the handle), set `_nav_cube_press_active`, return
  `True` so the caller `return "break"`s and skips the scene pick. **Ctrl is the
  camera-orbit modifier**, so a Ctrl-press returns `False` and is left to orbit even
  over the cube.
* `_drag_navigation_cube_if_active()` — while a cube press is active, forward
  `MouseMoveEvent()` so a button-held drag re-highlights / rotates.
* `_release_navigation_cube_if_active()` — while active, forward
  `LeftButtonReleaseEvent()` (this is the event that **snaps** the camera), clear the
  flag.

Wired as three early `return "break"` hooks: in `left_press` (after
`set_event_info`), `left_motion`, and `left_release`. `_nav_cube_press_active` is
initialised `False` in `Kraken3DInspector.__init__`.

**Why this is side-effect-safe.** The widget *aborts* the events it consumes (proven:
a freshly-added independent observer on the same interactor fired 0 times during a
forwarded cube click), so forwarding does not also trip the app's
`_on_left_button_press` VTK observer or the orbit interactor style — no double pick,
no double orbit. And because the press is gated on `GetInteractionState() != 0`, a
click anywhere in the scene (state 0) forwards nothing and falls straight through to
the normal pick path.

## Guard

`KrakenOS/UI/validate_open3d_navigation_cube_click.py` (penta Phase 148) —
display-free: builds the service against a fake inspector with a fake cube
(`GetEnabled`/`GetRepresentation().GetInteractionState`) and a fake interactor
recording `MouseMoveEvent`/`LeftButtonPressEvent`/`LeftButtonReleaseEvent`/
`GetControlKey`. Asserts: no cube → no press; Ctrl down → no press (orbit); state 0 →
move probe but no press; state != 0 → press + flag + `True`; drag/release no-op
unless active, and the release fires exactly one `LeftButtonReleaseEvent` and clears
the flag. Plus a source-contract that `_install_pick_only_left_click_bindings`
contains the three forwarding hook calls.

Phase 148 additionally drives the **live** inspector (Xvfb): reset the camera to a
top-down view, forward a press+release over a cube handle via the exact helper path
the closures use, and assert the camera look-direction changed to a distinct standard
view — and that several handles snap to distinct directions including a reversal pair
(±X, ±Y), confirming the user's "reverse the view" ask.

## Notes

* Verified end-to-end under Xvfb via the exact helper path the closures call: from a
  top-down reset, the cube handles snap the camera to **5 distinct standard
  directions** (±X, ±Y, +Z) with **2 reversal pairs** present, and
  `_nav_cube_press_active` is left clean (`False`) after each click.
* **In-app eyeball owed:** the headless harness can drive the interactor directly but
  cannot deliver a real Tk `<ButtonPress-1>` hover-pick through the embedded VTK
  canvas, so the final mouse-on-handle click should be eyeballed in the running app.
