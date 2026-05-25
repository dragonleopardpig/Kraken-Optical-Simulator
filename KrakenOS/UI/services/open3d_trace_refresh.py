"""Open 3D trace and refresh orchestration.

This service is intentionally toolkit-light.  It owns the sampling-mode and
SceneBundle refresh policy, while the Tk/VTK inspector still owns rendering and
user interaction state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class Open3DRefreshResult:
    sampling_mode: str | None
    system: Any
    rays: Any
    scene_bundle: Any
    row_names: list[str]


class Open3DTraceRefreshService:
    """Coordinate Open 3D trace rebuilds without owning the UI widgets."""

    def __init__(self, editor: Any) -> None:
        self.editor = editor

    @staticmethod
    def normalize_sampling_mode_label(sampling_mode: object) -> str | None:
        mode = str(sampling_mode or "").strip().lower()
        return mode or None

    @staticmethod
    def sampling_mode_is_open3d_scene(mode: object) -> bool:
        normalized = Open3DTraceRefreshService.normalize_sampling_mode_label(mode)
        return normalized in {
            "full_pupil",
            "world_envelope",
            "world_sections",
            "source_cone_world",
            "world_source_cone",
            "point_cone_world",
        }

    def inspector_active_sampling_mode(self, inspector: Any) -> str | None:
        mode = self.normalize_sampling_mode_label(getattr(inspector, "_last_refresh_sampling_mode", None))
        if mode is not None:
            return mode
        return self.normalize_sampling_mode_label(getattr(self.editor, "_active_preview_sampling_mode", None))

    def remember_inspector_sampling_mode(self, inspector: Any, sampling_mode: object) -> None:
        mode = self.normalize_sampling_mode_label(sampling_mode)
        if mode is not None:
            inspector._last_refresh_sampling_mode = mode

    def has_traceable_step_overlays(self) -> bool:
        """Return True when Open 3D must add transient STEP rows before tracing."""
        try:
            return self.editor._step_path_for_label("optical") is not None
        except Exception:
            return False

    def build_inspector_refresh(
        self,
        inspector: Any,
        *,
        sampling_mode: str | None = None,
        force_retrace: bool = False,
        update_state: bool = True,
    ) -> Open3DRefreshResult:
        resolved_sampling_mode = self.normalize_sampling_mode_label(sampling_mode)
        open3d_sampling_mode = None
        current = None
        include_live_step_overlays = self.has_traceable_step_overlays()
        if not include_live_step_overlays and not force_retrace and resolved_sampling_mode is None:
            open3d_sampling_mode = self.normalize_sampling_mode_label(self.editor._preview_3d_sampling_mode())
            current_mode = self.normalize_sampling_mode_label(getattr(self.editor, "_active_preview_sampling_mode", None))
            if current_mode == open3d_sampling_mode or self.sampling_mode_is_open3d_scene(current_mode):
                current = self.editor._current_preview_scene_trace()
        if current is not None:
            system, rays, scene_bundle = current
            resolved_sampling_mode = self.normalize_sampling_mode_label(
                getattr(self.editor, "_active_preview_sampling_mode", None)
            )
        else:
            if resolved_sampling_mode is None and force_retrace:
                resolved_sampling_mode = self.inspector_active_sampling_mode(inspector)
            if resolved_sampling_mode is None:
                if open3d_sampling_mode is None:
                    open3d_sampling_mode = self.normalize_sampling_mode_label(self.editor._preview_3d_sampling_mode())
                resolved_sampling_mode = open3d_sampling_mode
            system, rays, scene_bundle = self.editor._build_preview_system_rays_bundle(
                sampling_mode=resolved_sampling_mode,
                update_state=bool(update_state),
                include_live_step_overlays=include_live_step_overlays,
            )
        self.remember_inspector_sampling_mode(inspector, resolved_sampling_mode)
        row_names = self.editor._preview_render_row_names(scene_bundle)
        return Open3DRefreshResult(
            sampling_mode=resolved_sampling_mode,
            system=system,
            rays=rays,
            scene_bundle=scene_bundle,
            row_names=row_names,
        )

    def build_live_preview(self, inspector: Any) -> Open3DRefreshResult:
        sampling_mode = self.editor._preview_3d_sampling_mode()
        system, rays, scene_bundle = self.editor._build_preview_system_rays_bundle(
            sampling_mode=sampling_mode,
            update_state=False,
            include_live_step_overlays=True,
        )
        self.remember_inspector_sampling_mode(inspector, sampling_mode)
        row_names = self.editor._preview_render_row_names(scene_bundle)
        return Open3DRefreshResult(
            sampling_mode=self.normalize_sampling_mode_label(sampling_mode),
            system=system,
            rays=rays,
            scene_bundle=scene_bundle,
            row_names=row_names,
        )

    def build_trace_now_preview(self, inspector: Any) -> Open3DRefreshResult:
        sampling_mode = self.inspector_active_sampling_mode(inspector)
        if sampling_mode is None:
            sampling_mode = self.editor._preview_3d_sampling_mode()
        system, rays, scene_bundle = self.editor._build_preview_system_rays_bundle(
            sampling_mode=sampling_mode,
            update_state=False,
            include_live_step_overlays=True,
        )
        self.remember_inspector_sampling_mode(inspector, sampling_mode)
        row_names = self.editor._preview_render_row_names(scene_bundle)
        return Open3DRefreshResult(
            sampling_mode=self.normalize_sampling_mode_label(sampling_mode),
            system=system,
            rays=rays,
            scene_bundle=scene_bundle,
            row_names=row_names,
        )

    def current_or_rebuild_scene(
        self,
        *,
        system: Any = None,
        rays: Any = None,
        scene_bundle: Any = None,
    ) -> Open3DRefreshResult:
        include_live_step_overlays = self.has_traceable_step_overlays()
        if system is None or rays is None or scene_bundle is None:
            current = None if include_live_step_overlays else self.editor._current_preview_scene_trace()
            if current is not None:
                system, rays, scene_bundle = current
                sampling_mode = self.normalize_sampling_mode_label(
                    getattr(self.editor, "_active_preview_sampling_mode", None)
                )
            else:
                sampling_mode = self.editor._preview_3d_sampling_mode()
                system, rays, scene_bundle = self.editor._build_preview_system_rays_bundle(
                    sampling_mode=sampling_mode,
                    update_state=False,
                    include_live_step_overlays=include_live_step_overlays,
                )
        else:
            sampling_mode = self.normalize_sampling_mode_label(
                getattr(self.editor, "_active_preview_sampling_mode", None)
            )
        row_names = self.editor._preview_render_row_names(scene_bundle)
        return Open3DRefreshResult(
            sampling_mode=self.normalize_sampling_mode_label(sampling_mode),
            system=system,
            rays=rays,
            scene_bundle=scene_bundle,
            row_names=row_names,
        )

    def sync_open_inspector(
        self,
        *,
        system: Any = None,
        rays: Any = None,
        scene_bundle: Any = None,
        reset_camera: bool = False,
    ) -> bool:
        inspector = getattr(self.editor, "_three_d_inspector", None)
        if inspector is None:
            return False
        try:
            if not inspector.winfo_exists():
                self.editor._three_d_inspector = None
                return False
        except Exception:
            self.editor._three_d_inspector = None
            return False
        result = self.current_or_rebuild_scene(
            system=system,
            rays=rays,
            scene_bundle=scene_bundle,
        )
        self.remember_inspector_sampling_mode(inspector, result.sampling_mode)
        inspector.refresh_scene(
            result.system,
            result.rays,
            result.row_names,
            scene_bundle=result.scene_bundle,
            reset_camera=bool(reset_camera),
        )
        return True
