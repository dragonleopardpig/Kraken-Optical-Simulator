"""bugs/0999: what the Tk editor does with the clipboard, a scheduled plot refresh and the plot auto-save.

On a real Tk editor, with no clipboard tool to be found (so the fallback is what runs): an
element's rows copied and pasted back, a text copied, a plot refresh scheduled, and the auto-save
switched on in a large window and in a small one. Run at the commit before and after.

    python bugs/0999_tk_copy_paste_autosave.py <output .json>

The auto-save is pointed at a file beside the output -- after the editor's module is imported,
which is what hands every service the real path.
"""
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

LAYOUT = Path("KrakenOS/common_optical_layouts/beam_splitter_two_arm_doublets.py")


def main(out: str) -> None:
    import tkinter.messagebox as tk_messagebox

    for name in ("showinfo", "showwarning", "showerror"):
        setattr(tk_messagebox, name, lambda *a, **k: "ok")
    shutil.which = lambda *_a, **_k: None
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services import layout_analysis_display

    picture = Path(out).with_suffix(".auto_saved.png")
    picture.unlink(missing_ok=True)
    layout_analysis_display.AUTO_PLOT_PATH = picture
    editor = KrakenLayoutEditor()
    editor.geometry("1700x950+0+0")

    def settle(seconds: float = 0.5) -> None:
        end = time.time() + seconds
        while time.time() < end:
            editor.update()
            time.sleep(0.02)

    settle(1.5)
    editor.layout_files[LAYOUT.stem] = LAYOUT
    editor.load_layout_by_name(LAYOUT.stem, refresh=False)
    settle(0.8)
    record = {}
    editor._select_table_indices([3, 4], focus_index=3)
    settle(0.3)
    editor.copy_selected_rows_to_clipboard()
    settle(0.3)
    text = str(editor.clipboard_get())
    record["rows copied"] = {"status": str(editor.status_var.get()), "on the Tk clipboard": hashlib.sha1(text.encode()).hexdigest()[:12],
                             "characters": len(text)}
    editor._surface_row_clipboard = []
    record["pasted"] = [str(row.name) for row in editor._pasted_surface_rows()]
    editor.clipboard_clear()
    editor.clipboard_append("")
    record["pasted from an empty clipboard"] = [str(row.name) for row in editor._pasted_surface_rows()]
    editor.copy_selected_text("three words here")
    settle(0.2)
    record["text copied"] = {"status": str(editor.status_var.get()), "on the Tk clipboard": str(editor.clipboard_get())}
    editor.copy_selected_text("")
    record["no text"] = str(editor.status_var.get())

    refreshes = []
    real = editor._refresh_plot_from_controls
    editor._refresh_plot_from_controls = lambda *a, **k: (refreshes.append(1), real(*a, **k))[1]
    record["exists"] = bool(editor.winfo_exists())
    editor._schedule_refresh_plot()
    editor._schedule_refresh_plot()                     # the second cancels the first
    record["scheduled"] = editor._refresh_after_id is not None
    settle(1.0)
    del editor._refresh_plot_from_controls
    record["refreshes after two schedules"] = len(refreshes)

    if layout_analysis_display.AUTO_PLOT_PATH != picture:
        raise RuntimeError("the auto-save would write the user's picture")
    record["window"] = [editor.winfo_width(), editor.winfo_height()]
    editor.auto_save_plot_var.set(True)
    editor._autosave_plot()
    settle(1.5)
    record["auto-saved in the large window"] = picture.exists() and picture.stat().st_size > 5000
    picture.unlink(missing_ok=True)
    editor.geometry("1000x650+0+0")
    settle(1.0)
    record["small window"] = [editor.winfo_width(), editor.winfo_height()]
    editor._autosave_plot()
    settle(1.5)
    record["auto-saved in the small window"] = picture.exists()
    record["still waiting"] = editor._autosave_after_id is not None
    editor.auto_save_plot_var.set(False)
    settle(0.6)
    Path(out).write_text(json.dumps(record, indent=1, sort_keys=True), encoding="utf-8")
    print("written", out, flush=True)
    os._exit(0)


if __name__ == "__main__":
    main(sys.argv[1])
