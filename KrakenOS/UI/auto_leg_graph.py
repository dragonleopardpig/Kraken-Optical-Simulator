"""Automatic branch-leg graph helpers for 2-D folded-path labeling.

The layout editor owns UI state and drawing.  This module owns the pure graph
extraction that turns projected branch rays into stable user-facing path legs.
"""

from __future__ import annotations

import hashlib
from typing import Iterable

import numpy as np


DEFAULT_BEAM_SPLITTER_SURFACE = "Beam Splitter"


def auto_leg_point_key(point: object, tolerance: float = 0.25) -> str:
    arr = np.asarray(point, dtype=float).ravel()
    if arr.size < 2 or not np.all(np.isfinite(arr[:2])):
        return "nan"
    scale = max(float(tolerance), 1e-9)
    return f"{round(float(arr[0]) / scale):.0f},{round(float(arr[1]) / scale):.0f}"


def auto_leg_node_label(node: dict[str, object]) -> str:
    label = str(node.get("label", "") or "").strip()
    return label or str(node.get("key", "") or "node").strip()


def auto_leg_node_for_hit(
    point: object,
    surface_id: int | None,
    rows: Iterable[object],
    *,
    branch_path: str = "",
    branch_label: str = "",
    beam_splitter_surface: str = DEFAULT_BEAM_SPLITTER_SURFACE,
) -> dict[str, object]:
    row_list = list(rows)
    if surface_id is None or not (0 <= int(surface_id) < len(row_list)):
        branch_path = str(branch_path or "").strip()
        branch_label = str(branch_label or "").strip().lower()
        if branch_path and branch_path != "primary":
            stable = hashlib.sha1(branch_path.encode("utf-8")).hexdigest()[:10]
            key = f"term:path:{stable}"
        elif branch_label and branch_label != "primary":
            key = f"term:label:{branch_label}"
        else:
            key = f"term:{auto_leg_point_key(point)}"
        return {
            "key": key,
            "label": "Terminal",
            "row_index": None,
            "kind": "terminal",
        }
    row = row_list[int(surface_id)]
    if getattr(row, "surface", "") == beam_splitter_surface:
        kind = "beam_splitter"
        key = f"bs:{int(surface_id)}"
    else:
        kind = "terminal"
        key = f"row:{int(surface_id)}"
    return {
        "key": key,
        "label": str(getattr(row, "name", "") or getattr(row, "element", "") or f"S{int(surface_id)}").strip(),
        "row_index": int(surface_id),
        "kind": kind,
    }


def auto_leg_hit_point_index(points: np.ndarray, surface_ids: np.ndarray, hit_index: int) -> int:
    if points.shape[0] >= surface_ids.size + 1:
        return min(max(int(hit_index) + 1, 0), points.shape[0] - 1)
    return min(max(int(hit_index), 0), points.shape[0] - 1)


def auto_leg_candidate_key(
    start_node: dict[str, object],
    end_node: dict[str, object],
    non_branch_surface_ids: tuple[int, ...],
) -> tuple[tuple[str, str], tuple[int, ...]]:
    node_pair = tuple(sorted((str(start_node.get("key", "")), str(end_node.get("key", "")))))
    reverse_ids = tuple(reversed(non_branch_surface_ids))
    surface_key = min(non_branch_surface_ids, reverse_ids)
    return node_pair, surface_key


