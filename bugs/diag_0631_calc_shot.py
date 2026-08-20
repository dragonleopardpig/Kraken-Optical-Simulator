"""bugs/0631: screenshot the System Selection Calculator with a worked example filled in."""
from __future__ import annotations
import subprocess, tkinter as tk
from types import SimpleNamespace
from pathlib import Path
from KrakenOS.UI.services.system_selection import open_system_selection_dialog

OUT = Path("bugs/_0631_system_selection_calculator.png")


def main() -> int:
    root = tk.Tk(); root.geometry("+40+40")
    editor = SimpleNamespace(winfo_toplevel=lambda: root,
                             _show_centered_dialog=lambda d: d.geometry("+60+60"))
    dlg = open_system_selection_dialog(editor, fov_wh=(100.0, 100.0),
                                       sensor_wh=(12.8, 12.8), camera_pixels=(5120, 5120))

    def walk(w):
        out = [w]
        for c in w.winfo_children(): out.extend(walk(c))
        return out
    entries = [w for w in walk(dlg) if w.winfo_class() == "TEntry"]
    for e, v in zip(entries, ["100", "100", "50", "200", "12.8", "12.8"]):
        e.delete(0, "end"); e.insert(0, v)
    dlg.deiconify(); dlg.lift()
    for _ in range(20):
        dlg.update()
    x, y, w, h = dlg.winfo_rootx(), dlg.winfo_rooty(), dlg.winfo_width(), dlg.winfo_height()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["import", "-window", "root", "-crop", f"{w}x{h}+{x}+{y}", "+repage", str(OUT)], check=True)
    print(f"saved {OUT} ({w}x{h})")
    root.destroy()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
