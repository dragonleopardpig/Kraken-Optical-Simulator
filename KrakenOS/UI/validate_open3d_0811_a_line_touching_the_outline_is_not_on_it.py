"""bugs/0811 -- a line touching the outline is not on it.

User, after 0809, on the re-exported MV-CS050-60UM_V5_TCL4.0X-65DI-5M_view.dxf: "still showing broken line
shown in latest broken.png", and correct.png from the component six-view: the SPO port's flange plate
drawn as a closed rectangle.

Measured on a headless export of the same view: the plate's 17 mm front bottom edge PASSED the depth test
at full length and was then deleted by the outline dedupe. That dedupe resamples the outline ring but
tested a candidate only at its VERTICES, and both ends of the bottom edge sit on the ring (the 0.05 mm
notch floors between plate and pocket). With it gone, the plate ends hung down to 0.14-0.19 mm stubs.

Under the plate's top edge four 0.105 mm ticks remained -- the M3 hole walls 1.7 mm behind the plate's
face, one pixel of which the depth test's 3x3 filter calls visible next to the plate's rim. 0809 left
them because at pixel pitch such a tick and a real short peek are the same two samples (the bugs/0803 D
fixture); the triangles themselves tell them apart.

A-D display-free; E the user's scene (standalone only).
"""

from __future__ import annotations

import contextlib
import inspect
import io
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENE = PROJECT_ROOT / "attachment" / "MV-CS050-60UM_V5_TCL4.0X-65DI-5M.py"
VIEW = (0.0, 0.0, -1.0)   # camera at +Z: a larger z is nearer the viewer
FAR_AWAY = (490.0, 510.0, -10.0, 10.0, -1.0, 1.0)   # a second body, so parts get their own tiles


def _box(bounds):
    import pyvista as pv

    return pv.Box(bounds=bounds).triangulate()


def _length(run) -> float:
    return float(np.sum(np.linalg.norm(np.diff(np.asarray(run, float), axis=0), axis=1)))