def auto_leg_midpoint(polyline: object) -> np.ndarray:
    arr = np.asarray(polyline, dtype=float)
    if arr.ndim != 2 or arr.shape[0] == 0:
        return np.zeros(2, dtype=float)
    if arr.shape[0] == 1:
        return np.asarray(arr[0, :2], dtype=float)
    lengths = np.linalg.norm(np.diff(arr[:, :2], axis=0), axis=1)
    total = float(np.sum(lengths))
    if total <= 1e-12:
        return np.asarray(arr[arr.shape[0] // 2, :2], dtype=float)
    target = 0.5 * total
    accumulated = 0.0
    for index, length in enumerate(lengths):
        if accumulated + float(length) >= target:
            local = (target - accumulated) / max(float(length), 1e-12)
            return arr[index, :2] + (arr[index + 1, :2] - arr[index, :2]) * local
        accumulated += float(length)
    return np.asarray(arr[-1, :2], dtype=float)


def auto_leg_representative_polyline(polylines: Iterable[object]) -> np.ndarray:
    clean = [np.asarray(polyline, dtype=float) for polyline in polylines if np.asarray(polyline, dtype=float).ndim == 2]
    clean = [polyline[:, :2] for polyline in clean if polyline.shape[0] >= 2]
    if not clean:
        return np.empty((0, 2), dtype=float)
    midpoints = np.vstack([auto_leg_midpoint(polyline) for polyline in clean])
    median_midpoint = np.median(midpoints, axis=0)
    return min(clean, key=lambda polyline: float(np.linalg.norm(auto_leg_midpoint(polyline) - median_midpoint)))


def auto_leg_direction_from_node(entry: dict[str, object], node_key: str) -> np.ndarray:
    polyline = np.asarray(entry.get("polyline", []), dtype=float)
    if polyline.ndim != 2 or polyline.shape[0] < 2:
        return np.array([1.0, 0.0], dtype=float)
    start_key = str(entry.get("start_node_key", "") or "")
    if str(node_key) == start_key:
        pairs = zip(polyline[:-1], polyline[1:])
    else:
        pairs = zip(polyline[:0:-1], polyline[-2::-1])
    for p0, p1 in pairs:
        direction = np.asarray(p1, dtype=float) - np.asarray(p0, dtype=float)
        norm = float(np.linalg.norm(direction))
        if norm > 1e-9:
            return direction / norm
    return np.array([1.0, 0.0], dtype=float)


def ordered_auto_leg_keys(
    legs: dict[tuple[tuple[str, str], tuple[int, ...]], dict[str, object]],
) -> list[tuple[tuple[str, str], tuple[int, ...]]]:
    adjacency: dict[str, list[tuple[tuple[str, str], tuple[int, ...]]]] = {}
    for key, entry in legs.items():
        for node_key in (str(entry.get("start_node_key", "")), str(entry.get("end_node_key", ""))):
            if node_key:
                adjacency.setdefault(node_key, []).append(key)

    def sort_key(edge_key: tuple[tuple[str, str], tuple[int, ...]], node_key: str) -> tuple[float, str]:
        entry = legs[edge_key]
        direction = auto_leg_direction_from_node(entry, node_key)
        angle = float(np.rad2deg(np.arctan2(float(direction[1]), float(direction[0]))))
        if angle < 0.0:
            angle += 360.0
        return angle, str(entry.get("stable_signature", ""))

    ordered: list[tuple[tuple[str, str], tuple[int, ...]]] = []
    visited_edges: set[tuple[tuple[str, str], tuple[int, ...]]] = set()
    visited_nodes: set[str] = set()
    queue: list[str] = ["source"] if "source" in adjacency else sorted(adjacency)[:1]
    while queue:
        node_key = queue.pop(0)
        if node_key in visited_nodes:
            continue
        visited_nodes.add(node_key)
        for edge_key in sorted(adjacency.get(node_key, []), key=lambda key: sort_key(key, node_key)):
            if edge_key in visited_edges:
                continue
            visited_edges.add(edge_key)
            ordered.append(edge_key)
            entry = legs[edge_key]
            other = (
                str(entry.get("end_node_key", "") or "")
                if str(entry.get("start_node_key", "") or "") == node_key
                else str(entry.get("start_node_key", "") or "")
            )
            if other and other not in visited_nodes and other not in queue:
                queue.append(other)
    for edge_key in sorted(legs, key=lambda key: str(legs[key].get("stable_signature", ""))):
        if edge_key not in visited_edges:
            ordered.append(edge_key)
    return ordered


def leg_geometry_from_points(points: Iterable[object]) -> dict[str, object] | None:
    clean_points: list[np.ndarray] = []
    for point in points:
        arr = np.asarray(point, dtype=float).ravel()
        if arr.size >= 2 and np.all(np.isfinite(arr[:2])):
            clean_points.append(np.asarray(arr[:2], dtype=float))
    if len(clean_points) < 2:
        return None
    segments: list[tuple[np.ndarray, np.ndarray]] = []
    total_length = 0.0
    for p0, p1 in zip(clean_points[:-1], clean_points[1:]):
        length = float(np.linalg.norm(p1 - p0))
        if length <= 1e-9:
            continue
        segments.append((p0, p1))
        total_length += length
    if not segments:
        return None
    first = segments[0][0]
    last = segments[-1][1]
    vector = last - first
    length = float(np.linalg.norm(vector))
    if length > 1e-9:
        unit = vector / length
    else:
        first_segment = segments[0][1] - segments[0][0]
        unit = first_segment / max(float(np.linalg.norm(first_segment)), 1e-12)
    return {
        "points": clean_points,
        "segments": segments,
        "hub": first,
        "endpoint": last,
        "unit": unit,
        "length": np.asarray([total_length], dtype=float),
    }


def build_auto_leg_entries_from_projected(
    projected: object,
    rows: Iterable[object],
    *,
    beam_splitter_surface: str = DEFAULT_BEAM_SPLITTER_SURFACE,
) -> list[dict[str, object]]:
    row_list = list(rows)
    if not any(getattr(row, "surface", "") == beam_splitter_surface for row in row_list):
        return []
    legs: dict[tuple[tuple[str, str], tuple[int, ...]], dict[str, object]] = {}
    for ray in getattr(projected, "rays", []) or []:
        points = np.asarray(getattr(ray, "points_2d", []), dtype=float)
        surface_ids = np.asarray(getattr(ray, "surface_ids", []), dtype=int).ravel()
        branch_path = str(getattr(ray, "branch_path", "") or "").strip()
        branch_label = str(getattr(ray, "branch_label", "") or "").strip()
        if points.ndim != 2 or points.shape[0] < 2:
            continue
        breakpoints: list[tuple[int, dict[str, object]]] = [
            (
                0,
                {
                    "key": "source",
                    "label": "Input",
                    "row_index": 0 if row_list else None,
                    "kind": "source",
                },
            )
        ]
        point_index_by_hit: dict[int, int] = {}
        for hit_index, raw_surface_id in enumerate(surface_ids.tolist()):
            surface_id = int(raw_surface_id)
            point_index = auto_leg_hit_point_index(points, surface_ids, hit_index)
            point_index_by_hit[hit_index] = point_index
            if 0 <= surface_id < len(row_list) and getattr(row_list[surface_id], "surface", "") == beam_splitter_surface:
                breakpoints.append(
                    (
                        point_index,
                        auto_leg_node_for_hit(points[point_index], surface_id, row_list, beam_splitter_surface=beam_splitter_surface),
                    )
                )
        if surface_ids.size:
            terminal_surface_id = int(surface_ids[-1])
            terminal_hit_index = int(surface_ids.size - 1)
            terminal_point_index = point_index_by_hit.get(
                terminal_hit_index,
                auto_leg_hit_point_index(points, surface_ids, terminal_hit_index),
            )
            if not (
                0 <= terminal_surface_id < len(row_list)
                and getattr(row_list[terminal_surface_id], "surface", "") == beam_splitter_surface
            ):
                breakpoints.append(
                    (
                        terminal_point_index,
                        auto_leg_node_for_hit(
                            points[terminal_point_index],
                            terminal_surface_id,
                            row_list,
                            branch_path=branch_path,
                            branch_label=branch_label,
                            beam_splitter_surface=beam_splitter_surface,
                        ),
                    )
                )
        last_surface_is_splitter = (
            bool(surface_ids.size)
            and 0 <= int(surface_ids[-1]) < len(row_list)
            and getattr(row_list[int(surface_ids[-1])], "surface", "") == beam_splitter_surface
        )
        if breakpoints[-1][0] < points.shape[0] - 1 and (len(breakpoints) == 1 or last_surface_is_splitter):
            breakpoints.append(
                (
                    points.shape[0] - 1,
                    auto_leg_node_for_hit(
                        points[-1],
                        None,
                        row_list,
                        branch_path=branch_path,
                        branch_label=branch_label,
                        beam_splitter_surface=beam_splitter_surface,
                    ),
                )
            )

        deduped: list[tuple[int, dict[str, object]]] = []
        for point_index, node in sorted(breakpoints, key=lambda item: item[0]):
            point_index = min(max(int(point_index), 0), points.shape[0] - 1)
            if deduped and point_index == deduped[-1][0] and str(node.get("key", "")) == str(deduped[-1][1].get("key", "")):
                continue
            if deduped and point_index == deduped[-1][0]:
                deduped[-1] = (point_index, node)
            else:
                deduped.append((point_index, node))
        if len(deduped) < 2:
            continue

        for (start_point_index, start_node), (end_point_index, end_node) in zip(deduped[:-1], deduped[1:]):
            if end_point_index <= start_point_index:
                continue
            polyline = np.asarray(points[start_point_index : end_point_index + 1, :2], dtype=float)
            if polyline.shape[0] < 2 or not np.all(np.isfinite(polyline)):
                continue
            segment_surface_ids: list[int] = []
            non_branch_surface_ids: list[int] = []
            for hit_index, surface_id_raw in enumerate(surface_ids.tolist()):
                point_index = point_index_by_hit.get(hit_index)
                if point_index is None or point_index <= start_point_index or point_index > end_point_index:
                    continue
                surface_id = int(surface_id_raw)
                if not (0 <= surface_id < len(row_list)):
                    continue
                segment_surface_ids.append(surface_id)
                if getattr(row_list[surface_id], "surface", "") != beam_splitter_surface:
                    non_branch_surface_ids.append(surface_id)
            candidate_key = auto_leg_candidate_key(start_node, end_node, tuple(non_branch_surface_ids))
            stable_signature = "|".join(
                [
                    ",".join(candidate_key[0]),
                    ",".join(str(value) for value in candidate_key[1]),
                ]
            )
            if candidate_key not in legs:
                legs[candidate_key] = {
                    "start_node": start_node,
                    "end_node": end_node,
                    "start_node_key": str(start_node.get("key", "")),
                    "end_node_key": str(end_node.get("key", "")),
                    "stable_signature": stable_signature,
                    "polylines": [],
                    "surface_indices": set(),
                    "context_indices": set(),
                    "segment_surface_ids": set(),
                }
            entry = legs[candidate_key]
            entry["polylines"].append(polyline)
            entry["surface_indices"].update(non_branch_surface_ids)
            entry["segment_surface_ids"].update(segment_surface_ids)
            for node in (start_node, end_node):
                row_index = node.get("row_index")
                if row_index is not None:
                    entry["context_indices"].add(int(row_index))

    entries: list[dict[str, object]] = []
    for leg_number, key in enumerate(ordered_auto_leg_keys(legs), start=1):
        entry = legs[key]
        polyline = auto_leg_representative_polyline(list(entry.get("polylines", []) or []))
        if polyline.shape[0] < 2:
            continue
        stable_hash = hashlib.sha1(str(entry.get("stable_signature", "")).encode("utf-8")).hexdigest()[:10]
        start_label = auto_leg_node_label(dict(entry.get("start_node", {}) or {}))
        end_label = auto_leg_node_label(dict(entry.get("end_node", {}) or {}))
        via_surface_indices = set(entry.get("surface_indices", set()) or set()) - set(entry.get("context_indices", set()) or set())
        via_names = [
            str(getattr(row_list[index], "name", "") or getattr(row_list[index], "element", "") or f"S{index}").strip()
            for index in sorted(via_surface_indices)
            if 0 <= int(index) < len(row_list)
        ]
        detail = f"Input to {end_label}" if start_label == "Input" else f"{start_label} to {end_label}"
        if via_names:
            detail = f"{detail} via {', '.join(via_names[:3])}"
            if len(via_names) > 3:
                detail = f"{detail}, +{len(via_names) - 3} more"
        entries.append(
            {
                "leg_id": f"auto_{stable_hash}",
                "short_label": f"Path {leg_number}",
                "detail": detail,
                "polyline": polyline,
                "segments": leg_geometry_from_points([point for point in polyline]),
                "surface_indices": set(entry.get("surface_indices", set()) or set()),
                "context_indices": set(entry.get("context_indices", set()) or set()),
                "segment_surface_ids": set(entry.get("segment_surface_ids", set()) or set()),
                "start_node_key": str(entry.get("start_node_key", "")),
                "end_node_key": str(entry.get("end_node_key", "")),
            }
        )
    return entries
