# 0973 -- OPEN: choosing an insertable layout over a scene makes Save overwrite the shipped layout

**Status: open. Found while checking 0972; nothing is changed yet -- the remedy is a choice (below).**

## What happens

Six common layouts are "insertable" (`_is_insertable_common_layout`: Doublet Lens, F-Theta Lens 50mm
Figure 8, F-Theta Lens 50mm Wavefront 0 Deg, Flat Mirror 45 Deg, Ideal 2F Lens, Single Lens -- the
six the Common Component menu lists). Choosing one of them from the **Layouts** menu while a scene is
open does not replace the scene: the loader **appends** it (status: "Appended ...").

But the same call has already pointed the scene at the appended layout's own file. Measured in the Tk
editor, on temp copies of the two shipped files:

| Step | Rows | The scene's file |
|---|---|---|
| Layouts > Single Lens | 4 | `single_lens.py` |
| Layouts > Doublet Lens (appended) | 7 | **`doublet_lens.py`** -- the title bar says so too |
| File > Save | 7 | `doublet_lens.py` is overwritten with the merged 7-row scene, no question asked |

So one Save does two wrong things: the shipped Doublet Lens layout is replaced by the user's scene,
and the file the user was working in is not saved.

It is in both interfaces -- the loader is the model's -- and it predates the Qt work. 0972 gave the
Qt interface the Layouts menu, so it is reachable there now as well.

## Cause

`load_layout_by_name` (`services/layout_table_workbench.py`) sets `self.current_layout_file = path`
on its first lines, before it decides `append_to_existing`. The sibling
`insert_layout_component_by_name` (Insert > Common Component) ends with
`self.current_layout_file = None`.

## The choice

| | After an append, the scene's file is | Save then |
|---|---|---|
| A | the file it had before the append | writes the user's own file -- what the title bar already promised |
| B | none (untitled), as Insert > Common Component does | asks where to save |

A keeps the user in their file; B is the more cautious and is what the other insert path does today.
With A, Insert > Common Component would be the odd one out (it untitles a scene that had a file).
Either removes the overwrite.

## How it was found

A mutation check for 0972 made the Common Component entries call the layout loader instead of the
inserter, and the Qt claim still passed: the rows grew by three either way. The only thing that told
the two apart was the scene's file.
