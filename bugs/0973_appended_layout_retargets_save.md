# 0973 -- choosing an insertable layout over a scene made Save overwrite the shipped layout

**Fixed with option A -- recommended, and the user said to go ahead (2026-10-06): after an append the
scene keeps the file it had.** (Option B was to untitle the scene, as Insert > Common Component does.)

## What happened

Six common layouts are "insertable" (`_is_insertable_common_layout`: Doublet Lens, F-Theta Lens 50mm
Figure 8, F-Theta Lens 50mm Wavefront 0 Deg, Flat Mirror 45 Deg, Ideal 2F Lens, Single Lens -- the
six the Common Component menu lists). Choosing one of them from the **Layouts** menu while a scene is
open does not replace the scene: the loader **appends** it (status: "Appended ...").

But the same call had already pointed the scene at the appended layout's own file. Measured in the Tk
editor, on temp copies of the two shipped files:

| Step | Rows | The scene's file, before the fix | After the fix |
|---|---|---|---|
| Layouts > Single Lens | 4 | `single_lens.py` | `single_lens.py` |
| Layouts > Doublet Lens (appended) | 7 | **`doublet_lens.py`** -- the title bar said so too | `single_lens.py` |
| File > Save | 7 | `doublet_lens.py` overwritten with the merged scene, no question asked | `single_lens.py` written; `doublet_lens.py` untouched |

So one Save did two wrong things: the shipped Doublet Lens layout was replaced by the user's scene,
and the file the user was working in was not saved.

It was in both interfaces -- the loader is the model's -- and it predates the Qt work. 0972 gave the
Qt interface the Layouts menu, which made it reachable there as well.

## Cause

`load_layout_by_name` (`services/layout_table_workbench.py`) set `self.current_layout_file = path`
on its first lines, before it decided `append_to_existing`.

## Change

The loader notes what the scene is before it starts -- its file and its transient-import mark
(bugs/0375). When it appends, it puts both back, and it leaves the three selector names alone. An
appended layout is a component the scene took in; the scene did not become that layout.

- A scene opened from a file keeps that file and its title; Save writes it.
- An untitled scene stays untitled; Save asks where.
- A transient import (a fresh lens import, title "* name") stays one; Save still asks rather than
  write over the generated file. Before, an append silently cleared that mark as well.
- A load that **replaces** the scene is unchanged: it takes the loaded layout's file and name.

## Not changed

- ~~Insert > Common Component still untitles the scene~~ -- **changed in bugs/0975** on the user's
  word: it keeps the scene's file too.
- A scene opened from the Layouts menu and then saved still writes the shipped layout's file, as it
  always has: that is the file the scene was opened from.
- The append also clears the learned folded-magnification state at the top of the loader and, unlike
  a replacing load, does not ask for it to be measured again. Not examined here.

## Guard: `validate_appended_layout_keeps_scene_file` (phase 741)

Every claim works on temp copies; nothing under the repository can be written.

- **A:** a scene opened from the user's own file (File > Open) takes in Doublet Lens -- 4 to 7 rows,
  status "Appended", and the file, the title and the selector names are what they were.
- **S:** Save asks nothing and writes the user's file; the scene emptied and the file opened again
  gives the merged 7 rows; `doublet_lens.py` is byte for byte as it was.
- **U:** an untitled scene stays untitled; Save asks once and writes there.
- **I:** a transient import stays marked, title "* my_bench.py"; Save asks instead of writing over it.
- **H:** open, append, undo, redo -- rows 4, 7, 4, 7, one file throughout.
- **R:** a replacing load still takes the loaded layout's file, name and a clean mark -- an
  insertable layout from the empty starter, and a layout that is not insertable over an open scene.
- **T / Q:** through the real menu entries of both interfaces (Layouts > Single Lens, Layouts >
  Doublet Lens, Save): the title stays `single_lens.py`, Save asks nothing, rewrites that file and
  leaves `doublet_lens.py` as it was; in Qt the table follows and no Tk window opens.

The model claims skip the 2D redraw (it cost three minutes of the run); T and Q go through it.

## Checks

**Mutations: 6 of 6 caught, each by exactly the claims meant to catch it** -- the bug put back (A, S,
U, I, H, T, Q); an append clearing the transient mark (I); an append untitling the scene, the option
not taken (A, S, I, H, T, Q); the selectors taking the appended name (A); a replacing load keeping
the old file (R, T, Q) or the old mark (R). And the 0972 mutation that led here -- a Common
Component entry that loads instead of inserting -- is still caught by that guard (P4, T, Q).

**Neighbouring guards, all pass:** the menus (740), the window title (0637), the unsaved-import
mark (0375), the deferred load trace (0646), the flag's layout identity, the table component
workflow, the interaction contract (655).

**Baseline:** phases 741 and 740 recorded (pass; 740 phases). The full Tk gate is owed since 8403abde.

## How it was found

A mutation check for 0972 made the Common Component entries call the layout loader instead of the
inserter, and the Qt claim still passed: the rows grew by three either way. The only thing that told
the two apart was the scene's file.
