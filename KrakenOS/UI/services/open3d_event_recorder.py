"""Record raw Open 3D interaction events to JSON for bug reproduction.

The user clicks ``Record`` in the inspector toolbar, performs the buggy
gesture, then clicks ``Stop``. The recorder writes every mouse press /
move / release, every key press, every toolbar button activation, plus
a snapshot of the camera and pick-state at the start of the recording,
into ``attachment/recorded_bug_repros/recording_YYYYmmdd_HHMMSS.json``.

That JSON is then replayable by
``KrakenOS/UI/validate_open3d_interaction_workflows.py --replay <path>``
so a future fix is gated on the exact sequence the user reported.

The recorder is intentionally additive: it does not alter the events
the inspector handles. The Tk bindings and toolbar button commands
keep firing as before; the recorder just appends a row to the
in-memory log when it sees one go past.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


_PROJECT_ROOT = Path(__file__).resolve().parents[3]
RECORDING_DIR = _PROJECT_ROOT / "attachment" / "recorded_bug_repros"


@dataclass
class RecordedEvent:
    """One event captured during a recording."""

    timestamp_ms: float
    kind: str
    x: int | None = None
    y: int | None = None
    button: int | None = None
    key: str | None = None
    modifiers: list[str] = field(default_factory=list)
    label: str = ""
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class RecordingPrelude:
    """Pre-recording state snapshot so a replay can reach the same baseline."""

    captured_at_iso: str
    camera_position: list[float]
    camera_focal: list[float]
    camera_view_up: list[float]
    camera_parallel_scale: float
    camera_parallel_projection: int
    picked_row_index: int | None
    picked_step_label: str | None
    picked_ray_index: int | None
    picked_optical_axis_id: str | None
    selected_step_label: str | None
    interaction_mode: str
    rows: list[str]
    step_paths: dict[str, str]
    notes: str = ""


class Open3DEventRecorder:
    """Capture interaction events between Record / Stop button clicks."""

    def __init__(self, inspector: Any) -> None:
        self._inspector = inspector
        self.recording: bool = False
        self.events: list[RecordedEvent] = []
        self.prelude: RecordingPrelude | None = None
        self._t0: float = 0.0
        self._last_record_path: Path | None = None

    # ------------------------------------------------------------------
    # Public lifecycle

    def is_recording(self) -> bool:
        return self.recording

    def start(self, note: str = "") -> None:
        self.events = []
        self.prelude = self._snapshot_prelude(note)
        self._t0 = time.perf_counter()
        self.recording = True

    def stop(self) -> Path | None:
        if not self.recording:
            return None
        self.recording = False
        try:
            return self._dump()
        except Exception as exc:
            try:
                self._inspector.editor.append_debug(f"Event recorder dump failed: {exc}")
            except Exception:
                pass
            return None

    @property
    def last_path(self) -> Path | None:
        return self._last_record_path

    # ------------------------------------------------------------------
    # Capture API -- called from the bindings / button hooks

    def record_mouse(self, kind: str, *, event: Any, button: int) -> None:
        """``kind`` is mouse_press / mouse_move / mouse_release."""
        if not self.recording:
            return
        try:
            x = int(getattr(event, "x", 0))
            y = int(getattr(event, "y", 0))
            modifiers = self._modifiers_from_state(int(getattr(event, "state", 0) or 0))
        except Exception:
            return
        self._append(
            RecordedEvent(
                timestamp_ms=self._elapsed_ms(),
                kind=kind,
                x=x,
                y=y,
                button=int(button),
                modifiers=modifiers,
            )
        )

    def record_key(self, kind: str, *, keysym: str, state: int = 0) -> None:
        """``kind`` is key_press / key_release."""
        if not self.recording:
            return
        self._append(
            RecordedEvent(
                timestamp_ms=self._elapsed_ms(),
                kind=kind,
                key=str(keysym),
                modifiers=self._modifiers_from_state(int(state or 0)),
            )
        )

    def record_command(self, label: str, payload: dict[str, Any] | None = None) -> None:
        """Toolbar buttons / menu items / programmatic actions."""
        if not self.recording:
            return
        self._append(
            RecordedEvent(
                timestamp_ms=self._elapsed_ms(),
                kind="command",
                label=str(label),
                payload=dict(payload or {}),
            )
        )

    # ------------------------------------------------------------------
    # Internals

    def _append(self, event: RecordedEvent) -> None:
        self.events.append(event)

    def _elapsed_ms(self) -> float:
        return (time.perf_counter() - self._t0) * 1000.0

    @staticmethod
    def _modifiers_from_state(state: int) -> list[str]:
        mods: list[str] = []
        if state & 0x0001:
            mods.append("shift")
        if state & 0x0004:
            mods.append("ctrl")
        if state & 0x0008 or state & 0x20000:
            mods.append("alt")
        if state & 0x0010:
            mods.append("num_lock")
        return mods

    def _snapshot_prelude(self, note: str) -> RecordingPrelude:
        inspector = self._inspector
        camera_position = [0.0, 0.0, 0.0]
        camera_focal = [0.0, 0.0, 0.0]
        camera_view_up = [0.0, 1.0, 0.0]
        camera_parallel_scale = 1.0
        camera_parallel_projection = 0
        try:
            renderer = inspector._renderer
            if renderer is not None:
                cam = renderer.GetActiveCamera()
                if cam is not None:
                    camera_position = [float(v) for v in cam.GetPosition()]
                    camera_focal = [float(v) for v in cam.GetFocalPoint()]
                    camera_view_up = [float(v) for v in cam.GetViewUp()]
                    camera_parallel_scale = float(cam.GetParallelScale())
                    camera_parallel_projection = int(cam.GetParallelProjection())
        except Exception:
            pass

        try:
            interaction_mode = str(inspector.current_interaction_mode().value)
        except Exception:
            interaction_mode = "idle"
        try:
            rows = [
                f"S{i}:{getattr(row, 'surface', '')}:{getattr(row, 'name', '')}"
                for i, row in enumerate(inspector.editor.rows)
            ]
        except Exception:
            rows = []
        try:
            step_paths = {
                str(label): str(inspector.editor._step_path_for_label(str(label)) or "")
                for label in ("optical", "lens", "camera", "led")
                if inspector.editor._step_path_for_label(str(label)) is not None
            }
        except Exception:
            step_paths = {}

        return RecordingPrelude(
            captured_at_iso=time.strftime("%Y-%m-%dT%H:%M:%S"),
            camera_position=camera_position,
            camera_focal=camera_focal,
            camera_view_up=camera_view_up,
            camera_parallel_scale=camera_parallel_scale,
            camera_parallel_projection=camera_parallel_projection,
            picked_row_index=getattr(inspector, "_picked_row_index", None),
            picked_step_label=getattr(inspector, "_picked_step_label", None),
            picked_ray_index=getattr(inspector, "_picked_ray_index", None),
            picked_optical_axis_id=getattr(inspector, "_picked_optical_axis_id", None),
            selected_step_label=getattr(inspector.editor, "_selected_step_label", None),
            interaction_mode=interaction_mode,
            rows=rows,
            step_paths=step_paths,
            notes=str(note or ""),
        )

    def _dump(self) -> Path:
        RECORDING_DIR.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        path = RECORDING_DIR / f"recording_{stamp}.json"
        payload: dict[str, Any] = {
            "version": 1,
            "prelude": asdict(self.prelude) if self.prelude is not None else {},
            "events": [asdict(event) for event in self.events],
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        self._last_record_path = path
        return path
