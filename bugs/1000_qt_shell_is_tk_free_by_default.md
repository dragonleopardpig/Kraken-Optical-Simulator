# 1000 -- the Qt shell starts without Tk

Phase 7f of the Qt migration (docs/design_qt_migration.md), its last step: what bugs/0993-0999
made possible on request is how the Qt shell starts.

## What changes

Started with nothing asked for, the Qt shell builds the editor with no Tk root and the 3D
inspector with no Tk window. In one process -- the shell started, the 3D scene built, a session
driven:

| | Tk roots | Tk widgets | Tk variables |
|---|---|---|---|
| before | 1 | 414 at start, +247 for the 3D scene, +73 in the session | 186 |
| now | 0 | 0 | 0 |

A Tk call that is still made somewhere on the editor or the inspector no longer reaches a hidden
window nobody sees: it raises.

`KRAKEN_QT_TK_FREE` (`KrakenOS/UI/qt/tk_free.py`) asks for something else:

    KRAKEN_QT_TK_FREE=0            the hidden Tk application, as it was
    KRAKEN_QT_TK_FREE=inspector    only the inspector has no Tk window
    KRAKEN_QT_TK_FREE=all          the default (also unset, empty, 1)

The Tk interface is not touched by any of this: `KrakenLayoutEditor()` builds its root and its
panels as it always did, and both interfaces stay.

## What it rests on

- **The same model.** An editor without a Tk root equals the Tk-rooted one in every plain
  attribute after each of 63 steps of editing, inputs, settings, analyses, a saved file,
  tolerances and the optimizer, and saves the same file byte for byte (phase 759). The hosted
  inspector without its Tk window holds the same state as the one with (phase 760). The whole Qt
  shell without Tk equals the one with its hidden Tk application over a session (phase 761).
- **The Qt shell's own guards.** The Qt-era gate phases (633-760) run without Tk: 124 of 128 as
  they were; the other four asked the hidden Tk application a question and now hold either
  mode's truth (bugs/0999).
- **The harness hosted in the Qt shell.** Its 352 phases pass without Tk, in 17 minutes where
  the hidden Tk application made it 44.
- **The full Tk gate** before the switch was thrown: see below.

## What was found on the way to here (bugs/0993-0999)

Not one of these was about Tk going away -- each was something that only worked, or failed
unnoticed, because a Tk object happened to be there:

- 0993-0995: the editor's pane layout, three model reactions, the field state, the debug log, a
  start value, the atmosphere's numbers, which inputs apply, the optimizer's operands;
- 0996: the same scene saved twice gave two different files;
- 0997: Stop pressed right after Start did not stop the optimizer's worker;
- 0998: the FOV dialog promised after a lens swap never opened in the Qt shell;
- 0999: Copy and Paste without a clipboard tool used the clipboard of a hidden application
  nothing pumps; a scheduled plot refresh could not be scheduled without a root.

## Guards

- `validate_qt_shell_without_tk` (phase 761), claim A: started with NOTHING asked for, the whole
  process makes no Tk object; and the switch means what it says -- unset, empty, `all` and `1` are
  "all", `0` and `off` the hidden Tk application, `inspector` the inspector alone, anything else
  is refused. It compares the default with `KRAKEN_QT_TK_FREE=0`.
- `validate_inspector_without_tk_window` (phase 760) compares `0` with `inspector`.
- The four mode-aware guards of bugs/0999 run in the default, which is now the Tk-free one.

## What is left

Phase 7g -- the validators off Tk. The 94 guards that build a headless editor still build one
with a Tk root (and use its hidden Tk table); the Tk interface's own guards stay as they are.
`KRAKEN_QT_TK_FREE=0` and `=inspector` can go once nothing compares against them.
