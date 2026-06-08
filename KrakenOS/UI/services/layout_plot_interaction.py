from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np


_PROTECTED_GLOBALS = {
    "LayoutPlotInteractionMixin",
    "_PROTECTED_GLOBALS",
    "_sync_layout_globals",
}


def _sync_layout_globals(source: dict[str, object]) -> None:
    target = globals()
    for name, value in source.items():
        if name.startswith("__") or name in _PROTECTED_GLOBALS:
            continue
        target[name] = value


class LayoutPlotInteractionMixin:
    def _open_plot_axis_once(self, target_ax) -> None:
        if target_ax not in {self.ax, self._analysis_ax, *self._analysis_axes}:
            return
        now = time.monotonic()
        if now - self._last_viewer_open_time < 0.4:
            return
        self._last_viewer_open_time = now
        self._open_high_res_plot_in_system_viewer(target_ax)

    def _plot_hover_hint_text(self, target_ax, x_display: float | None = None, y_display: float | None = None) -> str:
        if target_ax is self.ax:
            if x_display is not None and y_display is not None:
                ray_index = self._find_layout_pick_ray(float(x_display), float(y_display))
                if ray_index is not None:
                    return self._ray_terminal_hint_text(ray_index)
                row_index = self._find_layout_pick_row(float(x_display), float(y_display))
                if row_index is not None and 0 <= int(row_index) < len(self.rows):
                    row = self.rows[int(row_index)]
                    name = str(getattr(row, "name", "") or getattr(row, "surface", "") or "").strip()
                    return f"S{int(row_index)} {name}: click to select"
            return "Click surface to select, ray to inspect; empty area opens viewer"
        if target_ax is not None:
            return "Click to open in viewer"
        return ""

    def _on_plot_canvas_motion(self, event) -> None:
        target_ax = getattr(event, "inaxes", None)
        if target_ax not in self._hover_hint_artists:
            target_ax = None
        x_display = getattr(event, "x", None)
        y_display = getattr(event, "y", None)
        message = self._plot_hover_hint_text(target_ax, x_display, y_display)
        if target_ax is not None:
            self._set_hover_hint_text(target_ax, message)
        if target_ax is self.ax and message and message != self._last_plot_hover_message:
            self._last_plot_hover_message = message
            if message.startswith("Ray "):
                self.status_var.set(message)
        if target_ax is self._hover_axis:
            if hasattr(self, "canvas"):
                self.canvas.draw_idle()
            return
        self._set_hover_axis(target_ax)

    def _on_plot_canvas_leave(self, _event=None) -> None:
        self._last_plot_hover_message = ""
        self._set_hover_axis(None)

    def _on_plot_widget_click(self, event) -> str | None:
        try:
            self.canvas.draw()
            renderer = self.figure.canvas.get_renderer()
            widget = self.canvas.get_tk_widget()
            x_display = float(event.x)
            y_display = float(widget.winfo_height() - event.y)
            if self.ax is not None and self.ax in self.figure.axes:
                if self.ax.get_window_extent(renderer).contains(x_display, y_display):
                    ray_index = self._find_layout_pick_ray(x_display, y_display)
                    if ray_index is not None:
                        self._select_ray_inspector_ray(ray_index)
                        return "break"
                    row_index = self._find_layout_pick_row(x_display, y_display)
                    if row_index is not None:
                        self._select_table_row(row_index)
                        return "break"
                    self._open_plot_axis_once(self.ax)
                    return "break"
            for axis in self._analysis_axes or ([self._analysis_ax] if self._analysis_ax is not None else []):
                if axis is not None and axis in self.figure.axes:
                    if axis.get_window_extent(renderer).contains(x_display, y_display):
                        self._open_plot_axis_once(axis)
                        return "break"
        except Exception as exc:
            self.append_debug(f"Plot viewer dispatch failed: {exc}")
        return None

    def _find_layout_pick_row(self, x_display: float, y_display: float) -> int | None:
        if self.ax is None or not self._layout_pick_regions:
            return None
        return find_nearest_pick_region(
            (x_display, y_display),
            self._layout_pick_regions,
            transform_points=self.ax.transData.transform,
        )

    def _find_layout_pick_ray(self, x_display: float, y_display: float) -> int | None:
        if self.ax is None or not self._layout_ray_pick_regions:
            return None
        return find_nearest_ray_region(
            (x_display, y_display),
            self._layout_ray_pick_regions,
            transform_points=self.ax.transData.transform,
        )

    def _select_ray_inspector_ray(self, ray_index: int) -> None:
        try:
            index = int(ray_index)
        except Exception:
            return
        if self._ray_inspector_window is None or not self._ray_inspector_window.winfo_exists():
            self.open_ray_inspector()
        else:
            self._refresh_ray_inspector()
        table = self._ray_inspector_ray_table
        if table is None:
            return
        iid = str(index)
        if not table.exists(iid):
            self.status_var.set(f"Ray {index} is not available in the current Ray Inspector data.")
            return
        self._layout_selected_ray_index = index
        table.selection_set(iid)
        table.focus(iid)
        table.see(iid)
        self._populate_ray_inspector_hits()
        self._update_layout_selection_overlay()
        self.status_var.set(self._ray_terminal_hint_text(index, label=f"Selected ray {index} in Ray Inspector"))

    def _draw_layout_selected_ray_overlay(self, ray_index: int) -> bool:
        ray = self._layout_projected_rays_by_index.get(int(ray_index))
        if ray is None or self.ax is None:
            return False
        pts = np.asarray(getattr(ray, "points_2d", []), dtype=float)
        if pts.ndim != 2 or pts.shape[0] < 1 or pts.shape[1] < 2:
            return False
        pts = pts[np.all(np.isfinite(pts[:, :2]), axis=1)]
        if pts.shape[0] < 1:
            return False
        artists: list = []
        if pts.shape[0] == 1:
            artists.append(
                self.ax.scatter(
                    pts[:, 0],
                    pts[:, 1],
                    s=58,
                    c="#f97316",
                    edgecolors="white",
                    linewidths=1.4,
                    zorder=982,
                )
            )
        else:
            underlay, = self.ax.plot(
                pts[:, 0],
                pts[:, 1],
                color="white",
                linewidth=6.0,
                alpha=0.94,
                zorder=980,
            )
            overlay, = self.ax.plot(
                pts[:, 0],
                pts[:, 1],
                color="#f97316",
                linewidth=2.8,
                alpha=1.0,
                zorder=981,
            )
            artists.extend([underlay, overlay])
        for ordinal, (label, point, event_kind) in enumerate(projected_ray_event_label_items(ray, limit=14)):
            marker_size = 42 if event_kind == "terminal" else 34
            artists.append(
                self.ax.scatter(
                    [point[0]],
                    [point[1]],
                    s=marker_size,
                    c="#f97316",
                    edgecolors="white",
                    linewidths=1.0,
                    zorder=984,
                )
            )
            offset_y = 7 if ordinal % 2 == 0 else -15
            artists.append(
                self.ax.annotate(
                    label,
                    xy=(float(point[0]), float(point[1])),
                    xytext=(8, offset_y),
                    textcoords="offset points",
                    fontsize=8,
                    color="#111827",
                    zorder=985,
                    clip_on=True,
                    bbox={
                        "boxstyle": "round,pad=0.24",
                        "facecolor": "white",
                        "edgecolor": "#f97316",
                        "linewidth": 0.8,
                        "alpha": 0.84,
                    },
                )
            )
        self._layout_selection_artists = artists
        return True

    def _update_layout_selection_overlay(self, row_index: int | None = None) -> None:
        self._clear_layout_selection_overlay()
        if self.ax is None:
            if hasattr(self, "canvas"):
                self.canvas.draw_idle()
            return
        if row_index is None:
            if self._layout_selected_ray_index is not None:
                if self._draw_layout_selected_ray_overlay(int(self._layout_selected_ray_index)):
                    self.canvas.draw_idle()
                    return
                self._layout_selected_ray_index = None
            row_index = self._current_selected_row_index()
        if row_index is None:
            if hasattr(self, "canvas"):
                self.canvas.draw_idle()
            return
        polylines = self._layout_pick_regions.get(int(row_index))
        if not polylines:
            if hasattr(self, "canvas"):
                self.canvas.draw_idle()
            return
        artists: list = []
        for polyline in polylines:
            pts = np.asarray(polyline, dtype=float)
            if pts.ndim != 2 or pts.shape[0] == 0:
                continue
            if pts.shape[0] == 1:
                artists.append(
                    self.ax.scatter(
                        pts[:, 0],
                        pts[:, 1],
                        s=55,
                        c="#f97316",
                        edgecolors="white",
                        linewidths=1.4,
                        zorder=950,
                    )
                )
                continue
            underlay, = self.ax.plot(
                pts[:, 0],
                pts[:, 1],
                color="white",
                linewidth=5.0,
                alpha=0.92,
                zorder=940,
            )
            overlay, = self.ax.plot(
                pts[:, 0],
                pts[:, 1],
                color="#f97316",
                linewidth=2.2,
                alpha=0.98,
                zorder=941,
            )
            artists.extend([underlay, overlay])
        self._layout_selection_artists = artists
        self.canvas.draw_idle()

    def _configure_plot_hover_hints(self) -> None:
        self._hover_hint_artists = {}
        self._hover_axis = None
        if hasattr(self, "canvas"):
            self.canvas.get_tk_widget().configure(cursor="")
        candidate_axes = [self.ax]
        candidate_axes.extend([axis for axis in self._analysis_axes if axis is not None])
        if self._analysis_ax is not None and self._analysis_ax not in candidate_axes:
            candidate_axes.append(self._analysis_ax)
        for axis in candidate_axes:
            if axis is None:
                continue
            highlight = Rectangle(
                (0.0, 0.0),
                1.0,
                1.0,
                transform=axis.transAxes,
                facecolor="#60a5fa",
                edgecolor="#2563eb",
                linewidth=1.0,
                alpha=0.06,
                visible=False,
                zorder=1000,
            )
            axis.add_patch(highlight)
            hint_text = (
                "Click surface to select, ray to inspect; empty area opens viewer"
                if axis is self.ax
                else "Click to open in viewer"
            )
            hint = axis.text(
                0.5,
                0.985,
                hint_text,
                transform=axis.transAxes,
                ha="center",
                va="top",
                fontsize=8,
                color="#334155",
                visible=False,
                zorder=1001,
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.65, "pad": 0.8},
            )
            self._hover_hint_artists[axis] = (highlight, hint)

    def _set_hover_hint_text(self, axis, text: str) -> None:
        artists = self._hover_hint_artists.get(axis)
        if not artists:
            return
        _highlight, hint = artists
        try:
            hint.set_text(str(text or ""))
        except Exception:
            pass

    def _set_hover_axis(self, axis) -> None:
        self._hover_axis = axis
        for current_ax, artists in self._hover_hint_artists.items():
            active = current_ax is axis
            for artist in artists:
                artist.set_visible(active)
        if hasattr(self, "canvas"):
            cursor = "hand2" if axis is not None else ""
            self.canvas.get_tk_widget().configure(cursor=cursor)
            self.canvas.draw_idle()

    @staticmethod
    def _viewer_open_command(image_path: Path) -> list[str] | None:
        preferred = os.getenv("KRAKEN_IMAGE_VIEWER", "").strip()
        if preferred:
            parts = preferred.split()
            binary = parts[0]
            if shutil.which(binary):
                return [*parts, str(image_path)]
        for binary in ("nomacs-x11", "nomacs"):
            if shutil.which(binary):
                return [binary, str(image_path)]
        if sys.platform == "darwin":
            return ["open", str(image_path)]
        if os.name == "nt":
            return None
        if shutil.which("xdg-open"):
            return ["xdg-open", str(image_path)]
        if shutil.which("gio"):
            return ["gio", "open", str(image_path)]
        for binary in ("imv", "feh", "eog", "gwenview", "ristretto", "pqiv", "sxiv", "nsxiv"):
            if shutil.which(binary):
                return [binary, str(image_path)]
        return None

    def _open_image_with_system_viewer(self, image_path: Path) -> None:
        if os.name == "nt":
            os.startfile(str(image_path))  # type: ignore[attr-defined]
            return
        command = self._viewer_open_command(image_path)
        if command is None:
            raise RuntimeError("No system image viewer command found.")
        subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)

    def _high_res_export_kept_axes(self, target_ax) -> set:
        """Axes to keep visible when exporting ``target_ax`` to a high-res image.

        Besides the clicked axis this includes any twin axes that share an axis
        with it (a ``twinx``/``twiny`` overlay), so a secondary-axis series such
        as the distortion twin on a field-curvature plot is exported alongside
        the primary axis instead of being hidden away.
        """
        kept = {target_ax}
        for shared in (target_ax.get_shared_x_axes(), target_ax.get_shared_y_axes()):
            try:
                kept.update(shared.get_siblings(target_ax))
            except Exception:
                pass
        return {axis for axis in kept if axis in self.figure.axes}

    def _open_high_res_plot_in_system_viewer(self, target_ax=None) -> None:
        previous_hover_axis = self._hover_axis if self._hover_axis in self._hover_hint_artists else None
        hidden_axes: list[tuple[object, bool]] = []
        try:
            # Hide hover hint overlays so exported images only contain plot content.
            self._set_hover_axis(None)
            out_dir = SCREENSHOT_DIR
            try:
                out_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                out_dir = VIEWER_EXPORT_DIR
                out_dir.mkdir(parents=True, exist_ok=True)
            if target_ax is self.ax:
                axis_label = "layout"
            elif target_ax in self._analysis_axes:
                axis_index = self._analysis_axes.index(target_ax) + 1
                axis_label = f"analysis{axis_index}"
            else:
                axis_label = "analysis"
            image_path = out_dir / ("2D.png" if axis_label == "layout" else f"kraken_plot_{axis_label}.png")

            self.canvas.draw()
            if target_ax is not None and target_ax in self.figure.axes:
                renderer = self.figure.canvas.get_renderer()
                # Keep twin axes (those sharing an axis with the clicked one) visible
                # so a secondary-axis series -- e.g. the distortion twin on a
                # field-curvature plot -- is not hidden out of the export.
                kept_axes = self._high_res_export_kept_axes(target_ax)
                tight_boxes = [
                    box for box in (axis.get_tightbbox(renderer) for axis in kept_axes)
                    if box is not None
                ]
                tight_bbox = Bbox.union(tight_boxes) if tight_boxes else None
                if tight_bbox is not None:
                    # savefig expects bbox_inches in inches, convert from display pixels
                    bbox = tight_bbox.transformed(self.figure.dpi_scale_trans.inverted()).padded(0.08)
                else:
                    fig_w, fig_h = self.figure.get_size_inches()
                    pos = target_ax.get_position()
                    bbox = Bbox.from_extents(
                        float(pos.x0) * fig_w,
                        float(pos.y0) * fig_h,
                        float(pos.x1) * fig_w,
                        float(pos.y1) * fig_h,
                    ).expanded(1.08, 1.12)
                for axis in self.figure.axes:
                    if axis in kept_axes:
                        continue
                    hidden_axes.append((axis, bool(axis.get_visible())))
                    axis.set_visible(False)
                self.figure.savefig(image_path, dpi=320, bbox_inches=bbox)
            else:
                self.figure.savefig(image_path, dpi=320)

            self._open_image_with_system_viewer(image_path)
            self.status_var.set(f"Opened image in system viewer: {image_path.name}")
            self.append_progress(f"Opened high-res image: {image_path}")
        except Exception as exc:
            self.append_debug(f"High-resolution viewer launch failed: {exc}")
        finally:
            if hidden_axes:
                for axis, visible in hidden_axes:
                    try:
                        axis.set_visible(visible)
                    except Exception:
                        pass
                try:
                    self.canvas.draw_idle()
                except Exception:
                    pass
            if previous_hover_axis is not None:
                self._set_hover_axis(previous_hover_axis)
