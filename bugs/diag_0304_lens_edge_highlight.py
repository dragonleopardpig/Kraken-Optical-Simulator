"""0304 diag: why does the Measure hover highlight the CAMERA edge but not the
round IMAGING LENS edge, and does the drawn-edge fallback fix it?

The flagged recording (flag_20260714_152932_363): with the 0303 axis-snap in
place, the second Measure arrow now snaps onto the optical axis, but "there is
no edge highlight on the Lens Edge" -- and the user noted the CAMERA edge DOES
highlight, only "this particular Image Lens" does not.

Root cause: the hover highlight (``_set_dimension_anchor_snap_highlight``) draws
the picked FACE's outline. A box-like camera STEP has planar faces the face pick
resolves cleanly, so it highlights. A smooth round lens is displayed from a
tessellation, so ``_step_feature_pick_for_display_xy`` returns None for it (the
round-lens tessellation guard) -> no outline -> nothing highlights.

Fix (pure, numeric here): ``_step_component_edge_outline(label)`` merges the
component's ALREADY-DRAWN edge/rim LINE actors (skipping the solid body), and if
a perfectly smooth singlet drew no sharp edges, synthesises the rim circle via
``_lens_rim_circle_polyline``. Either way a round lens now yields a hover outline.

This binds the real methods to a fake ``self`` with VTK actors (no Tk / render).
"""

from __future__ import annotations

import numpy as np
import pyvista as pv
from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper

from KrakenOS.UI import open3d_inspector as _oi
from KrakenOS.UI.open3d_inspector import Kraken3DInspector

# The module loads pyvista/VTK lazily when an inspector is constructed; in this
# headless probe we trigger that load so module-level ``pv`` is populated (no
# display, just imports) -- otherwise every ``pv``-guarded helper returns None.
_oi._load_3d_backends()


def _actor_for(poly) -> vtkActor:
    mapper = vtkPolyDataMapper()
    mapper.SetInputData(poly)
    actor = vtkActor()
    actor.SetMapper(mapper)
    return actor


class _Editor:
    def __init__(self, mesh=None):
        self._mesh = mesh

    def _transformed_imported_step_mesh_for_label(self, key):
        return self._mesh


class _Fake:
    """Minimal stand-in carrying just what the outline helper reads."""

    _step_component_edge_outline = Kraken3DInspector._step_component_edge_outline
    _lens_rim_circle_polyline = staticmethod(Kraken3DInspector._lens_rim_circle_polyline)

    def __init__(self, follow_actor_map, actor_by_key, editor):
        self._step_follow_actor_map = follow_actor_map
        self._actor_by_key = actor_by_key
        self.editor = editor


def main() -> int:
    failures: list[str] = []

    # Geometry: a rim-like LINE poly (the "lens edge") + a solid SURFACE body.
    line_poly = pv.Line((0.0, 0.0, 0.0), (10.0, 0.0, 0.0))          # 1 line, 2 pts
    body_poly = pv.Sphere(radius=8.0)                                # polys, 0 lines
    edge_actor = _actor_for(line_poly)
    body_actor = _actor_for(body_poly)

    # 1) Both an edge actor and the solid body are registered as follow actors
    #    (the real overlay registers the body with follow_step_label too). The
    #    helper must take ONLY the line geometry and drop the solid body.
    fake = _Fake(
        {"lens": ["edge", "body"]},
        {"edge": edge_actor, "body": body_actor},
        _Editor(),
    )
    out = _Fake._step_component_edge_outline(fake, "lens")
    print("edge+body -> outline pts :", None if out is None else int(out.n_points),
          "lines :", None if out is None else int(out.GetNumberOfLines()))
    if out is None or int(out.n_points) <= 0:
        failures.append("edge+body: no outline (should highlight the lens edge)")
    else:
        if int(out.GetNumberOfLines()) <= 0:
            failures.append("edge+body: outline has no LINE cells")
        if int(out.GetNumberOfPolys()) > 0:
            failures.append("edge+body: outline pulled in the solid body (polys present)")
        if int(out.n_points) != int(line_poly.n_points):
            failures.append(f"edge+body: expected only the line's points, got {int(out.n_points)}")

    # 2) Unknown label -> None (no highlight fabricated for a non-component).
    if _Fake._step_component_edge_outline(fake, "not-a-component") is not None:
        failures.append("unknown label unexpectedly produced an outline")

    # 3) A smooth singlet: only the solid body is drawn (no sharp edges), so the
    #    line merge is empty and the helper synthesises the rim circle instead.
    drum = pv.Cylinder(center=(0.0, 0.0, 0.0), direction=(1.0, 0.0, 0.0),
                       radius=10.0, height=3.0, resolution=96, capping=True)
    fake_smooth = _Fake(
        {"lens": ["body"]},
        {"body": _actor_for(body_poly)},   # a solid surface only -> excluded
        _Editor(drum),
    )
    rim = _Fake._step_component_edge_outline(fake_smooth, "lens")
    print("smooth singlet -> rim pts:", None if rim is None else int(rim.n_points),
          "lines :", None if rim is None else int(rim.GetNumberOfLines()))
    if rim is None or int(rim.n_points) <= 0:
        failures.append("smooth singlet: no rim-circle fallback (round lens must still highlight)")
    elif int(rim.GetNumberOfLines()) <= 0:
        failures.append("smooth singlet: rim fallback produced no LINE cells")

    print()
    if failures:
        print("RESULT: FAIL")
        for f in failures:
            print(" -", f)
        return 1
    print("RESULT: ALL PASS -- a round lens now yields a hover outline (drawn edges,")
    print("or a synthesised rim), so the Measure snap confirms the lens edge just")
    print("like the camera edge already did.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
