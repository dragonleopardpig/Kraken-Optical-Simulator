# Qt migration -- design and plan

Status (2026-09-23): **the seam is in place on `tk`; phase 2 has begun on `qt`.**

| step | landed |
|---|---|
| 1a/1b the UI host; 175 dialog + scheduling call sites through `host_of` | bugs/0851 |
| 1c the model declares its 64 state variables; hosts make variables; `ObservableValue` | bugs/0852 |
| 1d the editor OWNS its Tk root instead of BEING one (forwarding) | bugs/0853 |
| found on the way: two `@staticmethod` slips (Optimize, Paraxial Matrix Report) | bugs/0850 |
| 2 (part 1) PySide6 in devenv, `QtUiHost`, and a spike proving the VTK viewport under Qt | bugs/0854 |
| 2 (part 2) the Qt shell: `KrakenOS/UI/qt/` -- menus, docks, surface table, viewport, status line | bugs/0855 |
| 2 (fix) the shell must run on XWayland: Qt on Wayland gives VTK a surface id and Xlib aborts | bugs/0856 |
| 2 (fix) the 3D view draws the model's optical elements, not only the imported STEP bodies | bugs/0857 |
| 2 the 3D view draws the traced light, through the model's own ray-display pipeline | bugs/0858 |

Deferred on purpose: moving seven self-contained dialog functions out of services (reached only
from menu actions; a Qt build calls Qt dialogs instead, so their location does not block Qt), and
the inspector's own 1d (it IS the 3D view; it becomes a Qt widget in phase 5).

**Now on branch `qt`, phase 2.** The shell exists and runs:
`python -m KrakenOS.UI.qt.app attachment/om05a_folded.py`.

## The shell (bugs/0855)

`KrakenQtMainWindow` owns no optics. It holds a `KrakenLayoutEditor` built with
`ui=QtUiHost(...)`, so **`File -> Open Layout` calls the model's own `editor.open_layout()`** --
the method the Tk File menu calls -- and the chooser that appears is Qt's, because that is what
the host behind `host_of(self)` puts up. No Qt-specific load path was written. The surface table
is a `QAbstractTableModel` over `editor.rows` with no copy in between, and the status bar binds
once to `status_var` through the `trace_add` a `tk.StringVar` and an `ObservableValue` both have
-- which is what step 1c was for.

`qt/actions.py` and `qt/docks.py` follow the structure of `optiland_gui/action_manager.py` and
`panel_manager.py` (MIT, (c) 2024 Kramer Harrison), attributed in each module. optiland's own
panels are not lifted: they are optiland's model's views.

Still transitional: that editor builds a Tk widget tree behind the scenes (0853 freed it from
BEING a root, not from having one), so the shell passes `headless=True` and withdraws the root.
Phase 5 removes it.

The viewport draws the model's own display geometry -- `_scene_surface_meshes` over the system
from `_build_preview_system_rays_bundle`, which is exactly what the Tk 3D view draws, with each
record's colour and opacity -- and the traced rays through that view's ray pipeline, bounding
included, so a ray that misses the detector visibly misses. One system build feeds both passes.
`View -> Show Rays` switches the light. On `om05a_folded.py`: 20 elements, 106 rays, 3 bodies.

## Phase 3, the dialogs -- the recipe (bugs/0859)

Measured 2026-09-23: **62 functions build a `tk.Toplevel`, about 9 000 lines** (validators and
archive excluded); the largest are the CAD/STL face-roles editor (1 902), the Scene Source Manager
(680) and the Paraxial Calculator (459).

Porting one-for-one would double the dialog code and guarantee drift. Instead, for every dialog
that is *a summary, a table and an export* -- a large share of the 62 -- the DATA moves out into a
toolkit-free builder under `KrakenOS/UI/reports/` returning a `Report`, each toolkit keeps only
its layout, and both render the same object. A number then cannot differ between the two views,
and the contents become checkable **without a display**, which no Tk dialog's ever were.

| piece | what |
|---|---|
| `reports/base.py` | `ReportColumn` (heading, numeric -> format + alignment), `Report` (`cell()`, `write_csv()`), `ReportFailed` |
| `reports/<name>.py` | one builder per dialog |
| `qt/dialogs/report_dialog.py` | the Qt layout for the whole family |

