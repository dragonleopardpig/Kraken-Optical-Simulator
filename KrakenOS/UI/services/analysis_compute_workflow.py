"""Analysis progress, clipboard reports, and optimization workflow helpers.

This mixin owns editor-side report/progress plumbing and the optimization
worker lifecycle.  Heavy worker entry points remain late-bound through
``layout_editor.py`` for multiprocessing compatibility.
"""

from __future__ import annotations

import csv
from pathlib import Path
from queue import Empty
import os
import shutil
import signal
import subprocess
import time
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp

import numpy as np

import KrakenOS as Kos
from KrakenOS.Optimization import (
    OPERAND_REGISTRY,
    VARIABLE_REGISTRY,
    MeritFunction,
    MTFAtFrequencyOperand,
    OpticalVariable,
)
from KrakenOS.Optimization.pygmo_backend import probe_pygmo_backend
from KrakenOS.UI.services.catalog_metadata import _normalize_metal_catalog_specs
from KrakenOS.UI.services.surface_value_parsing import _native_variable_matches
from KrakenOS.UI.source_trace_helpers import PUPIL_PATTERN_DEFAULT, SOURCE_MODEL_DEFAULT
from KrakenOS.UI.surface_table_model import SurfaceRow, surface_rows_to_specs

DEBUG_LOG_PATH = Path.home() / ".cache" / "krakenos" / "logs" / "kraken_debug_latest.log"


def _layout_module():
    from KrakenOS.UI import layout_editor as layout_editor_module

    return layout_editor_module


def _build_system_from_specs(row_specs: list[dict], *, build: int = 0, setup=None) -> object:
    return _layout_module()._build_system_from_specs(row_specs, build=build, setup=setup)


def _optional_cupy():
    return _layout_module()._optional_cupy()


def _optional_torch():
    return _layout_module()._optional_torch()


def _run_optimization_job(*args, **kwargs):
    return _layout_module()._run_optimization_job(*args, **kwargs)


