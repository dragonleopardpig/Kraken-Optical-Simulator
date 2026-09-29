# 0931 -- the Scene Components browser in the Qt shell (phase 5f, part 3b)

`panels/open3d_step_admin.py` (1 639 lines) is the Tk browser beside the 3D view. It groups the
STEP overlays, promoted rows, elements, display toggles and scene sources under categories. From
it you select, and you hide/show, delete, promote and edit through its right-click menus. It lives
in the inspector's withdrawn window, so under the Qt shell none of it could be reached.

## Measured before changing it

- **The tree was Tk-only.** `refresh()` inserted into a Treeview straight from the data helpers
  (`_scene_component_records`, `_promoted_step_rows`, ...).
- **A click was Tk-only.** `_on_tree_select` read `tree.selection()` and then dispatched the iid to
  the inspector's `select_*_from_admin`.
- **Four menus were direct `tk.Menu`s**, unlike the 16 viewport builders converted in bugs/0907.
  Under a shell they could not show.
- **Three helpers read the Tk tree** for children and text: the hide cascade, the element menu and
  the sources menu. Under the shell that tree still exists, hidden and rebuilt from the same data,
  so the reads worked by accident: the hidden-Tk trap of bugs/0929.

## The browser as data, in both shells

- `tree_nodes()`: one dict per node (iid, parent, text, default expansion, hidden tag), parents
  first. Tk's `refresh()` inserts exactly these, keeping each item's open state and the selection.
- `select_iid(iid)`: the selection dispatch. The Tk handler passes its selection in.
- `show_menu_for_iid(iid, event)`: select, then post that item's menu. The Tk right-click handler
  delegates to it.
- `node_children` / `node_text` read the data, and the hide cascade and both menus use them.
- The four menus go through `new_context_menu`, so under a shell they are `MenuModel`s shown as
  QMenus (bugs/0907).
- `refresh()` ends by notifying `inspector.scene_components_changed`.
  - It is at the end of `refresh()` itself, not in the inspector's `refresh_step_admin_panel`,
    because Hide calls the panel's own `refresh()`.
  - Measured: with the hook in the inspector, a Qt Hide tagged the node but the Qt item stayed
    black.

**Qt**: `qt/scene_components_dock.SceneComponentsTree` is a left dock drawing the nodes:
- hidden items are grey;
- expansion and the selection survive a rebuild;
- a click calls `select_iid`;
- a right-click calls `show_menu_for_iid` at the pointer.

Measured on om05a_folded:
- 39 nodes, the same iids and texts;
- clicking S0 selects it in the browser and in the editor's table;
- the right-click gives the browser's own menu (S0: Object / Hide / Delete);
- Hide greys the item.

## Guards

`validate_open3d_qt_5f_scene_components`, penta phase **710**:
- **T**: the Tk tree renders `tree_nodes()` exactly (iid, parent, text).
- **M**: no browser menu is a direct `tk.Menu`; all four go through `new_context_menu`.
- **Q**: the Qt claims above.

`validate_open3d_browser_group_hide` (bugs/0360/0361) is re-pointed. Its fake panel fed the cascade
a fake Tk tree, so it now supplies `node_children`. Its router fake gets the shared
`show_menu_for_iid`. Its claims are unchanged: the parent cascade, the category / sources / empty /
leaf routing.

## Left in 5f

- The browser's **properties pane**: the "Selected Element" details and action buttons (Import,
  Carry, Accept, Promote, Native, Delete, Faces, Center, Normal axis...). These actions are also
  reachable from the right-click menus and the toolbar's CAD / target menu.

## Gate: subset only -- FULL GATE OWED

- The user had 30 minutes, so this was committed on a 23-phase subset: every phase touching the
  browser / admin / hide (35, 65, 311, 342, 369, 370, 488, 514, 516, 585, 655, 656, 664, 676) plus
  the Qt phases (694, 695, 704-710).
- Phase 514 (`validate_open3d_0705_device_browser_row`) read the source of `refresh` /
  `_on_tree_select` / `_on_tree_right_click` for the Device-row wiring. It now reads `tree_nodes` /
  `select_iid` / `show_menu_for_iid`, the methods that hold that logic; its claims are unchanged,
  and it passes 6/6.
- An earlier 2-shard full gate was stopped by the memory watchdog (2.2 GB free, with Sioyek and
  Firefox open). **Run the full gate first next session.**
