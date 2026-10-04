# 0952 -- edge tabs hide and show the panels; a small arrow folds the ribbon

User requests, 2026-10-04:
- "the slide out in top, bottom, left, right edge, can they be hide/unhide by introducing vertical
  tab on the left/right window edge? Horizontal edge for Top and Bottom slide out."
- "please also make the ribbon palette hide/unhide with a small arrow just like other popular
  apps."

## Edge tabs (`qt/docks.py`: `EdgeRails`, `RailTab`)

A slim strip on each window edge carries one tab per panel docked on that edge.

| Edge | Tabs | Text |
|---|---|---|
| Left | Scene Components | upright, reads bottom to top |
| Right | System, Source, Trace, Optimization, 3D Live | upright, reads top to bottom |
| Top | Surface Table | flat |
| Bottom | Debug, Progress, Results | flat, at the right end of the status bar |

- **The bottom strip is the status bar.** A second row there would cost the 3D scene 29 px for
  nothing (measured on a 1000-px screen: 3D view 400 px with a row, 425 px without).
- **A tab is down exactly while its panel is on show.**
- **A click on a tab:**
  - of a hidden panel shows it, with the panels it was tabbed with, itself in front;
  - of a panel behind another tab brings it to the front;
  - of the panel on show hides it, together with the panels tabbed with it. One click folds that
    edge's stack and gives its room to the scene.
- **A hidden panel comes back at its size.** Qt brings a re-shown dock back at its minimum
  (measured: the surface table at 124 px where it had been 170), so the rail remembers the size.
- **A panel dragged to another edge takes its tab along**, redrawn for that edge. A panel closed
  by its own button lifts its tab.

## The ribbon's fold arrow (`qt/ribbon.py`)

A small arrow at the end of the ribbon's tab row, after the search box: up while the ribbon is
open, down while it is folded to its tab row. It does what a double-click on a tab already did.
The height it frees goes to the 3D scene (bugs/0951).

## Guards

- **`validate_qt_scene_layout` (phase 724)**, claims R, H, M, A:
  - **R:** the tabs per edge are the ones above; upright on the left and right, flat on top and
    bottom; each strip is on its window edge; every tab's down-state is its panel's.
  - **H:** Scene Components (300 px) hides and the scene gains 306 px, then comes back. Right
    stack: "Trace" comes to the front; "Trace" again folds all five (scene +406 px); "Source"
    brings all five back with Source in front. "Debug" hides only itself. The table hides (scene
    +176 px) and comes back at its height (+0).
  - **M:** Debug docked on the left gets an upright tab on the left strip; docked back, a flat one
    below. Progress closed by its own button lifts its tab; the tab brings it back.
  - **A:** the arrow is in the tab row; one click folds (arrow down, ribbon 116 -> 30 px, scene
    +86 px, table unchanged); another opens it.
- **Ribbon guard (phase 714):** T counts the table's width between the edge strips.

**Mutation-checked:**
- the ribbon not putting its neighbours' heights back, and a tab hiding only its own panel: A and
  H fail;
- a tab that does nothing: H and M fail.

**Seen by eye** at 2560 x 1440: the default layout, and every panel folded with the ribbon folded
(3D scene 2502 x 1247 px).

## Not done

- The arrangement is not saved between sessions (it was not before either).
- The ribbon has no tab on the top strip: it folds by its own arrow.
