"""Reproduce the bug-0294 crash on the REAL import path (NVIDIA GLX, DISPLAY=:0).

The user's crash is NOT on quit -- it fires as the "Import Lens from Folder"
import finishes loading. This drives the exact inspector handler body
(open3d_inspector.import_machine_vision_lens_from_folder, 6251-6265) against the
already-present vendor folder, printing a STAGE marker (flushed) before each step
so the last line printed before a segfault names the crash site.

Run:  DISPLAY=:0 .devenv/state/venv/bin/python bugs/probe_0294_import_crash.py
"""
from __future__ import annotations

import sys
from pathlib import Path

FOLDER = "attachment/Lens/PYRITE_56_80_10x_V38_1097785"


def stage(msg: str) -> None:
    print(f"STAGE: {msg}", flush=True)


def main() -> int:
    stage("import KrakenLayoutEditor")
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    stage("construct editor")
    app = KrakenLayoutEditor()
    app.update_idletasks()

    stage("open 3D inspector")
    app.open_3d_view()
    app.update_idletasks()
    app.update()
    inspector = app._three_d_inspector
    if inspector is None or not inspector.available:
        print("inspector unavailable:", getattr(inspector, "unavailable_reason", "?"))
        return 3
    inspector.deiconify()
    inspector.update_idletasks()
    inspector.update()

    # Drive the REAL inspector handler (open3d_inspector.import_machine_vision_
    # lens_from_folder) end-to-end -- monkeypatch the folder chooser so no dialog
    # pops. This exercises the exact code path the user hits, including the
    # keep-inspector-alive fix.
    stage("monkeypatch folder chooser -> vendor folder")
    from KrakenOS.UI import open3d_inspector as insp_mod

    insp_mod.filedialog.askdirectory = lambda *a, **k: str(Path(FOLDER).resolve())

    stage("inspector.import_machine_vision_lens_from_folder()  <-- REAL handler")
    inspector.import_machine_vision_lens_from_folder()
    app.update_idletasks()

    stage("verify inspector survived the swap")
    survivor = app.__dict__.get("_three_d_inspector")
    print("  _three_d_inspector is None:", survivor is None, flush=True)
    print("  same object as before:", survivor is inspector, flush=True)
    if survivor is not None:
        print("  survivor.winfo_exists:", bool(survivor.winfo_exists()), flush=True)
        for _ in range(3):
            survivor.update()

    stage("CLEAN -- no crash; tearing down")
    app.destroy()
    print("CLEAN EXIT", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
