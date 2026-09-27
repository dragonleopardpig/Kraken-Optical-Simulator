# 0907 -- the 3D view's right-click menus, in the Qt shell (phase 5c)

Every CAD / Place / Orient command in the 3D view is a right-click verb (bugs/0619). After 0906 the
Qt shell hosted the real inspector, but it held the right-button press back, because the press
posts a Tk menu and nothing pumps Tk under Qt. So none of those commands could be reached from Qt.

## Measured

The inspector and its face-assignment service build 16 menus, submenus included:
- 8 in `open3d_face_assignment`: the face, body, opening, scene-source, optical-axis,
  inspection-part and empty-space menus, plus the Row Actions submenu;
- 8 in `open3d_inspector`: the measurement, thickness-dimension, detector-camera and Quick
  Estimation role menus, with their submenus.

Across them, the builders make only these calls on a menu: `add_command` (180), `add_separator`
(47), `add_checkbutton` (6), `add_cascade` (5), plus `invoke`, `unpost` and a post. Every entry's
action is a plain Python callable.

## So the builders are not rewritten

- **`context_menu.new_context_menu(owner, master)`** replaces the 16 `tk.Menu(...,
  tearoff=False)` calls:
  - When no shell hook is installed, it still returns `tk.Menu(master, tearoff=False)`, looked up
    by name at call time. That keeps the existing menu guards' `tk.Menu` fakes working.
  - When a shell has installed `show_context_menu` on the inspector, it returns a `MenuModel`
    instead.
- **`MenuModel`** takes the same calls and records the entries. `run(entry)` does what a Tk click
  does: a check entry toggles its variable and a radio entry sets its own BEFORE the command runs;
  a disabled entry does nothing. A call it does not model raises, rather than passing silently.
- **Posting.** `_popup_context_menu` gives a model to the shell and skips all the Tk grab /
  `<Unmap>` / focus machinery. The inspector's four direct `tk_popup` sites now share
  `_post_viewport_menu`, which is the same Tk popup under Tk and routes a model through the shared
  popup, so a scene click dismisses it like every other menu (bugs/0341).
- **Qt.** `InspectorView.show_context_menu` renders the model as a QMenu (`build_qmenu`: cascades,
  separators, disabled entries, check state, `&` escaped), each action calling `MenuModel.run`.
  When the menu hides, it stops being the live menu. The right press is now routed
  (`DEFERRED_PRESSES` is empty).

## Measured while guarding

A right-click can change what the NEXT menu reads. At one pixel, a menu built straight after the
previous pixel's click differed from one built after its own click, although repeated builds at
that pixel were identical four times in a row. So the Tk-vs-model comparison clicks each pixel once
to settle the state and then compares.

## Not done here

Several verbs open a Tk dialog (Element settings, Open Face Editor, Replace STEP, Export DXF, ...).
Under Qt the verb runs but its Tk dialog cannot show. Those dialogs move with 5f/5g.

## Guard

`validate_open3d_0907_context_menus_in_qt` (penta phase 695):
- **S (static).** No viewport menu is a direct `tk.Menu`; only the two posters post; every call
  the builders make on a menu is one `MenuModel` takes.
- **M (static).** Click semantics, and the factory returns a `tk.Menu` without a shell and a model
  with one.
- **T (Tk shell, om05a_folded).** At every grid pixel, the REAL posted `tk.Menu` and the model the
  same builder filled have the identical outline. This held for seven kinds of menu, face menus
  among them.
- **Q (real Qt shell).** Every right-click QMenu has exactly its model's outline, over at least
  four kinds of menu.
- **A (real Qt shell).** Triggering "Select Elements" arms the box select.
- **D (real Qt shell).** A scene left-click dismisses a shown menu.

The 0906 guard's R and D checks asserted that the right press was held back. They are re-pointed:
R to `DEFERRED_PRESSES`, and D to "the press is routed and the live menu is never a Tk menu".
