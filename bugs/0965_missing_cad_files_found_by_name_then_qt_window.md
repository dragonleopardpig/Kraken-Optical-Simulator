# 0965 -- missing CAD files: found by name first, then a Qt window for the rest

The user chose option 1 (2026-10-05, "proceed"): find by name first, a Qt window only for what is
still missing, and a command to open it again.

## What was wrong

When a layout names STEP / STL files that are not on disk, the load opens the missing-assets
window (Locate, Locate folder, Skip). In the Qt shell that window was a Tk window on the hidden Tk
root, with no Tk event loop: invisible or frozen. The layout loaded with placeholders and there was
no way to fix it.

## Change

- **`services/missing_assets_session.py`** holds everything the window did -- Locate, Locate
  folder, Skip, Skip all, Reset, and the rebuild on close -- plus **find by name**
  (`auto_locate`). A missing file whose name matches exactly ONE file under the layout's folder or
  the project's `attachment/` folder is pointed at it. A name that matches two different files is
  left for the user, because a guess could put the wrong part in the scene.
- **The load** (`_prompt_for_missing_cad_assets`):
  - finds by name first, and logs each file found to the progress log;
  - the status line says "Found N missing CAD file(s) by name", and to save the layout to keep the
    new paths;
  - only what is still missing opens a window: the shell's (`show_missing_assets` -> a non-modal
    Qt dialog, `qt/dialogs/missing_assets_dialog.py`) or the Tk one (now a view of the same
    session).
- **Ribbon:** Scene > CAD > **Missing Files** ("Resolve Missing CAD Files..."), also in the command
  palette, opens it again, or says nothing is missing.

## Guard: `validate_missing_assets_found_by_name` (phase 734)

P1, P2 (the session), L (the load's step), Q (the Qt shell) and T (the Tk window) all pass,
run once, alone, at low priority.

**NOT yet done** (the user stopped the session to leave):
- the mutation checks;
- the neighbouring guards: 0810 (it drives `MissingAssetsDialog.run(..., assets=...)` -- the call
  shape is kept), the model-forms census (validate_qt_model_forms_open_in_qt; its entry updated to
  the new count, 6 tkinter calls), the ribbon guard (a new action and icon), and the inspector
  popups guard;
- recording phase 734 in the baseline.

**Full gate still owed** for 0962-0965. Run it only when the user asks, possibly on another host.
