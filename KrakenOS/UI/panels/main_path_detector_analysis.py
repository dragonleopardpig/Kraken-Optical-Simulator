"""Path detector analysis plot/export orchestration."""

from __future__ import annotations

import csv
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any

from matplotlib import colormaps
import numpy as np

import KrakenOS as Kos
from KrakenOS.UI.branch_field_analysis import (
    branch_field_analysis_data_from_coherent,
    write_branch_field_csv,
)
from KrakenOS.UI.branch_throughput_analysis import normalize_branch_throughput_filter_label
from KrakenOS.UI.coherent_detector_analysis import (
    COHERENT_DETECTOR_CSV_COLUMNS,
    COHERENT_SUM_MODE_DEFAULT,
    coherent_detector_group_key,
    coherent_detector_pair_key,
    diffraction_detector_field_data_from_coherent,
    fft_angle_axis_mrad,
    fft_vector_field_intensity,
    iter_coherent_detector_csv_rows,
    normalize_coherent_sum_mode,
)
from KrakenOS.UI.detector_path_analysis import (
    BRANCH_DETECTOR_MTF_CSV_COLUMNS,
    BRANCH_DETECTOR_PSF_CSV_COLUMNS,
    branch_detector_mtf_data_from_psf,
    branch_detector_psf_data_from_samples,
    detector_map_data_from_samples,
    detector_map_extent,
    iter_branch_detector_mtf_csv_rows,
    iter_branch_detector_psf_csv_rows,
    iter_detector_map_csv_rows,
    write_branch_detector_mtf_csv,
    write_branch_detector_psf_csv,
    write_detector_map_csv,
)


def _normalize_path_filter_label(value: object) -> str:
    return normalize_branch_throughput_filter_label(value)


def _normalize_coherent_sum_mode(value: object) -> str:
    return normalize_coherent_sum_mode(value)


