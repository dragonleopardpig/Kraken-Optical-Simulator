"""Guard for the Qt shell's ribbon + command palette (bugs/0935). In a real Qt shell on om05a_folded:

  C  the ribbon and `RIBBON_EXCLUDED` cover the shell's `ACTIONS` exactly (a new action cannot go
     missing), no action is on it twice, and every action has an icon that draws pixels -- no two
     icons render the same
  B  each ribbon button runs ITS OWN action (the click reaches that action's `trigger`)
  R  Show Rays keeps one state: a ribbon click flips the menu action AND really hides the traced
     rays (the viewport's ray actors), and the menu action checks the ribbon button again
  A  the ribbon's plot picker is the analysis picker: it carries the same menu, and its caption
     follows the model's selection
  P  the palette: Ctrl+Shift+P focuses it; "gaussian beam" runs the Gaussian Beam Report action;
     a fragment several commands share runs nothing
  F  on a 1000-px screen the ribbon starts folded and the 3D view keeps >= 400 px; a tab click drops
     its page as a pop-up, and running a command from it closes the pop-up
  D  (bugs/0940) the ribbon is a dock: undocked it is a window of its own showing its pages, with
     EXACTLY ONE page visible (unfolding used to show all four drawn over each other); docked
     again it returns to the top area, folded to its tab row, and the 3D view gets its height back
  U  docked and unfolded (double-click a tab), exactly one page shows; folded again, none
  T  (bugs/0940) the surface table is across the TOP of the window -- full width, under the ribbon
     and above the 3D inspector -- so its columns show without sideways scrolling
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "QTRIBBON_RESULT "
SKIP_MARK = "QTRIBBON_SKIP "
SCENE = Path("attachment/om05a_folded.py")


def qt_runtime_checks() -> list:
    import time

    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage
    from PySide6.QtTest import QTest

    from KrakenOS.UI.qt.actions import ACTIONS
    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.qt.ribbon import RIBBON_EXCLUDED, ribbon_entries

    app, window = build(["guard"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    view = window.build_inspector_view()

    def settle(seconds: float) -> None:
        end = time.time() + seconds
        while time.time() < end:
            app.processEvents()
            time.sleep(0.02)

    settle(1.5)
    ribbon = window.ribbon
    actions = window.action_manager.actions
    rows = []

    # C -- coverage, uniqueness, icons that draw and differ
    on_ribbon = [name for _t, _g, name, _s, _l in ribbon_entries()]
    declared = [a[0] for a in ACTIONS]
    missing = sorted(set(declared) - set(on_ribbon) - set(RIBBON_EXCLUDED))
    unknown = sorted(set(on_ribbon) - set(declared))
    twice = sorted({n for n in on_ribbon if on_ribbon.count(n) > 1})
    images = {}
    for name, action in actions.items():
        image = action.icon().pixmap(32, 32).toImage().convertToFormat(QImage.Format.Format_ARGB32)
        drawn = sum(1 for y in range(image.height()) for x in range(image.width()) if image.pixelColor(x, y).alpha() > 40)
        images[name] = (drawn, bytes(image.constBits()))
    blank = sorted(n for n, (drawn, _b) in images.items() if drawn < 20)
    by_bits: dict = {}
    for name, (_drawn, bits) in images.items():
        by_bits.setdefault(bits, []).append(name)
    same = [names for names in by_bits.values() if len(names) > 1]
    rows.append(["C", not missing and not unknown and not twice and not blank and not same,
                 f"{len(set(on_ribbon))} actions on the ribbon + {len(RIBBON_EXCLUDED)} excluded of {len(declared)}; "
                 f"missing {missing}, unknown {unknown}, twice {twice}; blank icons {blank}; identical icons {same}"])

    # B -- every ribbon button reaches its own action (spied, so no dialog opens)
    reached: dict = {}
    wrong = []
    for name, button in ribbon.buttons.items():
        action = actions[name]
        if action.isCheckable():
            continue
        action.trigger = lambda n=name: reached.setdefault(n, 0) or reached.__setitem__(n, 1)
        button.click()
        del action.trigger
        if reached.get(name) != 1:
            wrong.append(name)
    checked = [n for n in ribbon.buttons if not actions[n].isCheckable()]
    rows.append(["B", len(checked) >= 38 and not wrong,
                 f"{len(checked)} ribbon buttons clicked; each reached its own action: {not wrong} {wrong[:5]}"])

    # R -- Show Rays, one state
    rays = actions["show_rays"]
    button = ribbon.buttons["show_rays"]
    start = rays.isChecked()
    QTest.mouseClick(button, Qt.MouseButton.LeftButton)
    app.processEvents()
    ray_actors = list(window.viewport.ray_actors) if window.viewport is not None else []
    visible = sorted({bool(actor.GetVisibility()) for actor in ray_actors})
    after_click = (rays.isChecked(), button.isChecked(), visible)
    rays.trigger()                              # the menu's route
    app.processEvents()
    after_menu = (rays.isChecked(), button.isChecked())
    rows.append(["R", after_click[0] == (not start) and after_click[1] == (not start)
                 and bool(ray_actors) and after_click[2] == [not start] and after_menu == (start, start),
                 f"ribbon click -> action {after_click[0]}, button {after_click[1]}, the {len(ray_actors)} ray "
                 f"actors visible {after_click[2]}; "
                 f"menu trigger -> action/button {after_menu} (started {start})"])

    # A -- the plot picker
    bar = window.analysis_toolbar
    picker = ribbon.plot_picker_docked
    from KrakenOS.UI.analysis_modes import MODE_GROUPS

    mode = MODE_GROUPS[0][0][1]
    before = picker.text()
    window.editor.toggle_analysis_mode(mode)
    app.processEvents()
    caption_on, bar_on = picker.text(), bar.button.text()
    window.editor.toggle_analysis_mode(mode)
    app.processEvents()
    rows.append(["A", picker.menu() is bar.menu and caption_on == bar_on and caption_on != before
                 and picker.text() == bar.button.text() == before,
                 f"same menu: {picker.menu() is bar.menu}; caption {before!r} -> {caption_on!r} (the toolbar: "
                 f"{bar_on!r}) -> {picker.text()!r} as the model's selection changed"])

    # P -- the palette
    window.raise_()
    window.activateWindow()
    active = QTest.qWaitForWindowActive(window, 3000)   # a shortcut only fires in the active window
    target = app.focusWidget() or window
    QTest.keyClick(target, Qt.Key.Key_P, Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
    app.processEvents()
    focused = ribbon.palette.hasFocus() or app.focusWidget() is ribbon.palette
    ran = []
    actions["gaussian_beam"].trigger = lambda: ran.append("gaussian_beam")
    matched = ribbon.run_command("gaussian beam")
    del actions["gaussian_beam"].trigger
    ambiguous = ribbon.match("report")
    rows.append(["P", focused and matched == "gaussian_beam" and ran == ["gaussian_beam"] and ambiguous is None,
                 f"Ctrl+Shift+P focuses the palette: {focused} (window active {active}); 'gaussian beam' ran {ran}; 'report' matches {ambiguous}"])

    # F -- folded on a short screen, the pop-up
    screen_height = window.screen().availableGeometry().height()
    popup = ribbon.show_popup(0)
    settle(0.3)
    shown = popup.isVisible()
    popup_button = next(b for b in popup.findChildren(type(button)) if b.text() == "Redraw")
    actions["redraw"].trigger = lambda: None
    popup_button.click()
    del actions["redraw"].trigger
    app.processEvents()
    ribbon_was_folded = ribbon.collapsed
    rows.append(["F", (screen_height >= 1100 or ribbon.collapsed) and view.widget.height() >= 400
                 and shown and not popup.isVisible(),
                 f"screen {screen_height} px: folded={ribbon.collapsed}; 3D view {view.widget.height()} px; "
                 f"pop-up shown {shown}, closed after a command: {not popup.isVisible()}"])

    def visible_pages() -> list:
        return [i for i in range(ribbon.tabs.count()) if ribbon.tabs.widget(i).isVisible()]

    # D -- undock / dock
    from PySide6.QtCore import Qt as _Qt

    view_docked = view.widget.height()
    folded_height = ribbon.dock.height()
    ribbon.tabs.setCurrentIndex(2)
    ribbon.set_floating(True)
    settle(0.6)
    floating = (ribbon.dock.isFloating(), visible_pages(), ribbon.collapsed)
    ribbon.set_floating(False)
    settle(0.6)
    redocked = (ribbon.dock.isFloating(), window.dockWidgetArea(ribbon.dock) == _Qt.DockWidgetArea.TopDockWidgetArea,
                ribbon.collapsed, ribbon.dock.height(), view.widget.height())
    rows.append(["D", floating[0] and floating[1] == [2] and not floating[2]
                 and not redocked[0] and redocked[1] and redocked[2] == ribbon_was_folded
                 and redocked[3] == folded_height and redocked[4] == view_docked,
                 f"floating={floating[0]}, pages visible {floating[1]} (current 2), unfolded={not floating[2]}; docked "
                 f"again at the top={redocked[1]}, folded={redocked[2]}, height {redocked[3]} (was {folded_height}), "
                 f"3D view {redocked[4]} (was {view_docked})"])

    # U -- unfold / fold while docked
    ribbon.set_collapsed(False)
    settle(0.4)
    unfolded = visible_pages()
    ribbon.set_collapsed(True)
    settle(0.4)
    rows.append(["U", unfolded == [ribbon.tabs.currentIndex()] and visible_pages() == [],
                 f"unfolded: pages visible {unfolded} (current {ribbon.tabs.currentIndex()}); folded: {visible_pages()}"])

    # T -- the surface table across the top
    table = window.dock_manager["SurfaceTableDock"]
    inspector_dock = window.dock_manager["InspectorDock"]
    top = window.dockWidgetArea(table) == _Qt.DockWidgetArea.TopDockWidgetArea
    order = (ribbon.dock.geometry().bottom() <= table.geometry().top()
             and table.geometry().bottom() <= inspector_dock.geometry().top())
    full = table.width() >= window.width() - 4
    rows.append(["T", top and order and full,
                 f"table in the top area={top}; ribbon < table < inspector top-to-bottom={order}; "
                 f"width {table.width()} of the window's {window.width()}"])
    return rows


def _run() -> list:
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
        "from KrakenOS.UI.validate_qt_ribbon import qt_runtime_checks\n"
        # flushed, then exit WITHOUT interpreter teardown (a VTK/Qt teardown crash must not lose it)
        f"print({RESULT_MARK!r} + json.dumps(qt_runtime_checks()), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True, timeout=1200,
                              env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return [["X", False, "timed out"]]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return [["X", True, line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
    return [["X", False, f"exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    if not SCENE.exists():
        return True, [f"SKIP = {SCENE} absent"]
    rows = _run()
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
