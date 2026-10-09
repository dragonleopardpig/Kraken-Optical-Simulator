"""Record the Tk main window's pane layout behaviour: sash positions, the two sidebar toggles, the left panel's scrolling."""
import json
import os
import subprocess
import sys
import time
from types import SimpleNamespace


def main(out: str) -> None:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor.geometry("1700x950+0+0")

    def settle(seconds: float = 1.2) -> None:
        end = time.time() + seconds
        while time.time() < end:
            editor.update()
            time.sleep(0.02)

    settle(2.5)

    def panes() -> dict:
        main = editor.main_pane
        names = [str(p) for p in main.panes()]
        return {"panes": len(names), "sashes": [int(main.sashpos(i)) for i in range(max(len(names) - 1, 0))],
                "left_present": bool(editor._pane_present(editor.left_sidebar_host)),
                "right_present": bool(editor._pane_present(editor.right_sidebar_host)),
                "left_restore_shown": bool(editor.left_restore_frame.winfo_ismapped()),
                "right_restore_shown": bool(editor.right_restore_frame.winfo_ismapped()),
                "collapsed": [bool(editor._left_sidebar_collapsed), bool(editor._right_sidebar_collapsed)],
                "center_sash": int(editor.center_panel.sashpos(0)), "passes": int(editor._initial_layout_passes),
                "status": str(editor.status_var.get())[:40], "width": int(main.winfo_width())}

    record = {"start": panes()}
    canvas = editor.control_canvas
    record["scrollregion"] = str(canvas.cget("scrollregion"))
    record["stack_width"] = str(canvas.itemcget(editor.control_stack_window, "width"))
    px, py = canvas.winfo_rootx() + 40, canvas.winfo_rooty() + 60
    canvas.event_generate("<Motion>", warp=True, x=40, y=60)
    settle(0.3)
    before = canvas.yview()
    wheel = [editor._on_left_panel_mousewheel(SimpleNamespace(num=5, delta=0)), editor._on_left_panel_mousewheel(SimpleNamespace(num=5, delta=0))]
    settle(0.2)
    record["wheel"] = {"returns": wheel, "moved_down": canvas.yview()[0] > before[0], "pointer_inside": [px, py] is not None}
    editor._on_left_panel_mousewheel(SimpleNamespace(num=4, delta=0))
    editor._on_left_panel_mousewheel(SimpleNamespace(num=4, delta=0))
    for label, toggle in (("left hidden", editor.toggle_left_sidebar), ("left shown", editor.toggle_left_sidebar),
                          ("right hidden", editor.toggle_right_sidebar), ("both hidden", editor.toggle_left_sidebar),
                          ("left back", editor.toggle_left_sidebar), ("right back", editor.toggle_right_sidebar)):
        toggle()
        settle(0.8)
        record[label] = panes()
    editor._initial_layout_passes = 0
    editor._maybe_refresh_initial_pane_layout()
    settle(0.8)
    record["refreshed"] = panes()
    subprocess.run(["import", "-display", os.environ["DISPLAY"], "-window", "root", out + ".png"], check=False)
    open(out + ".json", "w").write(json.dumps(record, indent=1, sort_keys=True))
    print("written", out, flush=True)
    os._exit(0)


if __name__ == "__main__":
    main(sys.argv[1])
