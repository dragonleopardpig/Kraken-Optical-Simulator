"""Validate that Open 3D Live Mode traces imported optical STEP overlays."""

from __future__ import annotations

import inspect
from dataclasses import dataclass

from KrakenOS.UI.layout_editor import Kraken3DInspector, KrakenLayoutEditor
from KrakenOS.UI.services.open3d_trace_refresh import Open3DTraceRefreshService


@dataclass
class Open3DLiveTransientStepCheck:
    check: str
    ok: bool
    detail: str


def validate_open3d_live_transient_step() -> list[Open3DLiveTransientStepCheck]:
    inspector_source = inspect.getsource(Kraken3DInspector)
    editor_source = inspect.getsource(KrakenLayoutEditor)
    open3d_refresh_service = inspect.getsource(Open3DTraceRefreshService)
    checks = [
        Open3DLiveTransientStepCheck(
            "Live refresh requests transient STEP overlays",
            "def build_live_preview" in open3d_refresh_service
            and "include_live_step_overlays=True" in open3d_refresh_service
            and "update_state=False" in open3d_refresh_service,
            "Live Mode builds a render-only trace bundle without overwriting the persistent 2D preview state.",
        ),
        Open3DLiveTransientStepCheck(
            "Transient optical STEP rows use the promoted-solid contract",
            "def _step_overlay_optical_solid_row_plan" in editor_source
            and "self._optical_stl_solid_row(" in editor_source
            and '"Solid_3d_stl"' in editor_source
            and '"LiveStepOverlayTrace"' in editor_source,
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
            and "self._render_row_file_backed(rows, int(index))" in inspector_source
            and "solid_mesh = self._stl_mesh_with_world_transform(row, row_transform)" in editor_source
            and "file_backed_optical_solid and row_transform is not None" in editor_source,
            "Live trace rows are classified from the render row list and displayed with the full CAD/STL body.",
        ),
        Open3DLiveTransientStepCheck(
            "CAD body edges are cleaned before display",
            "def _display_feature_edges" in inspector_source
            and ".clean(tolerance=1e-6" in inspector_source
            and "ray_surface_edge_overlays.append((edges, file_backed_silhouette_color" in inspector_source,
            "Imported solids use strong outline edges without relying on raw triangulation boundaries.",
        ),
        Open3DLiveTransientStepCheck(
            "Transient STEP overlays are not drawn twice during live tracing",
            "def _live_trace_step_overlay_labels" in inspector_source
            and "live_trace_step_overlay_labels = self._live_trace_step_overlay_labels()" in inspector_source
            and "if label in live_trace_step_overlay_labels:" in inspector_source
            and "continue" in inspector_source,
            "When Live Mode turns an imported optical STEP into a transient row, the display-only overlay is suppressed.",
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
            and "clear_overlay=True" in inspector_source
            and "_live_step_overlay_trace_plan_cache = {}" in inspector_source,
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
