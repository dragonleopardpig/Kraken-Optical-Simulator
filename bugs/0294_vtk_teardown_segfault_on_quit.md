# 0294 — Segfault on app quit (embedded VTK render window torn down at interpreter shutdown)

The user imported a lens folder in the real `layout_editor` GUI (the 0293 datasheet-only path — it worked, the
surrogate `machine_vision_pyrite_56_80_10x_v38_1097785_*.py` was written), then quit the app and got:

```
vtkTkRenderWidget.cxx:571  WARN| A TkRenderWidget is being destroyed before it[s] associated
vtkRenderWindow is destroyed. This is very bad and usually due to the order in which objects are
being destroyed. Always destroy the vtkRenderWindow before destroying the user interface components.
Segmentation fault (core dumped)
```

The crash is **on exit**, not during the import — the surrogate had already been built and loaded.

## First diagnosis (WRONG — kept only as a tidy best-effort)
The warning text says "destroy the vtkRenderWindow before the UI", so the first fix (commit 68df71d9) made the
root editor quit finalize the inspector's render window before destroying the widget, mirroring the inspector's
own `_on_close`. **The user still crashed** with the identical warning + core dump.

A minimal repro settled it — `bugs/probe_0294_vtk_teardown.py` builds a bare `tk.Tk()` +
`vtkTkRenderWindowInteractor` + cone and tears it down four ways (`naive`, `finalize_then_destroy`, `robust`,
`robust_norefs`). Under Xvfb/llvmpipe **every** mode prints the "TkRenderWidget destroyed before its
vtkRenderWindow" warning **and still exits 0 (`CLEAN EXIT`)**. So:

- The warning is **benign and unavoidable** — it fires on every teardown sequence, finalize-first or not.
- Finalize-before-destroy **ordering does not prevent the crash**. It's tidy, so it's kept, but it is not the fix.

## Root cause
The real fault is **GL-driver-specific**. The inspector (`Kraken3DInspector`), the STL-placement dialog and the
face-role dialog each embed a `vtkTkRenderWindowInteractor` over a **GLX** render window. Running the Tk + VTK
widget destructors at Python interpreter shutdown tears the render window down against a GL context that is
already going away. On **NVIDIA GLX** (the user's X299-SSD box, RTX 4070) that SIGSEGVs; on llvmpipe (Xvfb) it
does not — which is why it reproduces on the user's display but not headless here.

The three embedded Tk+VTK widgets:
- `KrakenOS/UI/open3d_inspector.py` (`Kraken3DInspector`)
- `KrakenOS/UI/panels/optical_stl_placement_dialog.py`
- `KrakenOS/UI/panels/main_optical_solid_face_roles_dialog.py`

## Fix
Don't run the crashy destructor chain on the interactive quit path. `KrakenOS/UI/layout_editor.py`,
`KrakenLayoutEditor.request_quit` now hard-exits:

```python
def request_quit(self) -> None:
    if not (self.headless or self._confirm_close_with_optional_save()):
        return
    if self.headless:
        self.destroy()          # headless/programmatic: tear down normally (tests, validators)
        return
    self._hard_exit_after_cleanup()

def _hard_exit_after_cleanup(self) -> None:
    # cancel pending Tk `after` callbacks
    ...
    self._shutdown_analysis_executor()               # no orphaned child processes
    self._shutdown_optimization_worker(force=True)
    sys.stdout.flush(); sys.stderr.flush()
    os._exit(0)                                       # skip every Tk/VTK destructor
```

`os._exit(0)` terminates the process immediately without running Python/Tk/VTK finalizers, so the NVIDIA GLX
teardown never happens. The only work that MUST NOT be skipped — shutting down the analysis/optimization worker
**processes** so none is orphaned — is done first, then the streams are flushed. The OS reclaims the GL contexts
and memory.

The **headless / programmatic path keeps the ordinary `destroy()`** — a hard-exit there would kill the test /
validator process that created the editor. `KrakenLayoutEditor.destroy()` also still finalizes the inspector's
render window before destroying it (the 68df71d9 ordering, kept as a tidy best-effort for that path).

Not caused by the 0293 import feature — this quit path is pre-existing and would segfault on any NVIDIA-GLX quit
with a VTK widget having been created. The user hit it because the new *Import Lens from Folder…* CAD-menu entry
opened the 3D inspector.

## Guard + gate
`KrakenOS/UI/validate_open3d_vtk_teardown_ordering.py` (`run_checks()`) — display-free source contract:
- `request_quit` hard-exits the interactive path via `_hard_exit_after_cleanup`, and keeps `destroy()` on the
  `headless` branch.
- `_hard_exit_after_cleanup` calls `os._exit(...)` **after** `_shutdown_analysis_executor()` /
  `_shutdown_optimization_worker(...)` (workers down before the hard exit → no orphans).
- Still-correct best-effort ordering: `_destroy_vtk_render_window` calls `Finalize()`; `_on_close` and
  `KrakenLayoutEditor.destroy` finalize the render window **before** destroying the inspector widget;
  `WM_DELETE_WINDOW` routes through `_on_close`.

Penta **phase 258**, baseline updated (title now "Interactive app quit hard-exits before the NVIDIA-GLX-crashy
VTK teardown").

## Owed / limitation
The guard is a source contract, not a live run. The real crash needs an **NVIDIA GLX display**; there is no GLX
GPU on the headless box (the Tk-embedded widget needs GLX, not the EGL offscreen path), and Xvfb/llvmpipe does
not reproduce it. **In-app eyeball owed** — open the Open 3D inspector, then quit the app and confirm a clean
exit (the benign warning may still print, but there must be **no core dump**).
