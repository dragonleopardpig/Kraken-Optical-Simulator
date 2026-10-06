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
| 0864 | Gaussian Beam report (this row once read "System Selection Calculator" -- wrong: that was never ported until 0930) | report + inputs |
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
| 0932 | Phase 5f part 3c: the browser's Properties / Selected-Element pane in Qt -- 5f complete | phase 5 |
| 0933 | Phase 5g part 1: the face-roles editor split into a toolkit-neutral session + VTK preview; the Tk dialog is a view (parity: identical state over 19 steps, pixel-identical preview); two latent Tk defects fixed | phase 5 |
| 0935 | The Qt shell's ribbon (tabs of icon groups over the shell's own actions) + command palette; folds on short screens | shell |
| 0965 | Missing CAD files: found by name first (layout folder, attachment/; unique names only), then a non-modal Qt window for the rest (a session shared with the Tk window); ribbon Scene > CAD > Missing Files | phase 3 |
| 0966 | Overlays > Modern look, on by default in the Qt shell: pale glass with a highlight, one quiet outline, rays that keep their hue but fade with their number, a gradient backdrop (the recipe is Optiland's viewer); display only -- the same actors, points and rays in both looks | shell parity |
| 0967 | The Inspection Cell VIEW: `services/inspection_cell_session.py` (composition and transplant, the double-click pick, opening a station, the file watch on the host's clock, the STEP export through the host), the Tk window a view of it, a non-modal Qt dialog with its own VTK view behind the `show_inspection_cell` seam | phase 7a |
| 0968 | Four panel-made model variables reached only by name (`__dict__.get`, a catalogue's string) are declared; the registry guard's scan sees that kind of use now | phase 7c |
| 0969 | An operand's surface choices are model data (`operand_surface_options`); the Tk panel registers its pickers and the Qt panel takes the list through a seam -- the model no longer walks the window's 409 widgets on every table sync | phase 7c |
| 0970 | Services that import tkinter: 14 -> 7. Six never needed it (dead imports, an annotation), `inspection_cell` makes its station's switches through the host; the seven left hold real Tk windows or menus and are pinned by a list that can only shrink | phase 7d |
| 0971 | Both interfaces stay (the user's decision). `python -m KrakenOS.UI` opens the preferred one: command line, then environment, then a saved per-user preference, else a question asked once; Interface Preference... is one form in both interfaces | phase 7h, 7i |
| 0972 | The Layouts / Machine Vision / Examples / Common Component menus are model data (`editor.selector_menu`): the Tk menu bar is refilled from it, and the Qt ribbon gets four buttons that show it -- the Qt interface had none of the four (132 layouts, 23 machine-vision layouts, ~400 examples) | phase 7d |
| 0974 | The modern look reaches the un-promoted optical STEP body: a smoked bronze chosen by measured contrast with the promoted prisms within it; and a selected element gets its own colours back (a defect of 0966) | look |
| 0976 | "Copy this text" is a model command (`copy_selected_text`, `copy_all_text`) with a Tk view (`panels/main_text_copy.py`): the nine Tk methods leave `services/analysis_compute_workflow.py` | phase 7d |
| 0964 | The Qt shell had NO 2D plot (built only by its guard): now a 2D Plot panel with the Tk plot toolbar's six controls (plot2d_toolbar.PLOT_2D), Trace Now, Update, Ray Inspector; an Update shows it | phase 6 |
| 0963 | The ribbon folds by the WINDOW's height (on crossing 1100 px), not the screen's; a fold by hand is kept | shell |
| 0962 | The top edge's panel tabs ride in the ribbon's tab row, no row of their own | shell |
| 0961 | The 3D toolbar is one tabbed strip (34 px, was 96) that hides; Hide All Panels on every edge strip (Ctrl+Shift+H); Clean 3D Scene (F11, ribbon corner) folds and hides everything and puts it back; phase 722 counts only the menu's own entries | shell |
| 0960 | Every flag froze the app 5-12 s on om05a: the recorder's snapshot rebuilt a refused STEP trace plan; refused plans are now kept and the snapshot only reads what the trace knows | both shells |
| 0959 | Flag Bug for the whole Qt window (Ctrl+Shift+B, a ribbon corner button): every flag carries the window, its dialogs and the shell's state; the Tk editor's 2D flag has its Qt route | shell |
| 0958 | Imported STEP hardware drawn soft (smooth body, one faint edge pass): an Overlays switch in both shells, on by default in the Qt shell's scene | shell |
| 0957 | Under Qt a bound key (`s`, Escape, Delete) ran its handler twice: one `s` wrote two flag bundles | phase 5 |
| 0956 | `tools/penta_parallel_gate.py`: the full gate as many small groups, several at a time, with memory admission and a watchdog (44.5 min instead of 1 h 54 min on 14 GB) | tooling |
| 0955 | The solve review windows (paraxial thickness, folded mirror, best image): fixed in Tk (broken since 2026-05-24), a modal Qt dialog from one shared description | phase 3 |
| 0954 | Atmospheric Settings in Qt (a fourth `system_controls` group): Tk menu-bar parity 75 of 75 | phase 6 |
| 0953 | Quick Estimation's four windows open in the running shell: three row forms (`FormPanel` for the design block) and a report | phase 5 |
| 0952 | Edge tabs hide and show the panels (upright on the left / right edges, flat on top, the bottom ones in the status bar); a small arrow folds the ribbon | shell |
| 0951 | The real inspector is the window's central 3D scene from start-up (Nav Cube and all); the preview is only the fallback; the ribbon's view commands drive it | shell |
| 0950 | The inspector's five small popups open in the running shell (`shell_host_of`; a row form; a flag-description session) | phase 5 |
| 0949 | The ribbon is the shell's only command surface: no menu bar; a File tab; six dropdown buttons hold the long lists; shortcuts registered on the window | shell |
| 0936 | Phase 5g part 3: Inspect Optical CAD/STL Solids as one report in both shells; the numeric Place/Orient assistant (uncalled since a53b72a3) removed | phase 5 |
| 0937 | Validator input fixtures kept in git (`test_fixtures/`, restored by the gates); the 0667 guard stops writing into attachment/ | tooling |
| 0938 | Phase 5g part 4: Measure MTF from Image as one session, Tk + Qt (old/new byte-identical CSVs) -- **5g complete** | phase 5 |
| 0939 | Phase 5h: the penta harness's 352 inspector phases re-run with the inspector hosted in the Qt shell -- 352/352 pass; `penta_validator_gate.py --shell qt` gates it (own baseline, ~15 min) | phase 5 |
| 0934 | Phase 5g part 2: the face-roles editor in the Qt shell -- a QDialog over the same session + preview, opened by the model's `show_face_roles_dialog` seam and the Edit menu | phase 5 |
| 0931 | Phase 5f part 3b: the Scene Components browser in Qt (tree data, selection, menus) | phase 5 |
| 0930 | Phase 5f part 3a: design constraints + the System Selection calculator in Qt (one implementation each) | phase 5 |
| 0929 | Phase 5f part 2: the 3D Live dock; Quick Estimation readouts owned by the model | phase 5 |
| 0928 | Phase 5f part 1: the 3D toolbar rows as one catalogue; Qt toolbar above the viewport | phase 5 |
| 0927 | Phase 5e: measure / box select / nav cube proven under Qt input; the solve banner re-wraps on a window resize | phase 5 |
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

## Status and remaining work (re-measured 2026-10-06, after 0965)

The phase table above is the original estimate. Where each phase stands, and what is left, measured
against the code rather than remembered (earlier measurements: 2026-09-27 after 0904, 2026-10-03
after 0945). The counts are a source scan of `KrakenOS/UI` with validators, captures and `archive/`
left out: 342 product modules.
"Shell parity" is work the table never had a row for: the main window's own panels, which turned
out to hide model state in Tk widgets just as the dialogs did.

| Phase | Status | Remaining, with sizes |
|---|---|---|
| 1a-1d seam | **done** (0851-0853) | -- |
| 2 shell + viewport | **done** (0854-0858) | -- |
| 3 dialogs | **done** (0859-0897 reports and row forms; 0933-0938 face roles, diagnostics, MTF from image; 0945 lens drawing; 0947 the sweep; 0950 + 0953 the inspector's popups; 0954 Atmospheric Settings; 0955 the solve reviews; 0965 missing CAD files; 0967 the Inspection Cell view) | -- no window a Qt user can reach is a `tk.Toplevel` any more. The 15 Tk-only `Toplevel` builders left are each the Tk VIEW of something the Qt shell shows its own way (row forms, reports, face roles and its coating table, MTF from image, lens drawing, CAD/STL placement, missing files, the Inspection Cell view, the calculator, Atmospheric Settings, the plot chooser, tooltips, the Tk editor's own flag and System Selection window) and go when Tk goes. 26 builders in all: those 15, 10 that ask the shell first, and the inspector itself (phase 5's row); 16 direct tkinter dialog calls remain, all inside those Tk views (phase 721 holds the count) |
| 4 tables -> model/view | **mostly done** (reports 0894-0897, surface table 0903, Path view on the table toolbar 0944, the right-click menu 0948: all 118 entries run in Qt with no Tk window since 0955) | **the Tk table is still the cell PARSER**: `_read_rows_from_table` is named 57 times in 24 files (23 in `services/layout_table_workbench.py`), and that module still asks the hidden Tk table for its selection in 10 places. This is the seam that must move before Tk can go |
| shell parity | **done.** Tk menu-bar commands routed 75 of 75 (0942-0945, 0954; phase 718); ribbon only since 0949 -- 6 tabs, 68 buttons + 6 dropdowns reach all 101 actions, a command palette, a fold arrow, and it folds by the window's height (0963); one 3D scene, the real inspector, central (0951), panels around it on edge tabs (0952) whose top strip rides in the ribbon's tab row (0962); a tabbed 3D toolbar that hides, Hide All Panels, Clean 3D Scene (0961); the 2D plot with the Tk plot toolbar's controls (0964); Flag Bug for the whole window (0959); docks, undo/redo, save, table copy/paste | ~~`_refresh_operand_surface_choices` walks every Tk widget~~ -- model data now (0969); ~~four model variables made only by a Tk panel and reached by name~~ -- declared (0968). The ribbon window's minimum width is 1234 px of the guard's 1240 |
| **5 interaction layer** | **done** (0905-0939, and the popups: 0950, 0953, 0959): the real inspector is the Qt shell's 3D scene, the harness's 352 phases pass with it there, and no inspector window a Qt user can reach is a Tk window | the inspector still IS a `tk.Toplevel` (`class Kraken3DInspector(Open3DDebugToolsMixin, tk.Toplevel)`, 26 058 lines, 129 `tk.`/`ttk.` references) -- its own step 1d, deferred since 0853; and the cursor decision below |
| 6 matplotlib | **done** (2D plot 0893, FormFigure 0887, MTF from image 0938) | -- |
| 7 validators + gate | **started**: `--shell qt` harness gate 352/352 (0939, last run 2026-10-05); 76 validators exercise the Qt shell | **validators:** 876 under `KrakenOS/UI`, 162 in no penta phase; 247 build a real editor (94 of them `headless=True`); 78 touch Tk directly (they import tkinter or call `winfo_*`, `event_generate`, `wait_window`, `nametowidget`, `tk.Toplevel`, `ttk.*` -- a wider net than the 63 counted on 10-03); 7 drive the model through `ScriptedUiHost`, 5 build a toolkit-free editor. **product code:** 50 of 342 modules import tkinter -- 26 of 44 panels and 5 of 7 widgets (views: expected), `uihost/tk_host.py`, 4 top-level modules (`layout_editor`, `open3d_inspector`, `context_menu`, `modern_ttk_theme`) and **14 of 151 services** (5 never use it; the other 9 hold 76 references). The editor makes a `tk.Tk()` root whatever the shell, so under Qt every Tk panel is still built, hidden. Then Qt as the default shell and the Tk-retirement decision |

**Gates.** Qt-hosted harness **352/352 at 45b312f5** (2026-10-06, X299-SSD, 43 min; covers 0966, whose
modern look is on by default there). Full Tk gate **733/733 at 8403abde** (2026-10-05, M90aPro; covers 0962-0965 and the fix to
0965), Qt-hosted harness 352/352. It took two passes -- another session's test run took the memory
and 31 phases went unreported; they were re-run one group at a time (bugs/0965 has the record).
Before it: 730/730 at 3265c622 (0961, X299-SSD), and **728/728 with 0959** (2026-10-04, on 5b070cd0 plus 0959), run in parallel
with `tools/penta_parallel_gate.py --jobs 4` (bugs/0956): 41.9 min, no group killed at the 6.5 GB
admission mark (lowest free memory 3.2 GB). The Qt-hosted harness (`--shell qt`): 352/352. Before it:
727/727 with 0958 (41.6 min), 726/726 at c45e41f6 (after 0954 and 0955), 44.5 min in
parallel where the sequential run took 1 h 54 min.
Before it: **724/724 with 0953** (2026-10-04, on 9aea5eb8 plus 0953; covers 0950-0953;
1 h 54 min on M90aPro in seven sequential chunks, lowest free memory 2.9 GB -- close to the 2.5 GB
watchdog, so quit other apps before the next one). Before it: 721/721 at 89c64ca9 (after 0948 and
0949), 720/720 at 7e384fdc (after 0947), 717/717 at 7ace2ca9. The baseline holds 733 phases, all pass,
734 the newest. On 14 GB hardware the parallel shard gate does
not fit (7 GB per shard): run it as sequential `--phases` chunks (1 h 42 min, bugs/0945).

### What is left, in order

1. ~~Sweep the Tk leftovers a menu can reach~~ -- **done (0947, phase 721).** Of 20 editor form
   commands run in the Qt shell, 14 opened Tk windows and 2 Tk message boxes before; none do now.
   "Set bounds" used to hang there (it waited on a Tk window).
2. ~~The table's right-click menu~~ -- **done (0948, phase 722).** The Tk builder fills a recording
   `MenuModel` and Qt renders it. Every one of its 118 distinct entries was run in a Qt shell; the
   reports it opens go to the Qt report dialog through a `show_report` seam on the Tk report
   handle. One entry still ends in Tk (Best Image Solve: the paraxial solve prompts, item 5).
3. **The inspector's popups.** ~~The small ones~~ -- **done (0950, phase 723):** the centred
   input, LED Edge Distance and Edit Thickness ask through the host, Resize Solid is a row form,
   and the bug-flag description is a session with a Tk and a Qt view. All five froze the Qt shell
   or were never seen before. ~~Quick Estimation's four windows~~ -- **done (0953, phase 725):**
   Target FOV, the FOV solve and the detector's design box are row forms (a `FormPanel` carries
   the design block), and the configuration table is a report. No inspector window a Qt user can
   reach is a Tk window now. ~~A Qt route for the 2D bug flag~~ -- **done (0959, phase 729):**
   Flag Bug (Ctrl+Shift+B, the ribbon's corner) pictures the whole window and every dialog, from
   anywhere in the window, a modal dialog included; every flag now carries the shell's state.
4. ~~Atmospheric Settings~~ -- **done (0954, phase 726): menu parity 75 of 75.** A fourth group
   of the `system_controls` catalogue in a window of its own; the model's command opens it through
   a `show_atmosphere_settings` seam.
5. ~~Paraxial solve prompts~~ -- **done (0955, phase 727).** The three "apply this?" windows are
   one description (`solve_reviews`) with a Tk window and a modal Qt dialog. They had been broken
   in the Tk app itself since 2026-05-24 (a non-widget handed to Tk as the parent). The table's
   right-click menu now has no entry that ends in Tk. ~~The 2D-plot toggles (cardinals,
   thickness)~~ -- **done (0964, phase 733)**, with the 2D plot itself, which the running Qt shell
   had never built. ~~The missing-assets decision~~ -- **done (0965, phase 734):** the user chose
   "find by name first, then a Qt window for the rest".
6. **Phase 7** -- validators off Tk, Qt the default shell, the Tk-retirement decision. Broken
   down below.

### Phase 7, broken down (measured 2026-10-06; the ORDER is a proposal, not yet agreed)

Everything a user does in the Qt shell now happens in Qt windows. What phase 7 has to change is
underneath: the Qt shell is still a set of Qt views over a model that keeps part of its state in
hidden Tk widgets, and the tests still reach the model through Tk.

| Step | What | Size |
|---|---|---|
| 7a | ~~The last window: the Inspection Cell view as a Qt window~~ -- **done (0967, phase 736).** Measured first: the Tk window was on screen in the Qt shell and dead (a 200 ms timer on it never fired). Now one session, a Tk view and a Qt view | done |
| 7b | **The model off the hidden Tk table:** the cell parser reads the rows from the model, not from a `ttk.Treeview`; the selection is asked of the shell (`_table_has_selection()` already does it for Group / Ungroup, 0948) | `_read_rows_from_table`: 57 references in 24 files; 10 `self.table.selection()` |
| 7c | ~~The variable sweep (0901)~~ -- **done.** Four panel-made variables reached only by name are declared (0968, phase 631; four, not seven -- three were host-made already), and an operand's surface choices are model data handed to each shell's pickers instead of a walk over every Tk widget (0969, phase 737: a table sync went from about 5 ms to 2.8) | done |
| 7d | **Services import no tkinter.** ~~The ones that never needed it~~ -- done (0970, phase 738): 14 -> 7. ~~The menu bar's Layouts / Examples menus~~ -- done (0972, phase 740): 7 -> 6. ~~The text copy helpers~~ -- done (0976, phase 743): 6 -> 5. **Left:** five services hold real Tk view code -- the Tk flag popup, the inline thickness editor, popup helpers, the LED edge prompt, the System Selection window -- and five import a Tk view package at module level; phase 738 lists both and may only shrink | 5 + 5 files |
| 7e | **The inspector owns its window** instead of being a `tk.Toplevel` -- step 1d for the inspector, as 0853 was for the editor | 1 class, 129 references |
| 7f | **The editor builds without a Tk root** under a host that is not Tk, so the Tk panels are not built in the Qt shell at all. Needs 7b-7e first | `layout_editor.py`: 39 references |
| 7g | **Validators off Tk:** the 78 that touch Tk directly are repointed (the model through `ScriptedUiHost`, a view through its own shell); the 247 that build an editor follow 7f | 78 + 247 validators |
| 7h | ~~Qt is the default shell~~ -- **replaced by the user's decision and done (0971, phase 739): the user chooses.** `python -m KrakenOS.UI` opens the preferred interface -- command line, environment, a saved per-user preference, else a question asked once | done |
| 7i | ~~The Tk-retirement decision~~ -- **decided 2026-10-06: Tk is NOT retired.** "I would like to have both TK and QT available, let user to choose his usage preference." The seam -- one model, a Tk view and a Qt view -- is permanent; `panels/` stays | decided |

7a-7d are independent of each other and each lands with the gate green on Tk; 7e and 7f are the
two structural steps; 7h can be decided at any point after 7a, because the user already works in
the Qt shell (the reports since 0957 are about it).

**Decided (the user, 2026-10-06):** both interfaces stay and the user chooses which opens (0971).
What that changes below: 7d part 2 is worth doing (Tk view code belongs in `panels/`, not in
`services/`); 7g is "both interfaces gated" rather than "validators off Tk"; 7e and 7f still
stand -- the Qt interface should not need a hidden Tk tree. **Still owed:** the cursor cues (below).

### Phase 5, broken down

| Step | What | Size (inspector methods unless noted) |
|---|---|---|
| 5a | event plumbing: the 30 bindings onto `QVTKRenderWindowInteractor` -- mouse, wheel, keys, modifiers. **Part 1 done (0905)**: handlers built apart from their Tk binding, `dispatch_viewport_event`, `VIEWPORT_KEYS`, cursor/timer/pointer seams, `_attach_vtk_core`. **Part 2 done (0906)**: the Qt shell hosts the real inspector (View -> 3D Inspector) and feeds it Qt events; the right-button press is held for 5c | 30 bindings |
| 5b | hover and pick, keeping the modifier contract (plain = face, Alt = nearest drawn edge; two event streams). The event half landed with 0906 (hover order, Alt on/off, a click picks what dispatch picks); what remains is proving the RESULTS match Tk -- face vs edge highlight, hover status text, the thickness-handle and nav-cube hovers -- and moving the inspector's hidden Tk status line into the shell **Done (0926)**: nothing to port -- swept with real Qt input and with the Tk bindings' own sequence (VTK motion first, then the hover handler), every hover field, the outline GEOMETRY (face vs nearest drawn edge, plain vs Alt on the vendor LED), the hover text, the status line, the nav-cube cell and the thickness-handle hover are identical at every pixel; the inspector's status line already reaches the shell's status bar (0906) | ~133 |
| 5c | right-click contextual scene commands as Qt menus. **Done (0907)**: the builders are unchanged -- `new_context_menu` hands them a recording `MenuModel` under a shell and Qt renders it; verbs that open a Tk DIALOG run but the dialog cannot show until 5f/5g | 16 builders |
| 5d | drag / move / rotate, snap, glue -- the densest bug arc (0433 stay-put, 0503 glue, 0693 frame). **Done (0925)**: nothing to port in the gesture layer -- a static audit of the drag code found only host-routed timers, and real Qt input commits the SAME change as the dispatched gesture for a move-handle drag, a rotate-handle click and both long-press carries (the carry-hold timer is a QTimer under Qt). The one Tk-only piece was the "Place/Orient CAD/STL Solid" side panel (built in the withdrawn Toplevel, never seen): it is now `row_forms/stl_placement.py`, shown by the shell as a non-modal dialog, and its Done keeps the shell's inspector (Tk's Done closes the separate 3D window) | ~62 |
| 5e | measure tool, box select, navigation cube, banner/HUD. **Done (0927)**: a static audit found no Tk-bound call on the path; a nav-cube click, a two-click measure and a rubber-band box give the same camera / segment / rows with real Qt input as dispatched. Found: the solve banner was wrapped to the viewport only on a scene refresh, so a window resize (either toolkit) left it running past the edge and over the nav cube -- it now re-lays out when the render window's size changes | ~69 |
| 5f | Scene Components tree + the 3D top/live controls. **Top controls done (0928)**: the View / Scene / Carry rows are a catalogue (`open3d_toolbar.py`) rendered by Tk and by `qt/inspector_toolbar.py` above the Qt viewport, bound to the same model variables; **Live controls done (0929)**: 26 of the Tk panel's 28 editor variables were already in the Qt System/Source/Trace docks; the rest -- the header, two display choices, Quick Estimation (model-owned readouts now) and the Variable-thickness solve -- are a 3D Live dock; **Constraints + System Selection done (0930)**: the design-constraint block's logic is `design_constraints_model.py` and the calculator's is `system_selection_text` (one implementation each, Tk + Qt); Qt gets the block in the 3D Live dock and the calculator as a row-form dialog (Analysis menu + dock button); **Scene Components tree done (0931)**: the browser's tree is data (`tree_nodes`), a click is `select_iid`, a right-click `show_menu_for_iid`, its four menus go through `new_context_menu`; Qt draws a Scene Components dock from them. **Properties pane done (0932)**: `properties_for` is the pane as data, `apply_face_direction` takes the value; Qt shows Import / Properties / Selected Element / STEP Placement under the tree. **5f complete.** | 1 639 + 374 + 559 lines |
| 5g | **CAD handling**: the face-roles editor (VTK preview with click-picking, 2 034 lines), the optical-solid utility dialogs (273), MTF-from-image (draw-a-box, 406). **Face-roles part 1 done (0933)**: `face_roles_session.py` holds the records, selection, form, messages and every action (timers + questions through `host_of`); `face_roles_preview.py` is the VTK scene, pick and orbit, fed any renderer; the Tk dialog is a view over them. **Face-roles part 2 done (0934)**: `qt/dialogs/face_roles_dialog.py` renders the same session (the model hands it to `editor.show_face_roles_dialog`; Edit -> Assign CAD/STL Optical Faces); the debounced retrace runs on the Qt timer. **Utility dialogs done (0936)**: the diagnostics are `reports/optical_solid_diagnostics.py` (Tk `ReportWindow` + Qt report dialog); the numeric Place/Orient assistant was dead code (its caller replaced by the 3D placement handler in May) and was removed. **MTF from Image done (0938)**: `mtf_from_image_session.py` + Tk view + Qt dialog (File menu, ribbon). **5g complete.** | 2 713 lines |
| 5h | re-prove the bug arc: every penta phase that drives the inspector, re-run against the Qt interactor. **Done (0939)**: `KRAKEN_PENTA_SHELL=qt` hosts the inspector in the real Qt shell and runs the harness's own 352 phases -- all pass; `tools/penta_validator_gate.py --shell qt` keeps it gated (own baseline). Real Qt INPUT parity is the per-step guards 704-716. **Phase 5 complete.** | gate |

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
