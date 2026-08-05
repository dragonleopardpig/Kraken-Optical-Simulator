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
    # bugs/0459: the COUNT alone cannot say whether the drawn beam reaches the sensor. On
    # 2026-07-29 the user's live view truncated the beam at the lens while every headless
    # measurement of the same file drew it to x=264.9, and the flag could not distinguish the
    # two. These bounds make a flag decide it: the union extent of the visible ray actors, plus
    # how many reach past the scene's far half.
    ray_actor_bounds: list[float] = field(default_factory=list)
    ray_actor_extents: list[list[float]] = field(default_factory=list)
    # bugs/0459: the TRACED side, to sit beside the drawn side above.
    traced_ray_path_count: int = 0
    traced_ray_max_x: float = 0.0
    traced_ray_terminations: dict[str, int] = field(default_factory=dict)
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
    # bugs/0074+: a promoted optical solid carries its world placement in the row
    # Desp (the optical chain) AND in StepOverlayPromotion bounds (the 3-D body).
    # Capturing both pins whether an "it snapped to the axis" flag is a DATA bug
    # (Desp went to ~0) or a DISPLAY bug (Desp survives but the body draws on-axis).
    promoted_solid_rows: list[dict[str, Any]] = field(default_factory=list)
    #: bugs/0550: rows whose gap went NEGATIVE, i.e. the station chain runs backwards there
    #: and the trace loses its next surface. Always captured -- the writer does not reproduce
    #: headlessly, so the flag itself has to name the row (set KRAKEN_TRAP_NEGATIVE_GAP=1 to
    #: also capture the stack of whoever wrote it).
    negative_gap_rows: list[dict[str, Any]] = field(default_factory=list)
    # bugs/0086: an imported (un-promoted) STEP overlay can DESYNC -- the body
    # draws on-axis while its stored placement / gizmo / face metadata sit at the
    # dragged-off pose ("snap back when ray off" + floating gizmo). The desync is
    # not reproducible headlessly, so capture the data side here: the live
    # placement/axis offset, whether an axis-snap anchor is still bound, and the
    # live-trace plan's row decenter. Compared with step_actor_bounds (the drawn
    # body) this pins whether the body reverted (offset survives, body on-axis) or
    # the placement was cleared (offset ~0).
    step_overlay_poses: dict[str, Any] = field(default_factory=dict)
    show_rays: bool = False
    #: bugs/0553: the ray-VISIBILITY toggles. Without these a flag saying "rays stop half way"
    #: cannot be told apart from the user having Show Clipped Rays ON -- where drawing a
    #: vignetted stub that ends at the aperture stop is the CORRECT, requested behaviour.
    show_clipped_rays: bool | None = None
    show_terminal_diagnostics: bool | None = None
    # Diagnostics for the "3D shows a fan, not a cone" report (bug 0038/0040):
    # which sampling mode the live 3D actually chose and why (committed tag,
    # transient, cached-bundle mode, the 3D/2D mode the editor wants, and the
    # nonseq/folded/full-pupil flags that gate cone vs envelope).
    sampling_diagnostics: dict[str, Any] = field(default_factory=dict)
    # bugs/0393: what the LAST lens-swap camera-body clearance computed (inputs + the reason
    # any input was empty), so a flag pins why the auto-refocus did/didn't clear the camera.
    swap_clearance_diagnostics: dict[str, Any] = field(default_factory=dict)
    # bugs/0398: per promoted optical-solid row -- is it marked a beam splitter, and is it a
    # fold-override key (i.e. does it re-aim the downstream camera)? Pins why an added BS still
    # re-orients the camera despite the 0397 mark.
    bs_follower_diagnostics: dict[str, Any] = field(default_factory=dict)
    # bugs/0124: what the LAST right-click resolved -- the live hover key, the
    # hovered STEP label, the flaky VTK cell-picker label, and whether the
    # bugs/0121 hovered-face override fired. Pins why a BS-inside-LED right-click
    # still lands on the LED edge despite the gold outline on the BS face.
    right_click_diagnostics: dict[str, Any] = field(default_factory=dict)
    # bugs/0330: the LED clear-aperture square highlights the whole panel (F005)
    # LIVE, yet the square (F053) headless at the SAME camera+render size -- the
    # miss can only be a projection/size/DPI difference at the live pick instant.
    # ``render_window_size`` is the render window's pixel size at flag time;
    # ``opening_hover_debug`` is what the LAST opening-loop hover snap saw (sizes,
    # cursor, each mined opening's projected centroid + px distance, chosen face).
    # Together they say whether the square projected onto or away from the cursor
    # LIVE -- the datum a single before-flag screenshot can never carry.
    render_window_size: list[int] = field(default_factory=list)
    opening_hover_debug: dict[str, Any] = field(default_factory=dict)
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

        # bugs/0074+: promoted optical solids' LIVE row pose + StepOverlayPromotion
        # bounds. The row Desp drives the optical chain (and, off-beam, the 0067
        # body re-decenter); the bounds drive the 3-D body world placement. If a
        # flag reads "snapped to the axis", a Desp ~0 here means the decenter was
        # zeroed (data); a non-zero Desp with an on-axis body means a display bug.
        try:
            for index, row in enumerate(list(getattr(inspector.editor, "rows", []) or [])):
                advanced = getattr(row, "advanced", {}) or {}
                if not isinstance(advanced, dict):
                    continue
                stl = str(advanced.get("Solid_3d_stl", "") or "").strip()
                if stl in {"", "None"}:
                    continue
                promotion = advanced.get("StepOverlayPromotion")
                if not isinstance(promotion, dict):
                    continue

                def _f(value: object) -> float:
                    try:
                        return round(float(value), 4)
                    except Exception:
                        return 0.0

                def _vec(value: object) -> list[float]:
                    try:
                        return [round(float(v), 4) for v in (value or [])][:3]
                    except Exception:
                        return []

                snapshot.promoted_solid_rows.append({
                    "row_index": int(index),
                    "desp": [_f(getattr(row, "desp_x", 0.0)), _f(getattr(row, "desp_y", 0.0)), _f(getattr(row, "desp_z", 0.0))],
                    "tilt": [_f(getattr(row, "tilt_x", 0.0)), _f(getattr(row, "tilt_y", 0.0)), _f(getattr(row, "tilt_z", 0.0))],
                    "thickness": _f(getattr(row, "thickness", 0.0)),
                    "diameter": _f(getattr(row, "diameter", 0.0)),
                    "glass": str(getattr(row, "glass", "") or "").strip(),
                    "promotion_center_world": _vec(promotion.get("center_world")),
                    "promotion_bounds_min_world": _vec(promotion.get("bounds_min_world")),
                    "promotion_bounds_max_world": _vec(promotion.get("bounds_max_world")),
                })
        except Exception:
            pass

        # bugs/0550 (flag_20260805_072959, "Extra rays out of bound"): a gap is a DISTANCE and
        # may never go negative -- a negative thickness makes the station chain run BACKWARDS
        # across that row, and the trace loses its next surface (measured on
        # machine_vision_Apo75: 375 no_next_intersection / 93 reaching, against 279 / 225 once
        # the gap was merely zeroed with every pose held). No writer reproduces this headlessly
        # and every writer found so far already guards, so the FLAG has to name the row itself.
        try:
            rows = list(getattr(getattr(inspector, "editor", None), "rows", None) or [])
            stations, total = [0.0], 0.0
            for row in rows[:-1]:
                total += float(getattr(row, "thickness", 0.0) or 0.0)
                stations.append(total)
            for index, row in enumerate(rows):
                thickness = float(getattr(row, "thickness", 0.0) or 0.0)
                if thickness >= 0.0:
                    continue
                snapshot.negative_gap_rows.append({
                    "row_index": int(index),
                    "name": str(getattr(row, "name", "") or ""),
                    "surface": str(getattr(row, "surface", "") or ""),
                    "thickness": round(thickness, 4),
                    "station": round(float(stations[index]) if index < len(stations) else 0.0, 4),
                    "next_station": round(
                        float(stations[index + 1]) if index + 1 < len(stations) else 0.0, 4
                    ),
                })
        except Exception:
            pass

        # bugs/0086: per imported STEP overlay, capture the DATA-side pose so the
        # "snap back / floating gizmo" desync (not reproducible headlessly) is
        # pinned: the live placement+axis offset, the bound axis-snap anchor (if
        # any) + its target, and the live-trace plan row decenter. The analyzer
        # compares these with step_actor_bounds (the drawn body).
        try:
            editor = getattr(inspector, "editor", None)
            label_set = set()
            try:
                from KrakenOS.UI.layout_editor import STEP_OVERLAY_LABEL_SET as _LBLS
                label_set = set(_LBLS)
            except Exception:
                label_set = {"optical", "lens", "camera", "led"}
            for label in sorted(label_set):
                if editor is None:
                    break
                try:
                    if editor._step_path_for_label(label) is None:
                        continue
                except Exception:
                    continue
                pose: dict[str, Any] = {}
                try:
                    pose["placement_offset_xyz"] = [round(float(v), 4) for v in editor._step_placement_offset_xyz(label)]
                except Exception:
                    pass
                try:
                    pose["axis_offset_xy"] = [round(float(v), 4) for v in editor._step_axis_offset_xy(label)]
                except Exception:
                    pass
                try:
                    anchor = editor._step_overlay_axis_anchor(label)
                    if isinstance(anchor, dict):
                        pose["axis_anchor"] = {
                            "face_id": str(anchor.get("face_id", "") or ""),
                            "target_point": [round(float(v), 4) for v in (anchor.get("target_point") or [])][:3],
                            "source": str(anchor.get("source", "") or ""),
                        }
                    else:
                        pose["axis_anchor"] = None
                except Exception:
                    pass
                if label == "lens":
                    # bugs/0568: how far the lens BODY's optical (CAD barrel) axis sits off the
                    # surrogate's own axis. "The lens STEP is not centered" is otherwise only
                    # visible by eye, and the placement numbers alone cannot show it -- they mean
                    # different things for different bodies.
                    try:
                        import numpy as _np

                        body = editor._lens_step_overlay_axis_world_line()
                        axis = editor._lens_surrogate_optical_axis_line()
                        if body is not None and axis is not None:
                            gap = _np.asarray(axis[0], dtype=float) - _np.asarray(body[0], dtype=float)
                            gap = gap - float(_np.dot(gap, axis[1])) * _np.asarray(axis[1], dtype=float)
                            pose["optical_axis_offset_mm"] = round(float(_np.linalg.norm(gap)), 4)
                            pose["optical_axis_tilt_deg"] = round(
                                float(
                                    _np.degrees(
                                        _np.arccos(
                                            min(1.0, max(-1.0, abs(float(_np.dot(body[1], axis[1])))))
                                        )
                                    )
                                ),
                                4,
                            )
                    except Exception:
                        pass
                if label == "optical":
                    try:
                        _rows, records = editor._live_step_overlay_trace_rows()
                        rec = records[0] if records else {}
                        if isinstance(rec, dict):
                            pose["live_trace_row_decenter_mm"] = [round(float(v), 4) for v in (rec.get("row_decenter_mm") or [])][:3]
                            pose["live_trace_pose_source"] = str(rec.get("pose_source", "") or "")
                    except Exception:
                        pass
                if pose:
                    snapshot.step_overlay_poses[str(label)] = pose
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
            # bugs/0459: read the ray geometry straight off the RENDERER, not off the actor
            # maps -- the merged-ray path (bugs/0223 Fix B) collapses many polylines into a
            # few actors whose keys do not round-trip through _actor_ray_map, so a map-based
            # read reports nothing while the screen is full of rays. Union extent + per-actor
            # extents let a flag say whether the drawn beam reaches the sensor.
            renderer = getattr(inspector, "_renderer", None)
            if renderer is not None:
                props = renderer.GetViewProps()
                props.InitTraversal()
                lo = [float("inf")] * 3
                hi = [float("-inf")] * 3
                extents: list[list[float]] = []
                for _ in range(int(props.GetNumberOfItems())):
                    prop = props.GetNextProp()
                    try:
                        if not bool(prop.GetVisibility()):
                            continue
                        mapper = prop.GetMapper()
                        data = mapper.GetInput() if mapper is not None else None
                        if data is None or int(getattr(data, "GetNumberOfLines", lambda: 0)()) <= 0:
                            continue
                        b = [float(v) for v in prop.GetBounds()]
                        if any(b[i] > b[i + 1] for i in (0, 2, 4)):
                            continue
                        for axis in range(3):
                            lo[axis] = min(lo[axis], b[2 * axis])
                            hi[axis] = max(hi[axis], b[2 * axis + 1])
                        extents.append([round(v, 2) for v in b])
                    except Exception:
                        continue
                if extents:
                    snapshot.ray_actor_bounds = [
                        lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]
                    ]
                    snapshot.ray_actor_extents = extents[:40]
            # bugs/0459: the drawn extent alone cannot say WHERE the beam was lost. Record the
            # TRACED extent beside it, straight off the bundle the inspector is holding, so one
            # flag separates "the live trace produced short rays" from "the trace is fine and
            # the DISPLAY truncated them". Measured 2026-07-29: the user's drawn rays stop at
            # x=85.4 while every headless trace of the same file reaches x=243+.
            try:
                bundle = inspector.__dict__.get("_current_scene_bundle")
                paths = list(getattr(bundle, "ray_paths", None) or [])
                snapshot.traced_ray_path_count = len(paths)
                far = None
                for path in paths:
                    pts = getattr(path, "points_world", None)
                    if pts is None:
                        continue
                    try:
                        xs = [float(p[0]) for p in pts]
                    except Exception:
                        continue
                    if xs:
                        top = max(xs)
                        far = top if far is None else max(far, top)
                if far is not None:
                    snapshot.traced_ray_max_x = round(float(far), 2)
                snapshot.traced_ray_terminations = {}
                for path in paths[:2000]:
                    reason = str(getattr(path, "termination_reason", "") or "")
                    snapshot.traced_ray_terminations[reason] = (
                        snapshot.traced_ray_terminations.get(reason, 0) + 1
                    )
            except Exception:
                pass
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
        # bugs/0330: persist the live render size + the last opening-loop hover
        # snap's projection debug, so a "CA not highlighted" flag reveals whether
        # the square projected onto or away from the cursor at the live pick.
        try:
            widget = getattr(inspector, "_vtk_widget", None)
            rw = widget.GetRenderWindow() if widget is not None else None
            if rw is not None:
                snapshot.render_window_size = [int(v) for v in rw.GetSize()]
        except Exception:
            pass
        try:
            dbg = getattr(inspector, "_last_opening_hover_debug", None)
            snapshot.opening_hover_debug = dict(dbg) if isinstance(dbg, dict) else {}
        except Exception:
            pass
        # bugs/0124: carry the last right-click resolution so a re-recorded
        # BS-inside-LED right-click reveals why the hovered-face override (0121)
        # didn't fire.
        try:
            rc = getattr(inspector, "_last_right_click_debug", None)
            snapshot.right_click_diagnostics = dict(rc) if isinstance(rc, dict) else {}
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
        # bugs/0553: which rays the user asked to SEE. "Rays stop half way before the mirror"
        # is expected when Show Clipped Rays is ON (a vignetted ray legitimately ends at the
        # stop) and a defect when it is OFF, and the flag could not previously tell them apart.
        for attr, field_name in (
            ("show_clipped_rays_var", "show_clipped_rays"),
            ("show_terminal_diagnostics_var", "show_terminal_diagnostics"),
        ):
            for owner in (inspector, getattr(inspector, "editor", None)):
                var = getattr(owner, attr, None) if owner is not None else None
                if var is None:
                    continue
                try:
                    setattr(snapshot, field_name, bool(var.get()))
                    break
                except Exception:
                    continue

        # Sampling-mode diagnostics for the "fan, not cone" report.
        try:
            editor = getattr(inspector, "editor", None)
            diag: dict[str, Any] = {}

            def _safe(label, fn):
                try:
                    diag[label] = fn()
                except Exception as exc:
                    diag[label] = f"<err: {exc!r}>"

            diag["inspector_last_refresh_mode"] = getattr(inspector, "_last_refresh_sampling_mode", None)
            if editor is not None:
                diag["committed_tag"] = getattr(editor, "_last_scene_trace_sampling_mode", None)
                diag["active_preview_mode"] = getattr(editor, "_active_preview_sampling_mode", None)
                _safe("preview_3d_mode", editor._preview_3d_sampling_mode)
                _safe("preview_2d_mode", editor._preview_2d_sampling_mode)
                _safe("prefers_meridional_fan", editor._launch_pupil_prefers_meridional_fan)
                _safe("is_full_pupil_mode", editor._is_full_pupil_mode)
                _safe("ray_count", editor._current_ray_count)

                def _trace_flags():
                    tm = editor._resolved_trace_mode(system=getattr(editor, "last_system", None))
                    if isinstance(tm, dict):
                        return {k: tm.get(k) for k in ("use_nonseq", "use_folded", "mode", "trace_mode")}
                    return tm
                _safe("resolved_trace_mode", _trace_flags)
                # bugs/0187: the ACTUAL tracer backend used for the last preview. Unlike
                # resolved_trace_mode (which reports the off-axis classification and stays
                # non-seq for a folded Mirror), this reveals whether the folded-sequential
                # fix engaged: "Scalar TraceLoop"/"BatchTraceLoop" => folded-sequential ran,
                # "NsTraceLoop" => non-seq (fix did not engage / stale app).
                diag["actual_trace_backend"] = getattr(editor, "_last_preview_trace_backend", None)
                diag["folded_sequential_engaged"] = getattr(
                    editor, "_last_preview_folded_sequential", None
                )
                # bugs/0235: WHY the off-thread worker trace did/did-not engage. When
                # actual_trace_backend is the synchronous "Scalar TraceLoop" on a promoted
                # STEP scene, async_trace_decision says which gate rejected the kick
                # ("no_promoted_step_rows", "capture_none", ...), and async_trace_worker_outcome
                # reveals a kicked-but-failed worker ("worker_failed" + error tail) that fell
                # back to the sync 41s trace -- the flag_20260706_070708_237 case.
                diag["async_trace_decision"] = getattr(editor, "_last_async_trace_decision", None)
                diag["async_trace_worker_outcome"] = getattr(
                    editor, "_last_async_trace_worker_outcome", None
                )

                def _bundle_mode():
                    from KrakenOS.UI.layout_plot_controller import scene_bundle_launch_sampling_mode
                    return scene_bundle_launch_sampling_mode(getattr(editor, "_last_scene_bundle", None))
                _safe("cached_bundle_mode", _bundle_mode)
            snapshot.sampling_diagnostics = diag
        except Exception:
            pass

        try:  # bugs/0393: last lens-swap camera-body clearance diagnostics
            swap_dbg = getattr(inspector.editor, "_swap_clearance_debug", None)
            if isinstance(swap_dbg, dict):
                snapshot.swap_clearance_diagnostics = dict(swap_dbg)
        except Exception:
            pass

        try:  # bugs/0398: BS-follower diagnostics -- why an added BS still re-aims the camera
            from KrakenOS.UI.nonseq_output_ports import (
                build_optical_solid_output_port_pose_overrides,
                _row_is_marked_beam_splitter,
                _row_advanced,
            )
            editor_rows = list(getattr(inspector.editor, "rows", []) or [])
            overrides = build_optical_solid_output_port_pose_overrides(editor_rows) or {}
            override_keys = sorted(int(k) for k in overrides)
            promoted = []
            for idx, row in enumerate(editor_rows):
                advanced = _row_advanced(row)
                if str(advanced.get("Solid_3d_stl") or "").strip() in {"", "None"}:
                    continue
                promotion = advanced.get("StepOverlayPromotion")
                promoted.append({
                    "row": idx,
                    "name": str(getattr(row, "name", "") or "")[:36],
                    "top_marker": bool(advanced.get("OpticalSolidBeamSplitter")),
                    "promo_marker": bool(isinstance(promotion, dict) and promotion.get("beam_splitter")),
                    "is_marked": bool(_row_is_marked_beam_splitter(row)),
                    "is_fold_override": idx in overrides,
                })
            snapshot.bs_follower_diagnostics = {
                "n_rows": len(editor_rows),
                "override_keys": override_keys,
                "promoted": promoted,
            }
        except Exception as exc:
            snapshot.bs_follower_diagnostics = {"error": repr(exc)[:160]}

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
