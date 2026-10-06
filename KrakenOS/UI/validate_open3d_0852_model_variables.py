"""Guard: the model declares its own state variables (bugs/0852, docs/design_qt_migration.md
step 1c).

Measured: of 135 ``tk.*Var`` state variables, 92 were created by PANELS (views) onto the editor,
and model code read or wrote 100 of them -- 1174 ``set`` and 191 ``get`` calls. Without the Tk
panels those attributes would not exist, and a Qt view cannot create a ``tk.StringVar``.

Now the hosts make variables (``string_var`` / ``int_var`` / ``double_var`` / ``boolean_var``: a
real ``tk.*Var`` from TkUiHost, an ``ObservableValue`` otherwise), the editor's and inspector's
constructors create theirs through ``self.ui``, and ``model_variables.MODEL_VARIABLES`` declares
the 69 panel-made variables the model uses; ``ensure_model_variables`` creates whichever are
missing, never replacing one. Under Tk the panels have made them all, so nothing changes.

  V  ObservableValue behaves like a real tk variable, side by side: coercion on get for each
     kind, write traces with tk's (name, index, mode) signature, trace_remove
  F  the host factories: real tk variables of the right class from TkUiHost, ObservableValues of
     the right kind from ScriptedUiHost
  R  the registry: a toolkit-free owner gets all 69 with their kinds and start-up values; an
     existing variable (and its trace) is never replaced; a REAL editor has every one after
     start-up as a tk variable, holding exactly the registry value -- so the registry is current
  C  completeness: every panel-made variable model code uses is registered or named
     dialog-scoped, and every registered one is still made by a panel -- a new unregistered
     one fails here. "Uses" includes reaching it by NAME (bugs/0968): ``self.__dict__.get("x_var")``,
     ``getattr(editor, "x_var", None)``, a catalogue's ``"editor.x_var"`` -- four variables had
     slipped past a scan that looked for attributes only
  D  what the four are for, on an owner with NO Tk panel: the model's atmosphere and source
     summaries and its trace badge are written into the registry's variables (they were dropped:
     no variable, no write), and the 2D-layout switch is read from one
  H  the editor's and inspector's constructors create no tk variable directly
"""
from __future__ import annotations

import ast
import collections
from pathlib import Path
from types import SimpleNamespace

ROOT = Path("KrakenOS/UI")


def _panel_made_model_used() -> tuple[set[str], set[str]]:
    """(panel-made variables model code uses, every panel-made variable) -- by AST."""
    skip = ("validate_", "capture_", "warm_")
    files = [p for p in ROOT.rglob("*.py") if not p.name.startswith(skip) and "archive" not in p.parts]
    made_by_panel: set[str] = set()
    for path in files:
        if "panels" not in path.parts:
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8", errors="replace"))):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute):
                f = node.value.func
                if isinstance(f.value, ast.Name) and f.value.id in ("tk", "tkinter") and f.attr.endswith("Var"):
                    for t in node.targets:
                        if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == "self":
                            made_by_panel.add(t.attr)
    used = collections.Counter()
    for path in files:
        if "panels" in path.parts or "widgets" in path.parts:
            continue
        registry = path.name == "model_variables.py"      # its keys are declarations, not uses
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8", errors="replace"))):
            if isinstance(node, ast.Attribute) and node.attr in made_by_panel:
                used[node.attr] += 1
            # reached by NAME (bugs/0968): __dict__.get("x_var"), getattr(o, "x_var"), "editor.x_var"
            elif (not registry and isinstance(node, ast.Constant) and isinstance(node.value, str)
                  and node.value.rpartition(".")[2] in made_by_panel):
                used[node.value.rpartition(".")[2]] += 1
    return {name for name in made_by_panel if used[name]}, made_by_panel


