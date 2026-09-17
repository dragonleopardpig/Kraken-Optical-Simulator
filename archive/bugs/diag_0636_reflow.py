from __future__ import annotations
import subprocess, tkinter as tk
from types import SimpleNamespace
from pathlib import Path
from KrakenOS.UI.services.system_selection import open_system_selection_dialog
def grab(win,out):
    win.deiconify(); win.lift()
    for _ in range(20): win.update()
    x,y,w,h=win.winfo_rootx(),win.winfo_rooty(),win.winfo_width(),win.winfo_height()
    subprocess.run(["import","-window","root","-crop",f"{w}x{h}+{x}+{y}","+repage",str(out)],check=True)
    print(f"saved {out} ({w}x{h})")
def fill(win,vals):
    def walk(w):
        o=[w]
        for c in w.winfo_children(): o.extend(walk(c))
        return o
    for e,v in zip([w for w in walk(win) if w.winfo_class()=="TEntry"],vals):
        e.delete(0,"end"); e.insert(0,v)
root=tk.Tk(); root.geometry("+20+20")
ed=SimpleNamespace(winfo_toplevel=lambda:root,_show_centered_dialog=lambda d:d.geometry("+30+30"),
                   _current_camera_record=lambda:{"resolution_px":[5120,5120]})
dlg=open_system_selection_dialog(ed)
fill(dlg,["8","8","1","","23.04","23.04","0.55"])
dlg.update_idletasks()
dlg.geometry("360x560"); 
for _ in range(10): dlg.update()
grab(dlg, Path("bugs/_0636_reflow_narrow.png"))
dlg.geometry("640x430")
for _ in range(10): dlg.update()
grab(dlg, Path("bugs/_0636_reflow_wide.png"))
root.destroy()
