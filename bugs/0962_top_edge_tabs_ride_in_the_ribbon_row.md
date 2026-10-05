# 0962 -- the top edge's panel tabs ride in the ribbon's tab row

Follow-up of bugs/0961 (Clean 3D Scene). Recommended next; the user said "please proceed
recommended next."

## What was wrong

The edge tab strips (bugs/0952) are toolbars on the window's edges. The left and right ones are
narrow, and the bottom one lives in the status bar. The TOP one had a row of its own above the
ribbon: 30-36 px of height for ONE tab ("Surface Table") and the Hide All button. Clean 3D Scene
could not put it away, because it is how a panel comes back. So even the "clean" 3D view lost that
row.

## Change

- **While the ribbon is docked at the top,** the top strip sits in the ribbon's tab row, between
  the last ribbon tab and the search box, exactly as tall as that row (26 px). The window has no row
  above the ribbon any more.
- **Undocked** (floating) or docked at the bottom, the ribbon gives the strip back: it is the
  window's top row again, as before. Docked at the top again, it takes it back.
- **It is the same strip object.** `EdgeRails` keeps adding and moving tabs on it wherever it sits:
  a panel dragged to the top edge still gets its tab there.

`KrakenQtMainWindow._place_top_rail`, run when the ribbon docks, undocks or moves;
`Ribbon.corner_row` is the corner's layout.

## Measured (om05a_folded, a 1916x1034 window)

| | before | after |
|---|---|---|
| 3D view, default panels | 1124x559 | 1144x599 |
| 3D view, Clean 3D Scene | 1836x931 | 1856x971 |

At 1500x950 the clean scene goes from 84 % of the window to 90 %. The side strips also gain
height, since nothing sits above them now.

## Guards

- **`validate_qt_clean_scene` (phase 731), new claim E:**
  - the top strip is inside the ribbon's tab row, no taller than it (26 of 26 px);
  - no toolbar row above the window;
  - its Surface Table tab still hides the table (the scene +176 px) and brings it back;
  - undocked, the ribbon leaves the strip as the window's top row (`EdgeRailTop`);
  - docked again, it takes the strip back and the scene returns to the same height.

  C's bar for the clean scene is raised from 80 % to 85 % (90 % measured).
- **`validate_qt_scene_layout` (phase 724), claim R re-pointed:** the top tabs are in the ribbon's
  tab row while the ribbon is docked, else at the window's top edge.

**Mutation-checked:**
- the strip never moved: E fails;
- never moved back when the ribbon floats: E fails.

**Seen by eye:** docked folded, docked in clean mode, and undocked, at 1916x1034.

**Other guards run:** the scene layout (724), the ribbon (714), the Qt-hosted inspector (0906), the
5f toolbar guard, the shell flag (729) and the clean scene (731) all pass.

## Gates

**Not gated on its own** (user, 2026-10-05: "why need to run all the tests and phases each fix? I
think this slows down a lot. Why can't run after a few round of fix?"). A fix now gets:
- its own guard, mutation-checked;
- the guards that read the code it changed.

The full gate runs every few fixes, and the next one covers 0962. The last full gate: 730 of 730
at 3265c622 (0961).

**Covered:** full gate 733 of 733 at 8403abde (2026-10-05, M90aPro), Qt-hosted harness 352 of 352 -- the record is in bugs/0965.

