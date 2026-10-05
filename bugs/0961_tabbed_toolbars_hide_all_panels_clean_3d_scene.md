# 0961 -- tabbed 3D toolbar, Hide All Panels, Clean 3D Scene; phase 722 made machine-independent

User, 2026-10-05: "please proceed recommended next. Please make all toolbars tabbed and can be
hide/unhide. Give user chance to have big clean 3D scene. Also, the side tabs, can have 'one click
hide all' option?"

## 1. The 3D toolbar is one tabbed strip

The 3D scene had three toolbars stacked above it -- View, Scene, Carry -- 96 px high, each a
scrolling row that hid its end behind a scroll bar when the scene was narrow.

- **One strip**: the tab names (View | Scene | Carry) at its left, the chosen row beside them --
  **34 px**.
- **Each row is a real toolbar**: what does not fit goes behind its **»** button instead of a
  scroll bar. Each field keeps its label with it (Axis, Normal, Rot, Snap mm).
- **A row's hint text comes after its controls.** Carry's 70-character hint came first and pushed
  every control behind » in a 700-px scene. The hint is also the tab's tooltip.
- **The strip's ▴ arrow hides it.** Home > Workspace > **3D Toolbar** brings it back (also in the
  command palette).

The Tk app's rows are unchanged; both still come from the one catalogue (`open3d_toolbar.py`).

The ribbon was already tabbed and folds to its tab row. The surface table's own row hides with its
panel.

## 2. Hide All Panels

**Hide All Panels** -- the first button on every edge's tab strip, Home > Workspace, or
**Ctrl+Shift+H**:
- one click puts every open panel away;
- the next brings back the SAME ones: the same tab in front of each stack, each panel at its size;
- it reads "on" whenever no panel is open, however they were closed, and then shows them all.

Two size bugs were found and fixed while building it:
- **A stack came back about 120 px wide.** A panel behind a tab keeps a stale size (100 px measured),
  and restoring it shrank the whole stack. Only the panel in front now gives its stack's size.
- **Panels side by side came back the wrong width.** Debug came back 628 px wide where it had been
  470: only heights were restored on the bottom edge. Sizes are now restored both ways, all
  panels in one pass.

## 3. Clean 3D Scene

**Clean 3D Scene** -- **F11**, the button beside the ribbon's fold arrow (on every tab), or
Home > Workspace -- folds the ribbon, hides the 3D toolbar and puts every panel away.

- **On your screen size** (a 1916x1034 window, om05a_folded): the 3D view grows from 1124x559 to
  **1836x931**.
- **The edge tab strips stay**, so any panel is one click away.
- **Again, it puts back exactly what it put away:**
  - the ribbon's fold state, and the 3D toolbar;
  - the panels, each at its size;
  - a panel closed BEFORE stays closed, and one opened DURING stays open -- also after Hide All
    was used in between.
- **The ribbon is put back FIRST.** Unfolding it after the panels raced their resizes and left the
  scene 46 px off.

F11 is free on this desktop: Hyprland's fullscreen is Super+Shift+F.

## 4. Phase 722 no longer depends on the machine or on untracked files (recommended next, from 0960)

`validate_qt_table_context_menu` failed on X299-SSD, for two separate reasons:

- **A fixed 900 s limit on the every-entry run.** The i7-7820X needs about 1100 s (938 s at HEAD).
  The limit is a hang guard, not a speed test: it is now 2400 s (`EVERY_ENTRY_TIMEOUT_S`).
- **Counts that included files not in git.** The "Machine Vision Lens" submenu lists every layout
  file in `common_optical_layouts/`, and your checkouts carry untracked ones. So the "100+
  commands" (B, Q) and "100 run" (E) bounds passed with them and failed on a clean checkout (97
  commands, 98 run). The bounds now count only the menu's own entries (`listed_from_files`):
  - B and Q: 88-98 own commands per cell, floor 80;
  - E: 89 own entries run, floor 85.

  The numbers are identical in a clean worktree and in one with the untracked layouts copied in.
  Both pass.

## 5. The parallel gate gives each group whole physical cores

`tools/penta_parallel_gate.py` dealt out CPU numbers in runs. On X299-SSD CPU N and N+8 are one
physical core, so "2 cores" per group was about one: the 0960 run took 90 min and its
timing-bounded phases failed under load.

- **By default** it now reads the CPU topology
  (`/sys/devices/system/cpu/cpu*/topology/thread_siblings_list`) and gives each group whole
  physical cores, both threads, spreading the remainder over the first groups. The last physical
  core (at least two CPUs) is left for the desktop.
  - X299-SSD at `--jobs 3`: `0,8,1,9,2,10 | 3,11,4,12 | 5,13,6,14`, core 7 free.
  - A machine without hyperthreads is split as before (14 CPUs, `--jobs 4`: four groups of three).
- **`--cores` takes lists** as well as a range: `"0,8,1,9"` or `"0-5,8-13"`.

**Measured, and not settled:** at `--jobs 3` the full gate took **132 min** with no failure. At
`--jobs 6` (two sibling-sharing threads per group) it took 90 min, but two timing-bounded phases
failed. A group is mostly ONE busy thread, so three groups leave physical cores idle. Another
session's test run was also competing for the machine. `--jobs 7` (one whole physical core per
group, core 7 left free) should be both fast and quiet; it has not been run yet.

## 6. The ribbon guard's width limit

The Hide All button was first 32 px wide on strips whose tabs are 21. Each side strip grew 11 px,
and the window's minimum width with it: 1232 -> 1254 px, over the ribbon guard's 1240 (phase
714 W). It is now 22 px with a 16-px icon: 1234 px.

## Guard: `validate_qt_clean_scene` (phase 731)

In a real Qt shell on `beam_splitter_two_arm_doublets` (in git), by real clicks and keys:

- **T:** one strip of tabs at most 40 px; a tab click shows that row only; every control on its
  own row's tab; a long row puts its end behind » without widening the window; the hint comes after
  the controls.
- **H:** the arrow hides the strip (the scene gains its height); the 3D Toolbar switch brings it
  back.
- **A:** Hide All from the left strip, then from the right: the same 10 panels back, the same fronts,
  every size within 3 px; closed one by one, the switch reads on; Ctrl+Shift+H shows all.
- **C:** F11 -- ribbon folded, toolbar hidden, no panel open, the corner button on, the scene 84% of
  the window. Then Progress is opened and Ctrl+Shift+H pressed twice, and the corner button puts back
  ribbon, toolbar and panels; Debug (closed before) stays closed, Progress (opened during) stays
  open, each panel at its depth into the scene.

**Mutation-checked:**
- the stale behind-tab size used: A fails;
- sizes restored one way only: A fails;
- the switch not kept in step: A and C fail;
- the toolbar left shown: C fails;
- "show every closed panel" on the way back: C fails (Debug reopens);
- the hint first: T fails.

**Seen by eye:** 1500x950 and 1916x1034, every state.

**Other guards run:**
- the ribbon (714): its W failed at first, see section 6; it passes now;
- the scene layout (724) and the Qt-hosted inspector (0906);
- the 5f toolbar guard;
- the inspector popups (723) and menu parity (718);
- soft STEP bodies (728), the shell flag (729) and the 0960 snapshot guard (730).

## Gates (X299-SSD)

- **Full Tk gate: 730 of 730 pass** (`tools/penta_parallel_gate.py --jobs 3`, whole physical
  cores, 132.2 min). That includes 722 with its new bounds, and the new 731. Lowest free memory
  5.6 GB.
- Phase 731 recorded in the baseline: 730 phases, none failing.
