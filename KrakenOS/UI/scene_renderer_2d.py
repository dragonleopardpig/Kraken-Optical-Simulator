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
    ProjectedCurve2D,
    ProjectedRay2D,
    ProjectedScene2D,
)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def render_scene_2d(
    projected: ProjectedScene2D,
    ax: Any,
    *,
    show_clipped_rays: bool = True,
    ray_count_hint: int = 5,
) -> int:
    """Draw all projected geometry on *ax*.

    Returns the number of surface lines drawn (useful for z-order styling).
    """
    surf_line_count = _draw_surface_curves(projected.curves, ax)
    _style_surface_lines(ax, surf_line_count)
    _draw_rays(projected.rays, ax, show_clipped=show_clipped_rays, ray_count_hint=ray_count_hint)
    _draw_labels(projected.labels, ax)
    return surf_line_count


def render_optics_markers(
    planes: list[PlaneMarker],
    ax: Any,
    *,
    orientation: str = "Vertical",
    project_fn: Any = None,
) -> list[Any]:
    """Draw cardinal-plane markers.  Returns the created artists."""
    artists: list[Any] = []
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    x_min, x_max = min(x0, x1), max(x0, x1)
    y_min, y_max = min(y0, y1), max(y0, y1)
    span = y1 - y0
    y_top = y1 - 0.18 * span

    for plane in planes:
        z_val = float(plane.z_position)
        color = plane.color
        label = plane.label

        if orientation == "Horizontal":
            if project_fn is not None:
                _, y_vals = project_fn([z_val, z_val], [0.0, 0.0])
                y_mark = float(y_vals[0])
            else:
                y_mark = -z_val
            if y_mark < y_min or y_mark > y_max:
                continue
            line = ax.axhline(y_mark, color=color, linewidth=1.0, linestyle=":", alpha=0.9)
            text = ax.text(
                x0 + 0.04 * (x1 - x0), y_mark, label,
                color=color, fontsize=8, ha="left", va="bottom",
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.65, "pad": 0.6},
            )
            artists.extend((line, text))
        else:
            if z_val < x_min or z_val > x_max:
                continue
            line = ax.axvline(z_val, color=color, linewidth=1.0, linestyle=":", alpha=0.9)
            text = ax.text(
                z_val, y_top, label,
                color=color, fontsize=8, ha="center", va="top",
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.65, "pad": 0.6},
            )
            artists.extend((line, text))
    return artists


def set_plot_limits(
    ax: Any,
    bounds: BoundsRect,
    *,
    max_radius: float = 1.0,
    has_off_axis: bool = False,
    orientation: str = "Vertical",
    use_drawn_data: bool = False,
) -> None:
    """Set axis limits from the projected bounds or from drawn data."""
    if use_drawn_data or has_off_axis or orientation == "Horizontal":
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
            line.set_zorder(max(float(line.get_zorder()), 20.0))
        else:
            line.set_zorder(min(float(line.get_zorder()), 10.0))


def _draw_rays(
    rays: list[ProjectedRay2D],
    ax: Any,
    *,
    show_clipped: bool = True,
    ray_count_hint: int = 5,
) -> None:
    linewidth = 1.1 if ray_count_hint <= 9 else 0.8
    alpha = 0.92 if ray_count_hint <= 9 else 0.72
    for ray in rays:
        if not show_clipped and not ray.reaches_image:
            continue
        pts = np.asarray(ray.points_2d, dtype=float)
        if pts.ndim != 2 or pts.shape[0] < 2:
            continue
        ax.plot(pts[:, 0], pts[:, 1], color=ray.color, linewidth=linewidth, alpha=alpha)


def _draw_labels(labels: list[LabelSpec], ax: Any) -> None:
    for label in labels:
        ax.text(
            label.x, label.y, label.text,
            ha=label.ha, va=label.va,
            fontsize=label.fontsize, color=label.color,
            clip_on=True,
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