class MainPathDetectorAnalysis:
    """Own detector/path analysis rendering and CSV export while delegating editor state."""

    def __init__(self, editor: Any) -> None:
        object.__setattr__(self, "editor", editor)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name == "editor":
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def _branch_detector_spot_samples(
        self,
        system,
        filter_text: str,
        *,
        require_detector: bool = False,
        ray_records: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        source_records = list(ray_records if ray_records is not None else self._collect_ray_analysis_records())
        ray_records = [
            record
            for record in source_records
            if self._ray_record_branch_filter_matches(record, filter_text)
        ]
        if not ray_records:
            return {
                "x": np.asarray([]),
                "y": np.asarray([]),
                "weights": np.asarray([]),
                "terminals": [],
                "terminal_surfaces": [],
                "coord": "local",
                "used_detector_only": False,
                "matched_ray_count": 0,
                "analysis_sources": [],
            }

        detector_records = [
            record for record in ray_records if self._surface_index_is_detector(record.get("last_surface"))
        ]
        if require_detector and not detector_records:
            return {
                "x": np.asarray([]),
                "y": np.asarray([]),
                "weights": np.asarray([]),
                "terminals": [
                    self._terminal_surface_label(record.get("last_surface"), str(record.get("last_name", "") or ""))
                    for record in ray_records
                ],
                "terminal_surfaces": [record.get("last_surface") for record in ray_records],
                "coord": "local",
                "used_detector_only": False,
                "matched_ray_count": len(ray_records),
                "analysis_sources": [str(record.get("analysis_source", "") or "") for record in ray_records],
            }
        samples = detector_records if detector_records else ray_records
        x_values: list[float] = []
        y_values: list[float] = []
        weights: list[float] = []
        terminals: list[str] = []
        terminal_surfaces: list[object] = []
        analysis_sources: list[str] = []
        coord_modes: set[str] = set()
        for record in samples:
            x_value, y_value, coord_mode = self._record_terminal_hit_local_xy(system, record)
            if not np.isfinite(x_value) or not np.isfinite(y_value):
                continue
            branch_power = self._safe_positive_float(record.get("branch_power"), np.nan)
            if not np.isfinite(branch_power):
                branch_power = self._safe_positive_float(record.get("transmission"), 1.0)
            source_weight = self._safe_positive_float(record.get("source_weight"), 1.0)
            source_power = self._safe_positive_float(record.get("source_power"), 1.0)
            x_values.append(float(x_value))
            y_values.append(float(y_value))
            weights.append(float(max(branch_power * source_weight * source_power, 0.0)))
            terminals.append(
                self._terminal_surface_label(record.get("last_surface"), str(record.get("last_name", "") or ""))
            )
            terminal_surfaces.append(record.get("last_surface"))
            analysis_sources.append(str(record.get("analysis_source", "") or ""))
            coord_modes.add(coord_mode)

        coord = "local" if coord_modes == {"local"} else "world"
        return {
            "x": np.asarray(x_values, dtype=float),
            "y": np.asarray(y_values, dtype=float),
            "weights": np.asarray(weights, dtype=float),
            "terminals": terminals,
            "terminal_surfaces": terminal_surfaces,
            "coord": coord,
            "used_detector_only": bool(detector_records),
            "matched_ray_count": len(ray_records),
            "analysis_sources": analysis_sources,
        }

    def _plot_branch_detector_spot_analysis(
        self,
        analysis_ax,
        system,
        mode: str,
        ray_records: list[dict[str, object]] | None = None,
    ) -> None:
        filter_text = self._current_analysis_branch_filter()
        self._set_analysis_parallel_status("Path Spot" if mode == "spot" else "Path RMS", 1, False)
        samples = self._branch_detector_spot_samples(system, filter_text, ray_records=ray_records)
        x_values = np.asarray(samples.get("x", np.asarray([])), dtype=float)
        y_values = np.asarray(samples.get("y", np.asarray([])), dtype=float)
        weights = np.asarray(samples.get("weights", np.asarray([])), dtype=float)
        if x_values.size == 0 or y_values.size == 0:
            analysis_ax.text(
                0.5,
                0.5,
                f"No detector hit data for\n{filter_text}",
                ha="center",
                va="center",
            )
            analysis_ax.set_axis_off()
            self.append_debug(f"Path {mode} analysis: no detector hit data for filter={filter_text}")
            return

        spot_mode = self._current_spot_view_mode()
        center_weights = np.maximum(weights, 1e-12) if weights.size == x_values.size else None
        center_x = (
            float(np.average(x_values, weights=center_weights))
            if center_weights is not None
            else float(np.mean(x_values))
        )
        center_y = (
            float(np.average(y_values, weights=center_weights))
            if center_weights is not None
            else float(np.mean(y_values))
        )
        if spot_mode == "Absolute":
            plot_x = x_values
            plot_y = y_values
        else:
            plot_x = x_values - center_x
            plot_y = y_values - center_y

        radii = np.sqrt((x_values - center_x) ** 2 + (y_values - center_y) ** 2)
        if weights.size == radii.size and float(np.sum(weights)) > 0.0:
            rms = float(np.sqrt(np.average(radii * radii, weights=np.maximum(weights, 0.0))))
        else:
            rms = float(np.sqrt(np.mean(radii * radii)))
        coordinate_label = "detector local" if samples.get("coord") == "local" else "world"

        if mode == "rms":
            bins = min(max(5, int(np.sqrt(max(len(radii), 1)))), 24)
            analysis_ax.hist(
                radii,
                bins=bins,
                weights=weights if weights.size == radii.size else None,
                color="#2563eb",
                edgecolor="white",
            )
            analysis_ax.set_title(f"Path Spot Radius | RMS={rms:.4g} mm")
            analysis_ax.set_xlabel("Radius from weighted centroid [mm]")
            analysis_ax.set_ylabel("Power-weighted count" if weights.size == radii.size else "Count")
            analysis_ax.set_box_aspect(0.52)
            analysis_ax.grid(True, axis="y", alpha=0.2)
        else:
            marker_sizes = np.full(plot_x.shape, 22.0, dtype=float)
            max_weight = float(np.nanmax(weights)) if weights.size == plot_x.size else 0.0
            if max_weight > 0.0:
                marker_sizes = 14.0 + 38.0 * np.sqrt(np.clip(weights / max_weight, 0.0, 1.0))
            scatter = analysis_ax.scatter(
                plot_x,
                plot_y,
                s=marker_sizes,
                c=weights if weights.size == plot_x.size else "#c0392b",
                cmap="viridis",
                alpha=0.82,
                edgecolors="#111827",
                linewidths=0.25,
            )
            if max_weight > 0.0:
                self.figure.colorbar(scatter, ax=analysis_ax, fraction=0.046, pad=0.04, label="Relative path power")
            analysis_ax.axhline(0.0, color="#2c3e50", linewidth=0.6, alpha=0.5)
            analysis_ax.axvline(0.0, color="#2c3e50", linewidth=0.6, alpha=0.5)
            title_suffix = "Absolute" if spot_mode == "Absolute" else "Centroid Referenced"
            analysis_ax.set_title(f"Path Detector Spot ({title_suffix})")
            analysis_ax.set_xlabel(f"X [{coordinate_label}, mm]")
            analysis_ax.set_ylabel(f"Y [{coordinate_label}, mm]")
            self._apply_equal_spot_axis_scaling(analysis_ax, plot_x, plot_y)
            analysis_ax.grid(True, alpha=0.2)

        terminal_count = len(set(samples.get("terminals", []) or []))
        analysis_ax.text(
            0.02,
            0.98,
            f"{filter_text}\nrays={x_values.size}/{int(samples.get('matched_ray_count', x_values.size) or x_values.size)} | terminals={terminal_count}",
            transform=analysis_ax.transAxes,
            ha="left",
            va="top",
            fontsize=7.5,
            bbox={"facecolor": "white", "edgecolor": "#cbd5e1", "alpha": 0.78, "pad": 3},
        )
        self.append_debug(
            f"Path {mode} analysis ok: filter={filter_text}, rays={x_values.size}, "
            f"terminals={terminal_count}, rms={rms:.6g}, coord={coordinate_label}"
        )

    def _detector_map_extent(self, samples: dict[str, object], x_values: np.ndarray, y_values: np.ndarray) -> tuple[float, float, float, float]:
        return detector_map_extent(samples, x_values, y_values, self._detector_model_for_samples(samples))

    def _branch_detector_map_data(
        self,
        system,
        filter_text: str | None = None,
        ray_records: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        filter_text = self._current_analysis_branch_filter() if filter_text is None else _normalize_path_filter_label(filter_text)
        samples = self._branch_detector_spot_samples(system, filter_text, require_detector=True, ray_records=ray_records)
        x_values = np.asarray(samples.get("x", np.asarray([])), dtype=float)
        detector_model = self._detector_model_for_samples(samples)
        bins = self._current_detector_bin_count(int(x_values.size), coherent=False, detector_model=detector_model)
        empty_message = (
            f"No detector hits for {filter_text}. DetMap needs rays that terminate on a Detector row. "
            "Try Layouts -> Beam Splitters / Folds -> Beam Splitter Two Path Doublets, "
            "Michelson Interferometer (Interferogram), Mach-Zehnder Interferometer (Interferogram), "
            "or Twyman-Green Interferometer (Interferogram); click Update; then choose a detector "
            "Analysis path such as Output: Detector output port or a Terminal: ... Detector entry."
        )
        return detector_map_data_from_samples(
            samples,
            filter_text,
            bins=bins,
            detector_model=detector_model,
            empty_message=empty_message,
        )

    def _branch_detector_psf_data(
        self,
        system,
        filter_text: str | None = None,
        ray_records: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        filter_text = self._current_analysis_branch_filter() if filter_text is None else _normalize_path_filter_label(filter_text)
        samples = self._branch_detector_spot_samples(system, filter_text, require_detector=True, ray_records=ray_records)
        x_values = np.asarray(samples.get("x", np.asarray([])), dtype=float)
        detector_model = self._detector_model_for_samples(samples)
        bins = self._current_detector_bin_count(int(x_values.size), coherent=False, detector_model=detector_model)
        return branch_detector_psf_data_from_samples(
            samples,
            filter_text,
            bins=bins,
            detector_model=detector_model,
        )

    def _plot_branch_detector_psf_analysis(
        self,
        analysis_ax,
        system,
        wavelength: float,
        ray_records: list[dict[str, object]] | None = None,
    ) -> None:
        filter_text = self._current_analysis_branch_filter()
        self._set_analysis_parallel_status("Path PSF", 1, False)
        try:
            data = self._branch_detector_psf_data(system, filter_text, ray_records=ray_records)
            hist = np.asarray(data["hist"], dtype=float)
            x_edges = np.asarray(data["x_edges"], dtype=float)
            y_edges = np.asarray(data["y_edges"], dtype=float)
            display = hist.T / max(float(data["peak_power"]), 1e-15)
            image = analysis_ax.imshow(
                display,
                origin="lower",
                extent=[float(x_edges[0]), float(x_edges[-1]), float(y_edges[0]), float(y_edges[-1])],
                interpolation="nearest",
                aspect="equal",
                cmap="inferno",
                vmin=0.0,
                vmax=1.0,
            )
            centered_x = np.asarray(data["centered_x"], dtype=float)
            centered_y = np.asarray(data["centered_y"], dtype=float)
            if centered_x.size <= 400:
                analysis_ax.scatter(centered_x, centered_y, s=6, c="white", alpha=0.45, linewidths=0.0)
            analysis_ax.set_title(f"Path Detector PSF  |  {wavelength:.4g} um")
            analysis_ax.set_xlabel(f"X [{data['coordinate_label']}, centroid mm]")
            analysis_ax.set_ylabel(f"Y [{data['coordinate_label']}, centroid mm]")
            analysis_ax.set_box_aspect(0.62)
            cbar = analysis_ax.figure.colorbar(image, ax=analysis_ax, fraction=0.046, pad=0.04)
            cbar.set_label("Normalized power")
            analysis_ax.text(
                0.02,
                0.98,
                f"{filter_text}\n{data['terminal_label']}\nrays={centered_x.size} | bins={int(data['bins'])}x{int(data['bins'])}\n"
                f"power={float(data['total_power']):.6g}",
                transform=analysis_ax.transAxes,
                ha="left",
                va="top",
                fontsize=7.5,
                bbox={"facecolor": "white", "edgecolor": "#cbd5e1", "alpha": 0.78, "pad": 3},
            )
            self.append_debug(
                f"Path PSF ok: filter={filter_text}, terminal={data['terminal_label']}, "
                f"rays={centered_x.size}, bins={int(data['bins'])}, power={float(data['total_power']):.6g}"
            )
        except Exception as exc:
            analysis_ax.text(0.5, 0.5, str(exc), ha="center", va="center")
            analysis_ax.set_axis_off()
            self.append_debug(f"Path PSF unavailable: {exc}")

    def _branch_detector_mtf_data(
        self,
        system,
        filter_text: str | None = None,
        ray_records: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        return branch_detector_mtf_data_from_psf(
            self._branch_detector_psf_data(system, filter_text, ray_records=ray_records)
        )

    def _plot_branch_detector_mtf_analysis(
        self,
        analysis_ax,
        system,
        wavelength: float,
        ray_records: list[dict[str, object]] | None = None,
    ) -> None:
        filter_text = self._current_analysis_branch_filter()
        self._set_analysis_parallel_status("Path MTF", 1, False)
        try:
            data = self._branch_detector_mtf_data(system, filter_text, ray_records=ray_records)
            plot_freq = np.asarray(data["plot_freq"], dtype=float)
            plot_tan = np.asarray(data["plot_tan"], dtype=float)
            plot_sag = np.asarray(data["plot_sag"], dtype=float)
            plot_avg = np.asarray(data["plot_avg"], dtype=float)
            target_freq = self._current_mtf_frequency()
            mtf_mode = self._operand_mtf_mode("MTF @ freq")
            if mtf_mode == "tangential":
                selected_curve = plot_tan
                selected_label = "Tangential"
            elif mtf_mode == "sagittal":
                selected_curve = plot_sag
                selected_label = "Sagittal"
            else:
                selected_curve = plot_avg
                selected_label = "Average"
            selected_value = float(np.interp(target_freq, plot_freq, selected_curve, left=selected_curve[0], right=selected_curve[-1]))

            analysis_ax.plot(plot_freq, plot_tan, color="#2563eb", linewidth=1.4, label="Tangential")
            analysis_ax.plot(plot_freq, plot_sag, color="#dc2626", linewidth=1.2, linestyle=(0, (6, 3)), label="Sagittal")
            if mtf_mode == "average":
                analysis_ax.plot(plot_freq, plot_avg, color="#111827", linewidth=1.0, linestyle=(0, (2, 2)), label="Average")
            analysis_ax.axvline(target_freq, color="#475569", linewidth=0.9, linestyle=(0, (2, 2)), alpha=0.8)
            analysis_ax.set_title(f"Path Detector MTF  |  {wavelength:.4g} um")
            analysis_ax.set_xlabel("Spatial frequency [cycles/mm]")
            analysis_ax.set_ylabel("MTF")
            analysis_ax.set_ylim(0.0, 1.05)
            x_max = max(float(plot_freq[-1]), max(10.0, target_freq * 1.2))
            analysis_ax.set_xlim(0.0, x_max)
            analysis_ax.set_box_aspect(0.62)
            analysis_ax.grid(True, alpha=0.2)
            analysis_ax.legend(loc="best", fontsize=7)
            analysis_ax.text(
                0.02,
                0.98,
                f"{filter_text}\n{data['terminal_label']}\n{selected_label} @ {target_freq:.3g} cy/mm = {selected_value:.4g}\n"
                f"rays={len(data['x_values'])} | bins={int(data['bins'])}x{int(data['bins'])}",
                transform=analysis_ax.transAxes,
                ha="left",
                va="top",
                fontsize=7.5,
                bbox={"facecolor": "white", "edgecolor": "#cbd5e1", "alpha": 0.78, "pad": 3},
            )
            self.append_debug(
                f"Path MTF ok: filter={filter_text}, terminal={data['terminal_label']}, "
                f"rays={len(data['x_values'])}, bins={int(data['bins'])}, target={target_freq:.6g}, value={selected_value:.6g}"
            )
        except Exception as exc:
            analysis_ax.text(0.5, 0.5, str(exc), ha="center", va="center")
            analysis_ax.set_axis_off()
            self.append_debug(f"Path MTF unavailable: {exc}")

    @staticmethod
    def _branch_psf_csv_columns() -> tuple[str, ...]:
        return BRANCH_DETECTOR_PSF_CSV_COLUMNS

    def _branch_detector_psf_csv_rows(self, data: dict[str, object]) -> list[dict[str, object]]:
        return list(iter_branch_detector_psf_csv_rows(data))

    @staticmethod
    def _branch_mtf_csv_columns() -> tuple[str, ...]:
        return BRANCH_DETECTOR_MTF_CSV_COLUMNS

    def _branch_detector_mtf_csv_rows(
        self,
        data: dict[str, object],
        *,
        target_freq: float | None = None,
        mtf_mode: str | None = None,
    ) -> list[dict[str, object]]:
        target = float(self._current_mtf_frequency() if target_freq is None else target_freq)
        mode = str(self._operand_mtf_mode("MTF @ freq") if mtf_mode is None else mtf_mode).strip().lower()
        return list(iter_branch_detector_mtf_csv_rows(data, target_freq=target, mtf_mode=mode))

    def export_branch_psf_csv(self) -> None:
        if self.last_system is None or self.last_rays is None:
            messagebox.showinfo(
                "Export Path PSF CSV",
                "No path PSF trace data. Click Update first, then choose an Analysis path.",
                parent=self,
            )
            return
        try:
            ray_records = self._ray_analysis_records_for_trace(system=self.last_system, rays=self.last_rays)
            data = self._branch_detector_psf_data(self.last_system, ray_records=ray_records)
            rows = self._branch_detector_psf_csv_rows(data)
        except Exception as exc:
            messagebox.showinfo("Export Path PSF CSV", str(exc), parent=self)
            return

        path = filedialog.asksaveasfilename(
            title="Export Path PSF CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*")],
            parent=self,
        )
        if not path:
            return
        write_branch_detector_psf_csv(path, data)
        self.status_var.set(f"Path PSF CSV exported: {Path(path).name}")
        self.append_debug(
            f"Path PSF CSV exported: {path} | filter={data['filter_text']}, terminal={data['terminal_label']}, "
            f"rays={len(data['x_values'])}, bins={int(data['bins'])}, rows={len(rows)}"
        )

    def export_branch_mtf_csv(self) -> None:
        if self.last_system is None or self.last_rays is None:
            messagebox.showinfo(
                "Export Path MTF CSV",
                "No path MTF trace data. Click Update first, then choose an Analysis path.",
                parent=self,
            )
            return
        try:
            ray_records = self._ray_analysis_records_for_trace(system=self.last_system, rays=self.last_rays)
            data = self._branch_detector_mtf_data(self.last_system, ray_records=ray_records)
            target_freq = self._current_mtf_frequency()
            mtf_mode = self._operand_mtf_mode("MTF @ freq")
            rows = self._branch_detector_mtf_csv_rows(data, target_freq=target_freq, mtf_mode=mtf_mode)
        except Exception as exc:
            messagebox.showinfo("Export Path MTF CSV", str(exc), parent=self)
            return

        path = filedialog.asksaveasfilename(
            title="Export Path MTF CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*")],
            parent=self,
        )
        if not path:
            return
        write_branch_detector_mtf_csv(path, data, target_freq=target_freq, mtf_mode=mtf_mode)
        self.status_var.set(f"Path MTF CSV exported: {Path(path).name}")
        self.append_debug(
            f"Path MTF CSV exported: {path} | filter={data['filter_text']}, terminal={data['terminal_label']}, "
            f"rays={len(data['x_values'])}, bins={int(data['bins'])}, rows={len(rows)}"
        )

    def _plot_branch_detector_map_analysis(
        self,
        analysis_ax,
        system,
        ray_records: list[dict[str, object]] | None = None,
    ) -> None:
        filter_text = self._current_analysis_branch_filter()
        self._set_analysis_parallel_status("Detector map", 1, False)
        try:
            data = self._branch_detector_map_data(system, filter_text, ray_records=ray_records)
        except Exception as exc:
            analysis_ax.text(0.5, 0.5, str(exc), ha="center", va="center")
            analysis_ax.set_axis_off()
            self.append_debug(f"Detector map unavailable: {exc}")
            return

        x_values = np.asarray(data["x_values"], dtype=float)
        y_values = np.asarray(data["y_values"], dtype=float)
        hist = np.asarray(data["hist"], dtype=float)
        x_edges = np.asarray(data["x_edges"], dtype=float)
        y_edges = np.asarray(data["y_edges"], dtype=float)

        cmap = colormaps.get_cmap("magma").copy()
        cmap.set_bad("#f3f4f6")
        image = analysis_ax.imshow(
            hist.T,
            origin="lower",
            extent=[float(x_edges[0]), float(x_edges[-1]), float(y_edges[0]), float(y_edges[-1])],
            interpolation="nearest",
            aspect="auto",
            cmap=cmap,
        )
        if x_values.size <= 400:
            analysis_ax.scatter(x_values, y_values, s=8, c="white", alpha=0.55, linewidths=0.0)
        total_power = float(data["total_power"])
        peak_power = float(data["peak_power"])
        coordinate_label = str(data["coordinate_label"])
        terminal_label = str(data["terminal_label"])
        bins = int(data["bins"])
        analysis_ax.set_title("Detector Power Map")
        analysis_ax.set_xlabel(f"X [{coordinate_label}, mm]")
        analysis_ax.set_ylabel(f"Y [{coordinate_label}, mm]")
        analysis_ax.set_box_aspect(0.62)
        cbar = analysis_ax.figure.colorbar(image, ax=analysis_ax, fraction=0.046, pad=0.04)
        cbar.set_label("Power per pixel")
        analysis_ax.text(
            0.02,
            0.98,
            f"{filter_text}\n{terminal_label}\nrays={x_values.size} | bins={bins}x{bins}\npower={total_power:.6g} | peak={peak_power:.6g}",
            transform=analysis_ax.transAxes,
            ha="left",
            va="top",
            fontsize=7.5,
            bbox={"facecolor": "white", "edgecolor": "#cbd5e1", "alpha": 0.78, "pad": 3},
        )
        self.append_debug(
            f"Detector map ok: filter={filter_text}, terminal={terminal_label}, rays={x_values.size}, "
            f"bins={bins}, power={total_power:.6g}, peak={peak_power:.6g}, coord={coordinate_label}"
        )

    def export_detector_map_csv(self) -> None:
        if self.last_system is None or self.last_rays is None:
            messagebox.showinfo(
                "Export Detector Map CSV",
                "No detector-map trace data. Click Update first, then choose an Analysis path.",
                parent=self,
            )
            return
        try:
            ray_records = self._ray_analysis_records_for_trace(system=self.last_system, rays=self.last_rays)
            data = self._branch_detector_map_data(self.last_system, ray_records=ray_records)
        except Exception as exc:
            messagebox.showinfo("Export Detector Map CSV", str(exc), parent=self)
            return

        path = filedialog.asksaveasfilename(
            title="Export Detector Map CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*")],
            parent=self,
        )
        if not path:
            return

        filter_text = str(data["filter_text"])
        terminal_label = str(data["terminal_label"])
        total_power = float(data["total_power"])
        bins = int(data["bins"])
        x_values = np.asarray(data["x_values"], dtype=float)
        rows = list(iter_detector_map_csv_rows(data))
        write_detector_map_csv(path, data)
        self.status_var.set(f"Detector map CSV exported: {Path(path).name}")
        self.append_debug(
            f"Detector map CSV exported: {path} | filter={filter_text}, terminal={terminal_label}, "
            f"rays={x_values.size}, bins={bins}, power={total_power:.6g}, rows={len(rows)}"
        )

    @staticmethod
    def _coherent_detector_group_key(
        coherence_mode: str,
        source_id: object,
        source_ray_index: object,
        sample_index: int,
    ) -> str:
        return coherent_detector_group_key(coherence_mode, source_id, source_ray_index, sample_index)

    @staticmethod
    def _coherent_detector_pair_key(code_a: str, code_b: str) -> str:
        return coherent_detector_pair_key(code_a, code_b)

    def _should_use_gaussian_q_detector_weighting(self) -> bool:
        return self._current_source_model() == "Gaussian beam"

    def _gaussian_q_detector_sample_weights(
        self,
        records: list[dict[str, object]],
        x_values: np.ndarray,
        y_values: np.ndarray,
        power_values: np.ndarray,
        wavelength: float,
    ) -> dict[str, object]:
        if not records:
            return {
                "enabled": False,
                "weights": np.ones(0, dtype=float),
                "clip_transmissions": np.ones(0, dtype=float),
                "trace_count": 0,
                "stable_count": 0,
            }
        gaussian_records = [
            record
            for record in records
            if str(record.get("source_model", self._current_source_model()) or "").strip() == "Gaussian beam"
        ]
        if not gaussian_records:
            return {
                "enabled": False,
                "weights": np.ones(len(records), dtype=float),
                "clip_transmissions": np.ones(len(records), dtype=float),
                "trace_count": 0,
                "stable_count": 0,
            }
        try:
            beam = self._current_gaussian_beam_input(wavelength=wavelength)
        except Exception:
            return {
                "enabled": False,
                "weights": np.ones(len(records), dtype=float),
                "clip_transmissions": np.ones(len(records), dtype=float),
                "trace_count": 0,
                "stable_count": 0,
            }

        x_array = np.asarray(x_values, dtype=float).reshape(-1)
        y_array = np.asarray(y_values, dtype=float).reshape(-1)
        power_array = np.asarray(power_values, dtype=float).reshape(-1)
        count = min(len(records), x_array.size, y_array.size, power_array.size)
        weights = np.ones(count, dtype=float)
        clip_values = np.ones(count, dtype=float)
        envelope_values = np.ones(count, dtype=float)
        trace_count = 0
        stable_count = 0
        branch_keys: list[str] = []
        radii_t = np.ones(count, dtype=float)
        radii_s = np.ones(count, dtype=float)
        for sample_index, record in enumerate(records[:count]):
            branch_path = str(record.get("branch_path", "") or "").strip()
            branch_code = "".join(self._branch_path_selector_sequence(branch_path)) or "primary"
            branch_keys.append(branch_code)
            if str(record.get("source_model", self._current_source_model()) or "").strip() != "Gaussian beam":
                continue
            try:
                trace = Kos.propagate_branch_gaussian_q(record, beam, surfaces=self.rows)
            except Exception:
                continue
            trace_count += 1
            final = trace.final
            if final is None or not bool(trace.stable):
                continue
            stable_count += 1
            radius_t = self._safe_positive_float(getattr(final, "tangential_beam_radius_mm", np.nan), np.nan)
            radius_s = self._safe_positive_float(getattr(final, "sagittal_beam_radius_mm", np.nan), np.nan)
            if np.isfinite(radius_t) and radius_t > 1e-12:
                radii_t[sample_index] = float(radius_t)
            if np.isfinite(radius_s) and radius_s > 1e-12:
                radii_s[sample_index] = float(radius_s)
            clip = self._safe_positive_float(getattr(trace, "cumulative_clip_transmission", 1.0), 1.0)
            clip_values[sample_index] = float(np.clip(clip, 0.0, 1.0))

        if trace_count <= 0:
            return {
                "enabled": False,
                "weights": np.ones(count, dtype=float),
                "clip_transmissions": np.ones(count, dtype=float),
                "trace_count": 0,
                "stable_count": 0,
            }

        for branch_key in sorted(set(branch_keys)):
            mask = np.asarray([key == branch_key for key in branch_keys], dtype=bool)
            if not np.any(mask):
                continue
            group_power = np.maximum(power_array[:count][mask], 0.0)
            if float(np.sum(group_power)) > 0.0:
                center_x = float(np.average(x_array[:count][mask], weights=group_power))
                center_y = float(np.average(y_array[:count][mask], weights=group_power))
            else:
                center_x = float(np.mean(x_array[:count][mask]))
                center_y = float(np.mean(y_array[:count][mask]))
            dx = x_array[:count][mask] - center_x
            dy = y_array[:count][mask] - center_y
            rt = np.maximum(radii_t[mask], 1e-12)
            rs = np.maximum(radii_s[mask], 1e-12)
            envelope = np.exp(-2.0 * ((dx * dx) / (rt * rt) + (dy * dy) / (rs * rs)))
            if float(np.sum(group_power)) > 0.0:
                mean_envelope = float(np.average(envelope, weights=group_power))
            else:
                mean_envelope = float(np.mean(envelope))
            if not np.isfinite(mean_envelope) or mean_envelope <= 1e-15:
                mean_envelope = 1.0
            normalized_envelope = envelope / mean_envelope
            envelope_values[mask] = normalized_envelope
            weights[mask] = normalized_envelope * clip_values[mask]

        weights = np.where(np.isfinite(weights) & (weights >= 0.0), weights, 1.0)
        weighted_power = power_array[:count] * weights
        unweighted_total = float(np.sum(power_array[:count]))
        weighted_total = float(np.sum(weighted_power))
        return {
            "enabled": True,
            "weights": weights,
            "clip_transmissions": clip_values,
            "envelope_weights": envelope_values,
            "trace_count": trace_count,
            "stable_count": stable_count,
            "power_unweighted": unweighted_total,
            "power_weighted": weighted_total,
            "mean_weight": float(np.average(weights, weights=np.maximum(power_array[:count], 0.0)))
            if unweighted_total > 0.0
            else float(np.mean(weights)),
            "mean_clip": float(np.average(clip_values, weights=np.maximum(power_array[:count], 0.0)))
            if unweighted_total > 0.0
            else float(np.mean(clip_values)),
            "model": "Branch Gaussian q detector envelope with cumulative aperture clipping",
        }

    def _coherent_detector_field_data(
        self,
        system,
        wavelength: float,
        filter_text: str | None = None,
        *,
        coherence_mode: str | None = None,
        opd_offset_um: float = 0.0,
        phase_ramp_x_mrad: float = 0.0,
        phase_ramp_y_mrad: float = 0.0,
        visibility_scale: float = 1.0,
        gaussian_q_weighting: bool = False,
        ray_records: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        filter_text = self._current_analysis_branch_filter() if filter_text is None else _normalize_path_filter_label(filter_text)
        source_records = list(ray_records if ray_records is not None else self._collect_ray_analysis_records())
        ray_records = [
            record
            for record in source_records
            if self._ray_record_branch_filter_matches(record, filter_text)
            and self._surface_index_is_detector(record.get("last_surface"))
        ]
        if not ray_records:
            raise RuntimeError(f"No detector path hits for {filter_text}. Click Update and choose a detector path/terminal.")

        x_values: list[float] = []
        y_values: list[float] = []
        powers: list[float] = []
        top_values: list[float] = []
        phase_values: list[float] = []
        jones_p_values: list[complex] = []
        jones_s_values: list[complex] = []
        polarization_values: list[np.ndarray] = []
        source_ids: list[str] = []
        source_ray_indices: list[int] = []
        terminals: list[str] = []
        terminal_surfaces: list[object] = []
        branch_codes: list[str] = []
        sample_records: list[dict[str, object]] = []
        coord_modes: set[str] = set()
        for record in ray_records:
            x_value, y_value, coord_mode = self._record_terminal_hit_local_xy(system, record)
            if not np.isfinite(x_value) or not np.isfinite(y_value):
                continue
            branch_power = self._safe_positive_float(record.get("branch_power"), np.nan)
            if not np.isfinite(branch_power):
                branch_power = self._safe_positive_float(record.get("transmission"), 1.0)
            source_weight = self._safe_positive_float(record.get("source_weight"), 1.0)
            source_power = self._safe_positive_float(record.get("source_power"), 1.0)
            power = branch_power * source_weight * source_power
            if not np.isfinite(power) or power <= 0.0:
                continue
            op_mm = self._safe_float(record.get("top"), np.nan)
            if not np.isfinite(op_mm):
                op_mm = self._safe_float(record.get("op"), 0.0)
            branch_phase_deg = self._safe_float(record.get("branch_phase"), 0.0)
            jones_p, jones_s = self._normalize_jones_pair(
                record.get("branch_jones_p", complex(1.0, 0.0)),
                record.get("branch_jones_s", complex(0.0, 0.0)),
            )
            polarization_xyz = self._normalize_complex_vector(
                record.get("branch_polarization_xyz", (1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j))
            )
            branch_path = str(record.get("branch_path", "") or "").strip()
            branch_code = "".join(self._branch_path_selector_sequence(branch_path)) or "primary"
            x_values.append(float(x_value))
            y_values.append(float(y_value))
            powers.append(float(power))
            top_values.append(float(op_mm))
            phase_values.append(float(branch_phase_deg))
            jones_p_values.append(jones_p)
            jones_s_values.append(jones_s)
            polarization_values.append(polarization_xyz)
            source_ids.append(str(record.get("source_id", "") or "source:0"))
            source_ray_indices.append(int(record.get("source_ray_index", record.get("ray_index", 0)) or 0))
            terminals.append(self._terminal_surface_label(record.get("last_surface"), str(record.get("last_name", "") or "")))
            terminal_surfaces.append(record.get("last_surface"))
            branch_codes.append(branch_code)
            sample_records.append(record)
            coord_modes.add(coord_mode)

        if not x_values:
            raise RuntimeError(f"No finite coherent detector samples for {filter_text}.")
        terminal_count = len(set(terminals))
        if terminal_count > 1:
            raise RuntimeError("Coherent detector analysis needs one terminal plane. Choose a specific Terminal or output path.")

        x_array = np.asarray(x_values, dtype=float)
        y_array = np.asarray(y_values, dtype=float)
        power_array_unweighted = np.asarray(powers, dtype=float)
        power_array = np.asarray(power_array_unweighted, dtype=float)
        top_array = np.asarray(top_values, dtype=float)
        phase_deg_array = np.asarray(phase_values, dtype=float)
        jones_p_array = np.asarray(jones_p_values, dtype=np.complex128)
        jones_s_array = np.asarray(jones_s_values, dtype=np.complex128)
        polarization_array = np.asarray(polarization_values, dtype=np.complex128).reshape(-1, 3)
        source_id_array = np.asarray(source_ids, dtype=object)
        source_ray_index_array = np.asarray(source_ray_indices, dtype=int)
        branch_code_array = np.asarray(branch_codes, dtype=object)
        sample_data = {
            "terminal_surfaces": terminal_surfaces,
            "coord": "local" if coord_modes == {"local"} else "world",
        }
        x_min, x_max, y_min, y_max = self._detector_map_extent(sample_data, x_array, y_array)
        detector_model = self._detector_model_for_samples(sample_data)
        bins = self._current_detector_bin_count(int(x_array.size), coherent=True, detector_model=detector_model)
        _sample_hist, x_edges, y_edges = np.histogram2d(
            x_array,
            y_array,
            bins=bins,
            range=[[x_min, x_max], [y_min, y_max]],
        )

        ix = np.searchsorted(x_edges, x_array, side="right") - 1
        iy = np.searchsorted(y_edges, y_array, side="right") - 1
        ix = np.where(x_array == x_edges[-1], bins - 1, ix)
        iy = np.where(y_array == y_edges[-1], bins - 1, iy)
        valid = (ix >= 0) & (ix < bins) & (iy >= 0) & (iy < bins)
        if not np.any(valid):
            raise RuntimeError("Coherent detector samples did not fall inside the detector grid.")

        gaussian_q_data = self._gaussian_q_detector_sample_weights(
            sample_records,
            x_array,
            y_array,
            power_array_unweighted,
            wavelength,
        ) if bool(gaussian_q_weighting) else {
            "enabled": False,
            "weights": np.ones_like(power_array_unweighted, dtype=float),
            "clip_transmissions": np.ones_like(power_array_unweighted, dtype=float),
            "trace_count": 0,
            "stable_count": 0,
        }
        gaussian_weights = np.asarray(gaussian_q_data.get("weights", np.ones_like(power_array_unweighted)), dtype=float).reshape(-1)
        if gaussian_weights.size != power_array_unweighted.size:
            gaussian_weights = np.ones_like(power_array_unweighted, dtype=float)
            gaussian_q_data["enabled"] = False
        power_array = power_array_unweighted * np.maximum(gaussian_weights, 0.0)
        power_hist, _, _ = np.histogram2d(
            x_array,
            y_array,
            bins=[x_edges, y_edges],
            weights=power_array,
        )

        wavelength_mm = max(float(wavelength), 1e-12) * 1e-3
        ramp_x = float(phase_ramp_x_mrad) * 1e-3
        ramp_y = float(phase_ramp_y_mrad) * 1e-3
        visibility_scale = float(np.clip(float(visibility_scale), 0.0, 1.0))
        reference_op = float(np.average(top_array[valid], weights=power_array[valid])) if float(np.sum(power_array[valid])) > 0.0 else float(np.mean(top_array[valid]))
        phase_rad = (
            (2.0 * np.pi * (top_array - reference_op) / wavelength_mm)
            + np.deg2rad(phase_deg_array)
            + (2.0 * np.pi * float(opd_offset_um) / max(float(wavelength), 1e-12))
            + (2.0 * np.pi / wavelength_mm) * (ramp_x * x_array + ramp_y * y_array)
        )
        amplitudes = np.sqrt(np.maximum(power_array, 0.0)) * np.exp(1j * phase_rad)
        field = np.zeros((bins, bins), dtype=np.complex128)
        field_p = np.zeros((bins, bins), dtype=np.complex128)
        field_s = np.zeros((bins, bins), dtype=np.complex128)
        field_x = np.zeros((bins, bins), dtype=np.complex128)
        field_y = np.zeros((bins, bins), dtype=np.complex128)
        field_z = np.zeros((bins, bins), dtype=np.complex128)
        np.add.at(field, (ix[valid], iy[valid]), amplitudes[valid])
        np.add.at(field_p, (ix[valid], iy[valid]), amplitudes[valid] * jones_p_array[valid])
        np.add.at(field_s, (ix[valid], iy[valid]), amplitudes[valid] * jones_s_array[valid])
        np.add.at(field_x, (ix[valid], iy[valid]), amplitudes[valid] * polarization_array[valid, 0])
        np.add.at(field_y, (ix[valid], iy[valid]), amplitudes[valid] * polarization_array[valid, 1])
        np.add.at(field_z, (ix[valid], iy[valid]), amplitudes[valid] * polarization_array[valid, 2])
        all_coherent_intensity = (np.abs(field_x) ** 2) + (np.abs(field_y) ** 2) + (np.abs(field_z) ** 2)

        coherence_mode = self._current_coherent_sum_mode() if coherence_mode is None else _normalize_coherent_sum_mode(coherence_mode)
        grouped_pixel_fields: dict[tuple[str, int, int], dict[str, np.ndarray]] = {}
        coherence_group_keys: set[str] = set()
        branch_self_intensity: dict[str, np.ndarray] = {}
        pair_interference_by_codepair: dict[str, np.ndarray] = {}
        coherence_group_fields: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
        for sample_index in np.flatnonzero(valid):
            group_key = self._coherent_detector_group_key(
                coherence_mode,
                source_id_array[sample_index],
                source_ray_index_array[sample_index],
                int(sample_index),
            )
            sample_ix = int(ix[sample_index])
            sample_iy = int(iy[sample_index])
            pixel_key = (group_key, sample_ix, sample_iy)
            code = str(branch_code_array[sample_index] or "primary")
            code_fields = grouped_pixel_fields.get(pixel_key)
            if code_fields is None:
                code_fields = {}
                grouped_pixel_fields[pixel_key] = code_fields
            vector = code_fields.get(code)
            if vector is None:
                vector = np.zeros(3, dtype=np.complex128)
                code_fields[code] = vector
            amplitude = complex(amplitudes[sample_index])
            vector += amplitude * polarization_array[sample_index]
            coherence_group_keys.add(group_key)

        self_intensity_total = np.zeros((bins, bins), dtype=float)
        pair_interference_total = np.zeros((bins, bins), dtype=float)
        intensity_raw = np.zeros((bins, bins), dtype=float)
        for (_group_key, sample_ix, sample_iy), code_fields in grouped_pixel_fields.items():
            total_vector = np.zeros(3, dtype=np.complex128)
            present_codes = sorted(code_fields)
            for code in present_codes:
                vector = np.asarray(code_fields[code], dtype=np.complex128)
                code_array = branch_self_intensity.get(code)
                if code_array is None:
                    code_array = np.zeros((bins, bins), dtype=float)
                    branch_self_intensity[code] = code_array
                self_term = float(np.real(np.sum(vector * np.conj(vector))))
                code_array[sample_ix, sample_iy] += self_term
                self_intensity_total[sample_ix, sample_iy] += self_term
                total_vector += vector
            group_total = float(np.real(np.sum(total_vector * np.conj(total_vector))))
            intensity_raw[sample_ix, sample_iy] += group_total
            for code_index, code_a in enumerate(present_codes):
                vector_a = np.asarray(code_fields[code_a], dtype=np.complex128)
                for code_b in present_codes[code_index + 1:]:
                    vector_b = np.asarray(code_fields[code_b], dtype=np.complex128)
                    pair_key = self._coherent_detector_pair_key(code_a, code_b)
                    pair_array = pair_interference_by_codepair.get(pair_key)
                    if pair_array is None:
                        pair_array = np.zeros((bins, bins), dtype=float)
                        pair_interference_by_codepair[pair_key] = pair_array
                    pair_term = float(2.0 * np.real(np.sum(vector_a * np.conj(vector_b))))
                    pair_array[sample_ix, sample_iy] += pair_term
                    pair_interference_total[sample_ix, sample_iy] += pair_term
            group_fields = coherence_group_fields.get(_group_key)
            if group_fields is None:
                group_fields = (
                    np.zeros((bins, bins), dtype=np.complex128),
                    np.zeros((bins, bins), dtype=np.complex128),
                    np.zeros((bins, bins), dtype=np.complex128),
                )
                coherence_group_fields[_group_key] = group_fields
            gx, gy, gz = group_fields
            gx[sample_ix, sample_iy] += total_vector[0]
            gy[sample_ix, sample_iy] += total_vector[1]
            gz[sample_ix, sample_iy] += total_vector[2]

        if visibility_scale != 1.0:
            intensity_raw = self_intensity_total + (visibility_scale * pair_interference_total)
        intensity = np.where(intensity_raw > 0.0, intensity_raw, 0.0)
        coherence_groups = sorted(coherence_group_keys)

        if not np.any(intensity > 0.0):
            raise RuntimeError("Coherent detector field sum is zero.")

        branch_code_set = sorted(set(branch_codes))
        occupied_bins = int(np.count_nonzero(power_hist > 0.0))
        negative_bins = int(np.count_nonzero(intensity_raw < -1e-12))
        display_power = float(np.sum(intensity))
        all_coherent_power = float(np.sum(all_coherent_intensity))
        return {
            "filter_text": filter_text,
            "x_values": x_array,
            "y_values": y_array,
            "powers": power_array,
            "powers_unweighted": power_array_unweighted,
            "gaussian_q_weights": gaussian_weights,
            "gaussian_q_clip_transmissions": np.asarray(
                gaussian_q_data.get("clip_transmissions", np.ones_like(power_array_unweighted)),
                dtype=float,
            ),
            "gaussian_q_envelope_weights": np.asarray(
                gaussian_q_data.get("envelope_weights", np.ones_like(power_array_unweighted)),
                dtype=float,
            ),
            "top_values": top_array,
            "phase_deg": phase_deg_array,
            "jones_p": jones_p_array,
            "jones_s": jones_s_array,
            "polarization_xyz": polarization_array,
            "field": field,
            "field_p": field_p,
            "field_s": field_s,
            "field_x": field_x,
            "field_y": field_y,
            "field_z": field_z,
            "intensity": intensity,
            "intensity_raw": intensity_raw,
            "all_coherent_intensity": all_coherent_intensity,
            "power_hist": power_hist,
            "branch_intensity_by_code": branch_self_intensity,
            "self_intensity_total": self_intensity_total,
            "pair_interference_by_codepair": pair_interference_by_codepair,
            "pair_interference_total": pair_interference_total,
            "coherence_group_fields_xyz": coherence_group_fields,
            "x_edges": x_edges,
            "y_edges": y_edges,
            "bins": bins,
            "terminal_label": terminals[0] if terminals else "Detector",
            "coordinate_label": "detector local" if sample_data["coord"] == "local" else "world",
            "branch_codes": branch_code_set,
            "reference_op_mm": reference_op,
            "total_input_power": float(np.sum(power_array)),
            "total_input_power_unweighted": float(np.sum(power_array_unweighted)),
            "total_coherent_power": display_power,
            "all_coherent_power": all_coherent_power,
            "peak_intensity": float(np.max(intensity)),
            "sample_count": int(x_array.size),
            "occupied_bins": occupied_bins,
            "negative_bins": negative_bins,
            "coherence_mode": coherence_mode,
            "coherence_group_count": len(coherence_groups),
            "coherence_groups": coherence_groups,
            "polarization_model": (
                f"{coherence_mode} Jones vector sum + Gaussian q detector envelope"
                if bool(gaussian_q_data.get("enabled", False))
                else f"{coherence_mode} Jones vector sum"
            ),
            "detector_model": detector_model,
            "gaussian_q_weighted": bool(gaussian_q_data.get("enabled", False)),
            "gaussian_q_weight_model": str(gaussian_q_data.get("model", "")),
            "gaussian_q_trace_count": int(gaussian_q_data.get("trace_count", 0) or 0),
            "gaussian_q_stable_count": int(gaussian_q_data.get("stable_count", 0) or 0),
            "gaussian_q_mean_weight": float(gaussian_q_data.get("mean_weight", 1.0) or 1.0),
            "gaussian_q_mean_clip": float(gaussian_q_data.get("mean_clip", 1.0) or 1.0),
            "opd_offset_um": float(opd_offset_um),
            "phase_ramp_x_mrad": float(phase_ramp_x_mrad),
            "phase_ramp_y_mrad": float(phase_ramp_y_mrad),
            "visibility_scale": visibility_scale,
            "analysis_sources": [str(record.get("analysis_source", "") or "") for record in sample_records],
        }

    def export_coherent_detector_csv(self) -> None:
        if self.last_system is None or self.last_rays is None:
            messagebox.showinfo(
                "Export Coherent Detector CSV",
                "No coherent detector trace data. Click Update first, then choose an Analysis path.",
                parent=self,
            )
            return
        wavelength = self._current_wavelength()
        try:
            ray_records = self._ray_analysis_records_for_trace(system=self.last_system, rays=self.last_rays)
            data = self._coherent_detector_field_data(self.last_system, wavelength, ray_records=ray_records)
        except Exception as exc:
            messagebox.showinfo("Export Coherent Detector CSV", str(exc), parent=self)
            return

        path = filedialog.asksaveasfilename(
            title="Export Coherent Detector CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*")],
            parent=self,
        )
        if not path:
            return

        filter_text = str(data["filter_text"])
        terminal_label = str(data["terminal_label"])
        polarization_model = str(data.get("polarization_model", "Jones P/S vector sum"))
        coherence_mode = str(data.get("coherence_mode", COHERENT_SUM_MODE_DEFAULT))
        coherence_groups = int(data.get("coherence_group_count", 0) or 0)
        bins = int(data["bins"])
        sample_count = int(data["sample_count"])
        total_input_power = float(data["total_input_power"])
        total_coherent_power = float(data["total_coherent_power"])
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=COHERENT_DETECTOR_CSV_COLUMNS)
            writer.writeheader()
            writer.writerows(iter_coherent_detector_csv_rows(data, wavelength))
        self.status_var.set(f"Coherent detector CSV exported: {Path(path).name}")
        self.append_debug(
            f"Coherent detector CSV exported: {path} | filter={filter_text}, terminal={terminal_label}, "
            f"rays={sample_count}, bins={bins}, input={total_input_power:.6g}, coherent={total_coherent_power:.6g}, "
            f"mode={coherence_mode}, groups={coherence_groups}, polarization={polarization_model}"
        )

    def _plot_coherent_detector_analysis(
        self,
        analysis_ax,
        system,
        wavelength: float,
        ray_records: list[dict[str, object]] | None = None,
    ) -> None:
        filter_text = self._current_analysis_branch_filter()
        self._set_analysis_parallel_status("Coherent detector", 1, False)
        self._begin_analysis_progress("Coherent detector")
        try:
            self._update_analysis_progress("Binning complex fields", 1, 2)
            data = self._coherent_detector_field_data(system, wavelength, filter_text, ray_records=ray_records)
            intensity = np.asarray(data["intensity"], dtype=float)
            x_edges = np.asarray(data["x_edges"], dtype=float)
            y_edges = np.asarray(data["y_edges"], dtype=float)
            display = intensity / max(float(data["peak_intensity"]), 1e-15)
            self._update_analysis_progress("Rendering", 2, 2)
            cmap = colormaps.get_cmap("inferno").copy()
            cmap.set_bad("#f8fafc")
            image = analysis_ax.imshow(
                display.T,
                origin="lower",
                extent=[float(x_edges[0]), float(x_edges[-1]), float(y_edges[0]), float(y_edges[-1])],
                interpolation="nearest",
                aspect="auto",
                cmap=cmap,
                vmin=0.0,
                vmax=1.0,
            )
            if int(data["sample_count"]) <= 500:
                analysis_ax.scatter(data["x_values"], data["y_values"], s=6, c="white", alpha=0.45, linewidths=0.0)
            coordinate_label = str(data["coordinate_label"])
            branch_codes = ", ".join(str(code) for code in data["branch_codes"])
            analysis_ax.set_title("Coherent Detector Field Sum")
            analysis_ax.set_xlabel(f"X [{coordinate_label}, mm]")
            analysis_ax.set_ylabel(f"Y [{coordinate_label}, mm]")
            analysis_ax.set_box_aspect(0.62)
            cbar = analysis_ax.figure.colorbar(image, ax=analysis_ax, fraction=0.046, pad=0.04)
            cbar.set_label("Normalized displayed detector intensity")
            analysis_ax.text(
                0.02,
                0.98,
                f"{filter_text}\n{data['terminal_label']}\ncodes={branch_codes or '-'} | rays={int(data['sample_count'])}\n"
                f"input={float(data['total_input_power']):.6g} | displayed={float(data['total_coherent_power']):.6g}\n"
                f"mode={data.get('coherence_mode', COHERENT_SUM_MODE_DEFAULT)} | groups={int(data.get('coherence_group_count', 0) or 0)}\n"
                f"{data.get('polarization_model', 'Jones P/S vector sum')}",
                transform=analysis_ax.transAxes,
                ha="left",
                va="top",
                fontsize=7.5,
                bbox={"facecolor": "white", "edgecolor": "#cbd5e1", "alpha": 0.78, "pad": 3},
            )
            self.append_debug(
                f"Coherent detector ok: filter={filter_text}, terminal={data['terminal_label']}, "
                f"rays={int(data['sample_count'])}, bins={int(data['bins'])}, codes={branch_codes}, "
                f"input={float(data['total_input_power']):.6g}, displayed={float(data['total_coherent_power']):.6g}, "
                f"mode={data.get('coherence_mode', COHERENT_SUM_MODE_DEFAULT)}, groups={int(data.get('coherence_group_count', 0) or 0)}, "
                f"polarization={data.get('polarization_model', 'Jones P/S vector sum')}"
            )
            self._finish_analysis_progress("Coherent detector", success=True)
        except Exception as exc:
            self.append_debug(f"Coherent detector analysis error: {exc}")
            analysis_ax.text(0.5, 0.5, str(exc), ha="center", va="center")
            analysis_ax.set_axis_off()
            self._finish_analysis_progress("Coherent detector", success=False)

    def _branch_field_analysis_data(
        self,
        system,
        wavelength: float,
        filter_text: str | None = None,
        ray_records: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        filter_text = self._current_analysis_branch_filter() if filter_text is None else _normalize_path_filter_label(filter_text)
        coherent = dict(self._coherent_detector_field_data(system, wavelength, filter_text, ray_records=ray_records))
        return branch_field_analysis_data_from_coherent(
            coherent,
            wavelength_um=wavelength,
            propagation_mm=self._current_branch_field_propagation_mm(),
        )

    @staticmethod
    def _write_branch_field_csv(path: str | Path, data: dict[str, object], wavelength: float) -> None:
        write_branch_field_csv(path, data, wavelength)

    def export_branch_field_csv(self) -> None:
        if self.last_system is None or self.last_rays is None:
            messagebox.showinfo(
                "Export Branch Field CSV",
                "No branch-field trace data. Click Update first, then choose an Analysis path.",
                parent=self,
            )
            return
        wavelength = self._current_wavelength()
        try:
            ray_records = self._ray_analysis_records_for_trace(system=self.last_system, rays=self.last_rays)
            data = self._branch_field_analysis_data(self.last_system, wavelength, ray_records=ray_records)
        except Exception as exc:
            messagebox.showinfo("Export Branch Field CSV", str(exc), parent=self)
            return

        path = filedialog.asksaveasfilename(
            title="Export Branch Field CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*")],
            parent=self,
        )
        if not path:
            return

        self._write_branch_field_csv(path, data, wavelength)
        self.status_var.set(f"Branch field CSV exported: {Path(path).name}")
        self.append_debug(
            f"Branch field CSV exported: {path} | filter={data.get('filter_text')}, "
            f"terminal={data.get('terminal_label')}, z={float(data.get('branch_field_propagation_mm', 0.0) or 0.0):.6g}, "
            f"power={float(data.get('branch_field_total_power', 0.0) or 0.0):.6g}, "
            f"TEM00={float(data.get('branch_field_tem00_overlap_efficiency', 0.0) or 0.0):.6g}"
        )

    def _plot_branch_field_analysis(
        self,
        analysis_ax,
        system,
        wavelength: float,
        ray_records: list[dict[str, object]] | None = None,
    ) -> None:
        filter_text = self._current_analysis_branch_filter()
        self._set_analysis_parallel_status("Branch field", 1, False)
        self._begin_analysis_progress("Branch field")
        try:
            self._update_analysis_progress("Promoting detector field", 1, 2)
            data = self._branch_field_analysis_data(system, wavelength, filter_text, ray_records=ray_records)
            grid = data["branch_field_grid"]
            intensity = np.asarray(data["branch_field_intensity"], dtype=float)
            phase = np.asarray(data["branch_field_phase_rad"], dtype=float)
            phase_mask = np.asarray(data["branch_field_phase_mask"], dtype=bool)
            x_edges = np.asarray(grid.x_edges_mm, dtype=float)
            y_edges = np.asarray(grid.y_edges_mm, dtype=float)
            display = intensity / max(float(data["branch_field_peak_intensity"]), 1e-15)
            self._update_analysis_progress("Rendering", 2, 2)
            cmap = colormaps.get_cmap("magma").copy()
            cmap.set_bad("#f8fafc")
            image = analysis_ax.imshow(
                display.T,
                origin="lower",
                extent=[float(x_edges[0]), float(x_edges[-1]), float(y_edges[0]), float(y_edges[-1])],
                interpolation="nearest",
                aspect="auto",
                cmap=cmap,
                vmin=0.0,
                vmax=1.0,
            )
            if int(np.count_nonzero(phase_mask)) >= 4:
                x_centers = np.asarray(grid.x_centers_mm, dtype=float)
                y_centers = np.asarray(grid.y_centers_mm, dtype=float)
                masked_phase = np.ma.masked_where(~phase_mask, phase)
                try:
                    contours = analysis_ax.contour(
                        x_centers,
                        y_centers,
                        masked_phase.T,
                        levels=np.linspace(-np.pi, np.pi, 9),
                        colors="white",
                        linewidths=0.45,
                        alpha=0.65,
                    )
                    analysis_ax.clabel(contours, inline=True, fontsize=5, fmt="%.1f")
                except Exception as contour_exc:
                    self.append_debug(f"Branch field phase contour skipped: {contour_exc}")
            centroid_x = float(data["branch_field_centroid_x_mm"])
            centroid_y = float(data["branch_field_centroid_y_mm"])
            if np.isfinite(centroid_x) and np.isfinite(centroid_y):
                analysis_ax.plot([centroid_x], [centroid_y], marker="+", color="#38bdf8", markersize=7, mew=1.4)
            branch_codes = ", ".join(str(code) for code in data.get("branch_codes", []) or [])
            coordinate_label = str(data["coordinate_label"])
            analysis_ax.set_title("Branch Field Intensity / Phase")
            analysis_ax.set_xlabel(f"X [{coordinate_label}, mm]")
            analysis_ax.set_ylabel(f"Y [{coordinate_label}, mm]")
            analysis_ax.set_box_aspect(0.62)
            cbar = analysis_ax.figure.colorbar(image, ax=analysis_ax, fraction=0.046, pad=0.04)
            cbar.set_label("Normalized |E|^2; white contours = phase [rad]")
            propagation_mm = float(data.get("branch_field_propagation_mm", 0.0) or 0.0)
            analysis_ax.text(
                0.02,
                0.98,
                f"{filter_text}\n{data['terminal_label']}\ncomponent={data['branch_field_component']} | codes={branch_codes or '-'}\n"
                f"z={propagation_mm:.4g} mm | power={float(data['branch_field_total_power']):.6g} | peak={float(data['branch_field_peak_intensity']):.6g}\n"
                f"centroid=({centroid_x:.4g}, {centroid_y:.4g}) mm | w_fit={float(data['branch_field_tem00_waist_mm']):.4g} mm\n"
                f"TEM00 overlap={float(data['branch_field_tem00_overlap_efficiency']):.4g} | phase={float(data['branch_field_tem00_overlap_phase_rad']):.4g} rad",
                transform=analysis_ax.transAxes,
                ha="left",
                va="top",
                fontsize=7.2,
                bbox={"facecolor": "white", "edgecolor": "#cbd5e1", "alpha": 0.78, "pad": 3},
            )
            self.append_debug(
                f"Branch field ok: filter={filter_text}, terminal={data['terminal_label']}, "
                f"rays={int(data['sample_count'])}, bins={int(data['bins'])}, codes={branch_codes}, "
                f"z={propagation_mm:.6g}, power={float(data['branch_field_total_power']):.6g}, "
                f"waist={float(data['branch_field_tem00_waist_mm']):.6g}, "
                f"TEM00={float(data['branch_field_tem00_overlap_efficiency']):.6g}"
            )
            self._finish_analysis_progress("Branch field", success=True)
        except Exception as exc:
            self.append_debug(f"Branch field analysis error: {exc}")
            analysis_ax.text(0.5, 0.5, str(exc), ha="center", va="center")
            analysis_ax.set_axis_off()
            self._finish_analysis_progress("Branch field", success=False)

    @staticmethod
    def _fft_angle_axis_mrad(edges: np.ndarray, wavelength_um: float) -> tuple[np.ndarray, float]:
        return fft_angle_axis_mrad(edges, wavelength_um)

    @staticmethod
    def _fft_vector_field_intensity(fields: tuple[np.ndarray, np.ndarray, np.ndarray]) -> np.ndarray:
        return fft_vector_field_intensity(fields)

    def _diffraction_detector_field_data(
        self,
        system,
        wavelength: float,
        filter_text: str | None = None,
        ray_records: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        filter_text = self._current_analysis_branch_filter() if filter_text is None else _normalize_path_filter_label(filter_text)
        coherent = self._coherent_detector_field_data(system, wavelength, filter_text, ray_records=ray_records)
        return diffraction_detector_field_data_from_coherent(coherent, wavelength)

    def _plot_diffraction_detector_analysis(
        self,
        analysis_ax,
        system,
        wavelength: float,
        ray_records: list[dict[str, object]] | None = None,
    ) -> None:
        filter_text = self._current_analysis_branch_filter()
        self._set_analysis_parallel_status("Diffraction detector", 1, False)
        self._begin_analysis_progress("Diffraction detector")
        try:
            self._update_analysis_progress("Propagating detector field", 1, 2)
            data = self._diffraction_detector_field_data(system, wavelength, filter_text, ray_records=ray_records)
            intensity = np.asarray(data["diffraction_intensity"], dtype=float)
            display = intensity / max(float(data["diffraction_peak_intensity"]), 1e-15)
            angle_x = np.asarray(data["angle_x_mrad"], dtype=float)
            angle_y = np.asarray(data["angle_y_mrad"], dtype=float)
            self._update_analysis_progress("Rendering", 2, 2)
            cmap = colormaps.get_cmap("viridis").copy()
            cmap.set_bad("#f8fafc")
            image = analysis_ax.imshow(
                display.T,
                origin="lower",
                extent=[float(angle_x[0]), float(angle_x[-1]), float(angle_y[0]), float(angle_y[-1])],
                interpolation="nearest",
                aspect="auto",
                cmap=cmap,
                vmin=0.0,
                vmax=1.0,
            )
            branch_codes = ", ".join(str(code) for code in data.get("branch_codes", []) or [])
            analysis_ax.axhline(0.0, color="white", linewidth=0.7, alpha=0.55)
            analysis_ax.axvline(0.0, color="white", linewidth=0.7, alpha=0.55)
            analysis_ax.set_title("Diffraction Detector Angular Spectrum")
            analysis_ax.set_xlabel("Angle X [mrad]")
            analysis_ax.set_ylabel("Angle Y [mrad]")
            analysis_ax.set_box_aspect(0.62)
            cbar = analysis_ax.figure.colorbar(image, ax=analysis_ax, fraction=0.046, pad=0.04)
            cbar.set_label("Normalized angular intensity")
            analysis_ax.text(
                0.02,
                0.98,
                f"{filter_text}\n{data['terminal_label']}\ncodes={branch_codes or '-'} | rays={int(data['sample_count'])}\n"
                f"near={float(data['diffraction_near_field_power']):.6g} | far={float(data['diffraction_far_field_power']):.6g}\n"
                f"groups={int(data.get('diffraction_group_count', 0) or 0)} | bins={int(data.get('bins', 0) or 0)}\n"
                f"{data.get('diffraction_model', 'Fraunhofer FFT')}",
                transform=analysis_ax.transAxes,
                ha="left",
                va="top",
                fontsize=7.5,
                bbox={"facecolor": "white", "edgecolor": "#cbd5e1", "alpha": 0.78, "pad": 3},
            )
            self.append_debug(
                f"Diffraction detector ok: filter={filter_text}, terminal={data['terminal_label']}, "
                f"rays={int(data['sample_count'])}, bins={int(data['bins'])}, codes={branch_codes}, "
                f"near={float(data['diffraction_near_field_power']):.6g}, far={float(data['diffraction_far_field_power']):.6g}, "
                f"groups={int(data.get('diffraction_group_count', 0) or 0)}"
            )
            self._finish_analysis_progress("Diffraction detector", success=True)
        except Exception as exc:
            self.append_debug(f"Diffraction detector analysis error: {exc}")
            analysis_ax.text(0.5, 0.5, str(exc), ha="center", va="center")
            analysis_ax.set_axis_off()
            self._finish_analysis_progress("Diffraction detector", success=False)
