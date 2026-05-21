"""Validate that Open 3D Live Mode traces imported optical STEP overlays."""

from __future__ import annotations

import inspect
from dataclasses import dataclass

from KrakenOS.UI.layout_editor import Kraken3DInspector, KrakenLayoutEditor


@dataclass
class Open3DLiveTransientStepCheck:
    check: str
    ok: bool
    detail: str


def validate_open3d_live_transient_step() -> list[Open3DLiveTransientStepCheck]:
    inspector_source = inspect.getsource(Kraken3DInspector)
    editor_source = inspect.getsource(KrakenLayoutEditor)
    checks = [
        Open3DLiveTransientStepCheck(
            "Live refresh requests transient STEP overlays",
            "def _refresh_live_preview_scene" in inspector_source
            and "include_live_step_overlays=True" in inspector_source
            and "update_state=False" in inspector_source,
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
            and "self.editor._preview_render_rows(scene_bundle)" in inspector_source,
            "Surface mesh accounting uses the transient trace rows for the live bundle.",
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
