# 0294 — Segfault when importing a lens folder from inside the Open 3D inspector

The user opened the Open 3D inspector, used **Import Lens from Folder…** (the 0293 datasheet-only path) on
`attachment/Lens/PYRITE_56_80_10x_V38_1097785`, and as the import finished loading the app printed:

```
vtkTkRenderWidget.cxx:571  WARN| A TkRenderWidget is being destroyed before it[s] associated
vtkRenderWindow is destroyed. ...
Segmentation fault (core dumped)
```

**The crash is during the import, not on quit.** (The user confirmed: *"The crash happens after I loaded the
imported lens. The import is about to finish, and it crashes."*)

## First diagnosis (WRONG — reverted)
The warning text says "destroy the vtkRenderWindow before the UI", so this was first read as a *quit-time*
teardown-ordering bug and "fixed" two ways (commit 68df71d9 then e8374a33): finalize-before-destroy ordering,
then `os._exit(0)` on the interactive quit path. **Both missed** — the crash was never on quit. Two probes
settled it, both run on the user's real **NVIDIA RTX 4070 GLX** display (`DISPLAY=:0`):

- `bugs/probe_0294_vtk_teardown.py` — a bare `tk.Tk()` + `vtkTkRenderWindowInteractor` tears down cleanly
  (exit 0) in **every** mode (`naive`, `finalize_then_destroy`, `robust`, `robust_norefs`). The
  "TkRenderWidget destroyed…" warning is **benign**; the VTK/Tk teardown does **not** crash on NVIDIA.
- `bugs/probe_0294_import_crash.py` — drives the real inspector import handler; **reproduces the exit-139
  segfault** at the import's final refresh.

So the quit hardening was deleted (the app quits cleanly via the ordinary `destroy()` — proven exit 0 on NVIDIA).

## Root cause — use-after-free
`Import Lens from Folder…` is launched from **inside** the inspector
(`open3d_inspector.py: Kraken3DInspector.import_machine_vision_lens_from_folder`). Its flow:

1. `self.editor.import_machine_vision_lens_from_folder(dialog_parent=self)` builds the surrogate and loads it as
   the working layout via `load_layout_by_name`.
2. A complete layout load takes the replace branch → `_reset_complete_layout_runtime_state(close_viewers=True)`
   → `_close_scene_viewers_for_layout_replacement`, which ran **`self._three_d_inspector.destroy()`** — tearing
   down the very inspector whose handler is still on the stack (this is the benign warning).
3. Control returns to the handler, which calls **`self.refresh_from_editor(force_retrace=True)`** on the now
   **destroyed** `vtkTkRenderWindowInteractor` → use-after-free → **SIGSEGV on NVIDIA GLX**.

llvmpipe (Xvfb) survives the use-after-free, which is why it never reproduced headless — and why the whole thing
looked like an environmental render segfault at first.

## Fix
Keep the initiating inspector alive across the swap and refresh it in place.

`KrakenOS/UI/open3d_inspector.py` — `import_machine_vision_lens_from_folder`:
- Set `editor._keep_scene_viewers_across_layout_replacement = True` **before** the editor import, restored in a
  `finally` (so ordinary menu preset loads still close the 3D view).
- After the import, **guard `self.winfo_exists()`** (and `editor._three_d_inspector is self`) before touching any
  widget; if the inspector was torn down anyway, re-open a fresh 3D view via the live `editor` ref instead of
  refreshing the corpse.

`KrakenOS/UI/services/layout_table_workbench.py` — `_close_scene_viewers_for_layout_replacement`:
- Honour the flag: skip `inspector.destroy()` when `_keep_scene_viewers_across_layout_replacement` is set (the
  legacy PyVista plotter close is unchanged).

Result on NVIDIA (`bugs/probe_0294_import_crash.py`): exit 0, the inspector is the **same object** afterward,
refreshed in place — no destroy, no warning during import, no segfault.

## Guard + gate
`KrakenOS/UI/validate_open3d_import_from_inspector_survives.py` (`run_checks()`) — display-free source contract:
the import handler sets the keep flag *before* the editor import and restores it, and guards `winfo_exists()`
before the refresh; the workbench gates `inspector.destroy()` on `not keep_inspector`. Confirmed to FAIL against
the pre-fix source (5 failures) and PASS after. Penta **phase 258** (renamed
`phase_258_import_from_inspector_survives`), baseline title updated.

## Owed / limitation
The guard is a source contract. The real crash needs an **NVIDIA GLX display** (llvmpipe/Xvfb does not reproduce
it). Verified live on the user's RTX 4070 via `bugs/probe_0294_import_crash.py` (139 → 0). **In-app eyeball
owed** — open the Open 3D inspector, Import Lens from Folder…, and confirm the lens loads with the 3D view
refreshing in place (no core dump).