First port: the **Paraxial Matrix Report** (Analysis menu, Ctrl+M). Both views ask for the export
path through the UI host, so each gets its own file chooser from one call shape.

### The seven families

One dialog shape per family; a new dialog of a known shape is a builder plus a menu entry.

| family | model | Qt view |
|---|---|---|
| report | `reports/<name>.py` -> `Report` | `qt/dialogs/report_dialog.py` |
| report + controls | `Report` + `ReportChoice` | the same dialog, with a control strip |
| report + inputs | `Report` + `ReportValue` | the same dialog, with entry fields |
| form that writes back | `row_forms/<name>.py` -> `RowForm` | `qt/dialogs/row_form_dialog.py` |
| master / detail | `Report` + `DetailView` | the same dialog, split |
| tree | `TreeRow` | `qt/dialogs/report_dialog.py` (tree mode) |
| record list | `RowForm` + `RecordList` | `qt/dialogs/row_form_dialog.py` (list + form) |

### Ported so far

| bug | dialog | family |
|---|---|---|
| 0859 | Paraxial Matrix Report | report |
| 0860 | Surface/Element/Ray census reports (5) | report |
| 0861 | Non-sequential Path Report | report + controls |
| 0862 | Tk <-> Qt parity proven by SHA-256 over every displayed cell | -- |
| 0863 | Optical Invariants | report |
| 0864 | System Selection Calculator | report + inputs |
| 0865 | Paraxial Calculator (`UI/paraxial_calculator.py`) | report + inputs |
| 0867 | Ray Inspector (226 rows) | master / detail |
| 0868 | Trace Path Inspector (452 nodes) | tree |
| 0869 | Beam Splitter row form | row form |
| 0870 | Diffuse / Scatter row form | row form |
| 0871 | Error Map row form | row form |
| 0872 | Coating / Material row form | row form |
| 0873 | Advanced Surface row form (53 fields, 6 tabs) | row form |
| 0874 | Detector Settings row form | row form |
| 0875 | Scene Target row form (+ live `locked` / `is_enabled`) | row form |
| 0876 | Path-Local Pose + Element Settings (element BLOCKS, editable choices) | row form |
| 0881 | Scene Source Manager (`RecordList`: a form that edits a COLLECTION) | record list |
| 0882 | Glass Catalog Browser + Stock Lens Importer (live text filters) | record list |
| 0883 | Inspection Cell (six faces as records; host file choosers) | record list |
| 0884 | the five half-done ports finished on the shared Tk renderer (textarea + tabs) | -- |
| 0885 | Scene-source edit popup (the model decides the fields; `modal=True`) | row form |
| 0886 | Inspection Part + `FormPreview` (the model draws the picture) | row form |

The row-form framework: `FormField` kinds (number, int, bool, choice, text, textarea, static),
`choices` that grow at runtime, `editable` choices the user may type into, `on_change` fields that
rewrite other fields, `group` tabs, `enabled` (static) and `RowForm.locked` / `is_enabled` (live)
locks, `FormAction`s, and a `row_index` that may stand for a whole element BLOCK. 0874 was the
first dialog it absorbed with nothing new.

The Tk view of every row form is `panels/row_form_view.py`, the counterpart of
`qt/dialogs/row_form_dialog.py`, and since 0884 the two are feature-equal -- every `FormField`
kind and every `RowForm` property draws in both. The five dialogs that use it shrank hard:
`main_scene_element_dialogs.py` 616 -> 103 lines, `main_scene_source_manager_dialog.py`
770 -> 108. Both are now the factory's kwargs and one call.

`validate_3d_interaction_contract.py` is **stale** and not a penta phase: ~25 of its source-text
assertions name strings that moved into `reports/` and `row_forms/` during 0869-0873. Re-pointing
it is its own task.

**Next: the rest of phase 3**, dialog by dialog, each one a builder plus a menu entry. The
CAD/STL face-roles editor is deliberately **not** phase 3 -- it embeds a VTK preview with
click-picking, camera drag and gizmos, so it belongs to phase 5 with the rest of the interaction
layer.

## Phase 2 findings (2026-09-23, bugs/0854 + `bugs/spike_0854_qt_viewport.py`)

Proved end to end, headless: a PySide6 window whose `QVTKRenderWindowInteractor` draws the REAL
`om05a_folded.py` bodies (optical 32 311 points, lens 27 656, camera 112 916) from a headless
editor, a first frame in ~0.7 s, and a Qt mouse drag that rotates VTK's camera (407 mm of camera
travel; the second capture is a 3/4 view). A Tk root and a QApplication coexisted in that process,
which is what "one codebase, both toolkits" needs during the transition.

