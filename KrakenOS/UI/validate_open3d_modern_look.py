"""Guard for bugs/0966: the 3D scene's MODERN look -- glass, soft rays, a soft backdrop.

The user, in the Qt shell: "the rays, the glass, the optical elements can have a nicer look? Apart
from the STEP element, the rest look like old TK. Perhaps reference to Optiland, very nice display."
The table's elements were bright cyan under two dark-teal outline passes, the rays opaque and fully
saturated (hundreds per field: a painted fan), all on a white sheet.

  P  the look as numbers, no display (`services/open3d_scene_look.py`):
       P1 elements: default glass becomes pale glass with the glass material, its opacity kept inside
          the glass range, and an element hidden on purpose (opacity 0) STAYS hidden; the triangle
          wires laid over an opaque element are dropped; the two glass outline passes become ONE
          quiet colour and width; a mirror gets the mirror material; a colour the look does not own
          (a user's surface colour) is left alone. The classic palette has ONE source: the scene
          refresh's names and the inspector's default surface colours are the look module's.
       P2 rays: the hue is kept, saturation is capped and lightness drawn to the middle, a grey stub
          stays grey; up to 36 rays keep their opacity, beyond that it falls as 1/sqrt(n) to a floor;
          a diagnostic ray (not 1.0 px wide: a miss, a clipped stub) keeps its width and most of its
          opacity however many rays are drawn
  Q  in the real Qt shell, on a scene in git: the switch and its Overlays entry are ON by default;
     the backdrop is a gradient, no element actor carries a classic outline tone, the glass outlines
     are the one quiet colour at 1.2 px, and no ray is more saturated than the cap. The REAL menu
     entry switches to the classic look -- white sheet, the two glass passes at 2.8 and 2.0 px, rays
     fully saturated again -- and back
  E  display only: both looks draw the SAME actors per row with the same points, and the same rays
     with the same cells -- so picking and "the nearest DRAWN edge" cannot differ
  S  the look is for the TABLE's elements: through the real actor factory, a glass-toned line tied
     to a row is drawn modern, the same line with no row (imported STEP hardware, which has its own
     switch -- bugs/0958) is left as asked
  D  the number of rays reaches the law: 144 rays through the real merge come out at half opacity
  I  by the picture: the classic render is full of vivid pixels (neon rays, cyan glass), the modern
     one has almost none; the modern backdrop is darker and bluer at the top than at the bottom
  T  the Tk app is unchanged: the switch is off, the scene is the classic one, and its Overlays menu
     offers the same entry
"""
from __future__ import annotations

import colorsys
import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "MODERNLOOK_RESULT "
SKIP_MARK = "MODERNLOOK_SKIP "
SCENE = Path("KrakenOS/common_optical_layouts/beam_splitter_two_arm_doublets.py")
ENTRY = "Modern look"
#: the Qt 3D toolbar names a menu's entry "<menu>/<entry>"
QT_ENTRY = "Overlays/" + ENTRY


def _close(a, b, tol: float = 0.012) -> bool:
    return len(a) == len(b) and all(abs(float(x) - float(y)) <= tol for x, y in zip(a, b))


def _saturation(color) -> float:
    return colorsys.rgb_to_hls(*(float(c) for c in color))[2]


