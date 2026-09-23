# 0856 -- the Qt shell aborted on a Wayland desktop (BadWindow)

Flagged by the user, running the shipped shell on their own session:

```
$ python -m KrakenOS.UI.qt.app attachment/om05a_folded.py
X Error of failed request:  BadWindow (invalid Window parameter)
  Major opcode of failed request:  12 (X_ConfigureWindow)
```

No traceback, no Python error: Xlib's default error handler calls `exit()`, so the process was
gone before anything could report it.

## Root cause

`QVTKRenderWindowInteractor` gives VTK **the Qt widget's window id**, and VTK's on-screen render
window on Linux is X11 (`vtkXOpenGLRenderWindow`). On this desktop (Hyprland) Qt picks the
**Wayland** platform plugin by default, so that id is a Wayland surface -- VTK then asked the X
server to configure a window it had never heard of.

Nothing about the viewport code was wrong: the same code renders correctly the moment Qt is on
XWayland. This is the trap the phase-2 spike had already found headlessly ("Qt's platform and
VTK's display must be the same window system", bugs/0854) -- recorded there only as a rule for
running the guards under Xvfb, when it is really a constraint on the APPLICATION.

## Fix

`KrakenOS/UI/qt/app.py`:

- `choose_qt_platform(env)` -- returns the platform this process must use, and why. On Linux, with
  a Wayland session and an X server available, that is `xcb`; an explicit `QT_QPA_PLATFORM` is
  always left alone; a Wayland session with **no** `DISPLAY` is refused with a sentence saying so
  instead of aborting later.
- `build()` applies it before the `QApplication` exists (the only moment it can be applied) and
  prints one line saying what it did.
- `require_viewport_platform(name)` -- called by `SceneViewport` before the widget is created, so
  a wrong platform raises a RuntimeError that explains itself rather than letting Xlib kill the
  process.

Verified on the user's real session: `[KrakenOS] Qt platform -> xcb`, then
`vtkXOpenGLRenderWindow`, 25 rows in the table and the three om05a bodies drawn.

## Guard

`validate_open3d_0856_qt_platform.py`, penta phase 635.

D: the decision table, display-free -- Wayland + DISPLAY -> `xcb`; an explicit `QT_QPA_PLATFORM`
is untouched; Wayland with no DISPLAY is refused with a reason; a plain X session is left alone;
a non-Linux platform is left alone. R: `require_viewport_platform` passes `xcb` and `offscreen`
and raises for `wayland`, and the message names the variable to set. Q: in a SUBPROCESS with
`WAYLAND_DISPLAY` set and `QT_QPA_PLATFORM` unset -- the exact environment that aborted -- the
REAL `build()` brings the application up on `xcb` and the viewport gets an OpenGL render window.