Four traps, each of which cost a debugging round and each of which will bite again in phase 5:

1. **`vtkmodules.vtkRenderingOpenGL2` must be imported before the render window is created.**
   Otherwise VTK's object factory has no OpenGL override and `vtkRenderWindow()` returns the
   ABSTRACT base: `Render()` silently draws nothing, pixel readback returns 0 pixels, and
   `vtkWindowToImageFilter` SEGFAULTS. `GetClassName()` must say `vtkXOpenGLRenderWindow`.
2. **Qt's platform and VTK's display must be the same window system** -- a constraint on the
   APPLICATION, not just on test runs, which is what bugs/0856 was: the shell shipped without it
   and the user's launch died with `BadWindow (X_ConfigureWindow)` and no traceback, because
   Xlib's default error handler exits the process. `app.choose_qt_platform()` now puts Qt on
   `xcb` before the QApplication exists whenever a Wayland session has an X server, and
   `SceneViewport` refuses a wrong platform with an explained error. Headless runs still need
   `unset WAYLAND_DISPLAY; QT_QPA_PLATFORM=xcb` (or `offscreen` where no GL window is needed).
3. **Build the viewport only once its parent chain reaches a shown top-level.** The widget hands
   VTK its window id in `__init__` (`SetWindowInfo(winId())`), and Qt destroys and recreates a
   native window on reparenting -- a viewport built into a not-yet-parented container leaves VTK
   drawing into a dead handle: blank, and no mouse events.
4. **An imported STEP body's ACTIVE cell scalars are `kraken_step_selection_face_index`** (what
   face picking reads), so a mapper colours by that array through the default lookup table and
   ignores the actor colour -- the bodies rendered invisible on white, only their few line cells
   showing as specks. Every Qt-side mapper needs `ScalarVisibilityOff()` unless it means to colour
   by data.

And one that shapes phase 5: **`vtkInteractorStyleSwitch` starts in JOYSTICK mode**, where the
camera moves on timer ticks rather than move deltas, so a press-drag-release does nothing at all.
The style has to be set explicitly.

## Decisions (user, 2026-09-22)

| Question | Decision |
|---|---|
| Where | **Seam first, on `tk`** (renamed from `nonseq-display-refactor`). A Qt branch is created only once Qt is ready to migrate. |
| Binding | **PySide6** -- matches `~/Projects/optiland/optiland_gui`, whose MIT shell (main window, docks, action registry, viewer panel, command palette) is liftable into GPL-3 KrakenOS with attribution. |
| Coexistence | **One codebase, both toolkits.** Tk stays the working app until Qt reaches parity; each feature switches over and is re-proved on its own; bug fixes land once. |

## Why seam-first

The two god-classes *are* Tk objects -- `KrakenLayoutEditor(18 mixins..., tk.Tk)` and
`Kraken3DInspector(tk.Toplevel)` -- so every mixin reaches the toolkit through `self`. Porting
widgets first would mean porting that tangle twice. Cutting a toolkit-neutral seam while Tk keeps
running turns "migrate to Qt" from a rewrite into adding a second implementation behind an
interface, with the penta gate proving each step.

## The surface, measured (AST census, 2026-09-22; validators and archive excluded)

241 UI modules, 65 import tkinter.

| layer | dialogs | scheduling | tk vars | widgets |
|---|---|---|---|---|
| services / mixins (model + controller) | 106 | 54 | 37 | 100 |
| 3D inspector | 6 | 13 | 45 | 96 |
| editor core | 3 | 3 | 10 | 0 |
| views (panels, widgets) | 174 | 9 | 326 | 1059 |

`self.<Tk method>` calls across all layers: 150 (+33 `winfo_*`). The expensive part is not the
widget count -- it is the interaction layer (mouse bindings, face/edge/lens pick, gizmos, the
hover modifier contract), which carries ~50 shipped interaction bugs that must be re-proved on
Qt's event model.

## The seam

