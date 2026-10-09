"""Guard for bugs/0999: the Qt shell can run with NO Tk at all (docs/design_qt_migration.md phase 7f).

The Qt shell has always run a hidden Tk application beside itself: the editor's root with every
Tk panel, and the 3D inspector's withdrawn window with its own. Both can be built without
(bugs/0993, bugs/0998). With `KRAKEN_QT_TK_FREE=all` the shell asks for neither -- EXPERIMENTAL,
on request, until it is the default.

Run that way, the Qt-era phases of the gate (633-760) found four places where the editor still
called a Tk method on itself:

  * `_schedule_refresh_plot` asked its Tk root whether it exists -- and raised. The editor answers
    that itself now, as the inspector does (bugs/0998)
  * copying rows or text with no clipboard tool installed used Tk's clipboard by name, and
    pasting read it: the clipboard of a hidden application nothing pumps, and of none at all
    without a root. Both use the shell's clipboard
  * the plot auto-save waited for the Tk window to reach 1200 x 700: that test is the Tk window
    builder's now, and without a Tk window there is nothing of Tk's to wait for

  A  no Tk: on request the whole process -- the shell started, the 3D scene built, a session
     driven -- makes no Tk root, no Tk widget and no Tk variable (as it always was: 1 root,
     hundreds of widgets, the variables); the editor has no root and the inspector no window,
     and the 3D scene is up with the same actors
  S  the same shell: after every step the plain attributes of the editor and of the inspector
     equal the ones of the shell that has its hidden Tk application -- the actors' addresses
     and the timings in the debug log aside
  E  the editor answers for itself: it exists, and a plot refresh it schedules is put on the
     shell's host and runs
  C  the clipboard is the shell's, in both modes: an element's rows copied with no clipboard
     tool installed are on the Qt clipboard, and Paste reads them from there with the editor's
     own copy cleared -- and nothing from an empty clipboard
  P  the plot auto-save: without a Tk window it does not wait and the picture is written; with
     the hidden Tk window it waits as it always did; and the Tk window's test is unchanged --
     1200 x 700
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import traceback
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

RESULT_MARK = "QTNOTK_RESULT "
SKIP_MARK = "QTNOTK_SKIP "
LAYOUT = Path("KrakenOS/common_optical_layouts/beam_splitter_two_arm_doublets.py")
#: the editor's debug log carries how long things took; and which variables the HOST made is the
#: mode itself (none with the Tk panels, all 79 without) -- claim A holds that
TIMED = {"debug_lines", "_model_variables_created_at_init"}


def _claims(pairs) -> list:
    rows = []
    for key, claim in pairs:
        try:
            ok, detail = claim()
        except Exception as exc:        # a claim that raises is ITS failure, and the others still report
            ok, detail = False, f"raised {type(exc).__name__}: {exc}"
        rows.append([key, bool(ok), detail])
    return rows


def session(out: str) -> dict:
    """Start the Qt shell as the environment asks, build its 3D scene, drive it; record everything."""
    import shutil
    import tkinter as tk

    from KrakenOS.UI.validate_editor_without_tk_root import _canon, _digest
    from KrakenOS.UI.validate_inspector_without_tk_window import _normal

    made = Counter()
    phase = ["starting"]
    for cls, kind in ((tk.Tk, "roots"), (tk.BaseWidget, "widgets"), (tk.Variable, "variables")):
        real = cls.__init__

        def init(self, *args, _real=real, _kind=kind, **options):
            made[f"{_kind} {phase[0]}"] += 1
            return _real(self, *args, **options)

        cls.__init__ = init

    shutil.which = lambda *_args, **_options: None      # no clipboard tool: the shell's own clipboard is what is left
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtWidgets import QMessageBox

    for name in ("information", "warning", "critical"):
        setattr(QMessageBox, name, staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok))
    from KrakenOS.UI.qt.app import build

    app, window = build(["guard"])
    window.show()
    # The auto-save writes to a path the editor's module hands every service WHEN IT IS IMPORTED
    # (`_sync_layout_globals`) -- the user's own attachment folder. Point it at this guard's
    # folder only now, after `build` has imported the editor, or the import puts the real path
    # back; and it is checked again right before the auto-save is switched on.
    from KrakenOS.UI.services import layout_analysis_display

    picture = Path(out).with_name(Path(out).stem + "_auto_saved.png")
    picture.unlink(missing_ok=True)
    layout_analysis_display.AUTO_PLOT_PATH = picture

    def settle(seconds: float = 0.6) -> None:
        end = time.time() + seconds
        while time.time() < end:
            app.processEvents()
            time.sleep(0.02)

    settle(1.5)
    editor = window.editor
    editor.layout_files[LAYOUT.stem] = LAYOUT
    editor.load_layout_by_name(LAYOUT.stem, refresh=False)
    settle(1.0)
    phase[0] = "building the 3D scene"
    inspector = window.build_inspector_view().inspector
    settle(2.5)
    phase[0] = "in the session"

    def state(owner) -> dict:
        plain, objects = {}, []
        for key, value in list(owner.__dict__.items()):
            item = _canon(value)
            if item == "<object>":
                objects.append(key)
            else:
                item = _normal(item)
                plain[key] = item if len(json.dumps(item, default=str)) <= 3000 else {"<digest>": _digest(item)}
        return {"plain": plain, "objects": sorted(objects)}

    steps: list = []

    def record(label: str, result: str) -> None:
        steps.append([label, result, state(inspector), state(editor)])

    def step(label: str, call) -> None:
        try:
            call()
            result = "ok"
        except Exception as exc:
            where = " < ".join(frame.name for frame in traceback.extract_tb(exc.__traceback__)[-1:-5:-1])
            result = f"RAISED {type(exc).__name__}: {str(exc)[:140]} @ {where}"
        settle(0.8)
        record(label, result)

    record("built", "ok")
    step("refresh from the editor", inspector.refresh_from_editor)
    step("commit a cell", lambda: editor.commit_cell(3, "thickness", "7.25"))
    step("select rows", lambda: editor._select_table_indices([3, 4], focus_index=3))
    step("an analysis", lambda: editor.toggle_analysis_mode("spot"))
    step("refresh the plot", editor.refresh_plot)
    step("undo", editor.undo)

    # ---- E: a plot refresh the editor schedules -------------------------------------------------------
    refreshes: list = []
    real_refresh = editor._refresh_plot_from_controls
    editor._refresh_plot_from_controls = lambda *a, **k: (refreshes.append(1), real_refresh(*a, **k))[1]
    try:
        exists = bool(editor.winfo_exists())
        editor._schedule_refresh_plot()
        scheduled = editor.__dict__.get("_refresh_after_id") is not None
        settle(1.0)
        schedule = "ok"
    except Exception as exc:
        exists, scheduled, schedule = None, False, f"RAISED {type(exc).__name__}: {exc}"
    finally:
        del editor._refresh_plot_from_controls
    record("a scheduled plot refresh", schedule)

    # ---- C: the clipboard ------------------------------------------------------------------------------
    clipboard = QGuiApplication.clipboard()
    clipboard.setText("not rows")
    editor._select_table_indices([3, 4], focus_index=3)
    settle(0.3)
    names = [str(editor.rows[index].name) for index in editor._selected_copy_indices()]    # the whole element they are in
    editor.copy_selected_rows_to_clipboard()
    settle(0.3)
    copied_status = str(editor.status_var.get())
    on_qt_clipboard = str(clipboard.text())
    editor._surface_row_clipboard = []          # so Paste can only have them from the shell's clipboard
    pasted = [str(row.name) for row in editor._pasted_surface_rows()]
    clipboard.setText("")
    pasted_from_nothing = [str(row.name) for row in editor._pasted_surface_rows()]

    # ---- P: the plot auto-save -------------------------------------------------------------------------
    laid_out = bool(editor._plot_window_is_laid_out())
    if layout_analysis_display.AUTO_PLOT_PATH != picture:      # never write the user's own picture
        raise RuntimeError(f"the auto-save would write {layout_analysis_display.AUTO_PLOT_PATH}, not this guard's file")
    editor.auto_save_plot_var.set(True)
    editor._autosave_plot()
    settle(1.5)
    editor.auto_save_plot_var.set(False)
    saved = picture.stat().st_size if picture.exists() else 0
    settle(0.6)

    owned = inspector.__dict__.get("window")
    Path(out).write_text(json.dumps({"steps": steps}), encoding="utf-8")
    return {"made": dict(made), "root": editor.root is not None,
            "window": "no window" if owned is None else f"{type(owned).__name__}, {owned.state()}",
            "actors": len(inspector._actor_by_key), "available": bool(inspector.available),
            "exists": exists, "scheduled": scheduled, "refreshes": len(refreshes), "schedule": schedule,
            "copied": copied_status, "on the Qt clipboard": on_qt_clipboard[:60], "names": names, "pasted": pasted,
            "pasted from nothing": pasted_from_nothing, "rows on the Qt clipboard": len(on_qt_clipboard) > 200,
            "laid out": laid_out, "saved": saved, "steps": len(steps), "requested": os.environ.get("KRAKEN_QT_TK_FREE", ""),
            "model variables by the host": len(editor._model_variables_created_at_init)}


def compare(tk_path: str, free_path: str) -> dict:
    with_tk = json.loads(Path(tk_path).read_text(encoding="utf-8"))["steps"]
    without = json.loads(Path(free_path).read_text(encoding="utf-8"))["steps"]
    differ: dict = {}
    results, only_tk, only_free, compared = [], {"inspector": set(), "editor": set()}, {"inspector": set(), "editor": set()}, 0
    for (label, result_a, inspector_a, editor_a), (label_b, result_b, inspector_b, editor_b) in zip(with_tk, without):
        if label != label_b or result_a != "ok" or result_b != "ok":
            results.append((label, result_a, label_b, result_b))
        for which, a, b in (("inspector", inspector_a, inspector_b), ("editor", editor_a, editor_b)):
            plain_a, plain_b = a["plain"], b["plain"]
            for key in sorted(set(plain_a) | set(plain_b)):
                if key in plain_a and key in plain_b:
                    compared += 1
                    if plain_a[key] != plain_b[key] and not (which == "editor" and key in TIMED):
                        differ.setdefault(f"{which}.{key}", []).append(label)
                elif key in plain_a and key not in b["objects"]:
                    only_tk[which].add(key)
                elif key in plain_b and key not in a["objects"]:
                    only_free[which].add(key)
    return {"differ": differ, "results": results, "only_tk": {k: sorted(v) for k, v in only_tk.items()},
            "only_free": {k: sorted(v) for k, v in only_free.items()}, "steps": [len(with_tk), len(without)],
            "compared_per_step": compared // max(len(without), 1)}


def checks(tk_meta: dict, free_meta: dict, result: dict) -> list:
    from KrakenOS.UI.validate_editor_without_tk_root import ROOTLESS_ONLY_PLAIN, TK_ONLY_PLAIN
    from KrakenOS.UI.validate_inspector_without_tk_window import WINDOW_ONLY_PLAIN

    def claim_a():
        before = tk_meta["made"]
        return (free_meta["made"] == {} and free_meta["root"] is False and free_meta["window"] == "no window"
                and free_meta["requested"] == "all" and free_meta["available"] and free_meta["model variables by the host"] == 79
                and tk_meta["requested"] == "" and tk_meta["root"] is True and before.get("roots starting") == 1
                and before.get("widgets starting", 0) > 300 and before.get("widgets building the 3D scene") == 247
                and tk_meta["window"] == "Kraken3DInspectorWindow, withdrawn"
                and free_meta["actors"] == tk_meta["actors"] > 20,
                f"on request the whole Qt shell made Tk objects {free_meta['made'] or 'none'}: the editor has no root, the "
                f"inspector {free_meta['window']}, the host made all {free_meta['model variables by the host']} model variables "
                f"(as it always was: {before}); the 3D scene is up in both with {free_meta['actors']} actors")

    def claim_s():
        expected_tk = {"inspector": sorted(WINDOW_ONLY_PLAIN), "editor": sorted(TK_ONLY_PLAIN)}
        expected_free = {"inspector": [], "editor": sorted(ROOTLESS_ONLY_PLAIN)}
        return (not result["differ"] and not result["results"] and result["steps"][0] == result["steps"][1] >= 8
                and result["only_tk"] == expected_tk and result["only_free"] == expected_free
                and result["compared_per_step"] >= 450,
                f"{result['steps'][1]} steps, every one without an error in both ({result['results'] or 'none raised'}); about "
                f"{result['compared_per_step']} plain attributes of the editor and the inspector compared at each; they differ "
                f"in {sorted(result['differ']) or 'none'}; plain attributes only the shell with Tk holds: {result['only_tk']}; "
                f"only the one without: {result['only_free']}")

    def claim_e():
        return (free_meta["exists"] is True and free_meta["schedule"] == "ok" and free_meta["scheduled"]
                and free_meta["refreshes"] == 1 and tk_meta["exists"] is True and tk_meta["refreshes"] == 1,
                f"without a Tk root the editor says it exists ({free_meta['exists']}); a plot refresh it schedules "
                f"({free_meta['schedule']}) is on the shell's host ({free_meta['scheduled']}) and runs "
                f"{free_meta['refreshes']} time(s) -- with the hidden root: {tk_meta['refreshes']}")

    def claim_c():
        def right(meta: dict) -> bool:
            return (meta["rows on the Qt clipboard"] and meta["pasted"] == meta["names"] and len(meta["names"]) == 3
                    and meta["pasted from nothing"] == [] and meta["copied"] == "Copied 3 surface row(s) (Qt).")

        return (right(free_meta) and right(tk_meta),
                f"with no clipboard tool installed, an element's three rows copied in the Qt shell are on the Qt clipboard "
                f"({free_meta['copied']!r}), and Paste, the editor's own copy cleared, reads {free_meta['pasted']} from there "
                f"-- and nothing from an empty clipboard ({free_meta['pasted from nothing']}); with the hidden Tk application: "
                f"{tk_meta['copied']!r}, {tk_meta['pasted']}")

    def claim_p():
        from KrakenOS.UI.panels.main_window import MainWindowBuilder

        def window_of(width: int, height: int):
            editor = SimpleNamespace(root=object(), winfo_width=lambda: width, winfo_height=lambda: height)
            return SimpleNamespace(editor=editor)

        sizes = {size: MainWindowBuilder._plot_window_is_laid_out(window_of(*size))
                 for size in ((1199, 900), (1200, 699), (1200, 700), (1, 1), (1920, 1080))}
        no_window = MainWindowBuilder._plot_window_is_laid_out(SimpleNamespace(editor=SimpleNamespace(root=None)))
        return (free_meta["laid out"] is True and free_meta["saved"] > 5000 and tk_meta["laid out"] is False
                and tk_meta["saved"] == 0 and no_window is True
                and sizes == {(1199, 900): False, (1200, 699): False, (1200, 700): True, (1, 1): False, (1920, 1080): True},
                f"without a Tk window the auto-save does not wait ({free_meta['laid out']}) and wrote a picture of "
                f"{free_meta['saved']} bytes; with the hidden Tk window it waits as it always did ({tk_meta['laid out']}, "
                f"{tk_meta['saved']} bytes); the Tk window's test by size: {sizes}")

    return _claims((("A", claim_a), ("S", claim_s), ("E", claim_e), ("C", claim_c), ("P", claim_p)))


def _run(call: str, claim: str, tk_free: str) -> dict | list:
    driver = (
        "import json, os\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY')\n"
        "    raise SystemExit(0)\n"
        "import PySide6\n"
        "from KrakenOS.UI.validate_qt_shell_without_tk import session\n"
        # flushed, then exit WITHOUT interpreter teardown (a Tk/Qt/VTK teardown crash must not lose it)
        f"print({RESULT_MARK!r} + json.dumps({call}), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    env["PYTHONHASHSEED"] = "1"
    # ONE analysis worker, whatever memory is free: the count is capped by the machine's free
    # memory and the parallel trace agrees with the single one only to the last bits (the full
    # gate of 2026-10-10). The comparison is about Tk, not about the machine.
    env["KRAKEN_ANALYSIS_WORKER_MB"] = "1000000"
    env.pop("KRAKEN_QT_TK_FREE", None)
    if tk_free:
        env["KRAKEN_QT_TK_FREE"] = tk_free
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True, timeout=900,
                              env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return [[claim, False, f"{call} timed out"]]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return [["X", True, f"SKIP {call}: " + line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-8:]
    return [[claim, False, f"{call} exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    rows: list = []
    with tempfile.TemporaryDirectory() as folder:
        tk_path, free_path = str(Path(folder) / "with_tk.json"), str(Path(folder) / "without.json")
        metas = [_run(f"session({tk_path!r})", "S", ""), _run(f"session({free_path!r})", "A", "all")]
        if any(isinstance(meta, list) for meta in metas):
            for meta in metas:
                rows += meta if isinstance(meta, list) else []
        else:
            try:
                rows += checks(metas[0], metas[1], compare(tk_path, free_path))
            except Exception as exc:
                rows.append(["S", False, f"comparing the two sessions raised {type(exc).__name__}: {exc}"])
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
