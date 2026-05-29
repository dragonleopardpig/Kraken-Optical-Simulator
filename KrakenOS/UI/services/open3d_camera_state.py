"""Camera state capture/restore helpers.

Ports the camera-persistence surface of Slicer's ``vtkMRMLCameraNode``:
a structured snapshot of the active VTK camera that can be captured at
refresh-start and re-applied after the scene is rebuilt, without the
ad-hoc ``dict[str, tuple]`` pattern that Open3DSceneRefreshService
currently inlines.

Today only ``refresh_scene`` uses these helpers. Phase 9+ can hand them
out to a future Open3DCameraPresetService so view-preset switching
(iso / XY / XZ / YZ / bottom) routes through the same dataclass and
fires observer hooks instead of mutating the active camera directly.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CameraState:
    """Snapshot of an active VTK camera that survives RemoveAllViewProps."""

    position: tuple[float, float, float]
    focal_point: tuple[float, float, float]
    view_up: tuple[float, float, float]
    parallel_projection: int
    parallel_scale: float

    def is_finite(self) -> bool:
        for triple in (self.position, self.focal_point, self.view_up):
            for value in triple:
                if not _isfinite(value):
                    return False
        return _isfinite(self.parallel_scale)


def _isfinite(value: float) -> bool:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return False
    return value == value and value not in (float("inf"), float("-inf"))


def capture_camera_state(renderer, *, require_valid_bounds: bool = True) -> CameraState | None:
    """Return a CameraState from the renderer's active camera, or None."""
    if renderer is None:
        return None
    if require_valid_bounds:
        try:
            import numpy as _np

            bounds = _np.asarray(renderer.ComputeVisiblePropBounds(), dtype=float)
            if bounds.size != 6:
                return None
            if not _np.all(_np.isfinite(bounds)):
                return None
            if not (bounds[0] <= bounds[1] and bounds[2] <= bounds[3] and bounds[4] <= bounds[5]):
                return None
        except Exception:
            return None
    try:
        camera = renderer.GetActiveCamera()
    except Exception:
        camera = None
    if camera is None:
        return None
    try:
        state = CameraState(
            position=tuple(float(value) for value in camera.GetPosition()),
            focal_point=tuple(float(value) for value in camera.GetFocalPoint()),
            view_up=tuple(float(value) for value in camera.GetViewUp()),
            parallel_projection=int(camera.GetParallelProjection()),
            parallel_scale=float(camera.GetParallelScale()),
        )
    except Exception:
        return None
    return state if state.is_finite() else None


def apply_camera_state(renderer, state: CameraState | None) -> bool:
    """Push ``state`` back onto the renderer's active camera. Return True on success."""
    if renderer is None or state is None:
        return False
    try:
        camera = renderer.GetActiveCamera()
    except Exception:
        camera = None
    if camera is None:
        return False
    try:
        camera.SetPosition(*state.position)
        camera.SetFocalPoint(*state.focal_point)
        camera.SetViewUp(*state.view_up)
        camera.SetParallelProjection(int(state.parallel_projection))
        camera.SetParallelScale(float(state.parallel_scale))
    except Exception:
        return False
    return True
