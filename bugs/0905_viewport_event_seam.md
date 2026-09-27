# 0905 -- the 3D viewport's input handlers, reachable without Tk (phase 5a, part 1)

Phase 5 is the interaction layer: the Open 3D inspector's picking, dragging, snapping, menus and
gizmos. It looked enormous -- `open3d_inspector.py` is 26 234 lines -- but measured, it has only
**30** event hookups, and VTK itself does not care which toolkit hosts it. Those 30 split three
ways:

- **8 VTK observers** (mouse press/move, key press, camera interaction, render/resize) --
  toolkit-neutral already; they attach to any VTK interactor, Qt's included
- **11 Tk bindings on the viewport and its window** -- the shortcut keys and a resize trace
- **12 bindings inside Tk dialogs** the inspector opens -- those move with their dialogs

and the real mouse wiring turned out to live elsewhere: `services/open3d_mouse_bindings.py`
binds 16 Tk mouse events (buttons 1-3 with Ctrl/Shift, double-click, drag, hover, Alt) to handlers
that implement pick-vs-orbit, pan, the context menu and Alt-edge hover **with the inspector's own
camera math** (`_rotate_camera_fixed_drag`, `_pan_camera_fixed_drag`), each returning "break" so
VTK's own handling never runs.

Those handlers read only an event's `x`, `y`, modifier `state`, `keysym` and root position. So
5a is re-plumbing, not a rewrite. This bug is its first half: the seams, with Tk unchanged.

## The seams

- **Handlers built once, bound separately.** `_build_viewport_handlers()` returns the 14
  handlers by kind (`viewport_events.KINDS`); `_bind_tk_viewport(handlers)` is the old binding
  table; `dispatch_viewport_event(kind, event)` runs one with any event carrying the fields they
  read. The handler bodies are unchanged.
- **`viewport_events.ViewportEvent`** is exactly those fields, with Tk's X11 modifier bits kept
  (the handlers already mask them), and `button_handler(button, state, phase)` is the routing
  rule the Tk table encodes -- Shift + left pans like the middle button -- so a shell asks it
  rather than re-deciding it.
- **One shortcut-key table**, `VIEWPORT_KEYS`, that the Tk bindings and `dispatch_viewport_key`
  both read.
- **Cursor, timers, pointer** go through `_set_viewport_cursor`, the UI host, and a
  `viewport_pointer` hook; their Tk behaviour is unchanged.
- **`_attach_vtk_core(render_window, initialize)`** -- the renderer, the interactor observers,
  the pickers, the orientation marker, the gizmo overlay layer and the navigation cube, moved
  verbatim out of `__init__` so any VTK widget's render window can take them. (AST-checked: the
  moved block uses no local of `__init__`.)

## Finding: the Tk 3D view's cursor has never changed

The Tk VTK widget has **no cursor option**: `configure(cursor=...)` raises `TclError: unknown
option "-cursor"`, and all six call sites have always wrapped it in `try/except: pass`. So the
cursor cues the code was written to give -- hidden while carrying a body, a crosshair while
picking, a resize arrow while dragging a dimension -- **have never appeared in Tk**. The seam
keeps that exactly (a seam step changes no Tk behaviour); fixing it for Tk would mean setting the
cursor on the widget's parent frame, which the widget inherits. That is a behaviour change,
so it is left for a decision. The Qt viewport will show them (0906), because Qt widgets do take
a cursor -- the two shells would then differ on this until Tk is fixed or the cues are dropped.

## Two harness traps

- `event_generate` does **not** derive the modifier state from the event pattern: a synthetic
  Shift-drag must carry `state=` explicitly (Shift 0x1, Button1 0x100), as a real X server does.
- Synthetic events have no real timestamps, so a second press on the **same pixel** is read as a
  double-click and runs the double-click handler -- the pan looked dead because it started where
  the orbit had. Each gesture now starts on its own pixel.

## Guard

`KrakenOS/UI/validate_open3d_0905_viewport_event_seam.py` (penta phase 693):

- **H1/H2** -- the handlers read only `x`, `y`, `state`, `keysym` (all `ViewportEvent` fields);
  all 14 are built and every Tk sequence and shortcut key is still bound
- **R** -- `button_handler` routes every button and Shift exactly as the Tk binding table does
- **P** -- on a REAL inspector, an orbit and a pan through genuine Tk events and the same
  gestures through `dispatch_viewport_event` leave the camera in the **same place**
- **K** -- a dispatched Escape cancels an active operation; an unbound key does nothing
- **S1/S2** -- no timer on the Tk widget; the cursor and pointer seams reach a shell hook when one
  is installed and Tk otherwise
- **A** -- `_attach_vtk_core` built the five observers, the pickers, the navigation cube and the
  renderer in the window

Fourteen guards read "the mouse bindings" as the source of the one method this split in three;
they read `viewport_wiring_source()` now (install + handlers + Tk binding), so the next split
cannot break them. Four `validate_3d_interaction_contract` checks were re-pointed to where the
code now lives (the carry-hold timer, the carry cursor, the Esc/Delete/Backspace table, the
KeyPress observer); all 259 pass.
