"""Validate the Open 3D Live Mode integration contract."""

from __future__ import annotations

import inspect
from dataclasses import dataclass

from KrakenOS.UI.layout_editor import Kraken3DInspector, KrakenLayoutEditor
from KrakenOS.UI.panels.open3d_live_controls import Open3DLiveControlsPanel
from KrakenOS.UI.services.open3d_live_refresh import Open3DLiveRefreshService
from KrakenOS.UI.services.open3d_trace_refresh import Open3DTraceRefreshService


@dataclass
class Open3DLiveModeCheck:
    check: str
    ok: bool
    detail: str


def _editor_contract_source() -> str:
    return "\n".join(
        inspect.getsource(cls)
        for cls in KrakenLayoutEditor.__mro__
        if getattr(cls, "__module__", "").startswith("KrakenOS.UI")
    )


def validate_open3d_live_mode() -> list[Open3DLiveModeCheck]:
    inspector_source = inspect.getsource(Kraken3DInspector)
    editor_source = _editor_contract_source()
    open3d_live_controls_panel_source = inspect.getsource(Open3DLiveControlsPanel)
    open3d_live_refresh_service = inspect.getsource(Open3DLiveRefreshService)
    open3d_refresh_service = inspect.getsource(Open3DTraceRefreshService)
    checks = [
        Open3DLiveModeCheck(
            "Open 3D exposes a docked Live Controls panel",
            "Live Controls" in inspector_source
            and "def _build_live_left_panel" in inspector_source
            and "def build_source_controls" in open3d_live_controls_panel_source
            and "def build_field_controls" in open3d_live_controls_panel_source
            and "def build_trace_controls" in open3d_live_controls_panel_source,
            "Live Controls panel mirrors Source, Field, and Trace / Display controls.",
        ),
        Open3DLiveModeCheck(
            "Live Controls expose explicit STEP placement acceptance",
            "def _build_live_step_controls" in inspector_source
            and "Accept STEP Placement" in open3d_live_controls_panel_source
            and "accept_selected_step_placement" in open3d_live_controls_panel_source,
            "Transient STEP placement can be committed from the left Live Controls panel.",
        ),
        Open3DLiveModeCheck(
            "Live Controls are docked left of the 3D viewport",
            "self.columnconfigure(0, weight=0)" in inspector_source
            and "self.columnconfigure(1, weight=1)" in inspector_source
            and 'host.grid(row=1, column=1, sticky="nsew")' in inspector_source
            and 'live_panel.grid(row=1, column=0, sticky="nsew"' in inspector_source,
            "The control panel owns the left column while the VTK viewport remains the expanding right column.",
        ),
        Open3DLiveModeCheck(
            "Live controls are bound to the main editor state",
            "textvariable=self.editor_var(" in open3d_live_controls_panel_source
            and "self.editor._on_source_model_changed" in open3d_live_controls_panel_source
            and "self.editor._on_field_type_changed" in open3d_live_controls_panel_source
            and "self.editor._on_trace_mode_changed" in open3d_live_controls_panel_source,
            "Open 3D widgets reuse editor Tk variables and existing commit handlers.",
        ),
        Open3DLiveModeCheck(
            "Live Mode uses a debounced 3D retrace scheduler",
            "def schedule_live_refresh" in inspector_source
            and "def _run_live_refresh" in inspector_source
            and "Open3DLiveRefreshService(self)" in inspector_source
            and "def schedule" in open3d_live_refresh_service
            and "def run" in open3d_live_refresh_service
            and "self.after_id = inspector.after(delay, self.run)" in open3d_live_refresh_service
            and "normalized_live_refresh_delay(delay_ms)" in open3d_live_refresh_service
            and "self.pending = True" in open3d_live_refresh_service
            and 'self.schedule("pending scene change", delay_ms=PENDING_LIVE_REFRESH_RETRY_MS)' in open3d_live_refresh_service
            and "def build_live_preview" in open3d_refresh_service
            and "self.editor._preview_3d_sampling_mode()" in open3d_refresh_service
            and "self._open3d_live_refresh_service().schedule(reason, delay_ms=delay_ms)" in inspector_source,
            "Live refresh builds the same 3D preview scene through a service-owned debounce/cancellation contract.",
        ),
        Open3DLiveModeCheck(
            "Main left-panel edits can drive Open 3D Live Mode",
            "def _schedule_open3d_live_refresh" in editor_source
            and 'self._schedule_open3d_live_refresh("left panel edit")' in editor_source,
            "The existing main UI controls schedule Open 3D live refreshes when Live Mode is active.",
        ),
        Open3DLiveModeCheck(
            "3D STEP carry and manual refresh route through the live scheduler",
            "live_refresh_message" in inspector_source
            and "self.schedule_live_refresh(live_message)" in inspector_source
            and "self.schedule_live_refresh(transition.live_refresh_message, delay_ms=0)" in inspector_source
            and "def _trace_live_now" in inspector_source,
            "STEP movement has a live-refresh hook; trace-now can refresh the 3D sampling path even with Live Mode off.",
        ),
        Open3DLiveModeCheck(
            "Trace Now preserves the displayed Open 3D sampling mode",
            "def build_trace_now_preview" in open3d_refresh_service
            and "self.inspector_active_sampling_mode(inspector)" in open3d_refresh_service
            and "include_live_step_overlays=True" in open3d_refresh_service
            and "def _refresh_trace_now_scene" in inspector_source,
            "Manual Trace Now retraces the current Open 3D ray family instead of silently switching samplers.",
        ),
    ]
    return checks


def main() -> int:
    checks = validate_open3d_live_mode()
    failed = [check for check in checks if not check.ok]
    for check in checks:
        status = "PASS" if check.ok else "FAIL"
        print(f"{status}: {check.check} - {check.detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
