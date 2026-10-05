"""Guard for bugs/0965: missing CAD files are found by name first; a Qt window asks about the rest.

In the Qt shell the missing-CAD-assets window was a Tk window on the hidden Tk root, with no Tk event
loop -- invisible or frozen -- so a layout with a moved CAD file loaded with placeholders and no way
to fix it. The user chose: find by name first (the layout's folder, the project's attachment/),
then a Qt window only for what is still missing, and a command to open it again.

  P  the session (toolkit-free), on real `SurfaceRow`s and temp files:
       P1 found by name: a missing file whose name matches ONE file under the search folders is
          pointed at it -- a row's path and an overlay's editor attribute alike; a name matching
          TWO different files is left alone (a guess could put the wrong part in the scene); a name
          found nowhere stays missing
       P2 Locate refuses a folder (the entry stays missing) and takes a file; Skip records the row's
          skip (the placeholder) and Reset clears it; Locate folder resolves the ambiguous one from
          the folder the user picked; close() runs the redraw ONCE
  L  the load's step (`_prompt_for_missing_cad_assets`) on a real editor: a missing file found next
     to the layout is repointed with no window at all, the progress log names it, and the redraw
     runs; with one found and one not, the shell is handed a session holding only the one still
     missing
  Q  in a real Qt shell: the window that opens is a Qt dialog, NOT modal, and no Tk window is made;
     Locate (the host's file picker) repoints the row, Skip marks the other, Continue closes it and
     redraws once; the ribbon's "Resolve Missing CAD Files..." opens it again for what is left, and
     says so when nothing is missing
  T  the Tk window is a view of the same session: it lists the session's entries, its Skip all
     remaining and Continue act on the session
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

RESULT_MARK = "MISSINGASSETS_RESULT "
SKIP_MARK = "MISSINGASSETS_SKIP "
SCENE = Path("KrakenOS/common_optical_layouts/beam_splitter_two_arm_doublets.py")
#: a tiny valid ASCII STL -- the files only have to exist and be read as STL if anything reads them
STL = "solid guard\nfacet normal 0 0 1\nouter loop\nvertex 0 0 0\nvertex 1 0 0\nvertex 0 1 0\nendloop\nendfacet\nendsolid guard\n"


def _files(root: Path) -> dict:
    """The test's folders: the layout's folder, a catalogue folder with one name twice."""
    layout_dir = root / "layouts"
    catalogue = root / "catalogue"
    for folder in (layout_dir, catalogue / "a", catalogue / "b", root / "picked"):
        folder.mkdir(parents=True, exist_ok=True)
    paths = {
        "layout": layout_dir / "layout.py",
        "found": layout_dir / "guard_found_here.stl",
        "lens": catalogue / "guard_lens_here.step",
        "twice_a": catalogue / "a" / "guard_twice.stl",
        "twice_b": catalogue / "b" / "guard_twice.stl",
        "picked": root / "picked" / "guard_twice.stl",
        "loose": root / "picked" / "guard_any.stl",
    }
    paths["layout"].write_text("# guard\n", encoding="utf-8")
    for key in ("found", "lens", "twice_a", "twice_b", "picked", "loose"):
        paths[key].write_text(STL, encoding="utf-8")
    return paths


def pure_checks() -> list:
    from types import SimpleNamespace

    from KrakenOS.UI.layout_editor import SurfaceRow
    from KrakenOS.UI.services.missing_assets_scan import MISSING_RESOURCE_STATE_ATTR, scan_missing_assets
    from KrakenOS.UI.services.missing_assets_session import MissingAssetsSession

    root = Path(tempfile.mkdtemp(prefix="missing0965_"))
    paths = _files(root)
    rows = []
    for name in ("guard_found_here.stl", "guard_twice.stl", "guard_nowhere.stl"):
        row = SurfaceRow()
        row.advanced = {"Solid_3d_stl": f"/missing/{name[:-4]}/{name}"}
        rows.append(row)
    redraws: list = []
    editor = SimpleNamespace(rows=rows, current_layout_file=str(paths["layout"]),
                             imported_lens_step_path=Path("/missing/lens/guard_lens_here.step"))
    for attr in ("imported_optical_step_path", "imported_camera_step_path", "imported_led_step_path"):
        setattr(editor, attr, None)
    assets = scan_missing_assets(rows, editor=editor)
    session = MissingAssetsSession(editor, assets, on_resolve=lambda: redraws.append(1))
    keys = [(asset.scope, asset.row_index) for asset in assets]
    found = session.auto_locate([paths["layout"].parent, root / "catalogue"])
    by = {(asset.scope, asset.row_index): session.status[i] for i, asset in enumerate(assets)}
    rows_after = [row.advanced["Solid_3d_stl"] for row in rows]
    p1 = (len(assets) == 4 and len(found) == 2
          and by == {("editor", -1): "located", ("row", 0): "located", ("row", 1): "missing", ("row", 2): "missing"}
          and rows_after[0] == str(paths["found"].resolve()) and Path(editor.imported_lens_step_path) == paths["lens"].resolve()
          and rows_after[1] == "/missing/guard_twice/guard_twice.stl")
    out = [["P1", p1, f"{len(assets)} missing {keys}; found by name {[(assets[i].key, p.name) for i, p in found]}; "
                      f"status {by}; row paths now {[Path(p).parent.name + '/' + Path(p).name for p in rows_after]}"]]

    nowhere = keys.index(("row", 2))
    twice = keys.index(("row", 1))
    refused = session.locate(nowhere, root / "picked")
    after_refusal = session.status[nowhere]
    taken = session.locate(nowhere, paths["loose"])
    state_taken = (session.status[nowhere], rows[2].advanced["Solid_3d_stl"] == str(paths["loose"].resolve()))
    session.reset(nowhere)
    session.skip(nowhere)
    skipped = (session.status[nowhere], "Solid_3d_stl" in (rows[2].advanced.get(MISSING_RESOURCE_STATE_ATTR) or {}).get("keys", []))
    session.reset(nowhere)
    cleared = (session.status[nowhere], MISSING_RESOURCE_STATE_ATTR not in rows[2].advanced)
    matched, message = session.locate_folder(root / "picked")
    folder = (matched, session.status[twice], rows[1].advanced["Solid_3d_stl"] == str(paths["picked"].resolve()))
    session.close()
    session.close()
    out.append(["P2", bool(refused) and after_refusal == "missing" and taken == "" and state_taken == ("located", True)
                and skipped == ("skipped", True) and cleared == ("missing", True)
                and folder[1:] == ("located", True) and folder[0] >= 1 and redraws == [1],
                f"Locate a folder: refused ({refused.splitlines()[0] if refused else ''!r}), still {after_refusal}; a file: "
                f"{state_taken}; Skip -> {skipped}; Reset -> {cleared}; Locate folder -> {folder} (message {message!r}); "
                f"close() twice -> redraws {len(redraws)}"])
    return out


def _load_case(editor, root: Path, *, found: bool, unfindable: bool) -> dict:
    """Point two rows at missing files, run the load's step, report what happened."""
    paths = _files(root)
    editor.current_layout_file = paths["layout"]
    targets = []
    if found:
        editor.rows[2].advanced["Solid_3d_stl"] = "/missing/elsewhere/guard_found_here.stl"
        targets.append(2)
    if unfindable:
        editor.rows[3].advanced["Solid_3d_stl"] = "/missing/elsewhere/guard_nowhere_at_all.stl"
        targets.append(3)
    handed: list = []
    redraws: list = []
    progress: list = []
    editor.show_missing_assets = lambda session: handed.append(session)
    editor._after_missing_assets_dialog = lambda: redraws.append(1)
    original_progress = editor.append_progress
    editor.append_progress = lambda text, *a, **k: (progress.append(str(text)), original_progress(text, *a, **k))
    try:
        editor._prompt_for_missing_cad_assets()
    finally:
        del editor.append_progress
        del editor._after_missing_assets_dialog
        del editor.show_missing_assets
    result = {"rows": {index: editor.rows[index].advanced.get("Solid_3d_stl") for index in targets},
              "handed": len(handed), "redraws": len(redraws),
              "logged": [line for line in progress if "found by name" in line],
              "status": str(editor.status_var.get())}
    if handed:
        session = handed[0]
        result["left"] = [session.assets[i].expected_path.name for i in session.unresolved()]
        result["auto"] = [path.name for _i, path in session.auto_located]
    for index in targets:
        editor.rows[index].advanced.pop("Solid_3d_stl", None)
    return result


