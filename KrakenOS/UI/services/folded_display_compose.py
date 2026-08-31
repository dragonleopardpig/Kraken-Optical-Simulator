"""bugs/0671 -- the FOLDED assembly view: the verified straight trace re-arranged
into the real CAD world by pure reflections.

The om05a two-side station (bugs/0670) traces as ONE straight chain -- the honest
prescription. Its REAL geometry has five 45-degree folds per arm (outer prism, lower
prism, centre prism, RA mirror 1, RA mirror 2 -- the last two shared). This module
generalises the two-arm display-fold idea (straight per-arm SEQUENTIAL trace + a
display fold, [[project_two_arm_display_fold]]) from ONE +Y fold to an ARBITRARY
ordered list of fold planes per arm:

- Each arm carries a START FRAME (chain coords -> world: the device face's pose) and
  its ordered fold planes (point + normal; the reflection is sign-agnostic).
- A traced polyline is placed by the start frame, then each plane in order reflects
  the tail beyond its first crossing (crossing vertex inserted -- the 0103 lesson:
  reflect about the ACTUAL tilted plane, per ray).
- Reflections are isometries: the folded path has the SAME lengths the trace
  computed -- the display IS the physics, re-arranged (feedback: display must follow
  the physics engine; this never invents geometry).

The fold spec is DATA persisted in the layout settings (``display_fold_spec``):
    {"body_step": "attachment/....stp",           # the assembly CAD, drawn as-is
     "arms": [{"origin": [x,y,z], "u": [..], "v": [..], "n": [..],
               "y_center": 5.5, "y_range": [0.5, 1e9],
               "folds": [{"point": [..], "normal": [..]}, ...]}, ...]}
Arm selection: a ray belongs to the arm whose ``y_range`` contains its START y in
chain coordinates (the om05a patches sit at +-1..10 mm; the empty gap between the
faces carries no physical ray and is dropped).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _unit(v) -> np.ndarray:
    v = np.asarray(v, dtype=float).reshape(3)
    return v / float(np.linalg.norm(v))


def reflect_points(points: np.ndarray, plane_point, plane_normal) -> np.ndarray:
    n = _unit(plane_normal)
    d = (points - np.asarray(plane_point, dtype=float)) @ n
    return points - 2.0 * np.outer(d, n)


def fold_polyline(points_chain: np.ndarray, arm: dict[str, Any]) -> np.ndarray:
    """Chain-coordinate polyline -> folded WORLD polyline for one arm."""
    pts = np.asarray(points_chain, dtype=float).reshape(-1, 3)
    O = np.asarray(arm["origin"], dtype=float).reshape(3)
    U, V, N = _unit(arm["u"]), _unit(arm["v"]), _unit(arm["n"])
    y_c = float(arm.get("y_center", 0.0))
    world = O + np.outer(pts[:, 0], U) + np.outer(pts[:, 1] - y_c, V) + np.outer(pts[:, 2], N)
    start = 1  # a fold can never claim the launch point itself
    for fold in (arm.get("folds") or []):
        p0 = np.asarray(fold["point"], dtype=float).reshape(3)
        n = _unit(fold["normal"])
        d = (world - p0) @ n
        cross = None
        for i in range(start - 1, len(world) - 1):
            if d[i] == 0.0 and i >= start:
                cross, t = i, 0.0
                break
            if d[i] * d[i + 1] < 0.0:
                cross, t = i, float(d[i] / (d[i] - d[i + 1]))
                break
        if cross is None:
            break  # the ray terminated before this fold -- draw what physically exists
        vertex = world[cross] + t * (world[cross + 1] - world[cross])
        tail = reflect_points(world[cross + 1:], p0, n)
        world = np.vstack([world[: cross + 1], vertex[None, :], tail])
        d_check = None  # noqa: F841  (clarity: distances recomputed next plane)
        start = cross + 2
    return world


def arm_for_start_y(spec: dict[str, Any], y0: float) -> dict[str, Any] | None:
    """The arm whose y_range holds the ray's START -- None also when the start lies
    outside the arm's PHYSICAL aperture (``aperture_half`` around ``y_center``): the
    om05a prisms are 10.5 mm tall, so a 54 mm-FOV field launched beyond the device
    face never enters the glass; folding it would draw light the assembly cannot
    carry (bugs/0671 -- the folded view shows only physical rays)."""
    for arm in (spec.get("arms") or []):
        lo, hi = arm.get("y_range", (-np.inf, np.inf))
        if not (float(lo) <= y0 <= float(hi)):
            continue
        half = arm.get("aperture_half")
        if half is not None and abs(y0 - float(arm.get("y_center", 0.0))) > float(half):
            return None
        return arm
    return None


def resolve_body_step(spec: dict[str, Any]) -> Path | None:
    raw = str(spec.get("body_step") or "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path if path.exists() else None


def compose_folded_assembly_plotter(editor, *, off_screen: bool = False):
    """One pyvista scene: the assembly CAD body + every traced ray folded into it.
    Returns (plotter, report)."""
    import pyvista as pv

    spec = getattr(editor, "display_fold_spec", None)
    if not (isinstance(spec, dict) and (spec.get("arms") or [])):
        raise ValueError("this layout carries no display_fold_spec")
    plotter = pv.Plotter(off_screen=off_screen)
    try:
        plotter.set_background("white")
    except Exception:
        pass
    report: dict[str, Any] = {"rays": 0, "dropped": 0, "arms": {}, "body": False, "errors": []}

    body = resolve_body_step(spec)
    if body is not None:
        try:
            mesh = editor._load_step_mesh(body, largest_component=False)
            if mesh is not None and int(getattr(mesh, "n_points", 0)) > 0:
                plotter.add_mesh(mesh, color=(0.68, 0.70, 0.74), opacity=0.28, smooth_shading=True)
                report["body"] = True
        except Exception as exc:
            report["errors"].append(f"body: {exc}")

    try:
        editor._preview_trace_deferred_until_requested = False
    except Exception:
        pass
    system, rays, bundle = editor._build_preview_system_rays_bundle(trace_rays=True)
    for rp in (getattr(bundle, "ray_paths", None) or []):
        pts = np.asarray(getattr(rp, "points_world", rp), dtype=float)
        if pts.ndim != 2 or pts.shape[0] < 2 or not np.all(np.isfinite(pts[0])):
            continue
        finite = np.all(np.isfinite(pts), axis=1)
        pts = pts[finite]
        if pts.shape[0] < 2:
            continue
        arm = arm_for_start_y(spec, float(pts[0, 1]))
        if arm is None:
            report["dropped"] += 1  # e.g. the axis field launched in the gap between faces
            continue
        try:
            world = fold_polyline(pts, arm)
            line = pv.lines_from_points(world)
            color = str(getattr(rp, "color", "") or "#39FF14")
            plotter.add_mesh(line, color=color, line_width=1.6, opacity=0.85)
            key = id(arm)
            report["arms"][key] = report["arms"].get(key, 0) + 1
            report["rays"] += 1
        except Exception as exc:
            report["errors"].append(f"ray: {exc}")
    report["arms"] = list(report["arms"].values())

    # the shared sensor: fold the first arm's axis to the image plane and outline it
    try:
        rows = editor.rows
        z_img = sum(float(r.thickness) for r in rows[:-1])
        arm0 = (spec.get("arms") or [])[0]
        axis = fold_polyline(np.asarray([[0.0, float(arm0.get("y_center", 0.0)), 0.0],
                                         [0.0, float(arm0.get("y_center", 0.0)), z_img]]), arm0)
        centre = axis[-1]
        direction = _unit(axis[-1] - axis[-2])
        half = float(rows[-1].diameter) / (2.0 * np.sqrt(2.0))
        a = _unit(np.cross(direction, [1.0, 0.0, 0.0] if abs(direction[0]) < 0.9 else [0.0, 1.0, 0.0]))
        b = np.cross(direction, a)
        loop = np.asarray([centre + sx * half * a + sy * half * b
                           for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1), (-1, -1))])
        plotter.add_mesh(pv.lines_from_points(loop), color=(0.1, 0.5, 0.1), line_width=3.0)
        report["sensor_center"] = centre.tolist()
    except Exception as exc:
        report["errors"].append(f"sensor: {exc}")
    return plotter, report
