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
| | + `ReportChoice` / `ReportValue` (controls), `DetailView` / `DetailText` / `TreeRow` (detail and hierarchy), `ReportAction` + `ReportUpdate` (a verb, and one that writes back), `Report.csv_writer` (an export that is not the table) |
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
| master / detail (prose) | `Report` + `DetailText` | the same dialog, split |
| a verb, or an export that is not the table | `ReportAction`, `Report.csv_writer` | the same dialog's button box |
| a verb that changes the inputs | `ReportAction` -> `ReportUpdate` | the same, then a rebuild |
| where a report opens, and a double-click | `Report.initial_key`, `ReportAction.on_activate` | the same in both |
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
| 0887 | Surface Shape Builder + `FormFigure` (the matplotlib seam; most of phase 6) | row form |
| 0888 | Path Component placement + `RowForm.labels` (a choice renames a field) | row form |
| 0889 | Camera + Lens Matcher + `RowForm.read_only` (inputs and verbs, nothing to apply) | record list |
| 0890 | Galvo scan overlay + grating settings — the first tail pair needing nothing new | row form |
| 0891 | Tolerance preset + optimisation bounds (the panel decides where a refusal lands) | row form |
| 0892 | Tolerance preset chooser + beam-splitter resize — phase 3's dialog tail done | row form |
| 0893 | The 2D layout plot in Qt; the last Tk leaks out of the model | phase 6 |
| 0894 | The four report dialogs onto the shared Tk renderer; `DetailText` in both shells | report |
| 0895 | Ray + Trace Path inspectors onto it; `ReportAction` and `csv_writer` in both shells | master / detail, tree |
| 0896 | Paraxial Matrix + Gaussian Beam onto it; `ReportUpdate` (a verb that writes back) | report + inputs |
| 0897 | Non-Sequential Scene Graph -- its first builder, so Qt has it at all; `initial_key`, `on_activate` | tree |
| 0898 | Results / Debug / Progress as model data; Qt gets all three docks | phase 6 |
| 0899 | The 24 analysis plots as a catalogue; Qt gets the picker, Update and WFront 3D | phase 6 |
| 0900 | The system inputs as a catalogue; Qt gets the System dock, bound to the model's variables | phase 6 |
| 0901 | The 23 source inputs as a second group; one Qt class renders both docks | phase 6 |
| 0902 | The 15 trace inputs; the 45 enable rules and two live lists moved from Tk layout onto the model | phase 6 |
| 0903 | The surface table editable in Qt: selection seams, one `commit_cell`, the six verbs | phase 4 |
| 0904 | Optimisation in Qt: operand seam, Start/Stop seam, cell verbs, Optimization dock | phase 6 |
| 0905 | Phase 5a part 1: viewport handlers reachable without Tk; key table; cursor/timer/pointer seams; `_attach_vtk_core` | phase 5 |
| 0906 | Phase 5a part 2: the Qt shell hosts the REAL inspector (3D Inspector dock); Qt input -> dispatches; three Tk-armed timers and the pointer-over test moved onto the host | phase 5 |
| 0907 | Phase 5c: the 16 right-click menu builders fill a `MenuModel` under a shell; Qt shows it as a QMenu running the same callables | phase 5 |
| 0926 | Phase 5b: hover/pick results proven identical to Tk (om05a + LED, plain + Alt); no port needed | phase 5 |
| 0925 | Phase 5d: placement drags proven equal under Qt input; the CAD/STL placement panel as a row form + `show_row_form` seam; Qt honours `close_after` on every form | phase 5 |

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

The Tk view of every *report* is `panels/report_view.ReportWindow` (0894), the counterpart of
`qt/dialogs/report_dialog.py`. The four windows that still hand-built a `ttk.Treeview` over an
existing builder went onto it, and the pane only Tk had -- Source Illumination's per-source
detail prose -- became `Report.detail_text`, so Qt shows it too. 0895 took the last two, the Ray and Trace
Path inspectors, and with them the two remaining things a report could not say: a verb
(`ReportAction`) and an export that is not the table (`Report.csv_writer` -- these two flatten a
ray into one row per hit under ~140 columns, so Qt had been exporting a different file).

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

## Status and remaining work (measured 2026-09-27, after 0904)

The phase table above is the original estimate. Where each phase stands, and what is left, measured
against the code rather than remembered. "Shell parity" is work the table never had a row for: the
main window's own panels, which turned out to hide model state in Tk widgets just as the dialogs did.