class AnalysisComputeWorkflowMixin:
    def _set_results(self, items) -> None:
        self.results_table.delete(*self.results_table.get_children())
        measure = tkfont.nametofont("TkDefaultFont").measure
        property_width = measure("Property") + 18
        for key, value in items:
            self.results_table.insert("", "end", values=(key, value))
            property_width = max(property_width, measure(str(key)) + 18)
        self.results_table.column("property", width=min(property_width, 150), anchor="w", stretch=False)

    def append_debug(self, message: str) -> None:
        if not message:
            return
        line = message.rstrip()
        self.debug_text.insert("end", line + "\n")
        self.debug_text.see("end")
        self._append_debug_log(line)
        self.update_idletasks()

    def _bind_text_copy_shortcuts(self, widget: tk.Text) -> None:
        for sequence in ("<Control-c>", "<Control-C>", "<Control-Insert>", "<<Copy>>", "<Control-KeyPress-c>", "<Control-KeyPress-C>"):
            widget.bind(sequence, lambda _e, w=widget: self._copy_selection_from_text_widget(w), add="+")

    def _bind_text_context_menu(self, widget: tk.Text) -> None:
        widget.bind("<Button-3>", lambda e, w=widget: self._show_text_context_menu(e, w), add="+")

    def _bind_global_copy_shortcuts(self) -> None:
        for sequence in ("<Control-c>", "<Control-C>", "<Control-Insert>"):
            self.bind_all(sequence, self._copy_selection_from_focus, add="+")
        for sequence in ("<Control-v>", "<Control-V>", "<Shift-Insert>"):
            self.bind_all(sequence, self._paste_rows_from_focus, add="+")

    def _show_text_context_menu(self, event, widget: tk.Text):
        if self._text_popup_menu is None:
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label="Copy Selected", command=lambda: self._copy_selection_from_text_widget(widget))
            menu.add_command(label="Copy All", command=lambda: self._copy_all_from_text_widget(widget))
            self._text_popup_menu = menu
        else:
            self._text_popup_menu.entryconfigure(0, command=lambda: self._copy_selection_from_text_widget(widget))
            self._text_popup_menu.entryconfigure(1, command=lambda: self._copy_all_from_text_widget(widget))
        self._text_popup_menu.tk_popup(event.x_root, event.y_root)
        return "break"

    def _safe_focus_get(self):
        try:
            return self.focus_get()
        except (KeyError, tk.TclError):
            return None

    def _copy_selection_from_focus(self, _event=None):
        candidates = []
        focused = self._safe_focus_get()
        if focused is getattr(self, "table", None):
            return self.copy_selected_rows_to_clipboard(_event)
        if isinstance(focused, tk.Text):
            candidates.append(focused)
        for widget in (getattr(self, "debug_text", None), getattr(self, "progress_text", None)):
            if isinstance(widget, tk.Text) and widget not in candidates:
                candidates.append(widget)
        for widget in candidates:
            try:
                text = widget.get("sel.first", "sel.last")
            except tk.TclError:
                continue
            if not text:
                continue
            try:
                ok, backend = self._copy_text_to_clipboard(text)
                if ok:
                    self.status_var.set(f"Selected text copied to clipboard ({backend})")
                else:
                    self.status_var.set("Copy failed")
                return "break"
            except Exception as exc:
                self.append_debug(f"Copy selected text failed: {exc}")
                return "break"
        return None

    def _paste_rows_from_focus(self, _event=None):
        focused = self._safe_focus_get()
        if focused is getattr(self, "table", None):
            return self.paste_rows_from_clipboard(_event)
        return None

    def _copy_selection_from_text_widget(self, widget: tk.Text) -> str:
        try:
            text = widget.get("sel.first", "sel.last")
        except tk.TclError:
            self.status_var.set("No text selected")
            return "break"
        if not text:
            self.status_var.set("No text selected")
            return "break"
        try:
            ok, backend = self._copy_text_to_clipboard(text)
            if ok:
                self.status_var.set(f"Selected text copied to clipboard ({backend})")
            else:
                self.status_var.set("Copy failed")
        except Exception as exc:
            self.append_debug(f"Copy selected text failed: {exc}")
        return "break"

    def _copy_all_from_text_widget(self, widget: tk.Text) -> str:
        text = widget.get("1.0", "end-1c")
        if not text:
            self.status_var.set("No text to copy")
            return "break"
        try:
            ok, backend = self._copy_text_to_clipboard(text)
            if ok:
                self.status_var.set(f"All text copied to clipboard ({backend})")
            else:
                self.status_var.set("Copy failed")
        except Exception as exc:
            self.append_debug(f"Copy all text failed: {exc}")
        return "break"

    def _copy_text_to_clipboard(self, text: str) -> tuple[bool, str]:
        tools = (
            ("wl-copy", ["wl-copy"]),
            ("xclip", ["xclip", "-selection", "clipboard"]),
            ("xsel", ["xsel", "--clipboard", "--input"]),
        )
        encoded = text.encode("utf-8", errors="replace")
        for label, cmd in tools:
            if shutil.which(cmd[0]) is None:
                continue
            try:
                subprocess.run(cmd, input=encoded, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True, label
            except Exception:
                continue
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update()
            return True, "Tk"
        except Exception:
            return False, "none"

    def copy_debug_to_clipboard(self) -> None:
        try:
            self._copy_all_from_text_widget(self.debug_text)
        except Exception as exc:
            self.append_debug(f"Copy debug failed: {exc}")

    def _phase2_report_text(self) -> str:
        summary = self._phase2_feature_summary()
        lines = [
            "# KrakenOS UI Phase 2 Report",
            "",
            f"Source: {summary['source_summary']}",
            f"Error-map surfaces: {summary['error_map_count']}",
        ]
        for row_text in summary["error_map_rows"]:
            lines.append(f"- {row_text}")
        if summary["max_error_pv"] is not None:
            lines.append(f"Max error PV: {float(summary['max_error_pv']):.6g}")
            lines.append(f"Max error RMS: {float(summary['max_error_rms']):.6g}")
        lines.extend(
            [
                f"Coating surfaces: {summary['coating_count']}",
            ]
        )
        for row_text in summary["coating_rows"]:
            lines.append(f"- {row_text}")
        lines.append(f"Metal catalogs: {summary['metal_catalog_count']}")
        for index, metal in enumerate(getattr(self, "metal_catalogs", []) or []):
            name = str(metal.get("name", f"Metal {index}")) if isinstance(metal, dict) else str(metal)
            lines.append(f"- {index}: {name}")
        return "\n".join(lines).strip() + "\n"

    def copy_phase2_report_to_clipboard(self) -> None:
        try:
            text = self._phase2_report_text()
            ok, backend = self._copy_text_to_clipboard(text)
            self.append_debug(text)
            if ok:
                self.status_var.set(f"Phase 2 report copied to clipboard ({backend}).")
            else:
                self.status_var.set("Phase 2 report written to Debug; clipboard unavailable.")
        except Exception as exc:
            self.append_debug(f"Phase 2 report failed: {exc}")

    def copy_wavefront_fit_report_to_clipboard(self) -> None:
        try:
            text = str(getattr(self, "_last_wavefront_fit_report", "")).strip()
            if not text:
                self.status_var.set("Run Zernike analysis before copying the wavefront fit report.")
                return
            text = "# KrakenOS UI Wavefront Fit Report\n\n" + text + "\n"
            ok, backend = self._copy_text_to_clipboard(text)
            self.append_debug(text)
            if ok:
                self.status_var.set(f"Wavefront fit report copied to clipboard ({backend}).")
            else:
                self.status_var.set("Wavefront fit report written to Debug; clipboard unavailable.")
        except Exception as exc:
            self.append_debug(f"Wavefront fit report failed: {exc}")

    def export_wavefront_csv(self) -> None:
        rows = list(getattr(self, "_last_wavefront_samples", []) or [])
        if not rows:
            messagebox.showinfo("Export Wavefront CSV", "Run Wavefront or Zernike analysis before exporting wavefront samples.", parent=self)
            return
        path = filedialog.asksaveasfilename(
            title="Export Wavefront Samples CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*")],
            parent=self,
        )
        if not path:
            return
        columns = (
            "sample",
            "x_pupil",
            "y_pupil",
            "phase_waves",
            "display_value",
            "zemax_reference_waves",
            "zemax_residual_waves",
            "zemax_reference_file",
            "reconstructed_waves",
            "residual_waves",
            "style",
            "phase_method",
            "wavelength_um",
        )
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        self.status_var.set(f"Wavefront samples CSV exported: {Path(path).name}")

    def export_zernike_csv(self) -> None:
        rows = list(getattr(self, "_last_zernike_coefficients", []) or [])
        if not rows:
            messagebox.showinfo("Export Zernike CSV", "Run Zernike analysis before exporting coefficients.", parent=self)
            return
        path = filedialog.asksaveasfilename(
            title="Export Zernike Coefficients CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*")],
            parent=self,
        )
        if not path:
            return
        columns = (
            "index",
            "label",
            "coefficient_waves",
            "terms",
            "samples",
            "phase_method",
            "phase_pv_waves",
            "phase_rms_waves",
            "residual_rms_waves",
            "residual_pv_waves",
            "rms_chief_waves",
            "rms_centroid_waves",
            "fitting_error_waves",
            "wavelength_um",
        )
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        self.status_var.set(f"Zernike coefficients CSV exported: {Path(path).name}")

    def _reset_debug_log(self) -> None:
        try:
            DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            DEBUG_LOG_PATH.write_text("", encoding="utf-8")
        except Exception:
            pass

    def _append_debug_log(self, line: str) -> None:
        try:
            with DEBUG_LOG_PATH.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except Exception:
            pass

    def append_progress(self, message: str) -> None:
        if not message:
            return
        self.progress_text.insert("end", message.rstrip() + "\n")
        self.progress_text.see("end")
        self.update_idletasks()

    def _begin_analysis_progress(self, label: str) -> None:
        if self.optimization_running:
            return
        self.progress_spinner_var.set("...")
        self.progress_percent_var.set("working")
        self.progress_bar_var.set(0.0)
        self.append_progress(f"{label} started.")

    def _update_analysis_progress(self, label: str, done: int | None = None, total: int | None = None) -> None:
        if self.optimization_running:
            return
        frames = ("|", "/", "-", "\\")
        self.progress_spinner_var.set(frames[self._spinner_phase % len(frames)])
        self._spinner_phase += 1
        if done is not None and total is not None and total > 0:
            percent = max(0.0, min(100.0, (done / total) * 100.0))
            self.progress_percent_var.set(f"{int(percent)}% ({done}/{total})")
            self.progress_bar_var.set(percent)
        else:
            self.progress_percent_var.set(label)
        self.update_idletasks()

    def _finish_analysis_progress(self, label: str, success: bool = True) -> None:
        if self.optimization_running:
            return
        self.progress_spinner_var.set("ok" if success else "err")
        self.progress_percent_var.set("100%" if success else "failed")
        self.progress_bar_var.set(100.0 if success else 0.0)
        self.append_progress(f"{label} {'completed' if success else 'failed'}.")

    def _set_analysis_parallel_status(self, label: str, workers: int = 1, parallel_capable: bool = False) -> None:
        self._last_analysis_label = str(label)
        self._last_analysis_workers = max(1, int(workers))
        self._last_analysis_parallel_capable = bool(parallel_capable)
        self._last_analysis_accelerator = "CPU"

    def _set_analysis_accelerator(self, label: str) -> None:
        self._last_analysis_accelerator = str(label)

    def _analysis_parallel_summary(self) -> str:
        workers = max(1, int(self._last_analysis_workers))
        if workers <= 1:
            return "workers: 1"
        if self._last_analysis_parallel_capable:
            return f"workers: {workers} (parallel)"
        return f"workers: {workers}"

    def _analysis_compute_summary(self) -> str:
        return f"{self._analysis_parallel_summary()} | {self._last_analysis_accelerator}"

    def _report_compute_backends(self) -> None:
        if self._gpu_backend_reported:
            return
        self._gpu_backend_reported = True
        backend_pref = os.getenv("KRAKEN_POSTPROC_BACKEND", "auto").strip().lower()
        if backend_pref not in {"auto", "torch", "cupy", "cpu"}:
            backend_pref = "auto"
        self.append_debug(f"Post-processing backend preference: {backend_pref}")

        torch = _optional_torch()
        if torch is None:
            self.append_debug("Torch backend: unavailable.")
        else:
            try:
                if bool(torch.cuda.is_available()):
                    self.append_debug(f"Torch backend: CUDA available ({torch.cuda.device_count()} device(s)).")
                else:
                    self.append_debug("Torch backend: installed, CUDA not available.")
            except Exception as exc:
                self.append_debug(f"Torch backend: probe failed: {exc}")

        cp = _optional_cupy()
        if cp is None:
            self.append_debug("GPU backend: CuPy unavailable, PSF/MTF post-processing will use CPU.")
            return
        try:
            device_count = int(cp.cuda.runtime.getDeviceCount())
        except Exception:
            device_count = 0
        if device_count > 0:
            self.append_debug(f"GPU backend: CuPy available, detected {device_count} CUDA device(s).")
        else:
            self.append_debug("GPU backend: CuPy import succeeded, but no CUDA devices were detected.")

    def _update_optimization_button_state(self) -> None:
        button = getattr(self, "optimization_start_stop_button", None)
        if button is None:
            return
        running = bool(getattr(self, "optimization_running", False))
        try:
            button.configure(
                text="Stop Optimization" if running else "Start Optimization",
                command=self.stop_optimization if running else self.start_optimization,
            )
        except Exception:
            pass

    def _update_progress_indicators(self) -> None:
        self._update_optimization_button_state()
        if not self.optimization_running or self.optimization_context is None:
            self.progress_spinner_var.set("idle")
            self.progress_percent_var.set("0%")
            self.progress_bar_var.set(0.0)
            return
        done = int(self.optimization_context.get("generation_done", 0))
        total = max(1, int(self.optimization_context.get("generations_total", 1)))
        percent = max(0.0, min(100.0, (done / total) * 100.0))
        self.progress_percent_var.set(f"{int(percent)}% ({done}/{total})")
        self.progress_bar_var.set(percent)

    @staticmethod
    def _pick_image_plane_data(rays):
        try:
            X, Y, Z, L, M, N = rays.pick(-1, coordinates="local")
            if np.asarray(X).size:
                return X, Y, Z, L, M, N
        except Exception:
            pass
        return rays.pick(-1)

    def _build_analysis_rays(
        self,
        system,
        wavelength: float,
        sample_count: int | None = None,
        pattern: str = "hexapolar",
        *,
        surface_index: int | None = None,
        aperture_type: str | None = None,
        aperture_value: float | None = None,
        field_type: str | None = None,
        field_x: float | None = None,
        field_y: float | None = None,
    ):
        rays = Kos.raykeeper(system)
        random_source_bundle = self._build_random_source_bundle(sample_count)
        if random_source_bundle is not None:
            Kos.TraceLoop(*random_source_bundle, wavelength, rays, clean=1)
            return rays
        pupil = Kos.PupilCalc(
            system,
            self._analysis_surface_index() if surface_index is None else int(surface_index),
            wavelength,
            self._current_aperture_type() if aperture_type is None else str(aperture_type),
            self._current_aperture_value() if aperture_value is None else float(aperture_value),
        )
        pupil.Samp = max(2, int(sample_count if sample_count is not None else self._current_ray_count()))
        pupil.Ptype = self._current_analysis_pupil_pattern(pattern) if pattern == "hexapolar" else pattern

        clean = 1
        resolved_field_type = field_type or ("angle" if self._current_object_mode() == "Infinity" else "height")
        resolved_field_x = 0.0 if field_x is None else float(field_x)
        resolved_field_y = field_y
        if resolved_field_type == "angle":
            pupil.FieldType = "angle"
            field_values = (
                [float(resolved_field_y)]
                if resolved_field_y is not None
                else self._sample_field_values(self._current_field_angle_deg())
            )
            for value in field_values:
                pupil.FieldX = resolved_field_x
                pupil.FieldY = float(value)
                x, y, z, L, M, N = self._pupil_pattern_bundle(pupil)
                Kos.TraceLoop(x, y, z, L, M, N, wavelength, rays, clean=clean)
                clean = 0
        else:
            pupil.FieldType = "height"
            field_values = (
                [float(resolved_field_y)]
                if resolved_field_y is not None
                else self._sample_field_values(self._current_field_height())
            )
            for value in field_values:
                pupil.FieldX = resolved_field_x
                pupil.FieldY = float(value)
                x, y, z, L, M, N = self._pupil_pattern_bundle(pupil)
                Kos.TraceLoop(x, y, z, L, M, N, wavelength, rays, clean=clean)
                clean = 0
        return rays

    def _serializable_row_specs(self) -> list[dict]:
        return self._serializable_specs_for_rows(self.rows)

    def _serializable_specs_for_rows(self, rows: list[SurfaceRow]) -> list[dict]:
        metal_catalogs = _normalize_metal_catalog_specs(getattr(self, "metal_catalogs", []))
        specs = surface_rows_to_specs(rows, metal_catalogs=metal_catalogs)
        for row, spec in zip(rows, specs):
            if type(self)._is_open3d_promoted_optical_solid_row(row):
                spec["axis_move"] = 0.0
        return specs

    def _mtf_worker_count(self, ray_count: int) -> int:
        cpu_total = max(1, int(os.cpu_count() or 1))
        if ray_count <= 1 or cpu_total <= 1:
            return 1
        optimization_workers_var = self.__dict__.get("optimization_workers_var")
        if optimization_workers_var is not None:
            selected = optimization_workers_var.get().strip()
            if selected and selected.lower() != "auto":
                try:
                    parsed = int(selected)
                    if parsed > 0:
                        return self._cap_analysis_worker_count(max(1, min(parsed, cpu_total, ray_count)))
                except ValueError:
                    pass
        if ray_count < 2048:
            return 1
        auto_workers = self._optimization_worker_count()
        requested = max(1, min(auto_workers, cpu_total, ray_count, max(1, ray_count // 2048)))
        return self._cap_analysis_worker_count(requested)

    def _optimization_worker_count(self) -> int:
        cpu_total = max(1, int(os.cpu_count() or 1))
        optimization_workers_var = self.__dict__.get("optimization_workers_var")
        if optimization_workers_var is not None:
            selected = optimization_workers_var.get().strip()
            if selected and selected.lower() != "auto":
                try:
                    parsed = int(selected)
                    if parsed > 0:
                        return self._cap_analysis_worker_count(max(1, min(parsed, cpu_total)))
                except ValueError:
                    pass
        configured = os.getenv("KRAKEN_OPT_WORKERS", "").strip()
        if configured:
            try:
                parsed = int(configured)
                if parsed > 0:
                    return self._cap_analysis_worker_count(max(1, min(parsed, cpu_total)))
            except ValueError:
                pass
        requested = 1 if cpu_total <= 1 else max(2, cpu_total - 1)
        return self._cap_analysis_worker_count(requested)

    def _optimization_parallel_enabled(self) -> bool:
        parallel_pref = os.getenv("KRAKEN_OPT_PARALLEL", "1").strip().lower()
        return parallel_pref not in {"0", "false", "off", "no"}

    def _optimization_preflight_messages(
        self,
        merit: MeritFunction | None,
        variables: list[OpticalVariable] | None,
        optimization_workers: int,
        parallel_enabled: bool,
    ) -> tuple[bool, list[str]]:
        backend_ok, backend_message = probe_pygmo_backend()
        messages = [
            ("Optimization backend available: " if backend_ok else "Optimization backend unavailable: ")
            + backend_message
        ]
        if merit is not None and variables is not None:
            messages.append(
                "Optimization preflight: "
                f"variables={len(variables)}, operands={len(merit.operands)}, "
                f"workers={max(1, int(optimization_workers))}."
            )
            has_mtf_operand = any(isinstance(operand, MTFAtFrequencyOperand) for operand in merit.operands)
            if has_mtf_operand and int(optimization_workers) > 1:
                messages.append(
                    "Optimization preflight: MTF operands use internal MTF chunk workers "
                    "instead of pygmo mp_bfe."
                )
            elif parallel_enabled and int(optimization_workers) > 1:
                messages.append("Optimization preflight: pygmo mp_bfe parallel population evaluation is enabled.")
            elif not parallel_enabled:
                messages.append(
                    "Optimization preflight: KRAKEN_OPT_PARALLEL disables "
                    "pygmo mp_bfe parallel evaluation."
                )
        return backend_ok, messages

    def check_optimization_backend(self) -> None:
        parallel_enabled = self._optimization_parallel_enabled()
        optimization_workers = self._optimization_worker_count() if parallel_enabled else 1
        ok, messages = self._optimization_preflight_messages(None, None, optimization_workers, parallel_enabled)
        for message in messages:
            self.append_progress(message)
        if ok:
            self.status_var.set("Optimization backend available.")
        else:
            self.status_var.set("Optimization backend unavailable.")

    @staticmethod
    def _available_memory_bytes() -> int:
        if os.name == "posix":
            try:
                with open("/proc/meminfo", "r", encoding="utf-8") as handle:
                    for line in handle:
                        if line.startswith("MemAvailable:"):
                            parts = line.split()
                            if len(parts) >= 2:
                                return max(0, int(parts[1])) * 1024
            except Exception:
                pass
        return 0

    def _cap_analysis_worker_count(self, requested: int) -> int:
        requested = max(1, int(requested))
        available = self._available_memory_bytes()
        if available <= 0:
            return requested
        reserve_mb = max(1024, int(os.getenv("KRAKEN_ANALYSIS_RESERVE_MB", "2048") or 2048))
        per_worker_mb = max(128, int(os.getenv("KRAKEN_ANALYSIS_WORKER_MB", "768") or 768))
        usable = max(0, available - reserve_mb * 1024 * 1024)
        memory_limited = max(1, usable // (per_worker_mb * 1024 * 1024)) if usable > 0 else 1
        return max(1, min(requested, int(memory_limited)))

    def _ensure_analysis_executor(self, worker_count: int) -> ProcessPoolExecutor | None:
        worker_count = self._cap_analysis_worker_count(max(1, int(worker_count)))
        if worker_count <= 1:
            return None
        analysis_executor = self.__dict__.get("_analysis_executor")
        analysis_executor_workers = int(self.__dict__.get("_analysis_executor_workers", 0) or 0)
        if analysis_executor is not None and analysis_executor_workers == worker_count:
            return analysis_executor
        self._shutdown_analysis_executor()
        mp_context = None
        if os.name == "posix":
            try:
                mp_context = mp.get_context("spawn")
            except Exception:
                mp_context = None
        if mp_context is not None:
            self._analysis_executor = ProcessPoolExecutor(max_workers=worker_count, mp_context=mp_context)
        else:
            self._analysis_executor = ProcessPoolExecutor(max_workers=worker_count)
        self._analysis_executor_workers = worker_count
        return self._analysis_executor

    def _shutdown_analysis_executor(self) -> None:
        analysis_executor = self.__dict__.get("_analysis_executor")
        if analysis_executor is not None:
            processes = list(getattr(analysis_executor, "_processes", {}).values())
            try:
                analysis_executor.shutdown(wait=False, cancel_futures=True)
            except Exception:
                pass
            for process in processes:
                if process is None:
                    continue
                try:
                    if process.is_alive():
                        process.terminate()
                except Exception:
                    pass
            deadline = time.monotonic() + 0.5
            for process in processes:
                if process is None:
                    continue
                try:
                    remaining = max(0.0, deadline - time.monotonic())
                    process.join(timeout=remaining)
                except Exception:
                    pass
            for process in processes:
                if process is None:
                    continue
                try:
                    if process.is_alive():
                        process.kill()
                except Exception:
                    pass
                try:
                    process.join(timeout=0.1)
                except Exception:
                    pass
            self._analysis_executor = None
            self._analysis_executor_workers = 0

    @staticmethod
    def _terminate_process_group(pid: int, *, force: bool = False) -> None:
        if pid <= 0 or os.name != "posix":
            return
        signals = (signal.SIGTERM, signal.SIGKILL) if force else (signal.SIGTERM,)
        for sig in signals:
            try:
                os.killpg(pid, sig)
            except ProcessLookupError:
                return
            except Exception:
                break
            if sig == signal.SIGTERM:
                time.sleep(0.05)

    def _shutdown_optimization_worker(self, force: bool = False) -> None:
        if self._optimization_stop_event is not None:
            try:
                self._optimization_stop_event.set()
            except Exception:
                pass
        process = self._optimization_process
        if process is not None:
            try:
                process.join(timeout=0.15)
            except Exception:
                pass
            try:
                if force and process.is_alive():
                    self._terminate_process_group(int(process.pid or 0), force=True)
            except Exception:
                pass
            try:
                if process.is_alive():
                    process.join(timeout=0.15)
            except Exception:
                pass
            try:
                if not process.is_alive():
                    process.close()
            except Exception:
                pass
        queue = self._optimization_queue
        if queue is not None:
            try:
                queue.close()
            except Exception:
                pass
        self._optimization_process = None
        self._optimization_queue = None
        self._optimization_stop_event = None


    def _pupil_model_inputs(
        self,
        system,
        *,
        build_reference: bool,
    ) -> tuple[object, list[SurfaceRow], int]:
        pupil_system = system
        pupil_rows = self.rows
        if build_reference and any(row.surface == "Mirror" for row in self.rows):
            pupil_rows, _last_source_index = self._paraxial_reference_rows_for_layout(self.rows)
            pupil_system = _build_system_from_specs(self._serializable_specs_for_rows(pupil_rows), build=0)
        pupil_surface_index = self._pupil_surface_index_for_rows(pupil_rows)
        return pupil_system, pupil_rows, pupil_surface_index

    def _start_progress_spinner(self) -> None:
        if self._spinner_after_id is not None:
            self.after_cancel(self._spinner_after_id)
            self._spinner_after_id = None
        self._spinner_phase = 0
        self._animate_progress_spinner()

    def _stop_progress_spinner(self) -> None:
        if self._spinner_after_id is not None:
            self.after_cancel(self._spinner_after_id)
            self._spinner_after_id = None
        if not self.optimization_running:
            self.progress_spinner_var.set("idle")

    def _animate_progress_spinner(self) -> None:
        if not self.optimization_running:
            self._spinner_after_id = None
            self.progress_spinner_var.set("idle")
            return
        frames = ("|", "/", "-", "\\")
        self.progress_spinner_var.set(frames[self._spinner_phase % len(frames)])
        self._spinner_phase += 1
        self._spinner_after_id = self.after(120, self._animate_progress_spinner)

    @staticmethod
    def _optional_finite_float(value) -> float | None:
        if value is None:
            return None
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        if not np.isfinite(numeric):
            return None
        return float(numeric)

    @classmethod
    def _format_optional_float(cls, value, fmt: str = ".4g", *, scale: float = 1.0, suffix: str = "") -> str:
        numeric = cls._optional_finite_float(value)
        if numeric is None:
            return "Unavailable"
        return f"{numeric * float(scale):{fmt}}{suffix}"

    def _field_launch_sample_summary(self) -> dict[str, object]:
        requested = max(1, int(self._requested_field_count()))
        basis, unit, span = self._field_sampling_basis_span()
        sign = -1.0 if basis == "angle" and float(self._current_field_angle_deg()) < 0.0 else 1.0
        if basis == "object height":
            sign = -1.0 if float(self._current_field_height()) < 0.0 else 1.0
        maximum = float(span) * sign
        active = self._field_sampling_is_active()
        values = [float(value) for value in self._sample_field_values(maximum)] if active else [0.0]
        if not values:
            values = [0.0]
        unique_values = sorted({round(float(value), 12) for value in values})
        effective = max(1, len(unique_values))
        return {
            "requested": requested,
            "effective": effective,
            "basis": basis,
            "unit": unit,
            "min": float(min(values)),
            "max": float(max(values)),
            "overlap": requested > 1 and effective == 1,
            "active": active,
        }

    def _source_sampling_diagnostics(self, trace_summary: dict | None = None) -> list[tuple[str, str]]:
        diagnostics: list[tuple[str, str]] = []
        if self._current_source_model() != SOURCE_MODEL_DEFAULT:
            return diagnostics

        field_summary = self._field_launch_sample_summary()
        if bool(field_summary.get("overlap")):
            diagnostics.append(
                (
                    "Field sampling note",
                    (
                        f"{field_summary['requested']} requested field samples collapse to "
                        f"{field_summary['effective']} effective on-axis field because the "
                        f"{field_summary['basis']} span is 0 {field_summary['unit']}; "
                        "use a nonzero field value to launch distinct field bundles."
                    ),
                )
            )

        if not self._is_full_pupil_mode():
            pattern = self._current_pupil_pattern_label()
            if pattern in {PUPIL_PATTERN_DEFAULT, "Fan X", "Fan Y"}:
                diagnostics.append(
                    (
                        "Projection sampling note",
                        (
                            f"{pattern} uses the shared 3D envelope for layout projections; "
                            "use Full Pupil for denser pupil fills or explicit section diagnostics for dense YZ/XZ slices."
                        ),
                    )
                )

        active = ""
        if trace_summary:
            active = str(trace_summary.get("active", "") or "")
        if (
            self._current_object_mode() == "Finite"
            and float(self._current_source_cone_angle()) > 1e-12
            and active.lower().startswith("sequential")
        ):
            diagnostics.append(
                (
                    "Source cone note",
                    "Sequential Pupil / field ignores Source cone angle; finite-object cone angle comes from object distance and the entrance pupil. Use a physical source or non-sequential scene for explicit source half-angle.",
                )
            )
        return diagnostics


    @staticmethod
    def _optimization_bounds(parameter: str, value: float) -> tuple[float, float]:
        for spec in VARIABLE_REGISTRY.values():
            if spec.parameter == parameter:
                return spec.default_bounds(value)
        raise ValueError(f"Unsupported optimization parameter: {parameter}")

    @staticmethod
    def _variable_spec_for_field(field: str):
        return VARIABLE_REGISTRY.get(field)

    @staticmethod
    def _variable_spec_for_parameter(parameter: str):
        for spec in VARIABLE_REGISTRY.values():
            if _native_variable_matches(spec.parameter, parameter):
                return spec
        return None

    @classmethod
    def _optimization_value_from_row(cls, row: SurfaceRow, variable: OpticalVariable) -> float:
        spec = cls._variable_spec_for_parameter(variable.parameter)
        if spec is not None:
            return spec.value_from_row(row)
        if hasattr(row, str(variable.parameter)):
            return float(getattr(row, str(variable.parameter)))
        raise ValueError(f"Unsupported optimization parameter: {variable.parameter}")

    @classmethod
    def _apply_optimization_value_to_row(cls, row: SurfaceRow, variable: OpticalVariable, value: float) -> None:
        spec = cls._variable_spec_for_parameter(variable.parameter)
        if spec is not None:
            setattr(row, spec.field, float(value))
            return
        if hasattr(row, str(variable.parameter)):
            setattr(row, str(variable.parameter), float(value))
            return
        raise ValueError(f"Unsupported optimization parameter: {variable.parameter}")

    @staticmethod
    def _merit_spec_for_label(label: str):
        for spec in OPERAND_REGISTRY.values():
            if spec.label == label:
                return spec
        return None

    def _selected_operand_specs(self) -> list:
        if "merit_mode_list" in self.__dict__:
            labels = [self.merit_mode_list.get(i) for i in self.merit_mode_list.curselection()]
        else:
            labels = [str(label) for label in getattr(self, "_headless_selected_operand_labels", [])]
        specs = []
        for label in labels:
            spec = self._merit_spec_for_label(label)
            if spec is not None:
                specs.append(spec)
        return specs

    def _operand_weight(self, label: str) -> float:
        var = self.operand_weight_vars.get(label)
        if var is None:
            spec = self._merit_spec_for_label(label)
            return 1.0 if spec is None else spec.default_weight
        try:
            return float(var.get())
        except ValueError:
            spec = self._merit_spec_for_label(label)
            return 1.0 if spec is None else spec.default_weight

    def _operand_target(self, label: str) -> float:
        var = self.operand_target_vars.get(label)
        if var is None:
            spec = self._merit_spec_for_label(label)
            return 0.0 if spec is None else spec.default_target
        try:
            return float(var.get())
        except ValueError:
            spec = self._merit_spec_for_label(label)
            return 0.0 if spec is None else spec.default_target

    def _operand_wavelength(self, label: str) -> float:
        var = self.operand_wavelength_vars.get(label)
        if var is None:
            return self._current_wavelength()
        try:
            return float(var.get())
        except ValueError:
            return self._current_wavelength()

    def _operand_field(self, label: str) -> float:
        var = self.operand_field_vars.get(label)
        if var is None:
            return 0.0
        try:
            return float(var.get())
        except ValueError:
            return 0.0

    def _operand_field_x(self, label: str) -> float:
        var = self.operand_field_x_vars.get(label)
        if var is None:
            return 0.0
        try:
            return float(var.get())
        except ValueError:
            return 0.0

    def _operand_field_y(self, label: str) -> float:
        var = self.operand_field_y_vars.get(label)
        if var is not None:
            try:
                return float(var.get())
            except ValueError:
                return 0.0
        return self._operand_field(label)

    def _operand_field_type(self, label: str) -> str:
        if self._current_object_mode() == "Infinity":
            return "angle"
        return "height"

    def _resolved_field_coordinate(self, field_basis: str, raw_value: float, resolved_field_type: str) -> float:
        metrics = self._field_metrics_for_value(field_basis, raw_value)
        if resolved_field_type == "angle":
            return float(metrics["angle_deg"])
        return float(metrics["object_height"])

    def _resolved_mtf_field_samples(self, label: str) -> list[dict[str, float | str]]:
        field_basis = self._current_field_type()
        resolved_field_type = "angle" if self._current_object_mode() == "Infinity" else "height"
        basis_label = self._field_type_display_label(field_basis)
        if field_basis == "Angle" and resolved_field_type == "height":
            basis_label = "Field Half-Angle -> Object Semi-Height"
        unit = self._field_type_unit(field_basis)
        raw_x = 0.0
        resolved_x = 0.0
        raw_limit = abs(float(self._current_field_value()))
        count = max(1, self._current_field_count())
        if raw_limit <= 1e-9:
            raw_values = [0.0]
        elif count == 1:
            raw_values = [float(raw_limit)]
        else:
            raw_values = list(np.linspace(0.0, float(raw_limit), count))

        samples: list[dict[str, float | str]] = []
        for raw_value in raw_values:
            resolved_y = self._resolved_field_coordinate(field_basis, raw_value, resolved_field_type)
            samples.append(
                {
                    "basis": basis_label,
                    "unit": unit,
                    "display_x": float(raw_x),
                    "display_y": float(raw_value),
                    "field_type": resolved_field_type,
                    "field_x": float(resolved_x),
                    "field_y": float(resolved_y),
                    "legend": f"{self._format_field_sample_value(raw_value)} {unit}".strip(),
                }
            )
        return samples

    def _resolved_positive_field_samples(self) -> list[dict[str, float | str]]:
        field_basis = self._current_field_type()
        resolved_field_type = "angle" if self._current_object_mode() == "Infinity" else "height"
        unit = self._field_type_unit(field_basis)
        raw_limit = abs(float(self._current_field_value()))
        count = max(1, self._current_field_count())
        if count == 1:
            raw_values = [raw_limit]
        else:
            raw_values = list(np.linspace(0.0, raw_limit, count))
        samples: list[dict[str, float | str]] = []
        for raw_value in raw_values:
            resolved_y = self._resolved_field_coordinate(field_basis, raw_value, resolved_field_type)
            samples.append(
                {
                    "basis": self._field_type_display_label(field_basis),
                    "unit": unit,
                    "display_y": float(raw_value),
                    "field_type": resolved_field_type,
                    "field_x": 0.0,
                    "field_y": float(resolved_y),
                    "legend": f"{self._format_field_sample_value(raw_value)} {unit}".strip(),
                }
            )
        return samples

    def _resolved_field_grid_samples(self) -> list[dict[str, float | str]]:
        field_basis = self._current_field_type()
        resolved_field_type = "angle" if self._current_object_mode() == "Infinity" else "height"
        basis_label = self._field_type_display_label(field_basis)
        unit = self._field_type_unit(field_basis)
        raw_limit = abs(float(self._current_field_value()))
        count = max(3, self._current_field_count())
        if raw_limit <= 1e-9:
            raw_values = [0.0]
        else:
            raw_values = list(np.linspace(-raw_limit, raw_limit, count))
        samples: list[dict[str, float | str]] = []
        seen: set[tuple[float, float]] = set()
        for raw_y in raw_values:
            for raw_x in raw_values:
                key = (round(float(raw_x), 12), round(float(raw_y), 12))
                if key in seen:
                    continue
                seen.add(key)
                resolved_x = self._resolved_field_coordinate(field_basis, float(raw_x), resolved_field_type)
                resolved_y = self._resolved_field_coordinate(field_basis, float(raw_y), resolved_field_type)
                samples.append(
                    {
                        "basis": basis_label,
                        "unit": unit,
                        "display_x": float(raw_x),
                        "display_y": float(raw_y),
                        "field_type": resolved_field_type,
                        "field_x": float(resolved_x),
                        "field_y": float(resolved_y),
                    }
                )
        return samples

    def _operand_surface_index(self, label: str) -> int:
        var = self.operand_surface_vars.get(label)
        if var is None:
            return self._analysis_surface_index()
        value = var.get().strip()
        if not value or value == "Auto":
            return self._analysis_surface_index()
        try:
            return int(value.split(":", 1)[0].strip())
        except ValueError:
            return self._analysis_surface_index()

    def _operand_aperture_type(self, label: str) -> str:
        var = self.operand_aperture_type_vars.get(label)
        if var is None:
            return self._current_aperture_type()
        value = var.get().strip().upper()
        if value == "FNO":
            return "EPD"
        return value if value in {"STOP", "EPD"} else self._current_aperture_type()

    def _operand_aperture_value(self, label: str) -> float:
        var = self.operand_aperture_value_vars.get(label)
        if var is None:
            return self._current_aperture_value()
        try:
            value = float(var.get())
        except ValueError:
            return self._current_aperture_value()
        return value if value != 0.0 else self._current_aperture_value()

    def _build_optimization_variables(self) -> list[OpticalVariable]:
        variables: list[OpticalVariable] = []
        for index, row in enumerate(self.rows):
            if row.surface == "Image":
                continue
            for spec in VARIABLE_REGISTRY.values():
                if not spec.is_supported(row) or not self._variable_enabled_for_row(row, spec):
                    continue
                value = spec.value_from_row(row)
                lower, upper = spec.get_bounds(row) or spec.default_bounds(value)
                variables.append(
                    OpticalVariable(
                        index,
                        spec.parameter,
                        lower,
                        upper,
                        name=f"{row.name} {spec.label}",
                    )
                )
        return variables

    def _build_merit_function(self) -> MeritFunction:
        selected_specs = self._selected_operand_specs()
        if not selected_specs:
            return MeritFunction(operands=[])
        operands = []
        for spec in selected_specs:
            operands.extend(spec.build_merit_function(self).operands)
        return MeritFunction(operands=operands)

    def _build_tolerance_merit_function(self) -> tuple[MeritFunction, list[str]]:
        for attr_name in (
            "operand_weight_vars",
            "operand_target_vars",
            "operand_wavelength_vars",
            "operand_field_vars",
            "operand_field_x_vars",
            "operand_field_y_vars",
            "operand_surface_vars",
            "operand_aperture_type_vars",
            "operand_aperture_value_vars",
            "operand_frequency_vars",
            "operand_mtf_mode_vars",
            "operand_mtf_algorithm_vars",
        ):
            self.__dict__.setdefault(attr_name, {})
        selected_specs = self._selected_operand_specs()
        if selected_specs:
            operands = []
            labels = []
            for spec in selected_specs:
                labels.append(str(spec.label))
                operands.extend(spec.build_merit_function(self).operands)
            return MeritFunction(operands=operands), labels
        default_spec = self._merit_spec_for_label("Spot RMS")
        if default_spec is None:
            return MeritFunction(operands=[]), []
        return default_spec.build_merit_function(self), [str(default_spec.label)]

    @staticmethod

    def start_optimization(self) -> None:
        if self.optimization_running:
            return
        self._read_rows_from_table()
        variables = self._build_optimization_variables()
        if not variables:
            self.append_progress("Optimization skipped: no optimization variables marked.")
            return

        try:
            system = self.build_system()
        except Exception as exc:
            self.append_progress(f"Optimization aborted: system build failed: {exc}")
            return

        merit_specs = self._selected_operand_specs()
        merit = self._build_merit_function()
        if not merit.operands:
            self.append_progress("Optimization aborted: no merit operands selected.")
            return

        x0 = []
        for variable in variables:
            row = self.rows[variable.surface_index]
            x0.append(self._optimization_value_from_row(row, variable))

        population_size = 12
        optimization_workers = 1
        parallel_enabled = self._optimization_parallel_enabled()
        if parallel_enabled:
            optimization_workers = self._optimization_worker_count()
        preflight_ok, preflight_messages = self._optimization_preflight_messages(
            merit,
            variables,
            optimization_workers,
            parallel_enabled,
        )
        for message in preflight_messages:
            self.append_progress(message)
        if not preflight_ok:
            self.status_var.set("Optimization backend unavailable.")
            return
        self.append_progress(
            "Optimization start | operands: "
            + ", ".join(spec.label for spec in merit_specs)
        )
        self.append_progress(f"Variables: {', '.join(v.normalized_name() for v in variables)}")
        self.status_var.set("Optimization starting...")
        self.append_progress("Preparing optimization worker...")
        self.optimization_running = True
        self.optimization_cancel_requested = False
        self.optimization_context = {
            "variables": variables,
            "champion_x": list(x0),
            "generations_total": 12,
            "generation_done": 0,
            "verbosity_every": 1,
            "workers": optimization_workers,
            "compute_backend": "pending",
            "initial_total": None,
            "last_best": None,
        }
        self._update_progress_indicators()
        self._start_progress_spinner()
        ctx = mp.get_context("spawn")
        self._optimization_queue = ctx.Queue()
        self._optimization_stop_event = ctx.Event()
        self._optimization_process = ctx.Process(
            target=_run_optimization_job,
            args=(
                self._optimization_queue,
                self._optimization_stop_event,
                self._serializable_row_specs(),
                merit,
                variables,
                list(map(float, x0)),
                int(self.optimization_context["generations_total"]),
                int(self.optimization_context["verbosity_every"]),
                int(population_size),
                int(optimization_workers),
                bool(parallel_enabled),
            ),
        )
        self._optimization_process.start()
        self.after(75, self._poll_optimization_worker)

    def stop_optimization(self) -> None:
        if not self.optimization_running:
            self.append_progress("Stop ignored: no optimization is running.")
            return
        self.optimization_cancel_requested = True
        if self._optimization_stop_event is not None:
            try:
                self._optimization_stop_event.set()
            except Exception:
                pass
        self.append_progress("Stop requested. Applying the latest completed generation and terminating the worker.")
        partial_result = None
        if self.optimization_context is not None:
            partial_result = {
                "champion_x": list(self.optimization_context.get("champion_x", [])),
                "initial_total": self.optimization_context.get("initial_total"),
                "final_total": self.optimization_context.get("last_best", self.optimization_context.get("initial_total")),
                "compute_backend": self.optimization_context.get("compute_backend", "pending"),
                "workers": self.optimization_context.get("workers", 1),
                "operands": [],
            }
        self._finish_optimization(cancelled=True, result=partial_result)

    def _poll_optimization_worker(self) -> None:
        if not self.optimization_running or self.optimization_context is None:
            return

        ctx = self.optimization_context
        queue = self._optimization_queue
        process = self._optimization_process
        if queue is None or process is None:
            self.append_progress("Optimization failed: worker process not available.")
            self._finish_optimization(cancelled=True)
            return

        completed = False
        while True:
            try:
                payload = queue.get_nowait()
            except Empty:
                break

            message_type = str(payload.get("type", ""))
            if message_type == "bootstrap":
                for line in payload.get("debug_messages", []) or []:
                    self.append_debug(str(line))
                initial_total = float(payload.get("initial_total", 0.0))
                ctx["initial_total"] = initial_total
                ctx["compute_backend"] = str(payload.get("compute_backend", "sequential"))
                ctx["workers"] = max(1, int(payload.get("workers", 1)))
                self.status_var.set(f"Optimization running: initial merit = {initial_total:.6g}")
                self.append_progress(f"Initial merit: {initial_total:.6g}")
                self.append_progress(f"Optimization compute: {ctx['compute_backend']}")
            elif message_type == "generation":
                capture_text = str(payload.get("debug", ""))
                if capture_text:
                    self.append_debug(capture_text)
                ctx["generation_done"] = max(ctx["generation_done"], int(payload.get("generation_done", 0)))
                champion_x = list(payload.get("champion_x", []))
                if champion_x:
                    ctx["champion_x"] = champion_x
                self._update_progress_indicators()
                if "log_best" in payload:
                    ctx["last_best"] = float(payload.get("log_best", 0.0))
                    if (
                        ctx["generation_done"] == 1
                        or ctx["generation_done"] == ctx["generations_total"]
                        or ctx["generation_done"] % ctx["verbosity_every"] == 0
                    ):
                        self.append_progress(
                            "Gen {gen:>3} | fevals {fevals:>4} | best {best:.6g} | dx {dx:.6g} | df {df:.6g}".format(
                                gen=int(ctx["generation_done"]),
                                fevals=int(payload.get("log_fevals", 0)),
                                best=float(payload.get("log_best", 0.0)),
                                dx=float(payload.get("log_dx", 0.0)),
                                df=float(payload.get("log_df", 0.0)),
                            )
                        )
                    if champion_x:
                        for variable, value in zip(ctx["variables"], champion_x):
                            row = self.rows[variable.surface_index]
                            self._apply_optimization_value_to_row(row, variable, float(value))
                        self._sync_table()
                        self.status_var.set(
                            f"Optimization running: generation {ctx['generation_done']}/{ctx['generations_total']} | best merit = {ctx['last_best']:.6g}"
                        )
            elif message_type == "complete":
                self._finish_optimization(cancelled=bool(payload.get("cancelled", False)), result=payload)
                completed = True
                break
            elif message_type == "error":
                tb = str(payload.get("traceback", ""))
                if tb:
                    self.append_debug(tb)
                self.append_progress(f"Optimization failed: {payload.get('message', 'unknown error')}")
                self._finish_optimization(cancelled=True)
                completed = True
                break

        if completed:
            return
        if process.is_alive():
            self.after(75, self._poll_optimization_worker)
            return
        self.append_progress("Optimization worker exited unexpectedly.")
        self._finish_optimization(cancelled=True)

    def _finish_optimization(self, cancelled: bool, result: dict | None = None) -> None:
        self._shutdown_optimization_worker(force=bool(cancelled))
        if self.optimization_context is None:
            self.optimization_running = False
            self.optimization_cancel_requested = False
            self._stop_progress_spinner()
            self._update_progress_indicators()
            return

        ctx = self.optimization_context
        if result is not None:
            champion_x = list(result.get("champion_x", []))
            ctx["champion_x"] = champion_x
            ctx["compute_backend"] = str(result.get("compute_backend", ctx.get("compute_backend", "sequential")))
            ctx["workers"] = max(1, int(result.get("workers", ctx.get("workers", 1))))
            if result.get("initial_total") is not None:
                ctx["initial_total"] = float(result["initial_total"])

        champion_x = list(ctx.get("champion_x", []))
        for variable, value in zip(ctx["variables"], champion_x):
            row = self.rows[variable.surface_index]
            self._apply_optimization_value_to_row(row, variable, float(value))

        self._sync_table()
        self.refresh_plot()
        initial_total = float(ctx.get("initial_total") or 0.0)
        final_total_value = initial_total
        if result is not None:
            candidate_final = result.get("final_total", initial_total)
            if candidate_final is not None:
                final_total_value = float(candidate_final)
        final_total = float(final_total_value)
        compute_backend = str(ctx.get("compute_backend", "sequential"))
        compute_workers = max(1, int(ctx.get("workers", 1)))
        if cancelled:
            self.status_var.set(
                f"Optimization stopped: {initial_total:.6g} -> {final_total:.6g}"
            )
            self.append_progress(
                f"Optimization stopped | merit {initial_total:.6g} -> {final_total:.6g}"
            )
        else:
            self.status_var.set(
                f"Optimization finished: {initial_total:.6g} -> {final_total:.6g}"
            )
            self.append_progress(
                f"Optimization finished | merit {initial_total:.6g} -> {final_total:.6g}"
            )
        self.append_progress(f"Optimization compute: {compute_backend} | workers={compute_workers}")
        for operand in (result.get("operands", []) if result is not None else []):
            self.append_progress(
                f"  {operand['name']}: value={float(operand['value']):.6g} weighted={float(operand['weighted']):.6g}"
            )

        self.optimization_context = None
        self.optimization_running = False
        self.optimization_cancel_requested = False
        self._stop_progress_spinner()
        self._update_progress_indicators()
