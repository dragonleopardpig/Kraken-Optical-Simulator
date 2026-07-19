# 0360 — Elements browser: right-click a parent, Hide cascades to all children

**Ask (user, 2026-07-19):** "can make the elements right panel browser (parents with children),
right click the parents Hide and all its children or items will hide."

**Status:** SHIPPED 2026-07-19 (guard `validate_open3d_browser_group_hide`, penta phase 311).

## What ships

In the elements browser (`Open3DStepAdminPanel`):

- A node WITH children now gets a Hide/Show that cascades: `_set_element_hidden_cascade` hides the
  parent itself (when it has an element identity) plus every resolvable descendant
  (`_iter_descendant_iids`, depth-first through rows / step labels / display overlays / scene
  sources), each through the existing `_set_element_hidden` path so greying, per-kind handling and
  scene refresh behave exactly as single-item Hide always did.
- Pure GROUP nodes (a parent with no element identity of its own) previously got NO context menu
  at all — they now get Hide/Show entries that cascade over their children.
- Unresolvable descendants are skipped; the status line reports how many items were affected.

In-app eyeball owed.
