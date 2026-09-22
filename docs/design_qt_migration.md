# Qt migration -- design and plan

Status: **Phase 1 started 2026-09-22** on branch `tk`. 1a + 1b landed as bugs/0851 (the UI host; 175
call sites converted); 0850 (two broken static methods) was found on the way.

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