def pure_checks() -> list:
    from types import SimpleNamespace

    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    from KrakenOS.UI.services import open3d_scene_look as look
    from KrakenOS.UI.services import open3d_scene_refresh as refresh

    class Var:
        def __init__(self, value):
            self.value = value

        def get(self):
            return self.value

    switch = (look.is_modern(SimpleNamespace()), look.is_modern(SimpleNamespace(modern_look_var=Var(True))),
              look.is_modern(SimpleNamespace(modern_look_var=Var(False))))
    low, high = look.MODERN_GLASS_OPACITY
    opaque = look.mesh_look(look.CLASSIC_GLASS_COLOR, 0.86, 1.0)
    faint = look.mesh_look(look.CLASSIC_STEP_BODY_COLOR, 0.10, 1.0)
    hidden = look.mesh_look(look.CLASSIC_GLASS_COLOR, 0.0, 1.0)
    wires = look.mesh_look(look.CLASSIC_GLASS_COLOR, 1.0, 1.35, wireframe=True)
    silhouette = look.mesh_look(look.CLASSIC_SILHOUETTE_COLOR, 1.0, 2.8)
    edge = look.mesh_look(look.CLASSIC_EDGE_COLOR, 1.0, 2.0)
    mirror = look.mesh_look(look.CLASSIC_MIRROR_COLOR, 0.88, 1.0)
    ring = look.mesh_look(look.CLASSIC_OUTLINE_COLOR, 1.0, 1.0)
    users = look.mesh_look((0.8, 0.7, 0.4), 0.35, 1.0)
    one_source = (refresh._OPTICAL_STEP_EDGE_COLOR is look.CLASSIC_EDGE_COLOR
                  and refresh._OPTICAL_STEP_SILHOUETTE_COLOR is look.CLASSIC_SILHOUETTE_COLOR
                  and refresh._OPTICAL_STEP_BODY_COLOR is look.CLASSIC_STEP_BODY_COLOR
                  and Kraken3DInspector._surface_color(SimpleNamespace(Color=[0, 0, 0], Glass="BK7")) == look.CLASSIC_GLASS_COLOR
                  and Kraken3DInspector._surface_color(SimpleNamespace(Color=[0, 0, 0], Glass="MIRROR")) == look.CLASSIC_MIRROR_COLOR)
    p1 = (switch == (False, True, False)
          and opaque.color == look.MODERN_GLASS_COLOR and opaque.opacity == high and opaque.material == look.GLASS_MATERIAL
          and faint.color == look.MODERN_GLASS_COLOR and faint.opacity == low
          and hidden.opacity == 0.0 and wires.opacity == 0.0
          and silhouette.color == edge.color == look.MODERN_EDGE_COLOR
          and silhouette.line_width == edge.line_width == look.MODERN_EDGE_WIDTH < 2.0
          and mirror.color == look.MODERN_MIRROR_COLOR and mirror.material == look.MIRROR_MATERIAL and mirror.opacity == 0.88
          and ring.color == look.MODERN_OUTLINE_COLOR and users is None and one_source)
    rows = [["P1", p1,
             f"switch (none, on, off) {switch}; glass asked at 0.86 -> {opaque.opacity} and at 0.10 -> {faint.opacity} "
             f"(range {low}-{high}), hidden stays {hidden.opacity}, triangle wires -> {wires.opacity}; the two glass "
             f"passes (2.8 px, 2.0 px) -> {silhouette.line_width} px and {edge.line_width} px in one colour "
             f"{silhouette.color == edge.color}; mirror material {mirror.material}; a user's colour -> {users}; the "
             f"classic palette has one source: {one_source}"]]

    green, grey = (0.2, 1.0, 0.1), (0.66, 0.66, 0.66)
    soft = look.soften_ray_color(green)
    hue_before, light_before, sat_before = colorsys.rgb_to_hls(*green)
    hue_after, light_after, sat_after = colorsys.rgb_to_hls(*soft)
    factors = [round(look.ray_density_factor(n), 4) for n in (1, 36, 144, 900, 100000)]
    ordinary = look.ray_look(green, 0.88, 1.0, 900)
    miss = look.ray_look(green, 0.74, 1.5, 900)
    few = look.ray_look(green, 0.88, 1.0, 11)
    p2 = (abs(hue_after - hue_before) < 0.01 and sat_after <= look.RAY_MAX_SATURATION + 1e-6 < sat_before
          and abs(light_after - look.RAY_LIGHTNESS_CENTRE) < abs(light_before - look.RAY_LIGHTNESS_CENTRE)
          and look.soften_ray_color(grey) == grey
          and factors == [1.0, 1.0, 0.5, 0.2, look.RAY_MIN_DENSITY_FACTOR]
          and abs(ordinary[1] - 0.88 * 0.2) < 1e-9 and ordinary[2] == 1.0
          and abs(miss[1] - 0.74 * look.RAY_DIAGNOSTIC_DENSITY_FLOOR) < 1e-9 and miss[2] == 1.5
          and abs(few[1] - 0.88) < 1e-9)
    rows.append(["P2", p2,
                 f"green {green} -> {tuple(round(c, 3) for c in soft)}: hue {hue_before:.3f} -> {hue_after:.3f}, saturation "
                 f"{sat_before:.2f} -> {sat_after:.2f} (cap {look.RAY_MAX_SATURATION}), lightness {light_before:.2f} -> "
                 f"{light_after:.2f}; grey unchanged {look.soften_ray_color(grey) == grey}; opacity kept at "
                 f"1/36/144/900/100000 rays: {factors}; an ordinary ray of 900 -> {ordinary[1]:.3f}, a miss (1.5 px) -> "
                 f"{miss[1]:.3f} at {miss[2]} px, one of 11 -> {few[1]:.2f}"])
    return rows


