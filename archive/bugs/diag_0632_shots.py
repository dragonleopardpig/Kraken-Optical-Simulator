"""bugs/0632: screenshots — dialog self-fits the clipping case + compact left-panel form."""
from __future__ import annotations
import subprocess, tkinter as tk
from tkinter import ttk
from types import SimpleNamespace
from pathlib import Path
from KrakenOS.UI.services.system_selection import open_system_selection_dialog, build_system_selection_form

DLG = Path("bugs/_0633_dialog_perf_targets.png")
PANEL = Path("bugs/_0632_left_panel_section.png")


def _grab(win, out):
    win.deiconify(); win.lift()
    for _ in range(25):
        win.update()
    x, y, w, h = win.winfo_rootx(), win.winfo_rooty(), win.winfo_width(), win.winfo_height()
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["import", "-window", "root", "-crop", f"{w}x{h}+{x}+{y}", "+repage", str(out)], check=True)
    print(f"saved {out} ({w}x{h})")


def _fill(win, vals):
    def walk(w):
        o = [w]
        for c in w.winfo_children():
            o.extend(walk(c))
        return o
    for e, v in zip([w for w in walk(win) if w.winfo_class() == "TEntry"], vals):
        e.delete(0, "end"); e.insert(0, v)


def main() -> int:
    root = tk.Tk(); root.geometry("+30+30")
    editor = SimpleNamespace(winfo_toplevel=lambda: root,
                             _show_centered_dialog=lambda d: d.geometry("+40+40"),
                             _current_camera_record=lambda: {"resolution_px": [5120, 5120]})
    # Dialog — the exact clipping case from the flag: FOV 8, res 1, sensor 23.04, WD blank
    dlg = open_system_selection_dialog(editor)
    _fill(dlg, ["100", "100", "50", "200", "12.8", "12.8", "0.55"])
    dlg.after(150, lambda: dlg.event_generate("<Configure>"))
    _grab(dlg, DLG)

    root.destroy(); return 0
    # Compact left-panel section (rendered in a ~300px frame like the real panel)
    top = tk.Toplevel(root); top.geometry("300x520+380+30"); top.title("System Selection")
    lf = ttk.LabelFrame(top, text="System Selection", padding=8); lf.pack(fill="both", expand=True)
    lf.columnconfigure(0, weight=1)
    form = build_system_selection_form(lf, editor, compact=True)
    ttk.Button(lf, text="↺ From scene", command=form.set_prefill).grid(
        row=form.next_row, column=0, columnspan=2, sticky="ew", pady=(4, 0))
    _fill(top, ["8", "8", "1", "150", "23.04", "23.04"])
    _grab(top, PANEL)

    root.destroy()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
