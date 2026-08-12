# 0616 — The 's' flag-bug hotkey dies after a right-click replace/swap (FIXED)

Flag `flag_20260812_140652_363` (second complaint): *"the 's' shortcut not working
after this, I have to click 'Flag bug' button"* — after the camera replace+flip flow.

## Root cause — a deliberate skip with no follow-up

The 's' hotkey binds on the inspector toplevel and the VTK widget; it fires only while
keyboard focus is inside the inspector. The bugs/0348 menu-dismiss machinery restores
focus to the canvas after an ordinary entry click, but deliberately SKIPS its focus
grab while a modal dialog holds the Tk grab (so the dialog keeps keyboard focus).
Dialog-opening entries — "Replace Camera from Folder..." (folder chooser + flange
prompt), "Replace ... STEP..." (file chooser), "Swap Imaging Lens from Folder..." —
therefore end with focus stranded wherever the last dialog left it (typically the main
2D window), and the hotkey is dead until the user clicks the canvas.

## Fix

`_restore_canvas_focus()` in the face-assignment service — the same guarded
`grab_current() is None → focus_set()` the dismiss path uses — called in `finally`
from the dialog-opening context handlers (`_replace_step_overlay_from_context`,
`_swap_imaging_lens_from_context`). Runs after the dialog chain closes, never while a
modal still holds the grab.

Guard: phase 333 asserts both handlers restore canvas focus.

## Part 2 of the flag — "please check everything correct?"

Verified end-to-end on the user's exact configuration (BC-OM25M12X2-M58 replace +
flip) — see the verification numbers in the session record: seat exact at the vendor
front_to_sensor, pose persisted, ray census unchanged by the display-only flip.
