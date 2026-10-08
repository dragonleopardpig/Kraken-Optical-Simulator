"""Record, for every tracked layout: the table's cell texts, the rows the parser makes of them, and what a
fixed script of cell edits does. Run at the commit before and after bugs/0989; the two records must be equal."""
import hashlib
import json
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path

EDITS = (("thickness", "7.25"), ("rc", "-33.5"), ("name", "Edited 007"), ("tilt_x", "1, 2, 3"), ("desp_y", "0.5"),
         ("diameter", "12.5"), ("glass", "F2"), ("k", "abc"), ("tilt_x", "4"), ("in_diameter", "1e-1"), ("axis_move", "NA"))


def canon(value):
    """A JSON-safe, order-free form: a dict becomes its items sorted by the repr of the key."""
    if isinstance(value, dict):
        return {"__dict__": sorted(([repr(key), canon(item)] for key, item in value.items()), key=lambda pair: pair[0])}
    if isinstance(value, (list, tuple)):
        return [canon(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


def digest(value) -> str:
    return hashlib.sha1(json.dumps(canon(value)).encode()).hexdigest()[:16]


def main(out: str, only: str = "") -> None:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.uihost import ScriptedUiHost

    files = [Path(p) for p in subprocess.run(["git", "ls-files", "KrakenOS/common_optical_layouts", "test_fixtures"],
                                             capture_output=True, text=True).stdout.split() if p.endswith(".py")]
    files = sorted(p for p in files if p.name != "__init__.py" and (not only or only in p.name))
    host = ScriptedUiHost(answers={})
    editor = KrakenLayoutEditor(headless=True, ui=host)
    editor.refresh_plot = lambda *a, **k: None

    def rows_now():
        return [asdict(row) for row in editor.rows]

    def cells_now():
        table = editor.table
        return [[item, [str(v) for v in table.item(item, "values")], [str(t) for t in table.item(item, "tags")]]
                for item in table.get_children()]

    def step(label, call):
        try:
            result = call()
        except Exception as exc:
            result = f"RAISED {type(exc).__name__}: {exc}"
        return [label, result if isinstance(result, (str, type(None), bool, int)) else repr(result), digest(rows_now()), digest(cells_now())]

    record, full = {}, {}
    started = time.time()
    for number, path in enumerate(files):
        entry = {}
        try:
            editor.layout_files[path.stem] = path
            editor.load_layout_by_name(path.stem, refresh=False)
        except Exception as exc:
            record[path.as_posix()] = {"load": f"RAISED {type(exc).__name__}: {exc}"}
            continue
        entry["loaded"] = [len(editor.rows), digest(rows_now()), digest(cells_now())]
        steps = [step("read", editor._read_rows_from_table), step("read again", editor._read_rows_from_table),
                 step("sync", editor._sync_table), step("image value", editor._sync_image_row_table_value)]
        targets = list(range(1, min(len(editor.rows) - 1, 4)))
        for index in targets:
            for field, text in EDITS:
                steps.append(step(f"row {index} {field}={text}", lambda i=index, f=field, t=text: editor.commit_cell(i, f, t, quiet=True)))
        if targets:
            steps.append(step("surface=Mirror", lambda: editor.commit_cell(targets[-1], "surface", "Mirror")))
            steps.append(step("mirror tilt", lambda: editor.commit_cell(targets[-1], "tilt_x", "44, 45, 46", quiet=True)))
        try:
            options = list(editor.arm_view_options())
        except Exception as exc:
            options = []
            steps.append(["arm options", f"RAISED {type(exc).__name__}: {exc}", "", ""])
        for option in options[1:6]:
            def view(option=option):
                editor.arm_view_var.set(option)
                editor.set_arm_view()
                return [len(editor.table.get_children()), bool(editor.__dict__.get("_table_path_local_mode_active"))]
            steps.append(step(f"view {option}", view))
            shown = [editor._table_item_row_index(item) for item in editor.table.get_children()]
            shown = [index for index in shown if index is not None and 0 < index < len(editor.rows) - 1]
            hidden = [index for index in range(1, len(editor.rows) - 1) if index not in shown]
            if shown:
                steps.append(step("view edit", lambda i=shown[0]: editor.commit_cell(i, "thickness", "3.5", quiet=True)))
                steps.append(step("view pose", lambda i=shown[-1]: editor.commit_cell(i, "desp_x", "0.25", quiet=True)))
            if hidden:
                steps.append(step("hidden edit", lambda i=hidden[0]: editor.commit_cell(i, "thickness", "9", quiet=True)))
        if len(options) > 1:
            def back():
                editor.arm_view_var.set(options[0])
                editor.set_arm_view()
                return len(editor.table.get_children())
            steps.append(step("view all", back))
        entry["steps"] = steps
        entry["messages"] = len(host.calls)
        record[path.as_posix()] = entry
        if number < 2:
            full[path.as_posix()] = {"rows": rows_now(), "cells": cells_now()}
        if number % 20 == 0:
            print(f"{number + 1}/{len(files)} {path.name} ({time.time() - started:.0f} s)", flush=True)
    Path(out).write_text(json.dumps({"record": record, "full": canon(full)}, indent=1, sort_keys=True), encoding="utf-8")
    print(f"written {out}: {len(record)} layouts, {sum(len(e.get('steps', [])) for e in record.values())} steps in "
          f"{time.time() - started:.0f} s", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
