# 0979 -- the 2D bug flag's Tk windows: out of the recorder service

Phase 7d of the Qt migration (docs/design_qt_migration.md), second part, fifth service.

## What was there

`services/layout_bug_recorder.py` imported tkinter for two pieces of Tk in the Tk editor's own bug
flag (its Ctrl+Shift+B and toolbar button):

- the scan of the Tk windows open when the flag is taken -- each one's position and size, and
  whether it spills past the screen;
- the small window that asks for the flag's description without taking the editor away.

The Qt interface flags its whole window itself (bugs/0959) and never opens either.

## Change

- Both are `panels/main_bug_flag_windows.py`, class `MainBugFlagWindows` -- the same code, moved;
  the editor's two method names are unchanged, each a one-line delegation.
- What Save and Close DO is the service's, as two small methods any view can call:
  `_save_2d_flag_description` (description.txt, state.json's `description`, the status line) and
  `_keep_2d_flag_without_description`.
- The service imports no tkinter. Phase 738's list goes from three services to **two**. Phase
  723's list of Tk-only windows inside services loses this entry: one is left (System Selection).

Nothing a user sees changes.

## Guard: `validate_bug_flag_windows_view` (phase 746)

Nothing guarded the 2D flag before this, so the guard also runs it end to end. Every flag it takes
goes to a temp folder, and no screen grabber is run.

- **S:** the service imports and names no tkinter and builds no window; the panel defines both
  methods; the editor delegates both.
- **M:** with no display -- Save with words writes description.txt and state.json's description and
  keeps the other keys; Save with none, and Close, write nothing; a missing state.json or bundle
  folder is a debug line, never an error.
- **T:** a real Tk editor -- a flag taken with a 220 x 120 and a 9000 x 9000 window open lists both
  and marks only the second, and the status line counts it; the description window is titled for
  the bundle, is not modal, has Save, Close and Ctrl+Return; Save writes the words; Close (even
  with words typed) and the window's own close button leave the description empty.

## Checks

**Mutations: 12 of 12 caught.** Eleven at once: Save with no words writing an empty description,
not updating state.json, replacing it, or raising on a failed write; the service importing tkinter
again; the editor no longer delegating the scan; the scan walking nothing; no window ever marked
oversized; Close saving the typed words; the window made modal; its close button unwired.

The twelfth survived the first run: the description window parented to the PANEL object instead of
the editor. The panel forwards to the editor, so the window is built all the same -- only its
`master` differs, and a window whose master is not a widget is a trap for the next
`transient(master)` (bugs/0955). The guard now checks the owner, and catches it.

**Neighbouring guards, all pass:** the tkinter-import list (738: two services now), the inspector's
popups in both interfaces (723), the panel delegations (148), the Qt shell's own flag, the
interaction contract (655). **Baseline:** phase 746 recorded.
