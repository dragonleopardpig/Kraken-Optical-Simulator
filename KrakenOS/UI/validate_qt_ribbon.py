"""Guard for the Qt shell's ribbon + command palette (bugs/0935). In a real Qt shell on om05a_folded:

  M  (bugs/0949) the ribbon is the ONLY command surface: the window has no menu bar, and it opens
     on the Home tab (File is first, as in a ribbon, but not the everyday one)
  C  the ribbon's buttons and dropdown lists reach every one of the shell's `ACTIONS` exactly once
     (a new action cannot go missing), and every button and dropdown has an icon that draws pixels
     -- no two render the same
  L  (bugs/0949) each dropdown button lists exactly its declared commands, in order -- the shell's
     own action objects, so an entry is the same call as a button -- and opens on a plain click
  K  (bugs/0949) shortcuts work without a menu bar: F5 runs Redraw once, Ctrl+L flips Show Rays
  W  the window's minimum width stays under 1240 px (the tolerance reports once made it ~1500)
  B  each ribbon button runs ITS OWN action (the click reaches that action's `trigger`); a disabled
     action (Redo with nothing to redo) disables its button too
  R  Show Rays keeps one state: a ribbon click flips the menu action AND really hides the traced
     rays (the viewport's ray actors), and the menu action checks the ribbon button again
  A  the ribbon's plot picker is the analysis picker: it carries the same menu, and its caption
     follows the model's selection
  P  the palette: Ctrl+Shift+P focuses it; "gaussian beam" runs the Gaussian Beam Report action;
     a fragment several commands share runs nothing
  F  in a window under 1100 px high the ribbon starts folded (bugs/0963: the WINDOW's height, not the
     screen's) and the 3D view keeps >= 400 px; a tab click drops
     its page as a pop-up, and running a command from it -- a button, or an entry of one of its
     dropdowns -- closes the pop-up
  D  (bugs/0940) the ribbon is a dock: undocked it is a window of its own showing its pages, with
     EXACTLY ONE page visible (unfolding used to show all four drawn over each other); docked
     again it returns to the top area, folded to its tab row, and the 3D view gets its height back
  U  docked and unfolded (double-click a tab), exactly one page shows; folded again, none
  T  (bugs/0940) the surface table is across the TOP of the window -- full width, under the ribbon
     and above the 3D scene (the inspector, central since bugs/0951) -- so its columns show
     without sideways scrolling
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
    from KrakenOS.UI.qt.ribbon import DROPDOWNS, MODEL_MENUS, RIBBON, START_TAB, ribbon_actions, ribbon_entries

    app, window = build(["guard"])
    window.show()
    app.processEvents()
    start_tab = window.ribbon.tabs.tabText(window.ribbon.tabs.currentIndex())
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

    # M -- no menu bar: the ribbon is the one command surface
    from PySide6.QtWidgets import QMenuBar

    menu_bars = len(window.findChildren(QMenuBar)) + (0 if window.menuWidget() is None else 1)
    tabs = [ribbon.tabs.tabText(index) for index in range(ribbon.tabs.count())]
    rows.append(["M", menu_bars == 0 and tabs == [tab for tab, _groups in RIBBON] and tabs[0] == "File"
                 and start_tab == START_TAB == "Home",
                 f"menu bars in the window: {menu_bars}; tabs {tabs}; opens on {start_tab!r}"])

    # C -- coverage, uniqueness, icons that draw and differ
    on_ribbon = [name for _t, _g, name, _s, _l in ribbon_entries()]
    # a third kind of entry since bugs/0972: a button whose menu the MODEL fills (the layouts and
    # examples on disk) -- it holds no actions, but it must be built and have its own icon
    buttons_declared = [name for name in on_ribbon if name not in DROPDOWNS and name not in MODEL_MENUS]
    reached = ribbon_actions()
    declared = [a[0] for a in ACTIONS]
    missing = sorted(set(declared) - set(reached))
    unknown = sorted(set(reached) - set(declared))
    twice = sorted({n for n in reached if reached.count(n) > 1})
    unbuilt = sorted((set(buttons_declared) - set(ribbon.buttons)) | (set(DROPDOWNS) - set(ribbon.dropdowns))
                     | (set(MODEL_MENUS) - set(ribbon.model_menus))
                     | ({name for name in on_ribbon if name.startswith("model:")} - set(MODEL_MENUS)))
    images = {}
    # every BUTTON needs its own icon -- a command's, or a dropdown's; an entry of a list may have none
    faces = [(name, actions[name].icon()) for name in buttons_declared if name in actions]
    faces += [(name, button.icon()) for name, button in ribbon.dropdowns.items()]
    faces += [(name, button.icon()) for name, button in ribbon.model_menus.items()]
    for name, face in faces:
        image = face.pixmap(32, 32).toImage().convertToFormat(QImage.Format.Format_ARGB32)
        drawn = sum(1 for y in range(image.height()) for x in range(image.width()) if image.pixelColor(x, y).alpha() > 40)
        images[name] = (drawn, bytes(image.constBits()))
    blank = sorted(n for n, (drawn, _b) in images.items() if drawn < 20)
    by_bits: dict = {}
    for name, (_drawn, bits) in images.items():
        by_bits.setdefault(bits, []).append(name)
    same = [names for names in by_bits.values() if len(names) > 1]
    rows.append(["C", not missing and not unknown and not twice and not unbuilt and not blank and not same,
                 f"{len(buttons_declared)} buttons + {len(MODEL_MENUS)} model menus + {len(DROPDOWNS)} dropdowns listing "
                 f"{len(reached) - len(buttons_declared)} commands reach {len(set(reached))} of {len(declared)} "
                 f"actions; missing {missing}, unknown {unknown}, twice {twice}, declared but not built {unbuilt}; "
                 f"blank icons {blank}; identical icons {same}"])

    # L -- a dropdown lists its declared commands: the shell's own action objects, in order
    from PySide6.QtWidgets import QToolButton

    wrong_lists = []
    for key, (_about, members) in DROPDOWNS.items():
        button = ribbon.dropdowns.get(key)
        listed = [] if button is None or button.menu() is None else button.menu().actions()
        expected = [None if member is None else actions[member] for member in members]
        got = [None if entry.isSeparator() else entry for entry in listed]
        if (len(got) != len(expected) or any(a is not b for a, b in zip(got, expected))
                or button.popupMode() != QToolButton.ToolButtonPopupMode.InstantPopup):
            wrong_lists.append(key)
    rows.append(["L", len(DROPDOWNS) >= 6 and not wrong_lists,
                 f"{len(DROPDOWNS)} dropdowns {sorted(k.split(':')[1] for k in DROPDOWNS)}; lists that are not "
                 f"their declared action objects in order, or do not open on a click: {wrong_lists}"])

    # B -- every ribbon button reaches its own action (spied, so no dialog opens). A disabled action
    # (Redo with no history, bugs/0942) must disable its button too; enabled, its click still lands
    reached: dict = {}
    wrong = []
    disabled, live_when_disabled = [], []
    for name, button in ribbon.buttons.items():
        action = actions[name]
        if action.isCheckable():
            continue
        was_enabled = action.isEnabled()
        if not was_enabled:
            disabled.append(name)
            if button.isEnabled():
                live_when_disabled.append(name)
            action.setEnabled(True)
        action.trigger = lambda n=name: reached.setdefault(n, 0) or reached.__setitem__(n, 1)
        button.click()
        del action.trigger
        action.setEnabled(was_enabled)
        if reached.get(name) != 1:
            wrong.append(name)
    checked = [n for n in ribbon.buttons if not actions[n].isCheckable()]
    rows.append(["B", len(checked) >= 55 and not wrong and not live_when_disabled,
                 f"{len(checked)} ribbon buttons clicked; each reached its own action: {not wrong} {wrong[:5]}; "
                 f"disabled actions {disabled} -- their buttons disabled too: {not live_when_disabled}"])

    # R -- Show Rays, one state
    rays = actions["show_rays"]
    button = ribbon.buttons["show_rays"]
    start = rays.isChecked()
    QTest.mouseClick(button, Qt.MouseButton.LeftButton)
    app.processEvents()
    ray_actors = list(window.viewport.ray_actors) if window.viewport is not None else []
    visible = sorted({bool(actor.GetVisibility()) for actor in ray_actors})
    after_click = (rays.isChecked(), button.isChecked(), visible)
    rays.trigger()                              # the action's own route (a shortcut, the palette)
    app.processEvents()
    after_menu = (rays.isChecked(), button.isChecked())
    rows.append(["R", after_click[0] == (not start) and after_click[1] == (not start)
                 and bool(ray_actors) and after_click[2] == [not start] and after_menu == (start, start),
                 f"ribbon click -> action {after_click[0]}, button {after_click[1]}, the {len(ray_actors)} ray "
                 f"actors visible {after_click[2]}; "
                 f"action trigger -> action/button {after_menu} (started {start})"])

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

    # K -- shortcuts need no menu bar (the window is active: P waited for it)
    fired = []
    actions["redraw"].triggered.connect(lambda *_a: fired.append("redraw"))
    rays_before = rays.isChecked()
    target = app.focusWidget() or window
    QTest.keyClick(target, Qt.Key.Key_F5)
    QTest.keyClick(target, Qt.Key.Key_L, Qt.KeyboardModifier.ControlModifier)
    app.processEvents()
    rays_flipped = rays.isChecked() != rays_before
    QTest.keyClick(target, Qt.Key.Key_L, Qt.KeyboardModifier.ControlModifier)
    app.processEvents()
    rows.append(["K", fired == ["redraw"] and rays_flipped and rays.isChecked() == rays_before,
                 f"F5 ran Redraw {len(fired)} time(s); Ctrl+L flipped Show Rays: {rays_flipped}, and back: "
                 f"{rays.isChecked() == rays_before} (window active {active})"])

    # W -- the ribbon does not force a wide window
    widest = max(range(ribbon.tabs.count()), key=lambda index: ribbon.tabs.widget(index).minimumSizeHint().width())
    rows.append(["W", window.minimumSizeHint().width() <= 1240,
                 f"window minimum width {window.minimumSizeHint().width()} px; the widest tab is "
                 f"{ribbon.tabs.tabText(widest)!r} at {ribbon.tabs.widget(widest).minimumSizeHint().width()} px"])

    # F -- folded on a short screen, the pop-up
    window_height = window.height()
    popup = ribbon.show_popup(tabs.index("Home"))
    settle(0.3)
    shown = popup.isVisible()
    popup_button = next(b for b in popup.findChildren(type(button)) if b.text() == "Redraw")
    actions["redraw"].trigger = lambda: None
    popup_button.click()
    del actions["redraw"].trigger
    app.processEvents()
    closed_by_button = not popup.isVisible()
    # ... and an entry of a dropdown on a pop-up page: Analysis > More > Clear Marks
    more_popup = ribbon.show_popup(tabs.index("Analysis"))
    settle(0.3)
    more_shown = more_popup.isVisible()
    more_button = next(b for b in more_popup.findChildren(type(button)) if b.text() == "More")
    listed = more_button.menu().actions()
    next(entry for entry in listed if entry is actions["clear_marks"]).trigger()
    app.processEvents()
    closed_by_entry = not more_popup.isVisible()
    ribbon_was_folded = ribbon.collapsed
    rows.append(["F", (window_height >= 1100 or ribbon.collapsed) and view.widget.height() >= 400
                 and shown and closed_by_button and more_shown and closed_by_entry,
                 f"window {window_height} px high: folded={ribbon.collapsed}; 3D view {view.widget.height()} px; "
                 f"pop-up shown {shown}, closed after a button's command: {closed_by_button}; the Analysis "
                 f"pop-up shown {more_shown}, closed after a dropdown entry (More > Clear Marks): {closed_by_entry}"])

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
    scene = window.scene_stack.geometry()          # the central 3D scene, in window coordinates
    top = window.dockWidgetArea(table) == _Qt.DockWidgetArea.TopDockWidgetArea
    order = (ribbon.dock.geometry().bottom() <= table.geometry().top()
             and table.geometry().bottom() <= scene.top()
             and window.scene_stack.currentWidget() is window.inspector_host)
    # full width between the edge strips that carry the panels' tabs (bugs/0952)
    strips = sum(window.dock_manager.rails.rails[edge].width() for edge in ("left", "right")
                 if window.dock_manager.rails.rails[edge].isVisible())
    full = table.width() >= window.width() - strips - 4
    rows.append(["T", top and order and full,
                 f"table in the top area={top}; ribbon < table < the 3D scene top-to-bottom={order}; "
                 f"width {table.width()} of the window's {window.width()} less {strips} px of edge strips"])
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