def _describe(inspector) -> dict:
    """What the scene draws: each row's actors, the ray actors, the backdrop."""
    rows = {}
    for row, keys in sorted((inspector.__dict__.get("_row_actor_map") or {}).items()):
        items = []
        for key in keys:
            actor = inspector._actor_by_key.get(key)
            if actor is None or actor.GetMapper() is None:
                continue
            prop, data = actor.GetProperty(), actor.GetMapper().GetInput()
            items.append({"color": [round(float(c), 3) for c in prop.GetColor()], "opacity": round(float(prop.GetOpacity()), 3),
                          "width": round(float(prop.GetLineWidth()), 2), "points": int(data.GetNumberOfPoints()),
                          "material": [round(float(prop.GetAmbient()), 2), round(float(prop.GetDiffuse()), 2),
                                       round(float(prop.GetSpecular()), 2), round(float(prop.GetSpecularPower()), 1)]})
        rows[str(int(row))] = items
    ray_keys = set((inspector.__dict__.get("_merged_ray_cell_index") or {}).keys())
    rays = []
    actors = inspector._renderer.GetActors()
    actors.InitTraversal()
    for _ in range(actors.GetNumberOfItems()):
        actor = actors.GetNextActor()
        if inspector._actor_key(actor) in ray_keys:
            prop = actor.GetProperty()
            rays.append({"color": [round(float(c), 3) for c in prop.GetColor()], "opacity": round(float(prop.GetOpacity()), 3),
                         "width": round(float(prop.GetLineWidth()), 2),
                         "cells": int(actor.GetMapper().GetInput().GetNumberOfCells())})
    ray_indices = sorted({int(i) for cells in (inspector.__dict__.get("_merged_ray_cell_index") or {}).values() for i in cells})
    renderer = inspector._renderer
    return {"rows": rows, "rays": rays, "ray_indices": ray_indices,
            "gradient": bool(renderer.GetGradientBackground()),
            "background": [round(float(c), 3) for c in renderer.GetBackground()]}


def _picture(render_window) -> dict:
    """The rendered scene, measured: vivid pixels, and the backdrop's colour at the top and bottom."""
    import numpy as np
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
    arr = vtk_to_numpy(image.GetPointData().GetScalars()).reshape(height, width, -1).astype(float) / 255.0
    high, low = arr.max(axis=2), arr.min(axis=2)
    vivid = int(((high > 0.85) & ((high - low) / np.maximum(high, 1e-6) > 0.80)).sum())
    # the image's row 0 is the BOTTOM of the view; a strip clear of the readouts and the Nav Cube
    strip = slice(int(width * 0.40), int(width * 0.60))
    bottom = np.median(arr[2:8, strip].reshape(-1, 3), axis=0)
    top = np.median(arr[height - 8:height - 2, strip].reshape(-1, 3), axis=0)
    return {"vivid": vivid, "top": [round(float(c), 3) for c in top], "bottom": [round(float(c), 3) for c in bottom]}


def _has(items, color, width=None) -> int:
    return sum(1 for item in items if _close(item["color"], color) and (width is None or abs(item["width"] - width) < 0.05))


