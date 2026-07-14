"""End-to-end 3D STEP export check for the AZ85 folded periscope (bugs/0300).

Runs the REAL export path (_collect_native_step_export_shapes + _step_export_ray_polylines +
_write_step_with_cad_shapes_and_rays) headlessly and reports:
  * writer counts (analytic surfaces now include the Object + Image reference planes),
  * the Object / Image disc world centroids from the traced transform (Image must fold to
    the sensor, NOT sit on the straight +Z axis),
  * that the written STEP file is non-empty.

Run: .devenv/state/venv/bin/python bugs/diag_step_export_full.py
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor, SurfaceRow
from KrakenOS.UI.services.cad_step_export import _write_step_with_cad_shapes_and_rays
from KrakenOS.UI.validate_open3d_five_penta_initial_visual import _load_saved_layout

LAYOUT = Path("attachment/machine_vision_AZ85_RA_Mirror.py")


def _disc_centroid(system, j: int) -> np.ndarray | None:
    trans = getattr(system, "TRANS_2A", None)
    if trans is None or j >= len(trans):
        return None
    m = np.asarray(trans[j], dtype=float).reshape(4, 4)
    return (m @ np.asarray((0.0, 0.0, 0.0, 1.0)))[:3]


def main() -> int:
    app = KrakenLayoutEditor(headless=True)
    _load_saved_layout(app, LAYOUT)
    system = app.build_system()

    rows = app.rows
    obj_j = next((i for i, r in enumerate(rows) if r.surface == "Object"), None)
    img_j = max((i for i, r in enumerate(rows) if r.surface == "Image"), default=None)
    print(f"Object row j={obj_j}  Image row j={img_j}")
    if obj_j is not None:
        print(f"  Object disc centroid = {np.round(_disc_centroid(system, obj_j), 3).tolist()}")
    if img_j is not None:
        c = _disc_centroid(system, img_j)
        folded = c is not None and (abs(c[0]) > 50.0 or c[2] < 0.0)
        print(f"  Image  disc centroid = {np.round(c, 3).tolist()}  {'FOLDED to sensor' if folded else 'STRAIGHT AXIS <-- wrong'}")

    # Faithfulness: exported analytic disc placement (TRANS_2A -- what the writer uses)
    # vs the DISPLAY's authoritative folded surface world point (_surface_reference_world_point,
    # used by the on-screen thickness dimensions). They must coincide per surface.
    print("\nexport (TRANS_2A) vs display (_surface_reference_world_point) per surface:")
    worst = 0.0
    for j, (r, s) in enumerate(zip(rows, getattr(system, "SDT", []))):
        if not getattr(s, "Drawing", 1) or float(getattr(s, "Diameter", 0)) <= 0:
            continue
        try:
            disp = np.asarray(app._surface_reference_world_point(j, system=system), dtype=float).reshape(3)
        except Exception as exc:
            print(f"  j={j:2d} {r.surface:9s} display point unavailable: {exc}")
            continue
        exp = _disc_centroid(system, j)
        d = float(np.linalg.norm(disp - exp))
        worst = max(worst, d)
        print(f"  j={j:2d} {r.surface:9s} export={np.round(exp,2).tolist()} display={np.round(disp,2).tolist()} delta={d:.3f}")
    print(f"worst surface delta = {worst:.3f} mm  {'<-- MISMATCH' if worst > 1.0 else 'ok'}")

    cad_shapes = app._collect_native_step_export_shapes(system)
    ray_polylines = app._step_export_ray_polylines(system)
    rows_snapshot = [SurfaceRow(**asdict(r)) for r in rows]
    with TemporaryDirectory() as tmp:
        out = Path(tmp) / "az85.step"
        analytic, cad, rays = _write_step_with_cad_shapes_and_rays(
            system, rows_snapshot, cad_shapes, ray_polylines, out,
        )
        size = out.stat().st_size if out.exists() else 0
        print(f"\nwriter: analytic_surfaces={analytic}  cad_bodies={cad}  ray_envelopes={rays}  file_bytes={size}")
        drawable = sum(
            1
            for r, s in zip(rows, getattr(system, "SDT", []))
            if getattr(s, "Drawing", 1) and float(getattr(s, "Diameter", 0)) > 0
        )
        print(f"drawable rows (Drawing + Diameter>0) = {drawable}")
        assert size > 0, "STEP file empty"
        assert analytic >= 2, "expected Object + Image discs in the analytic count"
    print("\nOK: export ran, Object/Image planes included, file non-empty.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
