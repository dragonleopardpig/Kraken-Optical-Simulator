# 0950 -- the inspector's small popups open in the running shell

Step 3 of "what is left" in `docs/design_qt_migration.md`, first part (the small ones).

## The gap

The 3D inspector builds eleven windows by hand as `tk.Toplevel`. The Qt shell hosts the real
inspector, so its commands run there, but a Tk window made under Qt is never seen. Worse, four of
the small ones wait on themselves (`wait_window`), which stops the Qt event loop: the shell freezes.

**Measured before**, driving each entry point in a real Qt shell on om05a_folded:

| Popup | Reached from | In Qt before | In Qt now |
|---|---|---|---|
| Field value / Field type (centred input) | Quick Estimation right-click, live controls | Tk window + freeze | the shell's text prompt |
| LED Edge Distance | the Object→LED arrow, menus | Tk window + freeze | the shell's number prompt |
| Edit Thickness | click a thickness arrow | Tk window (unseen) | the shell's number prompt |
| Resize Solid | right-click a STEP body | Tk window + freeze | a Qt row form |
| Bug-flag description | `s` / Flag bug | Tk window (unseen): the flag kept its screenshot, never its words | a Qt window, not modal |

## Change

- **`shell_host_of(owner)`** (`uihost/__init__.py`): the host to ask through when something other
  than Tk is drawing, else `None`. One question, asked in one place.
- **The Tk windows are unchanged for the Tk app.** Each is placed by hand so that it lands on
  screen under Wayland, or holds focus against the 3D canvas (bugs/0053). Each popup asks
  `shell_host_of` first and uses the shell's own prompt when there is one.
- **Centred input, LED Edge Distance, Edit Thickness:** `host.askstring` / `host.askfloat`, with
  the same title, prompt and prefill.
- **Resize Solid:** the fields, the rule and the apply are shared.
  - `_step_overlay_resize_target(texts, axes)` is the rule both views use: three free sizes, or one
    cross-section + depth for a coupled cube.
  - Under a shell the question is a `RowForm` shown through `present_row_form`.
  - One tightening: `inf` is now refused as "must be positive" (it used to pass the `> 0` test).
- **Bug-flag description:** what Save / Keep / Discard / close do moved into a toolkit-neutral
  session (`services/flag_description.FlagDescription`).
  - The Tk popup calls it; so does the new Qt window (`qt/dialogs/flag_description_dialog.py`),
    reached through a `show_flag_description` seam on the editor.
  - The Qt window is not modal, as the Tk one is not: a carry or drag stays live while it is open.

## A Qt trap found on the way

`QDialog.closeEvent` calls `reject()` and **ignores the close if the dialog is still visible
afterwards**. A `reject()` override that does its work but does not hide the dialog leaves the
window open after Save. The dialog ends through `super().reject()` now; the guard's Q5 checks the
window is gone.

## Guard: `validate_qt_inspector_popups` (phase 723)

- **S:** every function in `open3d_inspector.py` and `services/` that builds a `tk.Toplevel` asks
  the shell before it does, or is in `KNOWN_TK_POPUPS` with its reason. The list is exact, so it
  can only shrink: 11 builders, 5 shell-aware, 6 listed.
- **P:** the resize rule and its refusals (not a number; zero, negative, nan, inf).
- **Q1-Q5:** in a real Qt shell each popup asks through the shell and the answer lands in the model.
  - Q3: after typing V into Edit Thickness, the *next* prompt is prefilled with V.
  - Q4: sizes of 0 are refused and store nothing; typed sizes are stored as the target extents.
  - Q5: Save writes description.txt, state.json and the recording's event; Keep keeps the bundle
    without words; closing an empty box deletes it; Escape with typed text saves it.
- **N:** no Tk popup is created and nothing waits on one.
- **T:** in the Tk app the same five still open their own Tk windows (same titles), take the typed
  value, and ask nothing through `tkinter.simpledialog`.

**Mutation-checked:**
- `shell_host_of` always `None` (the popups stay Tk under a shell): the Qt half fails.
- `shell_host_of` always the host (the Tk app loses its own windows): the Tk half fails.
- no `show_flag_description` seam, and the centred prompt's shell branch removed: S names
  `_centered_input_dialog` as unlisted, and the Qt half fails.

**Seen by eye:** the Qt flag window and the Resize Solid form, rendered to PNG.

## Still Tk (listed in the guard)

| Popup | Why |
|---|---|
| Quick Estimation ×4 (target FOV, FOV popup, detector design, config table) | the next part of this step |
| 2D bug-flag description | the 2D flag has no Qt route yet (a Tk key binding; the shell's editor is headless and skips it) |
| System Selection Calculator (Tk window) | reached from the Tk menu bar only; the Qt action opens its row form |

## Noticed, not changed

Resize Solid calls the om05a **camera** body a "beam-splitter cube" and couples its cross-section.
The coupling detector (`solid_resize.detect_coupling`) is fooled by a 45° face on the camera's
B-rep. Same text in Tk; it predates this change.