def _port(dxe, h):
    """A flange plate (front face z 5, top edge y h) under a farther tube, plus a far body."""
    buf = dxe._SceneDepthBuffer(VIEW, resolution=400, tile_min_triangles=1)
    buf.add_mesh(_box((-10.0, 10.0, -2.0, h, -5.0, 5.0)))
    buf.add_mesh(_box((-8.0, 8.0, h, 20.0, -12.0, -2.0)))
    buf.add_mesh(_box(FAR_AWAY))
    buf._build()
    return buf


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    problems: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)
        if not condition:
            problems.append(message)

    from KrakenOS.UI.services import dxf_viewport_export as dxe

    # ---- A: the outline dedupe looks at the whole candidate ------------------------------------------
    # the port's outline in the drawing plane: barrel top 15.5, a 0.05 mm notch down to the plate's
    # bottom 12.8 at each end, the plate top 14.8 between the tube walls
    ring = [np.array([[-30.0, 15.5], [-25.989, 15.5], [-25.989, 12.8], [-25.939, 12.8], [-25.939, 14.8],
                      [-25.439, 14.8], [-25.439, 36.0], [-9.439, 36.0], [-9.439, 14.8], [-8.939, 14.8],
                      [-8.939, 12.8], [-8.889, 12.8], [-8.889, 15.5], [-5.0, 15.5], [-5.0, -17.0],
                      [-30.0, -17.0], [-30.0, 15.5]])]
    bottom = np.array([[-25.939, 12.8], [-8.939, 12.8]])
    ok(len(dxe._strips_not_already_drawn([bottom], ring)) == 1,
       "A1: the plate's bottom edge, both ends on the ring and its middle 2 mm off it, is kept")
    wall = np.array([[-25.439, 20.0], [-25.439, 30.0]])
    ok(dxe._strips_not_already_drawn([wall], ring) == [], "A2: a line lying ON the ring is still absorbed")
    shifted = wall + np.array([0.02, 0.0])
    ok(dxe._strips_not_already_drawn([shifted], ring) == [],
       "A3: a copy a few hundredths of a millimetre off the ring is still absorbed")
    chord = np.array([[-25.989, 15.5], [-8.889, 15.5]])
    ok(len(dxe._strips_not_already_drawn([chord], ring)) == 1,
       "A4: a straight line across the port's mouth between two ring vertices is not the ring")

    # ---- B: a one-pixel tick next to an occluder's rim is not drawn -----------------------------------
    heights = np.linspace(0.0, 0.1, 11)
    reproduced, left = [], []
    for h in heights:
        buf = _port(dxe, float(h))
        for x in (-6.0, 0.37, 6.13):
            strip = np.array([[x, h, 2.0], [x, -2.0, 2.0]])   # an M3 hole wall 3 mm behind the face
            origin, raw, front, scale, _full = buf._grid_for(buf.to_plane(strip))
            steps = int(np.ceil(_length(strip) * scale))
            samples = strip[0] + np.linspace(0.0, 1.0, steps + 1)[:2, None] * (strip[1] - strip[0])
            px = np.rint((buf.to_plane(samples) - origin) * scale).astype(int)
            tol = buf._depth_span * 2e-3
            depth = buf.depth_of(samples)
            filtered = depth >= front[px[:, 1], px[:, 0]] - tol
            if bool(filtered.all()) and not bool((depth >= raw[px[:, 1], px[:, 0]] - tol).all()):
                reproduced.append(round(float(h), 3))
            left += [round(_length(r), 3) for r in buf.visible_runs(strip)]
    ok(bool(reproduced),
       f"B1 premise: at plate heights {sorted(set(reproduced))} the filter calls the wall's first two samples "
       f"visible where the raw buffer hides one -- the tick's origin")
    ok(not left, f"B2: no hole wall leaves a tick at any of the {len(heights)} sub-pixel offsets ({left})")
    buf = _port(dxe, 0.04)
    edge = np.array([[-10.0, 0.04, 5.0], [10.0, 0.04, 5.0]])
    runs = buf.visible_runs(edge)
    ok(len(runs) == 1 and abs(_length(runs[0]) - 20.0) < 1e-9,
       "B3: the plate's own top front edge, ON the rim, is still whole")
    emerging = np.array([[3.0, 0.04, 2.0], [3.0, -2.35, 2.0]])   # passes out below the plate (inside its tile)
    buf = dxe._SceneDepthBuffer(VIEW, resolution=400, tile_min_triangles=1)
    buf.add_mesh(_box((-10.0, 10.0, -2.0, 0.04, -5.0, 5.0)))
    buf.add_mesh(_box(FAR_AWAY))
    buf._build()
    runs = buf.visible_runs(emerging)
    ok(len(runs) == 1 and 0.3 < _length(runs[0]) < 0.5,
       f"B4: a line leaving the plate's bottom still shows its 0.35 mm below it "
       f"({[round(_length(r), 3) for r in runs]})")

    # ---- C: a real short peek survives (bugs/0803 D) ---------------------------------------------------
    scene = dxe._SceneDepthBuffer(VIEW, resolution=200, tile_min_triangles=1)
    scene.add_mesh(_box((-10.0, 10.0, -20.0, 20.0, -5.0, 5.0)))
    scene.add_mesh(_box(FAR_AWAY))
    scene._build()
    peeks = scene.visible_runs(np.array([[-10.25, 0.0, -50.0], [10.25, 0.0, -50.0]]))
    ok(len(peeks) == 2 and all(abs(float(r[:, 0].max())) > 10.0 or abs(float(r[:, 0].min())) > 10.0 for r in peeks),
       f"C: both 0.25 mm peeks past a box are kept ({[np.round(r[:, 0], 3).tolist() for r in peeks]})")

    # ---- D: wiring --------------------------------------------------------------------------------------
    src = inspect.getsource(dxe._SceneDepthBuffer.visible_runs)
    ok("_exactly_hidden" in src, "D1: visible_runs asks the triangles about short cut runs")
    src = inspect.getsource(dxe._strips_not_already_drawn)
    ok("probes" in src, "D2: the outline dedupe samples the candidate along its segments")

    # ---- E: the user's scene ------------------------------------------------------------------------------
    if app is not None or inspector is not None:
        notes.append("SKIP: E: the live export opens its own inspector -- run the guard standalone")
        return (not problems), notes
    if not SCENE.exists():
        notes.append("SKIP: E: the MV-CS050 + TCL4.0X scene is not in this checkout")
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
            insp._refresh_trace_now_scene("bugs/0811 guard")
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
        port = [p for p in polys if float(p[:, 0].min()) > -27.0 and float(p[:, 0].max()) < -8.0
                and float(p[:, 1].min()) > 12.0 and float(p[:, 1].max()) < 15.0]
        bottom = [p for p in port if np.ptp(p[:, 1]) < 1e-6 and abs(float(p[0, 1]) - 12.8) < 0.01
                  and np.ptp(p[:, 0]) > 16.9]
        ok(bool(bottom), f"E1: the flange plate's bottom edge is drawn "
                         f"({[np.round(p[[0, -1]], 3).tolist() for p in bottom]})")
        specks = [p for p in port if _length(p) < 0.3]
        ok(not specks, f"E2: no tick or stub is left around the plate ({[np.round(p, 3).tolist() for p in specks]})")
    except Exception as exc:
        ok(False, f"E: the live export raised {type(exc).__name__}: {exc}")
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
    print("bugs/0811 line-touching-the-outline validation " + ("PASSED." if passed else "FAILED."))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
