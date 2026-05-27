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
            "source_cone_world",
            "world_source_cone",
            "point_cone_world",
        }

    def _active_trace_can_feed_open3d(self) -> bool:
        mode = self.normalize_sampling_mode_label(getattr(self.editor, "_active_preview_sampling_mode", None))
        return self.sampling_mode_is_open3d_scene(mode)

    def _open3d_sampling_mode(self) -> str | None:
        return self.normalize_sampling_mode_label(self.editor._preview_3d_sampling_mode())

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

    @staticmethod
    def inspector_physics_requested(inspector: Any) -> bool:
        """Return True when the inspector is asking for live/visible physics."""
        for attr_name in ("live_mode_var", "show_rays_var"):
            var = getattr(inspector, attr_name, None)
            try:
                if var is not None and bool(var.get()):
                    return True
            except Exception:
                pass
        return False

    def inspector_should_trace_step_overlays(self, inspector: Any, *, force_retrace: bool = False) -> bool:
        """Return True when imported STEP overlays must participate in tracing.

        Imported optical STEP geometry should remain cheap CAD display hardware
        while the user is only placing/selecting it with rays hidden. Physics
        tracing is still forced by Live Mode, Trace Now, or visible rays.
        ``force_retrace`` rebuilds the active preview, but it must not turn a
        hidden-ray CAD placement/drop action into a transient optical trace.
        """
        if not self.has_traceable_step_overlays():
            return False
        return self.inspector_physics_requested(inspector)

    def current_scene_has_live_step_trace(self, inspector: Any) -> bool:
        """Return True when the inspector cache still contains live STEP rows."""
        labels_by_row = inspector._live_trace_step_overlay_label_by_row()
        if not labels_by_row:
            return False
        row_names = list(getattr(inspector, "_current_row_names", []) or [])
        if any(0 <= int(row_index) < len(row_names) for row_index in labels_by_row):
            return True
        scene_bundle = getattr(inspector, "_current_scene_bundle", None)
        if scene_bundle is None:
            return False
        try:
            rows = list(self.editor._preview_render_rows(scene_bundle) or [])
        except Exception:
            rows = []
        return any(0 <= int(row_index) < len(rows) for row_index in labels_by_row)

    def can_reuse_current_scene_for_show_rays(self, inspector: Any) -> bool:
        """Return True when Show Rays can be a display-only refresh."""
        for attr_name in ("_current_system", "_current_rays", "_current_scene_bundle"):
            if getattr(inspector, attr_name, None) is None:
                return False
        if not list(getattr(inspector, "_current_row_names", []) or []):
            return False
        try:
            showing_rays = bool(inspector.show_rays_var.get())
        except Exception:
            showing_rays = False
        if showing_rays and self.has_traceable_step_overlays():
            if not bool(inspector._live_trace_step_overlay_labels()):
                return False
            if not self.current_scene_has_live_step_trace(inspector):
                return False
        return True

    def has_promoted_step_optical_solid_rows(self) -> bool:
        """Return True when saved row-backed STEP solids need an Open 3D trace."""
        try:
            rows = getattr(self.editor, "rows", []) or []
            is_promoted = getattr(self.editor, "_is_open3d_promoted_optical_solid_row")
            return any(bool(is_promoted(row)) for row in rows)
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
        include_live_step_overlays = self.inspector_should_trace_step_overlays(
            inspector,
            force_retrace=bool(force_retrace),
        )
        requires_open3d_retrace = include_live_step_overlays or self.has_promoted_step_optical_solid_rows()
        if resolved_sampling_mode is not None and not self.sampling_mode_is_open3d_scene(resolved_sampling_mode):
            resolved_sampling_mode = self._open3d_sampling_mode()
        if not requires_open3d_retrace and not force_retrace and resolved_sampling_mode is None:
            open3d_sampling_mode = self._open3d_sampling_mode()
            current_mode = self.normalize_sampling_mode_label(getattr(self.editor, "_active_preview_sampling_mode", None))
            if self.sampling_mode_is_open3d_scene(current_mode):
                current = self.editor._current_preview_scene_trace()
        if current is not None:
            system, rays, scene_bundle = current
            resolved_sampling_mode = self.normalize_sampling_mode_label(
                getattr(self.editor, "_active_preview_sampling_mode", None)
            )
        else:
            if resolved_sampling_mode is None and force_retrace:
                resolved_sampling_mode = self.inspector_active_sampling_mode(inspector)
            if resolved_sampling_mode is not None and not self.sampling_mode_is_open3d_scene(resolved_sampling_mode):
                resolved_sampling_mode = self._open3d_sampling_mode()
            if resolved_sampling_mode is None:
                if open3d_sampling_mode is None:
                    open3d_sampling_mode = self._open3d_sampling_mode()
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
        if sampling_mode is None or not self.sampling_mode_is_open3d_scene(sampling_mode):
            sampling_mode = self._open3d_sampling_mode()
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
        requires_open3d_retrace = include_live_step_overlays or self.has_promoted_step_optical_solid_rows()
        if not self._active_trace_can_feed_open3d():
            system = None
            rays = None
            scene_bundle = None
        if requires_open3d_retrace:
            system = None
            rays = None
            scene_bundle = None
        if system is None or rays is None or scene_bundle is None:
            current = None
            if not requires_open3d_retrace and self._active_trace_can_feed_open3d():
                current = self.editor._current_preview_scene_trace()
            if current is not None:
                system, rays, scene_bundle = current
                sampling_mode = self.normalize_sampling_mode_label(
                    getattr(self.editor, "_active_preview_sampling_mode", None)
                )
            else:
                sampling_mode = self._open3d_sampling_mode()
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