| Phase | Status | Remaining, with sizes |
|---|---|---|
| 1a-1d seam | **done** (0851-0853) | -- |
| 2 shell + viewport | **done** (0854-0858) | -- |
| 3 dialogs | **mostly done** (0859-0897; 9 report builders, row forms) | lens drawing surface properties + PDF export (353 lines); atmosphere panel (220); the three paraxial solve prompts inside `main_paraxial_analysis_dialogs` (471); missing-assets (559) -- a resolution workflow, not a report: port as its own dialog or keep Tk-only, a decision owed |
| 4 tables -> model/view | **mostly done** (reports 0894-0897, surface table 0903) | the table's right-click menu -- 529 lines, 12 submenus, only the optimisation entries ported (0904); the Tk table is still the cell PARSER (`_read_rows_from_table`), the seam that must move before Tk can go |
| shell parity | **done for the core workflow** (0893, 0898-0904: plot, results/logs, plot picker, system/source/trace inputs, table editing, optimisation) | 2D-plot toolbar toggles (cardinals, thickness, path view); `_refresh_operand_surface_choices` still walks every Tk widget; the `self.__dict__.get` sweep (0901) |
| **5 interaction layer -- THE RISK** | **5a + 5c done (0905-0907)**: the real inspector runs in a Qt dock -- orbit, pan, zoom, pick, hover, keys, Alt, timers, and every right-click menu; `SceneViewport` stays central until parity | measured: `open3d_inspector.py` is 26 234 lines / 828 methods but only **30** event bindings, and VTK itself is toolkit-neutral -- so 5 is re-plumbing, not a rewrite. Four more services are Tk-bound (`three_d_scene_tools` 6 782, `scene_placement_commands` 10 385, `open3d_face_assignment` 3 059, `open3d_interaction` 1 611). Sub-steps below |
| 6 matplotlib | **done except inside phase-5 dialogs** (2D plot 0893, FormFigure 0887) | the embeds in MTF-from-image and the face-roles editor move with 5g |
| 7 validators + gate | **not started** | 226 validators build a real editor, 38 of them drive Tk widgets directly; ~165 validators are in no penta phase; then Qt as the default shell and the Tk-retirement decision |

### Phase 5, broken down

| Step | What | Size (inspector methods unless noted) |
|---|---|---|
| 5a | event plumbing: the 30 bindings onto `QVTKRenderWindowInteractor` -- mouse, wheel, keys, modifiers. **Part 1 done (0905)**: handlers built apart from their Tk binding, `dispatch_viewport_event`, `VIEWPORT_KEYS`, cursor/timer/pointer seams, `_attach_vtk_core`. **Part 2 done (0906)**: the Qt shell hosts the real inspector (View -> 3D Inspector) and feeds it Qt events; the right-button press is held for 5c | 30 bindings |
| 5b | hover and pick, keeping the modifier contract (plain = face, Alt = nearest drawn edge; two event streams). The event half landed with 0906 (hover order, Alt on/off, a click picks what dispatch picks); what remains is proving the RESULTS match Tk -- face vs edge highlight, hover status text, the thickness-handle and nav-cube hovers -- and moving the inspector's hidden Tk status line into the shell **Done (0926)**: nothing to port -- swept with real Qt input and with the Tk bindings' own sequence (VTK motion first, then the hover handler), every hover field, the outline GEOMETRY (face vs nearest drawn edge, plain vs Alt on the vendor LED), the hover text, the status line, the nav-cube cell and the thickness-handle hover are identical at every pixel; the inspector's status line already reaches the shell's status bar (0906) | ~133 |
| 5c | right-click contextual scene commands as Qt menus. **Done (0907)**: the builders are unchanged -- `new_context_menu` hands them a recording `MenuModel` under a shell and Qt renders it; verbs that open a Tk DIALOG run but the dialog cannot show until 5f/5g | 16 builders |
| 5d | drag / move / rotate, snap, glue -- the densest bug arc (0433 stay-put, 0503 glue, 0693 frame). **Done (0925)**: nothing to port in the gesture layer -- a static audit of the drag code found only host-routed timers, and real Qt input commits the SAME change as the dispatched gesture for a move-handle drag, a rotate-handle click and both long-press carries (the carry-hold timer is a QTimer under Qt). The one Tk-only piece was the "Place/Orient CAD/STL Solid" side panel (built in the withdrawn Toplevel, never seen): it is now `row_forms/stl_placement.py`, shown by the shell as a non-modal dialog, and its Done keeps the shell's inspector (Tk's Done closes the separate 3D window) | ~62 |
| 5e | measure tool, box select, navigation cube, banner/HUD | ~69 |
| 5f | Scene Components tree + the 3D top/live controls | 1 639 + 374 + 559 lines |
| 5g | **CAD handling**: the face-roles editor (VTK preview with click-picking, 2 034 lines), the optical-solid utility dialogs (273), MTF-from-image (draw-a-box, 406) | 2 713 lines |
| 5h | re-prove the bug arc: every penta phase that drives the inspector, re-run against the Qt interactor | gate |

5a is the prerequisite for everything after it; 5g needs 5a-5b (its preview picks faces).

**Found in 5a (0905), decision owed:** the Tk VTK widget has no cursor option, so all six cursor cues
in the Tk 3D view (hidden while carrying, crosshair while picking, resize arrow on a dimension drag)
have never shown -- every caller swallowed the TclError. Qt widgets do take a cursor, and since 0906
the shells DO differ on this until Tk is fixed (set the cursor on the widget's parent frame,
which it inherits) or the cues are dropped.

## Verification rule

Every seam step lands with the penta gate green on the phases it touches, and changes no
behaviour on Tk. A converted call site is proved by a guard that drives the REAL code through
`ScriptedUiHost` -- asserting the question asked and the answer's effect -- never by grepping for
the new call.
