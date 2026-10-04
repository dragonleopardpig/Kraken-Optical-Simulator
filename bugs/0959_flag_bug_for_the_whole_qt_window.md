# 0959 -- Flag Bug for the whole Qt window, from anywhere in it

Follow-up of bugs/0950 (the flag's description prompt) and of the two flags of 2026-10-04
(bugs/0957, bugs/0958). Recommended next; not flagged by the user.

## The gap

The bug flag is the user's reporting channel, and in the Qt shell it covered one part of the
window:

- **`s` shows only the 3D scene.** Its picture is the VTK render and its state is the scene. A
  flag about the ribbon, the surface table, an edge panel or a dialog had no picture of the thing
  it was about. ("The slide-outs overlap each other", bugs/0951, could not have been shown by a
  flag.)
- **`s` only works with the pointer over the scene.** There was no flag from the table, a panel
  or a dialog.
- **The Tk editor's own flag had no route.** Ctrl+Shift+B there records the whole screen, the 2D
  plot and every open dialog (it was made for a dialog taller than the screen). The Qt shell's
  editor is headless and never reaches it. This was the last open item of migration step 3.

## Change

**One command, Flag Bug**, reachable three ways:

| Where | What |
|---|---|
| Ctrl+Shift+B | the Tk editor's key; works in the main window and in any dialog, a modal one included |
| the small flag in the ribbon's corner | on every tab, and showing while the ribbon is folded |
| File > Application > Flag Bug | the ribbon entry every command has; also in the command palette |

**Every flag made in the Qt shell now carries the window**, whichever way it was made:

| File | `s` in the scene (about the scene) | Flag Bug (about the window) |
|---|---|---|
| `screenshot.png` | the 3D render with the pointer crosshair, as before | the window in front: the main window, or the dialog over it |
| `window.png` | the whole main window | the main window, when a dialog is the screenshot |
| `scene_3d.png` | -- | the 3D render |
| `window_<n>.png` | every other window on screen | every other window on screen |
| `layout_state.json` | the rows + settings as they are now | the same |
| `state.json` | as before, plus a `shell` block | the same; `screenshot_kind` is `window` or `dialog` |

- **The pictures are drawn by Qt, not taken from the screen.** They need no screenshot tool, do
  not depend on the compositor, and never show another application. A window is pictured whole
  even where it runs off the screen.
- **The 3D scene is painted in.** A VTK view draws through its own GL window, which Qt's own
  drawing cannot see; each one is rendered by VTK and placed where it sits in the window.
- **A crosshair marks the pointer** on the window's picture.
- **The `shell` block** says: window and screen sizes; the ribbon's tab and whether it is folded;
  each panel (visible, showing or behind a tab, undocked, where, how big); each open window
  (title, size, modal, in front, exceeds the screen); what has the keyboard; what the pointer is
  over, as a widget path (for example the surface table's dock).
- **`layout_state.json`** holds the live rows. Unsaved edits are not in the layout file, so the
  file named in `state.json` cannot stand in for them.
- **With no 3D inspector** (it could not be built) Flag Bug still writes a bundle: the window, the
  build, the layout's identity and the shell block.

## How it is built

- **Model side:** `flag_bug(subject="scene" | "window")` in `open3d_inspector.py`. Under a shell it
  asks one new seam, `capture_flag_shell(bundle_dir, as_screenshot=...)`, for the shell's pictures
  and state. Without that seam -- the Tk app -- the bundle is exactly as before.
- **View side:** `qt/flag_capture.py` draws the windows and builds the block.
  `KrakenQtMainWindow.flag_bug_action` runs the command.
- **No inspector:** `services/shell_flag.py` writes the bundle.
- **The key in a dialog:** a window's shortcut does not reach its dialogs, and a modal dialog
  shuts the window out altogether. Each window that takes the keyboard is given the Flag Bug
  action (`_offer_flag_bug`, on `focusChanged`). It is the same action, so one press is one flag.
- **The description box under a modal dialog** belongs to that dialog. As a window of the main
  window it would be shut out and could not be typed in. When the dialog closes, typed text is
  saved and an empty box keeps the bundle.
- **A flag's own description box** is never the subject of a flag and is not given the action.
- **A pop-up is not given the action either.** A menu shows its actions, so it would have grown a
  Flag Bug entry.

## Guard: `validate_qt_shell_flag` (phase 729)

In a real Qt shell on `beam_splitter_two_arm_doublets` (in git, so it never skips for missing
vendor CAD); bundles go to a temp folder.

- **P:** when a window "exceeds the screen" (9 cases).
- **N:** with no inspector, Flag Bug writes a bundle and asks for the words; Discard deletes it.
- **W:** the real key with the keyboard in the scene writes one bundle. The screenshot is the
  whole window at its own size; the scene region equals the 3D render in 100 % of its pixels; the
  crosshair is at the pointer; the state names the dock under the pointer, the ribbon's tab, the
  panels; `layout_state.json` has the model's 12 rows.
- **K:** one press, one flag: 1 from the surface table, 0 inside a flag's own description box; a
  menu that takes the keyboard keeps its one entry.
- **S:** the `s` flag keeps the 3D render as its screenshot and adds `window.png`.
- **T:** without the shell's seam the bundle is the three files it was.
- **D:** the key pressed in a real report dialog: the screenshot is that dialog, listed by title
  as the window in front; the main window is `window.png`.
- **M:** a modal dialog: the key works in it; the description box belongs to it and takes keys
  sent through the window system; closing the dialog saves typed text and keeps an empty box.
- **O:** a dialog 300 px taller than the screen is flagged as exceeding it and pictured whole.
- **R:** the corner button shows on every tab, ribbon open and folded; one click, one bundle.

**Mutation-checked:**
- no seam: W, S, T, D, M and O fail;
- the action not offered to dialogs: D and M fail;
- no VTK paint-in: W fails;
- no fallback without an inspector: N fails;
- the description box always a window of the main window: M fails (it gets no keys);
- the description box offered the action: K fails;
- a pop-up offered the action: K fails (the menu lists "Flag Bug");
- the subject always the main window: D and M fail.

**Seen by eye:** the whole-window picture on om05a_folded (ribbon, table, panels, scene, crosshair),
a row form as the screenshot, the File tab and the folded corner.

**Other guards run:** ribbon, menu parity, scene layout, inspector popups, the Qt-hosted inspector
(on the 1600x1000 display), the toolbar guard, and the five older flag guards pass.

## Gates

- **Full Tk gate with 0959: 728 of 728 phases pass**, in parallel (`tools/penta_parallel_gate.py
  --jobs 4`), 41.9 min; no group was killed (lowest free memory 3.2 GB).
- **The Qt-hosted harness (`--shell qt`): 352 of 352 pass.**

## Noticed, not changed

- **A flag takes about 5 s on om05a_folded, and it did before this change** (4.9 s without the
  shell's part, 5.0 s with it). The time is the recorder's scene snapshot: for the imported optical
  solid it re-inspects the STL mesh (4.1 s) and re-runs the STEP reconstruction (3.6 s) on every
  flag. The app is frozen for that long after `s`. Worth a cache; a bug of its own.
- Two `devenv shell` commands started in the same instant race on devenv's GC root; one dies with
  "Failed to remove existing GC root" before running anything. Start them a few seconds apart.
- `QTest.qWaitForWindowActive` is not a test that a dialog is the active window: it is true while
  the window the dialog belongs to is active. The guard polls `QApplication.activeWindow()`.
