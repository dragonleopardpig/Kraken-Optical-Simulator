"""Validate round lens-like imported STEP face picking contracts."""

from __future__ import annotations

import numpy as np

from KrakenOS.UI.open3d_inspector import Kraken3DInspector


def _cell_normal(data, cell_id: int) -> np.ndarray | None:
    try:
        cell = data.GetCell(int(cell_id))
        ids = cell.GetPointIds()
        points = np.asarray([data.GetPoint(ids.GetId(index)) for index in range(ids.GetNumberOfIds())], dtype=float)
    except Exception:
        return None
    if points.ndim != 2 or points.shape[0] < 3:
        return None
    normal = np.cross(points[1] - points[0], points[2] - points[0])
    norm = float(np.linalg.norm(normal))
    if not np.isfinite(norm) or norm <= 1e-12:
        return None
    return normal / norm


def main() -> int:
    try:
        import pyvista as pv
    except Exception as exc:
        print(f"Open 3D lens STEP face-pick validation skipped: pyvista unavailable ({exc}).")
        return 0

    failures: list[str] = []
    lens = pv.Cylinder(
        center=(0.0, 0.0, 0.0),
        direction=(0.0, 0.0, 1.0),
        radius=12.5,
        height=4.0,
        resolution=96,
    ).triangulate()
    axis_info = Kraken3DInspector._mesh_round_lens_axis(lens)
    if axis_info is None:
        failures.append("Round lens-like cylinder was not classified as lens-like.")
    else:
        _center, axis, _points = axis_info
        seed = None
        for cell_id in range(int(lens.GetNumberOfCells())):
            normal = _cell_normal(lens, cell_id)
            if normal is not None and abs(float(np.dot(normal, axis))) > 0.75:
                seed = cell_id
                break
        if seed is None:
            failures.append("Could not find a round lens cap cell for validation.")
        else:
            feature = Kraken3DInspector._round_lens_feature_for_cell(lens, seed)
            if feature is None:
                failures.append("Round lens cap cell did not return a grouped optical face feature.")
            else:
                center, outline, normal = feature
                if len(center) != 3 or not np.all(np.isfinite(center)):
                    failures.append("Grouped lens face center is not finite.")
                if len(normal) != 3 or abs(float(np.dot(normal, axis))) < 0.95:
                    failures.append("Grouped lens face normal is not aligned to the inferred lens axis.")
                if outline is None or int(getattr(outline, "n_points", 0)) <= 0:
                    failures.append("Grouped lens face did not produce a clean outline.")

    inspector_source = __import__("inspect").getsource(Kraken3DInspector)
    if "_kraken_round_lens_like_step_body" not in inspector_source or "prop.SetEdgeVisibility(0)" not in inspector_source:
        failures.append("Round lens-like STEP selection must suppress raw polygon edge visibility.")
    if "_round_lens_feature_for_cell" not in inspector_source or "_mesh_round_lens_axis" not in inspector_source:
        failures.append("Round lens-like STEP face grouping helpers are missing.")

    if failures:
        print("Open 3D lens STEP face-pick validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Open 3D lens STEP face-pick validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