Model/controller code (services, mixins, the editor and inspector cores) talks to the toolkit
only through a `UiHost` (`KrakenOS/UI/uihost/`), reached as **`host_of(self)`** -- the owner's
`ui` attribute, else its editor's, else the owner wrapped in `TkUiHost` (so guards that bind real
methods onto small fakes keep working unchanged). Views (panels) stay toolkit-specific: each gets
a Qt counterpart rather than an abstraction.

`UiHost` mirrors tkinter's own names, so converting a call site is mechanical and reviewable
(`messagebox.askyesno(` -> `host_of(self).askyesno(`):

| group | methods |
|---|---|
| event loop | `after`, `after_cancel`, `after_idle`, `update_idletasks` |
| messages | `showinfo`, `showwarning`, `showerror`, `askyesno`, `askokcancel`, `askyesnocancel`, `askretrycancel`, `askquestion` |
| files | `askopenfilename`, `askopenfilenames`, `asksaveasfilename`, `askdirectory` |
| input | `askstring`, `askinteger`, `askfloat` |
| clipboard | `clipboard_get`, `clipboard_set` |

Implementations:

- **`TkUiHost(root)`** -- today's behaviour exactly; resolves `tkinter.messagebox` etc. at call
  time.
- **`ScriptedUiHost`** -- no toolkit: a deterministic scheduler (`run_due`, `run_all`) and
  dialogs answered from a script, every call logged. For display-free guards: a guard asserts
  *which* question was asked and drives the answer, instead of patching module attributes.
- **`QtUiHost`** (Phase 2) -- `QTimer`, `QMessageBox`, `QFileDialog`, `QInputDialog`,
  `QClipboard`.

Model state held in `tk.*Var` (status line, ray count, overlay toggles...) moves to host-made
variables in step 1c: `TkUiHost` returns real `tk.*Var` (views can still bind
`textvariable=`), the others return a toolkit-free `ObservableValue` with the same
`get` / `set` / `trace_add` surface -- so the services that read and write them do not change.

Model -> view notification follows `optiland_connector.py` (a QObject with signals such as
`opticChanged`, `surfaceDataChanged`) once the Qt side exists; the Tk side keeps its direct calls
until then.

## Step 1c, measured: the model's state lives in view-made variables

`self.<name> = tk.*Var(...)` is defined 135 times -- **92 of them in panels** (views), 33 in the
inspector, 10 in the editor -- and **100 of the 135 are read or written by model code**. The
direction is inverted: `field_value_var` is created by a panel and read 21 times by services;
`status_var` is written over 1000 times from model code. A Qt view cannot create a `tk.StringVar`.

Step 1c therefore makes the EDITOR own every variable the model touches, created through its host
at start-up (`TkUiHost` hands back a real `tk.*Var`, so the Tk panels bind `textvariable=` to the
existing object instead of creating it; a Qt or scripted host hands back an `ObservableValue` with
the same `get` / `set` / `trace_add`). The 35 view-only variables stay where they are.

## Phases

| # | Work | Branch | Est. |
|---|---|---|---|
| 1a | `uihost` package: protocol, `TkUiHost`, `ScriptedUiHost`; `self.ui` on editor + inspector | tk | days |
| 1b | services/mixins: dialogs and scheduling through `self.ui` (one file per commit, gate green) | tk | ~1 wk |
| 1c | model `tk.*Var` -> host-made variables; widget-building code in services moved to views | tk | ~1 wk |
| 1d | editor/inspector *own* a root instead of *being* one (`tk.Tk` base removed) | tk | ~1 wk |
| 2 | PySide6 in devenv (xcb libs from optiland's devenv.nix); `QtUiHost`; lifted shell (main window, docks, actions); `QVTKRenderWindowInteractor` viewport | Qt branch | 1-2 wk |
| 3 | 42 dialogs -> Qt (bulk) | Qt | 2-4 wk |
| 4 | Treeviews -> Qt model/view | Qt | 1-2 wk |
| 5 | Interaction layer on Qt events + re-proving the bug arc -- **the risk** | Qt | 1-2 wk+ |
| 6 | matplotlib embeds -> `FigureCanvasQTAgg` | Qt | days |
| 7 | editor-instantiating validators repointed; penta gate re-baselined | Qt | 1-2 wk |

## Verification rule

Every seam step lands with the penta gate green on the phases it touches, and changes no
behaviour on Tk. A converted call site is proved by a guard that drives the REAL code through
`ScriptedUiHost` -- asserting the question asked and the answer's effect -- never by grepping for
the new call.
