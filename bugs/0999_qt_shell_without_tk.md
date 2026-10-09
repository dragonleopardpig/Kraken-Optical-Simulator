# 0999 -- the Qt shell can run with no Tk at all

Phase 7f of the Qt migration (docs/design_qt_migration.md): the editor without a Tk root
(bugs/0993) and the inspector without a Tk window (bugs/0998), together, in the real shell.

## What it is

`KRAKEN_QT_TK_FREE=all` starts the Qt shell with neither: `qt/app.py` builds the editor with
`tk_root=False`, `qt/inspector_view.py` the inspector with `tk_window=False`. It is on request,
EXPERIMENTAL, until it is the default. `KRAKEN_QT_TK_FREE=inspector` (bugs/0998) leaves only the
inspector's window out.

Measured in one process -- the shell started, the 3D scene built, a session driven:

| | Tk roots | Tk widgets | Tk variables |
|---|---|---|---|
| as it always was | 1 | 414 at start, +247 for the 3D scene, +73 in the session | 148 + 38 |
| `KRAKEN_QT_TK_FREE=all` | 0 | 0 | 0 |

## Measured: the Qt-era gate phases run that way

Phases 633-760 through the parallel gate with `KRAKEN_QT_TK_FREE=all` in the environment:
**124 pass, 4 fail of 128**. The four are guards that asked the hidden Tk application a question:

- phase 694 (`validate_open3d_0906_qt_hosts_inspector`) and phase 758
  (`validate_inspector_owns_its_window`): "the inspector's Toplevel is withdrawn". They now hold
  the truth of the mode they run in -- withdrawn, or none.
- phase 713 (`validate_open3d_qt_5g_face_roles`): listed the editor's Tk child windows to show
  that no Tk dialog opened. Without a root there cannot be one.
- phase 759 (`validate_editor_without_tk_root`): expected `winfo_exists` on a rootless editor to
  raise, which this step changes (below).

No product fault was found by the sweep. Four were found before it, by reading the editor's own
code for Tk calls on itself and trying them:

## Change

1. **`winfo_exists`.** `_schedule_refresh_plot` asks the editor whether it still exists before it
   schedules, by Tk's name -- and without a root that raised. The editor answers itself, as the
   inspector does since 0998: the root's answer with a root, exactly as before; "until it is
   destroyed" without; and one built with `__new__` still raises.
2. **Copy.** With no clipboard tool installed (`wl-copy`, `xclip`, `xsel`), copying rows or text
   fell back to Tk's clipboard by name. In the Qt shell that was the clipboard of a hidden
   application nothing pumps -- no other program could paste from it -- and of no application
   once there is no root. It goes to the shell's clipboard, the host's: under Tk the same clear,
   append and hand-over on the same root; in the Qt shell the Qt clipboard, in both modes.
3. **Paste.** It read Tk's clipboard by name. It reads the shell's.
4. **The plot auto-save** waited until the Tk window was 1200 x 700 -- a Tk test, in the
   toolkit-free analysis display. It is the Tk window builder's, the same numbers; without a Tk
   window there is nothing of Tk's to wait for.

## Proof that the Tk editor did not change

- `bugs/0999_tk_copy_paste_autosave.py`, a real Tk editor with no clipboard tool to be found: an
  element's three rows copied ("Copied 3 surface row(s) (Tk).", 3609 characters on the Tk
  clipboard) and pasted back from it; nothing pasted from an empty clipboard; a text copied; two
  plot refreshes scheduled, one run; the auto-save writing its picture in a 1700 x 950 window and
  waiting in an 1100 x 720 one. Identical at the commit before (twice) and after.
- `bugs/0993_tk_before_after.py`: the Tk-rooted editor's state over the 63-step session.

## Guard: `validate_qt_shell_without_tk` (phase 761)

Two Qt shells, as it always was and with `KRAKEN_QT_TK_FREE=all`, each driven through one session.

- **A:** on request the whole process makes no Tk root, widget or variable; the editor has no
  root, the inspector no window, the host made all 79 model variables; the 3D scene has the same
  actors.
- **S:** after each of 8 steps about 520 plain attributes of the editor and the inspector are
  equal in the two.
- **E:** the editor says it exists; a plot refresh it schedules is on the shell's host and runs
  once.
- **C:** with no clipboard tool, an element's three rows copied in the Qt shell are on the Qt
  clipboard, and Paste -- the editor's own copy cleared -- reads them from there, and nothing from
  an empty clipboard; in both modes.
- **P:** without a Tk window the auto-save does not wait and writes its picture; with the hidden
  Tk window it waits, as it always did; the Tk window's test is 1200 x 700.

## A mistake made on the way

The first run of this guard overwrote `attachment/2D.png`, the file the app's "Auto-save 2D PNG"
writes. The guard pointed the auto-save at a temporary file BEFORE the editor's module was
imported, and importing that module hands every service the real path again
(`_sync_layout_globals`). The picture there is now the guard's two-arm doublets scene; the file is
ignored by git, so it could not be put back from there. The guard sets the path after the import
and refuses to switch the auto-save on unless the path is its own; the later runs left the file
untouched (checked by its time and size).

## What is left of phase 7f

Making it the default: the Qt shell starts without Tk unless asked otherwise. The four guards
above already hold the truth of either mode.
