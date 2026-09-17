"""bugs/0802 -- the DXF draws only what is VISIBLE.

User: *"still have some stray lines"*, *"those strays also break one of the supposed to be
closed line"*, *"I think the camera is also quite messy"* (camera_top.png: the connector
internals, the PCB and the far wall all drawn through the body).

One cause. The export projected EVERY edge of every body, front and back -- a see-through
wireframe. Measured on the user's own scene:

| body | feature edges | occluded |
|---|---|---|
| lens (11272 triangles) | 4609 | **67.5%** |
| camera (231606 triangles) | 57903 | **94.2%** |

The "strays" floating inside the lens taper were back-facing edges showing through the cone,
which is why no 2D rule could separate them from genuine front detail: three earlier hypotheses
(the merge re-projection, the perturbed silhouette tilts, silhouette-vs-feature source) were all
killed by measurement, because the discriminator is DEPTH.

``_SceneDepthBuffer`` rasterises every solid in the view into one orthographic z-buffer, and each
body strip is cut to the runs that are not behind a solid. Scene-wide, not per mesh, so the lens
occludes the camera too.

Display-free: synthetic boxes, no app, no VTK render.
"""

from __future__ import annotations

import inspect

import numpy as np

from KrakenOS.UI.services.dxf_viewport_export import _SceneDepthBuffer  # noqa: E402


def _box(center, half):
    import pyvista as pv

    c, h = np.asarray(center, float), np.asarray(half, float)
    return pv.Box(bounds=(c[0] - h[0], c[0] + h[0], c[1] - h[1], c[1] + h[1],
                          c[2] - h[2], c[2] + h[2])).triangulate()


def run_checks(verbose: bool = False) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    problems: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)
        if not condition:
            problems.append(message)

    # VTK's GetDirectionOfProjection points FROM the camera INTO the scene. Projecting along
    # -Z puts the camera at +Z, so a LARGER z is NEARER the viewer -- the convention the
    # geometry below is written in. (The first version of this guard used +Z and every
    # verdict came out inverted: the test's convention, not the buffer's.)
    view = (0.0, 0.0, -1.0)

    # ---- A: nothing rasterised -> nothing is hidden ----------------------------------------
    empty = _SceneDepthBuffer(view)
    strip = np.array([[-5.0, 0.0, 50.0], [5.0, 0.0, 50.0]])
    runs = empty.visible_runs(strip)
    ok(len(runs) == 1 and np.allclose(runs[0], strip),
       "A: with no solids in the view every strip is kept whole")

    # ---- B: a strip BEHIND a solid is dropped ----------------------------------------------
    depth = _SceneDepthBuffer(view)
    depth.add_mesh(_box((0.0, 0.0, 0.0), (20.0, 20.0, 5.0)))
    behind = np.array([[-10.0, 0.0, -50.0], [10.0, 0.0, -50.0]])
    ok(depth.visible_runs(behind) == [],
       "B: a strip entirely behind a solid is removed -- the see-through wireframe")

    in_front = np.array([[-10.0, 0.0, 50.0], [10.0, 0.0, 50.0]])
    runs = depth.visible_runs(in_front)
    ok(len(runs) == 1
       and np.allclose(runs[0][0], in_front[0]) and np.allclose(runs[0][-1], in_front[-1]),
       "B: a strip in front of it is kept whole, end to end (it comes back sampled along its "
       "length, so compare the ends rather than the vertex count)")

    # a strip ON the front face must survive -- silhouette and feature edges LIE on the surface
    on_face = np.array([[-10.0, 0.0, 5.0], [10.0, 0.0, 5.0]])
    ok(len(depth.visible_runs(on_face)) == 1,
       "B: an edge lying ON the front surface is kept (the depth test has a tolerance, or "
       "every silhouette would erase itself)")

    # ---- C: a partly hidden strip is CUT, not dropped --------------------------------------
    half = _SceneDepthBuffer(view)
    half.add_mesh(_box((0.0, 0.0, 0.0), (10.0, 20.0, 5.0)))   # occupies x in [-10, 10]
    crossing = np.array([[float(x), 0.0, -50.0] for x in np.linspace(-40.0, 40.0, 81)])
    runs = half.visible_runs(crossing)
    ok(len(runs) == 2,
       f"C: a strip passing behind a solid comes back as the two visible runs ({len(runs)})")
    if len(runs) == 2:
        left_max = float(np.max(runs[0][:, 0]))
        right_min = float(np.min(runs[1][:, 0]))
        ok(left_max <= -9.0 and right_min >= 9.0,
           f"C: and it is cut at the body's edges ({left_max:.1f} .. {right_min:.1f} vs +/-10)")

    # a LONG 2-point segment with both ENDS visible, passing behind the body in the middle:
    # testing vertices alone would keep it whole
    long_segment = np.array([[-40.0, 0.0, -50.0], [40.0, 0.0, -50.0]])
    runs = half.visible_runs(long_segment)
    ok(len(runs) == 2,
       f"C: a single long segment whose middle passes behind the body is cut too "
       f"({len(runs)} runs) -- the test samples along the segment, not only its vertices")

    # ---- D: inter-object occlusion, which is why the buffer is SCENE-wide -------------------
    scene = _SceneDepthBuffer(view)
    scene.add_mesh(_box((0.0, 0.0, 40.0), (15.0, 15.0, 2.0)))   # near plate
    scene.add_mesh(_box((0.0, 0.0, -40.0), (30.0, 30.0, 2.0)))  # far plate, wider
    hidden_edge = np.array([[-5.0, 0.0, -38.0], [5.0, 0.0, -38.0]])
    ok(scene.visible_runs(hidden_edge) == [],
       "D: the far body's edge is hidden by the NEAR body -- one buffer for the whole view")
    outer_edge = np.array([[-28.0, 0.0, -38.0], [-20.0, 0.0, -38.0]])
    ok(len(scene.visible_runs(outer_edge)) == 1,
       "D: where the near body does not cover it, the far body still draws")

    # ---- E: wired into BOTH collectors, and rays are left alone -----------------------------
    from KrakenOS.UI.services import dxf_viewport_export as dxe

    viewport_src = inspect.getsource(dxe.collect_viewport_dxf_layers)
    # bugs/0809 moved the per-strip loop into _remove_hidden_lines (so it can be tested without a
    # display); the collector calls it, and the rules below live there.
    if hasattr(dxe, "_remove_hidden_lines") and "_remove_hidden_lines(" in viewport_src:
        viewport_src += inspect.getsource(dxe._remove_hidden_lines)
    ok("_SceneDepthBuffer" in viewport_src and "visible_runs" in viewport_src,
       "E: the viewport export removes hidden lines")
    ok('layers.get("KRAKEN_BODIES")' in viewport_src,
       "E: and only from the BODIES layer -- rays, axes and overlays draw over the scene in "
       "the 3D view, and the drawing follows the view (bugs/0800)")
    six_src = inspect.getsource(dxe.collect_component_six_view_layers)
    ok("_SceneDepthBuffer" in six_src and "visible_runs" in six_src,
       "E: the six-view component sheet does too -- one buffer per view direction")
    ok('entry.get("closed")' in viewport_src,
       "E: a closed outline ring is kept whole; cutting a ring into runs would stop it being "
       "a shape (bugs/0799)")
    return (not problems), notes


def main() -> int:
    try:
        passed, notes = run_checks()
    except Exception as exc:
        passed, notes = False, [f"FAIL: {type(exc).__name__}: {exc}"]
    for note in notes:
        print(note)
    print("bugs/0802 hidden-line validation " + ("PASSED." if passed else "FAILED."))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
