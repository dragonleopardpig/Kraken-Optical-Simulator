"""Phase 5f, part 1 guard (docs/design_qt_migration.md): the 3D inspector's View / Scene / Carry
rows are one catalogue (`open3d_toolbar.py`) rendered by both shells.

  C  every target in the catalogue resolves on a REAL inspector: each command is callable, each
     variable exists -- in the Tk inspector AND in the Qt shell's (a renamed method fails here,
     not on a user's click)
  T  the Tk panel renders the catalogue: each built Tk menu carries exactly the catalogue's entries,
     in order, and the three handle buttons exist
  Q  the Qt shell shows every control but the Tk-only Close, bound both ways: a check written by the
     widget reaches the model and runs its commit, a model write repaints the widget; a menu check,
     a choice and a command button reach the model too
  L  with the rows above it, the Qt viewport keeps >= 400 px and the window fits the screen
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "QT5F_RESULT "
SKIP_MARK = "QT5F_SKIP "
SCENE = Path("attachment/om05a_folded.py")


def _targets():
    from KrakenOS.UI import open3d_toolbar as catalogue

    for item in catalogue.walk(catalogue.ROWS):
        if isinstance(item, (catalogue.Command, catalogue.Button)):
            yield "call", item.target
        elif isinstance(item, catalogue.Toggle):
            yield "call", item.target
            yield "var", item.textvar
        elif isinstance(item, (catalogue.Check, catalogue.Radio)):
            yield "call", item.target
            yield "var", item.var
        elif isinstance(item, catalogue.Choice):
            yield "var", item.var
            if item.target:
                yield "call", item.target
        elif isinstance(item, catalogue.Entry):
            yield "var", item.var


def unresolved(inspector) -> list:
    from KrakenOS.UI import open3d_toolbar as catalogue

    missing = []
    for kind, target in _targets():
        try:
            value = catalogue.resolve(inspector, target)
        except Exception:
            value = None
        if value is None or (kind == "call" and not callable(value)) or (kind == "var" and not hasattr(value, "get")):
            missing.append(target)
    return sorted(set(missing))


def tk_checks() -> list:
    from KrakenOS.UI import open3d_toolbar as catalogue
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _open_inspector

    app = KrakenLayoutEditor(headless=True)
    try:
        inspector = _open_inspector(app)
        rows = [["C-tk", not unresolved(inspector), f"unresolved on the Tk inspector: {unresolved(inspector)}"]]
        mismatched = []
        menus = [m for m in catalogue.walk(catalogue.ROWS) if isinstance(m, (catalogue.Menu, catalogue.Radio)) and m.handle]
        for spec in menus:
            menu = getattr(inspector, spec.handle, None)
            if isinstance(spec, catalogue.Radio):
                wanted = [label for label, _value in spec.options]
            else:
                wanted = [e.label if e is not None else "---" for e in spec.entries]
            end = menu.index("end") if menu is not None else None
            built = [] if end is None else [
                "---" if menu.type(i) == "separator" else menu.entrycget(i, "label") for i in range(end + 1)]
            if built != wanted:
                mismatched.append((spec.label, built[:4], wanted[:4]))
        buttons = [getattr(inspector, h, None) is not None for h in ("_recorder_button", "_discard_button", "_flag_bug_button")]
        rows.append(["T", not mismatched and all(buttons),
                     f"{len(menus)} Tk menus equal the catalogue (mismatched: {mismatched}); handle buttons {buttons}"])
        return rows
    finally:
        try:
            app.destroy()
        except Exception:
            pass


def qt_runtime_checks() -> list:
    from KrakenOS.UI import open3d_toolbar as catalogue
    from KrakenOS.UI.qt.app import build

    app, window = build(["guard"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    view = window.build_inspector_view()
    for _ in range(30):
        app.processEvents()
    insp, toolbar = view.inspector, view.toolbar
    controls = toolbar.controls
    rows = [["C-qt", not unresolved(insp), f"unresolved on the Qt shell's inspector: {unresolved(insp)}"]]

    expected = set()
    for row in catalogue.ROWS:
        for item in row.left + row.right:
            if isinstance(item, catalogue.Command) and item.tk_only:
                continue
            if isinstance(item, catalogue.Toggle):
                expected.add(item.textvar)
            elif isinstance(item, catalogue.Menu):
                expected.add(item.label)

                def entries_of(menu) -> None:
                    # an entry is keyed by the menu that directly holds it (a cascade by its own)
                    for entry in menu.entries:
                        if isinstance(entry, catalogue.Menu):
                            entries_of(entry)
                        elif isinstance(entry, (catalogue.Check, catalogue.Command)) and not getattr(entry, "tk_only", False):
                            expected.add(f"{menu.label}/{entry.label}")

                entries_of(item)
            elif not isinstance(item, catalogue.Text):
                expected.add(item.label)
    missing = sorted(expected - set(controls))
    notes = []
    calls = []
    original = insp._on_show_rays_changed
    insp._on_show_rays_changed = lambda *a: calls.append("commit") or original(*a)
    box = controls.get("Show rays")
    before = bool(insp.show_rays_var.get())
    box.setChecked(not before)
    app.processEvents()
    wrote = bool(insp.show_rays_var.get()) == (not before) and calls == ["commit"]
    insp.show_rays_var.set(before)
    app.processEvents()
    repainted = box.isChecked() == before
    thickness = insp.editor.show_physical_distances_var
    t_before = bool(thickness.get())
    controls["Overlays/Thickness"].trigger()
    app.processEvents()
    menu_check = bool(thickness.get()) == (not t_before)
    controls["Rot"].setCurrentText("45")
    app.processEvents()
    choice = str(insp.rotation_step_deg_var.get()) == "45"
    controls["Measure"].click()
    app.processEvents()
    command = bool(insp._measure_pick_mode)
    insp.clear_measurements()
    notes = [f"check writes+commits={wrote}", f"model repaints={repainted}", f"menu check={menu_check}",
             f"choice={choice}", f"command={command}"]
    rows.append(["Q", not missing and "Close" not in controls and wrote and repainted and menu_check and choice and command,
                 f"{len(controls)} Qt controls (missing: {missing[:6]}; Close shown: {'Close' in controls}); " + ", ".join(notes)])
    screen = window.screen().availableGeometry().height()
    rows.append(["L", view.widget.height() >= 400 and window.height() <= screen,
                 f"viewport {view.widget.width()}x{view.widget.height()} px under a {toolbar.height()} px toolbar; "
                 f"window {window.height()} px on a {screen} px screen"])
    return rows


def _run(driver_call: str) -> tuple[str, list]:
    driver = (
        "import json, os\n"
        "try:\n"
        "    import PySide6\n"
        "except Exception as exc:\n"
        f"    print({SKIP_MARK!r} + repr(exc))\n"
        "    raise SystemExit(0)\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY')\n"
        "    raise SystemExit(0)\n"
        "from KrakenOS.UI.validate_open3d_qt_5f_toolbar import tk_checks, qt_runtime_checks\n"
        f"print({RESULT_MARK!r} + json.dumps({driver_call}))\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True,
                              timeout=1200, env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return "error", [["X", False, f"{driver_call} timed out"]]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return "ok", json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return "skip", [["X", True, line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
    return "error", [["X", False, f"{driver_call}: exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    if not SCENE.exists():
        return True, [f"SKIP = {SCENE} absent"]
    notes, passed = [], True
    for call in ("tk_checks()", "qt_runtime_checks()"):
        _status, rows = _run(call)
        for key, ok, detail in rows:
            passed = passed and bool(ok)
            notes.append(f"{key} = {detail}" if ok else f"{key} FAILED: {detail}")
    return passed, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
