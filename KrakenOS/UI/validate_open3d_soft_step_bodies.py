"""Guard for bugs/0958: imported STEP hardware can be drawn SOFT, and the Qt shell's scene does.

Flagged 2026-10-04 (flag_20261004_165652_107): "the 3D scene now back to TK. Previous QT, those STEP
files drawn nicer look". Since bugs/0951 the Qt shell's 3D scene is the real inspector, which
outlines every imported STEP body with two passes of its feature edges (2.8 px and 2.0 px, the
glass palette). On a vendor camera or lens barrel that is a dense dark web. The shell's first 3D
view drew the same bodies as plain smooth solids.

  P  pure: `step_overlay_style` -- off: the body as given, flat-shaded, the two glass passes; on: a
     denser smooth body and ONE thin faint pass
  Q  in the Qt shell the switch is ON by default; each imported STEP body is smooth, at least 0.45
     opaque, with one soft edge actor and no glass-palette edge actor; Overlays > Soft STEP bodies
     (the real menu action) switches to the outlined look -- flat body, the two glass passes -- and
     back
  E  the edges stay DRAWN in the soft style (Alt-hover picks the nearest drawn edge): the soft edge
     actor has exactly the points of each outlined pass
  I  by the picture: the rendered scene has far fewer dark-teal outline pixels soft than outlined
  T  the Tk app is unchanged: the switch is OFF by default there, a STEP body carries the two glass
     passes, and the Overlays menu offers the same switch
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "SOFTSTEP_RESULT "
SKIP_MARK = "SOFTSTEP_SKIP "
SCENE = Path("attachment/machine_vision_Pyrite90_0.3X.py")
ENTRY = "Overlays/Soft STEP bodies"


def pure_checks() -> list:
    from types import SimpleNamespace

    from KrakenOS.UI.services import open3d_scene_refresh as refresh

    class Var:
        def __init__(self, value):
            self.value = value

        def get(self):
            return self.value

    style = refresh.step_overlay_style
    absent = style(SimpleNamespace(), 0.26)
    off = style(SimpleNamespace(soft_step_bodies_var=Var(False)), 0.26)
    on = style(SimpleNamespace(soft_step_bodies_var=Var(True)), 0.26)
    dense = style(SimpleNamespace(soft_step_bodies_var=Var(True)), 0.60)
    glass = ((refresh._OPTICAL_STEP_SILHOUETTE_COLOR, 0.98, refresh._GLASS_EDGE_SILHOUETTE_WIDTH),
             (refresh._OPTICAL_STEP_EDGE_COLOR, 0.96, refresh._GLASS_EDGE_LINE_WIDTH))
    soft = ((refresh._SOFT_STEP_EDGE_COLOR, refresh._SOFT_STEP_EDGE_OPACITY, refresh._SOFT_STEP_EDGE_WIDTH),)
    return [["P", absent == off == (0.26, True, glass) and on == (refresh._SOFT_STEP_BODY_OPACITY, False, soft)
             and dense == (0.60, False, soft) and refresh._SOFT_STEP_EDGE_WIDTH <= 1.2
             and refresh._SOFT_STEP_EDGE_OPACITY < 0.8,
             f"off (or no switch): body {off[0]}, flat {off[1]}, {len(off[2])} passes at widths "
             f"{[p[2] for p in off[2]]}; on: body {on[0]}, flat {on[1]}, {len(on[2])} pass(es) at widths "
             f"{[p[2] for p in on[2]]} and opacities {[p[1] for p in on[2]]}; a body already denser keeps its "
             f"opacity ({dense[0]})"]]


def _close(a, b, tol: float = 0.02) -> bool:
    return all(abs(float(x) - float(y)) <= tol for x, y in zip(a, b))


def _describe(inspector, label: str) -> dict:
    """The actors of one imported STEP body, by what they are."""
    from KrakenOS.UI.services import open3d_scene_refresh as refresh

    found = {"soft_edges": [], "glass_silhouettes": [], "glass_edges": [], "body": None}
    body_key = None
    for key in (inspector.__dict__.get("_step_actor_map", {}) or {}).get(label, []) or []:
        body_key = key
    for key in sorted(inspector._all_actor_keys_for_step_label(label), key=str):
        actor = inspector._actor_by_key.get(key)
        if actor is None:
            continue
        prop = actor.GetProperty()
        color, width = tuple(float(c) for c in prop.GetColor()), float(prop.GetLineWidth())
        points = int(actor.GetMapper().GetInput().GetNumberOfPoints()) if actor.GetMapper() is not None else 0
        if key == body_key:
            found["body"] = {"opacity": round(float(prop.GetOpacity()), 3), "flat": int(prop.GetInterpolation()) == 0}
        elif _close(color, refresh._SOFT_STEP_EDGE_COLOR) and abs(width - refresh._SOFT_STEP_EDGE_WIDTH) < 0.05:
            found["soft_edges"].append(points)
        elif _close(color, refresh._OPTICAL_STEP_SILHOUETTE_COLOR) and abs(width - refresh._GLASS_EDGE_SILHOUETTE_WIDTH) < 0.05:
            found["glass_silhouettes"].append(points)
        elif _close(color, refresh._OPTICAL_STEP_EDGE_COLOR) and abs(width - refresh._GLASS_EDGE_LINE_WIDTH) < 0.05:
            found["glass_edges"].append(points)
    return found


def _outline_pixels(render_window) -> int:
    """Dark-teal pixels: the glass-palette outline strokes."""
    from vtkmodules.util.numpy_support import vtk_to_numpy
    from vtkmodules.vtkRenderingCore import vtkWindowToImageFilter

    render_window.Render()
    grab = vtkWindowToImageFilter()
    grab.SetInput(render_window)
    grab.SetInputBufferTypeToRGB()
    grab.ReadFrontBufferOff()
    grab.Update()
    image = grab.GetOutput()
    width, height, _depth = image.GetDimensions()
    arr = vtk_to_numpy(image.GetPointData().GetScalars()).reshape(height, width, -1).astype(int)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    return int(((r < 60) & (g > 55) & (g < 150) & (b > 55) & (b < 150) & (g - r > 40) & (b - r > 40)).sum())


def qt_runtime_checks() -> dict:
    import time

    from KrakenOS.UI.qt.app import build

    app, window = build(["guard"])
    window.show()
    app.processEvents()
    view = window.build_scene()
    window.load_layout_path(SCENE)

    def settle(seconds: float = 0.4) -> None:
        end = time.time() + seconds
        while time.time() < end:
            app.processEvents()
            time.sleep(0.02)

    settle(2.5)
    inspector = view.inspector
    editor = window.editor
    labels = [label for label in ("lens", "camera", "led", "optical") if editor._step_path_for_label(label) is not None
              and inspector._all_actor_keys_for_step_label(label)]
    if not labels:
        return {"rows": [["Q", True, "SKIP: no imported STEP body in the scene (the vendor CAD is not in git)"]]}
    action = view.toolbar.controls.get(ENTRY)
    default = (bool(inspector.soft_step_bodies_var.get()), action is not None and action.isChecked())
    render_window = view.widget.GetRenderWindow()

    soft = {label: _describe(inspector, label) for label in labels}
    soft_pixels = _outline_pixels(render_window)
    action.trigger()                                # the real Overlays menu entry
    settle()
    outlined = {label: _describe(inspector, label) for label in labels}
    outlined_pixels = _outline_pixels(render_window)
    status = str(inspector.status_var.get())
    off_state = (bool(inspector.soft_step_bodies_var.get()), action.isChecked())
    action.trigger()
    settle()
    again = {label: _describe(inspector, label) for label in labels}

    def is_soft(d):
        return (d["body"] is not None and not d["body"]["flat"] and d["body"]["opacity"] >= 0.45
                and len(d["soft_edges"]) == 1 and not d["glass_silhouettes"] and not d["glass_edges"])

    def is_outlined(d):
        return (d["body"] is not None and d["body"]["flat"] and d["body"]["opacity"] < 0.45
                and len(d["glass_silhouettes"]) == 1 and len(d["glass_edges"]) == 1 and not d["soft_edges"])

    rows = [["Q", default == (True, True) and all(is_soft(soft[l]) for l in labels) and off_state == (False, False)
             and all(is_outlined(outlined[l]) for l in labels) and all(is_soft(again[l]) for l in labels)
             and "outlined" in status,
             f"default (switch, menu entry checked) {default}; bodies {labels}: soft "
             f"{ {l: soft[l]['body'] for l in labels} } with edge actors soft/silhouette/edge "
             f"{ {l: (len(soft[l]['soft_edges']), len(soft[l]['glass_silhouettes']), len(soft[l]['glass_edges'])) for l in labels} }; "
             f"after the menu entry {off_state}: "
             f"{ {l: outlined[l]['body'] for l in labels} } with "
             f"{ {l: (len(outlined[l]['soft_edges']), len(outlined[l]['glass_silhouettes']), len(outlined[l]['glass_edges'])) for l in labels} }; "
             f"status {status!r}; switched back: soft again {all(is_soft(again[l]) for l in labels)}"]]
    same_edges = {l: (soft[l]["soft_edges"], outlined[l]["glass_silhouettes"], outlined[l]["glass_edges"]) for l in labels}
    rows.append(["E", all(a == b == c and a and a[0] > 0 for a, b, c in same_edges.values()),
                 f"edge points per body (soft pass, outlined silhouette pass, outlined edge pass): {same_edges}"])
    rows.append(["I", outlined_pixels >= 1500 and soft_pixels * 5 <= outlined_pixels,
                 f"dark-teal outline pixels in the rendered scene: soft {soft_pixels}, outlined {outlined_pixels}"])
    return {"rows": rows}


def tk_runtime_checks() -> dict:
    from KrakenOS.UI import open3d_toolbar as catalogue
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor.layout_files[SCENE.stem] = SCENE
    editor.load_layout_by_name(SCENE.stem)
    editor.open_3d_view()
    for _ in range(6):
        editor.update()
    inspector = getattr(editor, "_three_d_inspector", None)
    if inspector is None or not getattr(inspector, "available", False):
        return {"rows": [["T", True, "SKIP: the embedded 3D inspector is unavailable"]]}
    for _ in range(6):
        inspector.update()
        editor.update()
    default = bool(inspector.soft_step_bodies_var.get())
    with_path = [label for label in ("lens", "camera", "led", "optical") if editor._step_path_for_label(label) is not None]
    # the Tk app warms its STEP display cache in another process, then draws the bodies: wait
    import time

    deadline = time.time() + 120.0
    labels: list = []
    while time.time() < deadline:
        inspector.update()
        editor.update()
        labels = [label for label in with_path if inspector._all_actor_keys_for_step_label(label)]
        if with_path and len(labels) == len(with_path):
            break
        time.sleep(0.1)
    if not with_path:
        return {"rows": [["T", True, "SKIP: no imported STEP body in the scene"]]}
    if not labels:
        return {"rows": [["T", False, f"the Tk scene drew no actor for the imported STEP bodies {with_path}"]]}
    described = {label: _describe(inspector, label) for label in labels}
    unchanged = all(d["body"] is not None and d["body"]["flat"] and len(d["glass_silhouettes"]) == 1
                    and len(d["glass_edges"]) == 1 and not d["soft_edges"] for d in described.values())
    offered = [entry.label for entry in catalogue.OVERLAYS.entries
               if isinstance(entry, catalogue.Check) and entry.var == "inspector.soft_step_bodies_var"]
    menu = getattr(inspector, "_open3d_overlay_menu", None)
    in_tk_menu = False
    try:
        import tkinter as tk

        tk_menu = menu if isinstance(menu, tk.Menu) else inspector.nametowidget(menu.cget("menu"))
        last = tk_menu.index("end")
        in_tk_menu = any(tk_menu.type(i) == "checkbutton" and tk_menu.entrycget(i, "label") == "Soft STEP bodies"
                         for i in range(int(last) + 1))
    except Exception:
        in_tk_menu = False
    return {"rows": [["T", default is False and unchanged and offered == ["Soft STEP bodies"] and in_tk_menu,
                      f"Tk default {default}; bodies {labels} keep the two glass passes and a flat body: {unchanged} "
                      f"{ {l: (d['body'], len(d['glass_silhouettes']), len(d['glass_edges']), len(d['soft_edges'])) for l, d in described.items()} }; "
                      f"the Overlays catalogue offers {offered}; in the Tk menu {in_tk_menu}"]]}


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
        "from KrakenOS.UI.validate_open3d_soft_step_bodies import qt_runtime_checks, tk_runtime_checks\n"
        # flushed, then exit WITHOUT interpreter teardown (a VTK/Qt teardown crash must not lose it)
        f"print({RESULT_MARK!r} + json.dumps({call}), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True, timeout=1200,
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
    rows = pure_checks()
    if SCENE.exists():
        rows += _run("qt_runtime_checks()") + _run("tk_runtime_checks()")
    else:
        rows.append(["X", True, f"SKIP = {SCENE} absent"])
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
