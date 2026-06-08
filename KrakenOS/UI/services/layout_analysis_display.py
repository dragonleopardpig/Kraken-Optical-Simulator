from __future__ import annotations

import math

import numpy as np

from KrakenOS.UI.services.row_spec_contracts import _row_specs_signature


_PROTECTED_GLOBALS = {
    "LayoutAnalysisDisplayMixin",
    "_PROTECTED_GLOBALS",
    "_sync_layout_globals",
}


def _sync_layout_globals(source: dict[str, object]) -> None:
    target = globals()
    for name, value in source.items():
        if name.startswith("__") or name in _PROTECTED_GLOBALS:
            continue
        target[name] = value


class LayoutAnalysisDisplayMixin:
    def benchmark_psf_mtf(self) -> None:
        self.append_progress("Benchmark PSF/MTF started.")
        try:
            self._report_compute_backends()
            self._read_rows_from_table()
            system = self.build_system()
            wavelength = self._current_wavelength()
            field_type = "angle" if self._current_object_mode() == "Infinity" else "height"
            field_y = self._current_field_angle_deg() if field_type == "angle" else self._current_field_height()
            sample_count = max(64, self._current_ray_count() * 12)
            self.append_progress(f"Tracing benchmark rays: sample_count={sample_count}")
            x_local, y_local, workers = self._build_geometric_image_samples(
                system,
                wavelength,
                sample_count=sample_count,
                pattern="hexapolar",
                surface_index=self._analysis_surface_index(),
                aperture_type=self._current_aperture_type(),
                aperture_value=self._current_aperture_value(),
                field_type=field_type,
                field_x=0.0,
                field_y=field_y,
            )
            if x_local.size < 4:
                raise RuntimeError("Not enough traced image-plane samples for benchmark")

            span_x = max(float(np.ptp(x_local)), 1e-3)
            span_y = max(float(np.ptp(y_local)), 1e-3)
            span = max(span_x, span_y) * 1.25
            bins = 256

            t0 = time.perf_counter()
            hist_cpu, xedges_cpu, _yedges_cpu = np.histogram2d(
                x_local,
                y_local,
                bins=bins,
                range=[[-span / 2.0, span / 2.0], [-span / 2.0, span / 2.0]],
            )
            psf_cpu = hist_cpu / max(np.sum(hist_cpu), 1.0)
            otf_cpu = np.fft.fftshift(np.fft.fft2(psf_cpu))
            mtf_cpu = np.abs(otf_cpu)
            mtf_cpu /= max(float(np.max(mtf_cpu)), 1e-12)
            _freq_cpu = np.fft.fftshift(np.fft.fftfreq(bins, d=float(xedges_cpu[1] - xedges_cpu[0])))
            cpu_sec = time.perf_counter() - t0

            gpu_results: list[tuple[str, float]] = []

            cp = _optional_cupy()
            if cp is not None:
                try:
                    if int(cp.cuda.runtime.getDeviceCount()) > 0:
                        _ = cp.zeros((1,), dtype=cp.float32)
                        cp.cuda.Stream.null.synchronize()
                        t1 = time.perf_counter()
                        x_gpu = cp.asarray(x_local, dtype=cp.float64)
                        y_gpu = cp.asarray(y_local, dtype=cp.float64)
                        hist_gpu, xedges_gpu, _yedges_gpu = cp.histogram2d(
                            x_gpu,
                            y_gpu,
                            bins=bins,
                            range=[[-span / 2.0, span / 2.0], [-span / 2.0, span / 2.0]],
                        )
                        psf_gpu = hist_gpu / cp.maximum(cp.sum(hist_gpu), 1.0)
                        otf_gpu = cp.fft.fftshift(cp.fft.fft2(psf_gpu))
                        mtf_gpu = cp.abs(otf_gpu)
                        mtf_gpu /= cp.maximum(cp.max(mtf_gpu), 1e-12)
                        _freq_gpu = cp.fft.fftshift(
                            cp.fft.fftfreq(bins, d=float(cp.asnumpy(xedges_gpu[1] - xedges_gpu[0])))
                        )
                        cp.cuda.Stream.null.synchronize()
                        gpu_results.append(("CuPy", time.perf_counter() - t1))
                except Exception as exc:
                    self.append_debug(f"Benchmark CuPy path failed: {_short_error_message(exc)}")

            torch = _optional_torch()
            if torch is not None:
                try:
                    if bool(torch.cuda.is_available()):
                        device = torch.device("cuda")
                        _ = torch.zeros((1,), dtype=torch.float32, device=device)
                        if hasattr(torch.cuda, "synchronize"):
                            torch.cuda.synchronize()
                        t2 = time.perf_counter()
                        lower = -span / 2.0
                        upper = span / 2.0
                        step = (upper - lower) / float(bins)
                        x_t = torch.as_tensor(x_local, dtype=torch.float64, device=device)
                        y_t = torch.as_tensor(y_local, dtype=torch.float64, device=device)
                        ix = torch.floor((x_t - lower) / step).to(torch.int64)
                        iy = torch.floor((y_t - lower) / step).to(torch.int64)
                        valid = (ix >= 0) & (ix < bins) & (iy >= 0) & (iy < bins)
                        ix = ix[valid]
                        iy = iy[valid]
                        lin = ix * bins + iy
                        hist_t = torch.zeros(bins * bins, dtype=torch.float64, device=device)
                        hist_t.scatter_add_(0, lin, torch.ones_like(lin, dtype=torch.float64))
                        hist_t = hist_t.view(bins, bins)
                        psf_t = hist_t / torch.clamp(torch.sum(hist_t), min=1.0)
                        otf_t = torch.fft.fftshift(torch.fft.fft2(psf_t))
                        mtf_t = torch.abs(otf_t)
                        mtf_t = mtf_t / torch.clamp(torch.max(mtf_t), min=1e-12)
                        _freq_t = torch.fft.fftshift(torch.fft.fftfreq(bins, d=step, device=device))
                        if hasattr(torch.cuda, "synchronize"):
                            torch.cuda.synchronize()
                        gpu_results.append(("Torch", time.perf_counter() - t2))
                except Exception as exc:
                    self.append_debug(f"Benchmark Torch path failed: {_short_error_message(exc)}")

            self.append_progress(
                f"Benchmark traced rays={x_local.size} | trace workers={workers} | bins={bins} | CPU post={cpu_sec:.6f}s"
            )
            if gpu_results:
                gpu_results.sort(key=lambda item: item[1])
                best_name, best_sec = gpu_results[0]
                speedup = cpu_sec / max(best_sec, 1e-12)
                for name, timing in gpu_results:
                    self.append_progress(f"Benchmark {name} post={timing:.6f}s")
                self.append_progress(
                    f"Benchmark best GPU={best_name} {best_sec:.6f}s | speedup={speedup:.2f}x"
                )
                gpu_summary = ", ".join(f"{name}={timing:.6f}s" for name, timing in gpu_results)
                self.append_debug(
                    f"PSF/MTF benchmark: rays={x_local.size}, workers={workers}, cpu={cpu_sec:.6f}s, {gpu_summary}, best={best_name}, speedup={speedup:.2f}x"
                )
            else:
                self.append_progress("Benchmark GPU post=unavailable")
                self.append_debug(
                    f"PSF/MTF benchmark: rays={x_local.size}, workers={workers}, cpu={cpu_sec:.6f}s, gpu=unavailable"
                )
            self.status_var.set("Benchmark PSF/MTF completed")
        except Exception as exc:
            self.append_progress(f"Benchmark PSF/MTF failed: {exc}")
            self.append_debug(f"Benchmark PSF/MTF failed: {exc}")
            self.status_var.set("Benchmark PSF/MTF failed")

    def build_system(self, *, require_solids: bool = False, force_rebuild: bool = False):
        row_specs = self._serializable_row_specs()
        signature = _row_specs_signature(row_specs)
        require_geometry = bool(require_solids or self._rows_require_geometry_build(self.rows))
        cached_signature = self.__dict__.get("_system_cache_signature")
        cached_system = self.__dict__.get("_system_cache_system")
        cached_has_solids = bool(self.__dict__.get("_system_cache_has_solids", False))
        cached_geometry_ready = bool(self.__dict__.get("_system_cache_geometry_ready", False))
        if not force_rebuild and cached_system is not None and cached_signature == signature:
            if (not require_geometry or cached_geometry_ready) and (not require_solids or cached_has_solids):
                return cached_system
            try:
                original_build = int(getattr(cached_system, "BUILD", 0))
                cached_system.BUILD = 1
                cached_system.build()
                cached_system.BUILD = original_build
                self._system_cache_has_solids = True
                self._system_cache_geometry_ready = True
                return cached_system
            except Exception:
                pass

        system = _build_system_from_specs(
            row_specs,
            build=1 if require_geometry else 0,
        )
        self._system_cache_signature = signature
        self._system_cache_system = system
        self._system_cache_has_solids = bool(getattr(system.Pr3D, "ExistSolid", 0))
        self._system_cache_geometry_ready = bool(require_geometry)
        return system

    @classmethod
    def _rows_require_geometry_build(cls, rows: list[SurfaceRow]) -> bool:
        for row in rows:
            if cls._geometry_value_present(row.uda):
                return True
            advanced = row.advanced if isinstance(row.advanced, dict) else {}
            if cls._geometry_value_present(advanced.get("Mask_Shape")):
                return True
            if cls._geometry_value_present(advanced.get("Solid_3d_stl")):
                return True
        return False

    @classmethod
    def _open3d_step_label_for_optical_solid_row(cls, row) -> str:
        advanced = row.get("advanced", {}) if isinstance(row, dict) else getattr(row, "advanced", {})
        if not isinstance(advanced, dict):
            return ""
        if not cls._geometry_value_present(advanced.get("Solid_3d_stl")):
            return ""
        promotion = advanced.get("StepOverlayPromotion")
        if isinstance(promotion, dict):
            label = str(promotion.get("step_label", "optical") or "optical").strip().lower()
            return label or "optical"
        source_format = str(advanced.get("OpticalSolidSourceFormat", "") or "").strip().upper()
        source_path_text = str(advanced.get("OpticalSolidSourcePath", "") or "").strip()
        source_suffix = ""
        if source_path_text:
            try:
                source_suffix = Path(source_path_text).suffix.lower()
            except Exception:
                source_suffix = ""
        if source_format in {"STEP", "STP"} or source_suffix in {".step", ".stp"}:
            return "optical"
        return ""

    @classmethod
    def _is_open3d_promoted_optical_solid_row(cls, row) -> bool:
        return bool(cls._open3d_step_label_for_optical_solid_row(row))

    @staticmethod
    def _row_advanced_dict(row) -> dict:
        advanced = row.get("advanced", {}) if isinstance(row, dict) else getattr(row, "advanced", {})
        return advanced if isinstance(advanced, dict) else {}

    @classmethod
    def _step_native_promotion_metadata(cls, row) -> dict | None:
        promotion = cls._row_advanced_dict(row).get("StepNativePromotion")
        return promotion if isinstance(promotion, dict) else None

    @classmethod
    def _is_step_native_promoted_row(cls, row) -> bool:
        return cls._step_native_promotion_metadata(row) is not None

    @classmethod
    def _is_any_promoted_optical_solid_row(cls, row) -> bool:
        if cls._is_open3d_promoted_optical_solid_row(row):
            return True
        return cls._is_step_native_promoted_row(row)

    def _lens_row_group_for_row(self, row_index: int) -> list[int]:
        try:
            row_index = int(row_index)
        except Exception:
            return []
        if not (0 <= row_index < len(self.rows)):
            return []
        row = self.rows[row_index]
        promotion = self._step_native_promotion_metadata(row)
        if promotion is not None:
            raw_indices = promotion.get("row_indices", []) or []
            indices = sorted({int(value) for value in raw_indices if 0 <= int(value) < len(self.rows)})
            if indices:
                return indices
        return [row_index]

    @staticmethod
    def _geometry_value_present(value) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return value.strip().lower() not in {"", "none", "0", "0.0"}
        if isinstance(value, (int, float, np.integer, np.floating)):
            return abs(float(value)) > 1e-12
        return True

    def _current_wavelength(self) -> float:
        try:
            return float(self.wavelength_var.get())
        except ValueError:
            return 0.55

    def _current_aperture_type(self) -> str:
        value = self.aperture_type_var.get().strip().upper()
        if value == "FNO":
            return "EPD"
        if value in {"STOP", "EPD"}:
            return value
        return "STOP"

    def _current_aperture_type_label(self) -> str:
        value = self.aperture_type_var.get().strip().upper()
        if value in {"STOP", "EPD", "FNO"}:
            return value
        return "STOP"

    def _current_aperture_value(self) -> float:
        try:
            value = float(self.aperture_value_var.get())
        except ValueError:
            return 1.0
        if value == 0.0:
            return 1.0
        if self._current_aperture_type_label() == "FNO":
            f_number = max(abs(value), 1e-9)
            effl = max(abs(float(self._current_effl_estimate())), 1e-9)
            return effl / f_number
        return value

    def _current_mtf_frequency(self) -> float:
        var = self.__dict__.get("operand_frequency_vars", {}).get("MTF @ freq")
        if var is None:
            return 5.0
        try:
            value = float(var.get())
        except ValueError:
            return 5.0
        return max(0.0, value)

    def _operand_mtf_mode(self, label: str) -> str:
        var = self.__dict__.get("operand_mtf_mode_vars", {}).get(label)
        if var is None:
            return "average"
        value = var.get().strip().lower()
        if value in {"tangential", "sagittal", "average"}:
            return value
        return "average"

    def _operand_mtf_algorithm(self, label: str) -> str:
        var = self.__dict__.get("operand_mtf_algorithm_vars", {}).get(label)
        if var is None:
            return "diffraction_fft"
        value = var.get().strip().lower()
        if value == "diffraction fft":
            return "diffraction_fft"
        if value == "lsf fft":
            return "lsf_fft"
        return "psf_fft"

    def _mtf_analysis_settings(self) -> dict[str, float | int | str]:
        return {
            "wavelength": self._current_wavelength(),
            "surface_index": self._analysis_surface_index(),
            "aperture_type": self._current_aperture_type(),
            "aperture_value": self._current_aperture_value(),
            "field_type": ("angle" if self._current_object_mode() == "Infinity" else "height"),
            "field_x": 0.0,
            "field_y": (self._current_field_angle_deg() if self._current_object_mode() == "Infinity" else self._current_field_height()),
            "algorithm": self._operand_mtf_algorithm("MTF @ freq"),
        }

    @staticmethod
    def _normalize_field_type(field_type: str) -> str:
        return FIELD_TYPE_ALIASES.get(str(field_type).strip(), "Angle")

    @classmethod
    def _field_type_display_label(cls, field_type: str) -> str:
        return FIELD_TYPE_DISPLAY_LABELS.get(cls._normalize_field_type(field_type), "Field")

    @classmethod
    def _field_type_value_label(cls, field_type: str) -> str:
        labels = {
            "Angle": "Field Half-Angle [deg]",
            "Object Height": "Object Semi-Height [mm]",
            "Paraxial Image Height": "Paraxial Image Semi-Height [mm]",
            "Real Image Height": "Real Image Semi-Height [mm]",
        }
        return labels.get(cls._normalize_field_type(field_type), "Field value")

    @classmethod
    def _field_type_unit(cls, field_type: str) -> str:
        units = {
            "Angle": "deg",
            "Object Height": "mm",
            "Paraxial Image Height": "mm",
            "Real Image Height": "mm",
        }
        return units.get(cls._normalize_field_type(field_type), "")

    @staticmethod
    def _format_field_sample_value(value: float) -> str:
        return f"{float(value):.3f}".rstrip("0").rstrip(".")

    def _parse_numeric_series(self, value: str) -> list[float]:
        text = str(value or "").strip()
        if not text:
            return []
        samples: list[float] = []
        invalid: list[str] = []
        for token in re.split(r"[\s,;]+", text):
            if not token:
                continue
            try:
                samples.append(float(token))
            except ValueError:
                invalid.append(token)
        if invalid:
            self.append_debug(f"Ignoring invalid numeric samples: {', '.join(invalid)}")
        return samples

    @staticmethod
    def _name_offset(row: SurfaceRow) -> tuple[float, float]:
        if row.surface not in {"Object", "Image"}:
            return (0.0, 0.0)
        name = row.name.lower()
        base_y = max(row.diameter * 0.08, 0.0)
        if "front" in name:
            return (-max(row.diameter * 0.35, 8.0), base_y)
        if "back" in name:
            return (max(row.diameter * 0.15, 2.0), base_y)
        return (0.0, base_y)

    def _render_auxiliary_projection_axes(self, bundle: SceneBundle, max_radius: float) -> None:
        for plane, axis in dict(getattr(self, "_layout_projection_axes", {}) or {}).items():
            projected = project_scene_bundle(
                bundle,
                str(plane),
                filter_projection_axis_fields=self._should_filter_projection_axis_fields(bundle),
                filter_projection_slice=self._should_filter_projection_slice(bundle),
                filter_arm_view=self._filter_projected_scene_for_arm_view,
                filter_ray_display=self._filter_projected_scene_for_ray_display,
            )
            render_projected = self._projected_scene_for_layout_render(projected, suppress_scene_labels=True)
            render_scene_2d(
                render_projected,
                axis,
                show_clipped_rays=self.show_clipped_rays_var.get(),
                show_labels=False,
                ray_count_hint=max(1, self._preview_field_ray_count),
            )
            set_plot_limits(
                axis,
                projected.bounds,
                max_radius=max_radius,
                has_off_axis=True,
                orientation=str(plane),
                use_drawn_data=True,
            )
            x_label, y_label, _title = projection_axis_labels(str(plane))
            axis.set_xlabel(x_label, fontsize=8)
            axis.set_ylabel(y_label, fontsize=8)
            axis.set_title(self._projection_display_title(str(plane), bundle), fontsize=9)
            axis.tick_params(axis="both", which="major", labelsize=8)
            axis.grid(True, alpha=0.2)

    def _plot_refresh_service(self) -> PlotRefreshService:
        service = self.__dict__.get("_plot_refresh_service_instance")
        if service is None:
            service = PlotRefreshService(self)
            self._plot_refresh_service_instance = service
        return service

    def refresh_plot(self, *, suppress_analysis: bool = False, sampling_mode: str | None = None) -> None:
        self._plot_refresh_service().refresh_plot(
            suppress_analysis=suppress_analysis,
            sampling_mode=sampling_mode,
        )


    def _clear_preview_after_reset(self) -> None:
        """Clear UI trace products after Reset without building/tracing."""
        self.last_system = None
        self.last_rays = None
        self._last_preview_trace_signature = None
        self._last_preview_trace_backend = "none"
        self._last_preview_trace_note = ""
        self._last_scene_bundle = None
        self._last_optics_info = None
        self._last_wavefront_samples = []
        self._last_zernike_coefficients = []
        self._preview_field_ray_count = 1
        self._preview_field_bundle_count = 1
        self._system_cache_signature = None
        self._system_cache_system = None
        self._system_cache_has_solids = False
        self._layout_pick_regions = {}
        self._layout_ray_pick_regions = []
        self._layout_projected_rays_by_index = {}
        self._layout_selected_ray_index = None
        self._analysis_axes = []
        self._analysis_ax = None
        self._layout_projection_axes = {}
        self._clear_cardinal_marker_artists()
        self._clear_physical_distance_artists()
        self._clear_layout_selection_overlay()
        if getattr(self, "results_table", None) is not None:
            self.results_table.delete(*self.results_table.get_children())
        self._refresh_ray_inspector_if_open()
        self._refresh_branch_gaussian_q_report_if_open()
        self._refresh_branch_tree_if_open()
        self._refresh_branch_throughput_report_if_open()
        self._refresh_detector_aperture_report_if_open()
        self._refresh_source_illumination_report_if_open()
        self._refresh_analysis_branch_choices()
        self._refresh_nonseq_scene_graph_if_open()
        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title("")
        self.ax.set_xlabel("")
        self.ax.set_ylabel("")
        self.ax.grid(False)
        self.figure.subplots_adjust(left=0.07, right=0.98, bottom=0.15, top=0.92, wspace=0.28)
        self._sync_object_controls()
        self._configure_plot_hover_hints()
        self.canvas.draw_idle()
        self.progress_spinner_var.set("idle")
        self.progress_percent_var.set("")
        self.progress_bar_var.set(0.0)
        self.status_var.set("Reset complete. Table contains only Object and Image; click Update to trace.")
        self.append_progress("Reset completed without tracing.")
        if self._initial_layout_passes < 40:
            self.after(50, self._set_initial_pane_layout)

    def _autosave_plot(self) -> None:
        if not self.auto_save_plot_var.get():
            return
        if self._autosave_after_id is not None:
            try:
                self.after_cancel(self._autosave_after_id)
            except Exception:
                pass
        self._autosave_after_id = self.after(400, self._do_autosave_plot)

    def _do_autosave_plot(self) -> None:
        self._autosave_after_id = None
        if not self.auto_save_plot_var.get():
            return
        if self.winfo_width() < 1200 or self.winfo_height() < 700:
            self._autosave_after_id = self.after(400, self._do_autosave_plot)
            return
        try:
            AUTO_PLOT_PATH.parent.mkdir(parents=True, exist_ok=True)
            self.update_idletasks()
            self.canvas.draw()
            self.figure.savefig(AUTO_PLOT_PATH, dpi=150)
        except Exception as exc:
            self.append_debug(f"Auto-save plot failed: {exc}")

    def _plot_atmosphere_image_residual(
        self,
        analysis_ax,
        system,
        reference_wavelength: float,
        settings: dict[str, float | int],
        wavelengths: np.ndarray,
    ) -> None:
        self._update_analysis_progress("Tracing atmospheric residual", 1, 3)
        reference_wavelength = float(np.clip(float(reference_wavelength), float(wavelengths[0]), float(wavelengths[-1])))
        pupil = Kos.PupilCalc(
            system,
            self._analysis_surface_index(),
            reference_wavelength,
            self._current_aperture_type(),
            self._current_aperture_value(),
        )
        pupil.Samp = max(4, min(12, int(np.sqrt(max(1, self._current_ray_count())) * 2)))
        pupil.Ptype = self._current_analysis_pupil_pattern("hexapolar")
        pupil.FieldType = "angle"
        pupil.FieldX = 0.0
        pupil.FieldY = self._current_field_angle_deg() if self._current_object_mode() == "Infinity" else 0.0
        pupil.AtmosRef = 1
        pupil.T = float(settings["temperature_k"])
        pupil.P = float(settings["pressure_pa"])
        pupil.H = float(settings["humidity"])
        pupil.xc = float(settings["co2_ppm"])
        pupil.lat = float(settings["latitude_deg"])
        pupil.h = float(settings["altitude_m"])
        pupil.l1 = reference_wavelength
        pupil.z0 = float(settings["zenith_deg"])

        centroids: list[tuple[float, float, float, float]] = []
        total = max(1, int(wavelengths.size))
        for index, sample_wavelength in enumerate(wavelengths, start=1):
            self._update_analysis_progress(f"ADC residual {index}/{total}", index, total)
            pupil.l2 = float(sample_wavelength)
            x, y, z, l, m, n = pupil.Pattern2Field()
            rays_for_wavelength = Kos.raykeeper(system)
            Kos.TraceLoop(x, y, z, l, m, n, float(sample_wavelength), rays_for_wavelength, clean=1)
            x_img, y_img, _z_img, _l_img, _m_img, _n_img = self._pick_image_plane_data(rays_for_wavelength)
            x_img = np.asarray(x_img, dtype=float).ravel()
            y_img = np.asarray(y_img, dtype=float).ravel()
            finite = np.isfinite(x_img) & np.isfinite(y_img)
            x_img = x_img[finite]
            y_img = y_img[finite]
            if x_img.size == 0:
                continue
            cx = float(np.mean(x_img))
            cy = float(np.mean(y_img))
            radius = np.sqrt((x_img - cx) * (x_img - cx) + (y_img - cy) * (y_img - cy))
            rms = float(np.sqrt(np.mean(radius * radius)))
            centroids.append((float(sample_wavelength), cx, cy, rms))

        if len(centroids) < 2:
            raise RuntimeError("Not enough finite atmospheric image residual samples")

        self._update_analysis_progress("Rendering residual", 3, 3)
        centroid_array = np.asarray(centroids, dtype=float)
        valid_wavelengths = centroid_array[:, 0]
        centroid_x = centroid_array[:, 1]
        centroid_y = centroid_array[:, 2]
        spot_rms_um = centroid_array[:, 3] * 1000.0
        reference_x = float(np.interp(reference_wavelength, valid_wavelengths, centroid_x))
        reference_y = float(np.interp(reference_wavelength, valid_wavelengths, centroid_y))
        residual_x_um = (centroid_x - reference_x) * 1000.0
        residual_y_um = (centroid_y - reference_y) * 1000.0
        residual_mag_um = np.sqrt(residual_x_um * residual_x_um + residual_y_um * residual_y_um)
        blue_red_um = float(
            np.sqrt(
                (residual_x_um[-1] - residual_x_um[0]) * (residual_x_um[-1] - residual_x_um[0])
                + (residual_y_um[-1] - residual_y_um[0]) * (residual_y_um[-1] - residual_y_um[0])
            )
        )
        max_residual_um = float(np.max(residual_mag_um))
        max_spot_rms_um = float(np.max(spot_rms_um))

        line_x, = analysis_ax.plot(valid_wavelengths, residual_x_um, color="#2563eb", marker="o", markersize=3.0)
        line_y, = analysis_ax.plot(valid_wavelengths, residual_y_um, color="#dc2626", marker="s", markersize=3.0)
        line_mag, = analysis_ax.plot(valid_wavelengths, residual_mag_um, color="#111827", linewidth=2.0)
        analysis_ax.axvline(reference_wavelength, color="#64748b", linewidth=0.8, alpha=0.65)
        analysis_ax.axhline(0.0, color="#64748b", linewidth=0.8, alpha=0.45)
        analysis_ax.set_title("Atmospheric Image Residual")
        analysis_ax.set_xlabel("Wavelength [um]")
        analysis_ax.set_ylabel(f"Image residual vs {reference_wavelength:.4g} um [um]")
        analysis_ax.set_box_aspect(0.62)
        analysis_ax.grid(True, alpha=0.2)
        analysis_ax.legend([line_x, line_y, line_mag], ["X", "Y", "Magnitude"], loc="best", fontsize=8)
        analysis_ax.text(
            0.02,
            0.03,
            f"blue-red residual: {blue_red_um:.4g} um\n"
            f"max residual: {max_residual_um:.4g} um\n"
            f"max spot RMS: {max_spot_rms_um:.4g} um",
            transform=analysis_ax.transAxes,
            ha="left",
            va="bottom",
            fontsize=7.5,
            bbox={"facecolor": "white", "edgecolor": "#cbd5e1", "alpha": 0.78, "pad": 3},
        )
        result_items = [
            ("Mode", "Atmos image residual"),
            ("Reference wavelength [um]", f"{reference_wavelength:.6g}"),
            ("Samples", str(int(valid_wavelengths.size))),
            ("Zenith angle [deg]", f"{float(settings['zenith_deg']):.6g}"),
            ("Blue-red residual [um]", f"{blue_red_um:.6g}"),
            ("Max residual [um]", f"{max_residual_um:.6g}"),
            ("Max spot RMS [um]", f"{max_spot_rms_um:.6g}"),
        ]
        if getattr(self, "results_table", None) is not None:
            self._set_results(result_items)
        self.append_debug(
            f"Atmos image residual ok: samples={valid_wavelengths.size}, reference_um={reference_wavelength:.6g}, "
            f"blue_red_um={blue_red_um:.6g}, max_residual_um={max_residual_um:.6g}"
        )
        self._finish_analysis_progress("Atmosphere analysis", success=True)

    def _current_interferogram_settings(self) -> dict[str, object]:
        settings: dict[str, object] = {
            "analysis_title": "Interferogram",
            "detector_port": "cross",
            "detector_size_mm": 12.0,
            "pixels": 256,
            "fringe_tilt_x_mrad": 1.5,
            "fringe_tilt_y_mrad": 0.0,
            "opd_offset_um": 0.0,
            "visibility": 1.0,
            "coherence_mode": COHERENT_SUM_MODE_DEFAULT,
            "gaussian_q_weighting": "auto",
        }
        for row in getattr(self, "rows", []) or []:
            advanced = getattr(row, "advanced", {}) or {}
            if not isinstance(advanced, dict):
                continue
            row_settings = advanced.get("Interferogram")
            if isinstance(row_settings, dict):
                settings.update(row_settings)
        return settings

    @staticmethod
    def _raykeeper_value(rays, name: str, index: int, default=None):
        values = getattr(rays, name, None)
        if values is None or index >= len(values):
            return default
        arr = np.asarray(values[index]).ravel()
        if arr.size == 0:
            return default
        return arr[-1]

    def _interferogram_output_pair(self, settings: dict[str, object]) -> tuple[str, str, str]:
        port = str(settings.get("detector_port", "cross") or "cross").strip().lower()
        if port in {"return", "source", "source return", "output port 1", "port 1", "tt/rr"}:
            return "TT", "RR", "Output port 1"
        return "TR", "RT", "Detector output port"

    def _interferogram_branch_samples(
        self,
        rays,
        settings: dict[str, object],
        records: list[dict[str, object]] | None = None,
    ) -> tuple[dict, dict, str]:
        code_a, code_b, port_label = self._interferogram_output_pair(settings)
        grouped: dict[str, list[dict[str, float | str]]] = {code_a: [], code_b: []}

        def append_sample(
            *,
            branch_path: str,
            power: float,
            source_weight: float,
            source_power: float,
            top_mm: float,
            phase_deg: float,
            analysis_source: str,
        ) -> None:
            selectors = self._branch_path_selector_sequence(branch_path)
            if len(selectors) < 2:
                return
            code = "".join("T" if item in {"T", "transmit"} else "R" for item in selectors[-2:])
            if code not in grouped:
                return
            weight = max(power * max(source_weight, 0.0) * max(source_power, 0.0), 0.0)
            if weight <= 0.0:
                return
            grouped[code].append(
                {
                    "code": code,
                    "path": branch_path,
                    "power": weight,
                    "top_mm": top_mm,
                    "phase_deg": phase_deg,
                    "analysis_source": analysis_source,
                }
            )

        analysis_source = "raykeeper"
        ray_records: list[dict[str, object]] = []
        if records is not None:
            ray_records = list(records)
        else:
            try:
                ray_records = self._collect_ray_inspector_records(rays=rays)
            except Exception:
                ray_records = []

        event_records = [
            record
            for record in ray_records
            if str(record.get("analysis_source", "") or "") == "ray_events"
            and str(record.get("branch_path", "") or "").strip()
        ]
        if event_records:
            analysis_source = "ray_events"
            for record in event_records:
                branch_path = str(record.get("branch_path", "") or "")
                power = self._safe_positive_float(record.get("branch_power"), np.nan)
                if not np.isfinite(power):
                    power = self._safe_positive_float(record.get("transmission"), 1.0)
                source_weight = self._safe_positive_float(record.get("source_weight"), 1.0)
                source_power = self._safe_positive_float(record.get("source_power"), 1.0)
                top_mm = self._safe_float(record.get("top"), self._safe_float(record.get("op"), 0.0))
                phase_deg = self._safe_float(record.get("branch_phase", record.get("branch_phase_deg", 0.0)), 0.0)
                append_sample(
                    branch_path=branch_path,
                    power=power,
                    source_weight=source_weight,
                    source_power=source_power,
                    top_mm=top_mm,
                    phase_deg=phase_deg,
                    analysis_source=analysis_source,
                )
        else:
            branch_paths = list(getattr(rays, "BRANCH_PATH", []) or [])
            for ray_index in range(len(branch_paths)):
                branch_path = str(self._raykeeper_value(rays, "BRANCH_PATH", ray_index, "") or "")
                try:
                    power = float(self._raykeeper_value(rays, "BRANCH_POWER", ray_index, 0.0) or 0.0)
                except Exception:
                    power = 0.0
                try:
                    source_weight = float(self._raykeeper_value(rays, "SOURCE_WEIGHT", ray_index, 1.0) or 1.0)
                except Exception:
                    source_weight = 1.0
                try:
                    top_mm = float(self._raykeeper_value(rays, "TOP", ray_index, 0.0) or 0.0)
                except Exception:
                    top_mm = 0.0
                try:
                    phase_deg = float(self._raykeeper_value(rays, "BRANCH_PHASE", ray_index, 0.0) or 0.0)
                except Exception:
                    phase_deg = 0.0
                append_sample(
                    branch_path=branch_path,
                    power=power,
                    source_weight=source_weight,
                    source_power=1.0,
                    top_mm=top_mm,
                    phase_deg=phase_deg,
                    analysis_source=analysis_source,
                )
        if not grouped[code_a] or not grouped[code_b]:
            raise RuntimeError(f"Need both {code_a} and {code_b} Michelson paths at the detector port")

        def summarize(samples: list[dict[str, float | str]]) -> dict[str, float | str]:
            powers = np.asarray([float(sample["power"]) for sample in samples], dtype=float)
            total = float(np.sum(powers))
            if total <= 0.0:
                raise RuntimeError("Zero path power")
            tops = np.asarray([float(sample["top_mm"]) for sample in samples], dtype=float)
            phases = np.asarray([float(sample["phase_deg"]) for sample in samples], dtype=float)
            return {
                "code": str(samples[0]["code"]),
                "path": str(samples[0]["path"]),
                "power": total,
                "top_mm": float(np.average(tops, weights=powers)),
                "phase_deg": float(np.average(phases, weights=powers)),
                "count": float(len(samples)),
                "analysis_source": str(samples[0]["analysis_source"]),
            }

        return summarize(grouped[code_a]), summarize(grouped[code_b]), port_label

    def _preferred_interferogram_filter(
        self,
        settings: dict[str, object],
        ray_records: list[dict[str, object]] | None = None,
    ) -> str:
        current = self._current_analysis_branch_filter()
        records = self._collect_branch_throughput_records(ray_records=ray_records)
        choices = self._branch_throughput_filter_choices(records)
        if current in choices and current.startswith(("Output:", "Terminal:")) and not _is_all_path_filter(current):
            return current
        port = str(settings.get("detector_port", "cross") or "cross").strip().lower()
        preferred_output = (
            "Output: Source return port"
            if port in {"return", "source", "source return", "output port 1", "port 1", "tt/rr"}
            else "Output: Detector output port"
        )
        if preferred_output in choices:
            return preferred_output
        detector_terminals = [choice for choice in choices if choice.startswith("Terminal:") and "Detector" in choice]
        if detector_terminals:
            return detector_terminals[0]
        if current in choices:
            return current
        return ANALYSIS_PATH_FILTER_DEFAULT

    def _interferogram_detector_field_data(
        self,
        system,
        wavelength: float,
        settings: dict[str, object],
        ray_records: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        code_a, code_b, port_label = self._interferogram_output_pair(settings)
        filter_text = self._preferred_interferogram_filter(settings, ray_records=ray_records)
        coherence_mode = _normalize_coherent_sum_mode(settings.get("coherence_mode", COHERENT_SUM_MODE_DEFAULT))
        gaussian_setting = str(settings.get("gaussian_q_weighting", "auto") or "auto").strip().lower()
        gaussian_q_weighting = (
            self._should_use_gaussian_q_detector_weighting()
            if gaussian_setting in {"", "auto"}
            else gaussian_setting in {"1", "true", "yes", "on", "enabled"}
        )
        data = self._coherent_detector_field_data(
            system,
            wavelength,
            filter_text,
            coherence_mode=coherence_mode,
            opd_offset_um=float(settings.get("opd_offset_um", 0.0)),
            phase_ramp_x_mrad=float(settings.get("fringe_tilt_x_mrad", 0.0)),
            phase_ramp_y_mrad=float(settings.get("fringe_tilt_y_mrad", 0.0)),
            visibility_scale=float(settings.get("visibility", 1.0)),
            gaussian_q_weighting=gaussian_q_weighting,
            ray_records=ray_records,
        )
        available_codes = {str(code) for code in list(data.get("branch_codes", []) or [])}
        pair_key = self._coherent_detector_pair_key(code_a, code_b)
        pair_maps = dict(data.get("pair_interference_by_codepair", {}) or {})
        pair_map = np.asarray(
            pair_maps.get(pair_key, np.zeros_like(np.asarray(data.get("intensity", np.asarray([])), dtype=float))),
            dtype=float,
        )
        occupied_bins = int(data.get("occupied_bins", 0) or 0)
        pair_peak = float(np.max(np.abs(pair_map))) if pair_map.size else 0.0
        reliable = (
            {code_a, code_b}.issubset(available_codes)
            and int(data.get("sample_count", 0) or 0) >= 8
            and occupied_bins >= 4
            and pair_peak > 1e-12
        )
        result = dict(data)
        result.update(
            {
                "data_source": "coherent_detector",
                "analysis_title": str(settings.get("analysis_title", "Interferogram") or "Interferogram").strip(),
                "port_label": port_label,
                "filter_text": filter_text,
                "expected_branch_codes": [code_a, code_b],
                "pair_key": pair_key,
                "pair_interference_peak": pair_peak,
                "reliable": reliable,
                "extent": [
                    float(np.asarray(data["x_edges"], dtype=float)[0]),
                    float(np.asarray(data["x_edges"], dtype=float)[-1]),
                    float(np.asarray(data["y_edges"], dtype=float)[0]),
                    float(np.asarray(data["y_edges"], dtype=float)[-1]),
                ],
            }
        )
        return result

    def _interferogram_analysis_data(self, system, rays, wavelength: float) -> dict[str, object]:
        settings = self._current_interferogram_settings()
        ray_records: list[dict[str, object]] | None = None
        try:
            ray_records = self._ray_analysis_records_for_trace(system=system, rays=rays)
        except Exception:
            ray_records = []
        coherent_reason = ""
        try:
            coherent = self._interferogram_detector_field_data(system, wavelength, settings, ray_records=ray_records)
            if bool(coherent.get("reliable")):
                coherent["fallback_reason"] = ""
                return coherent
            coherent_reason = (
                "coherent detector fallback: "
                f"samples={int(coherent.get('sample_count', 0) or 0)}, "
                f"occupied_bins={int(coherent.get('occupied_bins', 0) or 0)}, "
                f"pair_peak={float(coherent.get('pair_interference_peak', 0.0) or 0.0):.6g}, "
                f"codes={','.join(str(code) for code in coherent.get('branch_codes', []) or []) or '-'}"
            )
        except Exception as exc:
            coherent_reason = f"coherent detector unavailable: {_short_error_message(exc)}"

        beam_a, beam_b, port_label = self._interferogram_branch_samples(rays, settings, records=ray_records)
        wavelength_um = max(float(wavelength), 1e-12)
        wavelength_mm = wavelength_um * 1e-3
        detector_size = max(float(settings.get("detector_size_mm", 12.0)), 1e-6)
        pixels = max(32, min(int(float(settings.get("pixels", 256))), 1024))
        tilt_x = float(settings.get("fringe_tilt_x_mrad", 1.5)) * 1e-3
        tilt_y = float(settings.get("fringe_tilt_y_mrad", 0.0)) * 1e-3
        opd_um = (float(beam_b["top_mm"]) - float(beam_a["top_mm"])) * 1000.0 + float(settings.get("opd_offset_um", 0.0))
        branch_phase_deg = float(beam_b["phase_deg"]) - float(beam_a["phase_deg"])
        phase0 = (2.0 * np.pi * opd_um / wavelength_um) + np.deg2rad(branch_phase_deg)
        axis = np.linspace(-0.5 * detector_size, 0.5 * detector_size, pixels)
        grid_x, grid_y = np.meshgrid(axis, axis)
        spatial_phase = (2.0 * np.pi / wavelength_mm) * (tilt_x * grid_x + tilt_y * grid_y)
        coherent_term = 2.0 * np.sqrt(max(float(beam_a["power"]), 0.0) * max(float(beam_b["power"]), 0.0)) * min(max(float(settings.get("visibility", 1.0)), 0.0), 1.0)
        intensity = (
            max(float(beam_a["power"]), 0.0)
            + max(float(beam_b["power"]), 0.0)
            + coherent_term * np.cos(phase0 + spatial_phase)
        )
        intensity = np.asarray(intensity, dtype=float)
        intensity = np.where(intensity > 0.0, intensity, 0.0)
        detector_radius = 0.5 * detector_size
        radius = np.sqrt(grid_x * grid_x + grid_y * grid_y)
        intensity = np.where(radius <= detector_radius, intensity, np.nan)
        visibility = coherent_term / max(float(beam_a["power"]) + float(beam_b["power"]), 1e-15)
        return {
            "data_source": "analytic_path_average",
            "analysis_title": str(settings.get("analysis_title", "Interferogram") or "Interferogram").strip(),
            "port_label": port_label,
            "intensity": intensity,
            "extent": [-0.5 * detector_size, 0.5 * detector_size, -0.5 * detector_size, 0.5 * detector_size],
            "coordinate_label": "detector synthetic",
            "branch_codes": [str(beam_a["code"]), str(beam_b["code"])],
            "sample_count": int(float(beam_a.get("count", 0.0)) + float(beam_b.get("count", 0.0))),
            "bins": pixels,
            "total_input_power": float(beam_a["power"]) + float(beam_b["power"]),
            "total_coherent_power": float(np.nansum(intensity)),
            "peak_intensity": float(np.nanmax(intensity)) if intensity.size else 0.0,
            "coherence_mode": str(settings.get("coherence_mode", COHERENT_SUM_MODE_DEFAULT)),
            "coherence_group_count": 2,
            "polarization_model": "Analytic path-average branch sum",
            "filter_text": self._preferred_interferogram_filter(settings, ray_records=ray_records),
            "beam_a": beam_a,
            "beam_b": beam_b,
            "opd_um": opd_um,
            "branch_phase_deg": branch_phase_deg,
            "visibility": visibility,
            "fallback_reason": coherent_reason,
            "analysis_sources": sorted(
                {
                    str(beam_a.get("analysis_source", "") or ""),
                    str(beam_b.get("analysis_source", "") or ""),
                }
            ),
        }

    def _plot_interferogram_analysis(self, analysis_ax, system, rays, wavelength: float) -> None:
        self._set_analysis_parallel_status("Interferogram", 1, False)
        self._begin_analysis_progress("Interferogram analysis")
        try:
            self._update_analysis_progress("Building detector interferogram", 1, 3)
            data = self._interferogram_analysis_data(system, rays, wavelength)
            intensity = np.asarray(data["intensity"], dtype=float)
            peak = float(np.nanmax(intensity)) if intensity.size else 0.0
            if peak <= 0.0 or not np.isfinite(peak):
                raise RuntimeError("Interferogram has zero finite intensity")
            display = intensity / peak
            extent = [float(value) for value in list(data.get("extent", (-1.0, 1.0, -1.0, 1.0)))]
            self._update_analysis_progress("Rendering", 2, 3)
            cmap = colormaps.get_cmap("magma").copy()
            cmap.set_bad("#f8fafc")
            image = analysis_ax.imshow(
                display,
                origin="lower",
                extent=extent,
                cmap=cmap,
                vmin=0.0,
                vmax=1.0,
                interpolation="bilinear",
            )
            title = str(data.get("analysis_title", "Interferogram") or "Interferogram").strip()
            analysis_ax.set_title(f"{title}  |  {data.get('port_label', 'Detector output')}")
            if str(data.get("data_source")) == "coherent_detector":
                coordinate_label = str(data.get("coordinate_label", "detector local"))
                analysis_ax.set_xlabel(f"X [{coordinate_label}, mm]")
                analysis_ax.set_ylabel(f"Y [{coordinate_label}, mm]")
            else:
                analysis_ax.set_xlabel("Detector X [mm]")
                analysis_ax.set_ylabel("Detector Y [mm]")
            analysis_ax.set_aspect("equal", adjustable="box")
            analysis_ax.set_box_aspect(0.82)
            analysis_ax.grid(False)
            self.figure.colorbar(image, ax=analysis_ax, fraction=0.046, pad=0.04, label="Normalized intensity")
            self._update_analysis_progress("Annotating", 3, 3)
            if str(data.get("data_source")) == "coherent_detector":
                pair_peak = float(data.get("pair_interference_peak", 0.0) or 0.0)
                branch_codes = ", ".join(str(code) for code in data.get("branch_codes", []) or [])
                gaussian_note = (
                    f"\nGaussian q: traces={int(data.get('gaussian_q_trace_count', 0) or 0)}, "
                    f"stable={int(data.get('gaussian_q_stable_count', 0) or 0)}, "
                    f"mean clip={float(data.get('gaussian_q_mean_clip', 1.0) or 1.0):.4g}"
                    if bool(data.get("gaussian_q_weighted", False))
                    else ""
                )
                detector_sum_label = (
                    "Gaussian-q detector-bin coherent sum"
                    if bool(data.get("gaussian_q_weighted", False))
                    else "Detector-bin coherent sum"
                )
                analysis_ax.text(
                    0.02,
                    0.02,
                    f"{detector_sum_label}\n"
                    f"{data.get('filter_text', ANALYSIS_PATH_FILTER_DEFAULT)}\n"
                    f"{data.get('terminal_label', 'Detector')} | codes={branch_codes or '-'}\n"
                    f"samples={int(data.get('sample_count', 0) or 0)}, bins={int(data.get('bins', 0) or 0)}, occupied={int(data.get('occupied_bins', 0) or 0)}\n"
                    f"input={float(data.get('total_input_power', 0.0) or 0.0):.6g}, displayed={float(data.get('total_coherent_power', 0.0) or 0.0):.6g}\n"
                    f"mode={data.get('coherence_mode', COHERENT_SUM_MODE_DEFAULT)} | groups={int(data.get('coherence_group_count', 0) or 0)}\n"
                    f"pair peak={pair_peak:.4g}, visibility={float(data.get('visibility_scale', 1.0) or 1.0):.3g}"
                    f"{gaussian_note}",
                    transform=analysis_ax.transAxes,
                    ha="left",
                    va="bottom",
                    fontsize=7.5,
                    color="#111827",
                    bbox={"facecolor": "white", "edgecolor": "#cbd5e1", "alpha": 0.82, "pad": 3},
                )
                self.append_debug(
                    f"Interferogram ok: source=coherent_detector, filter={data.get('filter_text')}, "
                    f"terminal={data.get('terminal_label')}, codes={branch_codes}, "
                    f"samples={int(data.get('sample_count', 0) or 0)}, occupied={int(data.get('occupied_bins', 0) or 0)}, "
                    f"pair_peak={pair_peak:.6g}, mode={data.get('coherence_mode', COHERENT_SUM_MODE_DEFAULT)}, "
                    f"gaussian_q={bool(data.get('gaussian_q_weighted', False))}"
                )
            else:
                beam_a = dict(data.get("beam_a", {}) or {})
                beam_b = dict(data.get("beam_b", {}) or {})
                opd_um = float(data.get("opd_um", 0.0) or 0.0)
                branch_phase_deg = float(data.get("branch_phase_deg", 0.0) or 0.0)
                visibility = float(data.get("visibility", 0.0) or 0.0)
                analysis_ax.text(
                    0.02,
                    0.02,
                    f"{beam_a.get('code', 'A')} vs {beam_b.get('code', 'B')}\n"
                    f"OPD {opd_um:.4g} um, phase {branch_phase_deg:.4g} deg\n"
                    f"analytic fallback | {str(data.get('fallback_reason', '') or '-').strip()}",
                    transform=analysis_ax.transAxes,
                    ha="left",
                    va="bottom",
                    fontsize=7.5,
                    color="#111827",
                    bbox={"facecolor": "white", "edgecolor": "#cbd5e1", "alpha": 0.82, "pad": 3},
                )
                self.append_debug(
                    f"Interferogram ok: source=analytic_fallback, codes={beam_a.get('code')}:{beam_b.get('code')}, "
                    f"opd_um={opd_um:.6g}, phase_deg={branch_phase_deg:.6g}, visibility={visibility:.6g}, "
                    f"reason={data.get('fallback_reason', '-')}"
                )
            self._finish_analysis_progress("Interferogram analysis", success=True)
        except Exception as exc:
            self.append_debug(f"Interferogram analysis error: {exc}")
            analysis_ax.text(
                0.5,
                0.5,
                "Interferogram unavailable\nNeed a beam-splitter layout with recombined paths",
                ha="center",
                va="center",
            )
            analysis_ax.set_axis_off()
            self._finish_analysis_progress("Interferogram analysis", success=False)

    def _analysis_plot_service(self) -> AnalysisPlotService:
        service = self.__dict__.get("_analysis_plot_service_instance")
        if service is None:
            service = AnalysisPlotService(self)
            self._analysis_plot_service_instance = service
        return service

    def _plot_analysis(self, analysis_ax, system, rays, wavelength: float) -> None:
        self._analysis_plot_service().plot_analysis(analysis_ax, system, rays, wavelength)

    def _plot_analysis_for_mode(self, analysis_ax, system, rays, wavelength: float, mode: str) -> None:
        previous_mode = self.analysis_mode
        try:
            self.analysis_mode = str(mode)
            self._plot_analysis(analysis_ax, system, rays, wavelength)
        finally:
            self.analysis_mode = previous_mode

    def _analysis_surface_index(self) -> int:
        selected = self.analysis_surface_var.get().strip()
        if selected and selected != "Auto":
            try:
                return int(selected.split(":", 1)[0])
            except ValueError:
                pass
        if len(self.rows) <= 2:
            return max(0, len(self.rows) - 1)
        candidate_indices = [i for i, row in enumerate(self.rows[1:-1], start=1)]
        if not candidate_indices:
            return 1
        return min(candidate_indices, key=lambda i: max(self.rows[i].diameter, 1e-9))

    def _current_object_mode(self) -> str:
        mode = self._left_mode_text("object_mode_var", "Finite")
        return mode if mode in {"Finite", "Infinity"} else "Finite"

    def _current_object_distance(self) -> float:
        if self.rows:
            try:
                if any(row.surface == "Mirror" for row in self.rows):
                    distance, _first_source_index = self._paraxial_total_object_gap(self.rows)
                else:
                    distance = float(self.rows[0].thickness)
            except Exception:
                distance = float(self.rows[0].thickness)
        else:
            distance = 100.0
        return max(distance, 1e-6)

    def _requested_field_count(self) -> int:
        text = self._left_mode_text("field_count_var", "1")
        try:
            return max(1, int(float(str(text).strip())))
        except Exception:
            return 1

    def _field_sampling_basis_span(self) -> tuple[str, str, float]:
        if self._current_object_mode() == "Infinity":
            return "angle", "deg", abs(float(self._current_field_angle_deg()))
        return "object height", "mm", abs(float(self._current_field_height()))

    def _field_sampling_is_active(self) -> bool:
        try:
            _basis, _unit, span = self._field_sampling_basis_span()
        except Exception:
            return True
        return bool(np.isfinite(span) and abs(float(span)) > 1e-12)

    def _infinity_field_launch_reference_point(self, system=None) -> np.ndarray:
        try:
            reference_index = int(self._analysis_surface_index())
            reference = np.asarray(
                self._surface_reference_world_point(reference_index, system=system),
                dtype=float,
            ).reshape(-1)[:3]
        except Exception:
            reference = np.asarray((0.0, 0.0, self._current_object_distance()), dtype=float)
        if reference.size < 3 or not np.all(np.isfinite(reference[:3])):
            reference = np.asarray((0.0, 0.0, self._current_object_distance()), dtype=float)
        return reference.astype(float)

    def _center_infinity_bundle_on_launch_reference(self, bundle, *, system=None):
        arrays = tuple(np.asarray(values, dtype=float).reshape(-1).copy() for values in bundle)
        if len(arrays) != 6 or len(arrays[0]) == 0:
            return bundle
        reference = self._infinity_field_launch_reference_point(system=system)
        origins = np.column_stack(arrays[:3])
        directions = np.column_stack(arrays[3:])
        dz = directions[:, 2]
        valid = np.isfinite(dz) & (np.abs(dz) > 1.0e-12)
        if not np.any(valid):
            return arrays
        t = (float(reference[2]) - origins[valid, 2]) / dz[valid]
        hits_xy = origins[valid, :2] + directions[valid, :2] * t[:, None]
        finite = np.all(np.isfinite(hits_xy), axis=1)
        if not np.any(finite):
            return arrays
        center_xy = np.median(hits_xy[finite], axis=0)
        shift_xy = np.asarray(reference[:2], dtype=float) - center_xy
        if not np.all(np.isfinite(shift_xy)):
            return arrays
        arrays = list(arrays)
        arrays[0] = arrays[0] + float(shift_xy[0])
        arrays[1] = arrays[1] + float(shift_xy[1])
        return tuple(arrays)

    def _current_field_count(self) -> int:
        if not self._field_sampling_is_active():
            return 1
        return self._requested_field_count()

    def _current_field_type(self) -> str:
        return self._normalize_field_type(self.field_type_var.get().strip())

    def _current_spot_view_mode(self) -> str:
        value = getattr(self, "spot_view_mode_var", None)
        if value is None:
            return "Grid"
        mode = value.get().strip()
        if mode in {"Grid", "Absolute", "Centroid"}:
            return mode
        return "Grid"

    @staticmethod
    def _apply_equal_spot_axis_scaling(
        analysis_ax,
        x_values: np.ndarray | Sequence[float],
        y_values: np.ndarray | Sequence[float],
        *,
        minimum_half_span: float = 1e-3,
        pad_fraction: float = 0.08,
    ) -> None:
        """Keep spot-diagram X/Y units physically equal so round spots stay round."""
        x_array = np.asarray(x_values, dtype=float).ravel()
        y_array = np.asarray(y_values, dtype=float).ravel()
        finite = np.isfinite(x_array) & np.isfinite(y_array)
        if np.any(finite):
            x_valid = x_array[finite]
            y_valid = y_array[finite]
            x_min = float(np.min(x_valid))
            x_max = float(np.max(x_valid))
            y_min = float(np.min(y_valid))
            y_max = float(np.max(y_valid))
            center_x = 0.5 * (x_min + x_max)
            center_y = 0.5 * (y_min + y_max)
            half_span = max(
                minimum_half_span,
                0.5 * max(x_max - x_min, y_max - y_min, 1e-12) * (1.0 + 2.0 * pad_fraction),
            )
            analysis_ax.set_xlim(center_x - half_span, center_x + half_span)
            analysis_ax.set_ylim(center_y - half_span, center_y + half_span)
        analysis_ax.set_aspect("equal", adjustable="box")
        analysis_ax.set_box_aspect(1.0)

    def _current_detector_bin_count(
        self,
        sample_count: int,
        *,
        coherent: bool = False,
        detector_model: dict[str, object] | None = None,
    ) -> int:
        sample_count = max(1, int(sample_count or 1))
        auto_min = 24 if coherent else 16
        auto_max = 128 if coherent else 96
        auto_scale = 5 if coherent else 4
        auto_bins = int(np.clip(max(auto_min, round(np.sqrt(sample_count) * auto_scale)), auto_min, auto_max))
        if detector_model:
            detector_bins = str(detector_model.get("bins", "") or "").strip()
            if detector_bins:
                try:
                    return int(np.clip(int(float(detector_bins)), 4, 512))
                except Exception:
                    pass
        text = self._left_mode_text("detector_bins_var", DETECTOR_BINS_DEFAULT).strip()
        if not text or text.lower() in {"auto", "default"}:
            return auto_bins
        try:
            bins = int(float(text))
        except Exception:
            return auto_bins
        return int(np.clip(bins, 4, 512))

    def _current_branch_field_propagation_mm(self) -> float:
        text = self._left_mode_text(
            "branch_field_propagation_mm_var",
            BRANCH_FIELD_PROPAGATION_MM_DEFAULT,
        ).strip()
        try:
            value = float(text)
        except Exception:
            return 0.0
        if not np.isfinite(value):
            return 0.0
        return float(np.clip(value, -1.0e6, 1.0e6))

    def _current_wavefront_style(self) -> str:
        value = getattr(self, "wavefront_style_var", None)
        if value is None:
            return WAVEFRONT_STYLE_DEFAULT
        style = value.get().strip()
        if style in WAVEFRONT_STYLE_VALUES:
            return style
        return WAVEFRONT_STYLE_DEFAULT

    def _current_tolerance_compare_view(self) -> str:
        value = getattr(self, "tolerance_compare_view_var", None)
        if value is None:
            return TOLERANCE_COMPARE_VIEW_DEFAULT
        view = value.get().strip()
        if view in TOLERANCE_COMPARE_VIEW_VALUES:
            return view
        return TOLERANCE_COMPARE_VIEW_DEFAULT

    @staticmethod
    def _convex_hull_area(points: np.ndarray) -> float:
        points = np.asarray(points, dtype=float)
        if points.ndim != 2 or points.shape[0] < 3 or points.shape[1] != 2:
            return 0.0
        sorted_points = sorted((float(x), float(y)) for x, y in points)

        def cross(origin: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
            return (a[0] - origin[0]) * (b[1] - origin[1]) - (a[1] - origin[1]) * (b[0] - origin[0])

        lower: list[tuple[float, float]] = []
        for point in sorted_points:
            while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0.0:
                lower.pop()
            lower.append(point)
        upper: list[tuple[float, float]] = []
        for point in reversed(sorted_points):
            while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0.0:
                upper.pop()
            upper.append(point)
        hull = lower[:-1] + upper[:-1]
        if len(hull) < 3:
            return 0.0
        area = 0.0
        for index, point in enumerate(hull):
            next_point = hull[(index + 1) % len(hull)]
            area += point[0] * next_point[1] - next_point[0] * point[1]
        return abs(area) * 0.5

    @classmethod
    def _wavefront_pupil_quality(
        cls,
        x_pupil: np.ndarray,
        y_pupil: np.ndarray,
        *,
        min_samples: int = 8,
    ) -> tuple[bool, str]:
        x = np.asarray(x_pupil, dtype=float).ravel()
        y = np.asarray(y_pupil, dtype=float).ravel()
        finite = np.isfinite(x) & np.isfinite(y)
        x = x[finite]
        y = y[finite]
        if x.size < min_samples:
            return False, f"only {int(x.size)} finite pupil samples"

        x_span = float(np.ptp(x))
        y_span = float(np.ptp(y))
        max_span = max(x_span, y_span)
        if not np.isfinite(max_span) or max_span <= 1e-10:
            return False, "all pupil coordinates collapsed to one point"
        if min(x_span, y_span) <= max(max_span * 1e-4, 1e-10):
            return False, "pupil coordinates are line-like, not a filled 2-D pupil"

        normalized = np.column_stack([(x - float(np.mean(x))) / max_span, (y - float(np.mean(y))) / max_span])
        unique_points = np.unique(np.round(normalized, decimals=7), axis=0)
        if unique_points.shape[0] < min_samples:
            return False, f"only {int(unique_points.shape[0])} unique pupil coordinates"
        try:
            if np.linalg.matrix_rank(normalized, tol=1e-7) < 2:
                return False, "pupil coordinates are rank-deficient"
        except Exception:
            pass

        hull_area = cls._convex_hull_area(unique_points)
        bbox_area = max(float(np.ptp(unique_points[:, 0]) * np.ptp(unique_points[:, 1])), 1e-12)
        if hull_area <= 1e-7 or hull_area / bbox_area < 0.02:
            return False, "pupil samples do not cover a usable 2-D aperture"
        return True, "filled 2-D pupil"

    def _compare_zemax_wavefront_reference(
        self,
        x_pupil: np.ndarray,
        y_pupil: np.ndarray,
        kraken_waves: np.ndarray,
        wavelength_um: float,
    ) -> dict[str, object] | None:
        reference = self.__dict__.get("_zemax_wavefront_reference", None)
        if reference is None:
            return None
        x = np.asarray(x_pupil, dtype=float).ravel()
        y = np.asarray(y_pupil, dtype=float).ravel()
        kraken = np.asarray(kraken_waves, dtype=float).ravel()
        finite = np.isfinite(x) & np.isfinite(y) & np.isfinite(kraken)
        if np.count_nonzero(finite) < 4:
            return {
                "ok": False,
                "reason": "not enough finite KrakenOS wavefront samples for Zemax comparison",
                "reference_file": reference.path,
            }
        x_norm, y_norm = normalized_pupil_coordinates(x, y)
        candidates = (
            ("as exported", reference.values_waves),
            ("flip Y", np.flipud(reference.values_waves)),
            ("flip X", np.fliplr(reference.values_waves)),
            ("flip X/Y", np.flipud(np.fliplr(reference.values_waves))),
            ("transpose", reference.values_waves.T),
        )
        best: dict[str, object] | None = None
        for orientation, values in candidates:
            sampled = sample_wavefront_grid(values, x_norm, y_norm)
            sampled_corrected = self._remove_wavefront_reference_plane(x_norm, y_norm, sampled)
            kraken_corrected = self._remove_wavefront_reference_plane(x_norm, y_norm, kraken)
            comparison_finite = finite & np.isfinite(sampled_corrected) & np.isfinite(kraken_corrected)
            sample_count = int(np.count_nonzero(comparison_finite))
            if sample_count < 4:
                continue
            residual = np.full_like(kraken, np.nan, dtype=float)
            residual[comparison_finite] = kraken_corrected[comparison_finite] - sampled_corrected[comparison_finite]
            residual_values = residual[comparison_finite]
            residual_rms = float(np.sqrt(np.nanmean(residual_values * residual_values)))
            residual_pv = float(np.nanmax(residual_values) - np.nanmin(residual_values))
            candidate = {
                "ok": True,
                "orientation": orientation,
                "sample_count": sample_count,
                "residual_rms_waves": residual_rms,
                "residual_pv_waves": residual_pv,
                "residual_rms_nm": residual_rms * float(wavelength_um) * 1000.0,
                "residual_pv_nm": residual_pv * float(wavelength_um) * 1000.0,
                "wavelength_um": float(wavelength_um),
                "reference_wavelength_um": float(reference.wavelength_um),
                "reference_file": reference.path,
                "reference_shape": reference.shape,
                "reference_samples_waves": sampled_corrected,
                "residual_samples_waves": residual,
            }
            if best is None or residual_rms < float(best.get("residual_rms_waves", np.inf)):
                best = candidate
        if best is None:
            return {
                "ok": False,
                "reason": "Zemax reference could not be sampled on the KrakenOS pupil coordinates",
                "reference_file": reference.path,
                "reference_shape": reference.shape,
            }
        if abs(float(reference.wavelength_um) - float(wavelength_um)) > max(1e-6, abs(float(wavelength_um)) * 1e-4):
            best["wavelength_note"] = (
                f"reference lambda {reference.wavelength_um:.6g} um differs from UI lambda {float(wavelength_um):.6g} um"
            )
        return best

    @staticmethod
    def _annotate_zemax_wavefront_comparison(axis, comparison: dict[str, object] | None) -> None:
        if axis is None or not comparison or not bool(comparison.get("ok", False)):
            return
        axis.text(
            0.69,
            0.165,
            "Zemax residual RMS {rms:.4g} waves ({rms_nm:.4g} nm)".format(
                rms=float(comparison.get("residual_rms_waves", 0.0)),
                rms_nm=float(comparison.get("residual_rms_nm", 0.0)),
            ),
            ha="left",
            va="center",
            fontsize=5.9,
            color="#1d4ed8",
        )

    def _wavefront_pattern_coordinates(self, pupil) -> tuple[np.ndarray, np.ndarray]:
        previous_rad = getattr(pupil, "rad", 0.0)
        previous_theta = getattr(pupil, "theta", 0.0)
        pupil.rad = self._current_pupil_rad()
        pupil.theta = self._current_pupil_theta()
        numpy_state = None
        try:
            if str(getattr(pupil, "Ptype", "")).strip().lower() == "rand":
                numpy_state = np.random.get_state()
                np.random.seed(self._current_source_seed())
            pupil.Pattern()
            return (
                np.asarray(getattr(pupil, "Cordx", []), dtype=float).ravel(),
                np.asarray(getattr(pupil, "Cordy", []), dtype=float).ravel(),
            )
        finally:
            pupil.rad = previous_rad
            pupil.theta = previous_theta
            if numpy_state is not None:
                np.random.set_state(numpy_state)

    def _wavefront_function_grid(
        self,
        x_pupil: np.ndarray,
        y_pupil: np.ndarray,
        phase_waves: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        x = np.asarray(x_pupil, dtype=float).ravel()
        y = np.asarray(y_pupil, dtype=float).ravel()
        values = np.asarray(phase_waves, dtype=float).ravel()
        finite = np.isfinite(x) & np.isfinite(y) & np.isfinite(values)
        x = x[finite]
        y = y[finite]
        values = values[finite]
        if values.size < 4:
            raise RuntimeError("Not enough finite wavefront samples for Wavefront Function plot")
        quality_ok, quality_note = self._wavefront_pupil_quality(x, y)
        if not quality_ok:
            raise RuntimeError(f"Wavefront Function unavailable: {quality_note}")

        x_scale = float(np.nanmax(np.abs(x)))
        y_scale = float(np.nanmax(np.abs(y)))
        if not np.isfinite(x_scale) or x_scale <= 1e-12:
            x_scale = 1.0
        if not np.isfinite(y_scale) or y_scale <= 1e-12:
            y_scale = 1.0
        x_norm = np.clip(x / x_scale, -1.0, 1.0)
        y_norm = np.clip(y / y_scale, -1.0, 1.0)
        grid_count = max(35, min(90, int(np.sqrt(max(values.size, 1)) * 6)))
        grid_axis = np.linspace(-1.0, 1.0, grid_count)
        xx, yy = np.meshgrid(grid_axis, grid_axis)
        pupil_mask = (xx * xx + yy * yy) <= 1.0
        zz = np.full_like(xx, np.nan, dtype=float)
        if np.ptp(x_norm) > 1e-6 and np.ptp(y_norm) > 1e-6 and values.size >= 10:
            for term_count in (min(28, max(10, values.size // 2)), 21, 15, 10, 6):
                if term_count < 4 or term_count > values.size:
                    continue
                try:
                    active_terms = np.ones(int(term_count), dtype=float)
                    coefficients, *_ = Kos.Zernike_Fitting(x_norm, y_norm, values, active_terms)
                    reconstructed = np.asarray(
                        Kos.Wavefront_Zernike_Phase(xx[pupil_mask], yy[pupil_mask], coefficients),
                        dtype=float,
                    ).ravel()
                    if reconstructed.size == int(np.count_nonzero(pupil_mask)) and np.any(np.isfinite(reconstructed)):
                        zz[pupil_mask] = reconstructed
                        break
                except Exception:
                    continue
        try:
            if not np.any(np.isfinite(zz)):
                from matplotlib.tri import LinearTriInterpolator, Triangulation

                triangulation = Triangulation(x_norm, y_norm)
                interpolator = LinearTriInterpolator(triangulation, values)
                zz = np.ma.asarray(interpolator(xx, yy)).filled(np.nan).astype(float)
        except Exception:
            # Keep the plot usable with sparse/degenerate pupil sets by using a
            # nearest-neighbour surface only inside the normalized pupil.
            sample_xy = np.column_stack([x_norm, y_norm])
            grid_xy = np.column_stack([xx[pupil_mask], yy[pupil_mask]])
            if grid_xy.size:
                diff = grid_xy[:, None, :] - sample_xy[None, :, :]
                nearest = np.argmin(np.sum(diff * diff, axis=2), axis=1)
                zz[pupil_mask] = values[nearest]
        zz[~pupil_mask] = np.nan
        if np.count_nonzero(np.isfinite(zz)) < 8:
            raise RuntimeError("Wavefront Function interpolation produced no finite surface")
        return xx, yy, zz

    def _remove_wavefront_reference_plane(
        self,
        x_pupil: np.ndarray,
        y_pupil: np.ndarray,
        values: np.ndarray,
    ) -> np.ndarray:
        x = np.asarray(x_pupil, dtype=float).ravel()
        y = np.asarray(y_pupil, dtype=float).ravel()
        wavefront = np.asarray(values, dtype=float).ravel()
        finite = np.isfinite(x) & np.isfinite(y) & np.isfinite(wavefront)
        corrected = np.full_like(wavefront, np.nan, dtype=float)
        if np.count_nonzero(finite) < 4:
            return wavefront - float(np.nanmean(wavefront))
        design = np.column_stack([np.ones(np.count_nonzero(finite)), x[finite], y[finite]])
        coeffs, *_ = np.linalg.lstsq(design, wavefront[finite], rcond=None)
        corrected[finite] = wavefront[finite] - (coeffs[0] + coeffs[1] * x[finite] + coeffs[2] * y[finite])
        return corrected

    @staticmethod
    def _plot_axes_nan_segments(axis, x_values: np.ndarray, y_values: np.ndarray, **kwargs) -> None:
        x_values = np.asarray(x_values, dtype=float).ravel()
        y_values = np.asarray(y_values, dtype=float).ravel()
        finite = np.isfinite(x_values) & np.isfinite(y_values)
        start: int | None = None
        for index, is_finite in enumerate(finite):
            if is_finite and start is None:
                start = index
            if (not is_finite or index == finite.size - 1) and start is not None:
                end = index + 1 if is_finite and index == finite.size - 1 else index
                if end - start >= 2:
                    axis.plot(x_values[start:end], y_values[start:end], **kwargs)
                start = None

    @staticmethod
    def _fill_axes_nan_segments(axis, x_values: np.ndarray, y_values: np.ndarray, bottom, **kwargs) -> None:
        x_values = np.asarray(x_values, dtype=float).ravel()
        y_values = np.asarray(y_values, dtype=float).ravel()
        bottom_array = np.broadcast_to(np.asarray(bottom, dtype=float), x_values.shape)
        finite = np.isfinite(x_values) & np.isfinite(y_values)
        start: int | None = None
        for index, is_finite in enumerate(finite):
            if is_finite and start is None:
                start = index
            if (not is_finite or index == finite.size - 1) and start is not None:
                end = index + 1 if is_finite and index == finite.size - 1 else index
                if end - start >= 2:
                    axis.fill_between(
                        x_values[start:end], y_values[start:end], bottom_array[start:end], **kwargs
                    )
                start = None

    def _draw_wavefront_solid_waterfall(
        self,
        axis,
        axis_x: np.ndarray,
        axis_y: np.ndarray,
        base_axis_y: np.ndarray,
        base_corners: list[tuple[float, float]],
    ) -> None:
        """Hidden-line waterfall: opaque slices drawn back-to-front so nearer
        rows occlude farther ones (the Zemax Wavefront Function look). Each
        slice's curtain stops at its own z=0 floor line, leaving the base-plane
        parallelogram visible as an apron around the relief."""
        line_color = "#1f2937"

        # Flat base plane the relief rests on (lowest zorder, drawn first).
        if len(base_corners) >= 3:
            corner_x = [corner[0] for corner in base_corners]
            corner_y = [corner[1] for corner in base_corners]
            axis.fill(corner_x, corner_y, facecolor="#eef2f7", edgecolor="#9aa5b1",
                      linewidth=0.5, zorder=1.0, closed=True)

        n_rows = axis_x.shape[0]
        row_step = 1 if n_rows <= 58 else 2
        rows = list(range(0, n_rows, row_step))

        def row_depth(row_index: int) -> float:
            row_floor = base_axis_y[row_index, :]
            finite_row = row_floor[np.isfinite(row_floor)]
            return float(np.nanmean(finite_row)) if finite_row.size else -np.inf

        # Highest floor rows are farthest back; draw them first so the nearer
        # (lower) rows painted on top hide what sits behind them.
        rows.sort(key=row_depth, reverse=True)
        for draw_index, row_index in enumerate(rows):
            row_x = axis_x[row_index, :]
            row_y = axis_y[row_index, :]
            if np.count_nonzero(np.isfinite(row_x) & np.isfinite(row_y)) < 2:
                continue
            zorder = 2.0 + draw_index * 0.01
            self._fill_axes_nan_segments(
                axis, row_x, row_y, base_axis_y[row_index, :],
                facecolor="white", edgecolor="none", zorder=zorder,
            )
            self._plot_axes_nan_segments(
                axis, row_x, row_y,
                color=line_color, linewidth=0.5, zorder=zorder + 0.004,
            )

    def _wavefront_projected_axes_coordinates(
        self,
        xx: np.ndarray,
        yy: np.ndarray,
        zz: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[tuple[float, float]]]:
        finite_z = zz[np.isfinite(zz)]
        z_scale = float(np.nanpercentile(np.abs(finite_z), 95.0)) if finite_z.size else 1.0
        if not np.isfinite(z_scale) or z_scale <= 1e-12:
            z_scale = float(np.nanmax(np.abs(finite_z))) if finite_z.size else 1.0
        if not np.isfinite(z_scale) or z_scale <= 1e-12:
            z_scale = 1.0
        z_norm = np.clip(zz / z_scale, -1.6, 1.6)
        # Rest the surface on the z=0 base plane (Zemax shows the relief rising
        # from a flat floor, not floating around a centred zero).
        finite_norm = z_norm[np.isfinite(z_norm)]
        z_floor = float(np.nanmin(finite_norm)) if finite_norm.size else 0.0
        z_norm = z_norm - z_floor

        # Orthographic projection tuned to resemble Zemax's Wavefront Function
        # printout: waterfall slices with strong OPD relief, no 3D axes.
        projected_x = 1.04 * xx + 0.08 * yy
        projected_y = 0.20 * yy + 0.82 * z_norm
        finite = np.isfinite(projected_x) & np.isfinite(projected_y)
        if not np.any(finite):
            raise RuntimeError("Wavefront Function projection produced no finite samples")

        plot_left, plot_right = 0.065, 0.945
        plot_bottom, plot_top = 0.265, 0.925
        x_min = float(np.nanmin(projected_x[finite]))
        x_max = float(np.nanmax(projected_x[finite]))
        y_min = float(np.nanmin(projected_y[finite]))
        y_max = float(np.nanmax(projected_y[finite]))
        x_span = max(x_max - x_min, 1e-12)
        y_span = max(y_max - y_min, 1e-12)
        scale = min((plot_right - plot_left) / x_span, (plot_top - plot_bottom) / y_span)
        x_mid = 0.5 * (x_min + x_max)
        y_mid = 0.5 * (y_min + y_max)
        plot_x_mid = 0.5 * (plot_left + plot_right)
        plot_y_mid = 0.5 * (plot_bottom + plot_top)
        axis_x = plot_x_mid + (projected_x - x_mid) * scale
        axis_y = plot_y_mid + (projected_y - y_mid) * scale
        # Per-point z=0 floor line (drops the OPD term). Within a waterfall row
        # yy is constant, so this is the horizontal baseline each slice rests on;
        # kept finite everywhere so the curtain fill always has a bottom edge.
        base_axis_y = plot_y_mid + (0.20 * yy - y_mid) * scale

        # Base-plane parallelogram: the z=0 footprint of the pupil grid box,
        # projected with the same transform so the surface sits on the floor.
        x_lo, x_hi = float(np.nanmin(xx)), float(np.nanmax(xx))
        y_lo, y_hi = float(np.nanmin(yy)), float(np.nanmax(yy))
        base_corners: list[tuple[float, float]] = []
        for corner_x, corner_y in ((x_lo, y_lo), (x_hi, y_lo), (x_hi, y_hi), (x_lo, y_hi)):
            base_px = 1.04 * corner_x + 0.08 * corner_y
            base_py = 0.20 * corner_y
            base_corners.append((
                plot_x_mid + (base_px - x_mid) * scale,
                plot_y_mid + (base_py - y_mid) * scale,
            ))

        axis_x[~finite] = np.nan
        axis_y[~finite] = np.nan
        return axis_x, axis_y, base_axis_y, base_corners

    @staticmethod
    def _wavefront_slice_curvature(values: np.ndarray) -> float:
        values = np.asarray(values, dtype=float)
        if values.ndim != 2 or min(values.shape) < 3:
            return 0.0
        curvatures: list[float] = []
        for line in values:
            finite = np.isfinite(line)
            if np.count_nonzero(finite) < 5:
                continue
            segment = line[finite]
            second = np.diff(segment, n=2)
            if second.size:
                curvatures.append(float(np.nanmean(np.abs(second))))
        return float(np.nanmedian(curvatures)) if curvatures else 0.0

    def _orient_wavefront_waterfall_grid(
        self,
        xx: np.ndarray,
        yy: np.ndarray,
        zz: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        row_curvature = self._wavefront_slice_curvature(zz)
        column_curvature = self._wavefront_slice_curvature(zz.T)
        if column_curvature > row_curvature * 1.15:
            return yy.T, xx.T, zz.T
        return xx, yy, zz

    def _plot_wavefront_function_unavailable(
        self,
        analysis_ax,
        *,
        reason: str,
        sample_count: int,
        phase_pv: float,
        phase_rms: float,
        phase_method: str,
        reference_note: str,
    ):
        analysis_ax.clear()
        analysis_ax.set_xlim(0.0, 1.0)
        analysis_ax.set_ylim(0.0, 1.0)
        analysis_ax.set_axis_off()

        border_color = "#111111"
        analysis_ax.add_patch(Rectangle((0.03, 0.03), 0.94, 0.92, fill=False, linewidth=0.85, edgecolor=border_color))
        analysis_ax.plot([0.03, 0.97], [0.235, 0.235], color=border_color, linewidth=0.7)
        analysis_ax.plot([0.03, 0.97], [0.195, 0.195], color=border_color, linewidth=0.7)
        analysis_ax.plot([0.68, 0.68], [0.03, 0.195], color=border_color, linewidth=0.7)
        analysis_ax.text(0.5, 0.214, "WAVEFRONT FUNCTION", ha="center", va="center", fontsize=9.2)

        analysis_ax.text(
            0.5,
            0.74,
            "Wavefront Function unavailable",
            ha="center",
            va="center",
            fontsize=7.8,
            color="#7f1d1d",
        )
        diagnostic = (
            f"KrakenOS returned {sample_count} phase samples, but their pupil coordinates are not a filled "
            f"2-D aperture: {reason}. Use Phase (unwrapped) to inspect the raw samples, or run Wavefront "
            "Function on an image surface with a valid sequential pupil."
        )
        wrapped_lines = textwrap.wrap(diagnostic, width=58)
        for line_index, line in enumerate(wrapped_lines[:7]):
            analysis_ax.text(
                0.5,
                0.64 - line_index * 0.04,
                line,
                ha="center",
                va="center",
                fontsize=5.6,
                color="#1f2937",
            )

        analysis_ax.text(
            0.045,
            0.118,
            f"P-V: {phase_pv:.4g} waves   RMS: {phase_rms:.4g} waves",
            ha="left",
            va="center",
            fontsize=7.2,
        )
        analysis_ax.text(0.045, 0.072, "SURFACE: IMAGE", ha="left", va="center", fontsize=7.2)
        analysis_ax.text(0.69, 0.118, "KRAKENOS UI", ha="left", va="center", fontsize=7.2)
        analysis_ax.text(0.69, 0.072, f"{phase_method}; invalid pupil", ha="left", va="center", fontsize=5.7)
        analysis_ax.set_box_aspect(0.78)
        return analysis_ax

    def _plot_wavefront_function_analysis(
        self,
        analysis_ax,
        x_pupil: np.ndarray,
        y_pupil: np.ndarray,
        phase_waves_centered: np.ndarray,
        *,
        phase_pv: float,
        phase_rms: float,
        phase_method: str,
        reference_note: str,
        pupil_quality: tuple[bool, str] | None = None,
        coordinate_note: str = "Phase pupil coordinates",
    ):
        quality_ok, quality_note = pupil_quality or self._wavefront_pupil_quality(x_pupil, y_pupil)
        if not quality_ok:
            sample_count = int(np.count_nonzero(np.isfinite(x_pupil) & np.isfinite(y_pupil)))
            return self._plot_wavefront_function_unavailable(
                analysis_ax,
                reason=quality_note,
                sample_count=sample_count,
                phase_pv=phase_pv,
                phase_rms=phase_rms,
                phase_method=phase_method,
                reference_note=reference_note,
            )
        xx, yy, zz = self._wavefront_function_grid(
            x_pupil,
            y_pupil,
            phase_waves_centered,
        )
        finite_z = zz[np.isfinite(zz)]
        z_span = float(np.nanmax(finite_z) - np.nanmin(finite_z)) if finite_z.size else 0.0
        max_slice_curvature = max(
            self._wavefront_slice_curvature(zz),
            self._wavefront_slice_curvature(zz.T),
        )
        shape_note = ""
        if z_span > 1e-12 and max_slice_curvature / z_span < 1e-5:
            shape_note = "near-flat/cylindrical samples"
        xx, yy, zz = self._orient_wavefront_waterfall_grid(xx, yy, zz)
        axis_x, axis_y, base_axis_y, base_corners = self._wavefront_projected_axes_coordinates(xx, yy, zz)
        analysis_ax.clear()
        analysis_ax.set_xlim(0.0, 1.0)
        analysis_ax.set_ylim(0.0, 1.0)
        analysis_ax.set_axis_off()

        border_color = "#111111"
        # Outer Zemax-style frame and bottom report/title table.
        analysis_ax.add_patch(Rectangle((0.03, 0.03), 0.94, 0.92, fill=False, linewidth=0.85, edgecolor=border_color))
        analysis_ax.plot([0.03, 0.97], [0.235, 0.235], color=border_color, linewidth=0.7)
        analysis_ax.plot([0.03, 0.97], [0.195, 0.195], color=border_color, linewidth=0.7)
        analysis_ax.plot([0.68, 0.68], [0.03, 0.195], color=border_color, linewidth=0.7)
        analysis_ax.text(0.5, 0.214, "WAVEFRONT FUNCTION", ha="center", va="center", fontsize=9.2)

        self._draw_wavefront_solid_waterfall(analysis_ax, axis_x, axis_y, base_axis_y, base_corners)

        analysis_ax.text(
            0.045,
            0.118,
            f"P-V: {phase_pv:.4g} waves   RMS: {phase_rms:.4g} waves",
            ha="left",
            va="center",
            fontsize=7.2,
        )
        analysis_ax.text(0.045, 0.072, "SURFACE: IMAGE", ha="left", va="center", fontsize=7.2)
        analysis_ax.text(0.69, 0.118, "KRAKENOS UI", ha="left", va="center", fontsize=7.2)
        footer_note = "pattern coords" if coordinate_note != "Phase pupil coordinates" else "piston/tilt removed"
        analysis_ax.text(0.69, 0.072, f"{phase_method}; {footer_note}", ha="left", va="center", fontsize=6.4)
        if shape_note:
            analysis_ax.text(0.045, 0.165, shape_note, ha="left", va="center", fontsize=6.4, color="#7f1d1d")
        analysis_ax.set_box_aspect(0.78)
        return analysis_ax
