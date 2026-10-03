# 0949 -- the Qt shell is ribbon-only: no menu bar

User request, 2026-10-04: "now is mixture of Menu style and Ribbon tab style. Can we just change
everything to ribbon tab style?"

## What was there

The Qt shell had two command surfaces stacked on each other:
- a **menu bar** (File, View, Analysis, Edit, Help) holding all 93 actions;
- a **ribbon** under it (Home, Surfaces, Scene, Analysis, Tolerance) holding 51 of them.

42 actions were "menu + palette only" (`RIBBON_EXCLUDED`): imports, exports, clears, help.

## Change

The ribbon is the shell's only command surface.

- **No menu bar.** `populate_menu_bar` is gone, and with it the `menu` field of `ACTIONS`
  (93 entries, now `(name, text, shortcut, method, tooltip)`).
- **A File tab**, first as in any ribbon: Open, Reload, Save, Save As, Reset; Import and Export;
  Help, About, Quit. The shell still **opens on Home** (`START_TAB`).
- **Every action is on the ribbon**: 61 buttons, and 6 dropdown buttons holding the other 32.
  `RIBBON_EXCLUDED` is gone.
- **Dropdown buttons** (`DROPDOWNS`) hold the long lists that are used now and then. A button each
  would only widen the ribbon. Their entries are the shell's own action objects, so an entry, a
  button and a shortcut are one call.

| Dropdown | Tab | Holds |
|---|---|---|
| Import | File | Zemax file, Zemax wavefront map, CAD/STL solid, lens / camera / LED STEP |
| Export | File | 3D STEP, 3D view DXF, lens drawing, 7 analysis CSVs |
| Help | File | formula sheet, manual index, copy debug |
| Clear | Scene > CAD | CAD axis offsets, STEP imports |
| More | Analysis | PSF/MTF benchmark, copy reports, clear wavefront reference / marks |
| Export CSV | Tolerance | the 6 tolerance CSVs (each needs its report run first) |

- **New buttons** for commands that were menu-only: Reset, Copy / Paste rows, Refresh Plot, Folded
  Assembly, Drawing Properties, Path view > Add Component / Add Stock Lens, Place / Orient, Quit.
  15 icons drawn for them and for the dropdowns.

## The trap: shortcuts lived on the menu bar

Qt fires an action's shortcut only while some visible widget holds the action. The menu bar was that
widget. Without it, and with nothing else done, **every shortcut is dead**: Ctrl+O, Ctrl+S, Ctrl+Z,
F5 and the rest (measured: F5 ran Redraw 0 times). The window now holds the actions itself
(`self.addActions(...)`).

**All but two.** Copy / Paste rows are the table's own shortcuts (bugs/0942): Ctrl+C must copy rows
only while the table has focus. Held by the window as well, they fired from every view. The
menu-parity guard (phase 718, claim C) caught it on the first run: "Ctrl+C in the Results view
copied rows 1x". Those two stay off the window.

## Sizes

| | Before | After |
|---|---|---|
| Window minimum width | 1117 px | 1174 px |
| Widest tab | Analysis, 1071 px | Analysis, 1154 px (the More button) |
| Height taken above the table | menu bar + ribbon | ribbon |

## Guards

**`validate_qt_ribbon` (phase 714)**, new or changed claims:
- **M:** the window has no menu bar; tabs are File, Home, Surfaces, Scene, Analysis, Tolerance; it
  opens on Home.
- **C:** 61 buttons + 6 dropdowns listing 32 commands reach 93 of 93 actions, each exactly once;
  every button and dropdown has an icon that draws, no two the same.
- **L:** each dropdown lists exactly its declared action objects, in order, and opens on a click.
- **K:** F5 runs Redraw once; Ctrl+L flips Show Rays and back.
- **W:** the window's minimum width stays under 1240 px.
- **F:** folded, a pop-up page closes after a button's command and after a dropdown entry's
  (Analysis > More > Clear Marks).

**Mutation-checked:**
- without `addActions`, K fails (F5 ran Redraw 0 times, Ctrl+L did nothing);
- without the dropdown's close hook, F fails (the pop-up stays open).

**Other guards touched:**
- 0855 (phase 634) Q1 pinned the menus; it now pins "no menu bar, tabs as declared".
- 0860, 0861 and the menu-parity guard (718) unpacked the removed `menu` field. The parity guard
  read the method by position (`action[4]`), which would have become the tooltip and made its
  "editor: target exists" check pass on nothing. It unpacks by name now.

**Seen by eye:** each of the six tabs and the six dropdown lists rendered to PNG, and the 15 new
icons at 96, 26 and 16 px.

## Not changed

- The Tk shell keeps its menu bar.
- Right-click menus (table, 3D view, Scene Components) are context menus, not a menu bar.
- The command palette (Ctrl+Shift+P) still lists every command by name.