def qt_runtime_checks() -> dict:
    import time

    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.services import open3d_scene_look as look
    from KrakenOS.UI.services import open3d_scene_refresh as refresh

    app, window = build(["guard"])
    window.show()
    app.processEvents()
    view = window.build_scene()
    window.load_layout_path(SCENE)

    def settle(seconds: float = 0.5) -> None:
        end = time.time() + seconds
        while time.time() < end:
            app.processEvents()
            time.sleep(0.02)

    settle(2.5)
    inspector = view.inspector
    inspector.show_rays_var.set(True)
    window.action_manager["trace_now"].trigger()         # a load draws bodies only until a trace is asked for
    deadline = time.time() + 180.0
    while time.time() < deadline and not inspector.__dict__.get("_merged_ray_cell_index"):
        settle(0.3)
    settle(1.5)
    action = view.toolbar.controls.get(QT_ENTRY)
    if action is None:
        return {"rows": [["Q", False, f"the 3D toolbar offers no {QT_ENTRY!r} entry"]]}
    default = (bool(inspector.modern_look_var.get()), bool(action.isChecked()))
    render_window = view.widget.GetRenderWindow()

    modern, modern_picture = _describe(inspector), _picture(render_window)
    action.trigger()                                     # the real Overlays menu entry
    settle()
    classic, classic_picture = _describe(inspector), _picture(render_window)
    classic_status = str(inspector.status_var.get())
    off_state = (bool(inspector.modern_look_var.get()), bool(action.isChecked()))
    action.trigger()
    settle()
    again = _describe(inspector)

    def summary(scene: dict) -> dict:
        items = [item for row in scene["rows"].values() for item in row]
        return {"classic_silhouette_2.8": _has(items, look.CLASSIC_SILHOUETTE_COLOR, refresh._GLASS_EDGE_SILHOUETTE_WIDTH),
                "classic_edge_2.0": _has(items, look.CLASSIC_EDGE_COLOR, refresh._GLASS_EDGE_LINE_WIDTH),
                "classic_tones": _has(items, look.CLASSIC_SILHOUETTE_COLOR) + _has(items, look.CLASSIC_EDGE_COLOR)
                                 + _has(items, look.CLASSIC_OUTLINE_COLOR) + _has(items, look.CLASSIC_OUTLINE_OVERLAY_COLOR),
                "modern_edge_1.2": _has(items, look.MODERN_EDGE_COLOR, look.MODERN_EDGE_WIDTH),
                "glass_material": sum(1 for item in items if _close(item["material"], look.GLASS_MATERIAL, 0.02)),
                "ray_actors": len(scene["rays"]),
                "max_ray_saturation": round(max((_saturation(ray["color"]) for ray in scene["rays"]), default=0.0), 3),
                "gradient": scene["gradient"], "background": scene["background"]}

    m, c, a = summary(modern), summary(classic), summary(again)
    cap = look.RAY_MAX_SATURATION + 0.01
    is_modern = lambda s: (s["gradient"] and s["classic_tones"] == 0 and s["modern_edge_1.2"] >= 2 and s["glass_material"] >= 1
                           and s["ray_actors"] >= 1 and s["max_ray_saturation"] <= cap)
    is_classic = lambda s: (not s["gradient"] and _close(s["background"], look.CLASSIC_BACKGROUND)
                            and s["classic_silhouette_2.8"] >= 1 and s["classic_edge_2.0"] >= 1 and s["modern_edge_1.2"] == 0
                            and s["glass_material"] == 0
                            and s["ray_actors"] >= 1 and s["max_ray_saturation"] > cap)
    rows = [["Q", default == (True, True) and is_modern(m) and off_state == (False, False) and is_classic(c)
             and is_modern(a) and "classic" in classic_status,
             f"default (switch, menu entry checked) {default}; modern {m}; after the menu entry {off_state}: classic {c}; "
             f"status {classic_status!r}; switched back: modern again {is_modern(a)}"]]

    points = lambda scene: {row: sorted(item["points"] for item in items) for row, items in scene["rows"].items()}
    ray_cells = lambda scene: sum(ray["cells"] for ray in scene["rays"])
    rows.append(["E", points(modern) == points(classic) and len(points(modern)) >= 3
                 and modern["ray_indices"] == classic["ray_indices"] and len(modern["ray_indices"]) >= 2
                 and ray_cells(modern) == ray_cells(classic) > 0,
                 f"rows drawn {len(points(modern))} / {len(points(classic))}, the same actors with the same points per row: "
                 f"{points(modern) == points(classic)} ({sum(len(v) for v in points(modern).values())} actors); rays "
                 f"{len(modern['ray_indices'])} / {len(classic['ray_indices'])}, the same ones: "
                 f"{modern['ray_indices'] == classic['ray_indices']}; ray cells {ray_cells(modern)} / {ray_cells(classic)}"])

    darker_top = sum(modern_picture["bottom"]) - sum(modern_picture["top"])
    bluer_top = modern_picture["top"][2] - modern_picture["top"][0]
    # what stays vivid in the modern render is not the look's to change (the Nav Cube's arrows, the
    # optical axis, the axes triad): measured 953 of the classic 11 307 -- so the bound is 5x, not 10x
    rows.append(["I", classic_picture["vivid"] - modern_picture["vivid"] >= 3000
                 and modern_picture["vivid"] * 5 <= classic_picture["vivid"]
                 and darker_top > 0.25 and bluer_top > 0.08
                 and min(classic_picture["top"] + classic_picture["bottom"]) > 0.99,
                 f"vivid pixels: classic {classic_picture['vivid']}, modern {modern_picture['vivid']}; the modern backdrop is "
                 f"{modern_picture['top']} at the top and {modern_picture['bottom']} at the bottom, the classic one "
                 f"{classic_picture['top']} and {classic_picture['bottom']}"])
    # S and D go through the inspector's own two factories, last: they add actors to the scene
    import pyvista as pv

    line = pv.Line((0.0, 0.0, 0.0), (1.0, 0.0, 0.0))
    asked = dict(color=look.CLASSIC_EDGE_COLOR, opacity=1.0, line_width=refresh._GLASS_EDGE_LINE_WIDTH)
    free = inspector._add_mesh_actor(line, **asked)
    tied = inspector._add_mesh_actor(line, track_row_index=0, **asked)
    drawn = lambda actor: ([round(float(c), 3) for c in actor.GetProperty().GetColor()],
                           round(float(actor.GetProperty().GetLineWidth()), 2))
    rows.append(["S", free is not None and tied is not None
                 and _close(drawn(free)[0], look.CLASSIC_EDGE_COLOR) and drawn(free)[1] == refresh._GLASS_EDGE_LINE_WIDTH
                 and _close(drawn(tied)[0], look.MODERN_EDGE_COLOR) and drawn(tied)[1] == look.MODERN_EDGE_WIDTH,
                 f"a glass-edge line asked at {refresh._GLASS_EDGE_LINE_WIDTH} px: with no row it is drawn "
                 f"{drawn(free) if free is not None else None}, tied to a row {drawn(tied) if tied is not None else None}"])

    known = set(inspector._merged_ray_cell_index)
    inspector._pending_ray_specs = [(line, 100000 + index, (0.2, 1.0, 0.1), 0.88, 1.0) for index in range(144)]
    inspector._flush_merged_ray_actors()
    added = set(inspector._merged_ray_cell_index) - known
    merged = []
    actors = inspector._renderer.GetActors()
    actors.InitTraversal()
    for _ in range(actors.GetNumberOfItems()):
        actor = actors.GetNextActor()
        if inspector._actor_key(actor) in added:
            merged.append((round(float(actor.GetProperty().GetOpacity()), 3), int(actor.GetMapper().GetInput().GetNumberOfCells())))
    rows.append(["D", merged == [(round(0.88 * look.ray_density_factor(144), 3), 144)] and look.ray_density_factor(144) == 0.5,
                 f"144 rays asked at 0.88 through the real merge: (opacity, cells) {merged}"])
    return {"rows": rows}


