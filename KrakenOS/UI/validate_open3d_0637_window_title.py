"""Guard for bugs/0637 — the loaded layout file shows in the window title.

User: "after loading a .py file, there is no mention anywhere of the loaded file name."
The window title was set once to "KrakenOS Layout Editor" and never updated. Now every
loader/saver calls `_update_window_title`, which names the current layout file.

Checks (display-free):
  A  BEHAVIOUR — the title names a loaded file, tags a transient import, and falls back to
     the base title when nothing is loaded (via a stub that records `title()`).
  B  CONTRACT — the load/save/reset paths call `_update_window_title` (open_layout, the
     zemax loader, load_layout_by_name, save_layout, save_layout_as, reset_layout).

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0637_window_title
"""

from __future__ import annotations

import inspect


def run_checks():
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services import layout_import_export as ie
    from KrakenOS.UI.services import layout_table_workbench as wb

    cls = next(
        c for c in vars(wb).values() if isinstance(c, type) and "_update_window_title" in vars(c)
    )

    class _Stub:
        def __init__(self, path, unsaved=False):
            self.current_layout_file = path
            self._layout_is_unsaved_import = unsaved
            self._title = None

        def title(self, *a):
            if a:
                self._title = a[0]
            return self._title

    # ---------------------------------------------------------------- A: behaviour
    loaded = _Stub("attachment/machine_vision_Apo75.py")
    imported = _Stub("/x/machine_vision_pyrite.py", unsaved=True)
    empty = _Stub(None)
    cls._update_window_title(loaded)
    cls._update_window_title(imported)
    cls._update_window_title(empty)
    # Just the filename (the app name clipped on small title bars); "*" flags an import.
    if loaded._title != "machine_vision_Apo75.py":
        ok = False
        notes.append(f"FAIL: A (bugs/0637): loaded-file title should be the bare filename: {loaded._title!r}")
    elif imported._title != "* machine_vision_pyrite.py":
        ok = False
        notes.append(f"FAIL: A (bugs/0637): unsaved-import title wrong: {imported._title!r}")
    elif empty._title != "KrakenOS Layout Editor":
        ok = False
        notes.append(f"FAIL: A (bugs/0637): base title wrong: {empty._title!r}")
    else:
        notes.append("PASS: A: title is the bare filename, '*'-tags an import, base when empty")

    # ---------------------------------------------------------------- B: contract
    wb_src = inspect.getsource(wb)
    ie_src = inspect.getsource(ie)
    load_by_name = inspect.getsource(cls.load_layout_by_name)
    reset = inspect.getsource(cls.reset_layout)
    missing = []
    if "_update_window_title" not in load_by_name:
        missing.append("load_layout_by_name")
    if "_update_window_title" not in reset:
        missing.append("reset_layout")
    for site in ("open_layout", "_load_zemax_prescription_path", "save_layout", "save_layout_as"):
        try:
            src = inspect.getsource(getattr(next(
                c for c in vars(ie).values() if isinstance(c, type) and hasattr(c, site)), site))
        except Exception:
            src = ""
        if "_update_window_title" not in src:
            missing.append(site)
    if missing:
        ok = False
        notes.append(f"FAIL: B (bugs/0637): these paths do not update the title: {missing}")
    else:
        notes.append("PASS: B: every load/save/reset path updates the window title")

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for line in notes:
        print(line)
    print("Window-title validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
