"""Guard for bugs/0955: a table-cell solve shows its result for review -- in BOTH shells.

Three solves on the surface table's right-click menu (Paraxial Solve This Thickness, Folded
Paraxial Mirror Solve, Best Image Solve) compute a result and ask "apply this?" before they write.
  * In the Tk app the window failed with `bad window path name` from 2026-05-24 (d4c6642d): it was
    handed an object that is not a widget as its Tk parent, so every one of these solves ended in
    an error box and never applied.
  * In the Qt shell the same code ran, with the same error.
What the window says is now one description (`solve_reviews`), shown by a Tk window whose parent
is the editor and by a modal Qt dialog.

  P  pure: the three descriptions -- title, the line saying what was solved, the rows for each
     target, the rule -- from sample results
  T  in the Tk app each of the three opens its window with NO error box; Cancel leaves the row
     alone and says so; Apply writes the solved value to the row
  Q  in the Qt shell each opens a modal Qt dialog -- the two that are on the table's right-click
     menu are run FROM that menu; the folded mirror solve has no menu entry in either shell and is
     run by its command -- Cancel leaves the row alone; Apply writes the solved value; no Tk window
     and no error box
  E  both shells show the same title, intro, row labels and rule for each solve -- and the same
     numbers for the two paraxial ones
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "SOLVEREVIEW_RESULT "
SKIP_MARK = "SOLVEREVIEW_SKIP "
LENS_SCENE = Path("test_fixtures/machine_vision_Pyrite90_0.3X.py")
MIRROR_SCENE = Path("KrakenOS/common_optical_layouts/coating_polarization_example.py")
#: solve -> (scene, row, the editor command, the menu entry, the row holding the solved value,
#: what the status line says after Cancel)
SOLVES = {
    "thickness": (LENS_SCENE, 2, "solve_current_paraxial_variable_thickness", "Paraxial Solve This Thickness",
                  "Solved thickness [mm]", "Paraxial solve cancelled"),
    "best_image": (LENS_SCENE, 5, "solve_current_best_focus_distance", "Best Image Solve",
                   "Solved value [mm]", "Best image solve cancelled"),
    # no menu entry calls this command (found by this guard; not changed): it is run directly
    "folded_mirror": (MIRROR_SCENE, 3, "solve_current_folded_mirror_distance", None,
                      "Solved mirror thickness [mm]", "Folded mirror solve cancelled"),
}
TITLES = {"thickness": "Paraxial Solve", "best_image": "Best Image Solve", "folded_mirror": "Folded Mirror Solve"}


# ---- P -----------------------------------------------------------------------------------------
def pure_checks() -> list:
    from KrakenOS.UI.solve_reviews import best_focus_review, folded_mirror_solve_review, paraxial_solve_review

    def fmt(value):
        return value if isinstance(value, str) else f"{float(value):.6g}"

    base = {"effl": 90.8, "ppa": 1.5, "ppp": -2.5, "object_mode_before": "Finite",
            "object_distance_before": 300.0, "image_distance_before": 120.0, "object_principal": 301.5,
            "image_principal": 130.0, "solved_distance": 127.5, "selected_row": 5}
    image = paraxial_solve_review({**base, "target": "image"}, fmt)
    obj = paraxial_solve_review({**base, "target": "object", "object_mode_after": "Finite"}, fmt)
    thick = paraxial_solve_review({**base, "target": "thickness", "target_label": "air gap", "start_value": 10.0,
                                   "predicted_image_gap": 120.0, "residual": 1e-9, "sample_count": 21}, fmt)
    folded = folded_mirror_solve_review({**base, "straight_image_gap": 150.0, "upstream_gap": 30.0}, fmt)
    best = best_focus_review({"selected_row": 5, "target_label": "image gap", "start_value": 120.0, "lower": 100.0,
                              "upper": 140.0, "solved_distance": 121.25, "best_rms": 0.0012, "sample_count": 33}, fmt)
    best_path = best_focus_review({"selected_row": 5, "target_label": "image gap", "start_value": 120.0,
                                   "lower": 100.0, "upper": 140.0, "solved_distance": 121.25, "best_rms": 0.0012,
                                   "sample_count": 33, "filter_text": "Path 2", "metric_label": "Output vergence"}, fmt)
    ok = (
        (image.title, obj.title, thick.title, folded.title, best.title)
        == ("Paraxial Solve", "Paraxial Solve", "Paraxial Solve", "Folded Mirror Solve", "Best Image Solve")
        and len({image.intro, obj.intro, thick.intro}) == 3
        and image.rows[-2:] == (("Solved image gap [mm]", "127.5"), ("Apply to row", "5"))
        and obj.rows[-2:] == (("Solved object gap [mm]", "127.5"), ("Object mode after", "Finite"))
        and [label for label, _value in thick.rows[-6:]] == ["Solve row", "Start thickness [mm]", "Solved thickness [mm]",
                                                             "Predicted image gap [mm]", "Residual [mm]", "Samples"]
        and thick.rows[-6][1] == "5 (air gap)" and len(thick.rows) == 14 and len(image.rows) == 10
        and "principal planes" in image.rule and "holds the other gaps fixed" in thick.rule
        and len(folded.rows) == 10 and folded.rows[-2] == ("Solved mirror thickness [mm]", "127.5")
        and "straight-through image gap - gap before mirror" in folded.rule
        and len(best.rows) == 9 and len(best_path.rows) == 10 and best_path.rows[7] == ("Target path", "Path 2")
        and dict(best.rows)["Metric"] == "Image-plane RMS" and dict(best_path.rows)["Metric"] == "Output vergence"
        and (best.apply_label, best.cancel_label) == ("Apply", "Cancel")
    )
    return [["P", ok,
             f"rows: image {len(image.rows)}, object {len(obj.rows)}, thickness {len(thick.rows)}, folded "
             f"{len(folded.rows)}, best image {len(best.rows)} (+1 with a target path: {len(best_path.rows)}); three "
             f"different intros for the three paraxial targets: {len({image.intro, obj.intro, thick.intro}) == 3}"]]


def _solved_value(rows, label: str) -> float:
    return float(dict(rows)[label])


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= 1e-5 * max(1.0, abs(b))           # the window shows six significant figures


# ---- T: the Tk app -------------------------------------------------------------------------------
def tk_runtime_checks() -> dict:
    import tkinter as tk
    import tkinter.messagebox as messagebox
    from tkinter import ttk

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    errors: list = []
    for name in ("showerror", "showwarning"):
        setattr(messagebox, name, lambda *a, **k: errors.append(str(a[1] if len(a) > 1 else k.get("message"))[:120]))

    def widgets(root, kind):
        found = []
        for child in root.winfo_children():
            if isinstance(child, kind):
                found.append(child)
            found += widgets(child, kind)
        return found

    answer = {"press": "Cancel"}
    shown: list = []

    def scripted_wait(self, window=None):
        target = window or self
        texts = [str(label.cget("text")) for label in widgets(target, ttk.Label)]
        shown.append({"title": str(target.title()), "intro": texts[0], "rule": texts[-1],
                      "rows": [[texts[i], texts[i + 1]] for i in range(1, len(texts) - 1, 2)],
                      "buttons": [str(b.cget("text")) for b in widgets(target, ttk.Button)]})
        next(b for b in widgets(target, ttk.Button) if str(b.cget("text")) == answer["press"]).invoke()

    tk.Misc.wait_window = scripted_wait
    editor = KrakenLayoutEditor()
    facts: dict = {}
    notes: dict = {}
    for key, (scene, row, command, _entry, solved_label, cancelled) in SOLVES.items():
        editor.layout_files[scene.stem] = scene
        editor.load_layout_by_name(scene.stem)
        for _ in range(3):
            editor.update()

        def run(press: str):
            del shown[:]
            answer["press"] = press
            editor.current_menu_row_id = editor._table_item_for_row_index(row)
            editor.current_menu_field = "thickness"
            getattr(editor, command)()
            return (dict(shown[-1]) if shown else None), str(editor.status_var.get())

        before = float(editor.rows[row].thickness)
        review, status = run("Cancel")
        after_cancel = float(editor.rows[row].thickness)
        review_apply, _status = run("Apply")
        after_apply = float(editor.rows[row].thickness)
        solved = _solved_value(review_apply["rows"], solved_label) if review_apply else float("nan")
        facts[key] = review
        notes[key] = {"window": review["title"] if review else None, "status_after_cancel": status,
                      "before": before, "after_cancel": after_cancel, "solved": solved, "after_apply": after_apply}
    bad = sorted(key for key, note in notes.items()
                 if note["window"] != TITLES[key] or note["status_after_cancel"] != SOLVES[key][5]
                 or note["after_cancel"] != note["before"] or not _close(note["after_apply"], note["solved"]))
    return {"rows": [["T", not bad and not errors and len(notes) == 3,
                      f"Tk windows {[note['window'] for note in notes.values()]}; error boxes {errors}; per solve "
                      f"(before, after Cancel, solved, after Apply): "
                      f"{ {key: (note['before'], note['after_cancel'], note['solved'], note['after_apply']) for key, note in notes.items()} }; "
                      f"wrong {bad}"]],
            "facts": facts}


# ---- Q: the Qt shell -------------------------------------------------------------------------------
def qt_runtime_checks() -> dict:
    import time
    import tkinter as tk

    from PySide6.QtCore import QTimer

    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.uihost import host_of

    app, window = build(["guard"])
    window.show()
    app.processEvents()
    window.build_viewport()

    def settle(seconds: float = 0.3) -> None:
        end = time.time() + seconds
        while time.time() < end:
            app.processEvents()
            time.sleep(0.02)

    editor = window.editor
    errors: list = []
    host = host_of(window)
    for name in ("showerror", "showwarning"):
        setattr(host, name, lambda *a, **k: errors.append(str(a[1] if len(a) > 1 else k.get("message"))[:120]))
    tk_windows: list = []
    real_init = tk.Toplevel.__init__

    def counting_init(self, *args, **kwargs):
        real_init(self, *args, **kwargs)
        tk_windows.append(self)

    def no_wait(self, window=None):
        # a Tk window waited on under Qt would stop the shell for good: count it and move on
        tk_windows.append("waited")
        try:
            (window or self).destroy()
        except Exception:
            pass

    tk.Toplevel.__init__ = counting_init
    tk.Misc.wait_window = no_wait
    facts: dict = {}
    notes: dict = {}
    on_menu: dict = {}
    for key, (scene, row, command, entry_label, solved_label, cancelled) in SOLVES.items():
        window.load_layout_path(scene)
        settle()

        def run(press: str):
            seen: dict = {}
            tries = {"left": 2400}                  # a traced solve computes first, pumping events

            def answer():
                dialog = window.last_solve_review_dialog
                if dialog is None or not dialog.isVisible():
                    tries["left"] -= 1
                    if tries["left"] > 0:
                        QTimer.singleShot(50, answer)       # not shown yet: ask again
                    return
                seen.update({"title": dialog.windowTitle(), "intro": dialog.intro.text(), "rule": dialog.rule.text(),
                             "rows": [list(pair) for pair in dialog.shown_rows()], "modal": dialog.isModal(),
                             "buttons": [dialog.apply_button.text(), dialog.cancel_button.text()]})
                (dialog.apply_button if press == "Apply" else dialog.cancel_button).click()

            window.last_solve_review_dialog = None
            window.select_rows([row], row)
            model = editor.table_cell_menu(row, "thickness")           # also makes this the current cell
            solves = next(e.submenu for e in model.entries if e.kind == "cascade" and e.label == "Optimization / Solves")
            entry = next((e for e in solves.entries if e.kind == "command" and e.label == entry_label), None)
            on_menu[key] = entry is not None and bool(entry.enabled)
            if entry_label is not None and not on_menu[key]:
                return None, f"menu entry {entry_label!r} missing or disabled"
            QTimer.singleShot(0, answer)
            if entry is not None:
                solves.run(entry)
            else:
                getattr(editor, command)()
            tries["left"] = 0
            settle(0.2)
            return (seen or None), str(editor.status_var.get())

        before = float(editor.rows[row].thickness)
        review, status = run("Cancel")
        after_cancel = float(editor.rows[row].thickness)
        review_apply, _status = run("Apply")
        after_apply = float(editor.rows[row].thickness)
        solved = _solved_value(review_apply["rows"], solved_label) if review_apply else float("nan")
        facts[key] = review
        notes[key] = {"window": review["title"] if review else status, "modal": review.get("modal") if review else None,
                      "status_after_cancel": status, "before": before, "after_cancel": after_cancel,
                      "solved": solved, "after_apply": after_apply}
    bad = sorted(key for key, note in notes.items()
                 if note["window"] != TITLES[key] or note["modal"] is not True
                 or note["status_after_cancel"] != SOLVES[key][5] or note["after_cancel"] != note["before"]
                 or not _close(note["after_apply"], note["solved"]))
    return {"rows": [["Q", not bad and not errors and not tk_windows and len(notes) == 3
                      and on_menu == {"thickness": True, "best_image": True, "folded_mirror": False},
                      f"run from the right-click menu {on_menu}; Qt dialogs "
                      f"{[note['window'] for note in notes.values()]}, modal "
                      f"{[note['modal'] for note in notes.values()]}; error boxes {errors}; Tk windows "
                      f"{len(tk_windows)}; per solve (before, after Cancel, solved, after Apply): "
                      f"{ {key: (note['before'], note['after_cancel'], note['solved'], note['after_apply']) for key, note in notes.items()} }; "
                      f"wrong {bad}"]],
            "facts": facts}


def _run(call: str) -> dict:
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
        "from KrakenOS.UI.validate_solve_review_windows import qt_runtime_checks, tk_runtime_checks\n"
        # flushed, then exit WITHOUT interpreter teardown (a VTK/Qt teardown crash must not lose it)
        f"print({RESULT_MARK!r} + json.dumps({call}), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True, timeout=1500,
                              env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return {"rows": [["X", False, f"{call} timed out"]], "facts": {}}
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return {"rows": [["X", True, f"SKIP {call}: " + line[len(SKIP_MARK):]]], "facts": {}}
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-6:]
    return {"rows": [["X", False, f"{call} exit {proc.returncode}; " + " | ".join(tail)]], "facts": {}}


def parity(tk_facts: dict, qt_facts: dict) -> list:
    """E: the two shells say the same thing."""
    differ = []
    for key in SOLVES:
        a, b = tk_facts.get(key) or {}, qt_facts.get(key) or {}
        for name in ("title", "intro", "rule", "buttons"):
            if a.get(name) != b.get(name):
                differ.append(f"{key}.{name}: Tk {str(a.get(name))[:60]!r} vs Qt {str(b.get(name))[:60]!r}")
        if [label for label, _value in a.get("rows", [])] != [label for label, _value in b.get("rows", [])]:
            differ.append(f"{key}.row labels")
        # the paraxial solves are closed-form: the numbers must match too. The traced best-image
        # solve is compared by its labels (it is a numerical search)
        if key != "best_image" and a.get("rows") != b.get("rows"):
            differ.append(f"{key}.values: Tk {a.get('rows')} vs Qt {b.get('rows')}")
    counts = {key: len((tk_facts.get(key) or {}).get("rows", [])) for key in SOLVES}
    return [["E", len(tk_facts) == 3 and len(qt_facts) == 3 and not differ,
             f"rows shown per solve {counts}; differences between the Tk window and the Qt dialog: {differ}"]]


def run_checks() -> tuple[bool, list[str]]:
    rows = pure_checks()
    missing = [str(scene) for scene in (LENS_SCENE, MIRROR_SCENE) if not scene.exists()]
    if missing:
        rows.append(["X", True, f"SKIP = {missing} absent"])
    else:
        tk_side = _run("tk_runtime_checks()")
        qt_side = _run("qt_runtime_checks()")
        rows += list(tk_side["rows"]) + list(qt_side["rows"])
        if tk_side["facts"] and qt_side["facts"]:
            rows += parity(tk_side["facts"], qt_side["facts"])
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
