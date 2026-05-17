"""Render a ProjectedScene2D onto a matplotlib Axes.

This module depends on matplotlib and numpy only.  It does not import
KrakenOS, VTK, or tkinter widgets.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .scene_geometry import (
    BoundsRect,
    LabelSpec,
    PlaneMarker,
    PROJECTED_TERMINAL_STATUS_LABELS,
    ProjectedCurve2D,
    ProjectedRay2D,
    ProjectedScene2D,
    projected_ray_hits_detector,
    projected_ray_terminal_marker,
    projected_ray_terminal_status,
)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def render_scene_2d(
    projected: ProjectedScene2D,
    ax: Any,
    *,
    show_clipped_rays: bool = True,
    show_labels: bool = True,
    ray_count_hint: int = 5,
) -> int:
    """Draw all projected geometry on *ax*.

    Returns the number of surface lines drawn (useful for z-order styling).
    """
    surf_line_count = _draw_surface_curves(projected.curves, ax)
    _style_surface_lines(ax, surf_line_count)
    _draw_rays(projected.rays, ax, show_clipped=show_clipped_rays, ray_count_hint=ray_count_hint)
    if show_labels:
        _draw_labels(projected.labels, ax)
    return surf_line_count


def render_optics_markers(
    planes: list[PlaneMarker],
    ax: Any,
    *,
    orientation: str = "YZ",
    project_fn: Any = None,
) -> list[Any]:
    """Draw cardinal-plane markers.  Returns the created artists."""
    artists: list[Any] = []
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    x_min, x_max = min(x0, x1), max(x0, x1)
    y_min, y_max = min(y0, y1), max(y0, y1)
    span_x = max(x_max - x_min, 1e-9)
    span_y = max(y_max - y_min, 1e-9)

    visible_markers: list[tuple[PlaneMarker, float]] = []
    for plane in planes:
        z_val = float(plane.z_position)
        if orientation == "Horizontal":
            if project_fn is not None:
                _, y_vals = project_fn([z_val, z_val], [0.0, 0.0])
                y_mark = float(y_vals[0])
            else:
                y_mark = -z_val
            if y_mark < y_min or y_mark > y_max:
                continue
            visible_markers.append((plane, y_mark))
        else:
            if z_val < x_min or z_val > x_max:
                continue
            visible_markers.append((plane, z_val))

    for index, (plane, marker_pos) in enumerate(visible_markers):
        color = plane.color
        label = plane.label

        if orientation == "Horizontal":
            y_mark = marker_pos
            x_label = x_min + (0.04 + 0.10 * (index % 4)) * span_x
            y_offsets = (0.015, 0.055, -0.035, 0.095)
            y_label = y_mark + y_offsets[index % len(y_offsets)] * span_y
            y_label = min(max(y_label, y_min + 0.04 * span_y), y_max - 0.04 * span_y)
            line = ax.axhline(y_mark, color=color, linewidth=1.0, linestyle=":", alpha=0.9, zorder=70.0)
            text = ax.text(
                x_label, y_label, label,
                color=color, fontsize=8, ha="left", va="bottom",
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.65, "pad": 0.6},
                zorder=71.0,
            )
            artists.extend((line, text))
        else:
            z_val = marker_pos
            y_label = y_max - (0.10 + 0.065 * (index % 4)) * span_y
            line = ax.axvline(z_val, color=color, linewidth=1.0, linestyle=":", alpha=0.9, zorder=70.0)
            text = ax.text(
                z_val, y_label, label,
                color=color, fontsize=8, ha="center", va="top",
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.65, "pad": 0.6},
                zorder=71.0,
            )
            artists.extend((line, text))
    return artists


def set_plot_limits(
    ax: Any,
    bounds: BoundsRect,
    *,
    max_radius: float = 1.0,
    has_off_axis: bool = False,
    orientation: str = "YZ",
    use_drawn_data: bool = False,
) -> None:
    """Set axis limits from the projected bounds or from drawn data."""
    if use_drawn_data or has_off_axis or str(orientation or "") in {"Horizontal", "XZ", "XY"}:
        _set_limits_from_drawn_data(ax, bounds)
        ax.set_aspect("equal", adjustable="box")
    else:
        _set_limits_from_layout(ax, bounds, max_radius)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _draw_surface_curves(curves: list[ProjectedCurve2D], ax: Any) -> int:
    count = 0
    for curve in curves:
        pts = np.asarray(curve.points_2d, dtype=float)
        if pts.ndim != 2 or pts.shape[0] < 2:
            continue
        ax.plot(
            pts[:, 0], pts[:, 1],
            color=curve.style.color,
            linewidth=curve.style.linewidth,
            alpha=curve.style.alpha,
            solid_capstyle="round",
        )
        count += 1
    return count


def _style_surface_lines(ax: Any, surf_line_count: int) -> None:
    for index, line in enumerate(ax.lines):
        if index < surf_line_count:
            line.set_linewidth(max(line.get_linewidth(), 1.25))
            line.set_zorder(max(float(line.get_zorder()), 40.0))
        else:
            line.set_zorder(min(float(line.get_zorder()), 18.0))


def _draw_rays(
    rays: list[ProjectedRay2D],
    ax: Any,
    *,
    show_clipped: bool = True,
    ray_count_hint: int = 5,
) -> None:
    if ray_count_hint <= 9:
        linewidth = 1.1
        alpha = 0.92
    elif ray_count_hint <= 16:
        linewidth = 0.7
        alpha = 0.48
    else:
        linewidth = 0.55
        alpha = 0.32
    if rays:
        field_indices = [int(ray.field_index) for ray in rays]
        field_center = 0.5 * (min(field_indices) + max(field_indices))
        ordered_rays = sorted(
            rays,
            key=lambda ray: (abs(float(ray.field_index) - field_center), int(ray.ray_index)),
            reverse=True,
        )
    else:
        ordered_rays = []
    total_rays = max(len(ordered_rays), 1)
    show_direction_markers = ray_count_hint <= 3 and len(ordered_rays) <= 12
    endpoint_points: list[tuple[float, float, str, str]] = []
    for draw_order, ray in enumerate(ordered_rays, start=1):
        if not show_clipped and not projected_ray_hits_detector(ray):
            continue
        pts = np.asarray(ray.points_2d, dtype=float)
        if pts.ndim != 2 or pts.shape[0] < 2:
            continue
        finite = np.isfinite(pts[:, 0]) & np.isfinite(pts[:, 1])
        if not np.any(finite):
            continue
        terminal_marker = projected_ray_terminal_marker(ray)
        if terminal_marker is not None:
            endpoint_points.append(terminal_marker)
        ax.plot(
            pts[:, 0],
            pts[:, 1],
            color=ray.color,
            linewidth=linewidth,
            alpha=alpha,
            # Keep rays above CAD/prism outlines so exits do not look broken
            # where a surface edge crosses the traced polyline.
            zorder=42.0 + (10.0 * draw_order / total_rays),
        )
        if show_direction_markers:
            _draw_ray_direction_markers(
                pts,
                ax,
                color=ray.color,
                alpha=alpha,
                zorder=28.0 + (5.0 * draw_order / total_rays),
            )
    _draw_ray_endpoint_markers(endpoint_points, ax, ray_count_hint=ray_count_hint)


def _draw_ray_endpoint_markers(
    endpoints: list[tuple[float, float, str, str]],
    ax: Any,
    *,
    ray_count_hint: int,
) -> None:
    if not endpoints or ray_count_hint > 16:
        return
    marker_size = 28.0 if ray_count_hint <= 16 else 20.0
    status_styles = {
        "hit_detector": ("#064e3b", 0.94),
        "missed_detector": ("#b45309", 0.9),
        "absorbed": ("#581c87", 0.9),
        "escaped": ("#475569", 0.86),
        "stopped": ("#7f1d1d", 0.9),
    }
    visible_handles = []
    for status, label in PROJECTED_TERMINAL_STATUS_LABELS.items():
        group = [(x, y, color) for x, y, color, item_status in endpoints if item_status == status]
        if not group:
            continue
        edge_color, alpha = status_styles.get(status, ("#7f1d1d", 0.9))
        xy = np.asarray([(x, y) for x, y, _color in group], dtype=float)
        colors = [color for _x, _y, color in group]
        artist = ax.scatter(
            xy[:, 0],
            xy[:, 1],
            s=marker_size,
            c=colors,
            edgecolors=edge_color,
            linewidths=0.35,
            alpha=alpha,
            zorder=86.0,
            label=label,
        )
        visible_handles.append(artist)
    if len(visible_handles) > 1:
        ax.legend(handles=visible_handles, loc="lower right", fontsize=7, title="Ray terminal")


def _draw_ray_direction_markers(
    points: np.ndarray,
    ax: Any,
    *,
    color: str,
    alpha: float,
    zorder: float,
) -> None:
    """Draw small arrows on sparse branch plots without cluttering bundles."""
    pts = np.asarray(points, dtype=float)
    if pts.ndim != 2 or pts.shape[0] < 2:
        return
    finite = np.isfinite(pts[:, 0]) & np.isfinite(pts[:, 1])
    if not np.all(finite):
        pts = pts[finite]
    if pts.shape[0] < 2:
        return
    for start, end in zip(pts[:-1], pts[1:]):
        delta = np.asarray(end - start, dtype=float)
        length = float(np.linalg.norm(delta))
        if length <= 1e-6:
            continue
        unit = delta / length
        marker_len = min(0.28 * length, max(2.5, 0.10 * length))
        midpoint = np.asarray(start, dtype=float) + 0.58 * delta
        tail = midpoint - 0.5 * marker_len * unit
        head = midpoint + 0.5 * marker_len * unit
        ax.annotate(
            "",
            xy=(float(head[0]), float(head[1])),
            xytext=(float(tail[0]), float(tail[1])),
            arrowprops={
                "arrowstyle": "-|>",
                "color": color,
                "linewidth": 0.75,
                "alpha": min(float(alpha) + 0.05, 0.98),
                "shrinkA": 0,
                "shrinkB": 0,
                "mutation_scale": 7,
            },
            zorder=zorder,
        )


def _draw_labels(labels: list[LabelSpec], ax: Any) -> None:
    for label in labels:
        ax.text(
            label.x, label.y, label.text,
            ha=label.ha, va=label.va,
            fontsize=label.fontsize, color=label.color,
            clip_on=True,
            zorder=60.0,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.65, "pad": 0.2},
        )


def _set_limits_from_drawn_data(ax: Any, bounds: BoundsRect) -> None:
    if bounds.is_empty:
        # Fall back to matplotlib auto-computed data bounds
        x_values: list[float] = []
        y_values: list[float] = []
        for line in ax.lines:
            xdata = np.asarray(line.get_xdata(orig=False), dtype=float)
            ydata = np.asarray(line.get_ydata(orig=False), dtype=float)
            finite = np.isfinite(xdata) & np.isfinite(ydata)
            if np.any(finite):
                x_values.extend(xdata[finite].tolist())
                y_values.extend(ydata[finite].tolist())
        if not x_values:
            return
        bounds = BoundsRect(
            x_min=min(x_values), x_max=max(x_values),
            y_min=min(y_values), y_max=max(y_values),
        )
    m = bounds.margin(0.08, 0.12)
    ax.set_xlim(m.x_min, m.x_max)
    ax.set_ylim(m.y_min, m.y_max)


def _set_limits_from_layout(ax: Any, bounds: BoundsRect, max_radius: float) -> None:
    total_length = max(bounds.x_max - bounds.x_min, 1.0) if not bounds.is_empty else 1.0
    # Use original heuristic: x from surface extent, y from max_radius
    margin_x = max(total_length * 0.05, 5.0)
    margin_y = max(max_radius * 0.2, 2.0)
    if bounds.is_empty:
        ax.set_xlim(-margin_x, total_length + margin_x)
    else:
        ax.set_xlim(bounds.x_min - margin_x, bounds.x_max + margin_x)
    ax.set_ylim(-(max_radius + margin_y), max_radius + margin_y)
