# 0852 -- the model declares its own state variables (Qt seam, step 1c part 1)

docs/design_qt_migration.md.

## Measured

`self.<name> = tk.*Var(...)` is defined 135 times: **92 by panels** (views -- through their
delegation shells, onto the editor), 33 by the inspector, 10 by the editor. **Model code reads or
writes 100 of them** -- 1174 `set` and 191 `get` calls, and nothing else. The model's state lived in
view-made objects: without the Tk panels these attributes would not exist, and a Qt view cannot
create a `tk.StringVar`.

## What landed

- **Host variable factories** -- `string_var` / `int_var` / `double_var` / `boolean_var` on every
  `UiHost`. `TkUiHost` makes a real `tk.*Var` (master = tkinter's default root, exactly as the
  calls it replaces); `ScriptedUiHost` makes an **`ObservableValue`** (`uihost/values.py`):
  `get` / `set` / `trace_add` / `trace_remove` / `trace_info`, with tkinter's coercion on `get`
  and its `(name, index, mode)` trace signature.
- **The editor's 10 and the inspector's 32 constructor variables** are made through `self.ui`.
- **`KrakenOS/UI/model_variables.py`** declares the **64** panel-made variables the model uses,
  with their values after start-up. `ensure_model_variables(owner)` runs right after the editor
  builds its UI and creates whichever are MISSING -- never replacing one, so a panel's variable
  and any trace a view put on it stay exactly as they were. Under Tk the panels made them all:
  it creates nothing and Tk behaviour does not change. Without Tk panels (a Qt shell, a scripted
  guard) it creates all 64.
- Deliberately not registered: 9 **dialog-scoped** summary/filter variables that exist only while
  their report dialog is open (view state of those dialogs), and 20 view-only variables.

## Guard

`validate_open3d_0852_model_variables.py`, penta phase 631.

- **V** `ObservableValue` against real tk variables side by side: coercion for every kind, write
  traces, `trace_remove`
- **F** the factories: the right tk classes from TkUiHost, the right kinds from ScriptedUiHost
- **R** a toolkit-free owner gets all 64 with kinds and values; an existing variable is never
  replaced, re-set or re-traced; a REAL editor's panels made every one (registry created none),
  all tk variables, each holding exactly the registry value -- the registry is current
- **C** completeness: every panel-made variable model code uses is registered or dialog-scoped,
  and none registered is stale -- a new unregistered one fails here (it caught `status_var`,
  which the first cut left out because the inspector and two dialogs have their own)
- **H** the editor's and inspector's constructors make no tk variable directly

## Verification

Full penta suite in six shards (the single-process run was killed for low memory): 625 of 631
pass. It found three PASS->FAIL flips -- phases 204, 294, 531 -- all SOURCE PINS asserting a
toggle's default by searching for the text `tk.BooleanVar(value=X)`, which the host-made
constructors no longer spell. No default changed. `uihost/introspect.constructor_variable_default`
reads the `value=` of whatever factory makes `self.<attr>`, and those three guards plus the five
same-shaped pins in `validate_3d_interaction_contract` now assert the default itself. Phase 52 is
the known env failure.

## Next (step 1c part 2)

Seven self-contained dialog functions still build Tk widgets inside services (inspection cell and
part, system selection, catalog matcher, beam-splitter resize, dimension edit, flag description;
~1050 lines) -- they move to the view layer. The context menus in open3d_face_assignment, the
table drawing and the menu refresh belong to Qt phases 5, 4 and 2.
