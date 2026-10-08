"""Record what the open 3D inspector IS as a Tk thing: its window, every widget under it, their bindings -- and a
screenshot. Run at the commit before and after bugs/0992 (the inspector owns its window instead of being one)."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def main(out: str) -> None:
    import tkinter as tk
    import tkinter.messagebox as tk_messagebox

    for name in ("showinfo", "showwarning", "showerror"):
        setattr(tk_messagebox, name, lambda *a, **k: "ok")
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    LAYOUT = Path("KrakenOS/common_optical_layouts/beam_splitter_two_arm_doublets.py")
    editor = KrakenLayoutEditor()
    editor.geometry("1500x900+0+0")
    editor.layout_files[LAYOUT.stem] = LAYOUT
    editor.load_layout_by_name(LAYOUT.stem, refresh=False)

    def settle(seconds: float = 1.0) -> None:
        end = time.time() + seconds
        while time.time() < end:
            editor.update()
            time.sleep(0.02)

    settle(0.5)
    editor.open_3d_view()
    settle(4.0)
    insp = editor._three_d_inspector
    insp.geometry("1100x780+200+60")
    settle(2.0)

    def tree(widget) -> list:
        rows = []
        for child in widget.winfo_children():
            entry = {"path": str(child), "class": child.winfo_class(), "manager": child.winfo_manager(),
                     "binds": sorted(child.bind()), "mapped": int(child.winfo_ismapped())}
            if child.winfo_class() == "Menu":
                last = child.index("end")
                entry["entries"] = 0 if last is None else int(last) + 1
            rows.append(entry)
            rows += tree(child)
        return rows

    widgets = tree(insp)
    record = {
        "path": str(insp), "class": insp.winfo_class(), "title": insp.title(), "size": insp.geometry().split("+")[0],
        "minsize": list(insp.minsize()), "state": insp.state(), "exists": int(insp.winfo_exists()),
        "master_is_editor": insp.master is editor, "binds": sorted(insp.bind()),
        "delete_protocol": bool(insp.protocol("WM_DELETE_WINDOW")), "toplevel_of_child": str(insp.winfo_children()[0].winfo_toplevel()),
        "root_children": sorted((str(w), w.winfo_class()) for w in editor.root.winfo_children()),
        "widgets": widgets, "widget_count": len(widgets), "available": bool(insp.available),
        "child_master_is_inspector": insp.winfo_children()[0].master is insp,
        "ui_host": type(insp.ui).__name__, "bases": [c.__name__ for c in type(insp).__mro__[:4]],
    }
    fired = []
    insp.after(1, lambda: fired.append("ran"))
    settle(0.3)
    record["after_through_inspector"] = fired
    subprocess.run(["import", "-display", os.environ["DISPLAY"], "-window", "root", out + ".png"], check=False)
    insp._on_close()
    settle(0.5)
    try:
        gone = not insp.winfo_exists()
    except tk.TclError:
        gone = True
    record["closed"] = {"editor_forgot_it": editor._three_d_inspector is None, "window_gone": bool(gone),
                        "root_children_after": sorted((str(w), w.winfo_class()) for w in editor.root.winfo_children())}
    Path(out + ".json").write_text(json.dumps(record, indent=1, sort_keys=True), encoding="utf-8")
    print("written", out, "| widgets", len(widgets), "| path", record["path"], "| bases", record["bases"], flush=True)
    os._exit(0)


if __name__ == "__main__":
    main(sys.argv[1])
