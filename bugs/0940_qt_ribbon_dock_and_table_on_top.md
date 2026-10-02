# 0940 -- the ribbon docks / undocks; the surface table runs across the top

User requests (2026-10-02, on the Qt shell):
1. "The ribbon tab looks nice, but can it be dock and undock?"
2. "The surface editor table slide from the left edge, but it is long across horizontally, perhaps
   shift it to the top so that it slides down."

## 1. The ribbon is a dock

It was a locked QToolBar. It is now a QDockWidget (`RibbonDock`).
- **Title bar:** its title bar runs down the LEFT edge (`DockWidgetVerticalTitleBar`), so docking
  costs no height.
- **Undocking:** the float button or a double-click on that bar undocks it into a window of its
  own. Dragged back to the top or bottom edge, it docks again. `Ribbon.set_floating(bool)` does
  the same in code.
- **Floating:** the window opens fully, since it costs the 3D view nothing.
- **Re-docked:** it returns to its previous state, folded on a short screen, and gives the 3D
  view its height back.
- **Fixed height when docked:** the docked ribbon has a FIXED height equal to its content. With
  only a maximum, re-docking kept the floating window's ~114 px under a 30-px cap (measured).

**A bug found on the way (since 0935).** Unfolding the ribbon showed every tab page by hand, and
all four were drawn over each other. It was visible in the floating window, and on a docked
double-click unfold too. Folding now hides the tab widget's page stack instead, so Qt keeps
exactly the current page visible.

## 2. The surface table is across the top

`SurfaceTableDock` moved from the left column to the top dock area, between the ribbon and the 3D
inspector, at full window width:
- all columns show without sideways scrolling (AxisMove takes the slack);
- its rows run downward;
- it starts about five rows tall (`TABLE_DOCK_HEIGHT`, set once the layout has run) and can be
  dragged taller.

**Height budget.** The 3D view must keep >= 400 px on the gate's 1000-px screen (phase 707's L,
and 714's F). With the table on top it dropped to 326 px. The middle band was 204 px because the
right column stacked Results (86 px minimum) over the input-form tab stack.
- **Results moved to the bottom row**, beside Debug and Progress; the 1920-px screen has width to
  spare there.
- 3D view, measured:

  | Screen | Docked, folded | Docked, unfolded | Ribbon floating |
  |---|---|---|---|
  | 1000 px (gate) | 400 | -- | 428 |
  | 1920×1080 (the user's DP-2) | 482 | 413 | 511 |

## Guard

`validate_qt_ribbon` (phase 714) gains three claims:
- **D**: undocked, the ribbon floats with EXACTLY ONE page visible (the current one) and unfolded.
  Docked again it is in the top area, folded, at its tab-row height (30), and the 3D view is back
  to 400.
- **U**: docked and unfolded, exactly one page shows; folded, none.
- **T**: the table is in the top area, ribbon < table < inspector top to bottom, at the window's
  full width.

Mutation-checked: putting back the show-every-page unfold fails D and U (`pages visible [0, 1, 2,
3]`).

**Gated:** all 57 Qt-shell phases (634-654, 669-695, 704-716) pass, in three parallel batches; the `--shell qt` harness gate passes 352/352 with the inspector in the new layout.
