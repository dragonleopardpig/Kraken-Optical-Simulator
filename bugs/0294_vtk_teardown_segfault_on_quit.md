# 0294 — Segfault on app quit (VTK render window torn down after its Tk widget)

The user imported a lens folder in the real `layout_editor` GUI (the 0293 datasheet-only path — it worked, the
surrogate `machine_vision_pyrite_56_80_10x_v38_1097785_*.py` was written), then quit the app and got:

```
vtkTkRenderWidget.cxx:571  WARN| A TkRenderWidget is being destroyed before it[s] associated
vtkRenderWindow is destroyed. This is very bad and usually due to the order in which objects are
being destroyed. Always destroy the vtkRenderWindow before destroying the user interface components.
Segmentation fault (core dumped)
```

The crash is **on exit**, not during the import — the surrogate had already been built and loaded.

## Root cause
The Open 3D inspector (`Kraken3DInspector`) embeds a `vtkTkRenderWindowInteractor`. A Tk+VTK widget must
**finalize its `vtkRenderWindow` before the Tk widget is destroyed**; destroying the `vtkTkRenderWidget` while
the render window is still live segfaults.

The inspector's own X-button close does this correctly — `open3d_inspector.py`:

```python
self.protocol("WM_DELETE_WINDOW", self._on_close)
...
def _on_close(self):
    ...
    self._destroy_vtk_render_window()   # render_window.Finalize()
    self.destroy()                      # then tear down the Tk widget
```

But quitting the whole app (root window → `request_quit` → `KrakenLayoutEditor.destroy`) tore the inspector
down with a **bare** `self._three_d_inspector.destroy()` — the plain `tk.Toplevel.destroy()`, which never
runs `_on_close`, so the render window was never finalized. Tk destroyed the `vtkTkRenderWidget` first →
exactly the warning above → segfault. (`WM_DELETE_WINDOW` only fires when *that* window's own close button is
clicked; a root-window quit that destroys child `Toplevel`s bypasses it.)

Only `Kraken3DInspector` embeds a Tk-VTK render widget — the ray-inspector / gaussian-q windows in
`KrakenLayoutEditor.destroy` are not VTK-embedded, so this is the sole offender.

## Fix
`KrakenOS/UI/layout_editor.py`, `KrakenLayoutEditor.destroy` — finalize the inspector's render window before
destroying it, mirroring the inspector's own `_on_close` order:

```python
if self._three_d_inspector is not None:
    try:
        self._three_d_inspector._destroy_vtk_render_window()   # Finalize() first
    except Exception:
        pass
    try:
        self._three_d_inspector.destroy()
    except Exception:
        pass
    self._three_d_inspector = None
```

`_destroy_vtk_render_window()` is idempotent and fully `try/except`-guarded internally (it turns off the
orientation widget, `TerminateApp()`s the interactor, and `Finalize()`s the render window), so calling it from
the editor's teardown is safe.

Not caused by the 0293 import feature — this teardown path is pre-existing and would segfault on any quit with
the inspector open. The user hit it because using the new *Import Lens from Folder…* CAD-menu entry meant the
3D inspector was open at quit time.

## Guard + gate
`KrakenOS/UI/validate_open3d_vtk_teardown_ordering.py` (`run_checks()`) — display-free source contract:
`_destroy_vtk_render_window` calls `Finalize()`; both `_on_close` and `KrakenLayoutEditor.destroy` finalize the
render window **before** destroying the inspector widget (checked by textual position within each method body);
`WM_DELETE_WINDOW` routes through `_on_close`. Confirmed to fail against the pre-fix (bare-`destroy()`) shape.
Penta **phase 258**, baseline updated.

## Owed / limitation
The guard is a source contract, not a live run: reproducing the actual crash needs a real X server, and the
headless full renderer segfaults under Xvfb/llvmpipe (documented). **In-app eyeball owed** — open the Open 3D
inspector, then quit the app from the root window and confirm a clean exit (no VTK teardown warning, no core
dump).
