"""Validate that Open 3D Live Mode traces imported optical STEP overlays."""

from __future__ import annotations

import inspect
from dataclasses import dataclass

from KrakenOS.UI.layout_editor import Kraken3DInspector, KrakenLayoutEditor
from KrakenOS.UI.services.open3d_scene_refresh import Open3DSceneRefreshService
from KrakenOS.UI.services.open3d_step_state import Open3DStepStateService
from KrakenOS.UI.services.open3d_trace_refresh import Open3DTraceRefreshService
from KrakenOS.UI.services.step_overlay_promotion import StepOverlayPromotionService


@dataclass
class Open3DLiveTransientStepCheck:
    check: str
    ok: bool
    detail: str


def _editor_contract_source() -> str:
    return "\n".join(
        inspect.getsource(cls)
        for cls in KrakenLayoutEditor.__mro__
        if getattr(cls, "__module__", "").startswith("KrakenOS.UI")
    )


def validate_open3d_live_transient_step() -> list[Open3DLiveTransientStepCheck]:
    inspector_source = inspect.getsource(Kraken3DInspector)
    editor_source = _editor_contract_source()
    open3d_scene_refresh_service = inspect.getsource(Open3DSceneRefreshService)
    open3d_step_state_service = inspect.getsource(Open3DStepStateService)
    open3d_refresh_service = inspect.getsource(Open3DTraceRefreshService)
    physics_requested_source = inspect.getsource(Open3DTraceRefreshService.inspector_physics_requested)
    step_normal_axis_apply = inspect.getsource(Kraken3DInspector._apply_step_normal_axis_pick)
    step_surface_center_axis_apply = inspect.getsource(Kraken3DInspector._apply_step_surface_center_axis_pick)
    step_promotion_service = inspect.getsource(StepOverlayPromotionService)
    checks = [
        Open3DLiveTransientStepCheck(
            "Live refresh requests transient STEP overlays",
            "def build_live_preview" in open3d_refresh_service
            and "include_live_step_overlays=True" in open3d_refresh_service
            and "update_state=False" in open3d_refresh_service,
            "Live Mode builds a render-only trace bundle without overwriting the persistent 2D preview state.",
        ),
        Open3DLiveTransientStepCheck(
            "Open 3D traces transient optical STEP overlays only after explicit physics intent",
            "def has_traceable_step_overlays" in open3d_refresh_service
            and "def inspector_should_trace_step_overlays" in open3d_refresh_service
            and "def step_overlay_physics_preview_labels" in open3d_refresh_service
            and "def mark_step_overlay_physics_preview_ready" in open3d_refresh_service
            and "def clear_step_overlay_physics_preview" in open3d_refresh_service
            and "def inspector_step_overlay_preview_requested" in open3d_refresh_service
            and "show_rays_var" not in physics_requested_source
            and "live_mode_var" in physics_requested_source
            and "_step_normal_axis_pick_mode" in open3d_refresh_service
            and "_step_surface_center_axis_pick_mode" in open3d_refresh_service
            and "force_retrace" in open3d_refresh_service
            and "if bool(force_retrace):" not in open3d_refresh_service
            and "include_live_step_overlays = self.inspector_should_trace_step_overlays(" in open3d_refresh_service
            and "requires_open3d_retrace = include_live_step_overlays or self.has_promoted_step_optical_solid_rows()"
            in open3d_refresh_service
            and "if not requires_open3d_retrace and not force_retrace" in open3d_refresh_service
            and "include_live_step_overlays=include_live_step_overlays" in open3d_refresh_service,
            "Imported STEP carry/drop remains a CAD display workflow; Live Mode, Trace Now, or a placed optical-axis STEP preview opt into transient physics.",
        ),
        Open3DLiveTransientStepCheck(
            "Axis snap restores visible placed STEP physics preview",
            "_show_rays_before_axis_pick" in inspector_source
            and "def _restore_rays_after_step_axis_pick" in inspector_source
            and "mark_step_overlay_physics_preview_ready(label)" in inspector_source
            and "self.show_rays_var.set(True)" in inspector_source
            and "self.refresh_from_editor(force_retrace=restore_rays)" in inspector_source,
            "Center-to-axis placement hides rays only during picking, then restores Show Rays and retraces the intentionally placed optical STEP.",
        ),
        Open3DLiveTransientStepCheck(
            "Axis snap exits carry mode after the STEP is placed",
            "_step_carry_active_label = None" in step_normal_axis_apply
            and "_step_carry_active_label = None" in step_surface_center_axis_apply
            and "_restore_rays_after_step_axis_pick(label)" in step_normal_axis_apply
            and "_restore_rays_after_step_axis_pick(label)" in step_surface_center_axis_apply,
            "A completed surface/axis snap leaves the STEP selected for rotation rather than still carrying it under the mouse.",
        ),
        Open3DLiveTransientStepCheck(
            "Trace Now makes hidden-ray results visible",
            "def _refresh_trace_now_scene" in inspector_source
            and "self.show_rays_var.set(True)" in inspector_source
            and "mark_step_overlay_physics_preview_ready(\"optical\")" in inspector_source
            and "build_trace_now_preview(self)" in inspector_source,
            "Trace Now no longer computes a transient STEP trace while leaving the Open 3D ray layer hidden.",
        ),
        Open3DLiveTransientStepCheck(
            "Transient optical STEP rows use the promoted-solid contract",
            "def _step_overlay_optical_solid_row_plan" in step_promotion_service
            and "self._optical_stl_solid_row(" in step_promotion_service
            and 'source_format="STEP"' in step_promotion_service
            and '"StepOverlayPromotion"' in step_promotion_service
            and '"LiveStepOverlayTrace"' in step_promotion_service,
            "The imported optical STEP is converted to a file-backed Solid_3d_stl row with face metadata.",
        ),
        Open3DLiveTransientStepCheck(
            "Only the generic optical STEP overlay becomes live-traceable",
            "def _live_step_overlay_trace_rows" in editor_source
            and 'self._step_path_for_label("optical")' in editor_source
            and 'self._step_overlay_optical_solid_row_plan(\n                "optical",' in editor_source,
            "Lens, camera, and LED decorative overlays are not silently promoted into physics.",
        ),
        Open3DLiveTransientStepCheck(
            "The editable table rows are restored after transient tracing",
            "original_rows = self.rows" in editor_source
            and "self.rows = active_rows" in editor_source
            and "self.rows = original_rows" in editor_source,
            "Transient rows exist during system, ray, and SceneBundle construction only.",
        ),
        Open3DLiveTransientStepCheck(
            "Open 3D renders against the same transient row list",
            "def _preview_render_rows" in editor_source
            and "def _preview_render_row_names" in editor_source
            and "_last_live_step_overlay_scene_bundle" in editor_source
            and "self.editor._preview_render_row_names(scene_bundle)" in open3d_refresh_service,
            "Surface mesh accounting uses the transient trace rows for the live bundle.",
        ),
        Open3DLiveTransientStepCheck(
            "Transient file-backed rows keep CAD display styling",
            "def _render_row_file_backed" in inspector_source
            and "self._render_row_file_backed(rows, int(index))" in open3d_scene_refresh_service
            and "solid_mesh = self._stl_mesh_with_world_transform(row, row_transform)" in editor_source
            and "file_backed_optical_solid and row_transform is not None" in editor_source,
            "Live trace rows are classified from the render row list and displayed with the full CAD/STL body.",
        ),
        Open3DLiveTransientStepCheck(
            "CAD body edges are cleaned before display",
            "def _display_feature_edges" in inspector_source
            and ".clean(tolerance=1e-6" in inspector_source
            and "ray_surface_edge_overlays.append((edges, file_backed_silhouette_color" in open3d_scene_refresh_service,
            "Imported solids use strong outline edges without relying on raw triangulation boundaries.",
        ),
        Open3DLiveTransientStepCheck(
            "Transient STEP overlays are not drawn twice during live tracing",
            "def _live_trace_step_overlay_labels" in inspector_source
            and "current_live_trace_step_overlay_labels = {" in open3d_scene_refresh_service
            and "label_is_live_trace_row = label in current_live_trace_step_overlay_labels" in open3d_scene_refresh_service
            and "if label_is_live_trace_row:" in open3d_scene_refresh_service
            and "continue" in open3d_scene_refresh_service,
            "When Live Mode turns an imported optical STEP into a transient row, the display-only overlay is suppressed for the current trace row even if the row body mesh is not the first mesh item.",
        ),
        Open3DLiveTransientStepCheck(
            "Show Rays toggles reuse the current Open 3D scene bundle",
            "def can_reuse_current_scene_for_show_rays" in open3d_refresh_service
            and "def current_scene_has_live_step_trace" in open3d_refresh_service
            and "show_rays_fast_toggle_refresh" in inspector_source
            and "self._current_rays = rays" in open3d_scene_refresh_service
            and "self._current_row_names = list(row_names or [])" in open3d_scene_refresh_service,
            "Expensive transient STEP tracing is paid once; subsequent ray visibility changes are display-only refreshes.",
        ),
        Open3DLiveTransientStepCheck(
            "Transient STEP previews display the full traced launch family",
            "def _iter_3d_scene_ray_records" in editor_source
            and "_last_live_step_overlay_scene_bundle" in editor_source
            and "_last_live_step_overlay_trace_records" in editor_source
            and "transient_live_trace" in editor_source
            and "and not live_step_preview" in editor_source
            and "ray_path_reaches_image_from_events(path)" in editor_source,
            "Defocused rays from a placed transient STEP are not filtered down to only detector-hit paths, so grid bundles do not collapse into a single cone.",
        ),
        Open3DLiveTransientStepCheck(
            "Live STEP row plans are cached across source-only refreshes",
            "_live_step_overlay_trace_plan_cache" in editor_source
            and "def _live_step_overlay_trace_cache_key" in editor_source
            and "def _cached_live_step_overlay_trace_plan" in editor_source
            and "def _remember_live_step_overlay_trace_plan" in editor_source
            and "cache_hit" in editor_source,
            "Unchanged optical STEP pose and row context can reuse the transient row plan instead of remeshing.",
        ),
        Open3DLiveTransientStepCheck(
            "Transient STEP placement has an explicit persistent-row accept path",
            "def accept_selected_step_placement" in inspector_source
            and "def _promote_step_overlay_to_optical_solid_row" in inspector_source
            and "open_face_editor=False" in inspector_source
            and "promote_imported_overlay_to_row" in open3d_step_state_service
            and "clear_overlay=True" in open3d_step_state_service
            and "_live_step_overlay_trace_plan_cache = {}" in open3d_step_state_service,
            "Accepting placement promotes the overlay into a row-backed optical solid and clears transient state.",
        ),
    ]
    return checks


def main() -> int:
    checks = validate_open3d_live_transient_step()
    failed = [check for check in checks if not check.ok]
    for check in checks:
        status = "PASS" if check.ok else "FAIL"
        print(f"{status}: {check.check} - {check.detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
