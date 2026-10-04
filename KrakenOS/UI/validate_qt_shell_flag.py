"""Guard for bugs/0959: a bug flag for the whole Qt window, from anywhere in it.

The `s` flag was made for the 3D window: its picture is the VTK render and its state is the scene.
In the Qt shell the scene is one part of a window with a ribbon, a surface table, edge panels and
dialogs, so a flag about any of those had nothing to show for it -- and `s` only works with the
pointer over the scene. The Tk editor's own flag (Ctrl+Shift+B: the whole screen, the 2D plot, the
open dialogs) had no route in the Qt shell at all.

  P  pure: when a window "exceeds the screen" -- larger than it, or off any of its edges
  N  with NO 3D inspector (the scene not built) Flag Bug still writes a bundle -- the window's
     picture, the build, the shell's state -- and asks for the words; Discard deletes it
  W  Ctrl+Shift+B, the real key, with the keyboard in the 3D scene: ONE bundle; screenshot.png is
     the WHOLE window at its own size, with the 3D scene painted in where the scene is (the same
     pixels as the 3D render, kept as scene_3d.png) and a crosshair where the pointer was;
     state.json names what the pointer was over (the surface table's dock), the ribbon's tab, every
     panel and where it is; layout_state.json holds the model's rows
  K  one press, one flag: the key with the keyboard in the surface table writes one more bundle,
     and inside a flag's own description box it writes none; a menu that takes the keyboard does
     not grow a Flag Bug entry
  S  the `s` flag keeps its picture -- screenshot.png is the 3D render -- and now also carries the
     whole window (window.png) and the shell's state
  T  without a shell the bundle is as it was: three files, no shell state, whatever the subject
  D  a dialog in front (a real report dialog), the key pressed IN it: one bundle whose
     screenshot.png is that dialog, listed by title as the window in front; the main window is
     kept as window.png
  M  a MODAL dialog: the key works in it, and the description box belongs to it and takes typed
     text (a window of the main window would be shut out); closing the dialog saves what was
     typed; an empty box is kept, not deleted
  O  a dialog bigger than the screen is flagged as exceeding it and pictured WHOLE
  R  the ribbon's corner has a Flag Bug button on every tab, showing while the ribbon is folded;
     a click on it writes one bundle
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "SHELLFLAG_RESULT "
SKIP_MARK = "SHELLFLAG_SKIP "
SCENE = Path("KrakenOS/common_optical_layouts/beam_splitter_two_arm_doublets.py")


def pure_checks() -> list:
    from KrakenOS.UI.qt.flag_capture import exceeds_screen

    screen = (0, 0, 1600, 1000)
    cases = {
        "inside": (exceeds_screen(100, 100, 800, 600, screen), False),
        "exactly the screen": (exceeds_screen(0, 0, 1600, 1000, screen), False),
        "taller than the screen": (exceeds_screen(0, 0, 800, 1200, screen), True),
        "wider than the screen": (exceeds_screen(0, 0, 1700, 600, screen), True),
        "off the bottom edge": (exceeds_screen(100, 600, 800, 600, screen), True),
        "off the right edge": (exceeds_screen(1000, 100, 800, 600, screen), True),
        "off the top-left": (exceeds_screen(-20, -20, 800, 600, screen), True),
        "on a second screen": (exceeds_screen(1700, 100, 800, 600, (1600, 0, 1600, 1000)), False),
        "no size yet": (exceeds_screen(0, 0, 0, 0, screen), False),
    }
    wrong = sorted(name for name, (got, want) in cases.items() if got is not want)
    return [["P", not wrong, f"{len(cases)} cases, wrong: {wrong}"]]


def qt_runtime_checks() -> dict:
    import tempfile
    import time

    import numpy as np
    from PIL import Image
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtGui import QCursor
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QDialog, QMenu, QPlainTextEdit, QVBoxLayout

    from KrakenOS.UI import open3d_inspector
    from KrakenOS.UI.qt.app import build

    root = Path(tempfile.mkdtemp(prefix="flag0959_"))
    open3d_inspector.ATTACHMENT_DIR = root          # the bundles of this run go to a temp folder
    flags = root / "recorded_bug_repros"
    ctrl_shift = Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier
    app, window = build(["guard"])
    window.show()
    app.processEvents()
    action = window.action_manager["flag_bug"]
    rows = []

    def settle(seconds: float = 0.3) -> None:
        end = time.time() + seconds
        while time.time() < end:
            app.processEvents()
            time.sleep(0.02)

    def bundles() -> list:
        return sorted(flags.glob("flag_*")) if flags.exists() else []

    def new_bundles(before: list) -> list:
        settle()
        return [path for path in bundles() if path not in before]

    def files(bundle) -> list:
        return sorted(path.name for path in bundle.iterdir())

    def state(bundle) -> dict:
        return json.loads((bundle / "state.json").read_text(encoding="utf-8"))

    def size(path) -> "tuple | None":
        if not Path(path).exists():
            return None
        with Image.open(path) as image:
            return image.size

    def widget_size(widget) -> tuple:
        ratio = widget.devicePixelRatioF()
        return (round(widget.width() * ratio), round(widget.height() * ratio))

    def answer(how: str = "keep"):
        """Answer the prompt just opened -- and any other left open, so no claim sees another's."""
        prompt = window.last_flag_description_dialog
        if prompt is not None and prompt.outcome is None:
            prompt.finish(how)
        for other in QApplication.topLevelWidgets():
            if getattr(other, "is_flag_prompt", False) and other.outcome is None:
                other.finish("keep")
        settle(0.1)
        return prompt

    def press(target) -> None:
        QTest.keyClick(target, Qt.Key.Key_B, ctrl_shift)

    def attempt(key: str, claim) -> None:
        """Run one claim; one that raises has failed, and the others still run."""
        try:
            claim()
        except Exception as exc:
            rows.append([key, False, f"raised {type(exc).__name__}: {exc}"])
            answer("keep")

    def activate(top) -> bool:
        """Make ``top`` THE active window. (`QTest.qWaitForWindowActive` is no test of that: a
        dialog counts as active while the window it belongs to is.)"""
        end = time.time() + 3.0
        while time.time() < end:
            top.raise_()
            top.activateWindow()
            settle(0.1)
            if QApplication.activeWindow() is top:
                return True
        return False

    # ---- N: no inspector ------------------------------------------------------------------------
    def claim_n() -> None:
        before = bundles()
        no_scene = window._scene_inspector() is None
        action.trigger()
        made = new_bundles(before)
        prompt = window.last_flag_description_dialog
        ok_n, detail_n = False, f"no inspector: {no_scene}; bundles written: {len(made)}"
        if len(made) == 1:
            bundle, data = made[0], state(made[0])
            shell = data.get("shell", {})
            asked = prompt is not None and prompt.isVisible() and not prompt.isModal()
            picture = size(bundle / "screenshot.png") if (bundle / "screenshot.png").exists() else None
            answer("discard")
            ok_n = (no_scene and asked and picture == widget_size(window) and data.get("source") == "shell_window"
                    and data.get("screenshot_kind") == "window" and "git" in data.get("build", {})
                    and shell.get("central") == "none" and shell.get("toolkit") == "qt" and not bundle.exists())
            detail_n += (f"; picture {picture} for a window of {widget_size(window)}; source {data.get('source')!r}, kind "
                         f"{data.get('screenshot_kind')!r}, build {sorted(data.get('build', {}))[:2]}, central "
                         f"{shell.get('central')!r}; prompt shown, not modal: {asked}; after Discard the bundle exists: "
                         f"{bundle.exists()}")
        rows.append(["N", ok_n, detail_n])

    attempt("N", claim_n)

    view = window.build_scene()
    window.load_layout_path(SCENE)
    settle(2.0)
    inspector = window._scene_inspector()
    if inspector is None:
        rows.append(["X", True, "SKIP: the embedded 3D inspector is unavailable"])
        return {"rows": rows}

    # ---- W: the whole window, by the real key ---------------------------------------------------
    def claim_w() -> None:
        activate(window)
        on_table = window.rows_view.viewport().mapToGlobal(QPoint(60, 14))
        QCursor.setPos(on_table)
        settle()
        view.widget.setFocus()
        settle(0.1)
        before = bundles()
        press(view.widget)
        made = new_bundles(before)
        ok_w, detail_w = False, f"bundles written by one Ctrl+Shift+B in the scene: {len(made)}"
        if len(made) == 1 and not (made[0] / "scene_3d.png").exists():
            detail_w += f"; no scene_3d.png: the flag was not about the window -- files {files(made[0])}"
        elif len(made) == 1:
            bundle, data = made[0], state(made[0])
            shell = data.get("shell", {})
            shot = np.asarray(Image.open(bundle / "screenshot.png").convert("RGB")).astype(int)
            whole = (shot.shape[1], shot.shape[0]) == widget_size(window)
            # the 3D scene, where the scene is: the same pixels as the render VTK wrote
            origin = view.widget.mapTo(window, QPoint(0, 0))
            render = np.asarray(Image.open(bundle / "scene_3d.png").convert("RGB")).astype(int)
            region = shot[origin.y():origin.y() + render.shape[0], origin.x():origin.x() + render.shape[1]]
            same = float((np.abs(region - render).max(axis=2) <= 24).mean()) if region.shape == render.shape else 0.0
            drawn = float(render.std())
            chrome = float(shot[:origin.y()].std())                       # the ribbon + table above the scene
            # the crosshair, where the pointer was
            pointer = window.mapFromGlobal(on_table)
            ring = tuple(int(v) for v in shot[pointer.y(), pointer.x() + 16])
            ring_ok = ring[1] > 200 and ring[0] < 90 and ring[2] < 90
            told = shell.get("pointer", {})
            over = told.get("over", [])
            docks = {dock["name"]: dock for dock in shell.get("docks", [])}
            wanted_docks = {"SurfaceTableDock": "top", "RibbonDock": "top", "SystemDock": "right", "DebugDock": "bottom"}
            docks_ok = all(docks.get(name, {}).get("area") == area for name, area in wanted_docks.items())
            table_dock = window.dock_manager["SurfaceTableDock"]
            table_ok = (docks.get("SurfaceTableDock", {}).get("showing") is True
                        and docks["SurfaceTableDock"]["width"] == table_dock.width())
            ribbon = shell.get("ribbon", {})
            ribbon_ok = (ribbon.get("tab") == window.ribbon.tabs.tabText(window.ribbon.tabs.currentIndex())
                         and ribbon.get("folded") == bool(window.ribbon.collapsed))
            layout_rows = json.loads((bundle / "layout_state.json").read_text(encoding="utf-8")).get("rows", [])
            prompt = window.last_flag_description_dialog
            asked = prompt is not None and prompt.isVisible() and not prompt.isModal()
            ok_w = (files(bundle) == ["description.txt", "layout_state.json", "scene_3d.png", "screenshot.png", "state.json"]
                    and whole and same >= 0.97 and drawn > 3.0 and chrome > 10.0 and ring_ok
                    and told.get("window_xy") == [pointer.x(), pointer.y()] and "QDockWidget(SurfaceTableDock)" in over
                    and data.get("screenshot_kind") == "window" and data.get("scene_3d") == "scene_3d.png"
                    and shell.get("screenshot_of") == "window" and shell.get("central") == "inspector"
                    and docks_ok and table_ok and ribbon_ok and len(layout_rows) == len(window.editor.rows) > 0
                    and "scene_state" in data and not shell.get("errors") and asked)
            detail_w += (f"; files {files(bundle)}; screenshot {shot.shape[1]}x{shot.shape[0]} for a window of "
                         f"{widget_size(window)}; scene region equal to the 3D render in {same:.1%} of its pixels (render "
                         f"spread {drawn:.1f}, ribbon + table spread {chrome:.1f}); crosshair pixel at the pointer {ring}; "
                         f"pointer {told.get('window_xy')} over {over[:4]}; kind {data.get('screenshot_kind')!r}; docks "
                         f"{ {name: docks.get(name, {}).get('area') for name in wanted_docks} }; ribbon {ribbon}; "
                         f"layout_state rows {len(layout_rows)} of {len(window.editor.rows)}; errors {shell.get('errors')}; "
                         f"prompt shown, not modal: {asked}")
        rows.append(["W", ok_w, detail_w])

    attempt("W", claim_w)

    # ---- K: one press, one flag -----------------------------------------------------------------
    def claim_k() -> None:
        prompt = window.last_flag_description_dialog
        counts = []
        in_front = offered = None
        if prompt is not None and prompt.outcome is None:
            in_front = activate(prompt)
            prompt.text.setFocus()
            settle(0.1)
            before = bundles()
            press(prompt.text)
            counts.append(len(new_bundles(before)))
            offered = action in prompt.actions()
        answer("keep")
        activate(window)
        window.rows_view.setFocus()
        settle(0.1)
        before = bundles()
        press(window.rows_view)
        counts.append(len(new_bundles(before)))
        answer("keep")
        # a menu SHOWS its actions: one that took the keyboard must not grow a Flag Bug entry
        menu = QMenu(window)
        entry = menu.addAction("An entry")
        menu.popup(window.mapToGlobal(QPoint(40, 40)))
        settle(0.2)
        window._offer_flag_bug(None, menu)
        menu_entries = [item.text() for item in menu.actions()]
        menu.hide()
        del entry
        rows.append(["K", counts == [0, 1] and in_front is True and offered is False and menu_entries == ["An entry"],
                     f"bundles written by the key [in a flag's description box (in front: {in_front}), in the surface "
                     f"table]: {counts}; the description box was given the action: {offered}; a menu that took the "
                     f"keyboard lists {menu_entries}"])

    attempt("K", claim_k)

    # ---- S: the `s` flag ------------------------------------------------------------------------
    def claim_s() -> None:
        before = bundles()
        inspector.flag_bug()
        made = new_bundles(before)
        answer("keep")
        ok_s, detail_s = False, f"bundles: {len(made)}"
        if len(made) == 1:
            bundle, data = made[0], state(made[0])
            render_size = tuple(int(v) for v in view.widget.GetRenderWindow().GetSize())
            ok_s = (files(bundle) == ["description.txt", "layout_state.json", "screenshot.png", "state.json", "window.png"]
                    and size(bundle / "screenshot.png") == render_size and size(bundle / "window.png") == widget_size(window)
                    and data.get("screenshot_kind") == "scene_3d" and data.get("shell", {}).get("screenshot_of") is None
                    and data.get("shell", {}).get("window_png") == "window.png")
            detail_s += (f"; files {files(bundle)}; screenshot {size(bundle / 'screenshot.png')} = the render "
                         f"{render_size}; window.png {size(bundle / 'window.png')} = the window {widget_size(window)}; kind "
                         f"{data.get('screenshot_kind')!r}")
        rows.append(["S", ok_s, detail_s])

    attempt("S", claim_s)

    # ---- T: without a shell ---------------------------------------------------------------------
    def claim_t() -> None:
        hook = window.editor.__dict__.pop("capture_flag_shell", None)
        plain = []
        try:
            for subject in ("scene", "window"):
                before = bundles()
                inspector.flag_bug(subject=subject)
                made = new_bundles(before)
                answer("keep")
                plain.append((files(made[0]), "shell" in state(made[0]), state(made[0]).get("screenshot_kind"))
                             if len(made) == 1 else None)
        finally:
            if hook is not None:
                window.editor.capture_flag_shell = hook
        three = ["description.txt", "screenshot.png", "state.json"]
        rows.append(["T", hook is not None and plain == [(three, False, "scene_3d"), (three, False, "scene_3d")],
                     f"the shell had set its hook: {hook is not None}; without it, subject scene / window: {plain}"])

    attempt("T", claim_t)

    # ---- D: a dialog in front -------------------------------------------------------------------
    def claim_d() -> None:
        report = window.paraxial_matrix_report_action()
        settle()
        ok_d, detail_d = False, "the report dialog did not open"
        if report is not None:
            active = activate(report)
            target = report.focusWidget() or report
            before = bundles()
            press(target)
            made = new_bundles(before)
            answer("keep")
            detail_d = f"report dialog active: {active}; bundles written by the key in it: {len(made)}"
            if len(made) == 1:
                bundle, data = made[0], state(made[0])
                entries = [entry for entry in data.get("shell", {}).get("open_windows", []) if entry.get("png") == "screenshot.png"]
                ok_d = (size(bundle / "screenshot.png") == widget_size(report)
                        and size(bundle / "window.png") == widget_size(window) and (bundle / "scene_3d.png").exists()
                        and data.get("screenshot_kind") == "dialog" and len(entries) == 1
                        and entries[0]["title"] == report.windowTitle() and entries[0]["active"] is True
                        and entries[0]["exceeds_screen"] is False)
                detail_d += (f"; screenshot {size(bundle / 'screenshot.png')} = the dialog {widget_size(report)}; window.png "
                             f"{size(bundle / 'window.png')}; kind {data.get('screenshot_kind')!r}; listed as "
                             f"{[(entry['class'], entry['title'], entry['active']) for entry in entries]}")
            report.close()
            settle(0.1)
        rows.append(["D", ok_d, detail_d])

    attempt("D", claim_d)

    # ---- M: a modal dialog ----------------------------------------------------------------------
    def claim_m() -> None:
        def modal_dialog(title: str):
            dialog = QDialog(window)
            dialog.setWindowTitle(title)
            box = QPlainTextEdit()
            QVBoxLayout(dialog).addWidget(box)
            dialog.setModal(True)
            dialog.resize(420, 260)
            dialog.show()
            activate(dialog)
            box.setFocus()
            settle(0.1)
            return dialog, box

        outcomes = []
        for typed in ("typed in the box", ""):
            dialog, box = modal_dialog("A modal dialog")
            is_modal = QApplication.activeModalWidget() is dialog
            before = bundles()
            press(box)
            made = new_bundles(before)
            prompt = window.last_flag_description_dialog
            entry = {"modal": is_modal, "bundles": len(made)}
            if len(made) == 1 and prompt is not None:
                entry["kind"] = state(made[0]).get("screenshot_kind")
                entry["belongs to the dialog"] = prompt.parent() is dialog
                activate(prompt)
                prompt.text.setFocus()
                settle(0.1)
                for letter in typed:
                    # through the window system, as a real key is: a window a modal dialog shuts out
                    # gets none (a key sent straight to the widget would arrive anyway)
                    QTest.keyClick(prompt.windowHandle(), letter)
                settle(0.1)
                entry["typed"] = prompt.text.toPlainText()
                dialog.reject()                                  # the modal dialog closes, the prompt with it
                settle()
                entry["prompt open"] = prompt.isVisible()
                entry["bundle kept"] = made[0].exists()
                entry["description"] = (made[0] / "description.txt").read_text(encoding="utf-8") if made[0].exists() else None
            else:
                dialog.reject()
            outcomes.append(entry)
        want = [{"modal": True, "bundles": 1, "kind": "dialog", "belongs to the dialog": True,
                 "typed": "typed in the box", "prompt open": False, "bundle kept": True,
                 "description": "typed in the box\n"},
                {"modal": True, "bundles": 1, "kind": "dialog", "belongs to the dialog": True, "typed": "",
                 "prompt open": False, "bundle kept": True, "description": ""}]
        rows.append(["M", outcomes == want, f"typed, then nothing typed: {outcomes}"])

    attempt("M", claim_m)

    # ---- O: a dialog bigger than the screen -----------------------------------------------------
    def claim_o() -> None:
        screen = window.screen().geometry()
        big = QDialog(window)
        big.setWindowTitle("Taller than the screen")
        QVBoxLayout(big).addWidget(QPlainTextEdit("the OK button is off the bottom"))
        big.resize(520, screen.height() + 300)
        big.show()
        settle()
        activate(window)
        before = bundles()
        action.trigger()
        made = new_bundles(before)
        answer("keep")
        ok_o, detail_o = False, f"dialog {big.width()}x{big.height()} on a {screen.width()}x{screen.height()} screen; bundles {len(made)}"
        if len(made) == 1 and big.height() > screen.height():
            data = state(made[0])
            entries = [entry for entry in data.get("shell", {}).get("open_windows", []) if entry["title"] == big.windowTitle()]
            picture = size(made[0] / entries[0]["png"]) if entries and entries[0].get("png") else None
            ok_o = (len(entries) == 1 and entries[0]["exceeds_screen"] is True and picture == widget_size(big)
                    and data.get("shell", {}).get("oversized_windows") == [big.windowTitle()]
                    and data.get("screenshot_kind") == "window")
            detail_o += (f"; listed {[(entry['title'], entry['exceeds_screen'], entry['png']) for entry in entries]}; its "
                         f"picture {picture}; oversized {data['shell'].get('oversized_windows')}; the main window was in "
                         f"front, kind {data.get('screenshot_kind')!r}")
        big.close()
        settle(0.1)
        rows.append(["O", ok_o, detail_o])

    attempt("O", claim_o)

    # ---- R: the ribbon's corner button ----------------------------------------------------------
    def claim_r() -> None:
        ribbon = window.ribbon
        button = ribbon.flag_button
        was_folded = bool(ribbon.collapsed)
        shown = []
        for folded in (False, True):
            ribbon.set_collapsed(folded)
            settle(0.2)
            for index in range(ribbon.tabs.count()):
                ribbon.tabs.setCurrentIndex(index)
                settle(0.05)
                shown.append(button.isVisible() and button.visibleRegion().boundingRect().width() >= 16)
            ribbon._close_popups()
        before = bundles()
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        made = new_bundles(before)
        answer("discard")
        ribbon.set_collapsed(was_folded)
        tip = button.toolTip()
        rows.append(["R", all(shown) and len(shown) == 2 * ribbon.tabs.count() and len(made) == 1
                     and "Flag Bug" in tip and "Ctrl+Shift+B" in tip,
                     f"the corner button shows on every tab, ribbon open and folded: {all(shown)} ({len(shown)} checks); "
                     f"its tooltip names the command and its key: {tip[:44]!r}; a click on it with the ribbon folded "
                     f"wrote {len(made)} bundle(s)"])

    attempt("R", claim_r)

    return {"rows": rows}


def _run(call: str) -> list:
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
        "from KrakenOS.UI.validate_qt_shell_flag import qt_runtime_checks\n"
        # flushed, then exit WITHOUT interpreter teardown (a VTK/Qt teardown crash must not lose it)
        f"print({RESULT_MARK!r} + json.dumps({call}), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True, timeout=900,
                              env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return [["X", False, f"{call} timed out"]]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return json.loads(line[len(RESULT_MARK):])["rows"]
        if line.startswith(SKIP_MARK):
            return [["X", True, f"SKIP {call}: " + line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-6:]
    return [["X", False, f"{call} exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    rows = pure_checks() + _run("qt_runtime_checks()")
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
