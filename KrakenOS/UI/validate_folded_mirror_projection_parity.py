"""Validate folded mirror geometry is congruent in 2-D and Open 3-D."""

from __future__ import annotations

import numpy as np

import KrakenOS.UI.layout_editor as le
from KrakenOS.UI.layout_editor import KrakenLayoutEditor


def _normalize_line_angle_deg(angle: float) -> float:
    value = float(angle)
    while value <= -90.0:
        value += 180.0
    while value > 90.0:
        value -= 180.0
    return 0.0 if abs(value) < 1.0e-12 else value


def _line_angle_yz(points_xyz: np.ndarray) -> float:
    points = np.asarray(points_xyz, dtype=float)
    if points.ndim != 2 or points.shape[0] < 2 or points.shape[1] < 3:
        raise ValueError("expected at least two XYZ points")
    yz = np.column_stack((points[:, 2], points[:, 1]))
    finite = np.all(np.isfinite(yz), axis=1)
    yz = yz[finite]
    if yz.shape[0] < 2:
        raise ValueError("expected at least two finite YZ points")
    centered = yz - np.mean(yz, axis=0)
    covariance = centered.T @ centered
    values, vectors = np.linalg.eigh(covariance)
    vector = vectors[:, int(np.argmax(values))]
    return _normalize_line_angle_deg(np.rad2deg(np.arctan2(vector[1], vector[0])))


def _curve_angle_yz(curve: object) -> float:
    points = np.asarray(getattr(curve, "points_world", []), dtype=float)
    if points.ndim != 2 or points.shape[0] < 2:
        raise ValueError("expected curve points")
    coordinate_space = str(getattr(curve, "coordinate_space", "world") or "world")
    if coordinate_space == "folded_yz_display":
        p0 = points[0, :2]
        p1 = points[-1, :2]
        return _normalize_line_angle_deg(np.rad2deg(np.arctan2(p1[1] - p0[1], p1[0] - p0[0])))
    if points.shape[1] >= 3:
        return _line_angle_yz(points)
    p0 = points[0, :2]
    p1 = points[-1, :2]
    return _normalize_line_angle_deg(np.rad2deg(np.arctan2(p1[1] - p0[1], p1[0] - p0[0])))


def _angle_delta_deg(a: float, b: float) -> float:
    delta = _normalize_line_angle_deg(float(a) - float(b))
    return abs(delta)


def main() -> int:
    failures: list[str] = []
    le._load_3d_backends()
    app = KrakenLayoutEditor(headless=True)
    try:
        app.load_layouts()
        app.load_layout_by_name("Galvo F-Theta Laser Scanner", refresh=False)
        system, _rays, bundle = app._build_preview_system_rays_bundle(update_state=True)
        mirror_indices = [index for index, row in enumerate(app.rows) if row.surface == "Mirror"]
        if not mirror_indices:
            failures.append("Galvo layout has no mirror row")
        for mirror_index in mirror_indices:
            curves = [
                curve
                for curve in list(getattr(bundle, "surface_curves", []) or [])
                if int(getattr(curve, "row_index", -1)) == int(mirror_index)
                and str(getattr(curve, "kind", "") or "") == "mirror"
            ]
            meshes = [
                item
                for item in list(getattr(bundle, "surface_meshes", []) or [])
                if int(getattr(item, "row_index", -1)) == int(mirror_index)
                and str(getattr(item, "kind", "") or "") == "mirror"
                and not bool(getattr(item, "is_body", False))
            ]
            if len(curves) != 1:
                failures.append(f"mirror row {mirror_index}: curve count={len(curves)}, expected 1")
                continue
            if len(meshes) != 1:
                failures.append(f"mirror row {mirror_index}: mesh count={len(meshes)}, expected 1")
                continue
            curve_angle = _curve_angle_yz(curves[0])
            mesh_points = np.asarray(getattr(meshes[0].mesh, "points", []), dtype=float)
            mesh_angle = _line_angle_yz(mesh_points)
            delta = _angle_delta_deg(curve_angle, mesh_angle)
            if delta > 1.0e-6:
                failures.append(
                    f"mirror row {mirror_index}: Open 3D mesh angle {mesh_angle:.6f} deg "
                    f"does not match SceneBundle curve {curve_angle:.6f} deg"
                )
        if str(app._resolved_trace_mode(system=system).get("active", "")) != "Folded Preview":
            failures.append("Galvo layout did not resolve to Folded Preview trace mode")
    finally:
        app.destroy()
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("Folded mirror 2D/Open 3D geometry parity validator passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
