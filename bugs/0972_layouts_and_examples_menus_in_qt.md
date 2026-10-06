# 0972 -- the Qt interface had no Layouts, Machine Vision, Examples or Common Component menu

Phase 7d of the Qt migration (docs/design_qt_migration.md), second part, first service.

## What was wrong

Moving Tk code out of `services/layout_shell_controls.py` started with `_refresh_selector_menus`,
which fills four menus of the Tk menu bar from what is on disk:

| Tk menu | Holds | On this machine |
|---|---|---|
| **Layouts** | the common layouts, a submenu per category | 132 layouts in 8 categories |
| **Machine Vision** | the machine-vision lens layouts | 23 |
| **Examples** | the examples by category, then the Zemax prescriptions as a tree of folders | 407 |
| **Insert > Common Component** | the common layouts that can be inserted as a component | 6 |

**The Qt interface had none of the four.** Nothing under `qt/` named a layout list, an example or
a Zemax example; the only way to open any of them there was File > Open Layout and the file
chooser. Menu parity (phase 718) reported 76 of 76 all the same, because it counts the menu bar's
FIXED commands -- `add_command(label=..., command=self.method)` -- and these menus are filled at
run time.

## Change

- **The menus are model data.** `editor.selector_menu(kind)` returns a `MenuModel` for `"layouts"`,
  `"machine_vision"`, `"examples"` or `"insert_component"` -- the same recording menu the context
  menus have used since bugs/0907. Each entry's command is the model's own loader
  (`load_layout_by_name`, `load_example_by_name`, `load_zemax_example_file`,
  `insert_layout_component_by_name`).
- **Tk:** `_refresh_selector_menus` refills the menu bar's four menus from it
  (`context_menu.fill_tk_menu`). The three functions that built `tk.Menu`s inside the service are
  gone, and the service no longer imports tkinter.
- **Qt:** four ribbon buttons whose menu the model fills **each time it is opened**, so it is never
  stale: File > **Library** > Layouts, Machine Vision, Examples; Surfaces > Catalogs > **Common
  Component**. After an entry runs, the window follows the model (table, scene, title). They are a
  third kind of ribbon entry (`ribbon.MODEL_MENUS`), beside buttons and dropdowns of actions.
- The ribbon is no wider: the File tab is 701 px, the widest tab is still Analysis at 1154 px, the
  window's minimum is still 1234 px.

**The Tk menus are unchanged.** Their full outlines -- every label, every submenu, every disabled
line -- were recorded from the old code and compared with the new: all four identical.

## Also counted honestly

Phase 738 lists the services that import tkinter. A service can reach Tk without naming it, by
importing a Tk view module (`panels/`, `widgets/`) at module level; five do. That is a new claim
there (I), with its own exact list, so the count of seven that 0970 gave is not read as the whole
picture: after this, **six import tkinter directly and five import a Tk view package.**

## Guard: `validate_selector_menus` (phase 740)

- **P1-P4:** the model on a small made-up library -- categories in the declared order with empty
  ones left out; the Zemax tree (folders before files, "Top Level" first, alphabetical without
  regard to case); the separator only between two non-empty sides; one disabled line for an empty
  list; an unknown menu refused; each kind of entry calling the right loader with the right
  argument.
- **T:** a real Tk editor -- each of the four menus shows exactly the model's menu (132 / 23 / 407
  / 6 entries); a name added to the library appears after a refresh; a real entry loads its layout.
- **Q:** a real Qt shell -- the four buttons placed and built, each with an icon; opened, each
  shows exactly the model's menu, including a name added since the last opening; a real entry
  loads its layout with the table and the title following and no Tk window; a common component is
  inserted into the rows; the window's minimum width is 1234 px.

**Seen by eye:** the File tab with its Library group, and the Layouts menu open on a category.
