"""Guard: the 3D viewport's input handlers are reachable without Tk (bugs/0905,
docs/design_qt_migration.md phase 5a).

Phase 5 is the interaction layer, and its first step is the event wiring. Measured: the 26 234-
line inspector has only 30 event hookups, and the real mouse wiring is
`services/open3d_mouse_bindings.py` -- 16 Tk bindings onto handlers that implement pick-vs-orbit,
pan, the context menu and Alt-edge hover with the inspector's own camera math. The handlers read
only an event's x, y, modifier state, keysym and root position.

So the seam is:
* the handlers are BUILT once (`_build_viewport_handlers`) and BOUND to Tk separately
  (`_bind_tk_viewport`); `dispatch_viewport_event(kind, event)` runs one with any event carrying
  those fields -- `viewport_events.ViewportEvent` for a shell that is not Tk;
* the shortcut keys are ONE table (`VIEWPORT_KEYS`) the Tk bindings and `dispatch_viewport_key`
  both read;
* cursor, timers and pointer position go through seams (`_set_viewport_cursor`, the UI host,
  a `viewport_pointer` hook), their Tk behaviour unchanged;
* the VTK core -- renderer, interactor observers, pickers, orientation marker, gizmo layer,
  navigation cube -- is `_attach_vtk_core(render_window, initialize)`, which any VTK widget's
  render window can take.

  H  all 14 handlers are built, every Tk sequence and shortcut key is still bound, and every event
     field the handlers read is one ViewportEvent carries
  R  `button_handler` -- the rule a non-Tk shell uses -- routes each button and modifier exactly
     as the Tk binding table does (Shift + left pans like the middle button)
  P  on a REAL inspector, an orbit and a pan driven through genuine Tk events and the SAME gestures
     driven through `dispatch_viewport_event` leave the camera in the SAME place
  K  a dispatched Escape cancels an active operation; an unbound key does nothing
  S  the cursor and pointer seams reach a shell hook when one is installed and Tk otherwise; no
     timer is armed on the Tk widget
  A  `_attach_vtk_core` built the core: the five interactor observers, the pickers, the
     navigation cube, the renderer in the window
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

SCENE = Path("attachment/om05a_folded.py")


def _camera(inspector):
    camera = inspector._renderer.GetActiveCamera()
    return (tuple(camera.GetPosition()), tuple(camera.GetFocalPoint()), tuple(camera.GetViewUp()))


def _set_camera(inspector, state) -> None:
    camera = inspector._renderer.GetActiveCamera()
    camera.SetPosition(*state[0])
    camera.SetFocalPoint(*state[1])
    camera.SetViewUp(*state[2])
    inspector._renderer.ResetCameraClippingRange()


def _same(a, b, tol=1e-6) -> bool:
    return all(abs(x - y) <= tol for triple_a, triple_b in zip(a, b)
               for x, y in zip(triple_a, triple_b))


def _settle(editor, inspector, turns=4) -> None:
    for _ in range(turns):
        inspector.update()
        editor.update()


#: X11 state bits a real X server puts on a drag's events -- event_generate does not derive them
#: from the pattern's modifiers, so a synthetic Shift-drag must carry them explicitly
BUTTON1_MASK = 0x0100


def _tk_drag(widget, editor, inspector, press, motion, release, points, modifiers=0) -> None:
    (x0, y0), (x1, y1) = points
    widget.event_generate(press, x=x0, y=y0, state=modifiers)
    _settle(editor, inspector, 1)
    for step in range(1, 5):
        x = x0 + (x1 - x0) * step // 4
        y = y0 + (y1 - y0) * step // 4
        widget.event_generate(motion, x=x, y=y, state=modifiers | BUTTON1_MASK)
        _settle(editor, inspector, 1)
    widget.event_generate(release, x=x1, y=y1, state=modifiers | BUTTON1_MASK)
    _settle(editor, inspector, 2)


def _dispatched_drag(inspector, editor, button, state, points) -> None:
    from KrakenOS.UI.viewport_events import ViewportEvent, button_handler

    (x0, y0), (x1, y1) = points
    inspector.dispatch_viewport_event(button_handler(button, state, "press"),
                                      ViewportEvent(x0, y0, state))
    for step in range(1, 5):
        x = x0 + (x1 - x0) * step // 4
        y = y0 + (y1 - y0) * step // 4
        inspector.dispatch_viewport_event(button_handler(button, state, "motion"),
                                          ViewportEvent(x, y, state))
    inspector.dispatch_viewport_event(button_handler(button, state, "release"),
                                      ViewportEvent(x1, y1, state))
    _settle(editor, inspector, 2)


def run_checks() -> tuple[bool, list[str]]:
    from KrakenOS.UI import open3d_inspector
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services import open3d_mouse_bindings
    from KrakenOS.UI.services.open3d_mouse_bindings import Open3DMouseBindingsService as Service
    from KrakenOS.UI.viewport_events import KINDS, SHIFT, ViewportEvent, button_handler

    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    # ---- H (static half): every field the handlers read is a ViewportEvent field -----------
    tree = ast.parse(inspect.getsource(Service._build_viewport_handlers).lstrip())
    read = {node.attr for node in ast.walk(tree)
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
            and node.value.id == "event"}
    getattr_read = {node.args[1].value for node in ast.walk(tree)
                    if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "getattr"
                    and len(node.args) >= 2 and isinstance(node.args[0], ast.Name)
                    and node.args[0].id == "event" and isinstance(node.args[1], ast.Constant)}
    fields = set(ViewportEvent.__dataclass_fields__)
    missing = sorted((read | getattr_read) - fields)
    ok(not missing and read,
       f"H1: the handlers read {sorted(read | getattr_read)} from an event -- all ViewportEvent "
       f"fields" + (f"; NOT carried: {missing}" if missing else ""))

    # ---- R the button rule a non-Tk shell uses is the Tk table's ---------------------------
    binder = inspect.getsource(Service._bind_tk_viewport)
    table = {}
    for line in binder.splitlines():
        line = line.strip()
        if line.startswith("self._vtk_widget.bind(") and 'handlers["' in line:
            sequence = line.split('"')[1]
            table[sequence] = line.split('handlers["')[1].split('"')[0]
    expected = {"<ButtonPress-1>": button_handler(1, 0, "press"),
                "<B1-Motion>": button_handler(1, 0, "motion"),
                "<ButtonRelease-1>": button_handler(1, 0, "release"),
                "<Shift-ButtonPress-1>": button_handler(1, SHIFT, "press"),
                "<Shift-B1-Motion>": button_handler(1, SHIFT, "motion"),
                "<Shift-ButtonRelease-1>": button_handler(1, SHIFT, "release"),
                "<ButtonPress-2>": button_handler(2, 0, "press"),
                "<ButtonPress-3>": button_handler(3, 0, "press")}
    wrong = {seq: (table.get(seq), kind) for seq, kind in expected.items() if table.get(seq) != kind}
    ok(not wrong, "R: button_handler routes every button and Shift exactly as the Tk binding table "
       "does -- Shift + left drags like the middle button" + (f" -- differ {wrong}" if wrong else ""))

    # ---- S (static half) no timer on the Tk widget -----------------------------------------
    inspector_source = Path("KrakenOS/UI/open3d_inspector.py").read_text(encoding="utf-8")
    bindings_source = inspect.getsource(open3d_mouse_bindings)
    ok("self._vtk_widget.after(" not in inspector_source + bindings_source
       and "self._vtk_widget.after_cancel(" not in inspector_source + bindings_source,
       "S1: no timer is armed or cancelled on the Tk VTK widget -- they go through the UI host")

    editor = KrakenLayoutEditor()
    try:
        editor.layout_files[SCENE.stem] = SCENE
        editor.load_layout_by_name(SCENE.stem)
        editor.open_3d_view()
        editor.update_idletasks()
        editor.update()
        inspector = getattr(editor, "_three_d_inspector", None)
        if inspector is None or not getattr(inspector, "available", False):
            notes.append("SKIP P/K/S2/A: the embedded 3D inspector is unavailable")
            return state["ok"], notes
        _settle(editor, inspector, 6)
        widget = inspector._vtk_widget

        # ---- H (live half) --------------------------------------------------------------
        handlers = getattr(inspector, "_viewport_handlers", None) or {}
        bound = set(widget.bind())
        needed = {"<Button-1>", "<B1-Motion>", "<ButtonRelease-1>", "<Double-Button-1>",
                  "<Button-2>", "<B2-Motion>", "<ButtonRelease-2>", "<Shift-Button-1>",
                  "<Shift-B1-Motion>", "<Shift-ButtonRelease-1>", "<Button-3>", "<B3-Motion>",
                  "<ButtonRelease-3>", "<Motion>"}
        # Tk normalises <KeyPress-s> to the bare letter "s" in its binding list
        keys_bound = {keysym if len(keysym) == 1 else f"<Key-{keysym}>"
                      for keysym, _h in open3d_inspector.VIEWPORT_KEYS}
        unbound = sorted((needed | keys_bound) - bound)
        ok(set(handlers) == set(KINDS) and not unbound,
           f"H2: all {len(handlers)} handlers are built, and every Tk sequence and shortcut key is "
           f"still bound on the widget" + (f" -- unbound {unbound}" if unbound else ""))

        # ---- A the core ------------------------------------------------------------------
        interactor = inspector._vtk_interactor
        observed = [name for name in ("LeftButtonPressEvent", "MouseMoveEvent", "KeyPressEvent",
                                      "InteractionEvent", "EndInteractionEvent")
                    if interactor.HasObserver(name)]
        renderers = widget.GetRenderWindow().GetRenderers()
        in_window = any(renderers.GetItemAsObject(i) is inspector._renderer
                        for i in range(renderers.GetNumberOfItems()))
        ok(len(observed) == 5 and in_window and inspector._picker is not None
           and getattr(inspector, "_navigation_cube", None) is not None,
           f"A: _attach_vtk_core built the core -- observers {observed}, the renderer in the "
           f"window, the pickers and the navigation cube")

        # ---- P the same gesture two ways, the same camera --------------------------------
        width, height = widget.GetRenderWindow().GetSize()
        cx, cy = width // 2, height // 2
        start = _camera(inspector)
        results = {}
        # Each gesture starts at its OWN pixel: synthetic events carry no real timestamps, so a
        # second press on the same pixel is read by Tk as a double-click and runs the
        # double-click handler instead -- measured, it made the pan look dead.
        for name, button, modifier, tk_events, points in (
                ("orbit", 1, 0, ("<ButtonPress-1>", "<B1-Motion>", "<ButtonRelease-1>"),
                 ((cx, cy), (cx + 90, cy + 40))),
                ("pan", 1, SHIFT, ("<Shift-ButtonPress-1>", "<Shift-B1-Motion>",
                                   "<Shift-ButtonRelease-1>"),
                 ((cx - 60, cy - 50), (cx + 30, cy - 10)))):
            _set_camera(inspector, start)
            _tk_drag(widget, editor, inspector, *tk_events, points, modifiers=modifier)
            by_tk = _camera(inspector)
            _set_camera(inspector, start)
            _dispatched_drag(inspector, editor, button, modifier, points)
            by_dispatch = _camera(inspector)
            moved = not _same(by_tk, start)
            results[name] = (moved, _same(by_tk, by_dispatch))
        _set_camera(inspector, start)
        ok(all(moved and same for moved, same in results.values()),
           f"P: an orbit and a pan through genuine Tk events and through dispatch_viewport_event "
           f"moved the camera and left it in the SAME place ({results})")

        # ---- K the keys ------------------------------------------------------------------
        inspector._placement_target_pick_mode = True
        inspector.dispatch_viewport_key("Escape")
        cancelled = inspector._placement_target_pick_mode is False
        unbound_key = inspector.dispatch_viewport_key("F13") is False
        ok(cancelled and unbound_key,
           "K: a dispatched Escape cancelled the active operation; an unbound key did nothing")

        # ---- S (live half) cursor and pointer seams --------------------------------------
        # the Tk VTK widget can be configured but not read back (no cget), so record what
        # the seam asks of it
        configured = []
        real_configure = widget.configure

        def recording_configure(*args, **kwargs):
            configured.append(kwargs.get("cursor"))
            return real_configure(*args, **kwargs)

        widget.configure = recording_configure
        seen = []
        try:
            inspector.set_viewport_cursor = seen.append
            inspector._set_viewport_cursor("crosshair")
            hooked = seen == ["crosshair"] and configured == []
            del inspector.set_viewport_cursor
            # MEASURED: the Tk VTK widget has no cursor option at all -- configure(cursor=...)
            # raises TclError, and every caller has always swallowed it, so the Tk 3D view's
            # cursor cues have never shown. The seam keeps that exactly (bugs/0905 changes no Tk
            # behaviour); what is checked here is that, with no hook, it still asks Tk.
            tk_rejects = False
            try:
                inspector._set_viewport_cursor("fleur")
            except Exception:
                tk_rejects = True
            tk_cursor = configured == ["fleur"]
        finally:
            widget.configure = real_configure
        inspector.viewport_pointer = lambda: (12, 34)
        pointer = inspector._current_widget_pointer_xy()
        del inspector.viewport_pointer
        ok(hooked and tk_cursor and pointer == (12, 34),
           "S2: with a shell hook the cursor and pointer seams reach it and leave Tk alone; "
           "without one the seam asks the Tk widget as before"
           + (" (which REJECTS a cursor -- the Tk cue has never shown; see bugs/0905)"
              if tk_rejects else ""))
    finally:
        editor.destroy()

    return state["ok"], notes


def run() -> int:
    passed, notes = run_checks()
    print()
    for note in notes:
        print(("  " + note[2:]) if note.startswith("= ") else ("! " + note))
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
