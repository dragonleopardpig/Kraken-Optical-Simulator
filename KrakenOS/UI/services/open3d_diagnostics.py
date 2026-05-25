"""Shared Open 3D diagnostic report helpers."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from KrakenOS.UI.scene_geometry import ray_path_terminal_status_from_events


def event_face_id(event: object) -> str:
    metadata = getattr(event, "metadata", {}) or {}
    if not isinstance(metadata, dict):
        metadata = {}
    return str(
        getattr(event, "mesh_face_id", "")
        or getattr(event, "face_id", "")
        or metadata.get("mesh_face_id", "")
        or metadata.get("face_id", "")
        or ""
    ).strip()


def event_action(event: object) -> str:
    return str(getattr(event, "event_type", "") or getattr(event, "interaction", "") or "").strip().lower()


def surface_events(path: object) -> list[object]:
    return [
        event
        for event in list(getattr(path, "events", []) or [])
        if str(getattr(event, "event_kind", "") or "") == "surface"
    ]


def surface_sequence(path: object) -> tuple[str, ...]:
    sequence: list[str] = []
    for event in surface_events(path):
        face_id = event_face_id(event) or "surface"
        action = event_action(event)
        sequence.append(f"{face_id}:{action}" if action else face_id)
    return tuple(sequence)


def last_surface_summary(path: object) -> str:
    sequence = surface_sequence(path)
    if not sequence:
        return ""
    face_action = sequence[-1].split(":", 1)
    if len(face_action) == 2 and face_action[1]:
        return f"{face_action[0]} {face_action[1]}"
    return face_action[0]


def all_surface_events(ray_paths: list[object]) -> list[tuple[str, str]]:
    return [
        (event_face_id(event), event_action(event))
        for path in ray_paths
        for event in surface_events(path)
    ]


def central_path(ray_paths: list[object]) -> object:
    if not ray_paths:
        raise RuntimeError("No ray paths were rendered.")

    def _score(path: object) -> tuple[float, int]:
        points = np.asarray(getattr(path, "points_world", ()), dtype=float)
        radius = float("inf")
        if points.ndim == 2 and points.shape[0] and points.shape[1] >= 2:
            radius = float(np.linalg.norm(points[0, :2]))
        return radius, int(getattr(path, "ray_index", 0) or 0)

    return min(ray_paths, key=_score)


def terminal_direction(path: object) -> list[float]:
    points = np.asarray(getattr(path, "points_world", ()), dtype=float)
    if points.ndim != 2 or points.shape[0] < 2 or points.shape[1] < 3:
        return []
    direction = points[-1, :3] - points[-2, :3]
    norm = float(np.linalg.norm(direction))
    if norm <= 1e-12:
        return []
    return [round(float(value), 9) for value in (direction / norm)[:3]]


def ray_path_signature(path: object) -> dict[str, object]:
    points = np.asarray(getattr(path, "points_world", ()), dtype=float)
    terminal_point: list[float] = []
    max_abs_coordinate = 0.0
    if points.ndim == 2 and points.shape[0] and points.shape[1] >= 3:
        terminal_point = [round(float(value), 6) for value in points[-1, :3]]
        finite = points[:, :3][np.isfinite(points[:, :3])]
        if finite.size:
            max_abs_coordinate = float(np.max(np.abs(finite)))
    return {
        "ray_index": int(getattr(path, "ray_index", 0) or 0),
        "source_ray_index": int(getattr(path, "source_ray_index", getattr(path, "ray_index", 0)) or 0),
        "terminal_status": str(ray_path_terminal_status_from_events(path) or "unknown"),
        "terminal_point": terminal_point,
        "terminal_direction": terminal_direction(path),
        "max_abs_coordinate": round(max_abs_coordinate, 6),
        "sequence": " -> ".join(surface_sequence(path)),
    }


def snapshot_stats(path: Path) -> dict[str, object]:
    try:
        from PIL import Image
    except Exception:
        return {"path": str(path), "bytes": path.stat().st_size, "pixel_check": "PIL unavailable"}
    image = Image.open(path).convert("RGB")
    pixels = np.asarray(image, dtype=np.uint8)
    non_white = np.any(pixels < 245, axis=2)
    colored = (
        (np.abs(pixels[:, :, 0].astype(int) - pixels[:, :, 1].astype(int)) > 8)
        | (np.abs(pixels[:, :, 1].astype(int) - pixels[:, :, 2].astype(int)) > 8)
        | (np.abs(pixels[:, :, 0].astype(int) - pixels[:, :, 2].astype(int)) > 8)
    )
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "size": [int(image.width), int(image.height)],
        "non_white_pixels": int(np.count_nonzero(non_white)),
        "colored_pixels": int(np.count_nonzero(colored)),
    }


def trace_summary_text(inspector: object) -> str:
    actor = getattr(inspector, "_trace_summary_actor", None)
    if actor is None:
        return ""
    try:
        return str(actor.GetInput() or "")
    except Exception:
        return ""


def scene_bundle_state_report(
    scene_bundle: object,
    label: str,
    *,
    sampling_mode: object = "",
    image_path: Path | None = None,
    status: object = "",
    trace_summary: object = "",
) -> dict[str, Any]:
    ray_paths = list(getattr(scene_bundle, "ray_paths", []) or [])
    terminal_counts = Counter(
        str(ray_path_terminal_status_from_events(path) or "unknown").strip() or "unknown"
        for path in ray_paths
    )
    terminal_faces = Counter(last_surface_summary(path) for path in ray_paths if last_surface_summary(path))
    events = Counter(all_surface_events(ray_paths))
    sequences = Counter(surface_sequence(path) for path in ray_paths)
    path_signatures = [
        ray_path_signature(path)
        for path in sorted(ray_paths, key=lambda item: int(getattr(item, "ray_index", 0) or 0))
    ]
    report: dict[str, Any] = {
        "label": str(label),
        "sampling_mode": str(sampling_mode or ""),
        "path_count": len(ray_paths),
        "ray_paths": len(ray_paths),
        "terminal_counts": dict(sorted(terminal_counts.items())),
        "terminal_last_faces": dict(sorted(terminal_faces.items())),
        "central_path": ray_path_signature(central_path(ray_paths)) if ray_paths else {},
        "path_signatures": path_signatures,
        "surface_event_counts": {f"{face}:{action}": count for (face, action), count in sorted(events.items())},
        "surface_sequence_counts": {" -> ".join(sequence): count for sequence, count in sorted(sequences.items())},
    }
    if image_path is not None:
        report["image"] = snapshot_stats(image_path)
    if trace_summary:
        report["trace_summary_text"] = str(trace_summary)
    if status:
        report["status"] = str(status)
    return report


def inspector_state_report(
    inspector: object,
    label: str,
    *,
    image_path: Path | None = None,
    status: object = "",
) -> dict[str, Any]:
    return scene_bundle_state_report(
        getattr(inspector, "_current_scene_bundle", None),
        label,
        sampling_mode=getattr(inspector, "_last_refresh_sampling_mode", ""),
        image_path=image_path,
        status=status,
        trace_summary=trace_summary_text(inspector),
    )