def tk_checks() -> list:
    """L on the Tk editor, then T: the Tk window over a session."""
    import tkinter as tk

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.panels.missing_assets_dialog import MissingAssetsDialog
    from KrakenOS.UI.services.missing_assets_scan import scan_missing_assets
    from KrakenOS.UI.services.missing_assets_session import MissingAssetsSession

    editor = KrakenLayoutEditor()
    editor.layout_files[SCENE.stem] = SCENE
    editor.load_layout_by_name(SCENE.stem)
    for _ in range(4):
        editor.update()
    windows: list = []
    init = tk.Toplevel.__init__

    def counting(self, *args, **kwargs):
        init(self, *args, **kwargs)
        windows.append(type(self).__name__)

    tk.Toplevel.__init__ = counting
    try:
        only_found = _load_case(editor, Path(tempfile.mkdtemp(prefix="load0965_")), found=True, unfindable=False)
        both = _load_case(editor, Path(tempfile.mkdtemp(prefix="load0965b_")), found=True, unfindable=True)
    finally:
        tk.Toplevel.__init__ = init
    found_path = Path(only_found["rows"][2] or "")
    rows = [["L", found_path.name == "guard_found_here.stl" and found_path.exists() and only_found["handed"] == 0
             and only_found["redraws"] == 1 and len(only_found["logged"]) == 1 and "Found 1" in only_found["status"]
             and windows == [] and both["handed"] == 1 and both["left"] == ["guard_nowhere_at_all.stl"]
             and both["auto"] == ["guard_found_here.stl"] and both["redraws"] == 0,
             f"one missing, found next to the layout: row -> {found_path.parent.name}/{found_path.name}, windows "
             f"{only_found['handed']} (Tk windows made {windows}), redraws {only_found['redraws']}, logged "
             f"{only_found['logged'][:1]}, status {only_found['status']!r}; one found + one not: the shell got "
             f"{both['handed']} session(s) asking about {both.get('left')} (found by name: {both.get('auto')}), "
             f"redraws {both['redraws']} (on close)"]]

    # T -- the Tk window over a session
    editor.rows[3].advanced["Solid_3d_stl"] = "/missing/elsewhere/guard_tk_view.stl"
    redraws: list = []
    session = MissingAssetsSession(editor, scan_missing_assets(editor.rows, editor=editor),
                                   on_resolve=lambda: redraws.append(1))
    MissingAssetsDialog.run(editor, session=session, modal=False)
    for _ in range(4):
        editor.update()
    dialog = next((child for child in editor.winfo_children() if isinstance(child, MissingAssetsDialog)), None)
    listed = len(dialog._tree.get_children()) if dialog is not None else -1
    if dialog is not None:
        dialog._on_skip_all()
        skipped = list(session.status)
        dialog._on_close()
    else:
        skipped = []
    editor.rows[3].advanced.pop("Solid_3d_stl", None)
    editor.rows[3].advanced.pop("MissingResourceState", None)
    rows.append(["T", dialog is not None and listed == len(session.assets) >= 1 and skipped == ["skipped"] * listed
                 and session.closed and redraws == [1],
                 f"the Tk window lists {listed} of the session's {len(session.assets)} entries; Skip all remaining -> "
                 f"{skipped}; Continue -> session closed {session.closed}, redraws {len(redraws)}"])
    return rows


