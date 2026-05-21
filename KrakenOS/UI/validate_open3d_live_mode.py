"""Validate the Open 3D Live Mode integration contract."""

from __future__ import annotations

import inspect
from dataclasses import dataclass

from KrakenOS.UI.layout_editor import Kraken3DInspector, KrakenLayoutEditor


@dataclass
class Open3DLiveModeCheck:
    check: str
    ok: bool
    detail: str


def validate_open3d_live_mode() -> list[Open3DLiveModeCheck]:
    inspector_source = inspect.getsource(Kraken3DInspector)
    editor_source = inspect.getsource(KrakenLayoutEditor)
    checks = [
        Open3DLiveModeCheck(
            "Open 3D exposes a docked Live Controls panel",
            "Live Controls" in inspector_source
            and "def _build_live_left_panel" in inspector_source
            and "def _build_live_source_controls" in inspector_source
            and "def _build_live_field_controls" in inspector_source
            and "def _build_live_trace_controls" in inspector_source,
            "Live Controls panel mirrors Source, Field, and Trace / Display controls.",
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
            "textvariable=self._editor_var(" in inspector_source
            and "self.editor._on_source_model_changed" in inspector_source
            and "self.editor._on_field_type_changed" in inspector_source
            and "self.editor._on_trace_mode_changed" in inspector_source,
            "Open 3D widgets reuse editor Tk variables and existing commit handlers.",
        ),
        Open3DLiveModeCheck(
            "Live Mode uses a debounced 3D retrace scheduler",
            "def schedule_live_refresh" in inspector_source
            and "def _run_live_refresh" in inspector_source
            and "self.editor._preview_3d_sampling_mode()" in inspector_source
            and "self.after(delay, self._run_live_refresh)" in inspector_source,
            "Live refresh builds the same 3D preview scene instead of a display-only branch.",
        ),
        Open3DLiveModeCheck(
            "Main left-panel edits can drive Open 3D Live Mode",
            "def _schedule_open3d_live_refresh" in editor_source
            and 'self._schedule_open3d_live_refresh("left panel edit")' in editor_source,
            "The existing main UI controls schedule Open 3D live refreshes when Live Mode is active.",
        ),
        Open3DLiveModeCheck(
            "3D STEP carry and manual refresh route through the live scheduler",
            'self.schedule_live_refresh(f"{label} STEP carry moved")' in inspector_source
            and 'self.schedule_live_refresh(f"{label} STEP carry dropped", delay_ms=0)' in inspector_source
            and "def _trace_live_now" in inspector_source,
            "STEP movement has a live-refresh hook; trace-now can refresh the 3D sampling path even with Live Mode off.",
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
