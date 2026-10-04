"""Guard for bugs/0951 + bugs/0952: one 3D scene in the centre, and edge tabs to hide the panels.

Reported 2026-10-04: "the Nav Cube is missing in 3D scene", and the panels on the four edges "are
overlapping each other". Both had one cause: the shell opened on a bare PREVIEW of the scene in the
centre, and put the real inspector -- the one with the Nav Cube -- in a dock above it, which crushed
the preview and the side panels into a 112-px band. In a real Qt shell on om05a_folded:

  C  the window opens on ONE 3D scene: the real inspector is the central widget's page on show, no
     preview viewport is built beside it, and no dock holds it
  N  the Nav Cube is drawn: its corner viewport is the top-right of the scene and pixel-square, and
     the pixels there change when the cube's renderers are switched off (a self-controlled read)
  L  nothing is crushed or overlapping with every panel open: the panels sit left of, right of,
     above and below the scene; no two panels on show intersect; the scene is at least 400 px high
  S  the scene is the LAST thing to shrink: with every panel open and the window at its narrowest,
     the 3D view keeps its minimum width (its readouts and the Nav Cube do not shrink, so a
     narrower view runs them off the edge -- what phase 706 caught)
  V  the ribbon's view commands drive that scene: Show Rays and the inspector's own box are one
     switch (either way), Fit Scene frames it again after a zoom, Redraw refreshes it
  R  (0952) each edge carries one tab per panel docked there -- upright on the left and right, flat
     on the top and bottom, the bottom ones in the status bar -- and a tab is down exactly while its
     panel is on show
  H  a click on a tab hides its panel and gives the room to the scene; a second click brings it
     back. For a tabbed stack: a tab behind comes to the front; the front tab folds the whole
     stack; any tab of a folded stack brings the stack back with that panel in front
  M  a panel moved to another edge takes its tab along, redrawn for that edge; a panel closed by
     its own button lifts its tab
  A  (0952) the small arrow at the end of the ribbon's tab row folds the ribbon and opens it again
     -- up while open, down while folded -- and the height goes to the scene, not the table
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "QTLAYOUT_RESULT "
SKIP_MARK = "QTLAYOUT_SKIP "
SCENE = Path("attachment/om05a_folded.py")
EXPECTED_TABS = {
    "left": ["Scene Components"],
    "right": ["System", "Source", "Trace", "Optimization", "3D Live"],
    "top": ["Surface Table"],
    "bottom": ["Debug", "Progress", "Results"],
}


def qt_runtime_checks() -> list:
    import time

    import numpy as np
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QDockWidget
    from vtkmodules.util.numpy_support import vtk_to_numpy
    from vtkmodules.vtkRenderingCore import vtkWindowToImageFilter

    from KrakenOS.UI.qt.app import build

    app, window = build(["guard"])
    window.show()
    app.processEvents()
    view = window.build_scene()                      # what app.run() does
    window.load_layout_path(SCENE)

    def settle(seconds: float = 0.5) -> None:
        end = time.time() + seconds
        while time.time() < end:
            app.processEvents()
            time.sleep(0.02)

    settle(2.0)
    inspector = view.inspector
    widget = view.widget
    stack = window.scene_stack
    docks = window.dock_manager.docks
    rails = window.dock_manager.rails
    rows = []

    # C -- one 3D scene, central
    holding = [dock.objectName() for dock in window.findChildren(QDockWidget) if dock.isAncestorOf(widget)]
    rows.append(["C", window.centralWidget() is stack and stack.currentWidget() is window.inspector_host
                 and inspector.available and window.viewport is None and not holding
                 and widget.parentWidget() is window.inspector_host,
                 f"central page is the inspector's: {stack.currentWidget() is window.inspector_host}; inspector "
                 f"available {inspector.available}; a preview viewport was built beside it: "
                 f"{window.viewport is not None}; docks holding the 3D view {holding}"])

    # N -- the Nav Cube, by its pixels
    render_window = widget.GetRenderWindow()

    def capture():
        render_window.Render()
        grab = vtkWindowToImageFilter()
        grab.SetInput(render_window)
        grab.SetInputBufferTypeToRGB()
        grab.ReadFrontBufferOff()
        grab.Update()
        image = grab.GetOutput()
        width, height, _depth = image.GetDimensions()
        return vtk_to_numpy(image.GetPointData().GetScalars()).reshape(height, width, -1).astype(int)

    cube = getattr(inspector, "_navigation_cube", None)
    if cube is None or not getattr(cube, "available", False):
        rows.append(["N", False, f"no navigation cube on the hosted inspector ({cube!r})"])
    else:
        x0, y0, x1, y1 = cube._cube_renderer.GetViewport()
        with_cube = capture()
        height, width = with_cube.shape[:2]
        box = (int(y0 * height), int(y1 * height), int(x0 * width), int(x1 * width))
        renderers = [cube._cube_renderer, cube._arrow_renderer]
        for renderer in renderers:
            renderer.SetDraw(0)
        without = capture()
        for renderer in renderers:
            renderer.SetDraw(1)
        render_window.Render()
        region_with = with_cube[box[0]:box[1], box[2]:box[3]]
        region_without = without[box[0]:box[1], box[2]:box[3]]
        changed = float((np.abs(region_with - region_without).max(axis=2) > 24).mean())
        elsewhere = float((np.abs(with_cube - without).max(axis=2) > 24)[:box[0], :box[2]].mean())
        side = (box[3] - box[2], box[1] - box[0])
        rows.append(["N", abs(x1 - 1.0) < 1e-6 and abs(y1 - 1.0) < 1e-6 and abs(side[0] - side[1]) <= 2
                     and side[0] >= 100 and changed > 0.15 and elsewhere < 0.01,
                     f"cube viewport {tuple(round(v, 3) for v in (x0, y0, x1, y1))} = {side[0]}x{side[1]} px in "
                     f"the top-right of a {width}x{height} scene; pixels there that change when the cube is "
                     f"switched off: {changed:.0%} (elsewhere {elsewhere:.1%})"])

    # L -- nothing crushed, nothing overlapping
    def rect_of(item):
        geometry = item.geometry()
        return (geometry.left(), geometry.top(), geometry.right(), geometry.bottom())

    def on_show():
        return {name: dock for name, dock in docks.items() if rails.is_front(dock) and not dock.isFloating()}

    scene = rect_of(stack)
    shown = on_show()
    misplaced = []
    for name, dock in shown.items():
        left, top, right, bottom = rect_of(dock)
        edge = rails.edge_of(dock)
        beside = {"left": right <= scene[0], "right": left >= scene[2], "top": bottom <= scene[1],
                  "bottom": top >= scene[3]}.get(edge, False)
        if not beside or min(dock.width(), dock.height()) < 100:
            misplaced.append((name, edge, (left, top, right, bottom)))
    names = sorted(shown)
    overlapping = []
    for index, first in enumerate(names):
        for second in names[index + 1:]:
            a, b = rect_of(shown[first]), rect_of(shown[second])
            if a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]:
                overlapping.append((first, second))
    rows.append(["L", len(shown) >= 6 and not misplaced and not overlapping and widget.height() >= 400
                 and widget.width() >= 600,
                 f"{len(shown)} panels on show {names}; not beside the scene or under 100 px: {misplaced}; "
                 f"overlapping pairs {overlapping}; the 3D view is {widget.width()}x{widget.height()} px in a "
                 f"{window.width()}x{window.height()} window"])

    # S -- the scene is the last thing to shrink
    size_before = (window.width(), window.height())
    window.resize(window.minimumSizeHint().width(), window.height())
    settle(0.6)
    narrow = (window.width(), widget.width(), sorted(on_show()))
    window.resize(*size_before)
    settle(0.6)
    rows.append(["S", narrow[1] >= window.SCENE_MIN_WIDTH >= 640 and len(narrow[2]) >= 6
                 and abs(widget.width() - stack.width()) <= 2,
                 f"window narrowed to {narrow[0]} px with {len(narrow[2])} panels on show: the 3D view is "
                 f"{narrow[1]} px wide (floor {window.SCENE_MIN_WIDTH}); widened again: {widget.width()} px"])

    # V -- the ribbon's view commands drive the scene
    rays = window.action_manager["show_rays"]
    start = (rays.isChecked(), bool(inspector.show_rays_var.get()))
    rays.trigger()
    settle(0.3)
    after_ribbon = (rays.isChecked(), bool(inspector.show_rays_var.get()))
    inspector.show_rays_var.set(not after_ribbon[1])          # the inspector's own Show rays box
    inspector._on_show_rays_changed()
    settle(0.3)
    after_box = (rays.isChecked(), bool(inspector.show_rays_var.get()))
    camera = inspector._renderer.GetActiveCamera()
    window.reset_camera_action()
    fitted = float(camera.GetParallelScale())
    camera.SetParallelScale(fitted * 3.0)
    zoomed = float(camera.GetParallelScale())
    window.action_manager["reset_camera"].trigger()
    refitted = float(camera.GetParallelScale())
    refreshed = []
    real_refresh = inspector.refresh_from_editor
    inspector.refresh_from_editor = lambda *a, **k: refreshed.append(1)
    window.action_manager["redraw"].trigger()
    del inspector.refresh_from_editor
    assert inspector.refresh_from_editor == real_refresh
    rows.append(["V", start[0] == start[1] and after_ribbon == (not start[0], not start[0])
                 and after_box == (start[0], start[0]) and abs(refitted - fitted) <= 0.02 * fitted
                 and zoomed > 2.5 * fitted and refreshed == [1],
                 f"Show Rays (ribbon action, inspector box): start {start} -> ribbon click {after_ribbon} -> "
                 f"the inspector's box {after_box}; Fit Scene: parallel scale {fitted:.1f}, zoomed out to "
                 f"{zoomed:.1f}, fitted again {refitted:.1f}; Redraw refreshed the inspector {len(refreshed)}x"])

    # R -- the edge tabs
    def tabs_on(edge):
        return [tab for tab in rails.tabs.values() if tab.edge == edge]

    def titles(edge):
        wanted = EXPECTED_TABS[edge]
        return sorted((tab.text() for tab in tabs_on(edge)), key=lambda text: wanted.index(text) if text in wanted else 99)

    found = {edge: titles(edge) for edge in EXPECTED_TABS}
    shapes = {edge: all((tab.height() > tab.width()) == (edge in ("left", "right")) for tab in tabs_on(edge))
              for edge in EXPECTED_TABS}
    strips = {edge: rails.rails[edge] for edge in EXPECTED_TABS}
    at_edge = {
        "left": strips["left"].mapTo(window, strips["left"].rect().topLeft()).x() == 0,
        "right": strips["right"].mapTo(window, strips["right"].rect().topRight()).x() >= window.width() - 2,
        "top": strips["top"].mapTo(window, strips["top"].rect().topLeft()).y() <= 2,
        "bottom": strips["bottom"].window() is window and window.statusBar().isAncestorOf(strips["bottom"]),
    }
    by_title = {tab.text(): tab for tab in rails.tabs.values()}
    dock_of = {dock.windowTitle(): dock for dock in docks.values()}
    wrong_state = sorted(title for title, tab in by_title.items() if tab.isChecked() != rails.is_front(dock_of[title]))
    rows.append(["R", found == EXPECTED_TABS and all(shapes.values()) and all(at_edge.values()) and not wrong_state
                 and all(strip.isVisible() for strip in strips.values()),
                 f"tabs per edge {found}; upright on left/right and flat on top/bottom: {shapes}; each strip on "
                 f"its window edge (the bottom one in the status bar): {at_edge}; tabs whose down-state is not "
                 f"their panel's: {wrong_state}"])

    # H -- hide and show
    def click(title: str) -> None:
        QTest.mouseClick(by_title[title], Qt.MouseButton.LeftButton)
        settle(0.4)

    def front(title: str) -> bool:
        return rails.is_front(dock_of[title])

    width_before = stack.width()
    left_width = dock_of["Scene Components"].width()
    click("Scene Components")
    hidden = (front("Scene Components"), by_title["Scene Components"].isChecked(), stack.width() - width_before)
    click("Scene Components")
    back = (front("Scene Components"), by_title["Scene Components"].isChecked(), stack.width() - width_before)
    stack_titles = EXPECTED_TABS["right"]
    first_front = [title for title in stack_titles if front(title)]
    click("Trace")                                       # behind another tab: comes to the front
    raised = ([title for title in stack_titles if front(title)],
              [title for title in stack_titles if dock_of[title].isHidden()])
    width_open = stack.width()
    click("Trace")                                       # in front: the whole stack folds
    folded = ([title for title in stack_titles if not dock_of[title].isHidden()], stack.width() - width_open)
    click("Source")                                      # any tab of the folded stack opens it again
    reopened = ([title for title in stack_titles if front(title)],
                [title for title in stack_titles if dock_of[title].isHidden()])
    click("Debug")                                       # side by side, not tabbed: only itself
    bottom = {title: front(title) for title in EXPECTED_TABS["bottom"]}
    click("Debug")
    height_before = stack.height()
    table_height = dock_of["Surface Table"].height()
    click("Surface Table")
    table_hidden = (front("Surface Table"), stack.height() - height_before)
    click("Surface Table")
    table_back = (front("Surface Table"), stack.height() - height_before)
    rows.append(["H", hidden[:2] == (False, False) and hidden[2] >= left_width - 12 and back[:2] == (True, True)
                 and abs(back[2]) <= 12 and len(first_front) == 1 and raised == (["Trace"], [])
                 and folded[0] == [] and folded[1] >= 200 and reopened == (["Source"], [])
                 and bottom == {"Debug": False, "Progress": True, "Results": True}
                 and table_hidden[0] is False and table_hidden[1] >= table_height - 12
                 and table_back[0] is True and abs(table_back[1]) <= 12,
                 f"Scene Components ({left_width} px wide): one click -> on show {hidden[0]}, tab down {hidden[1]}, "
                 f"scene {hidden[2]:+d} px; again -> {back[0]}, {back[1]}, {back[2]:+d} px. Right stack (front "
                 f"{first_front}): 'Trace' -> front {raised[0]}, hidden {raised[1]}; 'Trace' again -> still open "
                 f"{folded[0]}, scene {folded[1]:+d} px; 'Source' -> front {reopened[0]}, hidden {reopened[1]}. "
                 f"'Debug' -> {bottom}. Surface Table ({table_height} px): scene {table_hidden[1]:+d} px, then "
                 f"{table_back[1]:+d} px"])

    # M -- a moved panel takes its tab; a closed one lifts it
    debug = dock_of["Debug"]
    window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, debug)
    settle(0.5)
    moved_tab = rails.tabs[debug.objectName()]
    moved = (moved_tab.edge, moved_tab.height() > moved_tab.width(), [tab.text() for tab in tabs_on("bottom")])
    window.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, debug)
    settle(0.5)
    home = rails.tabs[debug.objectName()].edge
    by_title = {tab.text(): tab for tab in rails.tabs.values()}
    progress = dock_of["Progress"]
    progress.close()                                     # the panel's own close button
    settle(0.3)
    closed = (progress.isHidden(), by_title["Progress"].isChecked())
    click("Progress")
    rows.append(["M", moved == ("left", True, ["Progress", "Results"]) and home == "bottom"
                 and closed == (True, False) and front("Progress") and by_title["Progress"].isChecked(),
                 f"Debug docked on the left: its tab is on the {moved[0]!r} strip, upright {moved[1]}, the bottom "
                 f"strip keeps {moved[2]}; docked back: {home!r}. Progress closed by its own button: hidden "
                 f"{closed[0]}, tab down {closed[1]}; its tab brings it back: {front('Progress')}"])

    # A -- the ribbon's fold arrow
    ribbon = window.ribbon
    window.resize(window.width(), window.height())
    ribbon.set_collapsed(False)
    settle(0.5)
    arrow = ribbon.fold_button
    open_state = (ribbon.collapsed, arrow.arrowType() == Qt.ArrowType.UpArrow, ribbon.dock.height(), stack.height(),
                  dock_of["Surface Table"].height())
    QTest.mouseClick(arrow, Qt.MouseButton.LeftButton)
    settle(0.5)
    folded_state = (ribbon.collapsed, arrow.arrowType() == Qt.ArrowType.DownArrow, ribbon.dock.height(),
                    stack.height(), dock_of["Surface Table"].height())
    QTest.mouseClick(arrow, Qt.MouseButton.LeftButton)
    settle(0.5)
    again = (ribbon.collapsed, arrow.arrowType() == Qt.ArrowType.UpArrow, ribbon.dock.height(), stack.height(),
             dock_of["Surface Table"].height())
    given = open_state[2] - folded_state[2]
    in_tab_row = ribbon.tabs.isAncestorOf(arrow) and arrow.isVisible() and arrow.width() <= 24
    rows.append(["A", open_state[:2] == (False, True) and folded_state[:2] == (True, True) and again[:2] == (False, True)
                 and given >= 60 and abs((folded_state[3] - open_state[3]) - given) <= 6
                 and abs(folded_state[4] - open_state[4]) <= 2 and abs(again[3] - open_state[3]) <= 6 and in_tab_row,
                 f"arrow in the tab row {in_tab_row}; open: ribbon {open_state[2]} px, scene {open_state[3]}, table "
                 f"{open_state[4]}; one click -> folded {folded_state[0]}, arrow down {folded_state[1]}, ribbon "
                 f"{folded_state[2]}, scene {folded_state[3]} ({folded_state[3] - open_state[3]:+d}), table "
                 f"{folded_state[4]}; again -> open, scene {again[3]}"])
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
        "from KrakenOS.UI.validate_qt_scene_layout import qt_runtime_checks\n"
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
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-6:]
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
