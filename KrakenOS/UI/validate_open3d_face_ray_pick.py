"""Validate through-body Open 3D face picking for internal CAD planes."""

from __future__ import annotations

import numpy as np

from KrakenOS.UI.services.open3d_face_pick import pick_face_from_ray


def _quad(a, b, c, d) -> list[tuple[tuple[float, float, float], ...]]:
    return [(a, b, c), (a, c, d)]


def _cube_with_internal_diagonal() -> tuple[list[dict[str, object]], np.ndarray]:
    s = 25.0
    triangles: list[tuple[tuple[float, float, float], ...]] = []
    faces: list[dict[str, object]] = []

    def add_face(face_id: str, normal, quad_points) -> None:
        start = len(triangles)
        face_triangles = _quad(*quad_points)
        triangles.extend(face_triangles)
        points = np.asarray(face_triangles, dtype=float).reshape((-1, 3))
        faces.append(
            {
                "face_id": face_id,
                "normal": list(normal),
                "centroid": list(np.mean(points, axis=0)),
                "triangle_indices": [start, start + 1],
            }
        )

    add_face("XMIN", (-1.0, 0.0, 0.0), ((0, 0, 0), (0, s, 0), (0, s, s), (0, 0, s)))
    add_face("XMAX", (1.0, 0.0, 0.0), ((s, 0, 0), (s, 0, s), (s, s, s), (s, s, 0)))
    add_face("YMIN", (0.0, -1.0, 0.0), ((0, 0, 0), (0, 0, s), (s, 0, s), (s, 0, 0)))
    add_face("YMAX", (0.0, 1.0, 0.0), ((0, s, 0), (s, s, 0), (s, s, s), (0, s, s)))
    add_face("ZMIN", (0.0, 0.0, -1.0), ((0, 0, 0), (s, 0, 0), (s, s, 0), (0, s, 0)))
    add_face("ZMAX", (0.0, 0.0, 1.0), ((0, 0, s), (0, s, s), (s, s, s), (s, 0, s)))
    diagonal_normal = np.asarray((1.0, -1.0, 0.0), dtype=float)
    diagonal_normal /= float(np.linalg.norm(diagonal_normal))
    add_face("SPLITTER", diagonal_normal, ((0, 0, 0), (s, s, 0), (s, s, s), (0, 0, s)))
    return faces, np.asarray(triangles, dtype=float)


def main() -> int:
    faces, triangles = _cube_with_internal_diagonal()
    origin = np.asarray((50.0, 12.5, 12.5), dtype=float)
    direction = np.asarray((-1.0, 0.0, 0.0), dtype=float)
    nearest = pick_face_from_ray(
        faces,
        triangles,
        origin,
        direction,
        prefer_internal=False,
    )
    through = pick_face_from_ray(
        faces,
        triangles,
        origin,
        direction,
        prefer_internal=True,
    )
    if nearest is None or nearest.face.get("face_id") != "XMAX":
        raise AssertionError(f"Expected nearest shell face XMAX, got {nearest}")
    if through is None or through.face.get("face_id") != "SPLITTER" or not through.internal:
        raise AssertionError(f"Expected through-body internal SPLITTER face, got {through}")
    point = np.asarray(through.point_world, dtype=float)
    expected = np.asarray((12.5, 12.5, 12.5), dtype=float)
    if float(np.linalg.norm(point - expected)) > 1e-9:
        raise AssertionError(f"Unexpected splitter hit point {point}, expected {expected}")
    print("Open 3D face ray-pick validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