def tk_runtime_checks() -> dict:
    from KrakenOS.UI import open3d_toolbar as catalogue
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services import open3d_scene_look as look
    from KrakenOS.UI.services import open3d_scene_refresh as refresh

    editor = KrakenLayoutEditor()
    editor.layout_files[SCENE.stem] = SCENE
    editor.load_layout_by_name(SCENE.stem)
    editor.open_3d_view()
    for _ in range(6):
        editor.update()
    inspector = getattr(editor, "_three_d_inspector", None)
    if inspector is None or not getattr(inspector, "available", False):
        return {"rows": [["T", True, "SKIP: the embedded 3D inspector is unavailable"]]}
    for _ in range(8):
        inspector.update()
        editor.update()
    default = bool(inspector.modern_look_var.get())
    scene = _describe(inspector)
    items = [item for row in scene["rows"].values() for item in row]
    classic = (_has(items, look.CLASSIC_SILHOUETTE_COLOR, refresh._GLASS_EDGE_SILHOUETTE_WIDTH),
               _has(items, look.CLASSIC_EDGE_COLOR, refresh._GLASS_EDGE_LINE_WIDTH),
               _has(items, look.MODERN_EDGE_COLOR, look.MODERN_EDGE_WIDTH))
    offered = [entry.label for entry in catalogue.OVERLAYS.entries
               if isinstance(entry, catalogue.Check) and entry.var == "inspector.modern_look_var"]
    menu = getattr(inspector, "_open3d_overlay_menu", None)
    in_tk_menu = False
    try:
        import tkinter as tk

        tk_menu = menu if isinstance(menu, tk.Menu) else inspector.nametowidget(menu.cget("menu"))
        last = tk_menu.index("end")
        in_tk_menu = any(tk_menu.type(i) == "checkbutton" and tk_menu.entrycget(i, "label") == ENTRY
                         for i in range(int(last) + 1))
    except Exception:
        in_tk_menu = False
    return {"rows": [["T", default is False and classic[0] >= 1 and classic[1] >= 1 and classic[2] == 0
                      and not scene["gradient"] and _close(scene["background"], look.CLASSIC_BACKGROUND)
                      and offered == [ENTRY] and in_tk_menu,
                      f"Tk default {default}; element actors with the classic silhouette pass / edge pass / the modern edge: "
                      f"{classic}; backdrop gradient {scene['gradient']}, colour {scene['background']}; the Overlays "
                      f"catalogue offers {offered}; in the Tk menu {in_tk_menu}"]]}


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
        "from KrakenOS.UI.validate_open3d_modern_look import qt_runtime_checks, tk_runtime_checks\n"
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
    rows = pure_checks() + _run("qt_runtime_checks()") + _run("tk_runtime_checks()")
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
