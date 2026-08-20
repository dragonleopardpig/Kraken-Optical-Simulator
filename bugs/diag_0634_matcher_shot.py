from __future__ import annotations
import subprocess, tkinter as tk
from types import SimpleNamespace
from pathlib import Path
from KrakenOS.UI.services.system_matcher import open_catalog_matcher_dialog
OUT = Path("bugs/_0634_matcher.png")
def main():
    root = tk.Tk(); root.geometry("+20+20")
    editor = SimpleNamespace(winfo_toplevel=lambda: root,
        _show_centered_dialog=lambda d: d.geometry("+30+30"),
        _current_camera_record=lambda: {"resolution_px":[5120,5120]})
    dlg = open_catalog_matcher_dialog(editor)
    def walk(w):
        o=[w]
        for c in w.winfo_children(): o.extend(walk(c))
        return o
    ents=[w for w in walk(dlg) if w.winfo_class()=="TEntry"]
    for e,v in zip(ents, ["55","55","12","150","0.55"]):
        e.delete(0,"end"); e.insert(0,v)
    btn=[w for w in walk(dlg) if w.winfo_class()=="TButton" and str(w.cget("text"))=="Match"][0]
    btn.invoke()
    dlg.deiconify(); dlg.lift()
    for _ in range(30): dlg.update()
    x,y,w,h=dlg.winfo_rootx(),dlg.winfo_rooty(),dlg.winfo_width(),dlg.winfo_height()
    subprocess.run(["import","-window","root","-crop",f"{w}x{h}+{x}+{y}","+repage",str(OUT)],check=True)
    print(f"saved {OUT} ({w}x{h})")
    # print pass count from status
    lbls=[w for w in walk(dlg) if w.winfo_class()=="TLabel"]
    for l in lbls:
        t=str(l.cget("text"))
        if "combinations match" in t: print("STATUS:", t)
    root.destroy()
main()
