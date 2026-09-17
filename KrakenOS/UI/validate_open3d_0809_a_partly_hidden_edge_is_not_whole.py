"""bugs/0809 -- a partly hidden edge is not a whole edge.

User, on MV-CS050-60UM_V5_TCL4.0X-65DI-5M_view.dxf + broken.jpg: a "minor problematic part" where the
SPO lens's illumination port meets the barrel -- and "the independent 6-view output: no such problem".

Reproduced headlessly (415 polylines vs the user's 413, same closed rings, same pieces): four 2 mm
vertical ticks below the port are the walls of the plate's M3 holes, 1.7 mm behind the plate's front
face. The depth test HID them -- 0.105 mm of each came back visible where the 3x3 min filter bleeds past
the plate edge -- but the viewport's hidden-line loop decided "fully visible" by comparing POINT COUNTS:
a 2-point edge returns a 2-point run for its two visible end samples, so the whole 2 mm edge was kept.
The six-view collector uses the runs directly, which is why it was clean.

The same export also carried a 545 mm line far below the lens: the HUD text box, a SCREEN-space
vtkTextActor whose pixel quad was flattened through the view matrix as a body.

A-C display-free (synthetic buffer, a fake renderer); D the user's scene (standalone only).
"""

from __future__ import annotations

import contextlib
import io
from pathlib import Path
from types import SimpleNamespace

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENE = PROJECT_ROOT / "attachment" / "MV-CS050-60UM_V5_TCL4.0X-65DI-5M.py"


def _quad(x0, x1, y0, y1, z):
    import pyvista as pv

    pts = np.array([[x0, y0, z], [x1, y0, z], [x1, y1, z], [x0, y1, z]], float)
    return pv.PolyData(pts, np.array([3, 0, 1, 2, 3, 0, 2, 3]))


def _camera():
    from vtkmodules.vtkRenderingCore import vtkCamera

    cam = vtkCamera()
    cam.SetPosition(0.0, 0.0, -200.0)   # looking +Z: nearer the viewer = smaller z
    cam.SetFocalPoint(0.0, 0.0, 0.0)
    cam.SetViewUp(0.0, 1.0, 0.0)
    cam.SetParallelProjection(True)
    return cam