def qt_checks() -> list:
    import time
    import tkinter as tk

    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.uihost import host_of

    app, window = build(["guard"])
    window.show()
    app.processEvents()
    window.build_scene()
    window.load_layout_path(SCENE)
    editor = window.editor

    def settle(seconds: float = 0.3) -> None:
        end = time.time() + seconds
        while time.time() < end:
            app.processEvents()
            time.sleep(0.02)

    settle(1.5)
    root = Path(tempfile.mkdtemp(prefix="qt0965_"))
    paths = _files(root)
    editor.current_layout_file = paths["layout"]
    editor.rows[2].advanced["Solid_3d_stl"] = "/missing/elsewhere/guard_qt_one.stl"
    editor.rows[3].advanced["Solid_3d_stl"] = "/missing/elsewhere/guard_qt_two.stl"
    redraws: list = []
    editor._after_missing_assets_dialog = lambda: redraws.append(1)
    windows: list = []
    init = tk.Toplevel.__init__
    tk.Toplevel.__init__ = lambda self, *a, **k: (init(self, *a, **k), windows.append(type(self).__name__))[0]
    host = host_of(window)
    host.askopenfilename = lambda **_options: str(paths["loose"])
    try:
        editor._prompt_for_missing_cad_assets()
        settle()
        dialog = window.last_missing_assets_dialog
        opened = dialog is not None and dialog.isVisible() and not dialog.isModal()
        listed = dialog.table.rowCount() if dialog is not None else -1
        if dialog is not None:
            dialog.table.selectRow(0)
            QTest.mouseClick(dialog.buttons["Locate..."], Qt.MouseButton.LeftButton)
            dialog.table.selectRow(1)
            QTest.mouseClick(dialog.buttons["Skip"], Qt.MouseButton.LeftButton)
            statuses = [dialog.table.item(i, 3).text() for i in range(dialog.table.rowCount())]
            located = editor.rows[2].advanced.get("Solid_3d_stl") == str(paths["loose"].resolve())
            QTest.mouseClick(dialog.buttons["Continue"], Qt.MouseButton.LeftButton)
            settle()
            closed = not dialog.isVisible()
        else:
            statuses, located, closed = [], False, False
        # the ribbon's command: something left (the skipped one is not asked again; reset it) ...
        editor.rows[3].advanced.pop("MissingResourceState", None)
        before = window.last_missing_assets_dialog
        window.action_manager["missing_assets"].trigger()
        settle()
        again = window.last_missing_assets_dialog
        reopened = again is not None and again is not before and again.isVisible() and again.table.rowCount() == 1
        if again is not None:
            again.close()
            settle()
        # ... and nothing left
        editor.rows[3].advanced.pop("Solid_3d_stl", None)
        editor.rows[2].advanced.pop("Solid_3d_stl", None)
        window.action_manager["missing_assets"].trigger()
        settle()
        none_said = str(editor.status_var.get())
    finally:
        tk.Toplevel.__init__ = init
        del editor._after_missing_assets_dialog
        del host.askopenfilename
    return [["Q", opened and listed == 2 and windows == [] and statuses == ["located", "skipped"] and located and closed
             and redraws[:1] == [1] and reopened and "No missing CAD files" in none_said,
             f"a Qt window, not modal: {opened}, listing {listed}; Tk windows made {windows}; Locate + Skip -> {statuses}, "
             f"row repointed {located}; Continue closed it {closed}, redraws {len(redraws)}; the ribbon command reopened "
             f"it for what is left: {reopened}; with nothing missing it says {none_said!r}"]]


def _run(call: str, module_call: str) -> list:
    driver = (
        "import json, os\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY')\n"
        "    raise SystemExit(0)\n"
        f"from KrakenOS.UI.validate_missing_assets_found_by_name import {module_call}\n"
        # flushed, then exit WITHOUT interpreter teardown (a Tk/Qt teardown crash must not lose it)
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
            return [["X", True, f"SKIP {call}: " + line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-6:]
    return [["X", False, f"{call} exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    rows = pure_checks() + _run("tk_checks()", "tk_checks") + _run("qt_checks()", "qt_checks")
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
