"""2D layout plot refresh orchestration service."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from typing import Any
import io
import traceback
import warnings

import KrakenOS as Kos

from KrakenOS.UI.layout_plot_controller import (
    active_plot_modes,
    max_surface_radius,
    plot_status_label,
    project_scene_bundle,
    projected_pick_state,
    trace_mode_summary_from_bundle,
)
from KrakenOS.UI.scene_projector import auxiliary_projection_planes, projection_axis_labels
from KrakenOS.UI.scene_renderer_2d import render_scene_2d, set_plot_limits


def _layout_module():
    from KrakenOS.UI import layout_editor as layout_editor_module

    return layout_editor_module


class PlotRefreshService:
    """Refresh the 2D layout, auxiliary projections, analysis axes, and reports."""

    def __init__(self, editor: Any) -> None:
        object.__setattr__(self, "editor", editor)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "editor":
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def refresh_plot(self, *, suppress_analysis: bool = False, sampling_mode: str | None = None) -> None:
        le = _layout_module()
        NonSequentialTracePreviewError = le.NonSequentialTracePreviewError
        _short_error_message = le._short_error_message
        active_modes = active_plot_modes(self.selected_analysis_modes, suppress_analysis=suppress_analysis)
        status_label = plot_status_label(active_modes, self.layout_preview_mode or "none")
        self._set_analysis_parallel_status(status_label, 1, False)
        self._begin_analysis_progress("Plot refresh")
        self.update_idletasks()
        self._clear_cardinal_marker_artists()
        self._clear_physical_distance_artists()
        self._clear_layout_selection_overlay()
        self._layout_pick_regions = {}
        self._layout_ray_pick_regions = []
        self._layout_projected_rays_by_index = {}
        self._last_optics_info = None
        self._last_sequential_focus_diagnostic = {}
        self._analysis_ax = None
        self._analysis_axes = []
        self._layout_projection_axes = {}
        if not self.rows:
            self.last_system = None
            self.last_rays = None
            self._last_scene_bundle = None
            self._last_auto_leg_entries = []
            self.ax.clear()
            self.ax.set_title("Axial Layout")
            self._refresh_ray_inspector_if_open()
            self._refresh_branch_gaussian_q_report_if_open()
            self._refresh_branch_tree_if_open()
            self._refresh_branch_throughput_report_if_open()
            self._refresh_detector_aperture_report_if_open()
            self._refresh_source_illumination_report_if_open()
            self._refresh_analysis_branch_choices()
            self._refresh_nonseq_scene_graph_if_open()
            self._sync_trace_state_badge({"requested": self._requested_trace_mode(), "active": "Sequential"})
            self._configure_plot_hover_hints()
            self.canvas.draw_idle()
            self._autosave_plot()
            self._finish_analysis_progress("Plot refresh", success=True)
            return

        max_radius = max_surface_radius(self.rows)

        self._update_analysis_progress("Building system", 1, 5)
        self.update_idletasks()
        self.figure.clear()
        # Plane selection drives which layout panes show: a single plane shows
        # only that pane; "All" shows the YZ main pane plus the two auxiliary
        # planes. The "2D" toggle hides the layout entirely, handing the canvas
        # to the analysis column (or a hint when nothing is selected).
        show_layout = self._show_layout_2d()
        selection = self._display_plane_selection()
        if show_layout and selection == "All":
            aux_planes = auxiliary_projection_planes("YZ")
        else:
            aux_planes = ()
        right_rows = len(active_modes)

        def _build_layout_axes(host) -> None:
            if aux_planes:
                if host is None:
                    sub = self.figure.add_gridspec(
                        len(aux_planes), 2,
                        width_ratios=[3.1, 1.1],
                        height_ratios=[1.0] * len(aux_planes),
                        wspace=0.22, hspace=0.30,
                    )
                else:
                    sub = host.subgridspec(
                        len(aux_planes), 2,
                        width_ratios=[3.1, 1.1],
                        height_ratios=[1.0] * len(aux_planes),
                        wspace=0.22, hspace=0.30,
                    )
                self.ax = self.figure.add_subplot(sub[:, 0])
                self._layout_projection_axes = {
                    plane: self.figure.add_subplot(sub[index, 1])
                    for index, plane in enumerate(aux_planes)
                }
            else:
                self.ax = (
                    self.figure.add_subplot(1, 1, 1)
                    if host is None
                    else self.figure.add_subplot(host)
                )
                self._layout_projection_axes = {}

        def _hidden_layout_axis():
            # Off-canvas, invisible main axis: the layout-draw pipeline still has
            # a valid Axes to draw into, but it neither shows nor steals space.
            ax = self.figure.add_axes([-0.2, -0.2, 0.05, 0.05])
            ax.set_visible(False)
            self._layout_projection_axes = {}
            return ax

        if show_layout and right_rows == 0:
            _build_layout_axes(None)
            self._analysis_axes = []
            self._analysis_ax = None
        elif show_layout and right_rows > 0:
            gs = self.figure.add_gridspec(1, 2, width_ratios=[3.9, 1.75], wspace=0.18)
            _build_layout_axes(gs[0])
            right_gs = gs[1].subgridspec(right_rows, 1, hspace=0.28)
            self._analysis_axes = [self.figure.add_subplot(right_gs[i, 0]) for i in range(right_rows)]
            self._analysis_ax = self._analysis_axes[0]
        elif right_rows > 0:
            # 2D layout hidden: hand the whole canvas to the analysis plots. A
            # single column wastes the freed width — each plot's fixed box-aspect
            # shrinks and centres it — so tile them into a near-square grid.
            columns = 1
            while columns * columns < right_rows:
                columns += 1
            grid_rows = (right_rows + columns - 1) // columns
            grid = self.figure.add_gridspec(grid_rows, columns, hspace=0.32, wspace=0.22)
            self._analysis_axes = [
                self.figure.add_subplot(grid[i // columns, i % columns])
                for i in range(right_rows)
            ]
            self._analysis_ax = self._analysis_axes[0]
            self.ax = _hidden_layout_axis()
        else:
            self.ax = _hidden_layout_axis()
            self._analysis_axes = []
            self._analysis_ax = None
            self.figure.text(
                0.5, 0.5,
                "2D layout hidden.\nEnable “2D” or tick an Analysis plot to display.",
                ha="center", va="center", fontsize=11, color="0.45",
            )

        title_bundle = None
        try:
            wavelength = self._current_wavelength()
            scene_sampling_mode = self._preview_scene_sampling_mode()
            preview_sampling_mode = str(sampling_mode or "").strip() or self._preview_2d_sampling_mode()
            if preview_sampling_mode == "display_slice":
                preview_sampling_mode = scene_sampling_mode
            capture = io.StringIO()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                with redirect_stdout(capture), redirect_stderr(capture):
                    system = self.build_system(require_solids=True)
                    # bugs/0201 (#6): route the 2D preview through the same folded-aware
                    # trace the 3D view uses. A direct mesh non-seq trace of the folded
                    # RA-mirror scene retroreflects the ideal Thin Lenses (0 rays), so the
                    # 2D view showed no ray tracing at all; the straight-equivalent /
                    # sequential-Mirror trace reaches the sensor and is bent onto the drawn
                    # detector after the bundle is built.
                    folded_trace_rows = self._folded_sequential_trace_rows(self.rows)
                    rays, straight_equivalent_fold_transform = (
                        self._trace_preview_rays_folded_aware(
                            system,
                            wavelength,
                            max_radius,
                            sampling_mode=preview_sampling_mode,
                            folded_trace_rows=folded_trace_rows,
                        )
                    )
            self.append_debug(capture.getvalue())
            self._update_analysis_progress("Tracing rays", 2, 5)
            self.update_idletasks()
            self.last_system = system
            self.last_rays = rays
            self._last_preview_trace_signature = self._preview_trace_signature()
            self._last_scene_trace_sampling_mode = preview_sampling_mode
            self._preview_scene_trace_dirty = False
            if self._apply_image_diameter_mode():
                self._sync_image_row_table_value()

            # --- Phase 3: scene-bundle pipeline ---
            self._update_analysis_progress("Rendering layout", 3, 5)
            self.update_idletasks()
            orientation = self._current_display_orientation()
            bundle = self._build_scene_bundle(system, rays, max_radius)
            if folded_trace_rows is not None:
                self._apply_folded_display_bend(bundle, straight_equivalent_fold_transform)
                # bugs/0227 (attachment/2D.png "rays defocus at the detector"): the 3D
                # pipeline follows the display bend with the bugs/0217 reconcile -- the
                # detector target + the on-axis ray hard-stops snap onto the cone's real
                # waist when the trailing fold mirror overshoots the prescription Image
                # row. The 2D layout stopped at the bend, so it drew the rays running a
                # plate PAST their focus to the overshot sensor line while the 3D showed
                # them sharp ON the detector. Mirror the 3D pipeline exactly.
                if straight_equivalent_fold_transform is not None:
                    self._reconcile_folded_image_to_ray_convergence(bundle)
            title_bundle = bundle
            self._last_scene_bundle = bundle
            self._refresh_3d_inspector_if_open(system=system, rays=rays, scene_bundle=bundle)
            self._refresh_arm_view_choices()
            self._refresh_analysis_branch_choices()
            trace_summary = trace_mode_summary_from_bundle(bundle)
            self._sync_trace_state_badge(trace_summary)
            self.append_progress(f"Trace mode: {trace_summary['requested']} -> {trace_summary['active']}")
            if trace_summary["note"]:
                self.append_debug(f"Trace mode note: {trace_summary['note']}")
            projected = project_scene_bundle(
                bundle,
                orientation,
                filter_projection_axis_fields=self._should_filter_projection_axis_fields(bundle),
                filter_projection_slice=self._should_filter_projection_slice(bundle),
                refresh_auto_leg_graph=self._refresh_auto_leg_graph,
                refresh_arm_view_choices=self._refresh_arm_view_choices,
                filter_arm_view=self._filter_projected_scene_for_arm_view,
                filter_ray_display=self._filter_projected_scene_for_ray_display,
            )

            # Pick regions from the projected scene avoid a redundant scene rebuild.
            self._layout_pick_regions, self._layout_ray_pick_regions = projected_pick_state(projected)
            self._layout_projected_rays_by_index = {
                int(getattr(ray, "ray_index", index)): ray
                for index, ray in enumerate(list(getattr(projected, "rays", []) or []))
            }

            # Render surfaces, rays, and labels
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                render_projected = self._projected_scene_for_layout_render(projected)
                render_scene_2d(
                    render_projected, self.ax,
                    show_clipped_rays=self.show_clipped_rays_var.get(),
                    show_labels=self._current_show_path_labels(),
                    ray_count_hint=max(1, self._preview_field_ray_count),
                )
                self._render_auxiliary_projection_axes(bundle, max_radius)

            self._draw_lens_mech_overlay()
            gaussian_extent = self._draw_gaussian_beam_overlay(system, wavelength)
            if gaussian_extent is not None:
                max_radius = max(max_radius, float(gaussian_extent))
            scan_bounds = self._draw_folded_scan_overlay(max_radius, system=system)
            tolerance_bounds = self._draw_pose_tolerance_overlay(max_radius, wavelength=wavelength)
            plot_bounds = self._combined_plot_bounds(projected.bounds, scan_bounds, tolerance_bounds)
            set_plot_limits(
                self.ax, plot_bounds,
                max_radius=max_radius,
                has_off_axis=bundle.has_off_axis,
                orientation=orientation,
                use_drawn_data=orientation in {"XZ", "XY"} or not scan_bounds.is_empty or not tolerance_bounds.is_empty,
            )
            self._draw_arm_labels(projected)

            # Cardinal markers and result-panel summaries are optional
            # diagnostics. They must not force an already-rendered layout into
            # fallback when paraxial/pupil data is unavailable for branched
            # non-sequential systems.
            self._update_analysis_progress("Computing cardinals", 4, 5)
            self.update_idletasks()
            optics_info: dict = {}
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", RuntimeWarning)
                    optics_info = self._collect_optics_info(system, rays, wavelength)
                self._last_optics_info = dict(optics_info)
            except Exception as diag_exc:
                self._last_optics_info = None
                self.append_debug(f"Optics summary unavailable: {diag_exc}")
            try:
                if self._last_optics_info is not None:
                    self._draw_optics_markers(optics_info)
            except Exception as diag_exc:
                self.append_debug(f"Optics marker draw skipped: {diag_exc}")
            try:
                self._draw_physical_distances()
            except Exception as diag_exc:
                self.append_debug(f"Physical-distance overlay skipped: {diag_exc}")
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                if self._analysis_axes:
                    for axis, mode in zip(self._analysis_axes, active_modes):
                        try:
                            self._plot_analysis_for_mode(axis, system, rays, wavelength, mode)
                        except Exception as diag_exc:
                            axis.clear()
                            axis.text(0.5, 0.5, "Analysis unavailable", ha="center", va="center")
                            axis.set_axis_off()
                            self.append_debug(f"{mode} analysis skipped: {diag_exc}")
                else:
                    self._analysis_ax = None
                try:
                    self._update_results(system, rays, wavelength, optics_info)
                except Exception as diag_exc:
                    self._set_results([("Status", "Layout rendered"), ("Results warning", str(diag_exc))])
                    self.append_debug(f"Results panel skipped: {diag_exc}")
                for label, refresh_fn in (
                    ("Ray inspector", self._refresh_ray_inspector_if_open),
                    ("Branch Gaussian q", self._refresh_branch_gaussian_q_report_if_open),
                    ("Trace path inspector", self._refresh_branch_tree_if_open),
                    ("Path throughput", self._refresh_branch_throughput_report_if_open),
                    ("Detector aperture", self._refresh_detector_aperture_report_if_open),
                    ("Source illumination", self._refresh_source_illumination_report_if_open),
                    ("Non-sequential scene graph", self._refresh_nonseq_scene_graph_if_open),
                ):
                    try:
                        refresh_fn()
                    except Exception as diag_exc:
                        self.append_debug(f"{label} refresh skipped: {diag_exc}")
            self._update_analysis_progress("Finalizing", 5, 5)
            self.update_idletasks()
            focus_diag = dict(self.editor.__dict__.get("_last_sequential_focus_diagnostic", {}) or {})
            focus_suffix = " | focus warning" if bool(focus_diag.get("warning")) else ""
            try:
                field_overlap = bool(self._field_launch_sample_summary().get("overlap"))
            except Exception:
                field_overlap = False
            field_suffix = " | field samples overlap" if field_overlap else ""
            detector_suffix = self._detector_aperture_status_suffix()
            self.status_var.set(f"Plot refreshed | {self._last_analysis_label} | {self._analysis_compute_summary()}{focus_suffix}{field_suffix}{detector_suffix}")
        except Exception as exc:
            self.last_system = None
            self.last_rays = None
            self._last_scene_bundle = None
            self.ax.clear()
            nonseq_trace_failed = isinstance(exc, NonSequentialTracePreviewError)
            if nonseq_trace_failed:
                self._plot_trace_failure_diagnostic(exc)
            else:
                self._plot_fallback_preview(max_radius)
            for axis in self._analysis_axes:
                axis.clear()
                axis.text(0.5, 0.5, "Analysis unavailable", ha="center", va="center")
                axis.set_axis_off()
            if nonseq_trace_failed:
                self._set_results([
                    ("Status", "Non-sequential trace failed"),
                    ("Error", str(exc)),
                    ("Fallback", "Sequential fallback suppressed"),
                ])
            else:
                self._set_results([("Status", "Unavailable"), ("Error", str(exc))])
            self._refresh_ray_inspector_if_open()
            self._refresh_branch_gaussian_q_report_if_open()
            self._refresh_branch_tree_if_open()
            self._refresh_branch_throughput_report_if_open()
            self._refresh_detector_aperture_report_if_open()
            self._refresh_source_illumination_report_if_open()
            self._refresh_analysis_branch_choices()
            self._refresh_nonseq_scene_graph_if_open()
            if nonseq_trace_failed:
                self.status_var.set(f"Non-sequential trace failed: {_short_error_message(exc)}")
            else:
                self.status_var.set(f"Plot refreshed with fallback preview: {exc}")
            self.append_debug(f"Plot refresh error: {exc}")
            self.append_debug(traceback.format_exc())

        self.ax.grid(True, alpha=0.2)
        x_label, y_label, _title = projection_axis_labels(self._current_display_orientation())
        self.ax.set_xlabel(x_label)
        self.ax.set_ylabel(y_label)
        self.ax.set_title(
            self._projection_display_title(
                self._current_display_orientation(),
                title_bundle,
            ),
            fontsize=10,
        )
        self.figure.subplots_adjust(left=0.07, right=0.98, bottom=0.15, top=0.92, wspace=0.28)
        self.figure.text(0.5, 0.035, "KrakenOS Layout", ha="center", va="center")
        self._sync_object_controls()
        self._configure_plot_hover_hints()
        self._update_layout_selection_overlay()
        self.canvas.draw_idle()
        self._autosave_plot()
        self._finish_analysis_progress("Plot refresh", success=True)
        if self._initial_layout_passes < 40:
            self.after(50, self._set_initial_pane_layout)
