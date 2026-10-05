"""Guard for bugs/0961: tabbed toolbars that hide, Hide All Panels, and a clean 3D scene in one click.

User, 2026-10-05: "Please make all toolbars tabbed and can be hide/unhide. Give user chance to have
big clean 3D scene. Also, the side tabs, can have 'one click hide all' option?"

In a real Qt shell on the two-arm doublets example (in git), driven by real clicks and keys:

  T  the 3D scene's View / Scene / Carry toolbars are ONE strip of tabs, at most 40 px tall (three
     stacked rows took 96): a tab click shows that row and no other; every control sits on its own
     row's tab; a row too long for the scene puts its end behind the toolbar's >> button instead of
     widening the window, and a row's hint text comes after its controls
  H  the strip's arrow hides it -- the scene gains its height -- and the 3D Toolbar switch brings it
     back
  A  Hide All Panels, clicked on an edge's tab strip, puts every open panel away and the scene takes
     their room; clicked again (on another edge) it brings back the SAME panels, the same tab in
     front of each stack, each stack at its size; the switch reads "on" whenever no panel is open,
     also when they were closed one by one, and Ctrl+Shift+H then shows them all
  C  Clean 3D Scene: F11 folds the ribbon, hides the 3D toolbar and every panel -- the scene gets
     at least 85 % of the window (the rest: the ribbon's tab row, the side tab strips, the status
     line -- 90 % measured at 1500x950 since the top edge's tab left its own 30-36 px row, E); the button by the ribbon's fold arrow shows it is on; clicked, it
     puts back what it put away: the ribbon unfolded again, the toolbar, the panels at their sizes --
     a panel closed BEFORE stays closed, one opened DURING stays open, even after Hide All was used
     in between
  E  (bugs/0962) the top edge's tab strip rides in the ribbon's tab row -- no row of its own above
     the window -- no taller than that row; its Surface Table tab still hides the table (the scene
     takes its height) and brings it back; undocked, the ribbon leaves the strip at the window's
     top edge, and docked again takes it back, the scene at the height it had
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "CLEANSCENE_RESULT "
SKIP_MARK = "CLEANSCENE_SKIP "
SCENE = Path("KrakenOS/common_optical_layouts/beam_splitter_two_arm_doublets.py")


def qt_runtime_checks() -> dict:
    import time

    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QLabel, QToolButton

    from KrakenOS.UI import open3d_toolbar as catalogue
    from KrakenOS.UI.qt.app import build

    app, window = build(["guard"])
    window.show()
    app.processEvents()
    view = window.build_scene()
    window.load_layout_path(SCENE)
    rows = []

    def settle(seconds: float = 0.4) -> None:
        end = time.time() + seconds
        while time.time() < end:
            app.processEvents()
            time.sleep(0.02)

    def activate() -> None:
        end = time.time() + 3.0
        while time.time() < end and QApplication.activeWindow() is not window:
            window.raise_()
            window.activateWindow()
            settle(0.1)

    settle(2.5)
    if window._scene_inspector() is None:
        return {"rows": [["X", True, "SKIP: the embedded 3D inspector is unavailable"]]}
    strip, scene, rails = view.toolbar, view.widget, window.dock_manager.rails
    actions = window.action_manager
    docks = list(window.dock_manager.docks.values())

    def scene_size() -> tuple:
        settle(0.3)
        return (scene.width(), scene.height())

    def open_names() -> list:
        return sorted(dock.objectName() for dock in docks if not dock.isHidden())

    def front_sizes() -> dict:
        return {dock.objectName(): (dock.width(), dock.height()) for dock in docks if rails.is_front(dock)}

    def close_to(before: dict, after: dict, tol: int = 3) -> bool:
        return before.keys() == after.keys() and all(
            abs(before[k][0] - after[k][0]) <= tol and abs(before[k][1] - after[k][1]) <= tol for k in before)

    # ---- T: one strip of tabs -------------------------------------------------------------------
    tabs, pages = strip.tabs, strip.pages
    titles = [tabs.tabText(i) for i in range(tabs.count())]
    shown_after_click = []
    for index in range(tabs.count()):
        QTest.mouseClick(tabs, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                         tabs.tabRect(index).center())
        settle(0.1)
        shown_after_click.append([page_index for page_index in range(pages.count())
                                  if pages.widget(page_index).isVisible()])
    QTest.mouseClick(tabs, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, tabs.tabRect(0).center())
    misplaced = []
    for row_index, row in enumerate(catalogue.ROWS):
        page = pages.widget(row_index)
        for item in row.left + row.right:
            label = getattr(item, "textvar", None) if isinstance(item, catalogue.Toggle) else getattr(item, "label", None)
            widget = strip.controls.get(label) if label else None
            if widget is not None and hasattr(widget, "parentWidget") and not page.isAncestorOf(widget):
                misplaced.append(label)
    view_bar = pages.widget(0)
    extension = view_bar.findChild(QToolButton, "qt_toolbar_ext_button")
    overflow = extension is not None and extension.isVisible()
    screen_width = window.screen().availableGeometry().width()
    carry = pages.widget([r.title for r in catalogue.ROWS].index("Carry"))
    carry_widgets = [carry.widgetForAction(a) for a in carry.actions() if carry.widgetForAction(a) is not None]
    hint_first = bool(carry_widgets) and isinstance(carry_widgets[0], QLabel) and len(carry_widgets[0].text()) > 30
    rows.append(["T", titles == [r.title for r in catalogue.ROWS] and strip.height() <= 40
                 and shown_after_click == [[i] for i in range(tabs.count())] and not misplaced and overflow
                 and window.width() <= screen_width and not hint_first,
                 f"tabs {titles}, strip {strip.height()} px; pages shown after clicking each tab {shown_after_click}; "
                 f"controls off their row's tab {misplaced}; View row in a {scene.width()}-px scene puts its end behind "
                 f">>: {overflow}; window {window.width()} px on a {screen_width}-px screen; Carry starts with its hint: "
                 f"{hint_first}"])

    # ---- H: the strip hides and comes back -----------------------------------------------------
    switch = actions["toolbar_3d"]
    before = scene_size()
    QTest.mouseClick(strip.hide_button, Qt.MouseButton.LeftButton)
    hidden = scene_size()
    hidden_state = (strip.isVisible(), switch.isChecked())
    switch.trigger()
    back = scene_size()
    rows.append(["H", hidden_state == (False, False) and hidden[1] - before[1] >= strip.height() - 2
                 and strip.isVisible() and switch.isChecked() and back == before,
                 f"scene {before} -> arrow {hidden} (strip shown, switch on: {hidden_state}) -> 3D Toolbar switch {back}"])

    # ---- A: Hide All Panels --------------------------------------------------------------------
    hide_all = actions["hide_panels"]
    opened, fronts, sizes, start = open_names(), sorted(front_sizes()), front_sizes(), scene_size()
    QTest.mouseClick(rails.hide_all_buttons["left"], Qt.MouseButton.LeftButton)
    after_hide, hide_scene, hide_checked = open_names(), scene_size(), hide_all.isChecked()
    QTest.mouseClick(rails.hide_all_buttons["right"], Qt.MouseButton.LeftButton)
    settle(0.5)
    after_show, show_fronts, show_sizes, show_scene = open_names(), sorted(front_sizes()), front_sizes(), scene_size()
    # one by one through the edges' own tabs, then the key
    for _ in range(12):
        front = next((dock for dock in docks if rails.is_front(dock)), None)
        if front is None:
            break
        rails.toggle(front)
        settle(0.1)
    one_by_one = (open_names(), hide_all.isChecked())
    activate()
    QTest.keyClick(app.focusWidget() or window, Qt.Key.Key_H, Qt.KeyboardModifier.ControlModifier
                   | Qt.KeyboardModifier.ShiftModifier)
    settle(0.5)
    by_key = (len(open_names()), hide_all.isChecked())
    rows.append(["A", after_hide == [] and hide_checked and hide_scene[0] > start[0] + 200 and hide_scene[1] > start[1] + 100
                 and after_show == opened and show_fronts == fronts and close_to(sizes, show_sizes)
                 and show_scene == start and one_by_one == ([], True) and by_key == (len(docks), False),
                 f"open {len(opened)} panels, scene {start}; the left strip's Hide All: open {after_hide}, switch on "
                 f"{hide_checked}, scene {hide_scene}; the right strip's: the same {len(after_show)} back {after_show == opened}, "
                 f"same fronts {show_fronts == fronts}, stack sizes {sizes} -> {show_sizes}, scene {show_scene}; closed one "
                 f"by one: open {one_by_one[0]}, switch on {one_by_one[1]}; Ctrl+Shift+H: {by_key[0]} of {len(docks)} "
                 f"open, switch on {by_key[1]}"])

    # ---- C: Clean 3D Scene ----------------------------------------------------------------------
    ribbon = window.ribbon
    ribbon.set_collapsed(False)
    debug, progress = window.dock_manager["DebugDock"], window.dock_manager["ProgressDock"]
    rails.toggle(debug)                                   # closed BEFORE: must stay closed
    settle(0.2)
    rails.toggle(progress)                                # closed before, opened DURING: stays open
    settle(0.5)
    window.fit_side_docks()
    settle(0.5)
    before_open, before_sizes, before_scene = open_names(), front_sizes(), scene_size()
    activate()
    scene.setFocus()
    settle(0.1)
    QTest.keyClick(scene, Qt.Key.Key_F11)
    clean_scene = scene_size()
    clean_state = {"ribbon folded": ribbon.collapsed, "toolbar shown": strip.isVisible(), "open": open_names(),
                   "corner button on": ribbon.clean_button.isChecked()}
    share = clean_scene[0] * clean_scene[1] / float(window.width() * window.height())
    rails.toggle(progress)
    settle(0.3)
    # and Hide All twice in between: its memory is spent, so only Clean's own record can put the
    # right panels back (showing "every closed panel" would bring Debug back too)
    for _ in range(2):
        QTest.keyClick(app.focusWidget() or window, Qt.Key.Key_H, Qt.KeyboardModifier.ControlModifier
                       | Qt.KeyboardModifier.ShiftModifier)
        settle(0.3)
    QTest.mouseClick(ribbon.clean_button, Qt.MouseButton.LeftButton)
    settle(0.6)
    restored = {"ribbon folded": ribbon.collapsed, "toolbar shown": strip.isVisible(), "open": open_names(),
                "corner button on": ribbon.clean_button.isChecked()}
    after_sizes = front_sizes()

    def depths(sizes: dict) -> dict:
        """How far each panel reaches into the scene: its height on the top and bottom edges, its
        width on the sides. (Its length along the edge changes when a neighbour comes back, as
        Progress does here.)"""
        found = {}
        for name, (width, height) in sizes.items():
            edge = rails.edge_of(window.dock_manager[name])
            found[name] = (0, height) if edge in ("top", "bottom") else (width, 0)
        return found

    kept_sizes = {name: after_sizes[name] for name in before_sizes if name in after_sizes}
    before_sizes, kept_sizes = depths(before_sizes), depths(kept_sizes)
    rows.append(["C", clean_state == {"ribbon folded": True, "toolbar shown": False, "open": [], "corner button on": True}
                 and share >= 0.85 and "DebugDock" not in before_open and "ProgressDock" not in before_open
                 and restored == {"ribbon folded": False, "toolbar shown": True,
                                  "open": sorted(before_open + ["ProgressDock"]), "corner button on": False}
                 and close_to(before_sizes, kept_sizes),
                 f"before: scene {before_scene}, open {len(before_open)} (Debug and Progress closed: "
                 f"{'DebugDock' not in before_open and 'ProgressDock' not in before_open}); F11: {clean_state}, scene "
                 f"{clean_scene} = {share:.0%} of the window; Progress opened during, Ctrl+Shift+H twice; the corner "
                 f"button: {restored}, depth into the scene {before_sizes} -> {kept_sizes}, scene {scene_size()}"])

    # ---- E: the top edge's tabs in the ribbon's tab row (bugs/0962) ---------------------------
    from PySide6.QtWidgets import QToolBar

    top = rails.rails["top"]
    tab = rails.tabs["SurfaceTableDock"]
    table = window.dock_manager["SurfaceTableDock"]
    bar = ribbon.tabs.tabBar()

    def own_rows() -> list:
        return [strip.objectName() for strip in window.findChildren(QToolBar)
                if strip.parentWidget() is window and strip.isVisible()
                and window.toolBarArea(strip) == Qt.ToolBarArea.TopToolBarArea]

    def placed() -> dict:
        settle(0.3)
        return {"in ribbon row": ribbon.tabs.isAncestorOf(top), "shown": top.isVisible(),
                "rows above the window": own_rows(),
                "top y": top.mapTo(window, top.rect().topLeft()).y(),
                "row y": bar.mapTo(window, bar.rect().topLeft()).y()}

    docked = placed()
    fits = top.height() <= bar.height()
    height = scene_size()[1]
    QTest.mouseClick(tab, Qt.MouseButton.LeftButton)
    hidden = (table.isHidden(), scene_size()[1] - height)
    QTest.mouseClick(tab, Qt.MouseButton.LeftButton)
    shown = (table.isHidden(), scene_size()[1] - height)
    ribbon.set_floating(True)
    floating = placed()
    ribbon.set_floating(False)
    settle(0.6)
    redocked, height_back = placed(), scene_size()[1]
    rows.append(["E", docked["in ribbon row"] and docked["shown"] and docked["rows above the window"] == []
                 and abs(docked["top y"] - docked["row y"]) <= 2 and fits
                 and hidden[0] and hidden[1] >= table.height() - 12 and shown == (False, 0)
                 and not floating["in ribbon row"] and floating["shown"] and floating["top y"] <= 2
                 and floating["rows above the window"] == ["EdgeRailTop"]
                 and redocked["in ribbon row"] and redocked["rows above the window"] == [] and height_back == height,
                 f"docked: {docked}, strip {top.height()} px in a {bar.height()}-px row; its Surface Table tab: "
                 f"table hidden {hidden[0]}, scene {hidden[1]:+d} px, then {shown}; ribbon undocked: {floating}; "
                 f"docked again: {redocked}, scene {height} -> {height_back} px high"])
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
        "from KrakenOS.UI.validate_qt_clean_scene import qt_runtime_checks\n"
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
    rows = _run("qt_runtime_checks()")
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
