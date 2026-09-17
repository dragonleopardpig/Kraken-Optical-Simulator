"""bugs/0803 -- a detailed part gets its OWN depth grid, and cut specks are dropped where they are noise.

Follow-on to bugs/0802 (hidden-line removal), whose residuals were small mount-hole rims breaking
into dots and coarse detail on small parts in the viewport export.

Measured before changing anything:

* **Viewport: one grid for the whole view is too coarse.** 263 mm of scene at 1400 px is 188 um per
  pixel, so the camera's 53 mm spanned 284 px where the six-view sheet gives it 1396. Per-part
  tiles (lens 109 um, camera 40 um) cut the total visible-length error against a 4000 px
  reference from 667 mm to 282 mm, and strips off by more than 0.25 mm from 406 to 144.
* **Six-view: the depth test was NOT what dotted the rims** -- small strips were almost never cut.
  An A/B of each 0802 change found that sampling ALONG segments added ~1100 sub-0.5 mm cut pieces
  (while recovering 21 real lines over 5 mm).

Dropping cut pieces under 3 px helps a SINGLE-PART sheet (722 fewer specks, lines over 5 mm
227 -> 232) but in a multi-body view a short piece can be a line emerging from behind another
body: applied there, even on fine tiles, it cost 130 -> 127 long lines. So it applies only when
no tiles were needed. Measured on one scene; stated as observed.

Display-free: synthetic boxes, no app.
"""

from __future__ import annotations

import inspect

import numpy as np

from KrakenOS.UI.services.dxf_viewport_export import _SceneDepthBuffer  # noqa: E402

VIEW = (0.0, 0.0, -1.0)   # camera at +Z: a larger z is nearer the viewer


def _box(bounds):
    import pyvista as pv

    return pv.Box(bounds=bounds).triangulate()


def _length(run) -> float:
    return float(np.sum(np.linalg.norm(np.diff(np.asarray(run, float), axis=0), axis=1)))


def run_checks(verbose: bool = False) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    problems: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)
        if not condition:
            problems.append(message)

    part = (-10.0, 10.0, -20.0, 20.0, -5.0, 5.0)
    far_away = (490.0, 510.0, -10.0, 10.0, -1.0, 1.0)

    # ---- A: a small part in a large scene gets its own, finer grid -------------------------
    scene = _SceneDepthBuffer(VIEW, resolution=200, tile_min_triangles=1)
    scene.add_mesh(_box(part))
    scene.add_mesh(_box(far_away))
    scene._build()
    ok(len(scene._grids) >= 1, f"A: the scene built per-part tiles ({len(scene._grids)})")
    inside = np.array([[-5.0, 0.0, 6.0], [5.0, 0.0, 6.0]])
    origin, _buf, _front, tile_scale, full = scene._grid_for(scene.to_plane(inside))
    global_pitch = 1.0 / scene._scale
    tile_pitch = 1.0 / tile_scale
    ok(full and tile_pitch < global_pitch / 5.0,
       f"A: a strip on the part is tested on its tile ({tile_pitch * 1000:.0f} um) not the "
       f"global grid ({global_pitch * 1000:.0f} um)")
    spanning = np.array([[0.0, 0.0, 6.0], [500.0, 0.0, 6.0]])
    *_rest, full_spanning = scene._grid_for(scene.to_plane(spanning))
    ok(not full_spanning,
       "A: a strip spanning both bodies falls back to the global grid, which is NOT full "
       "resolution once tiles exist")

    # ---- B: occlusion by ANOTHER body survives inside a tile --------------------------------
    occluded = _SceneDepthBuffer(VIEW, resolution=200, tile_min_triangles=1)
    occluded.add_mesh(_box(part))
    occluded.add_mesh(_box(far_away))
    occluded.add_mesh(_box((-6.0, 6.0, -6.0, 6.0, 49.0, 50.0)))   # near plate over the part
    face_edge = np.array([[-2.0, 0.0, 5.0], [2.0, 0.0, 5.0]])
    ok(occluded.visible_runs(face_edge) == [],
       "B: an edge on the part, behind a nearer plate, is hidden -- the tile rasterises every "
       "solid overlapping it, not just the part")
    ok(len(scene.visible_runs(face_edge)) == 1,
       "B: without the plate the same edge is visible")

    # ---- C: a fully visible strip comes back with its ORIGINAL vertices ----------------------
    three = np.array([[-8.0, -3.0, 7.0], [0.0, 4.0, 7.0], [8.0, -3.0, 7.0]])
    runs = scene.visible_runs(three)
    ok(len(runs) == 1 and runs[0].shape == three.shape and np.array_equal(runs[0], three),
       "C: an uncut strip is returned exactly -- resampled output would stop the silhouette "
       "and feature copies of an edge from deduplicating")

    # ---- D: cut specks are dropped in a single-part view, kept in a multi-body one ----------
    passing = np.array([[-10.25, 0.0, -50.0], [10.25, 0.0, -50.0]])   # behind, ends peek out
    single = _SceneDepthBuffer(VIEW, resolution=200, tile_min_triangles=1)
    single.add_mesh(_box(part))
    single._build()
    ok(not single._grids, "D: a single-part view needs no tiles")
    ok(single.visible_runs(passing) == [],
       "D: in a single-part view the sub-3-px end pieces left by the cut are dropped -- the "
       "part hiding itself at a rim, noise")
    multi_runs = scene.visible_runs(passing)
    ok(len(multi_runs) == 2 and all(_length(r) < 3.0 * tile_pitch * 2 for r in multi_runs),
       f"D: in a multi-body view the same short pieces are KEPT ({len(multi_runs)}) -- there "
       "a short visible piece can be a line emerging from behind another body")

    # ---- E: wiring ---------------------------------------------------------------------------
    src = inspect.getsource(_SceneDepthBuffer)
    ok("tile_min_triangles" in src and "_grid_for" in src,
       "E: tiles are part of the depth buffer used by both DXF collectors")
    ok("full_resolution and not self._grids" in src,
       "E: the speck drop is gated on a single-part view")
    return (not problems), notes


def main() -> int:
    try:
        passed, notes = run_checks()
    except Exception as exc:
        passed, notes = False, [f"FAIL: {type(exc).__name__}: {exc}"]
    for note in notes:
        print(note)
    print("bugs/0803 per-part depth grid validation " + ("PASSED." if passed else "FAILED."))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
