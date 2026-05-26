"""Geometric PSF/MTF analysis helpers for the Tk layout editor."""

from __future__ import annotations

import io
import os
from contextlib import redirect_stderr, redirect_stdout

import numpy as np

import KrakenOS as Kos
from KrakenOS.UI.surface_table_model import SurfaceRow


def _layout_module():
    from KrakenOS.UI import layout_editor as layout_editor_module

    return layout_editor_module


def _trace_analysis_chunk(*args, **kwargs):
    return _layout_module()._trace_analysis_chunk(*args, **kwargs)


def _trace_analysis_chunk_full(*args, **kwargs):
    return _layout_module()._trace_analysis_chunk_full(*args, **kwargs)


def _build_pupil_bundle_static(*args, **kwargs):
    return _layout_module()._build_pupil_bundle_static(*args, **kwargs)


def _optional_torch():
    return _layout_module()._optional_torch()


def _optional_cupy():
    return _layout_module()._optional_cupy()


class GeometricAnalysisMixin:
    def _trace_pattern_chunks_parallel(
        self,
        wavelength: float,
        bundles: list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]],
    ) -> tuple[np.ndarray, np.ndarray, int]:
        total_rays = int(sum(len(np.asarray(bundle[0])) for bundle in bundles))
        worker_count = self._mtf_worker_count(total_rays)
        if worker_count <= 1:
            x_parts: list[np.ndarray] = []
            y_parts: list[np.ndarray] = []
            row_specs = self._serializable_row_specs()
            for bundle in bundles:
                x_local, y_local = _trace_analysis_chunk(row_specs, wavelength, *bundle)
                if x_local.size:
                    x_parts.append(x_local)
                    y_parts.append(y_local)
            if not x_parts:
                return np.asarray([], dtype=float), np.asarray([], dtype=float), 1
            return np.concatenate(x_parts), np.concatenate(y_parts), 1

        row_specs = self._serializable_row_specs()
        futures = []
        x_parts = []
        y_parts = []
        executor = self._ensure_analysis_executor(worker_count)
        if executor is None:
            return np.asarray([], dtype=float), np.asarray([], dtype=float), 1
        try:
            chunk_specs = []
            for bundle in bundles:
                ray_total = len(np.asarray(bundle[0]))
                if ray_total == 0:
                    continue
                indices = np.array_split(np.arange(ray_total), worker_count)
                for chunk in indices:
                    if chunk.size == 0:
                        continue
                    chunk_bundle = tuple(np.asarray(values)[chunk] for values in bundle)
                    futures.append(executor.submit(_trace_analysis_chunk, row_specs, wavelength, *chunk_bundle))
                    chunk_specs.append(chunk_bundle)
            for future, chunk_bundle in zip(futures, chunk_specs):
                try:
                    x_local, y_local = future.result()
                except Exception:
                    x_local, y_local = _trace_analysis_chunk(row_specs, wavelength, *chunk_bundle)
                if x_local.size:
                    x_parts.append(x_local)
                    y_parts.append(y_local)
        finally:
            self._shutdown_analysis_executor()
        if not x_parts:
            return np.asarray([], dtype=float), np.asarray([], dtype=float), worker_count
        return np.concatenate(x_parts), np.concatenate(y_parts), worker_count

    def _trace_pattern_chunks_parallel_full(
        self,
        wavelength: float,
        bundles: list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]],
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]:
        total_rays = int(sum(len(np.asarray(bundle[0])) for bundle in bundles))
        worker_count = self._mtf_worker_count(total_rays)
        if worker_count <= 1:
            parts = [[] for _ in range(6)]
            row_specs = self._serializable_row_specs()
            for bundle in bundles:
                outputs = _trace_analysis_chunk_full(row_specs, wavelength, *bundle)
                if outputs[0].size:
                    for idx, arr in enumerate(outputs):
                        parts[idx].append(arr)
            if not parts[0]:
                empty = np.asarray([], dtype=float)
                return empty, empty, empty, empty, empty, empty, 1
            merged = [np.concatenate(group) for group in parts]
            return (*merged, 1)

        row_specs = self._serializable_row_specs()
        futures = []
        parts = [[] for _ in range(6)]
        executor = self._ensure_analysis_executor(worker_count)
        if executor is None:
            empty = np.asarray([], dtype=float)
            return empty, empty, empty, empty, empty, empty, 1
        try:
            chunk_specs = []
            for bundle in bundles:
                ray_total = len(np.asarray(bundle[0]))
                if ray_total == 0:
                    continue
                indices = np.array_split(np.arange(ray_total), worker_count)
                for chunk in indices:
                    if chunk.size == 0:
                        continue
                    chunk_bundle = tuple(np.asarray(values)[chunk] for values in bundle)
                    futures.append(executor.submit(_trace_analysis_chunk_full, row_specs, wavelength, *chunk_bundle))
                    chunk_specs.append(chunk_bundle)
            for future, chunk_bundle in zip(futures, chunk_specs):
                try:
                    outputs = future.result()
                except Exception:
                    outputs = _trace_analysis_chunk_full(row_specs, wavelength, *chunk_bundle)
                if outputs[0].size:
                    for idx, arr in enumerate(outputs):
                        parts[idx].append(arr)
        finally:
            self._shutdown_analysis_executor()
        if not parts[0]:
            empty = np.asarray([], dtype=float)
            return empty, empty, empty, empty, empty, empty, worker_count
        merged = [np.concatenate(group) for group in parts]
        return (*merged, worker_count)

    def _compute_diffraction_mtf_sample(
        self,
        system,
        *,
        wavelength: float,
        surface_index: int,
        aperture_type: str,
        aperture_value: float,
        field_type: str,
        field_x: float,
        field_y: float,
    ) -> dict[str, object]:
        def _diffraction_limited_result(pupil, method: str) -> dict[str, object]:
            focal = max(0.01, abs(float(getattr(pupil, "EFFL", 0.0))))
            diameter = max(0.01, 2.0 * float(getattr(pupil, "RadPupInp", 1.0)))
            cutoff = diameter / max(float(wavelength) * 1e-3 * focal, 1e-12)
            freq = np.linspace(0.0, max(cutoff, 1e-9), 256)
            nu = np.clip(freq / max(cutoff, 1e-12), 0.0, 1.0)
            mtf = (2.0 / np.pi) * (
                np.arccos(nu) - nu * np.sqrt(np.clip(1.0 - nu * nu, 0.0, 1.0))
            )
            return {
                "plot_freq": np.asarray(freq, dtype=float),
                "plot_tan": np.asarray(mtf, dtype=float),
                "plot_sag": np.asarray(mtf, dtype=float),
                "method": method,
                "worker_count": 1,
                "accelerator": "CPU",
                "sample_count": 0,
                "used_terms": 0,
                "phase_method": method,
            }

        def _sanitize_phase_arrays(px, py, phase):
            px = np.asarray(px, dtype=float)
            py = np.asarray(py, dtype=float)
            phase = np.asarray(phase, dtype=float)
            finite = np.isfinite(px) & np.isfinite(py) & np.isfinite(phase)
            return px[finite], py[finite], phase[finite]

        def _phase_is_degenerate(px: np.ndarray, py: np.ndarray) -> bool:
            if px.size < 6:
                return True
            unique_x = np.unique(np.round(px, 10)).size
            unique_y = np.unique(np.round(py, 10)).size
            return unique_x <= 1 or unique_y <= 1

        pupil = Kos.PupilCalc(
            system,
            int(surface_index),
            float(wavelength),
            str(aperture_type),
            float(aperture_value),
        )
        pupil.Samp = max(11, min(21, self._current_ray_count()))
        pupil.Ptype = "hexapolar"
        pupil.FieldType = str(field_type)
        pupil.FieldX = float(field_x)
        pupil.FieldY = float(field_y)
        if any(row.surface == "Thin Lens" for row in self.rows):
            return _diffraction_limited_result(pupil, "Ideal Diffraction")
        phase_method = "Phase2" if str(field_type).strip().lower() == "height" else "Phase"
        if phase_method == "Phase2":
            capture = io.StringIO()
            with redirect_stdout(capture), redirect_stderr(capture):
                px, py, phase, _p2v = Kos.Phase2(pupil)
            phase2_log = capture.getvalue().strip()
            if phase2_log:
                self.append_debug(phase2_log)
            px, py, phase = _sanitize_phase_arrays(px, py, phase)
        else:
            px, py, phase, _p2v = Kos.Phase(pupil)
            px, py, phase = _sanitize_phase_arrays(px, py, phase)
            if _phase_is_degenerate(px, py):
                capture = io.StringIO()
                with redirect_stdout(capture), redirect_stderr(capture):
                    px, py, phase, _p2v = Kos.Phase2(pupil)
                phase2_log = capture.getvalue().strip()
                if phase2_log:
                    self.append_debug(phase2_log)
                px, py, phase = _sanitize_phase_arrays(px, py, phase)
                phase_method = "Phase2"
        if _phase_is_degenerate(px, py):
            raise RuntimeError("Degenerate pupil sample from Phase/Phase2")
        if px.size < 6:
            raise RuntimeError("Not enough finite pupil samples for MTF fitting")
        phase_ptv = float(np.ptp(phase)) if phase.size else 0.0
        phase_peak = float(np.max(np.abs(phase))) if phase.size else 0.0
        if phase_ptv <= 1e-14 and phase_peak <= 1e-14:
            raise RuntimeError(f"Flat phase map from {phase_method}")

        zcoef = None
        used_terms = None
        last_error = None
        for term_count in (15, 10, 6, 4):
            if px.size <= term_count:
                continue
            try:
                coef_seed = np.ones(term_count)
                zcoef, _mat, _rms_chief, _rms_centroid, _fitting_error = Kos.Zernike_Fitting(
                    px,
                    py,
                    phase,
                    coef_seed,
                )
                used_terms = term_count
                break
            except Exception as exc:
                last_error = exc
        if zcoef is None:
            raise RuntimeError(f"Zernike fit failed: {last_error}")

        focal = max(0.01, abs(float(getattr(pupil, "EFFL", 0.0))))
        diameter = max(0.01, 2.0 * float(getattr(pupil, "RadPupInp", 1.0)))
        mtf = Kos.calculate_mtf(
            np.asarray(zcoef, dtype=float),
            focal,
            diameter,
            wavelength,
            pixels=256,
            PupilSample=4,
        )
        samples = int(mtf.shape[0])
        # Convert the FFT axis to image-plane cycles/mm using fc = D / (lambda * f).
        freq_max = diameter / max(wavelength * 1e-3 * focal, 1e-12)
        freq = np.linspace(0.0, freq_max, samples // 2)
        tangential = np.asarray(mtf[samples // 2, samples // 2:], dtype=float)
        sagittal = np.asarray(mtf[samples // 2 :, samples // 2], dtype=float)
        count = min(len(freq), len(tangential), len(sagittal))
        return {
            "plot_freq": np.asarray(freq[:count], dtype=float),
            "plot_tan": np.asarray(tangential[:count], dtype=float),
            "plot_sag": np.asarray(sagittal[:count], dtype=float),
            "method": "Diffraction",
            "worker_count": 1,
            "accelerator": "CPU",
            "sample_count": int(px.size),
            "used_terms": int(used_terms) if used_terms is not None else 0,
            "phase_method": phase_method,
        }

    def _compute_geometric_mtf_sample(
        self,
        system,
        *,
        wavelength: float,
        surface_index: int,
        aperture_type: str,
        aperture_value: float,
        field_type: str,
        field_x: float,
        field_y: float,
        algorithm: str = "psf_fft",
    ) -> dict[str, object]:
        dense_count = max(24, self._current_ray_count() * 6)
        x_local, y_local, worker_count = self._build_geometric_image_samples(
            system,
            wavelength,
            sample_count=dense_count,
            pattern="hexapolar",
            surface_index=int(surface_index),
            aperture_type=str(aperture_type),
            aperture_value=float(aperture_value),
            field_type=str(field_type),
            field_x=float(field_x),
            field_y=float(field_y),
        )
        return self._geometric_mtf_result_from_image_samples(
            x_local,
            y_local,
            worker_count=int(worker_count),
            sample_count=int(dense_count),
            algorithm=algorithm,
        )

    def _geometric_mtf_result_from_image_samples(
        self,
        x_local: np.ndarray,
        y_local: np.ndarray,
        *,
        worker_count: int,
        sample_count: int,
        algorithm: str = "psf_fft",
    ) -> dict[str, object]:
        x_vals = np.asarray(x_local, dtype=float)
        y_vals = np.asarray(y_local, dtype=float)
        if x_vals.size < 4:
            raise RuntimeError("Not enough image-plane ray samples for geometric MTF")

        centered_x, centered_y = self._center_image_plane_samples(x_vals, y_vals)
        if centered_x.size < 4:
            raise RuntimeError("Not enough centered image-plane ray samples for geometric MTF")

        span_x = max(float(np.ptp(centered_x)), 1e-3)
        span_y = max(float(np.ptp(centered_y)), 1e-3)
        span = max(span_x, span_y) * 1.25
        if span <= 0:
            span = 1.0
        bins = 128
        if str(algorithm).strip().lower() == "lsf_fft":
            positive, tangential, sagittal, accelerator = self._compute_lsf_mtf_arrays(
                centered_x,
                centered_y,
                bins,
                span,
            )
            method_name = "Geometric-LSF"
        else:
            mtf, freq, _xedges, _unused, accelerator = self._compute_geometric_mtf_arrays(
                centered_x,
                centered_y,
                bins,
                span,
            )
            center = bins // 2
            positive = np.asarray(freq[center:], dtype=float)
            tangential = np.asarray(mtf[center, center:], dtype=float)
            sagittal = np.asarray(mtf[center:, center], dtype=float)
            method_name = "Geometric-PSF"
        count = min(len(positive), len(tangential), len(sagittal))
        return {
            "plot_freq": np.asarray(positive[:count], dtype=float),
            "plot_tan": np.asarray(tangential[:count], dtype=float),
            "plot_sag": np.asarray(sagittal[:count], dtype=float),
            "method": method_name,
            "worker_count": int(worker_count),
            "accelerator": str(accelerator),
            "sample_count": int(x_vals.size),
            "pupil_samp": int(sample_count),
        }

    @staticmethod
    def _compute_lsf_mtf_arrays(
        x_local: np.ndarray,
        y_local: np.ndarray,
        bins: int,
        span: float,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, str]:
        x_local = np.asarray(x_local, dtype=float)
        y_local = np.asarray(y_local, dtype=float)
        finite = np.isfinite(x_local) & np.isfinite(y_local)
        x_local = x_local[finite]
        y_local = y_local[finite]
        if x_local.size == 0:
            raise RuntimeError("Not enough centered image-plane samples for LSF MTF")
        x_local = x_local - float(np.mean(x_local))
        y_local = y_local - float(np.mean(y_local))
        lower = -span / 2.0
        upper = span / 2.0
        hist_x, xedges = np.histogram(x_local, bins=bins, range=(lower, upper))
        hist_y, _yedges = np.histogram(y_local, bins=bins, range=(lower, upper))
        lsf_tan = np.asarray(hist_x, dtype=float)
        lsf_sag = np.asarray(hist_y, dtype=float)
        if float(np.sum(lsf_tan)) <= 0.0 or float(np.sum(lsf_sag)) <= 0.0:
            raise RuntimeError("Not enough line-spread samples for LSF MTF")

        # Apply a smooth window before FFT to stabilize high-frequency ringing.
        window = np.hanning(bins)
        lsf_tan *= window
        lsf_sag *= window
        lsf_tan /= max(float(np.sum(lsf_tan)), 1e-12)
        lsf_sag /= max(float(np.sum(lsf_sag)), 1e-12)
        mtf_tan = np.abs(np.fft.fft(lsf_tan))
        mtf_sag = np.abs(np.fft.fft(lsf_sag))
        mtf_tan /= max(float(mtf_tan[0]), 1e-12)
        mtf_sag /= max(float(mtf_sag[0]), 1e-12)
        dx = float(xedges[1] - xedges[0])
        freq = np.fft.fftfreq(bins, d=dx)
        positive = freq >= 0.0
        return (
            np.asarray(freq[positive], dtype=float),
            np.asarray(mtf_tan[positive], dtype=float),
            np.asarray(mtf_sag[positive], dtype=float),
            "CPU",
        )

    def _build_geometric_image_samples(
        self,
        system,
        wavelength: float,
        sample_count: int,
        pattern: str = "hexapolar",
        *,
        surface_index: int,
        aperture_type: str,
        aperture_value: float,
        field_type: str,
        field_x: float,
        field_y: float,
    ) -> tuple[np.ndarray, np.ndarray, int]:
        random_source_bundle = self._build_random_source_bundle(sample_count)
        if random_source_bundle is not None:
            x_local, y_local, worker_count = self._trace_pattern_chunks_parallel(wavelength, [random_source_bundle])
            finite = np.isfinite(x_local) & np.isfinite(y_local)
            return x_local[finite], y_local[finite], worker_count
        pupil = Kos.PupilCalc(
            system,
            int(surface_index),
            wavelength,
            str(aperture_type),
            float(aperture_value),
        )
        pupil.Samp = max(2, int(sample_count))
        pupil.Ptype = self._current_analysis_pupil_pattern(pattern) if pattern == "hexapolar" else str(pattern)
        pupil.FieldType = str(field_type)
        field_pairs = [(float(field_x), float(field_y))]
        bundles = []
        for fx, fy in field_pairs:
            pupil.FieldX = fx
            pupil.FieldY = fy
            bundles.append(self._pupil_pattern_bundle(pupil))
        x_local, y_local, worker_count = self._trace_pattern_chunks_parallel(wavelength, bundles)
        finite = np.isfinite(x_local) & np.isfinite(y_local)
        return x_local[finite], y_local[finite], worker_count

    @staticmethod
    def _center_image_plane_samples(
        x_local: np.ndarray,
        y_local: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        x_vals = np.asarray(x_local, dtype=float)
        y_vals = np.asarray(y_local, dtype=float)
        finite = np.isfinite(x_vals) & np.isfinite(y_vals)
        if not np.any(finite):
            return np.asarray([], dtype=float), np.asarray([], dtype=float)
        x_vals = x_vals[finite]
        y_vals = y_vals[finite]
        x_vals = x_vals - float(np.mean(x_vals))
        y_vals = y_vals - float(np.mean(y_vals))
        return x_vals, y_vals

    def _build_geometric_image_samples_for_field_samples(
        self,
        wavelength: float,
        sample_count: int,
        pattern: str,
        *,
        surface_index: int,
        aperture_type: str,
        aperture_value: float,
        field_samples: list[dict[str, float | str]],
    ) -> tuple[list[tuple[np.ndarray, np.ndarray]], int]:
        if not field_samples:
            return [], 1
        row_specs = self._serializable_row_specs()
        bundles = [
            _build_pupil_bundle_static(
                row_specs,
                wavelength,
                sample_count,
                pattern,
                surface_index=int(surface_index),
                aperture_type=str(aperture_type),
                aperture_value=float(aperture_value),
                field_type=str(sample["field_type"]),
                field_x=float(sample["field_x"]),
                field_y=float(sample["field_y"]),
                pupil_rad=self._current_pupil_rad(),
                pupil_theta=self._current_pupil_theta(),
            )
            for sample in field_samples
        ]
        total_rays = int(sum(len(np.asarray(bundle[0])) for bundle in bundles))
        worker_count = self._mtf_worker_count(total_rays)
        if worker_count <= 1:
            results: list[tuple[np.ndarray, np.ndarray]] = []
            for bundle in bundles:
                x_local, y_local = _trace_analysis_chunk(row_specs, wavelength, *bundle)
                centered_x, centered_y = self._center_image_plane_samples(x_local, y_local)
                results.append((centered_x, centered_y))
            return results, 1

        try:
            executor = self._ensure_analysis_executor(worker_count)
        except Exception:
            executor = None
        if executor is None:
            results = []
            for bundle in bundles:
                x_local, y_local = _trace_analysis_chunk(row_specs, wavelength, *bundle)
                centered_x, centered_y = self._center_image_plane_samples(x_local, y_local)
                results.append((centered_x, centered_y))
            return results, 1

        field_parts: list[list[tuple[np.ndarray, np.ndarray]]] = [[] for _ in bundles]
        futures: list[tuple[int, tuple[np.ndarray, ...], object]] = []
        chunks_per_field = max(1, worker_count // max(1, len(bundles)))
        try:
            for field_index, bundle in enumerate(bundles):
                ray_total = len(np.asarray(bundle[0]))
                if ray_total == 0:
                    continue
                chunk_count = max(1, min(chunks_per_field, ray_total))
                for chunk in np.array_split(np.arange(ray_total), chunk_count):
                    if chunk.size == 0:
                        continue
                    chunk_bundle = tuple(np.asarray(values)[chunk] for values in bundle)
                    future = executor.submit(_trace_analysis_chunk, row_specs, wavelength, *chunk_bundle)
                    futures.append((field_index, chunk_bundle, future))

            for field_index, chunk_bundle, future in futures:
                try:
                    x_local, y_local = future.result()
                except Exception:
                    x_local, y_local = _trace_analysis_chunk(row_specs, wavelength, *chunk_bundle)
                field_parts[field_index].append((np.asarray(x_local, dtype=float), np.asarray(y_local, dtype=float)))
        finally:
            self._shutdown_analysis_executor()

        results = []
        for parts in field_parts:
            if not parts:
                results.append((np.asarray([], dtype=float), np.asarray([], dtype=float)))
                continue
            merged_x = np.concatenate([part[0] for part in parts if part[0].size]) if any(part[0].size for part in parts) else np.asarray([], dtype=float)
            merged_y = np.concatenate([part[1] for part in parts if part[1].size]) if any(part[1].size for part in parts) else np.asarray([], dtype=float)
            centered_x, centered_y = self._center_image_plane_samples(merged_x, merged_y)
            results.append((centered_x, centered_y))
        return results, worker_count

    def _build_geometric_image_samples_full(
        self,
        system,
        wavelength: float,
        sample_count: int,
        pattern: str = "hexapolar",
        *,
        surface_index: int,
        aperture_type: str,
        aperture_value: float,
        field_type: str,
        field_x: float,
        field_y: float,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]:
        random_source_bundle = self._build_random_source_bundle(sample_count)
        if random_source_bundle is not None:
            x_local, y_local, z_local, l_local, m_local, n_local, worker_count = self._trace_pattern_chunks_parallel_full(
                wavelength,
                [random_source_bundle],
            )
            finite = (
                np.isfinite(x_local)
                & np.isfinite(y_local)
                & np.isfinite(z_local)
                & np.isfinite(l_local)
                & np.isfinite(m_local)
                & np.isfinite(n_local)
            )
            return (
                x_local[finite],
                y_local[finite],
                z_local[finite],
                l_local[finite],
                m_local[finite],
                n_local[finite],
                worker_count,
            )
        pupil = Kos.PupilCalc(
            system,
            int(surface_index),
            wavelength,
            str(aperture_type),
            float(aperture_value),
        )
        pupil.Samp = max(2, int(sample_count))
        pupil.Ptype = self._current_analysis_pupil_pattern(pattern) if pattern == "hexapolar" else str(pattern)
        pupil.FieldType = str(field_type)
        pupil.FieldX = float(field_x)
        pupil.FieldY = float(field_y)
        bundles = [self._pupil_pattern_bundle(pupil)]
        x_local, y_local, z_local, l_local, m_local, n_local, worker_count = self._trace_pattern_chunks_parallel_full(
            wavelength,
            bundles,
        )
        finite = (
            np.isfinite(x_local)
            & np.isfinite(y_local)
            & np.isfinite(z_local)
            & np.isfinite(l_local)
            & np.isfinite(m_local)
            & np.isfinite(n_local)
        )
        return (
            x_local[finite],
            y_local[finite],
            z_local[finite],
            l_local[finite],
            m_local[finite],
            n_local[finite],
            worker_count,
        )

    def _compute_psf_histogram(
        self,
        x_local: np.ndarray,
        y_local: np.ndarray,
        bins: int,
        span: float,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, str]:
        x_local, y_local = self._center_image_plane_samples(x_local, y_local)
        if x_local.size == 0:
            raise RuntimeError("Not enough image-plane samples for PSF histogram")
        backend_pref = os.getenv("KRAKEN_POSTPROC_BACKEND", "auto").strip().lower()
        gpu_min_samples = max(1, int(os.getenv("KRAKEN_GPU_MIN_SAMPLES", "1000000")))
        allow_auto_gpu = x_local.size >= gpu_min_samples
        if backend_pref == "auto" and not allow_auto_gpu:
            backend_pref = "cpu"
        if backend_pref in {"auto", "torch"}:
            torch = _optional_torch()
            if torch is not None:
                try:
                    if bool(torch.cuda.is_available()):
                        device = torch.device("cuda")
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
                        xedges_t = torch.linspace(lower, upper, bins + 1, dtype=torch.float64, device=device)
                        yedges_t = torch.linspace(lower, upper, bins + 1, dtype=torch.float64, device=device)
                        return (
                            hist_t.detach().cpu().numpy(),
                            xedges_t.detach().cpu().numpy(),
                            yedges_t.detach().cpu().numpy(),
                            "GPU-Torch",
                        )
                except Exception:
                    pass
        if backend_pref in {"auto", "cupy"}:
            cp = _optional_cupy()
            if cp is not None:
                try:
                    x_gpu = cp.asarray(x_local, dtype=cp.float64)
                    y_gpu = cp.asarray(y_local, dtype=cp.float64)
                    hist_gpu, xedges_gpu, yedges_gpu = cp.histogram2d(
                        x_gpu,
                        y_gpu,
                        bins=bins,
                        range=[[-span / 2.0, span / 2.0], [-span / 2.0, span / 2.0]],
                    )
                    return (
                        cp.asnumpy(hist_gpu),
                        cp.asnumpy(xedges_gpu),
                        cp.asnumpy(yedges_gpu),
                        "GPU-CuPy",
                    )
                except Exception:
                    pass
        hist, xedges, yedges = np.histogram2d(
            x_local,
            y_local,
            bins=bins,
            range=[[-span / 2.0, span / 2.0], [-span / 2.0, span / 2.0]],
        )
        return hist, xedges, yedges, "CPU"

    def _compute_geometric_mtf_arrays(
        self,
        x_local: np.ndarray,
        y_local: np.ndarray,
        bins: int,
        span: float,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, str]:
        x_local, y_local = self._center_image_plane_samples(x_local, y_local)
        if x_local.size == 0:
            raise RuntimeError("Not enough centered image-plane samples for geometric MTF")
        backend_pref = os.getenv("KRAKEN_POSTPROC_BACKEND", "auto").strip().lower()
        gpu_min_samples = max(1, int(os.getenv("KRAKEN_GPU_MIN_SAMPLES", "1000000")))
        allow_auto_gpu = x_local.size >= gpu_min_samples
        if backend_pref == "auto" and not allow_auto_gpu:
            backend_pref = "cpu"
        if backend_pref in {"auto", "torch"}:
            torch = _optional_torch()
            if torch is not None:
                try:
                    if bool(torch.cuda.is_available()):
                        device = torch.device("cuda")
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
                        xedges_t = torch.linspace(lower, upper, bins + 1, dtype=torch.float64, device=device)
                        dx = float((xedges_t[1] - xedges_t[0]).detach().cpu().item())
                        freq_t = torch.fft.fftshift(torch.fft.fftfreq(bins, d=dx, device=device))
                        return (
                            mtf_t.detach().cpu().numpy(),
                            freq_t.detach().cpu().numpy(),
                            xedges_t.detach().cpu().numpy(),
                            np.asarray([], dtype=float),
                            "GPU-Torch",
                        )
                except Exception:
                    pass
        if backend_pref in {"auto", "cupy"}:
            cp = _optional_cupy()
            if cp is not None:
                try:
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
                    dx = float(cp.asnumpy(xedges_gpu[1] - xedges_gpu[0]))
                    freq_gpu = cp.fft.fftshift(cp.fft.fftfreq(bins, d=dx))
                    return (
                        cp.asnumpy(mtf_gpu),
                        cp.asnumpy(freq_gpu),
                        cp.asnumpy(xedges_gpu),
                        np.asarray([], dtype=float),
                        "GPU-CuPy",
                    )
                except Exception:
                    pass
        hist, xedges, _yedges = np.histogram2d(
            x_local,
            y_local,
            bins=bins,
            range=[[-span / 2.0, span / 2.0], [-span / 2.0, span / 2.0]],
        )
        psf = hist / max(np.sum(hist), 1.0)
        otf = np.fft.fftshift(np.fft.fft2(psf))
        mtf = np.abs(otf)
        mtf /= max(float(np.max(mtf)), 1e-12)
        dx = float(xedges[1] - xedges[0])
        freq = np.fft.fftshift(np.fft.fftfreq(bins, d=dx))
        return mtf, freq, xedges, np.asarray([], dtype=float), "CPU"

    def _collect_optics_info(self, system, rays, wavelength: float) -> dict:
        info: dict[str, float | None | str] = {
            "effl": None,
            "magnification": None,
            "ppa": None,
            "ppp": None,
            "h1_z": None,
            "h2_z": None,
            "paraxial_image_size": None,
            "sensor_fill": None,
            "spot_rms": None,
            "spot_cen_x": None,
            "spot_cen_y": None,
            "ep_radius": None,
            "ep_z": None,
            "xp_radius": None,
            "xp_z": None,
            "airy_radius": None,
        }
        paraxial_rows = self.rows
        try:
            if any(row.surface == "Mirror" for row in self.rows):
                paraxial_rows, _last_source_index = self._paraxial_reference_rows_for_layout(self.rows)
            a, b, c, d, effl, ppa, ppp = self._exact_paraxial_solution_for_rows(paraxial_rows, wavelength)
            h1_vertex_z, h2_vertex_z = self._paraxial_vertex_zs(paraxial_rows)
            info.update(
                {
                    "effl": float(effl),
                    "ppa": float(ppa),
                    "ppp": float(ppp),
                    "h1_z": float(h1_vertex_z + float(ppa)),
                    "h2_z": float(h2_vertex_z + float(ppp)),
                }
            )
            if self._current_object_mode() == "Finite" and len(self.rows) >= 2:
                object_gap = max(float(self._paraxial_total_object_gap(self.rows)[0]), 1e-9)
                object_size = max(float(self.rows[0].diameter), 0.0)
                sensor_size = max(float(self.rows[-1].diameter), 0.0)
                object_principal = object_gap + float(ppa)
                image_gap = self._compute_image_gap_from_paraxial_solution(
                    float(a),
                    float(b),
                    float(c),
                    float(d),
                    object_gap,
                    self._current_object_mode(),
                )
                image_principal = image_gap - float(ppp)
                if np.isfinite(object_principal) and abs(object_principal) > 1e-12 and np.isfinite(image_principal):
                    magnification = image_principal / object_principal
                    image_size = abs(magnification) * object_size
                    info["paraxial_image_size"] = float(image_size)
                    info["magnification"] = float(magnification)
                    if sensor_size > 1e-12:
                        info["sensor_fill"] = float(image_size / sensor_size)
        except Exception:
            pass
        try:
            _, _, _, a, b, c, d, _effl, _ppa, _ppp, _, _, _ = system.Parax(wavelength)
            info["parax_a"] = float(a)
            info["parax_b"] = float(b)
            info["parax_c"] = float(c)
            info["parax_d"] = float(d)
            if info.get("magnification") is None:
                info["magnification"] = float(a)
        except Exception:
            pass
        try:
            analysis_rays = self._build_analysis_rays(system, wavelength)
            X, Y, Z, L, M, N = self._pick_image_plane_data(analysis_rays)
            if X.size:
                rms, cenX, cenY = Kos.RMS(X, Y, Z, L, M, N)
                info.update(
                    {
                        "spot_rms": float(rms),
                        "spot_cen_x": float(cenX),
                        "spot_cen_y": float(cenY),
                    }
                )
        except Exception:
            pass
        try:
            pupil_system, pupil_rows, pupil_surface_index = self._pupil_model_inputs(
                system,
                build_reference=True,
            )
            pupil = Kos.PupilCalc(
                pupil_system,
                pupil_surface_index,
                wavelength,
                self._current_aperture_type(),
                self._current_aperture_value(),
            )
            info.update(
                {
                    "ep_radius": float(pupil.RadPupInp),
                    "ep_z": float(pupil.PosPupInp[2]),
                    "xp_radius": float(pupil.RadPupOut),
                    "xp_z": float(pupil.PosPupOut[2]),
                    "airy_radius": float(pupil.FocusAiryRadius),
                }
            )
        except Exception:
            pass
        if self._current_aperture_type() == "EPD":
            ep_radius = max(abs(float(self._current_aperture_value())) * 0.5, 0.0)
            if np.isfinite(ep_radius) and ep_radius > 1e-9:
                info["ep_radius"] = float(ep_radius)
                # EPD mode defines the launch pupil directly in object space.
                # Draw it at the object plane so the marker matches the ray fan.
                info["ep_z"] = 0.0
                if info.get("airy_radius") is None and info.get("effl") is not None:
                    info["airy_radius"] = float(
                        1.22 * wavelength * abs(float(info["effl"])) / max(2.0 * ep_radius, 1e-9)
                    )
        return info

    def _pupil_surface_index_for_rows(self, rows: list[SurfaceRow]) -> int:
        if len(rows) <= 2:
            return max(0, len(rows) - 1)
        aperture_indices = [
            index
            for index, row in enumerate(rows[1:-1], start=1)
            if row.surface == "Aperture"
        ]
        if aperture_indices:
            return min(aperture_indices, key=lambda index: max(float(rows[index].diameter), 1e-9))
        candidate_indices = [
            index
            for index, row in enumerate(rows[1:-1], start=1)
            if row.surface in {"Standard", "Thin Lens", "Aperture"}
        ]
        if not candidate_indices:
            return max(1, len(rows) - 1)
        return min(candidate_indices, key=lambda index: (max(float(rows[index].diameter), 1e-9), index))

