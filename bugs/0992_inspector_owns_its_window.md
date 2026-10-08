# 0992 -- the 3D inspector owns its Tk window instead of being one

Phase 7e of the Qt migration (docs/design_qt_migration.md): step 1d for the inspector, as bugs/0853
was for the editor.

## What was there

`class Kraken3DInspector(Open3DDebugToolsMixin, tk.Toplevel)` -- the 3D view WAS a Tk window. So
it could only ever exist as one. In the Qt shell, where the same inspector object draws into a Qt
widget and takes Qt input (bugs/0906), it was still a `tk.Toplevel`, withdrawn and never shown.

## Change

- `tk.Toplevel` left the base classes. The constructor makes `self.window`, a `tk.Toplevel` child
  of the editor (a class of its own, `Kraken3DInspectorWindow`, only so that Tk names the window
  for what it is and no other dialog's Tk path is renumbered).
- `__getattr__` forwards to the window whatever the inspector does not define -- exactly the
  semantics a `tk.Toplevel` subclass had -- and `__str__` returns the window's path. So everything
  that treats the inspector as a widget keeps working unchanged: `ttk.Frame(self)`,
  `self.after(...)`, `tk.Toplevel(self)`, `transient(self)`, `parent=self`.
- `_last_child_ids`, tkinter's per-master counter for naming widgets, is a property onto the
  window's: tkinter ASSIGNS a fresh counter to a master that has none, which would have let a widget
  parented to the inspector and one parented to its window both be named `.!frame`.
- An inspector built with `__new__` -- sixteen guards build them -- has no window and gets a clean
  `AttributeError` for anything it lacks.

That is all: the inspector overrode no Tk method, called `super()` once, and nothing in the code
compares a widget Tk hands back (an event's widget, a toplevel, a focus owner) with the inspector.
The class is 26 000 lines; the change is 40.

Nothing a user sees changes in either interface.

## What this is for

Phase 7f: under a shell that is not Tk the inspector can be built with NO Tk window, where any
leftover Tk call fails loudly instead of quietly reaching a window nobody sees. That step is not
taken here -- the window is still made, and in the Qt shell it is still withdrawn.

## Proof that nothing changed

`bugs/0992_inspector_snapshot.py`, on a real Tk editor with the 3D view open, at the commit before
and after:

- the window: its class, title, size, minimum size, state, that the editor is its master, its
  close protocol;
- **every widget under it, 248 of them**: path, class, geometry manager, whether it is mapped, and
  its bound event sequences; for a menu, its entry count;
- that a child's master is the inspector, and its toplevel the window; that `after` through the
  inspector runs;
- closing: the editor forgets the inspector, the window is gone, the root's children after;
- a screenshot of the screen.

Identical, but for one thing by design -- the window's Tk path is `.!kraken3dinspectorwindow` where
it was `.!kraken3dinspector` (nothing looks a widget up by that name) -- and the screenshots are
identical pixel for pixel (`0992_inspector_before.png`, `0992_inspector_after.png`). Two runs at
the commit before agree with each other, so the comparison means something.

## Guard: `validate_inspector_owns_its_window` (phase 758)

- **A:** the inspector is not a Tk widget; its window is a Toplevel, child of the editor;
  `str(inspector)` is the window's path.
- **F:** `after` + `update` through the inspector run a callback; title, state, existence answer.
- **N:** widgets parented to the inspector and to its window share one naming counter.
- **P:** Tk takes the inspector where it takes a window -- a dialog's master, `transient`, a
  variable's master, a menu's, an argument of a Tk command.
- **E:** a raising callback of a widget inside the inspector reaches the editor's handler.
- **W:** an inspector built with `__new__` raises a clean `AttributeError`, also through a property.
- **D:** closing destroys the window and the editor forgets the inspector.
- **Q:** in the Qt shell the hosted inspector is the same kind of object, its window withdrawn.

## Checks

**The inspector's own regression set, at a0b73bb2:** the 352-phase harness passes with the inspector
as a Tk window (352 pass, 0 fail, 43 min) and hosted in the Qt shell (352 pass, 0 fail, 44 min) --
one process each, one after the other.

**Mutations: 7 of 7 caught.** The forwarding asking for the window without checking there is one
(a recursion on an inspector built with `__new__`); the inspector not answering with its window's
path; a widget-naming counter of its own; the window a child of the Tk root instead of the editor;
the Qt-hosted inspector's window left on screen; closing leaving the window up; the inspector a
`tk.Toplevel` again.

**Passing after the change:** 23 neighbour guards -- the fifteen others that build an inspector
with `__new__`, the editor's own-its-root guard (632), the Qt hosting and viewport seam guards
(0905, 0906), the interaction contract (655), the panel delegations, the bug-flag windows, and
phase 738.

**Baseline:** phase 758 recorded (pass; 757 phases). The full Tk gate was last run at 1f3e0d19,
before this change; the 405 phases outside the harness are owed.