def run_checks() -> tuple[bool, list[str]]:
    import tkinter as tk

    from KrakenOS.UI.model_variables import DIALOG_SCOPED_VARIABLES, MODEL_VARIABLES, ensure_model_variables
    from KrakenOS.UI.uihost import ObservableValue, ScriptedUiHost, TkUiHost

    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    root = tk.Tk()
    root.withdraw()
    try:
        # ---- V: ObservableValue against real tk variables ------------------------------------------
        cases = [("string", tk.StringVar, [5, "a", 2.5]), ("int", tk.IntVar, ["7", 3, 4.0]),
                 ("double", tk.DoubleVar, ["2.5", 3, 1e-3]), ("boolean", tk.BooleanVar, ["0", 1, "true", False])]
        mismatches = []
        for kind, tk_class, values in cases:
            real, ours = tk_class(master=root), ObservableValue(kind)
            for value in values:
                real.set(value)
                ours.set(value)
                if (real.get(), type(real.get())) != (ours.get(), type(ours.get())):
                    mismatches.append((kind, value, real.get(), ours.get()))
        ok(not mismatches, f"V1: get() coerces like tk for every kind ({mismatches or 'identical'})")
        seen_real, seen_ours = [], []
        real, ours = tk.StringVar(master=root), ObservableValue("string")
        h_real = real.trace_add("write", lambda *a: seen_real.append(a[1:]))
        h_ours = ours.trace_add("write", lambda *a: seen_ours.append(a[1:]))
        real.set("x"); ours.set("x")
        real.trace_remove("write", h_real); ours.trace_remove("write", h_ours)
        real.set("y"); ours.set("y")
        ok(seen_real == seen_ours == [("", "write")],
           f"V2: a write trace fires with tk's (name, index, mode) signature and stops after trace_remove "
           f"({seen_ours})")

        # ---- F: the factories ------------------------------------------------------------------------
        tk_host, scripted = TkUiHost(root), ScriptedUiHost()
        kinds = {"string_var": tk.StringVar, "int_var": tk.IntVar, "double_var": tk.DoubleVar, "boolean_var": tk.BooleanVar}
        ok(all(type(getattr(tk_host, m)()) is c for m, c in kinds.items())
           and [getattr(scripted, m)().kind for m in kinds] == ["string", "int", "double", "boolean"],
           "F: TkUiHost makes real tk variables of the right class; ScriptedUiHost makes ObservableValues "
           "of the right kind")
    finally:
        root.destroy()

    # ---- R: the registry -----------------------------------------------------------------------------
    owner = SimpleNamespace(ui=ScriptedUiHost())
    created = ensure_model_variables(owner)
    wrong = [n for n, (kind, value) in MODEL_VARIABLES.items()
             if not isinstance(getattr(owner, n), ObservableValue) or getattr(owner, n).kind != kind
             or getattr(owner, n).get() != value]
    # 65 since bugs/0901 added source_direction_preset_var, which model code reads through
    # self.__dict__.get(...); 69 since bugs/0968 taught the C scan to see that kind of read and
    # it found four more
    ok(len(created) == len(MODEL_VARIABLES) == 69 and not wrong,
       f"R1: a toolkit-free owner gets all {len(created)} declared variables with their kinds and "
       f"start-up values ({wrong or 'all right'})")
    keep = ObservableValue("string", "user text")
    fired = []
    keep.trace_add("write", lambda *a: fired.append(a))
    owner2 = SimpleNamespace(ui=ScriptedUiHost(), ray_count_var=keep)
    ensure_model_variables(owner2)
    ok(owner2.ray_count_var is keep and keep.get() == "user text" and not fired,
       "R2: an existing variable is never replaced, re-set or re-traced")

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    app = KrakenLayoutEditor(headless=True)
    try:
        import tkinter as tk2

        created_real = app._model_variables_created_at_init
        not_tk = [n for n in MODEL_VARIABLES if not isinstance(getattr(app, n, None), tk2.Variable)]
        drift = [(n, getattr(app, n).get(), d) for n, (_k, d) in MODEL_VARIABLES.items()
                 if n not in not_tk and getattr(app, n).get() != d]
        ok(created_real == [] and not not_tk and not drift,
           f"R3: a REAL editor's panels made every declared variable (the registry created "
           f"{created_real or 'none'}), all are tk variables, and each holds exactly the registry's "
           f"value after start-up ({drift or 'no drift'})")
    finally:
        app.destroy()

    # ---- C: completeness ----------------------------------------------------------------------------
    used, made = _panel_made_model_used()
    unregistered = sorted(used - set(MODEL_VARIABLES) - set(DIALOG_SCOPED_VARIABLES))
    stale = sorted(set(MODEL_VARIABLES) - made)
    ok(not unregistered and not stale,
       f"C: every panel-made variable model code uses is registered or dialog-scoped "
       f"(unregistered: {unregistered or 'none'}), and none registered is stale ({stale or 'none'})")

    # ---- D: what the four are for, with no Tk panel ---------------------------------------------------
    from KrakenOS.UI.services.layout_scene_projection import LayoutSceneProjectionMixin
    from KrakenOS.UI.services.layout_shell_controls import LayoutShellControlsMixin
    from KrakenOS.UI.services.source_modeling import SourceModelingMixin

    def panelless(**extra):
        bare = SimpleNamespace(ui=ScriptedUiHost(), **extra)
        ensure_model_variables(bare)
        return bare

    try:        # a missing variable is a FAILED claim here, not a crash that loses the others
        bare = panelless(_format_atmosphere_summary=lambda: "atmosphere says so",
                         _format_source_summary=lambda: "source says so")
        SourceModelingMixin._update_atmosphere_summary(bare)
        SourceModelingMixin._update_source_summary(bare)
        LayoutShellControlsMixin._sync_trace_state_badge(bare, {"requested": "Auto", "active": "Non-sequential"})
        written = (bare.atmosphere_summary_var.get(), bare.source_summary_var.get(), bare.trace_state_badge_var.get())
        shown_default = LayoutSceneProjectionMixin._show_layout_2d(bare)
        bare.show_layout_2d_var.set(False)
        shown_off = LayoutSceneProjectionMixin._show_layout_2d(bare)
        # before bugs/0968: the same calls on an owner WITHOUT the four variables
        old = SimpleNamespace(ui=ScriptedUiHost(), _format_atmosphere_summary=lambda: "x", _format_source_summary=lambda: "x")
        SourceModelingMixin._update_atmosphere_summary(old)
        SourceModelingMixin._update_source_summary(old)
        LayoutShellControlsMixin._sync_trace_state_badge(old, {"requested": "Auto", "active": "Non-sequential"})
        dropped = [name for name in ("atmosphere_summary_var", "source_summary_var", "trace_state_badge_var")
                   if name not in old.__dict__]
        ok(written == ("atmosphere says so", "source says so", "Scene: Auto -> Non-sequential")
           and shown_default is True and shown_off is False and len(dropped) == 3,
           f"D: with no Tk panel the model writes its summaries and badge into the registry's variables "
           f"{written} and reads the 2D-layout switch from one (on {shown_default}, off {shown_off}); without "
           f"them the same three writes went nowhere ({dropped})")
    except Exception as exc:
        ok(False, f"D: with no Tk panel the model's writes need the registry's variables -- raised {type(exc).__name__}: {exc}")

    # ---- H: the constructors ------------------------------------------------------------------------
    direct = []
    for path, cls in ((ROOT / "layout_editor.py", "KrakenLayoutEditor"), (ROOT / "open3d_inspector.py", "Kraken3DInspector")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == cls:
                for fn in node.body:
                    if isinstance(fn, ast.FunctionDef) and fn.name == "__init__":
                        for call in ast.walk(fn):
                            if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) \
                                    and isinstance(call.func.value, ast.Name) and call.func.value.id == "tk" \
                                    and call.func.attr.endswith("Var"):
                                direct.append(f"{path.name}:{call.lineno}")
    ok(not direct, f"H: the editor's and inspector's constructors make their variables through the host "
                   f"({direct or 'no direct tk.*Var'})")
    return state["ok"], notes


def run() -> int:
    passed, notes = run_checks()
    print()
    for note in notes:
        print(("  " + note[2:]) if note.startswith("= ") else ("! " + note))
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
