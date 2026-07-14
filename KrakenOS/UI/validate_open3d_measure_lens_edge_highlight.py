"""Validate the Measure hover-highlight on a round IMAGING LENS edge.

The flagged recording (flag_20260714_152932_363): with the 0303 axis-snap in
place, the second Measure arrow snaps onto the optical axis, but the user could
not tell WHICH edge it locked onto -- "there is no edge highlight on the Lens
Edge" -- and noted the CAMERA edge DID highlight, only "this particular Image
Lens" did not.

Root cause: the dimension-anchor hover highlight
(``_set_dimension_anchor_snap_highlight``) draws the picked FACE's outline. A
box-like camera STEP has planar faces the face pick resolves cleanly, so it
highlights; a smooth round lens is displayed from a tessellation, so
``_step_feature_pick_for_display_xy`` returns None for it -> no outline -> the
lens edge never lights up.

Fix: when a recognised STEP component yields no per-face outline, fall back to
``_step_component_edge_outline(label)`` -- the component's ALREADY-DRAWN edge/rim
LINE actors merged (the solid body dropped), or, for a perfectly smooth singlet
with no sharp edges, the synthesised rim circle (``_lens_rim_circle_polyline``).
Either way a round lens now yields a hover outline like the camera already did.

Display-free (no Tk / render -- just VTK/pyvista data objects):

* ``_step_component_edge_outline`` takes ONLY line geometry (skips the solid
  body), returns None for an unknown label, and synthesises the rim circle when
  only a smooth body is drawn;
* source asserts prove the hover routes an empty per-face outline through the
  fallback (keyed at component level so it is not rebuilt every pixel).

Exposes ``run_checks() -> (passed, failures)`` so it doubles as a penta phase.
"""

from __future__ import annotations

import inspect

import pyvista as pv
from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper

from KrakenOS.UI import open3d_inspector as _oi
from KrakenOS.UI.open3d_inspector import Kraken3DInspector

# The module loads pyvista/VTK lazily when an inspector is constructed; trigger
# that load headless (imports only, no display) so module-level ``pv`` -- which
# every ``pv``-guarded helper checks -- is populated.
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
    _step_component_edge_outline = Kraken3DInspector._step_component_edge_outline
    _lens_rim_circle_polyline = staticmethod(Kraken3DInspector._lens_rim_circle_polyline)

    def __init__(self, follow_actor_map, actor_by_key, editor):
        self._step_follow_actor_map = follow_actor_map
        self._actor_by_key = actor_by_key
        self.editor = editor


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []

    line_poly = pv.Line((0.0, 0.0, 0.0), (10.0, 0.0, 0.0))   # 1 line, 2 pts
    body_poly = pv.Sphere(radius=8.0)                          # polys, 0 lines

    # --- 1) edge + solid body registered -> take ONLY the line geometry ---------
    fake = _Fake(
        {"lens": ["edge", "body"]},
        {"edge": _actor_for(line_poly), "body": _actor_for(body_poly)},
        _Editor(),
    )
    out = _Fake._step_component_edge_outline(fake, "lens")
    if out is None or int(getattr(out, "n_points", 0)) <= 0:
        failures.append("round-lens component produced no hover outline")
    else:
        if int(out.GetNumberOfLines()) <= 0:
            failures.append("component outline has no LINE cells (should be the edge)")
        if int(out.GetNumberOfPolys()) > 0:
            failures.append("component outline pulled in the solid body (polys present)")
        if int(out.n_points) != int(line_poly.n_points):
            failures.append("component outline is not exactly the drawn edge geometry")

    # --- 2) unknown label -> None (never fabricate an outline for a non-component)
    if _Fake._step_component_edge_outline(fake, "not-a-component") is not None:
        failures.append("an unknown label unexpectedly produced an outline")

    # --- 3) smooth singlet (only a solid body drawn) -> synthesised rim circle ---
    drum = pv.Cylinder(center=(0.0, 0.0, 0.0), direction=(1.0, 0.0, 0.0),
                       radius=10.0, height=3.0, resolution=96, capping=True)
    fake_smooth = _Fake(
        {"lens": ["body"]},
        {"body": _actor_for(body_poly)},   # excluded (a solid, no lines)
        _Editor(drum),
    )
    rim = _Fake._step_component_edge_outline(fake_smooth, "lens")
    if rim is None or int(getattr(rim, "n_points", 0)) <= 0:
        failures.append("smooth singlet got no rim-circle fallback (round lens must still highlight)")
    elif int(rim.GetNumberOfLines()) <= 0:
        failures.append("rim-circle fallback has no LINE cells")

    # --- 4) hover wiring (source asserts) ---------------------------------------
    hover_src = inspect.getsource(Kraken3DInspector._set_dimension_anchor_snap_highlight)
    if "_step_component_edge_outline" not in hover_src:
        failures.append("the dimension-anchor hover does not fall back to _step_component_edge_outline")
    if "reanchor-component" not in hover_src:
        failures.append("the component fallback is not keyed at component level (would rebuild per pixel)")
    if "n_points" not in hover_src:
        failures.append("the fallback is not gated on an empty per-face outline (would override the camera face highlight)")

    helper_src = inspect.getsource(Kraken3DInspector._step_component_edge_outline)
    for needle in ("_step_follow_actor_map", "GetNumberOfLines", "_lens_rim_circle_polyline"):
        if needle not in helper_src:
            failures.append(f"_step_component_edge_outline does not use {needle}")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("Measure lens-edge highlight validation failed:")
        for name in failures:
            print(f"- {name}")
        return 1
    print(
        "Measure lens-edge highlight validation passed: a round imaging lens (whose "
        "smooth faces give no per-face outline) now falls back to its drawn edge/rim "
        "geometry -- or a synthesised rim circle -- so the Measure snap highlights the "
        "lens edge just like the box-like camera edge already did."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
