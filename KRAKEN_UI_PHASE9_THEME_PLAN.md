Kraken UI Phase 9 Theme Plan
============================

Status: Draft / deferred.

Phase 8 keeps the production UI on the existing Tk/ttk styling. A partial
modern ttk layer was prototyped in `KrakenOS/UI/modern_ttk_theme.py`, but it is
not applied to the main editor because mixing old Tk defaults with new styled
widgets makes the interface visually inconsistent.

Goals
-----

1. Define one complete visual system before touching production widgets:
   spacing, typography, colors, table states, disabled states, menus, dialogs,
   plot panels, and 3D toolbars.
2. Decide whether to stay on themed `ttk` or migrate selected panels to
   CustomTkinter. Do not mix both styles in the same visible workflow without a
   compatibility design.
3. Theme complete interaction groups at once: left panels, editable table,
   top menu/toolbar, right analysis panels, dialogs, and 3D handlers.
4. Add screenshot regression coverage before enabling the theme by default.
5. Keep an escape hatch such as `KRAKEN_UI_TTK_THEME=classic` for debugging.

Acceptance Checks
-----------------

* A screenshot set compares at least: Reset state, editable table, Source
  panel, Optimization panel, Analysis panel, 2D plot, embedded 3D view, and two
  representative dialogs.
* The full UI does not show mixed old/new button, combobox, treeview, or dialog
  styles in the same workflow.
* `python -m KrakenOS.UI.validate_demo_readiness --full` remains green after
  the theme is enabled.
