"""Guard for bugs/0947: a form the MODEL opens shows in the running shell, not in a Tk window.

The Qt shell's own menu actions build their forms themselves, so they always opened Qt dialogs. But
the editor's commands -- what the Tk menus, the surface table's right-click menu and the 3D
inspector's verbs call -- ended in Tk's `render_row_form` and in `tkinter.messagebox`, which the Qt
shell cannot show (its Tk root is withdrawn). Eighteen panels did, plus 18 dialog calls.

  S  outside the Tk-only windows listed in `TK_ONLY`, no module calls `render_row_form(` or a
     tkinter dialog function directly; and that list is exact -- a file with fewer calls than
     listed fails until the list is shortened, so it can only shrink
In a real Qt shell on the two-arm doublets example:
  F  every editor form command opens a QT dialog titled as its form, or -- when the form refuses
     -- says so through the host or on the status line, as that command always did; not one
     creates a Tk window or calls a tkinter dialog
  G  the model's route and the Qt menu action open the SAME dialog at the same size (the glass
     catalogue: a record list, so the dialog's own 1120 x 720 rule, which a smaller Tk hint does
     not undercut); a form whose Tk geometry is larger than that rule gets it (the Shape Builder,
     1180 x 760)
  W  a command that waits for its form (Set bounds) returns only once the dialog is closed
In the Tk editor:
  T  the same commands still open Tk windows sized by their geometry hint, grown only to fit their
     content, and Set bounds still waits
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "QTFORMS_RESULT "
SKIP_MARK = "QTFORMS_SKIP "
LAYOUT = Path("KrakenOS/common_optical_layouts/beam_splitter_two_arm_doublets.py")
SPLITTER, LENS, DETECTOR = 1, 2, 6

#: Tk-ONLY windows: code that runs only inside a Tk window (the Tk renderers, the Tk views of ported
#: sessions, windows with no Qt counterpart yet) -> (render_row_form calls, tkinter dialog calls).
#: Every other module must have none. The numbers are exact, so this list can only shrink.
TK_ONLY = {
    "panels/row_form_view.py": (1, 1),                         # the renderer; present_row_form's fallback
    "panels/mtf_from_image_dialog.py": (0, 4),                 # Tk view of mtf_from_image_session
    "panels/main_optical_solid_face_roles_dialog.py": (0, 1),  # Tk view of face_roles_session
    "panels/main_paraxial_analysis_dialogs.py": (0, 1),        # inside the Tk paraxial calculator
    "panels/optical_stl_placement_dialog.py": (0, 2),          # the Tk visual placement window
    "panels/inspection_cell_window.py": (0, 1),                # the Tk inspection-cell window
    "panels/missing_assets_dialog.py": (0, 9),                 # no Qt counterpart yet (decision owed)
}

#: (command, arguments, the form's title or "" when the scene makes it refuse)
COMMANDS = (
    ("open_beam_splitter_settings", (SPLITTER,), "Beam Splitter"),
    ("open_coating_material_editor", (LENS,), "Coating"),
    ("open_advanced_surface_editor", (LENS,), "Advanced"),
    ("open_error_map_editor", (LENS,), "Error Map"),
    ("open_surface_shape_builder", (LENS,), "Shape"),
    ("open_diffuse_scatter_settings", (LENS,), ""),             # not a Diffuse Object: refuses
    ("open_detector_settings", (DETECTOR,), "Detector"),
    ("open_scene_target_editor", (LENS,), ""),
    ("open_selected_path_local_pose_editor", (), ""),
    ("open_element_settings", (), ""),
    ("open_galvo_scan_overlay_settings", (LENS,), ""),
    ("open_surface_additional_settings", (LENS,), ""),
    ("open_glass_catalog_browser", (), "Glass"),
    ("open_scene_source_manager", (), "Source"),
    ("open_stock_lens_importer", (), "Stock Lens"),
    ("open_inspection_cell_dialog", (), ""),
    ("open_inspection_part_dialog", (), ""),
    ("open_camera_lens_matcher", (), ""),
    ("open_save_tolerance_solve_preset_dialog", (), ""),
    ("open_apply_tolerance_solve_preset_dialog", (), ""),
)


def static_checks() -> list:
    root = Path("KrakenOS/UI")
    render = re.compile(r"(?<![\w.])render_row_form\(")
    dialog = re.compile(r"\b(?:messagebox|filedialog|simpledialog)\.(?:show|ask)\w+\(")
    found: dict = {}
    for path in sorted(root.rglob("*.py")):
        name = path.relative_to(root).as_posix()
        if (path.name.startswith(("validate_", "capture_", "probe_", "diag_")) or "archive" in path.parts
                or "uihost" in path.parts or "__pycache__" in path.parts):
            continue
        code = "\n".join(line for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
                         if not line.lstrip().startswith(("#", "def render_row_form")))
        # a mention inside a docstring or comment is not a call: keep only lines that are code
        code = "\n".join(line for line in code.splitlines() if "``" not in line)
        counts = (len(render.findall(code)), len(dialog.findall(code)))
        if counts != (0, 0):
            found[name] = counts
    strays = {name: counts for name, counts in found.items() if name not in TK_ONLY}
    drifted = {name: (found.get(name, (0, 0)), allowed) for name, allowed in TK_ONLY.items()
               if found.get(name, (0, 0)) != allowed}
    return [["S", not strays and not drifted,
             f"{sum(a + b for a, b in found.values())} Tk-only calls in {len(found)} listed windows; outside them "
             f"(render_row_form, tkinter dialog): {strays}; listed files whose count changed (found, listed): {drifted}"]]


def qt_runtime_checks() -> list:
    import tkinter as tk
    import tkinter.filedialog as tk_filedialog
    import tkinter.messagebox as tk_messagebox
    import tkinter.simpledialog as tk_simpledialog

    from PySide6.QtCore import QTimer

    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.uihost import host_of

    tk_windows: list = []
    tk_dialogs: list = []
    tk_init = tk.Toplevel.__init__

    def counting_init(self, *args, **kwargs):
        tk_init(self, *args, **kwargs)
        tk_windows.append(self)

    tk.Toplevel.__init__ = counting_init
    for module, names in ((tk_messagebox, ("showinfo", "showwarning", "showerror", "askyesno")),
                          (tk_simpledialog, ("askinteger", "askfloat", "askstring")),
                          (tk_filedialog, ("asksaveasfilename", "askopenfilename"))):
        for name in names:
            setattr(module, name, (lambda n: lambda *a, **_k: tk_dialogs.append(n))(name))
    app, window = build(["guard"])
    window.show()
    app.processEvents()
    window.load_layout_path(LAYOUT)
    app.processEvents()
    editor = window.editor
    host = host_of(window)
    said: list = []
    for name in ("showinfo", "showwarning", "showerror"):
        setattr(host, name, (lambda n: lambda title=None, message=None, **_k: said.append((n, str(title))))(name))
    window.select_rows([LENS], LENS)

    outcomes: dict = {}
    wrong: list = []
    for command, arguments, title in COMMANDS:
        said.clear()
        editor.status_var.set("")
        before_windows, before_dialogs = len(tk_windows), len(tk_dialogs)
        previous = window.last_model_form_dialog
        try:
            getattr(editor, command)(*arguments)
            error = ""
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
        app.processEvents()
        dialog = window.last_model_form_dialog
        opened = dialog is not None and dialog is not previous and dialog.isVisible()
        shown = dialog.windowTitle() if opened else ""
        status = str(editor.status_var.get()).strip()
        outcomes[command] = (shown or (f"host:{said[0][1]}" if said else "")
                             or (f"status:{status[:40]}" if status else "") or error or "NOTHING")
        if (error or len(tk_windows) != before_windows or len(tk_dialogs) != before_dialogs
                or not (opened or said or status) or (title and title.lower() not in shown.lower())):
            wrong.append((command, outcomes[command], len(tk_windows) - before_windows, len(tk_dialogs) - before_dialogs))
        if opened:
            dialog.close()
            app.processEvents()
    kinds = {kind: sum(1 for value in outcomes.values() if value.startswith(kind)) for kind in ("host:", "status:")}
    forms = len(outcomes) - sum(kinds.values()) - sum(1 for value in outcomes.values() if value == "NOTHING")
    rows = [["F", not wrong and forms >= 12,
             f"{len(COMMANDS)} editor form commands: {forms} opened a Qt dialog, {kinds['host:']} refused through "
             f"the host, {kinds['status:']} on the status line; Tk windows {len(tk_windows)}, tkinter dialog calls "
             f"{len(tk_dialogs)}; wrong (command, got, Tk windows, Tk dialogs): {wrong}"]]

    # G -- one dialog, one size, whichever route opens it
    def size_of(dialog) -> tuple:
        app.processEvents()
        size = (dialog.width(), dialog.height()) if dialog is not None else (0, 0)
        if dialog is not None:
            dialog.close()
        return size

    editor.open_glass_catalog_browser()
    by_model = size_of(window.last_model_form_dialog)
    by_action = size_of(window.glass_catalog_action())
    editor.open_surface_shape_builder(LENS)
    shape = size_of(window.last_model_form_dialog)
    rows.append(["G", by_model == by_action == (1120, 720) and shape == (1180, 760),
                 f"the glass catalogue: {by_model} through the model, {by_action} through the Qt action (its Tk "
                 f"hint is 900 x 600); the Shape Builder {shape} (Tk hint 1180 x 760)"])

    # W -- a waiting command returns only after its dialog closes
    state = {"open_during_call": None}
    editor.current_menu_row_id = editor._table_item_for_row_index(LENS)
    editor.current_menu_field = "thickness"
    before_bounds = window.last_model_form_dialog

    def close_bounds() -> None:
        dialog = window.last_model_form_dialog
        state["open_during_call"] = dialog is not None and dialog is not before_bounds and dialog.isVisible()
        if state["open_during_call"]:
            state["title"] = dialog.windowTitle()
            dialog.reject()

    QTimer.singleShot(0, close_bounds)
    editor.edit_current_bounds()
    after = window.last_model_form_dialog
    rows.append(["W", state["open_during_call"] is True and after is not before_bounds and not after.isVisible()
                 and not tk_windows,
                 f"Set bounds: its dialog ({state.get('title')!r}) was open while the command ran: "
                 f"{state['open_during_call']}; closed when it returned: {after is not None and not after.isVisible()}; "
                 f"Tk windows {len(tk_windows)}"])
    return rows


def tk_runtime_checks() -> list:
    import tkinter as tk
    import tkinter.messagebox as tk_messagebox

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    for name in ("showinfo", "showwarning", "showerror"):
        setattr(tk_messagebox, name, lambda *a, **k: None)
    editor = KrakenLayoutEditor()
    editor.layout_files[LAYOUT.stem] = LAYOUT
    editor.load_layout_by_name(LAYOUT.stem, refresh=False)
    editor.update()

    def opened_by(call) -> list:
        before = set(editor.root.winfo_children())
        call()
        editor.update()
        return [w for w in set(editor.root.winfo_children()) - before if isinstance(w, tk.Toplevel)]

    glass = opened_by(editor.open_glass_catalog_browser)
    glass_size = glass[0].geometry().split("+")[0] if glass else ""
    # the hint is 900x600; Tk grows a window to its content's requested size, never below the hint
    fitted = (f"{max(900, glass[0].winfo_reqwidth())}x{max(600, glass[0].winfo_reqheight())}" if glass else "?")
    splitter = opened_by(lambda: editor.open_beam_splitter_settings(SPLITTER))
    titles = [w.title() for w in glass + splitter]
    waited = {"seen": None}
    editor.current_menu_row_id = editor._table_item_for_row_index(LENS)
    editor.current_menu_field = "thickness"
    real_wait = editor.wait_window

    def wait_window(target):
        waited["seen"] = isinstance(target, tk.Toplevel) and bool(target.winfo_exists())
        target.destroy()

    editor.wait_window = wait_window
    try:
        editor.edit_current_bounds()
    finally:
        editor.wait_window = real_wait
    return [["T", len(glass) == 1 and glass_size == fitted and glass_size.endswith("x600") and len(splitter) == 1
             and waited["seen"] is True,
             f"Tk opened {titles}; the glass catalogue at {glass_size!r} (its 900x600 hint, grown to its content: "
             f"{fitted!r}); Set bounds waited on its Tk window: {waited['seen']}"]]


def _run(call: str) -> list:
    driver = (
        "import json, os\n"
        "try:\n"
        "    import PySide6\n"
        "except Exception as exc:\n"
        f"    print({SKIP_MARK!r} + repr(exc))\n"
        "    raise SystemExit(0)\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY')\n"
        "    raise SystemExit(0)\n"
        "from KrakenOS.UI.validate_qt_model_forms_open_in_qt import qt_runtime_checks, tk_runtime_checks\n"
        # flushed, then exit WITHOUT interpreter teardown (a Qt/Tk teardown crash must not lose it)
        f"print({RESULT_MARK!r} + json.dumps({call}), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True, timeout=900,
                              env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return [["X", False, f"{call} timed out"]]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return [["X", True, line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
    return [["X", False, f"{call}: exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    rows = static_checks() + _run("qt_runtime_checks()") + _run("tk_runtime_checks()")
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
