"""Record what the surface table's selection does, on a real Tk editor: after each of a fixed script of selects,
clicks, keys, verbs, undo/redo and path views -- the selected items, the focus item, the active cell, the anchor,
what each selection query answers, and a digest of the rows. Run at the commit before and after bugs/0990."""
import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace


def canon(value):
    if isinstance(value, dict):
        return {"__dict__": sorted(([repr(key), canon(item)] for key, item in value.items()), key=lambda pair: pair[0])}
    if isinstance(value, (list, tuple)):
        return [canon(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


def digest(value) -> str:
    return hashlib.sha1(json.dumps(canon(value)).encode()).hexdigest()[:16]


def main(out: str, limit: str = "30") -> None:
    import tkinter.messagebox as tk_messagebox

    from KrakenOS.UI.layout_editor import FIELDS, KrakenLayoutEditor

    # a real Tk message box would wait for a user: record what it would have said, and answer it
    said: list = []
    for name, answer in (("showinfo", "ok"), ("showwarning", "ok"), ("showerror", "ok"), ("askyesno", True),
                         ("askokcancel", True), ("askyesnocancel", True), ("askretrycancel", False), ("askquestion", "yes")):
        setattr(tk_messagebox, name,
                (lambda name, answer: lambda *args, **options: (said.append([name, [str(a)[:90] for a in args[:2]]]), answer)[1])(name, answer))

    files = [Path(p) for p in subprocess.run(["git", "ls-files", "KrakenOS/common_optical_layouts"],
                                             capture_output=True, text=True).stdout.split() if p.endswith(".py")]
    files = sorted(p for p in files if not p.name.startswith("_"))
    editor = KrakenLayoutEditor()
    editor.geometry("1700x950+0+0")
    editor.refresh_plot = lambda *a, **k: None
    table = editor.table

    def settle(rounds: int = 5) -> None:
        for _ in range(rounds):
            editor.update()
            time.sleep(0.01)

    def state() -> dict:
        def ask(call):
            try:
                return call()
            except Exception as exc:
                return f"RAISED {type(exc).__name__}: {exc}"
        return {"selection": list(table.selection()), "focus": str(table.focus()), "active": editor._active_cell,
                "anchor": editor._selection_anchor_row, "status": str(editor.status_var.get())[:90],
                "current": ask(editor._current_selected_row_index), "indices": ask(editor._selected_table_indices),
                "has": ask(editor._table_has_selection), "surface_row": ask(editor._selected_surface_row_index),
                "source": ask(editor._current_selected_scene_source_id),
                "borders": len(editor.__dict__.get("_selection_border_overlays", [])),
                "native": list(editor._native_table_selection()) if editor._native_table_selection else None,
                "rows": digest([asdict(row) for row in editor.rows]), "items": len(table.get_children())}

    def step(label, call):
        try:
            result = call()
        except Exception as exc:
            result = f"RAISED {type(exc).__name__}: {exc}"
        settle()
        messages, said[:] = list(said), []
        return [label, result if isinstance(result, (str, type(None), bool, int)) else repr(result)[:80], state(), messages]

    def click(row_position: int, column: str, shift: bool = False, control: bool = False):
        items = table.get_children()
        if not items:
            return "no rows"
        item = items[min(row_position, len(items) - 1)]
        column_id = column if column.startswith("#") else f"#{FIELDS.index(column) + 1}"
        bbox = table.bbox(item, column_id)
        if not bbox:
            return "not visible"
        x, y, w, h = bbox
        event = SimpleNamespace(x=x + w // 2, y=y + h // 2, x_root=0, y_root=0, state=(0x0001 if shift else 0) | (0x0004 if control else 0))
        return editor._on_table_click(event)

    def key(name: str):
        return editor._move_active_cell(SimpleNamespace(keysym=name))

    record = {}
    started = time.time()
    done = 0
    for path in files:
        if done >= int(limit):
            break
        try:
            editor.layout_files[path.stem] = path
            editor.load_layout_by_name(path.stem, refresh=False)
        except Exception as exc:
            record[path.as_posix()] = {"load": f"RAISED {type(exc).__name__}: {exc}"}
            continue
        settle()
        if len(editor.rows) < 6:
            continue
        done += 1
        steps = [["loaded", len(editor.rows), state()]]
        steps.append(step("select [1,2] focus 2", lambda: editor._select_table_indices([1, 2], focus_index=2)))
        steps.append(step("select row 3", lambda: editor._select_table_row(3)))
        steps.append(step("click 2 thickness", lambda: click(2, "thickness")))
        steps.append(step("ctrl-click 4", lambda: click(4, "thickness", control=True)))
        steps.append(step("shift-click 1", lambda: click(1, "thickness", shift=True)))
        steps.append(step("click 3 label", lambda: click(3, "#1")))
        steps.append(step("ctrl-click 2 label", lambda: click(2, "#1", control=True)))
        steps.append(step("ctrl-click 2 label again", lambda: click(2, "#1", control=True)))
        steps.append(step("shift-ctrl-click 5 rc", lambda: click(5, "rc", shift=True, control=True)))
        for name in ("Down", "Down", "Right", "Up", "Left", "Left"):
            steps.append(step(f"key {name}", lambda name=name: key(name)))
        items = table.get_children()
        steps.append(step("marker click", lambda: editor._on_optimization_marker_click(None, items[2], "thickness")))
        sources = [position for position, item in enumerate(items) if str(item).startswith("scene_source_")]
        if sources:
            steps.append(step("click a source row", lambda: click(sources[0], "name")))
            steps.append(step("ctrl-click a source label", lambda: click(sources[0], "#1", control=True)))
        steps.append(step("clear", editor._clear_table_selection))
        steps.append(step("select [2]", lambda: editor._select_table_indices([2])))
        steps.append(step("commit", lambda: editor.commit_cell(2, "thickness", "4.5", quiet=True)))
        steps.append(step("undo", editor.undo))
        steps.append(step("redo", editor.redo))
        steps.append(step("select [2,3]", lambda: editor._select_table_indices([2, 3], focus_index=3)))
        steps.append(step("duplicate", editor.duplicate_selected))
        steps.append(step("move down", editor.move_down))
        steps.append(step("move up", editor.move_up))
        steps.append(step("group", editor.group_selected_as_element))
        steps.append(step("ungroup", editor.ungroup_selected_elements))
        steps.append(step("delete", editor.delete_selected))
        steps.append(step("undo delete", editor.undo))
        steps.append(step("sync", editor._sync_table))
        steps.append(step("add surface", editor.add_surface))
        options = list(editor.arm_view_options())
        for option in options[1:3]:
            def view(option=option):
                editor.arm_view_var.set(option)
                editor.set_arm_view()
            steps.append(step(f"view {option}", view))
            steps.append(step("view click 1", lambda: click(1, "thickness")))
        if len(options) > 1:
            def back():
                editor.arm_view_var.set(options[0])
                editor.set_arm_view()
            steps.append(step("view all", back))
        steps.append(step("click empty", lambda: editor._on_table_click(SimpleNamespace(x=30, y=int(table.winfo_height()) - 3, x_root=0, y_root=0, state=0))))
        record[path.as_posix()] = steps
    Path(out).write_text(json.dumps(canon(record), indent=1), encoding="utf-8")
    print(f"written {out}: {done} layouts, {sum(len(s) for s in record.values() if isinstance(s, list))} steps in "
          f"{time.time() - started:.0f} s", flush=True)
    os._exit(0)


if __name__ == "__main__":
    main(*sys.argv[1:])
