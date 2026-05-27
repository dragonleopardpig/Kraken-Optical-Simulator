"""Validate Open 3D action timing instrumentation contracts."""

from __future__ import annotations

import inspect

from KrakenOS.UI import diagnose_open3d_action_timing
from KrakenOS import MeshRayTrace
from KrakenOS import TraceLoopTool
import KrakenOS as Kos
from KrakenOS.UI.open3d_inspector import Kraken3DInspector
from KrakenOS.UI.services import layout_polyline_display, layout_table_workbench, open3d_interaction, open3d_scene_refresh
from KrakenOS.UI.services import open3d_step_overlay_refresh
from KrakenOS.UI.services import open3d_step_rotation_handles
from KrakenOS.UI.services import open3d_timing, open3d_trace_refresh
from KrakenOS.UI.services import three_d_scene_tools, trace_preview, trace_preview_sampling


def main() -> int:
    timing_source = inspect.getsource(open3d_timing)
    inspector_source = inspect.getsource(Kraken3DInspector)
    interaction_source = inspect.getsource(open3d_interaction.Open3DInteractionService)
    interaction_module_source = inspect.getsource(open3d_interaction)
    refresh_source = inspect.getsource(open3d_scene_refresh.Open3DSceneRefreshService.refresh_scene)
    step_overlay_refresh_source = inspect.getsource(open3d_step_overlay_refresh.Open3DStepOverlayRefreshService)
    step_rotation_source = inspect.getsource(open3d_step_rotation_handles.Open3DStepRotationHandleService)
    trace_refresh_source = inspect.getsource(open3d_trace_refresh.Open3DTraceRefreshService)
    three_d_scene_source = inspect.getsource(three_d_scene_tools.ThreeDSceneToolsMixin._build_preview_system_rays_bundle)
    trace_preview_source = inspect.getsource(trace_preview.TracePreviewService._trace_preview_bundles)
    mesh_ray_trace_source = inspect.getsource(MeshRayTrace)
    system_source = inspect.getsource(Kos.system)
    trace_loop_source = inspect.getsource(TraceLoopTool.NsTraceLoop)
    trace_sampling_source = inspect.getsource(trace_preview_sampling.TracePreviewSamplingMixin._trace_selected_through_envelope)
    polyline_source = inspect.getsource(layout_polyline_display.LayoutPolylineDisplayMixin._load_step_mesh)
    workbench_source = inspect.getsource(layout_table_workbench.LayoutTableWorkbenchMixin)
    diagnostic_source = inspect.getsource(diagnose_open3d_action_timing)
    checks = [
        (
            "timing service writes JSONL to a stable cache path",
            "open3d_timing_latest.jsonl" in timing_source
            and "open3d_timing_event" in timing_source
            and "open3d_timing_span" in timing_source,
        ),
        (
            "Open 3D inspector resets timing log on startup",
            "reset_open3d_timing_log(reason=\"inspector_init\")" in inspector_source,
        ),
        (
            "Open 3D render and refresh are timed",
            "_timing_start(\"render\")" in inspector_source
            and "_timing_start(" in inspect.getsource(Kraken3DInspector.refresh_from_editor)
            and "build_inspector_refresh" in inspect.getsource(Kraken3DInspector.refresh_from_editor),
        ),
        (
            "Open 3D interaction handlers record user-action timing",
            "_timed_open3d_interaction" in interaction_module_source
            and "left_click_vtk_pick" in interaction_source
            and "mouse_move_processed" in interaction_source,
        ),
        (
            "Open 3D scene refresh reports stage durations",
            "mesh_collect_ms" in refresh_source
            and "actor_clear_ms" in refresh_source
            and "surface_actor_ms" in refresh_source
            and "ray_actor_ms" in refresh_source
            and "refresh_scene_timing" in refresh_source,
        ),
        (
            "STEP mesh import records cache/conversion/read timings",
            "load_step_mesh" in polyline_source
            and "convert_step_to_stl" in polyline_source
            and "read_step_stl_mesh" in polyline_source
            and "load_step_mesh_memory_cache_hit" in polyline_source,
        ),
        (
            "Open 3D preview build records system/trace/scene bundle timings",
            "preview_system_rays_bundle_start" in three_d_scene_source
            and "preview_live_step_overlay_rows" in three_d_scene_source
            and "preview_build_system" in three_d_scene_source
            and "preview_trace_rays" in three_d_scene_source
            and "preview_build_scene_bundle" in three_d_scene_source,
        ),
        (
            "ray tracing records backend, bundle, and ray-count timings",
            "trace_preview_bundles_start" in trace_preview_source
            and "trace_preview_bundle_start" in trace_preview_source
            and "trace_preview_bundle_done" in trace_preview_source
            and "trace_preview_bundles_done" in trace_preview_source
            and "trace_preview_parallel_chunk_done" in trace_preview_source,
        ),
        (
            "non-sequential mesh ray intersection timing is summarized per trace bundle",
            "reset_mesh_trace_stats(active=True)" in trace_preview_source
            and "trace_preview_mesh_ray_stats" in trace_preview_source
            and "mesh_trace_stats_snapshot(reset=True)" in trace_preview_source
            and "def mesh_trace_stats_snapshot" in mesh_ray_trace_source
            and "mesh_ray_contexts" in mesh_ray_trace_source,
        ),
        (
            "non-sequential loop timing separates system tracing from raykeeper push",
            "EnableNsTraceTiming(True)" in trace_preview_source
            and "trace_preview_ns_loop_stats" in trace_preview_source
            and "NsTraceTimingSnapshot(reset=True)" in trace_preview_source
            and "def NsTraceTimingRecord" in system_source
            and "system.NsTrace" in trace_loop_source
            and "raykeeper.push" in trace_loop_source,
        ),
        (
            "world envelope keeps the first successful trace instead of retracing it",
            "candidate_rays" not in trace_sampling_source
            and "rays.clean()" in trace_sampling_source
            and "through_total <= 0" in trace_sampling_source
            and "_trace_preview_bundles(system, rays, wavelength, bundles)" in trace_sampling_source,
        ),
        (
            "display-backed timing replay follows the reported user workflow",
            "Machine Vision 150Mm Measured" in diagnostic_source
            and "Aspherized_Achromatic_Lenses" in diagnostic_source
            and "show_rays_var.set(False)" in diagnostic_source
            and "_apply_step_rotation_handle" in diagnostic_source
            and "partial_step_overlay_events" in diagnostic_source
            and "_finish_step_carry_drag(drop_state)" in diagnostic_source
            and "_clear_open3d_selection(render=True)" in diagnostic_source,
        ),
        (
            "display-backed timing replay can profile the first Show Rays refresh",
            "--trace-rays" in diagnostic_source
            and "trace_rays" in diagnostic_source
            and "show_rays_var.set(True)" in diagnostic_source,
        ),
        (
            "Ctrl-Z undo/redo restore path is timed and has a hidden-ray STEP display-only fast path",
            "history_undo" in workbench_source
            and "history_redo" in workbench_source
            and "history_restore" in workbench_source
            and "def _history_restore_is_open3d_step_display_only" in workbench_source
            and "history_restore_skip_plot_refresh" in workbench_source
            and "history_restore_actor_translate" in workbench_source
            and "self._refresh_open_3d_views(force_retrace=False)" in workbench_source
            and "app.undo()" in diagnostic_source,
        ),
        (
            "Ctrl-Z undo/redo clears stale transient STEP runtime state",
            "def _clear_step_runtime_after_history_restore" in workbench_source
            and "clear_step_overlay_physics_preview(label)" in workbench_source
            and "_clear_step_overlay_interaction_state()" in workbench_source
            and "self._clear_step_runtime_after_history_restore(set(changed_settings))" in workbench_source,
        ),
        (
            "imported STEP placement defers transient physics until live or placed-preview intent",
            "def inspector_should_trace_step_overlays" in trace_refresh_source
            and "def inspector_physics_requested" in trace_refresh_source
            and "def inspector_step_overlay_preview_requested" in trace_refresh_source
            and "def mark_step_overlay_physics_preview_ready" in trace_refresh_source
            and "_step_normal_axis_pick_mode" in trace_refresh_source
            and "live_mode_var" in trace_refresh_source
            and "show_rays_var" not in inspect.getsource(open3d_trace_refresh.Open3DTraceRefreshService.inspector_physics_requested)
            and "if bool(force_retrace):" not in trace_refresh_source
            and "include_live_step_overlays = self.inspector_should_trace_step_overlays(" in trace_refresh_source,
        ),
        (
            "Trace Now and axis snap make placed optical STEP previews visible",
            "def _refresh_trace_now_scene" in inspector_source
            and "self.show_rays_var.set(True)" in inspector_source
            and "mark_step_overlay_physics_preview_ready(\"optical\")" in inspector_source
            and "def _restore_rays_after_step_axis_pick" in inspector_source
            and "mark_step_overlay_physics_preview_ready(label)" in inspector_source
            and "self.refresh_from_editor(force_retrace=restore_rays)" in inspector_source,
        ),
        (
            "hidden-ray STEP drop does not force physics retrace",
            "physics_requested = self.editor._open3d_trace_refresh_service().inspector_physics_requested(self)"
            in inspector_source
            and "self.refresh_from_editor(force_retrace=physics_requested)" in inspector_source,
        ),
        (
            "hidden-ray imported STEP rotation refreshes only the selected STEP overlay",
            "def refresh_imported_step_overlay" in inspector_source
            and "Open3DStepOverlayRefreshService" in inspector_source
            and "refresh_imported_step_overlay" in step_rotation_source
            and "rotate_step_world_axis(" in step_rotation_source
            and "refresh=physics_requested" in step_rotation_source
            and "refresh_imported_step_overlay_rebuilt" in step_overlay_refresh_source,
        ),
        (
            "STEP hover selection groups smooth CAD regions instead of raw mesh facets",
            "def _smooth_component_for_cell" in inspector_source
            and "def _coarse_step_face_ray_pick_for_display_xy" in inspector_source
            and "_coarse_step_face_ray_pick_for_display_xy" in interaction_source
            and "feature_edges=False" in inspector_source
            and "_outline_for_cells(data, smooth_component" in inspector_source,
        ),
    ]
    failures = [name for name, ok in checks if not ok]
    if failures:
        print("Open 3D action timing validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Open 3D action timing validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