class _Props:
    def __init__(self, items):
        self._items, self._i = list(items), 0

    def InitTraversal(self):
        self._i = 0

    def GetNextProp(self):
        if self._i >= len(self._items):
            return None
        self._i += 1
        return self._items[self._i - 1]


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    problems: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)
        if not condition:
            problems.append(message)

    from KrakenOS.UI.services import dxf_viewport_export as dxe

    cam = _camera()
    view = dxe.view_projection_matrix(cam)

    # ---- A: the hidden-line loop keeps only what is visible --------------------------------------
    buffer = dxe._SceneDepthBuffer(cam.GetDirectionOfProjection())
    buffer.add_mesh(_quad(-10.0, 10.0, -10.0, 10.0, 0.0))           # the occluder, nearest the viewer
    buffer.add_mesh(_quad(-30.0, 30.0, -30.0, 30.0, 20.0))          # a back wall, so the grid has room
    buffer._build()
    crossing = np.array([[0.0, 0.0, 5.0], [20.0, 0.0, 5.0]])        # behind the occluder for x < 10
    clear = np.array([[-25.0, 20.0, 5.0], [25.0, 20.0, 5.0]])       # beside it, fully visible
    buried = np.array([[-5.0, -5.0, 5.0], [5.0, -5.0, 5.0]])        # wholly behind it
    entries = [
        {"points": dxe.project_points(crossing, view, None), "world": crossing, "color": None},
        {"points": dxe.project_points(clear, view, None), "world": clear, "color": None},
        {"points": dxe.project_points(buried, view, None), "world": buried, "color": None},
    ]
    runs = buffer.visible_runs(crossing)
    ok(len(runs) == 1 and len(runs[0]) == 2,
       f"A0: the premise -- a partly hidden 2-point edge returns ONE 2-point run ({[len(r) for r in runs]})")
    kept, removed = dxe._remove_hidden_lines(entries, buffer, view)
    spans = sorted(float(np.ptp(np.asarray(e["points"])[:, 0])) for e in kept)
    ok(len(kept) == 2 and removed == 2,
       f"A1: two entries survive (the clear one whole, the crossing one cut), the buried one goes "
       f"({len(kept)} kept, {removed} cut or dropped)")
    ok(any(abs(s - 50.0) < 1e-6 for s in spans) and any(9.0 < s < 10.5 for s in spans),
       f"A2: the crossing edge keeps only its visible ~10 mm, not its 20 mm (x spans {spans})")
    ok(any(e is entries[1] for e in kept), "A3: a fully visible edge passes through as the SAME entry")

    # ---- B: what is left of a hidden edge at a rim is at most the depth grid's own pixel ----------
    # The 3x3 min filter bleeds one pixel past an occluder's edge, and at that scale a real one-pixel
    # peek (bugs/0803 D keeps those in a multi-body view) cannot be told from the bleed. The defect
    # was the WHOLE edge being drawn; this pins that what survives is sub-pixel-scale, not the edge.
    touching = np.array([[0.0, 3.0, 5.0], [10.0, 3.0, 5.0]])           # hidden, ends ON the rim
    *_grid, touching_scale, _full = buffer._grid_for(buffer.to_plane(touching))
    pitch = 1.0 / float(touching_scale)
    crumbs = buffer.visible_runs(touching)
    lengths = [float(np.sum(np.linalg.norm(np.diff(r, axis=0), axis=1))) for r in crumbs]
    ok(all(length <= 2.0 * pitch + 1e-9 for length in lengths),
       f"B1: an edge hidden up to the occluder's rim leaves at most a pixel of it, not 10 mm "
       f"({[round(v, 3) for v in lengths]} vs pitch {pitch:.3f})")
    emerging = np.array([[0.0, 6.0, 5.0], [12.0, 6.0, 5.0]])          # 2 mm genuinely out in the open
    runs = buffer.visible_runs(emerging)
    lengths = [float(np.sum(np.linalg.norm(np.diff(r, axis=0), axis=1))) for r in runs]
    ok(len(runs) == 1 and 1.5 < lengths[0] < 2.5,
       f"B2: a line emerging 2 mm past the occluder keeps that piece ({lengths})")

    # ---- C: screen-space 2D props are not bodies ----------------------------------------------------
    from vtkmodules.vtkCommonCore import vtkPoints
    from vtkmodules.vtkCommonDataModel import vtkCellArray, vtkPolyData
    from vtkmodules.vtkFiltersSources import vtkCubeSource
    from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper

    cube = vtkCubeSource()
    cube.SetXLength(20.0); cube.SetYLength(20.0); cube.SetZLength(20.0)
    cube.Update()
    body = vtkActor()
    body_mapper = vtkPolyDataMapper()
    body_mapper.SetInputData(cube.GetOutput())
    body.SetMapper(body_mapper)

    hud_pts = vtkPoints()
    for x, y in ((12.0, 40.0), (250.0, 40.0), (250.0, 600.0), (12.0, 600.0)):   # PIXELS
        hud_pts.InsertNextPoint(x, y, 0.0)
    hud_cells = vtkCellArray()
    hud_cells.InsertNextCell(4)
    for i in range(4):
        hud_cells.InsertCellPoint(i)
    hud_quad = vtkPolyData()
    hud_quad.SetPoints(hud_pts)
    hud_quad.SetPolys(hud_cells)

    class _Hud:
        """The shape of a rendered vtkTextActor as the collector sees it."""
        def IsA(self, name):
            return name in ("vtkActor2D", "vtkTexturedActor2D", "vtkTextActor")
        def GetVisibility(self):
            return 1
        def GetMapper(self):
            return SimpleNamespace(GetInput=lambda: hud_quad)
        def GetMatrix(self):
            return None
        def GetProperty(self):
            return SimpleNamespace(GetColor=lambda: (1.0, 1.0, 1.0))

    renderer = SimpleNamespace(GetActiveCamera=lambda: cam, GetViewProps=lambda: _Props([body, _Hud()]))
    fake = SimpleNamespace(_renderer=renderer, _actor_key=lambda a: f"key{id(a)}",
                           _kraken_scene={}, _optical_axis_pick_records=[])
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        layers = dxe.collect_viewport_dxf_layers(fake)
    body_pts = [np.asarray(q["points"]) for q in layers["KRAKEN_BODIES"]["polylines"]]
    extent = max((float(np.abs(p).max()) for p in body_pts), default=0.0)
    ok(bool(body_pts) and extent <= 10.0 + 1e-6,
       f"C1: the cube draws and nothing reaches beyond its 10 mm half-size (max |coord| {extent:.3f}) -- "
       "the HUD quad in pixels is not a body")

    # ---- D: the user's scene --------------------------------------------------------------------------
    if app is not None or inspector is not None:
        notes.append("SKIP: D: the live export opens its own inspector -- run the guard standalone")
        return (not problems), notes
    if not SCENE.exists():
        notes.append("SKIP: D: the MV-CS050 + TCL4.0X scene is not in this checkout")
        return (not problems), notes
    live = None
    try:
        import time

        from KrakenOS.UI.capture_open3d_step_workflow_screenshots import _open_3d_inspector, _settle
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor

        quiet = contextlib.ExitStack()
        quiet.enter_context(contextlib.redirect_stdout(io.StringIO()))
        quiet.enter_context(contextlib.redirect_stderr(io.StringIO()))
        with quiet:
            live = KrakenLayoutEditor(headless=True)
            live._prompt_for_missing_cad_assets = lambda: None
            live.layout_files["scene"] = SCENE
            live.load_layout_by_name("scene")
            insp = _open_3d_inspector(live)
            _settle(insp, 0.8)
            insp._refresh_trace_now_scene("bugs/0809 guard")
            _settle(insp, 1.0)
            for _ in range(240):
                if (live._transformed_imported_step_mesh_for_label("lens") is not None
                        and live._transformed_imported_step_mesh_for_label("camera") is not None):
                    break
                live.update(); time.sleep(0.25)
            insp.refresh_from_editor(); _settle(insp, 1.0)
            c = insp._renderer.GetActiveCamera()
            c.SetParallelProjection(True)
            c.SetFocalPoint(0.0, 0.0, 128.0); c.SetPosition(0.0, -600.0, 128.0); c.SetViewUp(-1.0, 0.0, 0.0)
            c.SetParallelScale(90.0); insp._renderer.ResetCameraClippingRange(); _settle(insp, 0.3)
            layers = dxe.collect_viewport_dxf_layers(insp)
        polys = [np.asarray(q["points"]) for q in layers["KRAKEN_BODIES"]["polylines"]]
        lowest = min(float(p[:, 1].min()) for p in polys)
        ok(lowest > -40.0, f"D1: nothing in the drawing lies far below the lens (lowest {lowest:.1f} mm)")
        ticks = [p for p in polys if len(p) == 2 and abs(float(p[0, 0] - p[1, 0])) < 1e-6
                 and -26.0 < float(p[0, 0]) < -9.0 and float(np.ptp(p[:, 1])) > 0.5
                 and 12.0 < float(p[:, 1].min()) and float(p[:, 1].max()) < 15.0]
        ok(not ticks, f"D2: no hidden M3 hole wall below the port ({[np.round(t, 3).tolist() for t in ticks]})")
    except Exception as exc:
        ok(False, f"D: the live export raised {type(exc).__name__}: {exc}")
    finally:
        if live is not None:
            with contextlib.suppress(Exception):
                if live._three_d_inspector is not None:
                    live._three_d_inspector._on_close()
            with contextlib.suppress(Exception):
                live.destroy()
    return (not problems), notes


def main() -> int:
    try:
        passed, notes = run_checks()
    except Exception as exc:
        passed, notes = False, [f"FAIL: {type(exc).__name__}: {exc}"]
    for note in notes:
        print(note)
    print("bugs/0809 partly-hidden-edge validation " + ("PASSED." if passed else "FAILED."))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
