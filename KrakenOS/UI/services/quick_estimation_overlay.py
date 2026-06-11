"""Quick Estimation 3D overlays: FOV circles + sensor rectangle on the planes.

Drawn during the Open 3D scene refresh when Quick Estimation is enabled:

* Object plane -- a solid circle at the current object field-of-view radius, and
  a dashed "ghost" circle at the previous FOV so a change reads as bigger/smaller.
* Image plane -- a solid circle at the image footprint (the image of the object),
  the recommended rectangular sensor inscribed in it (so the user sees the image
  circle covering the sensor), and a dashed ghost of the previous image circle.

The full refresh calls ``RemoveAllViewProps`` first, so overlays are simply
re-added each refresh; no separate actor lifecycle is needed.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def _basis(axis: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    norm = float(np.linalg.norm(axis))
    axis = axis / norm if norm > 1e-9 else np.array([0.0, 0.0, 1.0])
    ref = np.array([0.0, 0.0, 1.0]) if abs(axis[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    u = np.cross(axis, ref)
    nu = float(np.linalg.norm(u))
    u = u / nu if nu > 1e-9 else np.array([1.0, 0.0, 0.0])
    v = np.cross(axis, u)
    return u, v


def _circle_points(center, u, v, radius, n=72):
    th = np.linspace(0.0, 2.0 * np.pi, n, endpoint=True)
    return center + radius * (np.outer(np.cos(th), u) + np.outer(np.sin(th), v))


def _rect_points(center, u, v, half_w, half_h):
    return np.array([
        center + half_w * u + half_h * v,
        center - half_w * u + half_h * v,
        center - half_w * u - half_h * v,
        center + half_w * u - half_h * v,
        center + half_w * u + half_h * v,
    ])


class QuickEstimationOverlayService:
    """Build the FOV-circle / sensor-rectangle overlays for Open 3D."""

    def __init__(self, inspector: Any, *, pv_module: Any) -> None:
        self.inspector = inspector
        self.editor = inspector.editor
        self._pv = pv_module

    def _solid_line_actor(self, points, color, width):
        pv = self._pv
        if pv is None:
            return
        try:
            mesh = pv.lines_from_points(np.asarray(points, dtype=float))
            self.inspector._add_mesh_actor(mesh, color=color, line_width=width, opacity=1.0)
        except Exception as exc:
            self.editor.append_debug(f"QE overlay solid line skipped: {exc}")

    def _dashed_line_actor(self, points, color, width):
        pv = self._pv
        if pv is None:
            return
        try:
            pts = np.asarray(points, dtype=float)
            n = len(pts)
            cells = []
            for i in range(0, n - 1, 2):  # every other segment -> dashed
                cells += [2, i, i + 1]
            if not cells:
                return
            mesh = pv.PolyData(pts, lines=np.asarray(cells, dtype=np.int64))
            self.inspector._add_mesh_actor(mesh, color=color, line_width=width, opacity=0.9)
        except Exception as exc:
            self.editor.append_debug(f"QE overlay dashed line skipped: {exc}")

    def _pick_disk_actor(self, center, normal, radius, color, row_index):
        """A faint, filled, *pickable* disk at a plane so the row can be picked /
        hover-highlighted / double-clicked (bugs/0055 follow-up). Without it the
        Object plane has no 3D geometry to click -- only the terminal sensor's
        detector footprint was ever pickable, so the object plane never lit up on
        hover and the FOV double-click could not reach it."""
        pv = self._pv
        if pv is None:
            return
        try:
            c = np.asarray(center, dtype=float).reshape(3)
            n = np.asarray(normal, dtype=float).reshape(3)
            nn = float(np.linalg.norm(n))
            if not np.isfinite(nn) or nn <= 1e-9:
                return
            n = n / nn
            r = float(radius)
            if not np.isfinite(r) or r <= 1e-9:
                return
            disk = pv.Disc(
                center=tuple(float(v) for v in c),
                inner=0.0,
                outer=r,
                normal=tuple(float(v) for v in n),
                r_res=1,
                c_res=64,
            )
            self.inspector._add_mesh_actor(
                disk,
                color=color,
                opacity=0.10,
                flat_shading=True,
                backface_culling=False,
                pick_row_index=int(row_index),
            )
        except Exception as exc:
            self.editor.append_debug(f"QE overlay pick disk skipped: {exc}")

    def add_overlays(self, system: Any, scene_bundle: Any = None) -> int:
        qe = self.inspector._quick_estimation_service()
        if not qe.is_enabled():
            return 0
        rows = getattr(self.editor, "rows", None) or []
        if len(rows) < 3:
            return 0
        state = qe.current_state()
        if state.get("object_mode") != "Finite":
            return 0
        mag = state.get("magnification")
        fov_semi = state.get("fov_semi")
        if not mag or not fov_semi or not np.isfinite(mag):
            return 0
        try:
            obj_pt = np.asarray(self.editor._surface_reference_world_point(0, system=system), dtype=float).reshape(3)
            img_pt = np.asarray(self.editor._surface_reference_world_point(len(rows) - 1, system=system), dtype=float).reshape(3)
        except Exception as exc:
            self.editor.append_debug(f"QE overlay reference points unavailable: {exc}")
            return 0
        axis = img_pt - obj_pt
        u, v = _basis(axis)

        target = qe.target_object_semi()
        object_semi = float(target) if target else float(fov_semi)        # object extent
        image_radius = abs(float(mag)) * object_semi                       # image footprint
        prev_object_semi = qe.previous_object_semi()
        rec = state.get("recommended_sensor") or {}
        count = 0

        # --- pickable plane disks so the Object/Image planes can be clicked,
        #     hover-highlighted, and double-clicked for the FOV popup (bugs/0055).
        self._pick_disk_actor(obj_pt, axis, max(object_semi, 0.5), (0.2, 0.9, 0.35), 0)
        self._pick_disk_actor(img_pt, axis, max(image_radius, 0.5), (0.2, 0.7, 1.0), len(rows) - 1)

        # --- object plane: current FOV circle (green) + previous ghost (gray) ---
        self._solid_line_actor(_circle_points(obj_pt, u, v, object_semi), (0.2, 0.9, 0.35), 2.5)
        count += 1
        if prev_object_semi and abs(prev_object_semi - object_semi) > 1e-6 * max(1.0, object_semi):
            self._dashed_line_actor(_circle_points(obj_pt, u, v, prev_object_semi), (0.65, 0.65, 0.65), 2.0)
            count += 1

        # --- image plane: image circle (cyan) + recommended sensor rect (yellow)
        #     + previous image circle ghost (gray) ---
        self._solid_line_actor(_circle_points(img_pt, u, v, image_radius), (0.2, 0.7, 1.0), 2.5)
        count += 1
        if rec:
            half_w = float(rec.get("width", 0.0)) / 2.0
            half_h = float(rec.get("height", 0.0)) / 2.0
            if half_w > 0 and half_h > 0:
                self._solid_line_actor(_rect_points(img_pt, u, v, half_w, half_h), (1.0, 0.9, 0.2), 2.5)
                count += 1
        if prev_object_semi and abs(prev_object_semi - object_semi) > 1e-6 * max(1.0, object_semi):
            prev_image_radius = abs(float(mag)) * float(prev_object_semi)
            self._dashed_line_actor(_circle_points(img_pt, u, v, prev_image_radius), (0.65, 0.65, 0.65), 2.0)
            count += 1
        return count
