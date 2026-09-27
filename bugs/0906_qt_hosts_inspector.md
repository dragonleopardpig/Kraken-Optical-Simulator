# 0906 -- the Qt shell hosts the REAL 3D inspector (phase 5a, part 2)

0905 made the inspector's input handlers reachable without Tk. This step puts the inspector itself
in the Qt shell. It is not a re-implementation: the same `Kraken3DInspector` object, the same VTK
core, the same handlers draw into a Qt VTK widget and take Qt input.

`SceneViewport` (the drawing-only Qt view, 0855-0858) stays the central widget; the inspector is a
**3D Inspector** dock (View -> 3D Inspector, Ctrl+I), until phase 5 reaches parity.

## How

- **`Kraken3DInspector(editor, *, vtk_host=None)`.** With a `vtk_host` (a
  `QVTKRenderWindowInteractor`), `_attach_shell_viewport` gives that widget's render window to
  `_attach_vtk_core`, builds the 14 handlers and binds them to nothing. The inspector then
  schedules on the shell's UI host, not a `TkUiHost` of its own. Its Tk Toplevel is withdrawn and
  keeps only its hidden panels. With no `vtk_host`, nothing changes.
- **`qt/inspector_view.InspectorView`** turns Qt input into dispatches, in the order the Tk
  bindings delivered them:
  - Button events go to the handler `button_handler` names, and Qt consumes them. The Tk
    inspector also replaces the VTK widget's own button bindings, so VTK's interactor style never
    sees a click.
  - A bare move goes to VTK first (its MouseMoveEvent observer runs the hover pick) and then to
    the "hover" handler. That is Tk's `add="+"` order.
  - The wheel stays with VTK, which zooms, as it does under Tk.
  - A key goes to VTK first and then to `dispatch_viewport_key`.
  - Alt alone flips edge hover, and losing focus clears it.
  - Positions are scaled by the widget's pixel ratio, as the widget scales its own.
  - The seams are installed: `set_viewport_cursor` (Tk cursor name -> Qt shape), `viewport_pointer`
    and `show_in_shell`.
- **`open_3d_view`** re-uses a shell-hosted inspector through `show_in_shell` and never
  deiconifies its Toplevel.

## Held back until 5c

A right-button PRESS posts the Tk context menu, which a Qt shell cannot show, so Qt does not route
it. Right-button motion and release (swallow the drag, clear the flag) are still routed.

## What the smoke run found

1. **Three timers were still armed on Tk objects.** Under Qt they would never fire, because
   nothing pumps Tk:
   - the Live Mode refresh (`inspector.after`)
   - the trailing hover re-pick (`widget.after` on the VTK widget; a Qt VTK widget has no `after`,
     so the re-pick silently never ran)
   - the async-trace poll (`editor.after`, the Tk root)

   All three now go through `host_of(...)`. Under Tk the host delegates to the same `after`, so Tk
   behaviour is unchanged. The 0905 guard's S1 check missed the second one because it searched for
   `self._vtk_widget.after(` and the code used a local `widget`.
2. **`_pointer_over_vtk_widget` read Tk `winfo_*`.** Under Qt it always answered "not over", so
   an Alt tap would never re-pick. It now asks the `viewport_pointer` seam first.
3. **The dock opened 0 px tall.** The four input forms (System, Source, Trace, Optimization) were
   stacked in the right-hand area at their full minimum heights, about 1600 px in all. That forced
   the window to 2141 px on a 1200-px screen and left the inspector nothing. A 0-px viewport picks
   nothing. Three changes fix it:
   - the four forms share one tabbed stack;
   - each form sits in a scroll area, so its full height is no longer the dock's minimum;
   - the inspector dock uses the otherwise empty top area, has a minimum size, and is resized
     after the first layout pass.

   The window now stays at its designed 950 px and the viewport is 1500x528. The dock may move
   but never float: floating re-creates the native window whose id VTK was given.

## Still differs from Tk

The cursor cues now SHOW in Qt. In Tk they never have (0905 finding: the Tk VTK widget rejects a
cursor), so the two shells differ on this until that decision is made.

## Guard

`validate_open3d_0906_qt_hosts_inspector` (penta phase 694).

Static checks:
- the Qt routing equals `button_handler` in all 45 button/modifier/phase cases, except the right
  press;
- every cursor the inspector asks for maps to a real Qt shape;
- the three timers and the pointer-over test go through the host and the seams.

In a real Qt shell on `om05a_folded`:
- W: the inspector is wired as described.
- L: the dock is a usable size and the window fits the screen.
- O: an orbit, a Shift+left pan and a middle pan sent as Qt mouse events move the camera, and
  leave it where the same gestures sent as ViewportEvents do. 0905 proved dispatch == Tk.
- P: a Qt hover + click selects exactly what the dispatched hover + click selects.
- K: Escape cancels an armed pick.
- A: Alt turns edge hover on and then off.
- D: a right click dispatches no press.
- U: the cursor and pointer seams work.
- S: a live refresh and a trailing re-pick both run in the Qt loop.
- V: Open 3D View re-uses the Qt inspector.

`validate_open3d_live_mode` (phase 664) pinned the old `inspector.after` line and has been
re-pointed. `validate_open3d_led_hover_repick` (ungated) handed its fake clock to the widget; it
now hands it to the fake inspector.
