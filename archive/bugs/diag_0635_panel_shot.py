"""bugs/0635: render the categorized left panel with a stub inspector (no VTK/scene)."""
from __future__ import annotations
import subprocess, tkinter as tk
from tkinter import ttk
from pathlib import Path
OUT = Path("bugs/_0635_categorized_panel.png")

def main():
    from KrakenOS.UI.panels.open3d_live_controls import Open3DLiveControlsPanel
    root = tk.Tk(); root.withdraw()
    class Stub:
        def __init__(self): self.live_mode_var = tk.BooleanVar()
        def __getattr__(self, n): return lambda *a, **k: None
    editor = Stub(); insp = Stub(); insp.editor = editor
    panel = Open3DLiveControlsPanel.__new__(Open3DLiveControlsPanel)
    panel.inspector = insp; panel.editor = editor
    # Replace the real section builders with labeled placeholders so we see structure only.
    for m in ["build_field_controls","build_trace_controls","build_quick_estimation_controls",
              "build_solve_controls","build_system_selection_controls"]:
        setattr(panel, m, lambda parent, _m=m: ttk.Label(
            parent, text="("+_m.replace("build_","").replace("_controls","").replace("_"," ")+" controls)",
            foreground="#aaaaaa").grid(row=0, column=0, sticky="w"))
    top = tk.Toplevel(root); top.geometry("300x780+20+10"); top.title("Live Controls")
    top.rowconfigure(1, weight=1); top.columnconfigure(0, weight=1)
    panel.build(top)
    top.update_idletasks()
    for _ in range(20): top.update()
    x,y,w,h = top.winfo_rootx(), top.winfo_rooty(), top.winfo_width(), top.winfo_height()
    subprocess.run(["import","-window","root","-crop",f"{w}x{h}+{x}+{y}","+repage",str(OUT)],check=True)
    print(f"saved {OUT} ({w}x{h})")
    root.destroy(); return 0
raise SystemExit(main())
