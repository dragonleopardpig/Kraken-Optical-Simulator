"""Analysis plot dispatch service."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any
import io

import KrakenOS as Kos
import numpy as np
from matplotlib import colormaps
from matplotlib.ticker import MaxNLocator
from scipy.interpolate import PchipInterpolator


def _layout_module():
    from KrakenOS.UI import layout_editor as layout_editor_module

    return layout_editor_module


class AnalysisPlotService:
    """Render analysis-panel plots while delegating editor state and helpers."""

    def __init__(self, editor: Any) -> None:
        object.__setattr__(self, "editor", editor)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "editor":
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    @staticmethod
    def _field_curve_xy(field_vals: np.ndarray, series_vals: np.ndarray) -> "tuple[np.ndarray, np.ndarray]":
        """Smooth (value, field) curve for a Zemax-style vertical-field panel.

        Field curvature and distortion are even in field, so samples are grouped
        by |field| (averaging any +/- pair or repeat) and ordered from the axis
        (field 0) outward. The aggregated samples are then resampled onto a dense
        field grid with a shape-preserving monotone cubic (PCHIP) so the drawn
        line is a smooth arc rather than polygonal chords.

        Those chords were the actual "T curve not smooth" defect: the tangential
        focus bends hard near the edge field, and at the ~0.7 deg sample spacing
        that fast-curving region rendered as visible corners. PCHIP passes exactly
        through every real sample (so the genuine edge turnover is kept, not
        flattened) and does not overshoot -- unlike the degree-2 fit tried earlier,
        which broke the inflection into pieces.
        """
        fields = np.abs(np.asarray(field_vals, dtype=float))
        values = np.asarray(series_vals, dtype=float)
        if fields.size == 0:
            return values, fields
        keys = np.round(fields, 9)
        unique = np.unique(keys)
        avg_fields = np.empty(unique.size, dtype=float)
        avg_values = np.empty(unique.size, dtype=float)
        for i, key in enumerate(unique):
            sel = keys == key
            avg_fields[i] = float(np.mean(fields[sel]))
            avg_values[i] = float(np.mean(values[sel]))
        if avg_fields.size < 3:
            return avg_values, avg_fields
        dense_fields = np.linspace(float(avg_fields[0]), float(avg_fields[-1]), 480)
        dense_values = PchipInterpolator(avg_fields, avg_values)(dense_fields)
        return dense_values, dense_fields

    @staticmethod
    def _symmetric_axis_limit(*value_arrays: np.ndarray) -> float:
        """A tidy symmetric +/- limit that comfortably contains the data."""
        peak = 0.0
        for values in value_arrays:
            finite = np.asarray(values, dtype=float)
            finite = finite[np.isfinite(finite)]
            if finite.size:
                peak = max(peak, float(np.max(np.abs(finite))))
        if peak <= 1e-9:
            return 1.0
        # Round up to 1/2/5 x 10^k so ticks land on readable values.
        exponent = np.floor(np.log10(peak))
        base = peak / (10.0 ** exponent)
        nice = 1.0 if base <= 1.0 else (2.0 if base <= 2.0 else (5.0 if base <= 5.0 else 10.0))
        return float(nice * (10.0 ** exponent))

    # Portrait box aspect (taller than wide) for the single-panel Field Curvature
    # and Distortion plots -- the field runs up the vertical axis, so a portrait
    # panel reads naturally and centres in the analysis cell.
    _FIELD_PANEL_BOX_ASPECT = 1.3

    @staticmethod
    def _field_curvature_field_max(axis_results, field_limit: float) -> float:
        source = axis_results.get("Y") or axis_results.get("X")
        field_reference = source["fields"]
        field_max = float(np.max(field_reference)) if field_reference.size else max(field_limit, 1.0)
        if field_max <= 1e-9:
            field_max = max(field_limit, 1.0)
        return field_max

    def _style_field_panel(
        self, panel, limit: float, title: str, xlabel: str,
        field_max: float, field_units: str, wavelength: float, frame_color: str,
    ) -> None:
        panel.set_box_aspect(self._FIELD_PANEL_BOX_ASPECT)
        panel.set_xlim(-limit, limit)
        panel.set_ylim(0.0, field_max)
        panel.axvline(0.0, color=frame_color, linewidth=0.8)
        panel.set_title(title, fontsize=9.0, color=frame_color, pad=16)
        panel.set_xlabel(xlabel, fontsize=7.5)
        panel.set_ylabel(f"Field ({field_units})", fontsize=7.5)
        panel.tick_params(axis="both", labelsize=6.5, direction="in")
        panel.xaxis.set_major_locator(MaxNLocator(nbins=4, symmetric=True))
        for spine_name in ("top", "right"):
            panel.spines[spine_name].set_visible(False)
        panel.text(0.5, 1.0, "+Y", transform=panel.transAxes, ha="center", va="bottom",
                   fontsize=7.0, color=frame_color)
        panel.text(
            0.0, -0.16,
            f"{title}   max field {field_max:.4g} {field_units}   {wavelength:.3f} um",
            transform=panel.transAxes, fontsize=6.2, color=frame_color, ha="left", va="top",
        )

    def _plot_field_curvature_panel(
        self,
        analysis_ax,
        axis_results: "dict[str, dict[str, np.ndarray]]",
        field_type: str,
        field_limit: float,
        wavelength: float,
    ):
        """Single-panel Field Curvature plot: tangential (T, solid) and sagittal
        (S, dashed) best-focus shift in mm, field on the vertical axis (Zemax +Y).
        Field curvature and distortion are distinct concepts and now render as
        separate analysis items (was the combined two-panel layout)."""
        line_color = "#2031c0"
        frame_color = "#1f2937"
        tangential = axis_results.get("Y")
        sagittal = axis_results.get("X")
        field_max = self._field_curvature_field_max(axis_results, field_limit)
        field_units = "deg" if field_type == "angle" else "mm"

        focus_values: list[np.ndarray] = []
        if tangential is not None:
            curve_x, curve_y = self._field_curve_xy(tangential["fields"], tangential["focus"])
            analysis_ax.plot(curve_x, curve_y, color=line_color, linewidth=1.4)
            focus_values.append(tangential["focus"])
            analysis_ax.text(curve_x[-1], curve_y[-1], " T", color=line_color, fontsize=8,
                             ha="left", va="bottom")
        if sagittal is not None:
            curve_x, curve_y = self._field_curve_xy(sagittal["fields"], sagittal["focus"])
            analysis_ax.plot(curve_x, curve_y, color=line_color, linewidth=1.4, linestyle=(0, (5, 2)))
            focus_values.append(sagittal["focus"])
            analysis_ax.text(curve_x[-1], curve_y[-1], " S", color=line_color, fontsize=8,
                             ha="left", va="top")

        focus_limit = self._symmetric_axis_limit(*focus_values) if focus_values else 1.0
        self._style_field_panel(analysis_ax, focus_limit, "FIELD CURVATURE", "Millimeters",
                                field_max, field_units, wavelength, frame_color)
        return analysis_ax

    def _plot_distortion_panel(
        self,
        analysis_ax,
        axis_results: "dict[str, dict[str, np.ndarray]]",
        field_type: str,
        field_limit: float,
        wavelength: float,
    ):
        """Single-panel Distortion plot: chief-ray distortion in percent, field on
        the vertical axis (Zemax +Y). Separate analysis item from Field Curvature."""
        line_color = "#2031c0"
        frame_color = "#1f2937"
        source = axis_results.get("Y") or axis_results.get("X")
        field_max = self._field_curvature_field_max(axis_results, field_limit)
        field_units = "deg" if field_type == "angle" else "mm"

        dist_curve_x, dist_curve_y = self._field_curve_xy(source["fields"], source["distortion"])
        analysis_ax.plot(dist_curve_x, dist_curve_y, color=line_color, linewidth=1.4)
        dist_limit = self._symmetric_axis_limit(source["distortion"])
        self._style_field_panel(analysis_ax, dist_limit, "DISTORTION", "Percent",
                                field_max, field_units, wavelength, frame_color)
        return analysis_ax

    def _sample_field_curvature_distortion(self, system, wavelength: float):
        """Trace the dense meridional field scan shared by the Field Curvature and
        Distortion analyses. Returns ``(axis_results, field_type, field_limit)`` or
        ``None`` if too few field samples survive.

        At each field the tangential and sagittal foci come from *isolated* pupil
        fans (a pupil-Y fan for tangential, a pupil-X fan for sagittal) so off-axis
        coma/vignetting in the meridional plane cannot corrupt the tangential
        estimate; the distortion image height comes from the chief ray.
        """
        field_type = "angle" if self._current_object_mode() == "Infinity" else "height"
        field_limit = self._current_field_angle_deg() if field_type == "angle" else self._current_field_height()
        if field_limit <= 1e-9:
            field_limit = 5.0 if field_type == "angle" else max(self._current_field_height(), 0.5)
        field_sample_count = max(21, self._current_field_count() * 2 + 1)
        field_samples = list(np.linspace(0.0, field_limit, field_sample_count))
        self.append_debug(
            f"Field curvature/distortion sampling: type={field_type}, limit={field_limit:.4g}, count={field_sample_count}"
        )
        fan_sample_count = max(15, self._current_ray_count())
        axis_results: dict[str, dict[str, np.ndarray]] = {}
        total_steps = len(field_samples) * 2
        completed_steps = 0

        def _best_focus(coords: np.ndarray, slopes: np.ndarray) -> float:
            # Longitudinal shift that minimises the transverse spread about the
            # centroid. Deviations are measured relative to the chief/centroid ray,
            # not in absolute image coordinates -- otherwise the field offset and
            # chief-ray slope dominate and the result collapses to the axis-crossing
            # distance (tens of mm) rather than the field curvature (sub-mm).
            centroid = float(np.mean(coords))
            slope_mean = float(np.mean(slopes))
            coords_rel = coords - centroid
            slopes_rel = slopes - slope_mean
            denom = float(np.sum(slopes_rel**2))
            if denom <= 1e-12:
                return 0.0
            return -float(np.sum(coords_rel * slopes_rel) / denom)

        measured_fields: list[float] = []
        image_heights: list[float] = []
        tangential_focus: list[float] = []
        sagittal_focus: list[float] = []
        worker_counts: list[int] = []

        def _sample(pattern: str, field_value: float):
            return self._build_geometric_image_samples_full(
                system,
                wavelength,
                sample_count=fan_sample_count,
                pattern=pattern,
                surface_index=self._analysis_surface_index(),
                aperture_type=self._current_aperture_type(),
                aperture_value=self._current_aperture_value(),
                field_type=field_type,
                field_x=0.0,
                field_y=field_value,
            )

        for field_value in field_samples:
            completed_steps += 2
            self._update_analysis_progress("Sampling field curvature", completed_steps, total_steps)
            mer_x, mer_y, _mz, mer_l, mer_m, mer_n, mer_workers = _sample("fany", field_value)
            sag_x, sag_y, _sz, sag_l, sag_m, sag_n, sag_workers = _sample("fanx", field_value)
            if mer_y.size < 3 or sag_x.size < 3:
                continue
            chief_x, chief_y, _cz, _cl, _cm, _cn, _cw = _sample("chief", field_value)

            slopes_mer_y = mer_m / np.where(np.abs(mer_n) < 1e-9, np.sign(mer_n) * 1e-9 + 1e-9, mer_n)
            slopes_sag_x = sag_l / np.where(np.abs(sag_n) < 1e-9, np.sign(sag_n) * 1e-9 + 1e-9, sag_n)

            chief_height = float(chief_y[0]) if chief_y.size else float(np.mean(mer_y))

            worker_counts.append(max(mer_workers, sag_workers))
            measured_fields.append(field_value)
            image_heights.append(chief_height)
            tangential_focus.append(_best_focus(mer_y, slopes_mer_y))
            sagittal_focus.append(_best_focus(sag_x, slopes_sag_x))

        if len(measured_fields) >= 2:
            fields = np.asarray(measured_fields, dtype=float)
            heights = np.asarray(image_heights, dtype=float)
            abs_fields = np.abs(fields)
            abs_heights = np.abs(heights)
            on_axis = int(np.argmin(abs_fields))

            def _curvature(focus_list: "list[float]") -> np.ndarray:
                # Reference each curve to the on-axis focus so the panel shows the
                # field-dependent curvature rising from ~0 at the axis, not the
                # constant defocus of wherever the image plane sits.
                focus = np.asarray(focus_list, dtype=float)
                if focus.size:
                    focus = focus - focus[on_axis]
                return focus

            # Distortion is referenced to the *paraxial* magnification (image height
            # per field as field -> 0), not a global least-squares slope, so it is
            # ~0 on axis and grows monotonically toward the edge (matching Zemax).
            distortion = np.zeros_like(abs_heights)
            mask = abs_fields > 1e-9
            if np.count_nonzero(mask) >= 2:
                f_on = abs_fields[mask]
                mag = abs_heights[mask] / f_on
                if np.unique(np.round(f_on, 9)).size >= 2:
                    mag_paraxial = float(np.polyfit(f_on**2, mag, 1)[-1])
                else:
                    mag_paraxial = float(np.min(mag))
                if not np.isfinite(mag_paraxial) or abs(mag_paraxial) <= 1e-12:
                    mag_paraxial = float(np.mean(mag))
                ideal = mag_paraxial * abs_fields
                valid = np.abs(ideal) > 1e-12
                distortion[valid] = (abs_heights[valid] - ideal[valid]) / ideal[valid] * 100.0

            workers_arr = np.asarray([max(worker_counts) if worker_counts else 1], dtype=float)
            axis_results["Y"] = {
                "fields": abs_fields,
                "focus": _curvature(tangential_focus),
                "distortion": distortion,
                "workers": workers_arr,
            }
            axis_results["X"] = {
                "fields": abs_fields,
                "focus": _curvature(sagittal_focus),
                "distortion": distortion,
                "workers": workers_arr,
            }

        if not axis_results:
            return None
        return axis_results, field_type, field_limit

    def plot_analysis(self, analysis_ax, system, rays, wavelength: float) -> None:
        le = _layout_module()
        SOURCE_MODEL_DEFAULT = le.SOURCE_MODEL_DEFAULT
        WAVEFRONT_FUNCTION_STYLE = le.WAVEFRONT_FUNCTION_STYLE
        WAVEFRONT_PHASE_STYLE = le.WAVEFRONT_PHASE_STYLE
        _is_all_path_filter = le._is_all_path_filter
        if analysis_ax is None:
            return
        analysis_ax.clear()
        analysis_ax.set_aspect("auto")
        analysis_ax.set_box_aspect(0.62)
        spot_field_series: list[tuple[np.ndarray, np.ndarray, float]] = []
        trace_ray_records: list[dict[str, object]] | None = None

        def current_trace_ray_records() -> list[dict[str, object]]:
            nonlocal trace_ray_records
            if trace_ray_records is None:
                trace_ray_records = self._ray_analysis_records_for_trace(system=system, rays=rays)
            return trace_ray_records

        if self.analysis_mode == "interferogram":
            self._plot_interferogram_analysis(analysis_ax, system, rays, wavelength)
            return
        if self.analysis_mode == "tolerance_compare":
            self._plot_tolerance_comparison_analysis(analysis_ax, system, wavelength)
            return
        if self.analysis_mode == "atmosphere":
            try:
                self._set_analysis_parallel_status("Atmosphere", 1, False)
                self._begin_analysis_progress("Atmosphere analysis")
                settings = self._current_atmosphere_settings()
                wavelengths = self._atmosphere_wavelength_samples()
                plot_mode = self._current_atmos_plot_mode()
                if plot_mode == "Image residual (current optics)":
                    self._plot_atmosphere_image_residual(analysis_ax, system, wavelength, settings, wavelengths)
                    return

                self._update_analysis_progress("Computing refraction", 1, 2)
                refraction_deg = np.asarray(
                    [
                        Kos.quick_refraction(
                            float(wl),
                            float(settings["zenith_deg"]),
                            conditions=None,
                            T=float(settings["temperature_k"]),
                            p=float(settings["pressure_pa"]),
                            RH=float(settings["humidity"]),
                            xc=float(settings["co2_ppm"]),
                            lat=float(settings["latitude_deg"]),
                            h=float(settings["altitude_m"]),
                        )
                        for wl in wavelengths
                    ],
                    dtype=float,
                )
                finite = np.isfinite(wavelengths) & np.isfinite(refraction_deg)
                wavelengths = wavelengths[finite]
                refraction_deg = refraction_deg[finite]
                if wavelengths.size < 2:
                    raise RuntimeError("Not enough finite atmosphere samples")

                refraction_arcsec = refraction_deg * 3600.0
                reference_wavelength = float(np.clip(self._current_wavelength(), wavelengths[0], wavelengths[-1]))
                reference_refraction = float(np.interp(reference_wavelength, wavelengths, refraction_arcsec))
                dispersion_arcsec = refraction_arcsec - reference_refraction
                blue_red_arcsec = float(
                    Kos.quick_dispersion(
                        float(wavelengths[0]),
                        float(wavelengths[-1]),
                        float(settings["zenith_deg"]),
                        conditions=None,
                        T=float(settings["temperature_k"]),
                        p=float(settings["pressure_pa"]),
                        RH=float(settings["humidity"]),
                        xc=float(settings["co2_ppm"]),
                        lat=float(settings["latitude_deg"]),
                        h=float(settings["altitude_m"]),
                    )
                    * 3600.0
                )

                line_ref, = analysis_ax.plot(
                    wavelengths,
                    refraction_arcsec,
                    color="#1d4ed8",
                    linewidth=2.0,
                    marker="o",
                    markersize=3.5,
                    label="Refraction",
                )
                ax2 = analysis_ax.twinx()
                line_disp, = ax2.plot(
                    wavelengths,
                    dispersion_arcsec,
                    color="#b45309",
                    linewidth=1.8,
                    linestyle="--",
                    marker="s",
                    markersize=3.0,
                    label=f"Dispersion vs {reference_wavelength:.4g} um",
                )
                analysis_ax.axvline(reference_wavelength, color="#64748b", linewidth=0.8, alpha=0.6)
                analysis_ax.set_title(f"Atmospheric Refraction / Dispersion  |  Z={float(settings['zenith_deg']):.3g} deg")
                analysis_ax.set_xlabel("Wavelength [um]")
                analysis_ax.set_ylabel("Refraction [arcsec]", color="#1d4ed8")
                ax2.set_ylabel("Relative dispersion [arcsec]", color="#b45309")
                analysis_ax.grid(True, alpha=0.2)
                analysis_ax.set_box_aspect(0.62)
                analysis_ax.legend([line_ref, line_disp], ["Refraction", "Relative dispersion"], loc="best", fontsize=8)
                y_min, y_max = analysis_ax.get_ylim()
                analysis_ax.text(
                    0.02,
                    0.03,
                    f"blue-red dispersion: {blue_red_arcsec:.3g} arcsec\n"
                    f"T={float(settings['temperature_k']):.4g} K, P={float(settings['pressure_pa']):.4g} Pa, "
                    f"RH={float(settings['humidity']):.3g}",
                    transform=analysis_ax.transAxes,
                    ha="left",
                    va="bottom",
                    fontsize=7.5,
                    bbox={"facecolor": "white", "edgecolor": "#cbd5e1", "alpha": 0.78, "pad": 3},
                )
                analysis_ax.set_ylim(y_min, y_max)
                self.append_debug(
                    f"Atmosphere ok: wavelengths={wavelengths.size}, zenith={float(settings['zenith_deg']):.6g}, "
                    f"blue_red_arcsec={blue_red_arcsec:.6g}, reference_um={reference_wavelength:.6g}"
                )
                self._update_analysis_progress("Rendering", 2, 2)
                self._finish_analysis_progress("Atmosphere analysis", success=True)
            except Exception as exc:
                self._set_analysis_parallel_status("Atmosphere", 1, False)
                self.append_debug(f"Atmosphere analysis error: {exc}")
                analysis_ax.text(0.5, 0.5, "Atmosphere analysis unavailable", ha="center", va="center")
                analysis_ax.set_axis_off()
                self._finish_analysis_progress("Atmosphere analysis", success=False)
            return

        if self.analysis_mode in {"spot", "rms"} and not _is_all_path_filter(self._current_analysis_branch_filter()):
            self._plot_branch_detector_spot_analysis(
                analysis_ax,
                system,
                self.analysis_mode,
                ray_records=current_trace_ray_records(),
            )
            return

        if self.analysis_mode == "psf" and not _is_all_path_filter(self._current_analysis_branch_filter()):
            self._plot_branch_detector_psf_analysis(
                analysis_ax,
                system,
                wavelength,
                ray_records=current_trace_ray_records(),
            )
            return

        if self.analysis_mode == "mtf" and not _is_all_path_filter(self._current_analysis_branch_filter()):
            self._plot_branch_detector_mtf_analysis(
                analysis_ax,
                system,
                wavelength,
                ray_records=current_trace_ray_records(),
            )
            return

        if self.analysis_mode == "detector_map":
            self._plot_branch_detector_map_analysis(
                analysis_ax,
                system,
                ray_records=current_trace_ray_records(),
            )
            return

        if self.analysis_mode == "coherent_detector":
            self._plot_coherent_detector_analysis(
                analysis_ax,
                system,
                wavelength,
                ray_records=current_trace_ray_records(),
            )
            return

        if self.analysis_mode == "branch_field":
            self._plot_branch_field_analysis(
                analysis_ax,
                system,
                wavelength,
                ray_records=current_trace_ray_records(),
            )
            return

        if self.analysis_mode == "diffraction_detector":
            self._plot_diffraction_detector_analysis(
                analysis_ax,
                system,
                wavelength,
                ray_records=current_trace_ray_records(),
            )
            return

        try:
            if self.analysis_mode in {"spot", "rms"}:
                field_type = "angle" if self._current_object_mode() == "Infinity" else "height"
                center_field = self._current_field_angle_deg() if field_type == "angle" else self._current_field_height()
                sampled_fields = [center_field]
                if self.analysis_mode == "spot" and self._current_source_model() == SOURCE_MODEL_DEFAULT:
                    sampled_fields = self._sample_field_values(center_field)
                    if not sampled_fields:
                        sampled_fields = [center_field]

                field_results = []
                analysis_workers = 1
                for field_value in sampled_fields:
                    Xi, Yi, Zi, Li, Mi, Ni, worker_count = self._build_geometric_image_samples_full(
                        system,
                        wavelength,
                        sample_count=max(24, self._current_ray_count() * 6),
                        pattern="hexapolar",
                        surface_index=self._analysis_surface_index(),
                        aperture_type=self._current_aperture_type(),
                        aperture_value=self._current_aperture_value(),
                        field_type=field_type,
                        field_x=0.0,
                        field_y=float(field_value),
                    )
                    analysis_workers = max(analysis_workers, int(worker_count))
                    if Xi.size == 0:
                        continue
                    field_results.append((Xi, Yi, Zi, Li, Mi, Ni, float(field_value)))

                if not field_results:
                    X = Y = Z = L = M = N = np.asarray([])
                else:
                    X = np.concatenate([result[0] for result in field_results])
                    Y = np.concatenate([result[1] for result in field_results])
                    Z = np.concatenate([result[2] for result in field_results])
                    L = np.concatenate([result[3] for result in field_results])
                    M = np.concatenate([result[4] for result in field_results])
                    N = np.concatenate([result[5] for result in field_results])
                    if self.analysis_mode == "spot":
                        spot_field_series = [
                            (result[0], result[1], result[6]) for result in field_results
                        ]
            else:
                analysis_rays = self._build_analysis_rays(system, wavelength)
                X, Y, Z, L, M, N = self._pick_image_plane_data(analysis_rays)
                analysis_workers = 1
        except Exception as exc:
            self.append_debug(f"{self.analysis_mode.upper()} analysis trace error: {exc}")
            X = Y = Z = L = M = N = np.asarray([])
            analysis_workers = 1

        if X.size == 0 and self.analysis_mode in {"spot", "rms"}:
            analysis_ax.text(0.5, 0.5, "No ray data", ha="center", va="center")
            analysis_ax.set_axis_off()
            return

        if self.analysis_mode == "spot":
            self._set_analysis_parallel_status("Spot", analysis_workers, True)
            spot_mode = self._current_spot_view_mode()
            if spot_field_series:
                colors = self._field_colors(len(spot_field_series))
                field_unit = "deg" if self._current_object_mode() == "Infinity" else "mm"
                prepared_series: list[tuple[np.ndarray, np.ndarray, float]] = []
                if spot_mode == "Absolute":
                    for x_field, y_field, field_value in spot_field_series:
                        prepared_series.append((x_field, y_field, field_value))
                else:
                    centered_series = []
                    max_span = 1e-3
                    for x_field, y_field, field_value in spot_field_series:
                        cx = float(np.mean(x_field))
                        cy = float(np.mean(y_field))
                        sx = x_field - cx
                        sy = y_field - cy
                        max_span = max(max_span, float(max(np.ptp(sx), np.ptp(sy), 1e-6)))
                        centered_series.append((sx, sy, field_value))
                    if spot_mode == "Grid" and centered_series:
                        cols = max(1, int(np.ceil(np.sqrt(len(centered_series)))))
                        rows = int(np.ceil(len(centered_series) / cols))
                        spacing = max(max_span * 1.8, 2e-3)
                        for index, (sx, sy, field_value) in enumerate(centered_series):
                            row = index // cols
                            col = index % cols
                            offset_x = (col - (cols - 1) / 2.0) * spacing
                            offset_y = ((rows - 1) / 2.0 - row) * spacing
                            prepared_series.append((sx + offset_x, sy + offset_y, field_value))
                    else:
                        prepared_series = centered_series
                X_plot = np.concatenate([item[0] for item in prepared_series]) if prepared_series else X
                Y_plot = np.concatenate([item[1] for item in prepared_series]) if prepared_series else Y
                draw_order = sorted(
                    range(len(prepared_series)),
                    key=lambda idx: abs(float(prepared_series[idx][2])),
                    reverse=True,
                )
                for rank, index in enumerate(draw_order):
                    _x_field, _y_field, field_value = prepared_series[index]
                    analysis_ax.scatter(
                        _x_field,
                        _y_field,
                        s=8,
                        c=colors[index],
                        alpha=0.45,
                        label=f"{field_value:.3g} {field_unit}",
                        zorder=3 + rank,
                    )
                if len(spot_field_series) > 1:
                    analysis_ax.legend(loc="upper right", fontsize=7, title="Field")
            else:
                if spot_mode == "Absolute":
                    X_plot = X
                    Y_plot = Y
                else:
                    X_plot = X - float(np.mean(X))
                    Y_plot = Y - float(np.mean(Y))
                analysis_ax.scatter(X_plot, Y_plot, s=18, c="#c0392b", alpha=0.8)
            analysis_ax.axhline(0.0, color="#2c3e50", linewidth=0.6, alpha=0.5)
            analysis_ax.axvline(0.0, color="#2c3e50", linewidth=0.6, alpha=0.5)
            title_suffix = {
                "Absolute": "Absolute",
                "Centroid": "Centroid Referenced",
                "Grid": "Grid View",
            }.get(spot_mode, "Grid View")
            analysis_ax.set_title(f"Spot Diagram ({title_suffix})")
            analysis_ax.set_xlabel("X [mm]")
            analysis_ax.set_ylabel("Y [mm]")
            self._apply_equal_spot_axis_scaling(analysis_ax, X_plot, Y_plot)
            if spot_mode == "Absolute":
                analysis_ax.xaxis.set_major_locator(MaxNLocator(5))
                analysis_ax.yaxis.set_major_locator(MaxNLocator(5))
                analysis_ax.tick_params(axis="x", labelrotation=0)
            analysis_ax.grid(True, alpha=0.2)
            self.append_debug(f"Spot analysis ok: rays={len(X)}, workers={analysis_workers}")
            return

        if self.analysis_mode == "psf":
            try:
                self._begin_analysis_progress("PSF analysis")
                field_type = "angle" if self._current_object_mode() == "Infinity" else "height"
                field_y = self._current_field_angle_deg() if field_type == "angle" else self._current_field_height()
                self._update_analysis_progress("Tracing rays", 1, 3)
                x_local, y_local, worker_count = self._build_geometric_image_samples(
                    system,
                    wavelength,
                    sample_count=max(48, self._current_ray_count() * 10),
                    pattern="hexapolar",
                    surface_index=self._analysis_surface_index(),
                    aperture_type=self._current_aperture_type(),
                    aperture_value=self._current_aperture_value(),
                    field_type=field_type,
                    field_x=0.0,
                    field_y=field_y,
                )
                self._update_analysis_progress("Building PSF image", 2, 3)
                if x_local.size < 4:
                    raise RuntimeError("Not enough image-plane samples for PSF")
                span_x = max(float(np.ptp(x_local)), 1e-3)
                span_y = max(float(np.ptp(y_local)), 1e-3)
                span = max(span_x, span_y) * 1.25
                bins = 128
                hist, xedges, yedges, accelerator = self._compute_psf_histogram(x_local, y_local, bins, span)
                psf = hist.T
                psf /= max(float(np.max(psf)), 1e-12)
                extent = [float(xedges[0]), float(xedges[-1]), float(yedges[0]), float(yedges[-1])]
                image = analysis_ax.imshow(psf, origin="lower", extent=extent, cmap="inferno", aspect="equal")
                self._set_analysis_parallel_status("PSF", worker_count, True)
                self._set_analysis_accelerator(accelerator)
                analysis_ax.set_title(f"Geometric PSF  |  {field_type}={field_y:.3g}  |  {wavelength:.4g} um")
                analysis_ax.set_xlabel("X [mm]")
                analysis_ax.set_ylabel("Y [mm]")
                analysis_ax.set_box_aspect(0.62)
                analysis_ax.grid(False)
                self.figure.colorbar(image, ax=analysis_ax, fraction=0.046, pad=0.04, label="Normalized intensity")
                self.append_debug(
                    f"PSF analysis ok: rays={x_local.size}, bins={bins}, workers={worker_count}, accel={accelerator}"
                )
                self._update_analysis_progress("Rendering", 3, 3)
                self._finish_analysis_progress("PSF analysis", success=True)
            except Exception as exc:
                self._set_analysis_parallel_status("PSF", 1, True)
                self.append_debug(f"PSF analysis error: {exc}")
                analysis_ax.text(0.5, 0.5, "PSF analysis unavailable", ha="center", va="center")
                analysis_ax.set_axis_off()
                self._finish_analysis_progress("PSF analysis", success=False)
            return

        if self.analysis_mode == "psf_map":
            try:
                self._set_analysis_parallel_status("PSF map", 1, True)
                self._begin_analysis_progress("PSF map")
                if self._current_source_model() != SOURCE_MODEL_DEFAULT:
                    analysis_ax.text(
                        0.5,
                        0.5,
                        "PSFMap uses Pupil / field sampling.\nUse Illum for random-source throughput.",
                        ha="center",
                        va="center",
                    )
                    analysis_ax.set_axis_off()
                    self._finish_analysis_progress("PSF map", success=False)
                    return
                field_samples = self._resolved_field_grid_samples()
                if not field_samples:
                    raise RuntimeError("No valid PSF-map samples")

                sample_count = max(32, self._current_ray_count() * 6)
                self._update_analysis_progress("Tracing field PSFs", 1, 3)
                sample_results, worker_count = self._build_geometric_image_samples_for_field_samples(
                    wavelength,
                    sample_count=sample_count,
                    pattern=self._current_analysis_pupil_pattern("hexapolar"),
                    surface_index=self._analysis_surface_index(),
                    aperture_type=self._current_aperture_type(),
                    aperture_value=self._current_aperture_value(),
                    field_samples=field_samples,
                )
                if not sample_results:
                    raise RuntimeError("No image-plane PSF samples")

                self._update_analysis_progress("Building PSF tiles", 2, 3)
                display_x = [float(sample["display_x"]) for sample in field_samples]
                display_y = [float(sample["display_y"]) for sample in field_samples]
                x_unique = np.asarray(sorted(set(round(value, 12) for value in display_x)), dtype=float)
                y_unique = np.asarray(sorted(set(round(value, 12) for value in display_y)), dtype=float)
                if x_unique.size == 0 or y_unique.size == 0:
                    raise RuntimeError("No valid PSF-map grid")
                x_lookup = {float(value): i for i, value in enumerate(x_unique)}
                y_lookup = {float(value): i for i, value in enumerate(y_unique)}

                centered_results: list[tuple[np.ndarray, np.ndarray]] = []
                spans: list[float] = []
                for x_local, y_local in sample_results:
                    x_vals, y_vals = self._center_image_plane_samples(x_local, y_local)
                    centered_results.append((x_vals, y_vals))
                    if x_vals.size >= 4:
                        spans.append(max(float(np.ptp(x_vals)), float(np.ptp(y_vals))))
                if not spans:
                    raise RuntimeError("No finite PSF-map ray bundles")

                span = max(max(spans) * 1.25, 1e-3)
                tile_bins = 48 if len(field_samples) <= 9 else 36 if len(field_samples) <= 25 else 28
                gap = max(1, tile_bins // 12)
                height = int(y_unique.size * tile_bins + max(0, y_unique.size - 1) * gap)
                width = int(x_unique.size * tile_bins + max(0, x_unique.size - 1) * gap)
                mosaic = np.full((height, width), np.nan, dtype=float)

                valid_tiles = 0
                for sample, (x_vals, y_vals) in zip(field_samples, centered_results):
                    if x_vals.size < 4:
                        continue
                    hist, _xedges, _yedges = np.histogram2d(
                        x_vals,
                        y_vals,
                        bins=tile_bins,
                        range=[[-span / 2.0, span / 2.0], [-span / 2.0, span / 2.0]],
                    )
                    tile = hist.T
                    peak = float(np.max(tile)) if tile.size else 0.0
                    if peak <= 0.0:
                        continue
                    tile = np.sqrt(tile / peak)
                    x_index = x_lookup[round(float(sample["display_x"]), 12)]
                    y_index = y_lookup[round(float(sample["display_y"]), 12)]
                    x0 = int(x_index * (tile_bins + gap))
                    y0 = int(y_index * (tile_bins + gap))
                    mosaic[y0 : y0 + tile_bins, x0 : x0 + tile_bins] = tile
                    valid_tiles += 1
                if valid_tiles == 0:
                    raise RuntimeError("No valid PSF-map tiles")

                cmap = colormaps.get_cmap("inferno").copy()
                cmap.set_bad("#f3f4f6")
                image = analysis_ax.imshow(
                    mosaic,
                    origin="lower",
                    interpolation="nearest",
                    cmap=cmap,
                    vmin=0.0,
                    vmax=1.0,
                )
                unit = str(field_samples[0]["unit"])
                basis = str(field_samples[0]["basis"])
                label = f"{basis} [{unit}]" if unit else basis
                x_ticks = [index * (tile_bins + gap) + (tile_bins - 1) / 2.0 for index in range(x_unique.size)]
                y_ticks = [index * (tile_bins + gap) + (tile_bins - 1) / 2.0 for index in range(y_unique.size)]
                analysis_ax.set_xticks(x_ticks, [self._format_field_sample_value(value) for value in x_unique])
                analysis_ax.set_yticks(y_ticks, [self._format_field_sample_value(value) for value in y_unique])
                analysis_ax.tick_params(axis="x", labelrotation=35 if x_unique.size > 3 else 0)
                analysis_ax.set_title("Wide-Field Geometric PSF Map")
                analysis_ax.set_xlabel(f"Field X: {label}")
                analysis_ax.set_ylabel(f"Field Y: {label}")
                analysis_ax.set_box_aspect(0.85)
                analysis_ax.grid(False)
                cbar = analysis_ax.figure.colorbar(image, ax=analysis_ax, fraction=0.046, pad=0.04)
                cbar.set_label("Normalized intensity per field")
                self._set_analysis_parallel_status("PSF map", worker_count, True)
                self.append_debug(
                    f"PSFMap ok: samples={len(field_samples)}, tiles={valid_tiles}, "
                    f"rays_per_field={sample_count}, bins={tile_bins}, span={span:.6g}, workers={worker_count}"
                )
                self._update_analysis_progress("Rendering", 3, 3)
                self._finish_analysis_progress("PSF map", success=True)
            except Exception as exc:
                self._set_analysis_parallel_status("PSF map", 1, True)
                self.append_debug(f"PSFMap error: {exc}")
                analysis_ax.text(0.5, 0.5, "PSF map unavailable", ha="center", va="center")
                analysis_ax.set_axis_off()
                self._finish_analysis_progress("PSF map", success=False)
            return

        if self.analysis_mode == "rms":
            self._set_analysis_parallel_status("RMS", analysis_workers, True)
            rms, cenX, cenY = Kos.RMS(X, Y, Z, L, M, N)
            radii = np.sqrt((X - cenX) ** 2 + (Y - cenY) ** 2)
            bins = min(max(5, int(np.sqrt(max(len(radii), 1)))), 20)
            analysis_ax.hist(radii, bins=bins, color="#4f81bd", edgecolor="white")
            analysis_ax.set_title(f"Spot Radius Histogram  |  RMS = {float(rms):.4g} mm")
            analysis_ax.set_xlabel("Radius [mm]")
            analysis_ax.set_ylabel("Count")
            analysis_ax.set_box_aspect(0.52)
            analysis_ax.grid(True, axis="y", alpha=0.2)
            self.append_debug(f"RMS analysis ok: rays={len(X)}, workers={analysis_workers}")
            return

        if self.analysis_mode == "pupil":
            try:
                self._set_analysis_parallel_status("Pupil", 1, False)
                self._begin_analysis_progress("Pupil analysis")
                self._update_analysis_progress("Building pupil", 1, 2)
                pupil = Kos.PupilCalc(
                    system,
                    self._analysis_surface_index(),
                    wavelength,
                    self._current_aperture_type(),
                    self._current_aperture_value(),
                )
                labels = [
                    ("Input Radius", float(pupil.RadPupInp)),
                    ("Input Z", float(pupil.PosPupInp[2])),
                    ("Output Radius", float(pupil.RadPupOut)),
                    ("Output Z", float(pupil.PosPupOut[2])),
                    ("Airy Radius", float(pupil.FocusAiryRadius)),
                ]
                y_pos = np.arange(len(labels))
                values = [item[1] for item in labels]
                analysis_ax.barh(y_pos, values, color="#16a085")
                analysis_ax.set_yticks(y_pos, [item[0] for item in labels])
                analysis_ax.set_title("Pupil Summary")
                analysis_ax.set_xlabel("mm")
                analysis_ax.set_box_aspect(0.52)
                analysis_ax.grid(True, axis="x", alpha=0.2)
                self._update_analysis_progress("Rendering", 2, 2)
                self._finish_analysis_progress("Pupil analysis", success=True)
            except Exception:
                analysis_ax.text(0.5, 0.5, "Pupil analysis unavailable", ha="center", va="center")
                analysis_ax.set_axis_off()
                self._finish_analysis_progress("Pupil analysis", success=False)
            return

        if self.analysis_mode == "seidel":
            try:
                self._set_analysis_parallel_status("Seidel", 1, False)
                self._begin_analysis_progress("Seidel analysis")
                self._update_analysis_progress("Building pupil", 1, 3)
                pupil = Kos.PupilCalc(
                    system,
                    self._analysis_surface_index(),
                    wavelength,
                    self._current_aperture_type(),
                    self._current_aperture_value(),
                )
                self._update_analysis_progress("Computing coefficients", 2, 3)
                seidel = Kos.Seidel(pupil)
                values = np.asarray(seidel.SCW_TOTAL, dtype=float)
                labels = seidel.SCW_NM
                analysis_ax.bar(np.arange(len(values)), values, color="#8e44ad")
                analysis_ax.set_xticks(np.arange(len(values)), labels, rotation=25, ha="right")
                analysis_ax.set_title("Seidel Coefficients in Waves")
                analysis_ax.set_ylabel("Waves")
                analysis_ax.set_box_aspect(0.52)
                analysis_ax.grid(True, axis="y", alpha=0.2)
                self._update_analysis_progress("Rendering", 3, 3)
                self._finish_analysis_progress("Seidel analysis", success=True)
            except Exception:
                analysis_ax.text(0.5, 0.5, "Seidel analysis unavailable", ha="center", va="center")
                analysis_ax.set_axis_off()
                self._finish_analysis_progress("Seidel analysis", success=False)
            return

        if self.analysis_mode == "wavefront":
            try:
                self._last_wavefront_samples = []
                self._last_zemax_wavefront_comparison = None
                self._set_analysis_parallel_status("Wavefront", 1, False)
                self._begin_analysis_progress("Wavefront analysis")
                self._update_analysis_progress("Building pupil", 1, 3)
                style = self._current_wavefront_style()
                pupil = Kos.PupilCalc(
                    system,
                    self._analysis_surface_index(),
                    wavelength,
                    self._current_aperture_type(),
                    self._current_aperture_value(),
                )
                pupil.Samp = max(8, min(22, int(np.sqrt(max(1, self._current_ray_count())) * 4)))
                pupil.Ptype = self._current_analysis_pupil_pattern("hexapolar")
                field_type = "angle" if self._current_object_mode() == "Infinity" else "height"
                pupil.FieldType = field_type
                pupil.FieldX = 0.0
                pupil.FieldY = self._current_field_angle_deg() if field_type == "angle" else self._current_field_height()
                try:
                    pattern_plot_x, pattern_plot_y = self._wavefront_pattern_coordinates(pupil)
                except Exception as exc:
                    self.append_debug(f"Wavefront sampled-pupil pattern fallback unavailable: {exc}")
                    pattern_plot_x = np.asarray([], dtype=float)
                    pattern_plot_y = np.asarray([], dtype=float)
                self._update_analysis_progress("Computing phase", 2, 3)
                phase_method = "Phase"
                numpy_state = None
                try:
                    if str(getattr(pupil, "Ptype", "")).strip().lower() == "rand":
                        numpy_state = np.random.get_state()
                        np.random.seed(self._current_source_seed())
                    try:
                        px, py, phase, _p2v = Kos.Phase(pupil)
                    finally:
                        if numpy_state is not None:
                            np.random.set_state(numpy_state)
                except Exception:
                    capture = io.StringIO()
                    with redirect_stdout(capture), redirect_stderr(capture):
                        px, py, phase, _p2v = Kos.Phase2(pupil)
                    phase_method = "Phase2"
                    phase2_log = capture.getvalue().strip()
                    if phase2_log:
                        self.append_debug(phase2_log)

                px = np.asarray(px, dtype=float).ravel()
                py = np.asarray(py, dtype=float).ravel()
                phase = np.asarray(phase, dtype=float).ravel()
                finite = np.isfinite(px) & np.isfinite(py) & np.isfinite(phase)
                pattern_plot_x = np.asarray(pattern_plot_x, dtype=float).ravel()
                pattern_plot_y = np.asarray(pattern_plot_y, dtype=float).ravel()
                if pattern_plot_x.shape == phase.shape and pattern_plot_y.shape == phase.shape:
                    pattern_plot_x = pattern_plot_x[finite]
                    pattern_plot_y = pattern_plot_y[finite]
                else:
                    pattern_plot_x = np.asarray([], dtype=float)
                    pattern_plot_y = np.asarray([], dtype=float)
                px = px[finite]
                py = py[finite]
                phase = phase[finite]
                if phase.size < 4:
                    raise RuntimeError("Not enough finite wavefront samples")

                plot_x = py
                plot_y = px
                coordinate_note = "Phase pupil coordinates"
                raw_quality_ok, raw_quality_note = self._wavefront_pupil_quality(plot_x, plot_y)
                pattern_quality_ok, _pattern_quality_note = self._wavefront_pupil_quality(pattern_plot_x, pattern_plot_y)
                if not raw_quality_ok and pattern_quality_ok:
                    plot_x = pattern_plot_x
                    plot_y = pattern_plot_y
                    coordinate_note = f"sampled pupil pattern fallback ({raw_quality_note})"
                phase_centered = phase - float(np.mean(phase))
                phase_pv = float(np.ptp(phase))
                phase_rms = float(np.sqrt(np.mean(phase_centered * phase_centered)))
                is_wavefront_function = style == WAVEFRONT_FUNCTION_STYLE

                colorbar_label = "Wavefront [waves]"
                cmap_name = "RdBu_r"
                display_values = phase
                metric_note = f"P-V {phase_pv:.4g} waves\nRMS {phase_rms:.4g} waves"
                image = None
                slope_rms = None
                display_pv = phase_pv
                display_rms = phase_rms
                function_reference = "mean piston removed"
                function_quality_ok = True
                function_quality_note = ""
                zemax_comparison: dict[str, object] | None = None

                if is_wavefront_function:
                    display_values = self._remove_wavefront_reference_plane(plot_x, plot_y, phase_centered)
                    finite_display = np.isfinite(display_values)
                    if np.any(finite_display):
                        display_pv = float(np.nanmax(display_values[finite_display]) - np.nanmin(display_values[finite_display]))
                        display_rms = float(np.sqrt(np.nanmean(display_values[finite_display] * display_values[finite_display])))
                    function_reference = "best-fit piston/tilt removed"
                    function_quality_ok, function_quality_note = self._wavefront_pupil_quality(plot_x, plot_y)
                    zemax_comparison = self._compare_zemax_wavefront_reference(plot_x, plot_y, display_values, wavelength)
                    analysis_ax = self._plot_wavefront_function_analysis(
                        analysis_ax,
                        plot_x,
                        plot_y,
                        display_values,
                        phase_pv=display_pv,
                        phase_rms=display_rms,
                        phase_method=phase_method,
                        reference_note=function_reference,
                        pupil_quality=(function_quality_ok, function_quality_note),
                        coordinate_note=coordinate_note,
                    )
                    self._annotate_zemax_wavefront_comparison(analysis_ax, zemax_comparison)
                elif style == "Wrapped phase":
                    display_values = np.mod(phase + 0.5, 1.0) - 0.5
                    colorbar_label = "Wrapped phase [waves]"
                    cmap_name = "twilight_shifted"
                    metric_note += "\nwrapped to +/-0.5 waves"
                elif style == "Interferogram":
                    display_values = 0.5 + 0.5 * np.cos(2.0 * np.pi * phase)
                    colorbar_label = "Relative intensity"
                    cmap_name = "gray"
                    metric_note += "\ncos(2*pi*W)"
                elif style == WAVEFRONT_PHASE_STYLE:
                    zemax_comparison = self._compare_zemax_wavefront_reference(plot_x, plot_y, phase_centered, wavelength)
                self._last_zemax_wavefront_comparison = zemax_comparison

                if not is_wavefront_function and style in {"Slope X", "Slope Y", "Slope magnitude"}:
                    from matplotlib.tri import LinearTriInterpolator, Triangulation

                    if np.ptp(plot_x) <= 1e-12 or np.ptp(plot_y) <= 1e-12:
                        raise RuntimeError("Degenerate pupil samples for slope map")
                    grid_count = max(48, min(120, int(np.sqrt(max(phase.size, 1)) * 6)))
                    x_grid = np.linspace(float(np.min(plot_x)), float(np.max(plot_x)), grid_count)
                    y_grid = np.linspace(float(np.min(plot_y)), float(np.max(plot_y)), grid_count)
                    xx, yy = np.meshgrid(x_grid, y_grid)
                    triangulation = Triangulation(plot_x, plot_y)
                    interpolator = LinearTriInterpolator(triangulation, phase)
                    phase_grid = np.asarray(interpolator(xx, yy).filled(np.nan), dtype=float)
                    grad_y, grad_x = np.gradient(phase_grid, y_grid, x_grid)
                    if style == "Slope X":
                        display_grid = grad_x
                        colorbar_label = "dW/dX [waves/pupil]"
                    elif style == "Slope Y":
                        display_grid = grad_y
                        colorbar_label = "dW/dY [waves/pupil]"
                    else:
                        display_grid = np.sqrt(grad_x * grad_x + grad_y * grad_y)
                        colorbar_label = "|grad W| [waves/pupil]"
                    finite_display = np.isfinite(display_grid)
                    if not np.any(finite_display):
                        raise RuntimeError("Wavefront slope interpolation produced no finite samples")
                    slope_rms = float(np.sqrt(np.nanmean(display_grid[finite_display] * display_grid[finite_display])))
                    metric_note += f"\nRMS slope {slope_rms:.4g}"
                    cmap = colormaps.get_cmap("magma" if style == "Slope magnitude" else "RdBu_r").copy()
                    cmap.set_bad("#f3f4f6")
                    image = analysis_ax.imshow(
                        np.ma.masked_invalid(display_grid),
                        origin="lower",
                        extent=[float(x_grid[0]), float(x_grid[-1]), float(y_grid[0]), float(y_grid[-1])],
                        cmap=cmap,
                        aspect="equal",
                    )
                elif not is_wavefront_function:
                    try:
                        image = analysis_ax.tricontourf(plot_x, plot_y, display_values, levels=48, cmap=cmap_name)
                        if style == "Interferogram":
                            analysis_ax.tricontour(plot_x, plot_y, display_values, levels=[0.5], colors="#2563eb", linewidths=0.45, alpha=0.65)
                    except Exception:
                        image = analysis_ax.scatter(plot_x, plot_y, c=display_values, cmap=cmap_name, s=22)

                if not is_wavefront_function:
                    analysis_ax.set_title(f"Wavefront: {style}")
                    analysis_ax.set_xlabel("X pupil")
                    analysis_ax.set_ylabel("Y pupil")
                    analysis_ax.set_aspect("equal", adjustable="box")
                    analysis_ax.set_box_aspect(0.72)
                    analysis_ax.grid(True, alpha=0.2)
                    analysis_ax.text(
                        0.98,
                        0.03,
                        metric_note,
                        transform=analysis_ax.transAxes,
                        ha="right",
                        va="bottom",
                        fontsize=7.5,
                        bbox={"facecolor": "white", "edgecolor": "#cbd5e1", "alpha": 0.78, "pad": 3},
                    )
                    analysis_ax.figure.colorbar(image, ax=analysis_ax, fraction=0.046, pad=0.04, label=colorbar_label)
                result_items = [
                    ("Mode", "Wavefront"),
                    ("Style", style),
                    ("Samples", str(int(phase.size))),
                    ("Phase method", phase_method),
                    ("Pupil coordinates", coordinate_note),
                    ("Phase P-V [waves]", f"{display_pv:.6g}"),
                    ("Phase RMS [waves]", f"{display_rms:.6g}"),
                    ("Display min", f"{float(np.nanmin(display_values)):.6g}" if style not in {"Slope X", "Slope Y", "Slope magnitude"} else "see slope map"),
                    ("Display max", f"{float(np.nanmax(display_values)):.6g}" if style not in {"Slope X", "Slope Y", "Slope magnitude"} else "see slope map"),
                ]
                if slope_rms is not None:
                    result_items.append(("Slope RMS", f"{slope_rms:.6g}"))
                if is_wavefront_function:
                    result_items.append(("Function reference", function_reference))
                    result_items.append(("Pupil quality", "OK" if function_quality_ok else function_quality_note))
                reference = self.editor.__dict__.get("_zemax_wavefront_reference", None)
                if zemax_comparison and bool(zemax_comparison.get("ok", False)):
                    result_items.extend(
                        [
                            ("Zemax WFM file", Path(str(zemax_comparison.get("reference_file", ""))).name),
                            ("Zemax WFM orientation", str(zemax_comparison.get("orientation", ""))),
                            ("Zemax residual RMS [waves]", f"{float(zemax_comparison.get('residual_rms_waves', 0.0)):.6g}"),
                            ("Zemax residual RMS [nm]", f"{float(zemax_comparison.get('residual_rms_nm', 0.0)):.6g}"),
                            ("Zemax residual P-V [waves]", f"{float(zemax_comparison.get('residual_pv_waves', 0.0)):.6g}"),
                        ]
                    )
                    wavelength_note = str(zemax_comparison.get("wavelength_note", "") or "").strip()
                    if wavelength_note:
                        result_items.append(("Zemax wavelength", wavelength_note))
                elif reference is not None and style in {WAVEFRONT_FUNCTION_STYLE, WAVEFRONT_PHASE_STYLE}:
                    result_items.append(("Zemax WFM compare", str((zemax_comparison or {}).get("reason", "unavailable"))))
                elif reference is not None:
                    result_items.append(("Zemax WFM compare", f"skipped for {style}"))
                if getattr(self, "results_table", None) is not None:
                    self._set_results(result_items)
                display_arr = np.asarray(display_values, dtype=float).ravel()
                if display_arr.shape != phase.shape:
                    display_arr = np.full_like(phase, np.nan, dtype=float)
                zemax_reference_arr = np.full_like(phase, np.nan, dtype=float)
                zemax_residual_arr = np.full_like(phase, np.nan, dtype=float)
                if zemax_comparison and bool(zemax_comparison.get("ok", False)):
                    reference_arr = np.asarray(zemax_comparison.get("reference_samples_waves", []), dtype=float).ravel()
                    residual_arr = np.asarray(zemax_comparison.get("residual_samples_waves", []), dtype=float).ravel()
                    if reference_arr.shape == phase.shape:
                        zemax_reference_arr = reference_arr
                    if residual_arr.shape == phase.shape:
                        zemax_residual_arr = residual_arr
                self._last_wavefront_samples = [
                    {
                        "sample": sample_index,
                        "x_pupil": float(x_value),
                        "y_pupil": float(y_value),
                        "phase_waves": float(phase_value),
                        "display_value": float(display_value) if np.isfinite(display_value) else "",
                        "zemax_reference_waves": float(zemax_reference_value) if np.isfinite(zemax_reference_value) else "",
                        "zemax_residual_waves": float(zemax_residual_value) if np.isfinite(zemax_residual_value) else "",
                        "zemax_reference_file": (
                            Path(str(zemax_comparison.get("reference_file", ""))).name
                            if zemax_comparison and bool(zemax_comparison.get("ok", False))
                            else ""
                        ),
                        "style": style,
                        "phase_method": phase_method,
                        "wavelength_um": float(wavelength),
                    }
                    for sample_index, (
                        x_value,
                        y_value,
                        phase_value,
                        display_value,
                        zemax_reference_value,
                        zemax_residual_value,
                    ) in enumerate(
                        zip(plot_x, plot_y, phase, display_arr, zemax_reference_arr, zemax_residual_arr)
                    )
                ]
                if zemax_comparison and bool(zemax_comparison.get("ok", False)):
                    self.append_debug(
                        "Zemax Wavefront Map comparison: file={file}, orientation={orientation}, "
                        "samples={samples}, residual_rms={rms:.6g} waves ({rms_nm:.6g} nm), "
                        "residual_pv={pv:.6g} waves".format(
                            file=Path(str(zemax_comparison.get("reference_file", ""))).name,
                            orientation=zemax_comparison.get("orientation", ""),
                            samples=int(zemax_comparison.get("sample_count", 0)),
                            rms=float(zemax_comparison.get("residual_rms_waves", 0.0)),
                            rms_nm=float(zemax_comparison.get("residual_rms_nm", 0.0)),
                            pv=float(zemax_comparison.get("residual_pv_waves", 0.0)),
                        )
                    )
                self.append_debug(
                    f"Wavefront ok: style={style}, samples={phase.size}, phase_rms={phase_rms:.6g}, "
                    f"phase_pv={phase_pv:.6g}, method={phase_method}"
                )
                self._update_analysis_progress("Rendering", 3, 3)
                self._finish_analysis_progress("Wavefront analysis", success=True)
            except Exception as exc:
                self.append_debug(f"Wavefront analysis error: {exc}")
                analysis_ax.clear()
                analysis_ax.text(0.5, 0.5, "Wavefront analysis unavailable", ha="center", va="center")
                analysis_ax.set_axis_off()
                self._finish_analysis_progress("Wavefront analysis", success=False)
            return

        if self.analysis_mode == "zernike":
            try:
                self._last_zernike_coefficients = []
                self._set_analysis_parallel_status("Zernike", 1, False)
                self._begin_analysis_progress("Zernike fit")
                self._update_analysis_progress("Building pupil", 1, 4)
                pupil = Kos.PupilCalc(
                    system,
                    self._analysis_surface_index(),
                    wavelength,
                    self._current_aperture_type(),
                    self._current_aperture_value(),
                )
                pupil.Samp = max(8, min(18, int(np.sqrt(max(1, self._current_ray_count())) * 4)))
                pupil.Ptype = "hexapolar"
                field_type = "angle" if self._current_object_mode() == "Infinity" else "height"
                pupil.FieldType = field_type
                pupil.FieldX = 0.0
                pupil.FieldY = self._current_field_angle_deg() if field_type == "angle" else self._current_field_height()

                self._update_analysis_progress("Computing phase", 2, 4)
                phase_method = "Phase2" if field_type == "height" else "Phase"
                if phase_method == "Phase2":
                    capture = io.StringIO()
                    with redirect_stdout(capture), redirect_stderr(capture):
                        px, py, phase, p2v = Kos.Phase2(pupil)
                    phase2_log = capture.getvalue().strip()
                    if phase2_log:
                        self.append_debug(phase2_log)
                else:
                    try:
                        px, py, phase, p2v = Kos.Phase(pupil)
                    except Exception:
                        capture = io.StringIO()
                        with redirect_stdout(capture), redirect_stderr(capture):
                            px, py, phase, p2v = Kos.Phase2(pupil)
                        phase_method = "Phase2"
                        phase2_log = capture.getvalue().strip()
                        if phase2_log:
                            self.append_debug(phase2_log)
                px = np.asarray(px, dtype=float).ravel()
                py = np.asarray(py, dtype=float).ravel()
                phase = np.asarray(phase, dtype=float).ravel()
                finite = np.isfinite(px) & np.isfinite(py) & np.isfinite(phase)
                px = px[finite]
                py = py[finite]
                phase = phase[finite]
                if px.size < 8:
                    raise RuntimeError("Not enough finite wavefront samples for Zernike fitting")
                if np.unique(np.round(px, 10)).size <= 1 or np.unique(np.round(py, 10)).size <= 1:
                    raise RuntimeError("Degenerate pupil sample for Zernike fitting")

                requested_terms = max(12, min(28, self._current_ray_count() + 8))
                candidate_terms = []
                for term_count in (requested_terms, 28, 21, 15, 10, 6, 4):
                    if 2 <= term_count < px.size and term_count not in candidate_terms:
                        candidate_terms.append(term_count)
                last_error = None
                fit_result = None
                self._update_analysis_progress("Fitting coefficients", 3, 4)
                for term_count in candidate_terms:
                    try:
                        coefficients, labels, rms_chief, rms_centroid, fitting_error = Kos.Zernike_Fitting(
                            px,
                            py,
                            phase,
                            np.ones(term_count, dtype=float),
                        )
                        fit_result = (term_count, coefficients, labels, rms_chief, rms_centroid, fitting_error)
                        break
                    except Exception as exc:
                        last_error = exc
                if fit_result is None:
                    raise RuntimeError(f"Zernike fit failed: {last_error}")

                term_count, coefficients, labels, rms_chief, rms_centroid, fitting_error = fit_result
                coefficients = np.asarray(coefficients, dtype=float).ravel()
                labels = np.asarray(labels, dtype=object).ravel()
                reconstructed = np.asarray(Kos.Wavefront_Zernike_Phase(px, py, coefficients), dtype=float).ravel()
                residual = phase - reconstructed
                phase_centered = phase - float(np.mean(phase))
                phase_rms = float(np.sqrt(np.mean(phase_centered * phase_centered)))
                residual_rms = float(np.sqrt(np.mean(residual * residual)))
                residual_pv = float(np.ptp(residual))
                phase_pv = float(np.ptp(phase))

                coeff_abs = np.abs(coefficients)
                min_visible = max(float(np.max(coeff_abs)) * 1e-4, 1e-12)
                nonzero = np.flatnonzero(coeff_abs > min_visible)
                aberration_nonzero = nonzero[nonzero >= 3]
                chart_note = ""
                if nonzero.size:
                    chart_pool = aberration_nonzero if aberration_nonzero.size else nonzero
                    chart_note = "Chart omits piston/tilt" if aberration_nonzero.size else "Chart includes low-order terms"
                    ranked = np.argsort(coeff_abs[chart_pool])[-10:][::-1]
                    shown_indices = chart_pool[ranked]
                else:
                    chart_note = "No non-zero terms above display threshold"
                    shown_indices = np.arange(min(coefficients.size, 10))
                shown_coefficients = coefficients[shown_indices]
                short_labels = []
                for index in shown_indices:
                    text = str(labels[index]) if index < labels.size else ""
                    descriptor = text.split("   ", 1)[-1].strip() if text else ""
                    if not descriptor:
                        descriptor = f"Z{int(index)}"
                    short_labels.append(f"Z{int(index):02d} {descriptor[:16]}")

                colors = ["#2563eb" if value >= 0.0 else "#dc2626" for value in shown_coefficients]
                y_pos = np.arange(shown_coefficients.size)
                analysis_ax.barh(y_pos, shown_coefficients, color=colors, alpha=0.88)
                analysis_ax.axvline(0.0, color="#111827", linewidth=0.8)
                analysis_ax.set_yticks(y_pos, short_labels)
                analysis_ax.invert_yaxis()
                analysis_ax.set_title(f"Zernike Fit  |  terms={term_count}  |  residual RMS={residual_rms:.4g} waves")
                analysis_ax.set_xlabel("Coefficient [waves]")
                analysis_ax.set_box_aspect(0.78)
                analysis_ax.grid(True, axis="x", alpha=0.2)
                analysis_ax.text(
                    0.98,
                    0.03,
                    f"Phase RMS {phase_rms:.4g} waves\n"
                    f"Phase P-V {phase_pv:.4g} waves\n"
                    f"Residual P-V {residual_pv:.4g} waves\n"
                    f"{chart_note}",
                    transform=analysis_ax.transAxes,
                    ha="right",
                    va="bottom",
                    fontsize=7.5,
                    bbox={"facecolor": "white", "edgecolor": "#cbd5e1", "alpha": 0.78, "pad": 3},
                )

                result_items = [
                    ("Mode", "Zernike fit"),
                    ("Terms", str(int(term_count))),
                    ("Samples", str(int(px.size))),
                    ("Phase method", phase_method),
                    ("Phase P-V [waves]", f"{phase_pv:.6g}"),
                    ("Phase RMS [waves]", f"{phase_rms:.6g}"),
                    ("Residual RMS [waves]", f"{residual_rms:.6g}"),
                    ("Residual P-V [waves]", f"{residual_pv:.6g}"),
                    ("RMS to chief [waves]", f"{float(rms_chief):.6g}"),
                    ("RMS to centroid [waves]", f"{float(rms_centroid):.6g}"),
                    ("Fitting error [waves]", f"{float(fitting_error):.6g}"),
                ]
                for index, coefficient in enumerate(coefficients):
                    text = str(labels[index]) if index < labels.size else ""
                    descriptor = text.split("   ", 1)[-1].strip() if text else f"Z{index}"
                    result_items.append((f"Z{index:02d} {descriptor}", f"{float(coefficient):.8g}"))
                if getattr(self, "results_table", None) is not None:
                    self._set_results(result_items)
                self._last_wavefront_fit_report = "\n".join(f"{key}\t{value}" for key, value in result_items)
                zernike_metrics = {
                    "terms": int(term_count),
                    "samples": int(px.size),
                    "phase_method": phase_method,
                    "phase_pv_waves": float(phase_pv),
                    "phase_rms_waves": float(phase_rms),
                    "residual_rms_waves": float(residual_rms),
                    "residual_pv_waves": float(residual_pv),
                    "rms_chief_waves": float(rms_chief),
                    "rms_centroid_waves": float(rms_centroid),
                    "fitting_error_waves": float(fitting_error),
                    "wavelength_um": float(wavelength),
                }
                self._last_zernike_coefficients = [
                    {
                        "index": int(index),
                        "label": str(labels[index]) if index < labels.size else f"Z{index}",
                        "coefficient_waves": float(coefficient),
                        **zernike_metrics,
                    }
                    for index, coefficient in enumerate(coefficients)
                ]
                self._last_wavefront_samples = [
                    {
                        "sample": int(sample_index),
                        "x_pupil": float(x_value),
                        "y_pupil": float(y_value),
                        "phase_waves": float(phase_value),
                        "reconstructed_waves": float(recon_value),
                        "residual_waves": float(residual_value),
                        "style": "Zernike fit",
                        "phase_method": phase_method,
                        "wavelength_um": float(wavelength),
                    }
                    for sample_index, (x_value, y_value, phase_value, recon_value, residual_value) in enumerate(
                        zip(px, py, phase, reconstructed, residual)
                    )
                ]
                self.append_debug(
                    f"Zernike fit ok: samples={px.size}, terms={term_count}, phase_rms={phase_rms:.6g}, "
                    f"residual_rms={residual_rms:.6g}, method={phase_method}"
                )
                self._update_analysis_progress("Rendering", 4, 4)
                self._finish_analysis_progress("Zernike fit", success=True)
            except Exception as exc:
                self._set_analysis_parallel_status("Zernike", 1, False)
                self.append_debug(f"Zernike fit error: {exc}")
                analysis_ax.clear()
                analysis_ax.text(0.5, 0.5, "Zernike fit unavailable", ha="center", va="center")
                analysis_ax.set_axis_off()
                self._finish_analysis_progress("Zernike fit", success=False)
            return

        if self.analysis_mode == "polarization":
            try:
                self._set_analysis_parallel_status("Polarization", 1, False)
                self._begin_analysis_progress("Polarization analysis")
                summary = self._polarization_summary(rays)
                surface_rows = list(summary.get("surface_rows", []))
                if not surface_rows:
                    raise RuntimeError("No raykeeper polarization data")

                labels = [f"S{int(row['surface'])}" for row in surface_rows]
                tp = np.asarray([np.nan if row["tp"] is None else float(row["tp"]) for row in surface_rows], dtype=float)
                ts = np.asarray([np.nan if row["ts"] is None else float(row["ts"]) for row in surface_rows], dtype=float)
                rp = np.asarray([np.nan if row["rp"] is None else float(row["rp"]) for row in surface_rows], dtype=float)
                rs = np.asarray([np.nan if row["rs"] is None else float(row["rs"]) for row in surface_rows], dtype=float)
                ttbe = np.asarray([np.nan if row["ttbe"] is None else float(row["ttbe"]) for row in surface_rows], dtype=float)
                x = np.arange(len(surface_rows), dtype=float)
                width = 0.34

                analysis_ax.bar(x - width / 2.0, tp, width=width, label="TP", color="#2563eb", alpha=0.82)
                analysis_ax.bar(x + width / 2.0, ts, width=width, label="TS", color="#f97316", alpha=0.82)
                if np.any(np.isfinite(rp)):
                    analysis_ax.plot(x, rp, label="RP", color="#1d4ed8", linestyle=(0, (3, 2)), linewidth=1.0, marker="o", markersize=3)
                if np.any(np.isfinite(rs)):
                    analysis_ax.plot(x, rs, label="RS", color="#c2410c", linestyle=(0, (3, 2)), linewidth=1.0, marker="s", markersize=3)
                if np.any(np.isfinite(ttbe)):
                    analysis_ax.plot(x, ttbe, label="TTBE", color="#111827", linewidth=1.25, marker="D", markersize=3)

                finite_chunks = [arr[np.isfinite(arr)] for arr in (tp, ts, rp, rs, ttbe) if np.any(np.isfinite(arr))]
                finite_values = np.concatenate(finite_chunks) if finite_chunks else np.empty(0, dtype=float)
                y_max = max(1.05, float(np.max(finite_values)) * 1.12) if finite_values.size else 1.05
                analysis_ax.set_ylim(0.0, y_max)
                analysis_ax.set_xticks(x, labels, rotation=30 if len(labels) > 7 else 0, ha="right" if len(labels) > 7 else "center")
                title_tt = self._format_percent_value(summary.get("image_mean_tt") or summary.get("mean_tt"))
                analysis_ax.set_title(f"Coating / Polarization  |  image TT {title_tt}")
                analysis_ax.set_ylabel("Energy fraction")
                analysis_ax.set_xlabel("Surface")
                analysis_ax.set_box_aspect(0.62)
                analysis_ax.grid(True, axis="y", alpha=0.2)
                analysis_ax.legend(loc="upper right", fontsize=7, ncol=2)
                self._finish_analysis_progress("Polarization analysis", success=True)
                self.append_debug(
                    "Polarization analysis ok: rays={rays}, image_rays={image}, mean_tt={tt}".format(
                        rays=int(summary["total_rays"]),
                        image=int(summary["image_rays"]),
                        tt=self._format_percent_value(summary["mean_tt"]),
                    )
                )
            except Exception as exc:
                self._set_analysis_parallel_status("Polarization", 1, False)
                self.append_debug(f"Polarization analysis error: {exc}")
                analysis_ax.text(0.5, 0.5, "Polarization analysis unavailable", ha="center", va="center")
                analysis_ax.set_axis_off()
                self._finish_analysis_progress("Polarization analysis", success=False)
            return

        if self.analysis_mode in ("field_curvature", "distortion"):
            # Field Curvature and Distortion are distinct concepts and render as
            # separate analysis items; both draw from one shared meridional scan.
            is_distortion = self.analysis_mode == "distortion"
            label = "Distortion" if is_distortion else "Field curvature"
            try:
                self._set_analysis_parallel_status(label, 1, True)
                self._begin_analysis_progress(label)
                sampled = self._sample_field_curvature_distortion(system, wavelength)
                if sampled is None:
                    raise RuntimeError("Not enough field samples for field-curvature/distortion")
                axis_results, field_type, field_limit = sampled
                if is_distortion:
                    self._plot_distortion_panel(analysis_ax, axis_results, field_type, field_limit, wavelength)
                else:
                    self._plot_field_curvature_panel(analysis_ax, axis_results, field_type, field_limit, wavelength)
                self.append_debug(
                    f"{label} ok: "
                    + ", ".join(
                        f"{axis}={len(data['fields'])},workers={int(data['workers'][0])}"
                        for axis, data in axis_results.items()
                    )
                )
                self._set_analysis_parallel_status(
                    label,
                    max(int(data["workers"][0]) for data in axis_results.values()),
                    True,
                )
                self._finish_analysis_progress(label, success=True)
            except Exception as exc:
                self._set_analysis_parallel_status(label, 1, True)
                self.append_debug(f"{label} error: {exc}")
                analysis_ax.text(0.5, 0.5, f"{label} unavailable", ha="center", va="center")
                analysis_ax.set_axis_off()
                self._finish_analysis_progress(label, success=False)
            return

        if self.analysis_mode == "field_map":
            try:
                self._set_analysis_parallel_status("Field map", 1, True)
                self._begin_analysis_progress("Field map")
                if self._current_source_model() != SOURCE_MODEL_DEFAULT:
                    analysis_ax.text(
                        0.5,
                        0.5,
                        "FieldMap uses Pupil / field sampling.\nSwitch Source model to Pupil / field.",
                        ha="center",
                        va="center",
                    )
                    analysis_ax.set_axis_off()
                    self._finish_analysis_progress("Field map", success=False)
                    return
                field_samples = self._resolved_field_grid_samples()
                if not field_samples:
                    raise RuntimeError("No valid field-map samples")
                sample_count = max(8, self._current_ray_count() * 2)
                total_steps = len(field_samples)
                rms_values: list[float] = []
                display_x: list[float] = []
                display_y: list[float] = []
                worker_max = 1
                for index, sample in enumerate(field_samples, start=1):
                    self._update_analysis_progress(f"Field map {index}/{total_steps}", index, total_steps)
                    x_local, y_local, _z_local, _l_local, _m_local, _n_local, worker_count = self._build_geometric_image_samples_full(
                        system,
                        wavelength,
                        sample_count=sample_count,
                        pattern="hexapolar",
                        surface_index=self._analysis_surface_index(),
                        aperture_type=self._current_aperture_type(),
                        aperture_value=self._current_aperture_value(),
                        field_type=str(sample["field_type"]),
                        field_x=float(sample["field_x"]),
                        field_y=float(sample["field_y"]),
                    )
                    worker_max = max(worker_max, int(worker_count))
                    x_centered, y_centered = self._center_image_plane_samples(x_local, y_local)
                    if x_centered.size < 2:
                        rms = np.nan
                    else:
                        rms = float(np.sqrt(np.mean((x_centered * x_centered) + (y_centered * y_centered))))
                    rms_values.append(rms)
                    display_x.append(float(sample["display_x"]))
                    display_y.append(float(sample["display_y"]))
                x_unique = np.asarray(sorted(set(round(value, 12) for value in display_x)), dtype=float)
                y_unique = np.asarray(sorted(set(round(value, 12) for value in display_y)), dtype=float)
                if x_unique.size == 0 or y_unique.size == 0:
                    raise RuntimeError("No valid field-map grid")
                grid = np.full((y_unique.size, x_unique.size), np.nan, dtype=float)
                x_lookup = {float(value): i for i, value in enumerate(x_unique)}
                y_lookup = {float(value): i for i, value in enumerate(y_unique)}
                for x_value, y_value, rms in zip(display_x, display_y, rms_values):
                    grid[y_lookup[round(float(y_value), 12)], x_lookup[round(float(x_value), 12)]] = rms
                if not np.any(np.isfinite(grid)):
                    raise RuntimeError("No finite field-map RMS values")
                if x_unique.size == 1:
                    x_extent = [float(x_unique[0]) - 0.5, float(x_unique[0]) + 0.5]
                else:
                    x_step = float(np.median(np.diff(x_unique)))
                    x_extent = [float(x_unique[0] - 0.5 * x_step), float(x_unique[-1] + 0.5 * x_step)]
                if y_unique.size == 1:
                    y_extent = [float(y_unique[0]) - 0.5, float(y_unique[0]) + 0.5]
                else:
                    y_step = float(np.median(np.diff(y_unique)))
                    y_extent = [float(y_unique[0] - 0.5 * y_step), float(y_unique[-1] + 0.5 * y_step)]
                cmap = colormaps.get_cmap("magma").copy()
                cmap.set_bad("#f3f4f6")
                im = analysis_ax.imshow(
                    grid,
                    origin="lower",
                    extent=[x_extent[0], x_extent[1], y_extent[0], y_extent[1]],
                    aspect="auto",
                    interpolation="nearest",
                    cmap=cmap,
                )
                analysis_ax.set_title("Wide-Field Spot RMS Map")
                unit = str(field_samples[0]["unit"])
                basis = str(field_samples[0]["basis"])
                label = f"{basis} [{unit}]" if unit else basis
                analysis_ax.set_xlabel(f"Field X: {label}")
                analysis_ax.set_ylabel(f"Field Y: {label}")
                cbar = analysis_ax.figure.colorbar(im, ax=analysis_ax, fraction=0.046, pad=0.04)
                cbar.set_label("Spot RMS [mm]")
                if grid.size <= 49:
                    for y_index, y_value in enumerate(y_unique):
                        for x_index, x_value in enumerate(x_unique):
                            value = grid[y_index, x_index]
                            if np.isfinite(value):
                                analysis_ax.text(
                                    float(x_value),
                                    float(y_value),
                                    f"{value:.3g}",
                                    ha="center",
                                    va="center",
                                    color="white",
                                    fontsize=7,
                                )
                analysis_ax.set_box_aspect(0.85)
                self.append_debug(
                    f"FieldMap ok: samples={len(field_samples)}, finite={int(np.isfinite(grid).sum())}, "
                    f"min={float(np.nanmin(grid)):.6g}, max={float(np.nanmax(grid)):.6g}, workers={worker_max}"
                )
                self._set_analysis_parallel_status("Field map", worker_max, True)
                self._finish_analysis_progress("Field map", success=True)
            except Exception as exc:
                self._set_analysis_parallel_status("Field map", 1, True)
                self.append_debug(f"FieldMap error: {exc}")
                analysis_ax.text(0.5, 0.5, "Field map unavailable", ha="center", va="center")
                analysis_ax.set_axis_off()
                self._finish_analysis_progress("Field map", success=False)
            return

        if self.analysis_mode == "illum_map":
            try:
                self._set_analysis_parallel_status("Illumination map", 1, True)
                self._begin_analysis_progress("Illumination map")
                if self._current_source_model() != SOURCE_MODEL_DEFAULT:
                    analysis_ax.text(
                        0.5,
                        0.5,
                        "IllumMap uses Pupil / field sampling.\nUse Illum for random-source throughput.",
                        ha="center",
                        va="center",
                    )
                    analysis_ax.set_axis_off()
                    self._finish_analysis_progress("Illumination map", success=False)
                    return
                field_samples = self._resolved_field_grid_samples()
                if not field_samples:
                    raise RuntimeError("No valid illumination-map samples")
                sample_count = max(8, self._current_ray_count() * 2)
                total_steps = len(field_samples)
                transmission_values: list[float] = []
                display_x: list[float] = []
                display_y: list[float] = []
                worker_max = 1
                for index, sample in enumerate(field_samples, start=1):
                    self._update_analysis_progress(f"Illum map {index}/{total_steps}", index, total_steps)
                    pupil = Kos.PupilCalc(
                        system,
                        self._analysis_surface_index(),
                        wavelength,
                        self._current_aperture_type(),
                        self._current_aperture_value(),
                    )
                    pupil.Samp = sample_count
                    pupil.Ptype = self._current_analysis_pupil_pattern()
                    pupil.FieldType = str(sample["field_type"])
                    pupil.FieldX = float(sample["field_x"])
                    pupil.FieldY = float(sample["field_y"])
                    bundle = self._pupil_pattern_bundle(pupil)
                    input_count = int(np.asarray(bundle[0]).size)
                    if input_count <= 0:
                        transmission = np.nan
                    else:
                        x_local, _y_local, worker_count = self._trace_pattern_chunks_parallel(wavelength, [bundle])
                        worker_max = max(worker_max, int(worker_count))
                        transmission = float(np.asarray(x_local).size) / float(input_count)
                    transmission_values.append(transmission)
                    display_x.append(float(sample["display_x"]))
                    display_y.append(float(sample["display_y"]))
                x_unique = np.asarray(sorted(set(round(value, 12) for value in display_x)), dtype=float)
                y_unique = np.asarray(sorted(set(round(value, 12) for value in display_y)), dtype=float)
                if x_unique.size == 0 or y_unique.size == 0:
                    raise RuntimeError("No valid illumination-map grid")
                grid = np.full((y_unique.size, x_unique.size), np.nan, dtype=float)
                x_lookup = {float(value): i for i, value in enumerate(x_unique)}
                y_lookup = {float(value): i for i, value in enumerate(y_unique)}
                for x_value, y_value, transmission in zip(display_x, display_y, transmission_values):
                    grid[y_lookup[round(float(y_value), 12)], x_lookup[round(float(x_value), 12)]] = transmission
                finite = grid[np.isfinite(grid)]
                if finite.size == 0:
                    raise RuntimeError("No finite illumination-map values")
                center_index = int(np.nanargmin(np.asarray(display_x) ** 2 + np.asarray(display_y) ** 2))
                reference = transmission_values[center_index] if center_index < len(transmission_values) else np.nan
                if not np.isfinite(reference) or float(reference) <= 1e-12:
                    reference = float(np.nanmax(grid))
                if not np.isfinite(reference) or float(reference) <= 1e-12:
                    raise RuntimeError("No valid illumination reference")
                grid = grid / float(reference)
                if x_unique.size == 1:
                    x_extent = [float(x_unique[0]) - 0.5, float(x_unique[0]) + 0.5]
                else:
                    x_step = float(np.median(np.diff(x_unique)))
                    x_extent = [float(x_unique[0] - 0.5 * x_step), float(x_unique[-1] + 0.5 * x_step)]
                if y_unique.size == 1:
                    y_extent = [float(y_unique[0]) - 0.5, float(y_unique[0]) + 0.5]
                else:
                    y_step = float(np.median(np.diff(y_unique)))
                    y_extent = [float(y_unique[0] - 0.5 * y_step), float(y_unique[-1] + 0.5 * y_step)]
                cmap = colormaps.get_cmap("viridis").copy()
                cmap.set_bad("#f3f4f6")
                im = analysis_ax.imshow(
                    grid,
                    origin="lower",
                    extent=[x_extent[0], x_extent[1], y_extent[0], y_extent[1]],
                    aspect="auto",
                    interpolation="nearest",
                    cmap=cmap,
                    vmin=0.0,
                    vmax=max(1.0, float(np.nanmax(grid))),
                )
                analysis_ax.set_title("Wide-Field Relative Illumination Map")
                unit = str(field_samples[0]["unit"])
                basis = str(field_samples[0]["basis"])
                label = f"{basis} [{unit}]" if unit else basis
                analysis_ax.set_xlabel(f"Field X: {label}")
                analysis_ax.set_ylabel(f"Field Y: {label}")
                cbar = analysis_ax.figure.colorbar(im, ax=analysis_ax, fraction=0.046, pad=0.04)
                cbar.set_label("Relative illumination")
                if grid.size <= 49:
                    for y_index, y_value in enumerate(y_unique):
                        for x_index, x_value in enumerate(x_unique):
                            value = grid[y_index, x_index]
                            if np.isfinite(value):
                                analysis_ax.text(
                                    float(x_value),
                                    float(y_value),
                                    f"{value:.3g}",
                                    ha="center",
                                    va="center",
                                    color="white",
                                    fontsize=7,
                                )
                analysis_ax.set_box_aspect(0.85)
                self.append_debug(
                    f"IllumMap ok: samples={len(field_samples)}, finite={int(np.isfinite(grid).sum())}, "
                    f"min={float(np.nanmin(grid)):.6g}, max={float(np.nanmax(grid)):.6g}, workers={worker_max}"
                )
                self._set_analysis_parallel_status("Illumination map", worker_max, True)
                self._finish_analysis_progress("Illumination map", success=True)
            except Exception as exc:
                self._set_analysis_parallel_status("Illumination map", 1, True)
                self.append_debug(f"IllumMap error: {exc}")
                analysis_ax.text(0.5, 0.5, "Illumination map unavailable", ha="center", va="center")
                analysis_ax.set_axis_off()
                self._finish_analysis_progress("Illumination map", success=False)
            return

        if self.analysis_mode == "wavefront_map":
            try:
                self._set_analysis_parallel_status("Wavefront map", 1, True)
                self._begin_analysis_progress("Wavefront map")
                if self._current_source_model() != SOURCE_MODEL_DEFAULT:
                    analysis_ax.text(
                        0.5,
                        0.5,
                        "WfeMap uses Pupil / field sampling.\nSwitch Source model to Pupil / field.",
                        ha="center",
                        va="center",
                    )
                    analysis_ax.set_axis_off()
                    self._finish_analysis_progress("Wavefront map", success=False)
                    return
                field_samples = self._resolved_field_grid_samples()
                if not field_samples:
                    raise RuntimeError("No valid wavefront-map samples")
                total_steps = len(field_samples)
                wfe_values: list[float] = []
                display_x: list[float] = []
                display_y: list[float] = []

                def _phase_arrays_for_sample(sample: dict[str, float | str]):
                    pupil = Kos.PupilCalc(
                        system,
                        self._analysis_surface_index(),
                        wavelength,
                        self._current_aperture_type(),
                        self._current_aperture_value(),
                    )
                    pupil.Samp = max(5, min(11, self._current_ray_count()))
                    pupil.Ptype = "hexapolar"
                    pupil.FieldType = str(sample["field_type"])
                    pupil.FieldX = float(sample["field_x"])
                    pupil.FieldY = float(sample["field_y"])
                    phase_method = "Phase2" if str(sample["field_type"]).strip().lower() == "height" else "Phase"
                    if phase_method == "Phase2":
                        capture = io.StringIO()
                        with redirect_stdout(capture), redirect_stderr(capture):
                            px, py, phase, _p2v = Kos.Phase2(pupil)
                        phase2_log = capture.getvalue().strip()
                        if phase2_log:
                            self.append_debug(phase2_log)
                    else:
                        try:
                            px, py, phase, _p2v = Kos.Phase(pupil)
                        except Exception:
                            capture = io.StringIO()
                            with redirect_stdout(capture), redirect_stderr(capture):
                                px, py, phase, _p2v = Kos.Phase2(pupil)
                            phase2_log = capture.getvalue().strip()
                            if phase2_log:
                                self.append_debug(phase2_log)
                    phase = np.asarray(phase, dtype=float).ravel()
                    return phase[np.isfinite(phase)]

                for index, sample in enumerate(field_samples, start=1):
                    self._update_analysis_progress(f"Wavefront map {index}/{total_steps}", index, total_steps)
                    try:
                        phase = _phase_arrays_for_sample(sample)
                        if phase.size < 3:
                            rms = np.nan
                        else:
                            centered = phase - float(np.mean(phase))
                            rms = float(np.sqrt(np.mean(centered * centered)))
                    except Exception as exc:
                        self.append_debug(f"WfeMap sample failed at ({sample['display_x']}, {sample['display_y']}): {exc}")
                        rms = np.nan
                    wfe_values.append(rms)
                    display_x.append(float(sample["display_x"]))
                    display_y.append(float(sample["display_y"]))
                x_unique = np.asarray(sorted(set(round(value, 12) for value in display_x)), dtype=float)
                y_unique = np.asarray(sorted(set(round(value, 12) for value in display_y)), dtype=float)
                if x_unique.size == 0 or y_unique.size == 0:
                    raise RuntimeError("No valid wavefront-map grid")
                grid = np.full((y_unique.size, x_unique.size), np.nan, dtype=float)
                x_lookup = {float(value): i for i, value in enumerate(x_unique)}
                y_lookup = {float(value): i for i, value in enumerate(y_unique)}
                for x_value, y_value, rms in zip(display_x, display_y, wfe_values):
                    grid[y_lookup[round(float(y_value), 12)], x_lookup[round(float(x_value), 12)]] = rms
                finite = grid[np.isfinite(grid)]
                if finite.size == 0:
                    raise RuntimeError("No finite wavefront-map values")
                if x_unique.size == 1:
                    x_extent = [float(x_unique[0]) - 0.5, float(x_unique[0]) + 0.5]
                else:
                    x_step = float(np.median(np.diff(x_unique)))
                    x_extent = [float(x_unique[0] - 0.5 * x_step), float(x_unique[-1] + 0.5 * x_step)]
                if y_unique.size == 1:
                    y_extent = [float(y_unique[0]) - 0.5, float(y_unique[0]) + 0.5]
                else:
                    y_step = float(np.median(np.diff(y_unique)))
                    y_extent = [float(y_unique[0] - 0.5 * y_step), float(y_unique[-1] + 0.5 * y_step)]
                cmap = colormaps.get_cmap("cividis").copy()
                cmap.set_bad("#f3f4f6")
                im = analysis_ax.imshow(
                    grid,
                    origin="lower",
                    extent=[x_extent[0], x_extent[1], y_extent[0], y_extent[1]],
                    aspect="auto",
                    interpolation="nearest",
                    cmap=cmap,
                )
                analysis_ax.set_title("Wide-Field Wavefront RMS Map")
                unit = str(field_samples[0]["unit"])
                basis = str(field_samples[0]["basis"])
                label = f"{basis} [{unit}]" if unit else basis
                analysis_ax.set_xlabel(f"Field X: {label}")
                analysis_ax.set_ylabel(f"Field Y: {label}")
                cbar = analysis_ax.figure.colorbar(im, ax=analysis_ax, fraction=0.046, pad=0.04)
                cbar.set_label("Wavefront RMS [waves]")
                if grid.size <= 49:
                    for y_index, y_value in enumerate(y_unique):
                        for x_index, x_value in enumerate(x_unique):
                            value = grid[y_index, x_index]
                            if np.isfinite(value):
                                analysis_ax.text(
                                    float(x_value),
                                    float(y_value),
                                    f"{value:.3g}",
                                    ha="center",
                                    va="center",
                                    color="white",
                                    fontsize=7,
                                )
                analysis_ax.set_box_aspect(0.85)
                self.append_debug(
                    f"WfeMap ok: samples={len(field_samples)}, finite={int(np.isfinite(grid).sum())}, "
                    f"min={float(np.nanmin(grid)):.6g}, max={float(np.nanmax(grid)):.6g}"
                )
                self._set_analysis_parallel_status("Wavefront map", 1, True)
                self._finish_analysis_progress("Wavefront map", success=True)
            except Exception as exc:
                self._set_analysis_parallel_status("Wavefront map", 1, True)
                self.append_debug(f"WfeMap error: {exc}")
                analysis_ax.text(0.5, 0.5, "Wavefront map unavailable", ha="center", va="center")
                analysis_ax.set_axis_off()
                self._finish_analysis_progress("Wavefront map", success=False)
            return

        if self.analysis_mode == "relative_illumination":
            try:
                self._set_analysis_parallel_status("Relative illumination", 1, True)
                self._begin_analysis_progress("Relative illumination")
                if self._normalize_scene_source_specs(getattr(self, "layout_scene_source_specs", [])):
                    self._update_analysis_progress("Building source illumination map", 1, 2)
                    self._plot_source_illumination_map_analysis(
                        analysis_ax,
                        system,
                        ray_records=current_trace_ray_records(),
                    )
                    self._update_analysis_progress("Rendering", 2, 2)
                    self._finish_analysis_progress("Relative illumination", success=True)
                    return
                if self._current_source_model() != SOURCE_MODEL_DEFAULT:
                    sample_count = max(24, self._current_ray_count() * 4)
                    wavelength_ri = 0.46
                    self._update_analysis_progress("Tracing random source", 1, 2)
                    bundle = self._build_random_source_bundle(sample_count)
                    if bundle is None:
                        raise RuntimeError("Random source bundle unavailable")
                    input_count = int(np.asarray(bundle[0]).size)
                    if input_count <= 0:
                        raise RuntimeError("No random source rays")
                    x_local, _y_local, worker_count = self._trace_pattern_chunks_parallel(wavelength_ri, [bundle])
                    output_count = int(np.asarray(x_local).size)
                    transmission = float(output_count) / float(input_count)
                    stats = self._source_statistics(input_count)
                    source_power = float(stats.get("power", 0.0))
                    collected_power = source_power * transmission
                    analysis_ax.bar(
                        ["Image plane"],
                        [transmission],
                        color="#111827",
                        width=0.5,
                    )
                    analysis_ax.set_title("Random Source Illumination")
                    analysis_ax.set_ylabel("Transmission")
                    analysis_ax.set_ylim(0.0, max(1.05, transmission * 1.1))
                    analysis_ax.grid(True, axis="y", alpha=0.2)
                    analysis_ax.text(
                        0.03,
                        0.94,
                        (
                            f"Input rays: {input_count}\n"
                            f"Image rays: {output_count}\n"
                            f"Source power: {source_power:.6g}\n"
                            f"Collected power: {collected_power:.6g}\n"
                            f"Power/ray: {float(stats.get('power_per_ray', 0.0)):.6g}"
                        ),
                        transform=analysis_ax.transAxes,
                        va="top",
                        ha="left",
                        fontsize=8,
                        bbox={
                            "boxstyle": "round,pad=0.35",
                            "facecolor": "white",
                            "edgecolor": "#d1d5db",
                            "alpha": 0.92,
                        },
                    )
                    self._update_analysis_progress("Random source illumination complete", 2, 2)
                    self.append_debug(
                        "Random source illumination ok: "
                        f"input={input_count}, image={output_count}, transmission={transmission:.6g}, "
                        f"source_power={source_power:.6g}, collected_power={collected_power:.6g}, workers={int(worker_count)}"
                    )
                    self._set_analysis_parallel_status("Relative illumination", int(worker_count), True)
                    self._finish_analysis_progress("Relative illumination", success=True)
                    return
                field_samples = self._resolved_positive_field_samples()
                if not field_samples:
                    raise RuntimeError("No valid field samples")
                sample_count = max(24, self._current_ray_count() * 4)
                wavelength_ri = 0.46
                illum_x: list[float] = []
                illum_y: list[float] = []
                worker_max = 1
                total_steps = len(field_samples)
                reference = None
                for index, sample in enumerate(field_samples, start=1):
                    self._update_analysis_progress(
                        f"Illumination field {index}/{len(field_samples)}",
                        index,
                        total_steps,
                    )
                    pupil = Kos.PupilCalc(
                        system,
                        self._analysis_surface_index(),
                        wavelength_ri,
                        self._current_aperture_type(),
                        self._current_aperture_value(),
                    )
                    pupil.Samp = sample_count
                    pupil.Ptype = self._current_analysis_pupil_pattern()
                    pupil.FieldType = str(sample["field_type"])
                    pupil.FieldX = float(sample["field_x"])
                    pupil.FieldY = float(sample["field_y"])
                    bundle = self._pupil_pattern_bundle(pupil)
                    input_count = int(np.asarray(bundle[0]).size)
                    if input_count <= 0:
                        continue
                    x_local, y_local, worker_count = self._trace_pattern_chunks_parallel(wavelength_ri, [bundle])
                    worker_max = max(worker_max, int(worker_count))
                    transmission = float(x_local.size) / float(input_count)
                    if reference is None:
                        reference = max(transmission, 1e-12)
                    rel = transmission / max(reference, 1e-12)
                    illum_x.append(float(sample["display_y"]))
                    illum_y.append(float(rel))
                if not illum_x:
                    raise RuntimeError("No relative illumination samples")
                analysis_ax.plot(illum_x, illum_y, color="#111827", linewidth=1.8, marker="o", markersize=4.0)
                if len(illum_x) >= 4:
                    smooth_x = np.linspace(float(min(illum_x)), float(max(illum_x)), 200)
                    deg = min(3, len(illum_x) - 1)
                    try:
                        poly = np.poly1d(np.polyfit(illum_x, illum_y, deg=deg))
                        analysis_ax.plot(smooth_x, np.clip(poly(smooth_x), 0.0, 1.05), color="#374151", linewidth=1.2, alpha=0.85)
                    except Exception:
                        pass
                basis = str(field_samples[0]["basis"])
                unit = str(field_samples[0]["unit"])
                analysis_ax.set_title("Relative Illumination")
                analysis_ax.set_xlabel(f"{basis} [{unit}]".strip())
                analysis_ax.set_ylabel("Relative illumination")
                analysis_ax.set_ylim(0.0, 1.05)
                analysis_ax.set_box_aspect(0.48)
                analysis_ax.grid(True, alpha=0.2)
                self.append_debug(
                    f"Relative illumination ok: samples={len(illum_x)}, wavelength={wavelength_ri:.3f} um, workers={worker_max}"
                )
                self._set_analysis_parallel_status("Relative illumination", worker_max, True)
                self._finish_analysis_progress("Relative illumination", success=True)
            except Exception as exc:
                self._set_analysis_parallel_status("Relative illumination", 1, True)
                self.append_debug(f"Relative illumination error: {exc}")
                analysis_ax.text(0.5, 0.5, "Relative illumination unavailable", ha="center", va="center")
                analysis_ax.set_axis_off()
                self._finish_analysis_progress("Relative illumination", success=False)
            return

        if self.analysis_mode == "lateral_color":
            try:
                self._set_analysis_parallel_status("Lateral color", 1, True)
                self._begin_analysis_progress("Lateral color")
                field_samples = self._resolved_positive_field_samples()
                if not field_samples:
                    raise RuntimeError("No valid field samples")
                wavelengths = [0.64, 0.546, 0.46]
                reference_wavelength = 0.546
                sample_count = max(20, self._current_ray_count() * 3)
                color_map = {0.64: "#d62728", 0.546: "#2ca02c", 0.46: "#1f77b4"}
                series: dict[float, tuple[list[float], list[float]]] = {wl: ([], []) for wl in wavelengths}
                worker_max = 1
                total_steps = len(field_samples) * len(wavelengths)
                done = 0
                for sample in field_samples:
                    centroids: dict[float, tuple[float, float]] = {}
                    for wl in wavelengths:
                        done += 1
                        self._update_analysis_progress(
                            f"Lateral color {done}/{total_steps}",
                            done,
                            total_steps,
                        )
                        x_local, y_local, _z, _l, _m, _n, worker_count = self._build_geometric_image_samples_full(
                            system,
                            wl,
                            sample_count=sample_count,
                            pattern="hexapolar",
                            surface_index=self._analysis_surface_index(),
                            aperture_type=self._current_aperture_type(),
                            aperture_value=self._current_aperture_value(),
                            field_type=str(sample["field_type"]),
                            field_x=float(sample["field_x"]),
                            field_y=float(sample["field_y"]),
                        )
                        worker_max = max(worker_max, int(worker_count))
                        if x_local.size < 3:
                            continue
                        centroids[wl] = (float(np.mean(x_local)), float(np.mean(y_local)))
                    if reference_wavelength not in centroids:
                        continue
                    ref_x, ref_y = centroids[reference_wavelength]
                    field_value = float(sample["display_y"])
                    for wl in wavelengths:
                        if wl not in centroids:
                            continue
                        cx, cy = centroids[wl]
                        delta_um = 1000.0 * float(np.hypot(cx - ref_x, cy - ref_y))
                        series[wl][0].append(field_value)
                        series[wl][1].append(delta_um)
                plotted = 0
                for wl in wavelengths:
                    x_vals, y_vals = series[wl]
                    if not x_vals:
                        continue
                    plotted += 1
                    analysis_ax.plot(
                        x_vals,
                        y_vals,
                        color=color_map[wl],
                        linewidth=1.5,
                        marker="o",
                        markersize=3.8,
                        label=f"{wl:.3f} um",
                    )
                if plotted == 0:
                    raise RuntimeError("No lateral color samples")
                basis = str(field_samples[0]["basis"])
                unit = str(field_samples[0]["unit"])
                analysis_ax.set_title("Lateral Color")
                analysis_ax.set_xlabel(f"{basis} [{unit}]".strip())
                analysis_ax.set_ylabel("Lateral color vs 0.546 um [um]")
                analysis_ax.set_box_aspect(0.48)
                analysis_ax.grid(True, alpha=0.2)
                analysis_ax.legend(loc="best", fontsize=8)
                self.append_debug(
                    f"Lateral color ok: fields={len(field_samples)}, wavelengths={len(wavelengths)}, workers={worker_max}"
                )
                self._set_analysis_parallel_status("Lateral color", worker_max, True)
                self._finish_analysis_progress("Lateral color", success=True)
            except Exception as exc:
                self._set_analysis_parallel_status("Lateral color", 1, True)
                self.append_debug(f"Lateral color error: {exc}")
                analysis_ax.text(0.5, 0.5, "Lateral color unavailable", ha="center", va="center")
                analysis_ax.set_axis_off()
                self._finish_analysis_progress("Lateral color", success=False)
            return

        if self.analysis_mode == "mtf":
            try:
                self._set_analysis_parallel_status("MTF", 1, True)
                self._begin_analysis_progress("MTF analysis")
                mtf_settings = self._mtf_analysis_settings()
                wavelength = float(mtf_settings["wavelength"])
                mtf_mode = self._operand_mtf_mode("MTF @ freq")
                mtf_algorithm = str(mtf_settings.get("algorithm", "psf_fft"))
                target_freq = self._current_mtf_frequency()
                field_samples = self._resolved_mtf_field_samples("MTF @ freq")
                if not field_samples:
                    raise RuntimeError("No valid MTF field samples")

                sample_results: list[dict[str, object]] = []
                max_workers = 1
                accelerators: set[str] = set()
                geometric_pending: list[tuple[dict[str, float | str], str]] = []
                total_steps = max(2, len(field_samples) + 1)
                for index, sample in enumerate(field_samples, start=1):
                    legend = str(sample["legend"])
                    self._update_analysis_progress(
                        f"MTF field {index}/{len(field_samples)}: {legend}",
                        index,
                        total_steps,
                    )
                    if mtf_algorithm != "diffraction_fft":
                        geometric_pending.append((sample, legend))
                        continue
                    try:
                        result = self._compute_diffraction_mtf_sample(
                            system,
                            wavelength=wavelength,
                            surface_index=int(mtf_settings["surface_index"]),
                            aperture_type=str(mtf_settings["aperture_type"]),
                            aperture_value=float(mtf_settings["aperture_value"]),
                            field_type=str(sample["field_type"]),
                            field_x=float(sample["field_x"]),
                            field_y=float(sample["field_y"]),
                        )
                        self.append_debug(
                            f"MTF sample {legend}: diffraction ok: method={result.get('phase_method', 'Phase')}, terms={result['used_terms']}, samples={result['sample_count']}"
                        )
                    except Exception as diff_exc:
                        self.append_debug(f"MTF sample {legend}: diffraction failed: {diff_exc}")
                        geometric_pending.append((sample, legend))
                        continue

                    plot_freq = np.asarray(result["plot_freq"], dtype=float)
                    plot_tan = np.asarray(result["plot_tan"], dtype=float)
                    plot_sag = np.asarray(result["plot_sag"], dtype=float)
                    if plot_freq.size == 0 or plot_tan.size == 0 or plot_sag.size == 0:
                        continue

                    tan_value = float(np.interp(target_freq, plot_freq, plot_tan, left=plot_tan[0], right=plot_tan[-1]))
                    sag_value = float(np.interp(target_freq, plot_freq, plot_sag, left=plot_sag[0], right=plot_sag[-1]))
                    if mtf_mode == "tangential":
                        selected_value = tan_value
                        selected_label = "Tangential"
                    elif mtf_mode == "sagittal":
                        selected_value = sag_value
                        selected_label = "Sagittal"
                    else:
                        selected_value = 0.5 * (tan_value + sag_value)
                        selected_label = "Average"

                    result.update(
                        {
                            "legend": legend,
                            "basis": str(sample["basis"]),
                            "unit": str(sample["unit"]),
                            "display_x": float(sample["display_x"]),
                            "display_y": float(sample["display_y"]),
                            "tan_value": tan_value,
                            "sag_value": sag_value,
                            "selected_value": float(selected_value),
                            "selected_label": selected_label,
                        }
                    )
                    sample_results.append(result)
                    max_workers = max(max_workers, int(result.get("worker_count", 1)))
                    accelerators.add(str(result.get("accelerator", "CPU")))

                if geometric_pending:
                    geometric_samples = [item[0] for item in geometric_pending]
                    dense_count = max(24, self._current_ray_count() * 6)
                    geometric_results, geometric_workers = self._build_geometric_image_samples_for_field_samples(
                        wavelength,
                        sample_count=dense_count,
                        pattern="hexapolar",
                        surface_index=int(mtf_settings["surface_index"]),
                        aperture_type=str(mtf_settings["aperture_type"]),
                        aperture_value=float(mtf_settings["aperture_value"]),
                        field_samples=geometric_samples,
                    )
                    max_workers = max(max_workers, int(geometric_workers))
                    for (sample, legend), (x_local, y_local) in zip(geometric_pending, geometric_results):
                        try:
                            result = self._geometric_mtf_result_from_image_samples(
                                x_local,
                                y_local,
                                worker_count=int(geometric_workers),
                                sample_count=int(dense_count),
                                algorithm=mtf_algorithm,
                            )
                            self.append_debug(
                                "MTF sample {legend}: geometric ok: rays={rays}, pupil_samp={pupil_samp}, workers={workers}, accel={accel}".format(
                                    legend=legend,
                                    rays=int(result["sample_count"]),
                                    pupil_samp=int(result.get("pupil_samp", 0)),
                                    workers=int(result["worker_count"]),
                                    accel=str(result["accelerator"]),
                                )
                            )
                        except Exception as geom_exc:
                            self.append_debug(f"MTF sample {legend}: geometric failed: {geom_exc}")
                            continue

                        plot_freq = np.asarray(result["plot_freq"], dtype=float)
                        plot_tan = np.asarray(result["plot_tan"], dtype=float)
                        plot_sag = np.asarray(result["plot_sag"], dtype=float)
                        if plot_freq.size == 0 or plot_tan.size == 0 or plot_sag.size == 0:
                            continue

                        tan_value = float(np.interp(target_freq, plot_freq, plot_tan, left=plot_tan[0], right=plot_tan[-1]))
                        sag_value = float(np.interp(target_freq, plot_freq, plot_sag, left=plot_sag[0], right=plot_sag[-1]))
                        if mtf_mode == "tangential":
                            selected_value = tan_value
                            selected_label = "Tangential"
                        elif mtf_mode == "sagittal":
                            selected_value = sag_value
                            selected_label = "Sagittal"
                        else:
                            selected_value = 0.5 * (tan_value + sag_value)
                            selected_label = "Average"

                        result.update(
                            {
                                "legend": legend,
                                "basis": str(sample["basis"]),
                                "unit": str(sample["unit"]),
                                "display_x": float(sample["display_x"]),
                                "display_y": float(sample["display_y"]),
                                "tan_value": tan_value,
                                "sag_value": sag_value,
                                "selected_value": float(selected_value),
                                "selected_label": selected_label,
                            }
                        )
                        sample_results.append(result)
                        accelerators.add(str(result.get("accelerator", "CPU")))

                if not sample_results:
                    raise RuntimeError("MTF analysis unavailable for all selected field samples")
                sample_results.sort(key=lambda result: float(result.get("display_y", 0.0)))

                colors = self._field_colors(len(sample_results))
                max_plot_freq = 0.0
                label_specs: list[dict[str, object]] = []
                for color, result in zip(colors, sample_results):
                    plot_freq = np.asarray(result["plot_freq"], dtype=float)
                    plot_tan = np.asarray(result["plot_tan"], dtype=float)
                    plot_sag = np.asarray(result["plot_sag"], dtype=float)
                    max_plot_freq = max(max_plot_freq, float(plot_freq[-1]))
                    legend = str(result["legend"])
                    overlap = bool(
                        np.allclose(
                            plot_tan,
                            plot_sag,
                            rtol=1e-3,
                            atol=max(1e-4, 5e-3 * float(max(np.max(np.abs(plot_tan)), np.max(np.abs(plot_sag)), 1e-9))),
                        )
                    )
                    result["ts_overlap"] = overlap
                    if overlap:
                        analysis_ax.plot(
                            plot_freq,
                            plot_tan,
                            label=f"T=S {legend}",
                            color=color,
                            linewidth=1.1,
                            alpha=1.0,
                            linestyle="-",
                            zorder=3,
                        )
                        label_specs.append(
                            {
                                "label": f"T=S {legend}",
                                "curve_x": plot_freq,
                                "curve_y": plot_tan,
                                "color": color,
                                "linestyle": (0, (2, 2)),
                            }
                        )
                    else:
                        analysis_ax.plot(
                            plot_freq,
                            plot_tan,
                            label=f"T {legend}",
                            color=color,
                            linewidth=1.1,
                            alpha=1.0,
                            linestyle="-",
                            zorder=3,
                        )
                        analysis_ax.plot(
                            plot_freq,
                            plot_sag,
                            label=f"S {legend}",
                            color=color,
                            linewidth=1.0,
                            alpha=1.0,
                            linestyle=(0, (6, 3)),
                            zorder=4,
                        )
                        label_specs.extend(
                            [
                                {
                                    "label": f"T {legend}",
                                    "curve_x": plot_freq,
                                    "curve_y": plot_tan,
                                    "color": color,
                                    "linestyle": (0, (2, 2)),
                                },
                                {
                                    "label": f"S {legend}",
                                    "curve_x": plot_freq,
                                    "curve_y": plot_sag,
                                    "color": color,
                                    "linestyle": (0, (1, 2)),
                                },
                            ]
                        )
                analysis_ax.plot(
                    [target_freq, target_freq],
                    [0.0, 0.08],
                    color="#2c3e50",
                    linewidth=0.9,
                    linestyle="-",
                    alpha=0.9,
                    zorder=1.8,
                )
                analysis_ax.text(
                    target_freq,
                    0.085,
                    f"ref {target_freq:.1f}",
                    ha="center",
                    va="bottom",
                    fontsize=6.5,
                    color="#2c3e50",
                    bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.45, "pad": 0.2},
                )
                basis = str(sample_results[0]["basis"])
                unit = str(sample_results[0]["unit"])
                x_text = self._format_field_sample_value(float(sample_results[0]["display_x"]))
                method_label = str(sample_results[0].get("method", "MTF"))
                dl_fc = None
                x_limit_upper = max_plot_freq if max_plot_freq > 0.0 else max(10.0, target_freq * 2.5)
                if method_label.lower().startswith("geometric"):
                    if target_freq > 0.0:
                        # Geometric PSF/LSF MTF can report a very high FFT limit
                        # once the spot is tight. Keep the UI centered on the
                        # user's reference frequency instead of compressing the
                        # useful part of the curve against the y-axis.
                        x_limit_upper = max(target_freq * 2.5, min(max_plot_freq, target_freq * 4.0))
                else:
                    try:
                        effl, _ppa, _ppp = self._exact_paraxial_cardinals(wavelength)
                        pupil_ref = Kos.PupilCalc(
                            system,
                            int(mtf_settings["surface_index"]),
                            wavelength,
                            str(mtf_settings["aperture_type"]),
                            float(mtf_settings["aperture_value"]),
                        )
                        ep_diameter = max(2.0 * abs(float(getattr(pupil_ref, "RadPupInp", 0.0))), 1e-9)
                        f_number = abs(float(effl)) / ep_diameter
                        if np.isfinite(f_number) and f_number > 1e-12:
                            dl_fc = 1.0 / (max(wavelength, 1e-12) * 1e-3 * f_number)
                            if np.isfinite(dl_fc) and dl_fc > 0.0:
                                x_limit_upper = max(target_freq * 1.1, float(dl_fc) * 1.02)
                                dl_freq = np.linspace(0.0, x_limit_upper, 512)
                                nu = np.clip(dl_freq / dl_fc, 0.0, 1.0)
                                dl_curve = (2.0 / np.pi) * (
                                    np.arccos(nu) - nu * np.sqrt(np.clip(1.0 - nu * nu, 0.0, 1.0))
                                )
                                dl_curve = np.where(dl_freq <= dl_fc, dl_curve, 0.0)
                                analysis_ax.plot(
                                    dl_freq,
                                    dl_curve,
                                    color="#475569",
                                    linewidth=1.3,
                                    linestyle=(0, (4, 2)),
                                    alpha=0.9,
                                    label="DL ref",
                                    zorder=2,
                                )
                    except Exception:
                        dl_fc = None
                analysis_ax.set_title(
                    f"MTF ({method_label})  |  {basis} samples  |  ref {target_freq:.1f} cy/mm  |  {wavelength:.4g} um"
                )
                analysis_ax.set_xlabel("Spatial frequency [cycles/mm]")
                analysis_ax.set_ylabel("MTF")
                analysis_ax.set_ylim(0.0, 1.05)
                analysis_ax.set_xlim(0.0, x_limit_upper)
                analysis_ax.set_aspect("auto")
                analysis_ax.set_box_aspect(0.62)
                analysis_ax.grid(True, alpha=0.2)
                y_top = analysis_ax.get_ylim()[1]
                if label_specs:
                    x_min, x_max = [float(v) for v in analysis_ax.get_xlim()]
                    y_min, _ = [float(v) for v in analysis_ax.get_ylim()]
                    active_x_max = x_max
                    for spec in label_specs:
                        curve_x = np.asarray(spec["curve_x"], dtype=float)
                        curve_y = np.asarray(spec["curve_y"], dtype=float)
                        nonzero = curve_x[curve_y > 0.03]
                        if nonzero.size:
                            active_x_max = min(active_x_max, float(np.max(nonzero)))
                    label_left = max(x_min + 0.06 * (x_max - x_min), min(target_freq + 1.5, active_x_max * 0.25))
                    label_right = max(label_left + 1.0, min(x_max - 0.06 * (x_max - x_min), active_x_max * 0.98))
                    label_x_positions = np.linspace(label_left, label_right, len(label_specs))
                    row_levels = [y_top - 0.07, y_top - 0.13, y_top - 0.19, y_top - 0.25]
                    for index, (spec, label_x) in enumerate(zip(label_specs, label_x_positions)):
                        curve_x = np.asarray(spec["curve_x"], dtype=float)
                        curve_y = np.asarray(spec["curve_y"], dtype=float)
                        marker_value = float(np.interp(label_x, curve_x, curve_y, left=curve_y[0], right=curve_y[-1]))
                        if not np.isfinite(marker_value):
                            continue
                        row_y = row_levels[index % len(row_levels)]
                        if marker_value >= y_top - 0.12:
                            label_y = row_y
                        else:
                            label_y = min(y_top - 0.04, max(row_y, marker_value + 0.06))
                        connector_end = label_y - 0.015 if label_y >= marker_value else label_y + 0.015
                        analysis_ax.plot(
                            [label_x, label_x],
                            [marker_value, connector_end],
                            color=str(spec["color"]),
                            linewidth=0.75,
                            linestyle=spec["linestyle"],
                            alpha=0.8,
                            zorder=2.5,
                        )
                        analysis_ax.text(
                            label_x,
                            label_y,
                            str(spec["label"]),
                            rotation=0,
                            ha="center",
                            va="top",
                            fontsize=6.1,
                            color=str(spec["color"]),
                            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.45, "pad": 0.2},
                        )
                if dl_fc is not None and np.isfinite(dl_fc):
                    dl_x = float(np.clip(dl_fc, analysis_ax.get_xlim()[0], analysis_ax.get_xlim()[1]))
                    analysis_ax.axvline(
                        dl_x,
                        color="#475569",
                        linewidth=0.9,
                        linestyle=(0, (1, 2)),
                        alpha=0.7,
                        zorder=1.5,
                    )
                    label_x = min(dl_x, analysis_ax.get_xlim()[1] - 0.5)
                    analysis_ax.text(
                        label_x,
                        0.035,
                        f"DL cutoff {float(dl_fc):.1f} cy/mm",
                        ha="right" if dl_x >= analysis_ax.get_xlim()[1] - 1.0 else "center",
                        va="bottom",
                        fontsize=7,
                        color="#475569",
                        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.45, "pad": 0.2},
                    )

                self._set_analysis_parallel_status("MTF", max_workers, max_workers > 1)
                if accelerators:
                    accel_summary = "/".join(sorted(accelerators))
                    self._set_analysis_accelerator(accel_summary)
                self._update_analysis_progress("Rendering MTF", total_steps, total_steps)
                self._finish_analysis_progress("MTF analysis", success=True)
            except Exception as exc:
                self._set_analysis_parallel_status("MTF", 1, True)
                self.append_debug(f"MTF analysis error: {exc}")
                analysis_ax.text(0.5, 0.5, "MTF analysis unavailable", ha="center", va="center")
                analysis_ax.set_axis_off()
                self._finish_analysis_progress("MTF analysis", success=False)
            return
