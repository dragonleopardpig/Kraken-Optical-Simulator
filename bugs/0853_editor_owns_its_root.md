# 0853 -- the editor owns its Tk root instead of being one (Qt seam, step 1d, editor)

docs/design_qt_migration.md. `KrakenLayoutEditor(18 mixins, tk.Tk)` WAS the Tk root, so the model
could only ever live inside a Tk application.

## What changed

- `tk.Tk` left the base classes. The constructor creates `self.root = tk.Tk()`.
- `__getattr__` forwards to the root whatever the editor does not define -- exactly the semantics a
  `tk.Tk` subclass had (tkinter's own `__getattr__` then reaches the Tcl interpreter), so
  `getattr(editor, name, default)` answers identically for every name. `__str__` returns the root
  path `"."`.
- `_last_child_ids` (tkinter's per-master widget-naming counter) is a property onto the ROOT's:
  tkinter ASSIGNS a fresh counter to a master that has none, which would have let a widget
  parented to the editor and one parented to the root both be named `.!frame`.
- Exceptions: tkinter reports a callback's exception to the root of the widget tree, found by
  walking `.master` up -- which now ends at the editor, so the editor's `report_callback_exception`
  still catches it; the real root's handler is set to the editor's as well.
- `destroy()` ends by destroying the root (was `super().destroy()`).

Why forwarding and not rewriting ~52 `self.<tk method>` calls, every panel's `ttk.Frame(self)` and
171 validators that call `editor.update()` / `editor.after(...)`: a spike showed tkinter accepts a
root-owning forwarder as a widget master -- frames, Toplevels, variables, menus, nested children --
so all of that keeps working unchanged, and a Qt shell can hold the same model with no root, where
any leftover Tk call fails loudly instead of silently.

Bonus: an editor built with `__new__` (the off-thread trace worker, `render_layout_snapshot`) now
gets a clean `AttributeError` for a missing attribute -- the bugs/0223 recursion class (tkinter's
`__getattr__` recursing through an unset `self.tk`) is gone by construction.

The inspector (`tk.Toplevel`) is not converted: it IS the 3D view, and becomes a Qt widget in
phase 5.

## Guard

`validate_open3d_0853_editor_owns_its_root.py`, penta phase 632: not a Tk / owns one / `str` is
`"."`; `after` + `update` + `winfo` through the editor; one naming counter; a raising widget
callback reaches the editor's handler and the root's handler is the editor's; a `__new__` editor
raises cleanly and honours getattr defaults; destroy runs the cleanup and destroys the root.
