# 0851 -- the Qt-migration seam, step 1a/1b: the UI host

docs/design_qt_migration.md. The user's decisions (2026-09-22): PySide6; one codebase, both
toolkits; **seam first on `tk`**, a Qt branch only once Qt is ready to migrate.

## What landed

`KrakenOS/UI/uihost/`:

| | |
|---|---|
| `UiHost` | the interface -- tkinter's own names: `after`, `after_cancel`, `after_idle`, `update_idletasks`; `showinfo/showwarning/showerror/askyesno/askokcancel/askyesnocancel/askretrycancel/askquestion`; `askopenfilename(s)/asksaveasfilename/askdirectory`; `askstring/askinteger/askfloat`; `clipboard_get/clipboard_set` |
| `TkUiHost(root)` | today's behaviour by delegation -- scheduling on the wrapped widget (a timer still dies with its window), dialogs to the tkinter modules resolved at call time |
| `ScriptedUiHost` | no toolkit: a deterministic clock (`run_due`, `run_all`) and dialogs answered from a script (value / list / callable; unscripted = cancel), every call recorded |
| `host_of(owner)` | the owner's `ui`, else its editor's, else `TkUiHost(owner)` -- so a guard's fake that stubbed `after` still gets its stub |

The editor takes `ui=` (default `TkUiHost(self)`); the inspector has its own `TkUiHost(self)`.

**175 call sites** in 17 model/controller files -- the services and mixins, the editor core and
the 3D inspector -- now reach the toolkit through `host_of(...)`: every `messagebox.* /
filedialog.* / simpledialog.*` call and every `self.after*` / `self.update_idletasks()`. Rewritten
by an AST-guided converter that only touches calls in a scope with a real `self` (closures
inherit it) and reports everything else. What remains is six view-building closures in
`inspection_cell.py` / `inspection_part.py` that construct their own Tk windows -- they move to
the view layer in step 1c, and the guard names them so nothing new slips in.

Found on the way: two methods carried a stray `@staticmethod` and had been broken for four months
-- fixed separately as bugs/0850.

## What it buys now, before any Qt

A guard can drive REAL editor code with no display and no module patching:

    editor = KrakenLayoutEditor(headless=True, ui=ScriptedUiHost(answers={"askyesno": True}))

and assert WHICH question was asked. The one validator that intercepted dialogs by replacing
`layout_table_workbench.messagebox` (0546) now scripts the host instead; two source pins that
grepped for `simpledialog.askfloat(` / `filedialog.asksaveasfilename` now look for the dialog call.

## Guard

`validate_open3d_0851_ui_host_seam.py`, display-free, penta phase 630.

- **T** Tk delegation: scheduling to the widget with arguments and handles untouched; dialogs to
  `tkinter.messagebox` at call time
- **S** scripted host: deadline order incl. a callback's own timer, cancellation, answers as
  value / list / callable, cancel by default, the call record
- **H** host resolution incl. the fake-with-a-stub fallback
- **L** no direct tkinter dialog / `self.after*` call left in the model/controller layer outside
  the six named view closures
- **E** a REAL headless editor built with a ScriptedUiHost asks File -> Open through it; the
  scripted cancel leaves the layout untouched and no toolkit dialog is raised

Verified with the FULL penta suite (see the commit).

## Next (design doc)

1c: model `tk.*Var` -> host-made variables (a real `tk.*Var` from TkUiHost, an `ObservableValue`
otherwise), and the widget-building code still inside services moved to views. 1d: editor and
inspector OWN a root instead of BEING one.
