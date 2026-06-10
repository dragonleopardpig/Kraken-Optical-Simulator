# 0045 — Surface Shape Builder button crashes with NameError (silent in UI)

**Status:** Fixed (2026-06-10).
**Component:** Editable-table Surface Shape Builder
(`KrakenOS/UI/services/layout_table_workbench.py`,
`open_surface_shape_builder` → `_main_surface_shape_builder_dialog`).
**Reported via:** user random-clicking 2D toolbar/table buttons:

```
File ".../layout_table_workbench.py", line 5753, in open_surface_shape_builder
    self._main_surface_shape_builder_dialog().open(row_index)
File ".../layout_table_workbench.py", line 5743, in _main_surface_shape_builder_dialog
    encode_custom_surface_value=encode_custom_surface_value,
NameError: name 'encode_custom_surface_value' is not defined
```

In the user's words: *"Can make unavailable options pop up message instead of
silent failing? OR are those bugs?"* — this one is a **bug**, not an unavailable
option. The traceback only reached the console, so in the UI the button looked
like it did nothing.

## Diagnosis

The big table/workbench region was extracted out of `layout_editor.py` into the
`LayoutTableWorkbenchMixin`. The extracted methods deliberately use *late-bound
editor globals*: `layout_editor.py` calls
`_layout_table_workbench_module._sync_layout_globals(globals())` at import time
(`layout_editor.py:2447`), which copies the editor module's globals into the
workbench module so the moved code keeps resolving the same names.

`_main_surface_shape_builder_dialog` passes a bundle of helpers to
`MainSurfaceShapeBuilderDialog`, including `encode_custom_surface_value`. That
symbol lives in `KrakenOS/UI/custom_surfaces.py`. Its sibling
`decode_custom_surface_value` is imported in `layout_editor.py:127` (and used
there at lines 1958/1960), so it gets synced into the workbench namespace and
resolves fine — the same file even calls `decode_custom_surface_value` directly
at workbench lines 5649/5726. But `encode_custom_surface_value` was **never
imported in `layout_editor.py`**, so the sync never carried it, and the workbench
reference at line 5743 was unbound → `NameError` the first time the dialog is
built.

It failed silently in the UI because Tkinter's default
`report_callback_exception` only prints the traceback to the console.

## Fix

Two parts:

1. **Root cause.** Import the symbol directly at the top of the workbench module
   (`KrakenOS/UI/services/layout_table_workbench.py`):

   ```python
   from KrakenOS.UI.custom_surfaces import encode_custom_surface_value
   ```

   This matches how the sibling service modules `layout_literals.py` and
   `layout_import_export.py` already import it, and makes the workbench
   self-sufficient instead of depending on the editor remembering to import and
   sync it. The sync never clobbers it (the editor's globals don't contain the
   name, so `_sync_layout_globals` leaves the direct import in place).

2. **No more silent failures.** Override
   `KrakenLayoutEditor.report_callback_exception` (`layout_editor.py`) so any
   uncaught Tk callback error still prints/logs the full traceback **and** shows
   a short dismissible `messagebox.showerror`, so a failing button is never
   invisible again. Suppressed when `headless` so automated/validator runs never
   block on a modal dialog. This directly answers the user's "pop up message
   instead of silent failing".

## Tests

`KrakenOS/UI/validate_surface_shape_builder_dialog_bindings.py` (display-free,
no Tk root / Xvfb): imports `layout_editor` (running the globals sync exactly as
the live app does), then AST-parses `_main_surface_shape_builder_dialog` and
asserts every free module-global name its body loads is bound in the workbench
namespace. This guards the whole class of "extracted method references a name
the editor never imported", not just this one symbol. Verified it PASSES after
the fix (9 free names, all bound) and FAILS if `encode_custom_surface_value` is
removed from the workbench namespace (reproduces the original NameError).

## Verification note

Confirmed headless that after `import KrakenOS.UI.layout_editor` the workbench
namespace binds both `encode_custom_surface_value` (direct import) and
`decode_custom_surface_value` (via sync), and that the
`report_callback_exception` override is installed on the editor class in place
of Tk's default.
