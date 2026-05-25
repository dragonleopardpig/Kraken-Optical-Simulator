"""Open 3D carry grip-marker actor helpers."""

from __future__ import annotations

from typing import Any

import numpy as np


class Open3DCarryGripService:
    """Own the in-scene carry grip marker actor for an Open 3D inspector."""

    def __init__(self, inspector: Any) -> None:
        self.inspector = inspector
        self.actor = None

    @staticmethod
    def _pyvista_module():
        try:
            import pyvista as pv  # type: ignore
        except Exception:
            return None
        return pv

    def clear(self, *, render: bool = True) -> None:
        actor = self.actor
        self.actor = None
        renderer = getattr(self.inspector, "_renderer", None)
        if actor is None or renderer is None:
            return
        try:
            renderer.RemoveActor(actor)
        except Exception:
            pass
        if render:
            self.inspector.render()

    def mesh(self, center):
        pv = self._pyvista_module()
        if pv is None:
            return None
        try:
            point = np.asarray(center, dtype=float).reshape(-1)[:3]
        except Exception:
            return None
        if point.size < 3 or not np.all(np.isfinite(point[:3])):
            return None
        _scene_center, scene_span = self.inspector._scene_bounds()
        radius = max(min(float(scene_span) * 0.018, 3.0), 0.35)
        parts = []
        try:
            parts.append(
                pv.Sphere(
                    radius=radius,
                    center=tuple(float(value) for value in point[:3]),
                    theta_resolution=16,
                    phi_resolution=8,
                )
            )
        except Exception:
            pass
        for axis in np.eye(3):
            try:
                start = point[:3] - axis * radius * 2.8
                end = point[:3] + axis * radius * 2.8
                parts.append(pv.Line(tuple(start), tuple(end)))
            except Exception:
                pass
        if not parts:
            return None
        mesh = parts[0]
        for part in parts[1:]:
            try:
                mesh = mesh.merge(part)
            except Exception:
                pass
        return mesh

    def show(self, center) -> None:
        self.clear(render=False)
        mesh = self.mesh(center)
        if mesh is None:
            return
        actor = self.inspector._add_mesh_actor(
            mesh,
            color=(1.0, 0.82, 0.06),
            opacity=0.98,
            line_width=4.0,
            flat_shading=True,
        )
        if actor is None:
            return
        try:
            actor.PickableOff()
        except Exception:
            pass
        self.actor = actor
        self.inspector.render()

    def translate(self, delta_xyz) -> None:
        actor = self.actor
        if actor is None:
            return
        try:
            delta = np.asarray(delta_xyz, dtype=float).reshape(-1)[:3]
        except Exception:
            return
        if delta.size < 3 or not np.all(np.isfinite(delta[:3])):
            return
        try:
            actor.AddPosition(float(delta[0]), float(delta[1]), float(delta[2]))
        except Exception:
            pass

    def update_after_delta(self, state: dict[str, object], delta_xyz) -> None:
        try:
            delta = np.asarray(delta_xyz, dtype=float).reshape(-1)[:3]
            grip = np.asarray(state.get("grip_world"), dtype=float).reshape(-1)[:3]
            center = np.asarray(state.get("center_world"), dtype=float).reshape(-1)[:3]
        except Exception:
            return
        if delta.size < 3 or grip.size < 3 or not np.all(np.isfinite(delta[:3])) or not np.all(np.isfinite(grip[:3])):
            return
        grip = grip[:3] + delta[:3]
        state["grip_world"] = tuple(float(value) for value in grip[:3])
        if center.size >= 3 and np.all(np.isfinite(center[:3])):
            center = center[:3] + delta[:3]
            state["center_world"] = tuple(float(value) for value in center[:3])
        if self.actor is None:
            self.show(grip[:3])
        else:
            self.translate(delta[:3])
