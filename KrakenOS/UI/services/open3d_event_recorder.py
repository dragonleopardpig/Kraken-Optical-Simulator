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
class SceneSnapshot:
    """Scene state captured alongside an event.

    Each field is something a visual bug ("the axis suddenly shortened",
    "edge highlight is offset from the body", "rotation handles popped
    up after a snap") manifests in numerically. A diff between two
    consecutive snapshots tells me what changed without needing a video.
    """

    interaction_mode: str = "idle"
    picked_row_index: int | None = None
    picked_row_indices: list[int] = field(default_factory=list)
    picked_step_label: str | None = None
    picked_ray_index: int | None = None
    picked_optical_axis_id: str | None = None
    selected_step_label: str | None = None
    selected_step_rotation_active_label: str | None = None
    optical_axis_records: list[dict[str, Any]] = field(default_factory=list)
    row_actor_bounds: dict[int, list[float]] = field(default_factory=dict)
    step_actor_counts: dict[str, int] = field(default_factory=dict)
    step_actor_bounds: dict[str, list[float]] = field(default_factory=dict)
    scene_visible_bounds: list[float] = field(default_factory=list)
    rotation_handle_count: int = 0
    placement_translate_handle_count: int = 0
    placement_rotate_handle_count: int = 0
    thickness_dimension_count: int = 0
    ray_actor_count: int = 0
    optical_axis_actor_count: int = 0
    optical_axis_highlight_present: bool = False
    # bugs/0010: capture the STEP face-hover edge highlight so a "ghost edges"
    # flag pins what/where the stray highlight is. ``hover_outline_bounds`` is the
    # gold hover-outline actor's world bounds (empty if none); ``hover_step_cell_key``
    # is its cache key; ``stray_props_above_body`` lists any visible prop whose
    # y-extent sits clearly above the optical body (the stranded "ghost").
    hover_outline_bounds: list[float] = field(default_factory=list)
    hover_step_cell_key: str | None = None
    stray_props_above_body: list[dict[str, Any]] = field(default_factory=list)
    show_rays: bool = False
    camera_position: list[float] = field(default_factory=list)
    camera_focal: list[float] = field(default_factory=list)
    camera_view_up: list[float] = field(default_factory=list)
    camera_parallel_scale: float = 0.0


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
    scene_state: SceneSnapshot | None = None


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

    def discard(self) -> int:
        """Throw away the in-progress recording without saving to disk.

        Returns the number of events that were dropped so the caller can
        report it. Leaves the prelude / events in a clean state ready
        for the next ``start()`` call.
        """
        events_dropped = len(self.events)
        self.recording = False
        self.events = []
        self.prelude = None
        return events_dropped

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
                scene_state=self._snapshot_scene(),
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
                scene_state=self._snapshot_scene(),
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
                scene_state=self._snapshot_scene(),
            )
        )

    def record_flag(self, description: str, screenshot_path: str, payload: dict[str, Any] | None = None) -> None:
        """User clicked Flag bug: insert a flagged event into the timeline.

        Use ``capture_scene_snapshot()`` from the inspector before this
        if you need the snapshot to predate any dialog redraw; here we
        just take the current state. ``screenshot_path`` and
        ``description`` are stamped into the payload so the post-mortem
        knows what the user was looking at and what they typed.
        """
        if not self.recording:
            return
        merged = dict(payload or {})
        merged.setdefault("description", str(description or ""))
        merged.setdefault("screenshot_path", str(screenshot_path or ""))
        self._append(
            RecordedEvent(
                timestamp_ms=self._elapsed_ms(),
                kind="flag",
                label="flag_bug",
                payload=merged,
                scene_state=self._snapshot_scene(),
            )
        )

    def capture_scene_snapshot(self) -> SceneSnapshot | None:
        """Public hook so the inspector can sample state outside an event."""
        return self._snapshot_scene()

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

    def _snapshot_scene(self) -> SceneSnapshot | None:
        """Capture renderer state at the moment of an event.

        Designed to be cheap: reads existing inspector dicts, the
        active camera, and currently-loaded optical-axis pick records.
        Doesn't touch the picker, doesn't refresh the scene, doesn't
        allocate VTK objects.
        """
        inspector = self._inspector
        try:
            snapshot = SceneSnapshot()
        except Exception:
            return None
        try:
            snapshot.interaction_mode = str(inspector.current_interaction_mode().value)
        except Exception:
            snapshot.interaction_mode = "idle"
        try:
            snapshot.picked_row_index = inspector._picked_row_index
            snapshot.picked_row_indices = sorted(
                int(value) for value in (inspector._picked_row_indices or set())
            )
            snapshot.picked_step_label = inspector._picked_step_label
            snapshot.picked_ray_index = inspector._picked_ray_index
            snapshot.picked_optical_axis_id = inspector._picked_optical_axis_id
            snapshot.selected_step_label = getattr(inspector.editor, "_selected_step_label", None)
            snapshot.selected_step_rotation_active_label = inspector._step_rotation_active_label
        except Exception:
            pass

        # Optical-axis world points: tells us when "the axis suddenly
        # shortened" by comparing two consecutive snapshots.
        try:
            for record in list(inspector._optical_axis_pick_records or []):
                points = record.get("points")
                point_list: list[list[float]] = []
                try:
                    import numpy as _np

                    arr = _np.asarray(points, dtype=float)
                    if arr.ndim == 2 and arr.shape[1] >= 3:
                        point_list = [
                            [float(v) for v in arr[i, :3]] for i in range(arr.shape[0])
                        ]
                except Exception:
                    pass
                snapshot.optical_axis_records.append(
                    {
                        "axis_id": str(record.get("axis_id", "") or ""),
                        "axis_kind": str(record.get("axis_kind", "") or ""),
                        "axis_label": str(record.get("axis_label", "") or ""),
                        "points": point_list,
                    }
                )
        except Exception:
            pass

        # Each row's actor bounding box: detects body movement /
        # disappearance / edge-highlight offsets row-by-row.
        try:
            actor_by_key = inspector._actor_by_key or {}
            for row_index, actor_keys in (inspector._row_actor_map or {}).items():
                try:
                    rk = int(row_index)
                except Exception:
                    continue
                if not actor_keys:
                    continue
                bounds_min = [float("inf")] * 3
                bounds_max = [float("-inf")] * 3
                found = False
                for actor_key in actor_keys:
                    actor = actor_by_key.get(actor_key)
                    if actor is None:
                        continue
                    try:
                        bounds = actor.GetBounds()
                    except Exception:
                        continue
                    if bounds is None or len(bounds) < 6:
                        continue
                    try:
                        b = [float(v) for v in bounds]
                    except Exception:
                        continue
                    if any(b[i] > b[i + 1] for i in (0, 2, 4)):
                        continue
                    bounds_min[0] = min(bounds_min[0], b[0])
                    bounds_max[0] = max(bounds_max[0], b[1])
                    bounds_min[1] = min(bounds_min[1], b[2])
                    bounds_max[1] = max(bounds_max[1], b[3])
                    bounds_min[2] = min(bounds_min[2], b[4])
                    bounds_max[2] = max(bounds_max[2], b[5])
                    found = True
                if found:
                    snapshot.row_actor_bounds[rk] = [
                        bounds_min[0],
                        bounds_max[0],
                        bounds_min[1],
                        bounds_max[1],
                        bounds_min[2],
                        bounds_max[2],
                    ]
        except Exception:
            pass

        # Per-STEP-overlay actor counts: a disappearing overlay shows
        # up as 0 here.
        try:
            for label, keys in (inspector._step_actor_map or {}).items():
                snapshot.step_actor_counts[str(label)] = len(list(keys or []))
        except Exception:
            pass

        # Per-STEP-overlay actor bounds: lets the analyzer compare the
        # optical-axis Z span against the union of every body in the
        # scene, catching "axis suddenly shortened" the moment a STEP
        # body sits outside the axis envelope.
        try:
            actor_by_key = inspector._actor_by_key or {}
            for label, actor_keys in (inspector._step_actor_map or {}).items():
                if not actor_keys:
                    continue
                bmin = [float("inf")] * 3
                bmax = [float("-inf")] * 3
                found = False
                for actor_key in actor_keys:
                    actor = actor_by_key.get(actor_key)
                    if actor is None:
                        continue
                    try:
                        ab = actor.GetBounds()
                    except Exception:
                        continue
                    if ab is None or len(ab) < 6:
                        continue
                    try:
                        ab = [float(v) for v in ab]
                    except Exception:
                        continue
                    if any(ab[i] > ab[i + 1] for i in (0, 2, 4)):
                        continue
                    bmin[0] = min(bmin[0], ab[0])
                    bmax[0] = max(bmax[0], ab[1])
                    bmin[1] = min(bmin[1], ab[2])
                    bmax[1] = max(bmax[1], ab[3])
                    bmin[2] = min(bmin[2], ab[4])
                    bmax[2] = max(bmax[2], ab[5])
                    found = True
                if found:
                    snapshot.step_actor_bounds[str(label)] = [
                        bmin[0],
                        bmax[0],
                        bmin[1],
                        bmax[1],
                        bmin[2],
                        bmax[2],
                    ]
        except Exception:
            pass

        # The renderer's ComputeVisiblePropBounds is the ground truth for
        # what the optical-axis builder was looking at; capture it so the
        # analyzer can detect order-of-operations bugs (e.g. the axis was
        # built before STEP overlays were appended).
        try:
            renderer = inspector._renderer
            if renderer is not None:
                bounds = renderer.ComputeVisiblePropBounds()
                if bounds is not None and len(bounds) >= 6:
                    snapshot.scene_visible_bounds = [float(v) for v in bounds[:6]]
        except Exception:
            pass

        # Handle counts: tells us when handles popped up unexpectedly.
        try:
            snapshot.rotation_handle_count = len(inspector._actor_step_rotate_map or {})
            snapshot.placement_translate_handle_count = len(inspector._actor_placement_move_map or {})
            snapshot.placement_rotate_handle_count = len(inspector._actor_placement_rotate_map or {})
            snapshot.thickness_dimension_count = len(inspector._actor_thickness_dimension_map or {})
            snapshot.ray_actor_count = len(inspector._actor_ray_map or {})
            snapshot.optical_axis_actor_count = len(inspector._actor_optical_axis_map or {})
            snapshot.optical_axis_highlight_present = inspector._optical_axis_highlight_actor is not None
        except Exception:
            pass

        # bugs/0010: pin the "ghost edges" -- the STEP face hover outline and any
        # stray prop stranded above the optical body after a Center-Row snap.
        try:
            outline_actor = getattr(inspector, "_hover_step_outline_actor", None)
            if outline_actor is not None:
                b = outline_actor.GetBounds()
                if b is not None and len(b) >= 6:
                    snapshot.hover_outline_bounds = [float(v) for v in b[:6]]
            key = getattr(inspector, "_hover_step_cell_key", None)
            snapshot.hover_step_cell_key = None if key is None else str(key)
        except Exception:
            pass
        try:
            body_top = None
            for span in (snapshot.step_actor_bounds or {}).values():
                if len(span) >= 4:
                    body_top = float(span[3]) if body_top is None else max(body_top, float(span[3]))
            for span in (snapshot.row_actor_bounds or {}).values():
                if len(span) >= 4:
                    body_top = float(span[3]) if body_top is None else max(body_top, float(span[3]))
            if body_top is not None:
                actor_by_key = getattr(inspector, "_actor_by_key", {}) or {}
                for actor_key, actor in list(actor_by_key.items()):
                    try:
                        b = actor.GetBounds()
                    except Exception:
                        continue
                    if b is None or len(b) < 6:
                        continue
                    ymin, ymax = float(b[2]), float(b[3])
                    # ymin <= ymax skips degenerate/NaN bounds (NaN compares False).
                    if ymin <= ymax and ymin > body_top + 2.0:
                        snapshot.stray_props_above_body.append(
                            {"key": str(actor_key), "bounds": [round(float(v), 3) for v in b[:6]]}
                        )
        except Exception:
            pass

        try:
            snapshot.show_rays = bool(inspector.show_rays_var.get())
        except Exception:
            pass

        # Camera: detects orbit / view changes between events.
        try:
            renderer = inspector._renderer
            if renderer is not None:
                cam = renderer.GetActiveCamera()
                if cam is not None:
                    snapshot.camera_position = [float(v) for v in cam.GetPosition()]
                    snapshot.camera_focal = [float(v) for v in cam.GetFocalPoint()]
                    snapshot.camera_view_up = [float(v) for v in cam.GetViewUp()]
                    snapshot.camera_parallel_scale = float(cam.GetParallelScale())
        except Exception:
            pass

        return snapshot

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
