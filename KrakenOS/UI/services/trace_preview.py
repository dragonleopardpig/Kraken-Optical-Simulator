"""Preview ray tracing orchestration service."""

from __future__ import annotations

import time
from typing import Any

import KrakenOS as Kos
import numpy as np

from KrakenOS.MeshRayTrace import mesh_trace_stats_snapshot, reset_mesh_trace_stats
from KrakenOS.UI.scene_geometry import SceneSource3D
from KrakenOS.UI.services.open3d_timing import open3d_timing_event
from KrakenOS.UI.services.row_spec_contracts import _requires_scalar_trace


def _layout_module():
    from KrakenOS.UI import layout_editor as layout_editor_module

    return layout_editor_module


class TracePreviewService:
    """Build and trace UI preview ray bundles while delegating editor state."""

    def __init__(self, editor: Any) -> None:
        object.__setattr__(self, "editor", editor)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "editor":
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def _trace_preview_rays(
        self,
        system,
        rays,
        wavelength: float,
        max_radius: float,
        *,
        allow_full_pupil: bool = True,
        sampling_mode: str = "display_slice",
    ) -> None:
        system.IgnoreVignetting(0)
        pupil_radius = self._resolved_preview_pupil_radius(
            max_radius,
            system=system,
            wavelength=wavelength,
        )
        preview_bundles: list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = []
        mode = str(sampling_mode or "display_slice").strip().lower()
        self._active_preview_sampling_mode = mode
        full_pupil = bool(allow_full_pupil and (self._is_full_pupil_mode() or mode == "full_pupil"))
        self._preview_field_bundle_count = max(1, self._current_field_count())
        scene_source_bundles, scene_source_records = self._build_scene_source_bundles(wavelength)
        if scene_source_bundles:
            rays.clean()
            self._trace_preview_bundles(
                system,
                rays,
                wavelength,
                scene_source_bundles,
                bundle_sources=scene_source_records,
            )
            self._preview_field_ray_count = max(int(len(np.asarray(bundle[0]))) for bundle in scene_source_bundles)
            self._preview_field_bundle_count = len(scene_source_bundles)
            system.Vignetting(0)
            return
        random_source_bundle = self._build_random_source_bundle()
        if random_source_bundle is not None:
            rays.clean()
            self._trace_preview_bundles(system, rays, wavelength, [random_source_bundle])
            self._preview_field_ray_count = int(len(np.asarray(random_source_bundle[0])))
            self._preview_field_bundle_count = 1
            system.Vignetting(0)
            return
        # DESIGN §5b per-branch launch: a beam splitter with > 1 IMAGING arm (each a
        # branch_selector arm with its own stop) needs ONE launch bundle per arm, each
        # aimed at that arm's own pupil -- a single launch cannot serve two arms with
        # different pupils and sprays (it can't even build the whole-layout reference
        # past the folded arm). No-op for ordinary single-axis scenes.
        if self._trace_per_branch_bundles(system, rays, wavelength, pupil_radius):
            system.Vignetting(0)
            return
        use_legacy_default_cone = self._should_use_default_finite_cone_source(system=system)
        if use_legacy_default_cone and mode in {"source_cone_world", "world_source_cone", "point_cone_world"}:
            default_cone_bundles, default_cone_ray_count = self._build_default_finite_cone_world_bundles()
            if default_cone_bundles:
                rays.clean()
                self._trace_preview_bundles(system, rays, wavelength, default_cone_bundles)
                self._preview_field_ray_count = max(1, int(default_cone_ray_count))
                self._preview_field_bundle_count = len(default_cone_bundles)
                system.Vignetting(0)
                return
        if mode == "world_envelope":
            if self._trace_world_envelope_rays(system, rays, wavelength, pupil_radius):
                system.Vignetting(0)
                return
        if mode == "world_cone":
            if self._trace_world_cone_rays(system, rays, wavelength, pupil_radius):
                system.Vignetting(0)
                return
        if use_legacy_default_cone and mode != "world_envelope":
            default_cone_bundles, default_cone_ray_count = self._build_default_finite_cone_preview_bundles()
            if default_cone_bundles:
                rays.clean()
                self._trace_preview_bundles(system, rays, wavelength, default_cone_bundles)
                self._preview_field_ray_count = max(1, int(default_cone_ray_count))
                self._preview_field_bundle_count = len(default_cone_bundles)
                system.Vignetting(0)
                return
        if mode == "world_sections":
            section_bundles, section_ray_count = self._build_world_section_bundles(pupil_radius, system=system)
            if section_bundles:
                rays.clean()
                self._trace_preview_bundles(system, rays, wavelength, section_bundles)
                self._preview_field_ray_count = max(1, int(section_ray_count))
                self._preview_field_bundle_count = int(len(section_bundles))
                system.Vignetting(0)
                return
        if full_pupil and not self._has_off_axis_geometry():
            # Full Pupil for axisymmetric systems. Each sampled field carries a
            # filled pupil bundle; finite objects must launch from the resolved
            # object field point rather than a synthetic parallel grid.
            rays.clean()
            if self._current_object_mode() == "Infinity":
                bundles = self._build_grid_angular_bundles(system, wavelength, pupil_radius)
                if bundles:
                    self._trace_preview_bundles(system, rays, wavelength, bundles)
                    self._preview_field_ray_count = int(len(np.asarray(bundles[0][0])))
                    self._preview_field_bundle_count = int(len(bundles))
                else:
                    self._preview_field_ray_count = 0
                    self._preview_field_bundle_count = 1
            else:
                bundles = self._build_grid_finite_object_bundles(system, wavelength, pupil_radius)
                if bundles:
                    self._trace_preview_bundles(system, rays, wavelength, bundles)
                    self._preview_field_ray_count = int(len(np.asarray(bundles[0][0])))
                    self._preview_field_bundle_count = int(len(bundles))
                else:
                    self._preview_field_ray_count = 0
                    self._preview_field_bundle_count = 1
            system.Vignetting(0)
            return
        if self._has_off_axis_geometry():
            rays.clean()
            if self._current_object_mode() == "Infinity":
                field_values = self._sample_field_values(self._current_field_angle_deg())
                if full_pupil:
                    disk_pts = self._sample_pupil_disk(pupil_radius)
                    for field_angle in field_values:
                        angle_rad = np.deg2rad(float(field_angle))
                        direction = np.array([0.0, np.sin(angle_rad), np.cos(angle_rad)], dtype=float)
                        norm = np.linalg.norm(direction)
                        if norm <= 1e-12:
                            continue
                        direction /= norm
                        n_pts = len(disk_pts)
                        x_values = disk_pts[:, 0].copy()
                        y_values = disk_pts[:, 1].copy()
                        z_values = np.zeros(n_pts, dtype=float)
                        l_values = np.full(n_pts, float(direction[0]), dtype=float)
                        m_values = np.full(n_pts, float(direction[1]), dtype=float)
                        n_values = np.full(n_pts, float(direction[2]), dtype=float)
                        preview_bundles.append(
                            self._center_infinity_bundle_on_launch_reference(
                                (x_values, y_values, z_values, l_values, m_values, n_values),
                                system=system,
                            )
                        )
                    self._trace_preview_bundles(system, rays, wavelength, preview_bundles)
                    self._preview_field_ray_count = len(disk_pts)
                else:
                    pupil_samples = self._sample_ray_heights(pupil_radius)
                    for field_angle in field_values:
                        angle_rad = np.deg2rad(float(field_angle))
                        direction = np.array([0.0, np.sin(angle_rad), np.cos(angle_rad)], dtype=float)
                        norm = np.linalg.norm(direction)
                        if norm <= 1e-12:
                            continue
                        direction /= norm
                        x_values = np.zeros(len(pupil_samples), dtype=float)
                        y_values = np.asarray(pupil_samples, dtype=float)
                        z_values = np.zeros(len(pupil_samples), dtype=float)
                        l_values = np.full(len(pupil_samples), float(direction[0]), dtype=float)
                        m_values = np.full(len(pupil_samples), float(direction[1]), dtype=float)
                        n_values = np.full(len(pupil_samples), float(direction[2]), dtype=float)
                        preview_bundles.append(
                            self._center_infinity_bundle_on_launch_reference(
                                (x_values, y_values, z_values, l_values, m_values, n_values),
                                system=system,
                            )
                        )
                        x_values = np.asarray(pupil_samples, dtype=float)
                        y_values = np.zeros(len(pupil_samples), dtype=float)
                        z_values = np.zeros(len(pupil_samples), dtype=float)
                        l_values = np.full(len(pupil_samples), float(direction[0]), dtype=float)
                        m_values = np.full(len(pupil_samples), float(direction[1]), dtype=float)
                        n_values = np.full(len(pupil_samples), float(direction[2]), dtype=float)
                        preview_bundles.append(
                            self._center_infinity_bundle_on_launch_reference(
                                (x_values, y_values, z_values, l_values, m_values, n_values),
                                system=system,
                            )
                        )
                    self._trace_preview_bundles(system, rays, wavelength, preview_bundles)
                    self._preview_field_ray_count = len(pupil_samples) * 2
            else:
                field_values = self._sample_field_values(self._current_field_height())
                object_distance = self._current_object_distance()
                if full_pupil:
                    disk_pts = self._sample_pupil_disk(pupil_radius)
                    for field_value in field_values:
                        origin = np.array([0.0, float(field_value), 0.0], dtype=float)
                        x_vals: list[float] = []
                        y_vals: list[float] = []
                        z_vals: list[float] = []
                        l_vals: list[float] = []
                        m_vals: list[float] = []
                        n_vals: list[float] = []
                        for px, py in disk_pts:
                            target = np.array([float(px), float(py), object_distance], dtype=float)
                            direction = target - origin
                            norm = np.linalg.norm(direction)
                            if norm <= 1e-12:
                                continue
                            direction /= norm
                            x_vals.append(float(origin[0]))
                            y_vals.append(float(origin[1]))
                            z_vals.append(float(origin[2]))
                            l_vals.append(float(direction[0]))
                            m_vals.append(float(direction[1]))
                            n_vals.append(float(direction[2]))
                        if x_vals:
                            preview_bundles.append(
                                (
                                    np.asarray(x_vals, dtype=float),
                                    np.asarray(y_vals, dtype=float),
                                    np.asarray(z_vals, dtype=float),
                                    np.asarray(l_vals, dtype=float),
                                    np.asarray(m_vals, dtype=float),
                                    np.asarray(n_vals, dtype=float),
                                )
                            )
                    self._trace_preview_bundles(system, rays, wavelength, preview_bundles)
                    self._preview_field_ray_count = len(disk_pts)
                else:
                    pupil_samples = self._sample_ray_heights(pupil_radius)
                    for field_value in field_values:
                        origin = np.array([0.0, float(field_value), 0.0], dtype=float)
                        x_values: list[float] = []
                        y_values: list[float] = []
                        z_values: list[float] = []
                        l_values: list[float] = []
                        m_values: list[float] = []
                        n_values: list[float] = []
                        for pupil_y in pupil_samples:
                            target = np.array([0.0, float(pupil_y), object_distance], dtype=float)
                            direction = target - origin
                            norm = np.linalg.norm(direction)
                            if norm <= 1e-12:
                                continue
                            direction /= norm
                            x_values.append(float(origin[0]))
                            y_values.append(float(origin[1]))
                            z_values.append(float(origin[2]))
                            l_values.append(float(direction[0]))
                            m_values.append(float(direction[1]))
                            n_values.append(float(direction[2]))
                        for pupil_x in pupil_samples:
                            target = np.array([float(pupil_x), 0.0, object_distance], dtype=float)
                            direction = target - origin
                            norm = np.linalg.norm(direction)
                            if norm <= 1e-12:
                                continue
                            direction /= norm
                            x_values.append(float(origin[0]))
                            y_values.append(float(origin[1]))
                            z_values.append(float(origin[2]))
                            l_values.append(float(direction[0]))
                            m_values.append(float(direction[1]))
                            n_values.append(float(direction[2]))
                        if x_values:
                            preview_bundles.append(
                                (
                                    np.asarray(x_values, dtype=float),
                                    np.asarray(y_values, dtype=float),
                                    np.asarray(z_values, dtype=float),
                                    np.asarray(l_values, dtype=float),
                                    np.asarray(m_values, dtype=float),
                                    np.asarray(n_values, dtype=float),
                                )
                            )
                    self._trace_preview_bundles(system, rays, wavelength, preview_bundles)
                    self._preview_field_ray_count = len(pupil_samples) * 2
        elif self._current_object_mode() == "Infinity":
            if not full_pupil and (mode == "display_slice" or not allow_full_pupil):
                preview_bundles, rays_per_field = self._build_meridional_preview_bundles(
                    pupil_radius,
                    system=system,
                    wavelength=wavelength,
                )
                self._trace_preview_bundles(system, rays, wavelength, preview_bundles)
                self._preview_field_ray_count = max(1, int(rays_per_field))
                system.Vignetting(0)
                return
            pupil = Kos.PupilCalc(
                system,
                self._analysis_surface_index(),
                wavelength,
                self._current_aperture_type(),
                self._current_aperture_value(),
            )
            pattern = self._current_kraken_pupil_pattern()
            if full_pupil:
                pupil.Samp = max(3, self._current_ray_count())
                pupil.Ptype = pattern or "hexapolar"
            else:
                pupil.Samp = max(1, self._current_ray_count() // 2)
                pupil.Ptype = pattern or "fan"
            last_bundle = 1
            pupil.FieldType = "angle"
            field_values = self._sample_field_values(self._current_field_angle_deg())
            for field_value in field_values:
                pupil.FieldX = 0.0
                pupil.FieldY = float(field_value)
                bundle = self._pupil_pattern_bundle(pupil)
                last_bundle = max(1, len(np.asarray(bundle[0])))
                preview_bundles.append(bundle)
            self._trace_preview_bundles(system, rays, wavelength, preview_bundles)
            self._preview_field_ray_count = last_bundle
        else:
            if not full_pupil and (mode == "display_slice" or not allow_full_pupil):
                preview_bundles, rays_per_field = self._build_meridional_preview_bundles(
                    pupil_radius,
                    system=system,
                    wavelength=wavelength,
                )
                self._trace_preview_bundles(system, rays, wavelength, preview_bundles)
                self._preview_field_ray_count = max(1, int(rays_per_field))
                system.Vignetting(0)
                return
            pupil = Kos.PupilCalc(
                system,
                self._analysis_surface_index(),
                wavelength,
                self._current_aperture_type(),
                self._current_aperture_value(),
            )
            pattern = self._current_kraken_pupil_pattern()
            if full_pupil:
                pupil.Samp = max(3, self._current_ray_count())
                pupil.Ptype = pattern or "hexapolar"
            else:
                pupil.Samp = max(1, self._current_ray_count() // 2)
                pupil.Ptype = pattern or "fan"
            pupil.FieldType = "height"
            field_values = self._sample_field_values(self._current_field_height())
            last_bundle = 1
            for field_value in field_values:
                pupil.FieldX = 0.0
                pupil.FieldY = float(field_value)
                bundle = self._pupil_pattern_bundle(pupil)
                last_bundle = max(1, len(np.asarray(bundle[0])))
                preview_bundles.append(bundle)
            self._trace_preview_bundles(system, rays, wavelength, preview_bundles)
            self._preview_field_ray_count = last_bundle
        system.Vignetting(0)

    def _trace_preview_bundles(
        self,
        system,
        rays,
        wavelength: float,
        bundles: list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]],
        *,
        bundle_sources: list[SceneSource3D | None] | None = None,
    ) -> None:
        le = _layout_module()
        NonSequentialTracePreviewError = le.NonSequentialTracePreviewError
        _short_error_message = le._short_error_message
        _trace_preview_chunk_batch = le._trace_preview_chunk_batch
        trace_start = time.perf_counter()
        self._last_preview_trace_backend = "none"
        self._last_preview_trace_note = ""
        # bugs/0223 (off-thread trace): capture/replay choke point. EVERY preview sampling
        # path funnels its launch bundles through this method, so:
        #  - CAPTURE (main thread): record the exact launch arrays and skip tracing -- the
        #    async orchestrator ships them to a worker process. The sampling above already
        #    ran on the main thread, so there is no editor-replication fidelity question.
        #  - REPLAY (worker process): substitute the captured launch arrays for the locally
        #    sampled ones, then trace normally. The worker's own sampling only picked the
        #    dispatcher branch; the rays actually traced are exactly the main thread's.
        capture = getattr(self.editor, "_preview_trace_bundle_capture", None)
        if isinstance(capture, list):
            capture.append(
                {
                    "bundles": [tuple(np.asarray(part, dtype=float) for part in bundle) for bundle in bundles],
                    "bundle_sources": None if bundle_sources is None else list(bundle_sources),
                    "system_id": id(system),
                }
            )
            self._last_preview_trace_backend = "async-capture"
            open3d_timing_event(
                "trace_preview_bundles_captured",
                bundle_count=len(bundles),
                total_rays=int(sum(int(len(np.asarray(bundle[0]))) for bundle in bundles)),
            )
            return
        replay = getattr(self.editor, "_preview_trace_bundle_replay", None)
        if isinstance(replay, list):
            if not replay:
                raise RuntimeError(
                    "async trace replay underrun: the worker sampling made more "
                    "_trace_preview_bundles calls than the main thread captured"
                )
            replay_call = replay.pop(0)
            bundles = [
                tuple(np.asarray(part, dtype=float) for part in bundle)
                for bundle in replay_call.get("bundles", [])
            ]
            bundle_sources = replay_call.get("bundle_sources")
        bundle_lengths = [int(len(np.asarray(bundle[0]))) for bundle in bundles]
        total_rays = int(sum(bundle_lengths))
        status = "ok"
        trace_state: dict[str, object] | None = None
        open3d_timing_event(
            "trace_preview_bundles_start",
            bundle_count=len(bundles),
            total_rays=total_rays,
            bundle_lengths=bundle_lengths[:16],
            bundle_lengths_truncated=len(bundle_lengths) > 16,
        )
        if not bundles:
            rays.clean()
            open3d_timing_event(
                "trace_preview_bundles_done",
                duration_ms=round(float((time.perf_counter() - trace_start) * 1000.0), 3),
                status=status,
                backend=self._last_preview_trace_backend,
                bundle_count=0,
                total_rays=0,
            )
            return
        try:
            row_specs = self._serializable_row_specs()
            trace_state = self._resolved_trace_mode(system=system)
            if getattr(self.editor, "_force_sequential_preview_trace", False):
                # bugs/0187 fix (3): a promoted full-mirror fold has been synthesised into a
                # sequential Mirror chain; trace it sequentially regardless of the tilted-mirror
                # off-axis classification (a non-seq trace of the folded specs reaches 0 rays).
                trace_state = {**trace_state, "use_nonseq": False, "use_folded": False, "active": "Sequential"}
            elif getattr(self.editor, "_force_nonseq_preview_trace", False):
                # bugs/0270: the additive illumination-marker EMISSION is a second source flooding a marked
                # face -- geometrically NON-sequential (it reflects through the scene) no matter what mode the
                # imaging trace resolved to. Force NsTraceLoop for the isolated marker trace so the marked-face
                # rays propagate + reflect (a sequential launch stops them at S0).
                trace_state = {**trace_state, "use_nonseq": True, "use_folded": False, "active": "Non-sequential"}
            sampling_mode = str(self.editor.__dict__.get("_active_preview_sampling_mode", "") or "ui_preview")
            launch_metadata = self._launch_metadata_for_trace(trace_state, sampling_mode=sampling_mode)

            def _bundle_launch_metadata(source: SceneSource3D | None) -> dict[str, object]:
                if source is None:
                    return dict(launch_metadata)
                return {
                    **launch_metadata,
                    "launch_ray_count": int(
                        getattr(source, "ray_count", launch_metadata.get("launch_ray_count", 1))
                        or launch_metadata.get("launch_ray_count", 1)
                    ),
                }

            if bool(trace_state.get("use_nonseq")):
                rays.clean()
                clean = 1
                restore_nonseq_settings = self._apply_nonseq_trace_settings(system)
                terminal_policy = self._trace_terminal_policy_metadata(trace_state)
                try:
                    for bundle_index, bundle in enumerate(bundles):
                        bundle_start = time.perf_counter()
                        bundle_ray_count = int(len(np.asarray(bundle[0])))
                        open3d_timing_event(
                            "trace_preview_bundle_start",
                            backend="NsTraceLoop",
                            bundle_index=int(bundle_index),
                            ray_count=bundle_ray_count,
                            clean=int(clean),
                        )
                        source = bundle_sources[bundle_index] if bundle_sources is not None and bundle_index < len(bundle_sources) else None
                        metadata = self._source_metadata_for_bundle(
                            bundle,
                            wavelength,
                            source=source,
                            terminal_policy=terminal_policy,
                            launch_metadata=_bundle_launch_metadata(source),
                        )
                        if hasattr(system, "EnableNsTraceTiming"):
                            system.EnableNsTraceTiming(True)
                        reset_mesh_trace_stats(active=True)
                        try:
                            Kos.NsTraceLoop(*bundle, wavelength, rays, clean=clean, source_metadata=metadata)
                        finally:
                            ns_loop_stats = {}
                            if hasattr(system, "NsTraceTimingSnapshot"):
                                ns_loop_stats = system.NsTraceTimingSnapshot(reset=True)
                            open3d_timing_event(
                                "trace_preview_ns_loop_stats",
                                backend="NsTraceLoop",
                                bundle_index=int(bundle_index),
                                ray_count=bundle_ray_count,
                                **ns_loop_stats,
                            )
                            open3d_timing_event(
                                "trace_preview_mesh_ray_stats",
                                backend="NsTraceLoop",
                                bundle_index=int(bundle_index),
                                ray_count=bundle_ray_count,
                                **mesh_trace_stats_snapshot(reset=True),
                            )
                        open3d_timing_event(
                            "trace_preview_bundle_done",
                            backend="NsTraceLoop",
                            bundle_index=int(bundle_index),
                            ray_count=bundle_ray_count,
                            duration_ms=round(float((time.perf_counter() - bundle_start) * 1000.0), 3),
                            ray_path_count=len(getattr(rays, "CC", []) or []),
                        )
                        clean = 0
                    self._last_preview_trace_backend = "NsTraceLoop"
                    return
                except Exception as exc:
                    status = "error"
                    rays.clean()
                    reason_text = ", ".join(str(reason) for reason in trace_state.get("reasons", ()) or ()) or "non-sequential scene request"
                    detail = _short_error_message(exc)
                    message = f"NsTraceLoop failed for {reason_text}: {detail}"
                    self._last_preview_trace_backend = "NsTraceLoop failed"
                    self._last_preview_trace_note = f"{message}; sequential fallback suppressed."
                    raise NonSequentialTracePreviewError(message, trace_state=trace_state) from exc
                finally:
                    restore_nonseq_settings()
            preview_row_specs = row_specs
            restore_image_catch = lambda: None
            image_catch_diameter = self._sequential_preview_image_catch_diameter(trace_state)
            if image_catch_diameter is not None:
                preview_row_specs = [dict(spec) for spec in row_specs]
                if preview_row_specs:
                    preview_row_specs[-1]["diameter"] = float(image_catch_diameter)
                    preview_row_specs[-1]["Diameter"] = float(image_catch_diameter)
                restore_image_catch = self._temporarily_set_system_surface_diameter(
                    system,
                    len(preview_row_specs) - 1,
                    float(image_catch_diameter),
                )
            worker_count = max(1, min(self._optimization_worker_count(), total_rays))
            scalar_required = bool(_requires_scalar_trace(preview_row_specs))
            if (
                worker_count <= 1
                or total_rays < 2
                or scalar_required
                or not hasattr(system, "BatchTrace")
                or not hasattr(rays, "batch_push")
            ):
                trace_loop = Kos.TraceLoop if scalar_required else getattr(Kos, "BatchTraceLoop", Kos.TraceLoop)
                self._last_preview_trace_backend = "Scalar TraceLoop" if trace_loop is Kos.TraceLoop else "BatchTraceLoop"
                try:
                    clean = 1
                    for bundle_index, bundle in enumerate(bundles):
                        bundle_start = time.perf_counter()
                        bundle_ray_count = int(len(np.asarray(bundle[0])))
                        open3d_timing_event(
                            "trace_preview_bundle_start",
                            backend=self._last_preview_trace_backend,
                            bundle_index=int(bundle_index),
                            ray_count=bundle_ray_count,
                            clean=int(clean),
                        )
                        source = bundle_sources[bundle_index] if bundle_sources is not None and bundle_index < len(bundle_sources) else None
                        metadata = self._source_metadata_for_bundle(
                            bundle,
                            wavelength,
                            source=source,
                            launch_metadata=_bundle_launch_metadata(source),
                        )
                        trace_loop(*bundle, wavelength, rays, clean=clean, source_metadata=metadata)
                        open3d_timing_event(
                            "trace_preview_bundle_done",
                            backend=self._last_preview_trace_backend,
                            bundle_index=int(bundle_index),
                            ray_count=bundle_ray_count,
                            duration_ms=round(float((time.perf_counter() - bundle_start) * 1000.0), 3),
                            ray_path_count=len(getattr(rays, "CC", []) or []),
                        )
                        clean = 0
                finally:
                    restore_image_catch()
                return

            rays.clean()
            executor = self._ensure_analysis_executor(worker_count)
            if executor is None:
                trace_loop = Kos.TraceLoop if scalar_required else getattr(Kos, "BatchTraceLoop", Kos.TraceLoop)
                self._last_preview_trace_backend = "Scalar TraceLoop" if trace_loop is Kos.TraceLoop else "BatchTraceLoop"
                try:
                    clean = 1
                    for bundle_index, bundle in enumerate(bundles):
                        bundle_start = time.perf_counter()
                        bundle_ray_count = int(len(np.asarray(bundle[0])))
                        open3d_timing_event(
                            "trace_preview_bundle_start",
                            backend=self._last_preview_trace_backend,
                            bundle_index=int(bundle_index),
                            ray_count=bundle_ray_count,
                            clean=int(clean),
                        )
                        source = bundle_sources[bundle_index] if bundle_sources is not None and bundle_index < len(bundle_sources) else None
                        metadata = self._source_metadata_for_bundle(
                            bundle,
                            wavelength,
                            source=source,
                            launch_metadata=_bundle_launch_metadata(source),
                        )
                        trace_loop(*bundle, wavelength, rays, clean=clean, source_metadata=metadata)
                        open3d_timing_event(
                            "trace_preview_bundle_done",
                            backend=self._last_preview_trace_backend,
                            bundle_index=int(bundle_index),
                            ray_count=bundle_ray_count,
                            duration_ms=round(float((time.perf_counter() - bundle_start) * 1000.0), 3),
                            ray_path_count=len(getattr(rays, "CC", []) or []),
                        )
                        clean = 0
                finally:
                    restore_image_catch()
                return

            merged_bundle = tuple(
                np.concatenate([np.asarray(bundle[index], dtype=float) for bundle in bundles if len(np.asarray(bundle[0])) > 0])
                for index in range(6)
            )
            merged_metadata: list[dict[str, object]] = []
            for bundle_index, bundle in enumerate(bundles):
                if len(np.asarray(bundle[0])) > 0:
                    source = bundle_sources[bundle_index] if bundle_sources is not None and bundle_index < len(bundle_sources) else None
                    merged_metadata.extend(
                        self._source_metadata_for_bundle(
                            bundle,
                            wavelength,
                            source=source,
                            launch_metadata=_bundle_launch_metadata(source),
                        )
                    )
            merged_total = len(np.asarray(merged_bundle[0]))
            if merged_total <= 0:
                self._shutdown_analysis_executor()
                return
            try:
                self._last_preview_trace_backend = "Parallel Batch preview"
                futures = []
                for chunk_index, chunk in enumerate(np.array_split(np.arange(merged_total), min(worker_count, merged_total))):
                    if chunk.size == 0:
                        continue
                    chunk_bundle = tuple(np.asarray(values)[chunk] for values in merged_bundle)
                    chunk_metadata = [merged_metadata[int(index)] for index in chunk if int(index) < len(merged_metadata)]
                    chunk_start = time.perf_counter()
                    future = executor.submit(
                            _trace_preview_chunk_batch,
                            preview_row_specs,
                            wavelength,
                            *chunk_bundle,
                        )
                    open3d_timing_event(
                        "trace_preview_parallel_chunk_submitted",
                        chunk_index=int(chunk_index),
                        ray_count=int(chunk.size),
                        submit_ms=round(float((time.perf_counter() - chunk_start) * 1000.0), 3),
                    )
                    futures.append((future, chunk_metadata, int(chunk_index), int(chunk.size)))
                for future, chunk_metadata, chunk_index, chunk_size in futures:
                    chunk_start = time.perf_counter()
                    batch_results, batch_active = future.result()
                    rays.batch_push(batch_results, batch_active, wavelength, source_metadata=chunk_metadata)
                    open3d_timing_event(
                        "trace_preview_parallel_chunk_done",
                        chunk_index=int(chunk_index),
                        ray_count=int(chunk_size),
                        duration_ms=round(float((time.perf_counter() - chunk_start) * 1000.0), 3),
                    )
            finally:
                restore_image_catch()
                self._shutdown_analysis_executor()
        except Exception:
            status = "error"
            raise
        finally:
            reason_text = ""
            if trace_state is not None:
                reason_text = ", ".join(str(reason) for reason in trace_state.get("reasons", ()) or ())
            open3d_timing_event(
                "trace_preview_bundles_done",
                duration_ms=round(float((time.perf_counter() - trace_start) * 1000.0), 3),
                status=status,
                backend=self._last_preview_trace_backend,
                bundle_count=len(bundles),
                total_rays=total_rays,
                use_nonseq=bool(trace_state.get("use_nonseq")) if trace_state is not None else False,
                trace_reasons=reason_text,
                ray_path_count=len(getattr(rays, "CC", []) or []),
            )

    def _build_pupilcalc_preview_bundles(self, system, wavelength: float, pattern: str):
        pupil = Kos.PupilCalc(
            system,
            self._analysis_surface_index(),
            float(wavelength),
            self._current_aperture_type(),
            self._current_aperture_value(),
        )
        pupil.Samp = max(2, self._current_ray_count())
        pupil.Ptype = str(pattern)
        axis = self._current_display_slice_axis()
        if self._current_object_mode() == "Infinity":
            pupil.FieldType = "angle"
            field_values = self._sample_field_values(self._current_field_angle_deg())
        else:
            pupil.FieldType = "height"
            field_values = self._sample_field_values(self._current_field_height())
        bundles = []
        for field_value in field_values:
            value = float(field_value)
            pupil.FieldX = value if axis == "x" else 0.0
            pupil.FieldY = value if axis == "y" else 0.0
            bundle = self._pupil_pattern_bundle(pupil)
            if len(bundle) == 6 and len(np.asarray(bundle[0])) > 0:
                if self._current_object_mode() == "Infinity":
                    bundle = self._center_infinity_bundle_on_launch_reference(bundle, system=system)
                bundles.append(bundle)
        rays_per_field = max((len(np.asarray(bundle[0])) for bundle in bundles), default=0)
        return bundles, int(rays_per_field)

    def _build_meridional_preview_bundles(self, pupil_radius: float, *, system=None, wavelength: float | None = None):
        """Per-field meridional fans for the 2D layout preview.

        Unlike full-pupil mode, this keeps the visible ray count tied to the
        user's `ray_count` setting so the 2D plot stays readable.
        """
        _short_error_message = _layout_module()._short_error_message
        if self._should_use_default_finite_cone_source(system=system):
            default_cone_bundles, default_cone_ray_count = self._build_default_finite_cone_preview_bundles()
            if default_cone_bundles:
                return default_cone_bundles, default_cone_ray_count

        pattern = self._current_kraken_pupil_pattern()
        if pattern is not None and system is not None and wavelength is not None:
            try:
                bundles, rays_per_field = self._build_pupilcalc_preview_bundles(system, float(wavelength), pattern)
                if bundles:
                    return bundles, rays_per_field
            except Exception as exc:
                self.append_debug(f"Pupil pattern preview failed ({_short_error_message(exc)}); using meridional fan.")

        axis = self._current_display_slice_axis()
        pupil_samples = np.asarray(self._sample_ray_heights(pupil_radius), dtype=float)
        bundles = []

        if self._current_object_mode() == "Infinity":
            if system is not None and wavelength is not None:
                try:
                    pupil = Kos.PupilCalc(
                        system,
                        self._analysis_surface_index(),
                        float(wavelength),
                        self._current_aperture_type(),
                        self._current_aperture_value(),
                    )
                    pupil.Samp = max(1, self._current_ray_count() // 2)
                    pupil.Ptype = "fan"
                    pupil.FieldType = "angle"
                    for field_angle in self._sample_field_values(self._current_field_angle_deg()):
                        angle = float(field_angle)
                        pupil.FieldX = angle if axis == "x" else 0.0
                        pupil.FieldY = angle if axis == "y" else 0.0
                        bundle = self._pupil_pattern_bundle(pupil)
                        if len(bundle) != 6 or len(bundle[0]) == 0:
                            continue
                        if axis == "x":
                            cross = np.asarray(bundle[1], dtype=float)
                        else:
                            cross = np.asarray(bundle[0], dtype=float)
                        tolerance = max(1e-8, 1e-9 * max(float(pupil_radius), 1.0))
                        mask = np.abs(cross) <= tolerance
                        if not np.any(mask):
                            center = float(np.median(cross))
                            mask = np.abs(cross - center) <= tolerance
                        if np.any(mask):
                            selected = tuple(np.asarray(values, dtype=float)[mask] for values in bundle)
                            selected_points = np.column_stack(selected)
                            if selected_points.shape[0] > 1:
                                _unique_rows, unique_idx = np.unique(
                                    np.round(selected_points, decimals=12),
                                    axis=0,
                                    return_index=True,
                                )
                                selected = tuple(values[np.sort(unique_idx)] for values in selected)
                            selected = self._center_infinity_bundle_on_launch_reference(selected, system=system)
                            bundles.append(selected)
                    if bundles:
                        return bundles, int(max(len(bundle[0]) for bundle in bundles))
                except Exception:
                    bundles = []

            field_values = self._sample_field_values(self._current_field_angle_deg())
            for field_angle in field_values:
                angle_rad = np.deg2rad(float(field_angle))
                direction = np.array([0.0, 0.0, 1.0], dtype=float)
                direction[0 if axis == "x" else 1] = np.sin(angle_rad)
                direction[2] = np.cos(angle_rad)
                norm = np.linalg.norm(direction)
                if norm <= 1e-12:
                    continue
                direction /= norm
                n_pts = len(pupil_samples)
                x_values = np.zeros(n_pts, dtype=float)
                y_values = np.zeros(n_pts, dtype=float)
                if axis == "x":
                    x_values = pupil_samples.copy()
                else:
                    y_values = pupil_samples.copy()
                bundle = (
                    x_values,
                    y_values,
                    np.zeros(n_pts, dtype=float),
                    np.full(n_pts, float(direction[0]), dtype=float),
                    np.full(n_pts, float(direction[1]), dtype=float),
                    np.full(n_pts, float(direction[2]), dtype=float),
                )
                bundle = self._center_infinity_bundle_on_launch_reference(bundle, system=system)
                bundles.append(bundle)
        else:
            field_values = self._sample_field_values(self._current_field_height())
            object_distance = self._current_object_distance()
            for field_value in field_values:
                origin = np.array([0.0, 0.0, 0.0], dtype=float)
                origin[0 if axis == "x" else 1] = float(field_value)
                x_values: list[float] = []
                y_values: list[float] = []
                z_values: list[float] = []
                l_values: list[float] = []
                m_values: list[float] = []
                n_values: list[float] = []
                for pupil_value in pupil_samples:
                    target = np.array([0.0, 0.0, object_distance], dtype=float)
                    target[0 if axis == "x" else 1] = float(pupil_value)
                    direction = target - origin
                    norm = np.linalg.norm(direction)
                    if norm <= 1e-12:
                        continue
                    direction /= norm
                    x_values.append(float(origin[0]))
                    y_values.append(float(origin[1]))
                    z_values.append(float(origin[2]))
                    l_values.append(float(direction[0]))
                    m_values.append(float(direction[1]))
                    n_values.append(float(direction[2]))
                if x_values:
                    bundles.append(
                        (
                            np.asarray(x_values, dtype=float),
                            np.asarray(y_values, dtype=float),
                            np.asarray(z_values, dtype=float),
                            np.asarray(l_values, dtype=float),
                            np.asarray(m_values, dtype=float),
                            np.asarray(n_values, dtype=float),
                        )
                    )

        return bundles, int(len(pupil_samples))
