# 0855 -- the Qt shell (Qt migration, phase 2 part 2)

docs/design_qt_migration.md. 0854 gave the migration a Qt host and proved VTK renders inside a Qt
widget. This is the window that uses both: `KrakenOS/UI/qt/`.

## What it is

A Qt-side VIEW layer over the model that already exists. `KrakenQtMainWindow` owns no optics: it
holds a `KrakenLayoutEditor` built with `ui=QtUiHost(...)`, so

- **`File -> Open Layout` calls the model's own `editor.open_layout()`** -- the same method the Tk
  File menu calls -- and the chooser that appears is `QFileDialog`, because that is what the host
  behind `host_of(self)` puts up. No Qt-specific load path was written.
- the surface table is a `QAbstractTableModel` reading `editor.rows` directly; there is no copy
  and no adapter record between the view and what the trace uses.
- the status bar binds once to `status_var` through `trace_add` -- the same call works whether the
  variable is a real `tk.StringVar` (a Tk panel made it) or an `ObservableValue` (a host made it),
  which is what step 1c was for.

| file | what |
|---|---|
| `qt/actions.py` | one declaration table -> QActions by name, menus built from it |
| `qt/docks.py` | dock factory (object names, features) + the default arrangement |
| `qt/rows_table.py` | the surface table's columns and model over `editor.rows` |
| `qt/viewport.py` | `SceneViewport`: the VTK widget, the renderer, the STEP bodies |
| `qt/main_window.py` | menus, docks, viewport, status line, the actions |
| `qt/app.py` | `python -m KrakenOS.UI.qt.app [layout.py]` |

`actions.py` and `docks.py` follow the structure of `optiland_gui/action_manager.py` and
`panel_manager.py` (MIT, (c) 2024 Kramer Harrison), attributed in each module.

## Two things the structure had to respect

**The viewport is built after `show()`.** `QVTKRenderWindowInteractor` hands VTK its window id in
its constructor, and Qt destroys and recreates a native window when a widget is reparented -- so
the window creates a plain container as its central widget, and `build_viewport()` adds the VTK
widget to that container's own layout once the window is up. Nothing is ever reparented.

**The Tk tree is still built, and never shown.** bugs/0853 freed the editor from BEING a Tk root,
not from having one; the shell builds it with `headless=True` and withdraws the root. That goes
away in phase 5, when the inspector becomes a Qt widget.

## Guard

`validate_open3d_0855_qt_shell.py`, penta phase 634. The Qt half runs in a subprocess on the xcb
platform (a QApplication must never be created inside the penta harness, which already holds a Tk
interpreter and a live VTK window) and needs a DISPLAY; without one, or without PySide6, those
sections SKIP.

A/B: the package imports no Qt binding; every declared action names a method the window defines.
Q1-Q7 against the real shell: menus and docks match the declaration and the viewport sits in the
central container; the table's rows, headings and sampled cells read back to `editor.rows`; a
model `status_var.set` reaches the status bar; the render window is OpenGL with a TRACKBALL style
(the default switch style starts in joystick mode, where a drag does nothing) and the bodies are
drawn with scalar colouring off; `File -> Open` TRIGGERED AS AN ACTION drives the model end to end
(asked "Open Kraken layout", loaded the file, table and title followed); a Qt press-drag-release
rotates the camera 462 mm; and the close drops the trace -- checked last, because closing
finalizes the VTK widget and rendering after that is the bugs/0294 use-after-free (it segfaulted
the guard when the close sat in the middle).
