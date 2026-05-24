"""Results panel and 2D physical-distance overlay service."""

from __future__ import annotations

from typing import Any

import numpy as np


class ResultsDisplayService:
    """Own result-panel rows and 2D physical-distance overlay drawing."""

    def __init__(self, editor: Any) -> None:
        object.__setattr__(self, "editor", editor)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "editor":
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def _clear_physical_distance_artists(self) -> None:
        for artist in self._physical_distance_artists:
            try:
                artist.remove()
            except Exception:
                pass
        self._physical_distance_artists.clear()

    def _on_toggle_physical_distances(self) -> None:
        self._clear_physical_distance_artists()
        if not self.show_physical_distances_var.get():
            self.canvas.draw_idle()
            self.status_var.set("Physical distances hidden")
            return
        self._draw_physical_distances()
        self.canvas.draw_idle()
        self.status_var.set("Physical distances updated")
        self._autosave_plot()

    def _draw_physical_distances(self) -> None:
        self._clear_physical_distance_artists()
        if not self.show_physical_distances_var.get():
            return
        if not self.rows or len(self.rows) < 3:
            return

        # Find the housing datum surfaces by name (the mechanical barrel edges).
        # These are flat reference planes — not the optical element edges.
        z_positions: list[float] = [0.0]
        z = 0.0
        for row in self.rows[:-1]:
            z += float(row.thickness)
            z_positions.append(z)
        if len(z_positions) < len(self.rows):
            z_positions.append(z)

        housing_front_z: float | None = None
        housing_rear_z: float | None = None
        for i, row in enumerate(self.rows):
            name_lower = row.name.lower()
            if housing_front_z is None and "front" in name_lower and "datum" in name_lower:
                housing_front_z = z_positions[i]
            if housing_rear_z is None and "rear" in name_lower and "datum" in name_lower:
                housing_rear_z = z_positions[i]

        # Fallback: use first/last optical surface edge if no datum surfaces
        if housing_front_z is None:
            for i, row in enumerate(self.rows):
                if row.surface not in {"Object", "Image", "Aperture"}:
                    housing_front_z = z_positions[i]
                    break
        if housing_front_z is None:
            return

        object_z = 0.0
        image_z = self._current_image_plane_z()
        camera_front_z = image_z - self._current_camera_front_to_sensor_mm()

        # Get plot bounds for positioning the arrows
        x0, x1 = self.ax.get_xlim()
        y0, y1 = self.ax.get_ylim()
        span_y = abs(y1 - y0)
        span_x = abs(x1 - x0)

        orientation = self._current_display_orientation()
        color_obj = "#2196f3"   # blue for object-to-front
        color_cam = "#4caf50"   # green for front-to-camera
        color_edge = "#ff5722"  # orange-red for camera edge marker
        color_led = "#f59e0b"   # amber for object-to-LED edge

        dist1 = abs(housing_front_z - object_z)
        dist2 = abs(camera_front_z - housing_front_z)
        led_edge_z: float | None = None
        led_dist = 0.0
        if self.imported_led_step_path is not None:
            try:
                led_dist = max(float(getattr(self, "led_object_edge_distance_mm", 0.0)), 0.0)
                led_edge_z = object_z + led_dist if led_dist > 1e-9 else None
            except Exception:
                led_edge_z = None

        if orientation == "Horizontal":
            _, obj_proj = self._project_xy([object_z], [0.0])
            _, front_proj = self._project_xy([housing_front_z], [0.0])
            _, cam_proj = self._project_xy([camera_front_z], [0.0])

            obj_y = float(obj_proj[0])
            front_y = float(front_proj[0])
            cam_y = float(cam_proj[0])

            # Both arrows at the same x offset (side by side)
            arrow_x = x0 + 0.08 * span_x

            # Object to Front Datum
            ann1 = self.ax.annotate(
                "", xy=(arrow_x, front_y), xytext=(arrow_x, obj_y),
                arrowprops=dict(arrowstyle="<->", color=color_obj, lw=1.8, shrinkA=0, shrinkB=0),
                zorder=72.0,
            )
            txt1 = self.ax.text(
                arrow_x + 0.01 * span_x, (obj_y + front_y) / 2.0,
                f"{dist1:.1f} mm",
                color=color_obj, fontsize=8, ha="left", va="center", zorder=73.0,
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.7, "pad": 0.6},
            )
            self._physical_distance_artists.extend((ann1, txt1))

            # Front Datum to Camera Front
            ann2 = self.ax.annotate(
                "", xy=(arrow_x, cam_y), xytext=(arrow_x, front_y),
                arrowprops=dict(arrowstyle="<->", color=color_cam, lw=1.8, shrinkA=0, shrinkB=0),
                zorder=72.0,
            )
            txt2 = self.ax.text(
                arrow_x + 0.01 * span_x, (front_y + cam_y) / 2.0,
                f"{dist2:.1f} mm",
                color=color_cam, fontsize=8, ha="left", va="center", zorder=73.0,
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.7, "pad": 0.6},
            )
            self._physical_distance_artists.extend((ann2, txt2))

            # Camera edge indicator line
            cam_line = self.ax.axhline(cam_y, color=color_edge, linewidth=1.2, linestyle="--", alpha=0.9, zorder=70.0)
            cam_label = self.ax.text(
                x0 + 0.04 * span_x, cam_y,
                "Camera Edge",
                color=color_edge, fontsize=8, ha="left", va="bottom", zorder=71.0,
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.65, "pad": 0.6},
            )
            self._physical_distance_artists.extend((cam_line, cam_label))

            if led_edge_z is not None:
                _, led_proj = self._project_xy([led_edge_z], [0.0])
                led_y = float(led_proj[0])
                led_arrow_x = x0 + 0.16 * span_x
                ann_led = self.ax.annotate(
                    "", xy=(led_arrow_x, led_y), xytext=(led_arrow_x, obj_y),
                    arrowprops=dict(arrowstyle="<->", color=color_led, lw=1.8, shrinkA=0, shrinkB=0),
                    zorder=74.0,
                )
                txt_led = self.ax.text(
                    led_arrow_x + 0.01 * span_x, (obj_y + led_y) / 2.0,
                    f"LED {led_dist:.1f} mm",
                    color=color_led, fontsize=8, ha="left", va="center", zorder=75.0,
                    bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.72, "pad": 0.6},
                )
                led_line = self.ax.axhline(led_y, color=color_led, linewidth=1.2, linestyle="--", alpha=0.9, zorder=70.0)
                led_label = self.ax.text(
                    x0 + 0.04 * span_x, led_y,
                    "LED Edge",
                    color=color_led, fontsize=8, ha="left", va="top", zorder=71.0,
                    bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.65, "pad": 0.6},
                )
                self._physical_distance_artists.extend((ann_led, txt_led, led_line, led_label))
        else:
            # Vertical orientation: z is the x-axis, y is transverse
            # Both arrows at the same y offset (side by side)
            arrow_y = y0 + 0.08 * span_y
            led_arrow_y = y0 + 0.16 * span_y

            # Object to Lens Front Edge
            ann1 = self.ax.annotate(
                "", xy=(housing_front_z, arrow_y), xytext=(object_z, arrow_y),
                arrowprops=dict(arrowstyle="<->", color=color_obj, lw=1.8, shrinkA=0, shrinkB=0),
                zorder=72.0,
            )
            txt1 = self.ax.text(
                (object_z + housing_front_z) / 2.0, arrow_y + 0.01 * span_y,
                f"{dist1:.1f} mm",
                color=color_obj, fontsize=8, ha="center", va="bottom", zorder=73.0,
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.7, "pad": 0.6},
            )
            self._physical_distance_artists.extend((ann1, txt1))

            # Lens Front Edge to Camera Front
            ann2 = self.ax.annotate(
                "", xy=(camera_front_z, arrow_y), xytext=(housing_front_z, arrow_y),
                arrowprops=dict(arrowstyle="<->", color=color_cam, lw=1.8, shrinkA=0, shrinkB=0),
                zorder=72.0,
            )
            txt2 = self.ax.text(
                (housing_front_z + camera_front_z) / 2.0, arrow_y + 0.01 * span_y,
                f"{dist2:.1f} mm",
                color=color_cam, fontsize=8, ha="center", va="bottom", zorder=73.0,
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.7, "pad": 0.6},
            )
            self._physical_distance_artists.extend((ann2, txt2))

            # Camera edge indicator line
            cam_line = self.ax.axvline(camera_front_z, color=color_edge, linewidth=1.2, linestyle="--", alpha=0.9, zorder=70.0)
            cam_label = self.ax.text(
                camera_front_z, y1 - 0.05 * span_y,
                "Camera Edge",
                color=color_edge, fontsize=8, ha="center", va="top", zorder=71.0,
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.65, "pad": 0.6},
            )
            self._physical_distance_artists.extend((cam_line, cam_label))

            if led_edge_z is not None:
                ann_led = self.ax.annotate(
                    "", xy=(led_edge_z, led_arrow_y), xytext=(object_z, led_arrow_y),
                    arrowprops=dict(arrowstyle="<->", color=color_led, lw=1.8, shrinkA=0, shrinkB=0),
                    zorder=74.0,
                )
                txt_led = self.ax.text(
                    (object_z + led_edge_z) / 2.0, led_arrow_y + 0.01 * span_y,
                    f"LED {led_dist:.1f} mm",
                    color=color_led, fontsize=8, ha="center", va="bottom", zorder=75.0,
                    bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.72, "pad": 0.6},
                )
                led_line = self.ax.axvline(led_edge_z, color=color_led, linewidth=1.2, linestyle="--", alpha=0.9, zorder=70.0)
                led_label = self.ax.text(
                    led_edge_z, y1 - 0.11 * span_y,
                    "LED Edge",
                    color=color_led, fontsize=8, ha="center", va="top", zorder=71.0,
                    bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.65, "pad": 0.6},
                )
                self._physical_distance_artists.extend((ann_led, txt_led, led_line, led_label))

    def _update_results(self, system, rays, wavelength: float, optics_info: dict | None = None) -> None:
        if optics_info is None:
            optics_info = self._collect_optics_info(system, rays, wavelength)
        items = []
        items.append(("Surface count", str(len(self.rows))))
        items.append(("Optimized vars", str(len(self._build_optimization_variables()))))
        items.append(("Object mode", self._current_object_mode()))
        items.append(("Wavelength [um]", f"{wavelength:.4g}"))
        items.append(("Analysis mode", self._last_analysis_label))
        items.append(("Analysis workers", self._analysis_compute_summary()))
        items.append(("Analysis surface", str(self._analysis_surface_index())))
        aperture_type_label = self._current_aperture_type_label()
        try:
            raw_aperture_value = float(self.aperture_value_var.get())
        except Exception:
            raw_aperture_value = self._current_aperture_value()
        items.append(("Aperture type", aperture_type_label))
        items.append(("Aperture value", f"{raw_aperture_value:.4g}" if aperture_type_label == "FNO" else f"{self._current_aperture_value():.4g}"))
        if aperture_type_label == "FNO":
            items.append(("Equivalent EPD [mm]", f"{self._current_aperture_value():.4g}"))
        field_metrics = self._field_metrics_summary()
        items.append(("Field type", self._field_type_display_label(self._current_field_type())))
        items.append(("Field half-angle [deg]", f"{field_metrics['current_angle_deg']:.4g}"))
        items.append(("Object semi-ht [mm]", f"{field_metrics['current_object_height']:.4g}"))
        items.append(("Paraxial img semi-ht [mm]", f"{field_metrics['current_paraxial_image_height']:.4g}"))
        items.append(("Real img semi-ht [mm]", f"{field_metrics['current_real_image_height']:.4g}"))
        field_launch_summary = self._field_launch_sample_summary()
        if int(field_launch_summary["requested"]) > 1:
            items.append((
                "Effective field samples",
                f"{int(field_launch_summary['effective'])} / {int(field_launch_summary['requested'])}",
            ))
            items.append((
                f"Field sample span [{field_launch_summary['unit']}]",
                f"{float(field_launch_summary['min']):.4g} .. {float(field_launch_summary['max']):.4g}",
            ))
            items.append(("Max parax img semi-ht [mm]", f"{field_metrics['max_paraxial_image_height']:.4g}"))
            items.append(("Max real img semi-ht [mm]", f"{field_metrics['max_real_image_height']:.4g}"))
            items.append(("Required image dia [mm]", f"{field_metrics['image_diameter']:.4g}"))
        if self.rows and self.rows[-1].surface == "Image":
            items.append(("Image row diameter [mm]", f"{float(self.rows[-1].diameter):.4g}"))

        camera_info = self._current_camera_record()
        if camera_info is not None:
            items.append(("Camera", ""))
            items.append(("Camera model", str(camera_info.get("model", self._current_camera_model()))))
            width = float(camera_info.get("sensor_width_mm", 0.0))
            height = float(camera_info.get("sensor_height_mm", 0.0))
            if width > 0.0 and height > 0.0:
                items.append(("Sensor active [mm]", f"{width:.4g} x {height:.4g}"))
            diagonal = camera_info.get("sensor_diagonal_mm")
            if diagonal is not None:
                items.append(("Sensor diagonal [mm]", f"{float(diagonal):.4g}"))
            resolution = camera_info.get("resolution_px")
            if isinstance(resolution, tuple) and len(resolution) == 2:
                items.append(("Resolution [px]", f"{int(resolution[0])} x {int(resolution[1])}"))
            pixel_size = camera_info.get("pixel_size_um")
            if isinstance(pixel_size, tuple) and len(pixel_size) == 2:
                items.append(("Pixel size [um]", f"{float(pixel_size[0]):.4g} x {float(pixel_size[1]):.4g}"))
            register = camera_info.get("camera_front_to_sensor_mm")
            if register is not None:
                items.append(("Camera front-sensor [mm]", f"{float(register):.4g}"))
            mount = camera_info.get("lens_mount")
            if mount:
                items.append(("Camera mount", str(mount)))

        total_length = sum(max(float(row.thickness), 0.0) for row in self.rows)
        items.append(("Total length [mm]", f"{total_length:.4g}"))

        trace_summary = self._trace_preview_summary(rays, self._last_scene_bundle)
        items.append(("Trace", ""))
        items.append(("Trace requested", str(trace_summary["requested"])))
        items.append(("Trace active", str(trace_summary["active"])))
        items.append(("Trace family", str(trace_summary["family"])))
        items.append(("Trace backend", str(trace_summary["backend"])))
        items.append(("Preview rays", str(trace_summary["total_rays"])))
        items.append(("Image hits", f"{trace_summary['image_hits']} / {trace_summary['total_rays']}"))
        items.append(("Stopped rays", str(trace_summary["stopped_rays"])))
        trace_note = str(trace_summary.get("note", "")).strip()
        if trace_note:
            items.append(("Trace note", trace_note))
        sampling_diagnostics = self._source_sampling_diagnostics(trace_summary)
        if sampling_diagnostics:
            items.append(("Source sampling", ""))
            items.extend(sampling_diagnostics)
        detector_aperture_records = self._collect_detector_aperture_records(ray_records=self._active_ray_analysis_records())
        self._detector_aperture_records = detector_aperture_records
        detector_counts = self._detector_aperture_counts(detector_aperture_records)
        if int(detector_counts.get("detectors", 0) or 0) > 0:
            detector_rays = int(detector_counts.get("rays", 0) or 0)
            detector_hits = int(detector_counts.get("hits", 0) or 0)
            detector_misses = int(detector_counts.get("misses", 0) or 0)
            detector_other = int(detector_counts.get("other", 0) or 0)
            hit_fraction = detector_hits / detector_rays if detector_rays > 0 else np.nan
            items.append(("Detector aperture", ""))
            items.append(("Detector surfaces", str(int(detector_counts["detectors"]))))
            items.append(("Detector rays", str(detector_rays)))
            items.append(("Detector hits", f"{detector_hits} / {detector_rays} ({self._format_percent_value(hit_fraction)})"))
            items.append(("Detector misses", str(detector_misses)))
            items.append(("Detector other terminals", str(detector_other)))
            items.append(("Detector hit power", self._format_ray_inspector_value(detector_counts.get("hit_power"))))
            items.append(("Detector miss power", self._format_ray_inspector_value(detector_counts.get("miss_power"))))
            if detector_counts.get("worst_margin") is not None:
                items.append(("Worst detector miss [mm]", f"{float(detector_counts['worst_margin']):.4g}"))
                worst_ray = str(detector_counts.get("worst_ray", "") or "").strip()
                worst_detector = str(detector_counts.get("worst_detector", "") or "").strip()
                if worst_ray or worst_detector:
                    items.append(("Worst detector miss ray", f"{worst_ray} {worst_detector}".strip()))
        focus_diag = self._sequential_focus_diagnostic(rays, trace_summary)
        self._last_sequential_focus_diagnostic = dict(focus_diag)
        if focus_diag:
            items.append(("Sequential focus", ""))
            items.append(("Best focus z [mm]", f"{float(focus_diag['best_focus_z']):.4g}"))
            items.append(("Focus offset [mm]", f"{float(focus_diag['focus_shift']):+.4g}"))
            items.append(("Image RMS [mm]", f"{float(focus_diag['image_rms']):.4g}"))
            items.append(("Best-focus RMS [mm]", f"{float(focus_diag['best_focus_rms']):.4g}"))
            focus_note = str(focus_diag.get("diagnostic", "") or "").strip()
            if focus_note:
                items.append(("Focus diagnostic", focus_note))
                self.append_debug(f"Sequential focus diagnostic: {focus_note}")

        pol_summary = self._polarization_summary(rays)
        items.append(("Coating / polarization", ""))
        items.append(("Coating attr surfaces", str(pol_summary["coated_surface_count"])))
        items.append(("Mean throughput TT", self._format_percent_value(pol_summary["mean_tt"])))
        items.append(("Image throughput TT", self._format_percent_value(pol_summary["image_mean_tt"])))
        items.append(("Mean TP / TS", f"{self._format_percent_value(pol_summary['mean_tp'])} / {self._format_percent_value(pol_summary['mean_ts'])}"))
        items.append(("Mean RP / RS", f"{self._format_percent_value(pol_summary['mean_rp'])} / {self._format_percent_value(pol_summary['mean_rs'])}"))
        items.append(("Mean P/S T split", self._format_percent_value(pol_summary["mean_ps_transmission_split"])))
        items.append(("Mean P/S R split", self._format_percent_value(pol_summary["mean_ps_reflection_split"])))

        phase2_summary = self._phase2_feature_summary()
        items.append(("Phase 2 report", ""))
        items.append(("Source model", str(phase2_summary["source_model"])))
        items.append(("Error-map surfaces", str(phase2_summary["error_map_count"])))
        if phase2_summary["max_error_pv"] is not None:
            items.append(("Max error PV", f"{float(phase2_summary['max_error_pv']):.4g}"))
            items.append(("Max error RMS", f"{float(phase2_summary['max_error_rms']):.4g}"))
        items.append(("Coating surfaces", str(phase2_summary["coating_count"])))
        items.append(("Metal catalogs", str(phase2_summary["metal_catalog_count"])))

        effl_value = self._optional_finite_float(optics_info.get("effl"))
        magnification_value = self._optional_finite_float(optics_info.get("magnification"))
        ppa_value = self._optional_finite_float(optics_info.get("ppa"))
        ppp_value = self._optional_finite_float(optics_info.get("ppp"))
        h1_z_value = self._optional_finite_float(optics_info.get("h1_z"))
        h2_z_value = self._optional_finite_float(optics_info.get("h2_z"))
        paraxial_image_size_value = self._optional_finite_float(optics_info.get("paraxial_image_size"))
        sensor_fill_value = self._optional_finite_float(optics_info.get("sensor_fill"))

        if effl_value is not None:
            items.append(("Imaging", ""))
            items.append(("EFFL [mm]", f"{effl_value:.4g}"))
            items.append(("Magnification", self._format_optional_float(magnification_value)))
            if paraxial_image_size_value is not None:
                items.append(("Paraxial image size [mm]", f"{paraxial_image_size_value:.4g}"))
            if sensor_fill_value is not None:
                items.append(("Sensor fill", f"{100.0 * sensor_fill_value:.3g}%"))
            if any(value is not None for value in (h1_z_value, h2_z_value, ppa_value, ppp_value)):
                items.append(("Principal Planes", ""))
                if h1_z_value is not None:
                    items.append(("Front PP z [mm]", f"{h1_z_value:.4g}"))
                if h2_z_value is not None:
                    items.append(("Back PP z [mm]", f"{h2_z_value:.4g}"))
                if ppa_value is not None:
                    items.append(("PPA offset [mm]", f"{ppa_value:.4g}"))
                if ppp_value is not None:
                    items.append(("PPP offset [mm]", f"{ppp_value:.4g}"))
        else:
            items.append(("Paraxial data", "Unavailable"))

        ep_radius_value = self._optional_finite_float(optics_info.get("ep_radius"))
        ep_z_value = self._optional_finite_float(optics_info.get("ep_z"))
        xp_radius_value = self._optional_finite_float(optics_info.get("xp_radius"))
        xp_z_value = self._optional_finite_float(optics_info.get("xp_z"))
        airy_radius_value = self._optional_finite_float(optics_info.get("airy_radius"))
        if any(value is not None for value in (ep_radius_value, ep_z_value, xp_radius_value, xp_z_value, airy_radius_value)):
            items.append(("Pupils", ""))
            if ep_radius_value is not None:
                items.append(("Entrance pupil radius [mm]", f"{ep_radius_value:.4g}"))
                items.append(("Entrance pupil diameter [mm]", f"{2.0 * ep_radius_value:.4g}"))
            else:
                items.append(("Entrance pupil", "Unavailable"))
            if ep_z_value is not None:
                items.append(("Entrance pupil z [mm]", f"{ep_z_value:.4g}"))
            if xp_radius_value is not None:
                items.append(("Exit pupil radius [mm]", f"{xp_radius_value:.4g}"))
                items.append(("Exit pupil diameter [mm]", f"{2.0 * xp_radius_value:.4g}"))
            else:
                items.append(("Exit pupil", "Unavailable"))
            if xp_z_value is not None:
                items.append(("Exit pupil z [mm]", f"{xp_z_value:.4g}"))
            if airy_radius_value is not None:
                items.append(("Airy radius [mm]", f"{airy_radius_value:.4g}"))
        else:
            items.append(("Pupil data", "Unavailable"))

        items.append(("Spot", ""))
        spot_rms_value = self._optional_finite_float(optics_info.get("spot_rms"))
        if spot_rms_value is not None:
            items.append(("Spot RMS [mm]", f"{spot_rms_value:.4g}"))
            items.append(("Spot centroid X [mm]", self._format_optional_float(optics_info.get("spot_cen_x"))))
            items.append(("Spot centroid Y [mm]", self._format_optional_float(optics_info.get("spot_cen_y"))))
        else:
            items.append(("Spot RMS [mm]", "Unavailable"))

        self._set_results(items)
