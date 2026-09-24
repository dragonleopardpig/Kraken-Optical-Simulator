# 0883 -- the Inspection Cell, and a bug only two Tk interpreters could show

Six faces of one part, each slotted with its own station layout, plus the part dimensions, the
cell-level solve, and the verbs that compose them: cell view, interference report, cell STEP,
save and load. `services/inspection_cell.py` 737 -> 515 lines; the dialog itself is now one call.

## Why this is a record list and not twelve loose fields

The Tk dialog drew six rows of *checkbox + entry + Browse button*. As a record-list form the six
**faces are the records**, so one `Browse Layout...` verb acts on the face you picked -- six
buttons become one -- and every file chooser asks through the **UI host**, so the same verb works
in Qt. The table also shows each face's enabled flag and slotted layout at a glance, which the
six separate rows did too.

The embedded cell **view** (`panels/inspection_cell_window.py`) is a VTK plotter and stays in
phase 5. This form only asks it to open.

## The bug the harness found, and one interpreter could not

The guard passed standalone and failed inside the penta harness with
`the REAL Tk dialog drew its 0-face tree under None`. Measured:

```
getattr(ed, "editor") is ed: False | type: NoneType
Toplevel landed in: the FIRST interpreter's root, not the editor's
```

`render_row_form` resolved its owner with `getattr(owner, "editor", owner)`. For the panel
shells that is the editor. But the Inspection Cell passes the **editor itself**, and the editor
forwards unknown attributes to its Tk root -- so `editor.editor` comes back as **None** rather
than raising, and the getattr default never fires. `tk.Toplevel(None)` then picks
`_get_default_root()`.

With one interpreter that is invisible: the default root *is* the editor's root. Inside the
harness, which already owns a root, the dialog was built in the **wrong interpreter** and the
editor never saw it. The fix is `getattr(owner, "editor", None) or owner` -- and the reason is
written next to it, because the next reader will otherwise "simplify" it back.

This is the second time two interpreters have exposed something invisible in one (bugs/0865: a
`tk.StringVar` with no `master=`). **A guard that builds its own editor must be run in the
harness, not just standalone.**

## Guard

`KrakenOS/UI/validate_open3d_0883_inspection_cell_form.py` (penta phase 671):

- **B** -- the six faces under the builder's columns, with its 8 verbs and the part/solve fields
- **S** -- the list opens on Front, picking row 3 loads Right, and the edit folds back into it
- **A** -- apply writes `editor.inspection_cell_spec`; only the slotted face is enabled
- **H** -- `Browse Layout...` asks the **host** for the *selected* face and slots it; a cancel
  leaves the spec alone
- **T** -- the REAL Tk dialog draws its six-face tree
- **Q** -- the Qt dialog lists 6 faces, opens on Front and loads Top when row 4 is picked
