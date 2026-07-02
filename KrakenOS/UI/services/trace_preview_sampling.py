"""Trace preview sampling and launch-bundle helpers.

This mixin owns the editor-side sampling choices that feed ``TracePreviewService``:
finite fans, pupil disks, world-envelope bundles, sparse/full pupil grids,
source model accessors, and image-diameter preview helpers.
"""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import warnings

import numpy as np

import KrakenOS as Kos
from KrakenOS.UI.layout_plot_controller import (
    build_preview_trace_signature,
    max_surface_radius,
    preview_trace_signature_matches,
)
from KrakenOS.UI.scene_geometry import SceneSource3D
from KrakenOS.UI.services.ray_display_geometry import _raykeeper_has_non_primary_branch_paths
from KrakenOS.UI.services.row_spec_contracts import _row_specs_signature
from KrakenOS.UI.services.trace_preview import TracePreviewService
from KrakenOS.UI.source_trace_helpers import (
    GAUSSIAN_INPUT_MODE_DEFAULT,
    GAUSSIAN_INPUT_MODE_VALUES,
    PUPIL_PATTERN_DEFAULT,
    PUPIL_PATTERN_TO_KRAKEN,
    PUPIL_PATTERN_VALUES,
    SOURCE_MODEL_DEFAULT,
    SOURCE_MODEL_VALUES,
    kraken_pattern_samp_for_count,
)

# bug 0041 (North Star invariant #2: 2D is a slice of the traced 3D data, not a
# separate simulation): the launch cone is the single 3D-truth pupil for a
# sequential scene. The 2D layout is the meridional slice of this same cone
# (rays at X=0), so the cone MUST contain a uniform meridional fan that matches
# the 2D's linspace heights. Two requirements follow:
#   * full radial rings (n_rings = count // 2) so the meridional spokes land
#     exactly on the 2D fan heights radius * j / n_rings, and
#   * an azimuth count divisible by 4 so the 90 deg / 270 deg spokes (the rays
#     in the YZ plane) actually exist -- otherwise the meridional slice is empty
#     and the 2D pane silently falls back to the whole projected cone.
# Density (>= 16 spokes) also keeps the down-axis view reading as a filled cone
# rather than the old crossing-fan asterisk (bug 0040).
_CONE_AZIMUTH_MIN = 16
_CONE_AZIMUTH_MAX = 24


class TracePreviewSamplingMixin:
    def _sample_ray_heights(self, max_radius: float) -> list[float]:
        if max_radius <= 1e-9:
            return [0.0]
        count = self._current_ray_count()
        span = max_radius * self._current_ray_height_factor()
        if count == 1:
            return [0.0]
        return list(np.linspace(-span, span, count))

    def _sample_field_values(self, maximum: float) -> list[float]:
        count = self._current_field_count()
        if count == 1:
            return [float(maximum)]
        span = abs(float(maximum))
        if span <= 1e-9:
            # User explicitly requested an on-axis field. Honour it instead of
            # silently inventing a synthetic ±span (the previous behaviour
            # generated phantom off-axis bundles for field_value=0).
            return [0.0] * count
        return list(np.linspace(-span, span, count))

    def _launch_field_radial_max(self) -> float:
        """Return the radial field maximum to use for finite-object launches.

        Takes the user-configured field height and clamps it by the object
        aperture (``rows[0].diameter / 2``). When a lens added or removed
        upstream changes ``_current_field_height()`` -- typically via a
        magnification shift for Real Image Height fields -- the launch grid
        automatically adapts. The clamp ensures the launch pattern never
        exceeds the object surface that physically emits the rays.

        When a vendor camera is registered, its sensor also defines the
        field of view that actually reaches the detector. The launch is
        additionally clamped to that FOV's inscribed object radius so rays
        never originate beyond the box the camera can image (bugs/0162).
        """
        height = abs(float(self._current_field_height()))
        if self.rows:
            try:
                object_radius = max(float(self.rows[0].diameter) * 0.5, 0.0)
            except Exception:
                object_radius = 0.0
            if object_radius > 0.0:
                height = min(height, object_radius)
        fov_radius = self._camera_fov_inscribed_object_radius()
        if fov_radius is not None and fov_radius > 0.0:
            height = min(height, fov_radius)
        return height

    def _camera_fov_inscribed_object_radius(self) -> float | None:
        """Inscribed radius of the registered camera's object-plane FOV box.

        A registered vendor camera's sensor maps back through the magnification
        to an object-plane field of view of half-extent ``sensor_half / |m|``
        (the green FOV overlay, ``detector_coverage_metrics``). The largest disc
        that fits inside that rectangle has radius ``min(half_w, half_h)``;
        bounding the radial field launch to it keeps every launched ray inside
        the FOV the camera can image (bugs/0162).

        Returns ``None`` when no camera is registered or the finite
        magnification is unavailable, so plain scenes keep the object-aperture
        clamp alone (and rays still launch -- never vanish).
        """
        try:
            sensor = self._current_camera_sensor_active_mm()
        except Exception:
            sensor = None
        if not sensor:
            return None
        try:
            mag = self._current_finite_paraxial_magnification()
        except Exception:
            mag = None
        if mag is None:
            return None
        try:
            m = abs(float(mag))
        except (TypeError, ValueError):
            return None
        if not np.isfinite(m) or m <= 1e-9:
            return None
        try:
            half_w = abs(float(sensor[0])) * 0.5
            half_h = abs(float(sensor[1])) * 0.5
        except (TypeError, ValueError, IndexError):
            return None
        inscribed = min(half_w, half_h)
        if inscribed <= 1e-9:
            return None
        return inscribed / m

    def _sample_field_grid_pairs(self, maximum: float) -> list[tuple[float, float]]:
        """Sample full-field preview points as an X/Y grid inscribed in the
        configured field disc.

        ``maximum`` is the user-configured radial field maximum (length or
        angle, depending on field type). A 3x3 grid is laid out so that its
        corners land exactly on that maximum and the per-axis samples sit at
        ``maximum/sqrt(2)``. The old behavior placed axis samples at the
        maximum and pushed grid corners to ``sqrt(2)*maximum``, which both
        oversampled past the user's field and (for finite-object launches)
        emitted rays from outside the object aperture. Keeping the grid
        inscribed makes the 3D preview reflect the actual achievable field
        instead of a sampling artifact.
        """
        count = self._current_field_count()
        radial_max = abs(float(maximum))
        axis_max = radial_max / float(np.sqrt(2.0)) if count > 1 else radial_max
        field_values = [float(value) for value in self._sample_field_values(axis_max)]
        if count <= 1:
            # Field Samples = 1 launches a single bundle from the object centre
            # (the on-axis field point), not the field edge -- the lone sample
            # is the chief field, matching the 2D layout's single-point fan.
            return [(0.0, 0.0)]
        pairs: list[tuple[float, float]] = []
        seen: set[tuple[float, float]] = set()
        for field_y in field_values:
            for field_x in field_values:
                key = (round(float(field_x), 12), round(float(field_y), 12))
                if key in seen:
                    continue
                seen.add(key)
                pairs.append((float(field_x), float(field_y)))
        return pairs

    def _should_use_default_finite_cone_source(self, *, system=None) -> bool:
        """Return whether Pupil/field should become a physical point source.

        It should not. Under the North Star architecture, Pupil/field remains
        the conventional prescription-analysis sampler. Non-sequential scenes
        use a 3D aperture/envelope reference by default, while physical point
        cones are launched only by explicit source models such as Random point
        cone or authored scene sources.
        """
        return False

    def _should_show_open3d_launch_reference_surface(self, *, system=None) -> bool:
        return False

    def _current_image_diameter_mode(self) -> str:
        if not hasattr(self, "image_diameter_mode_var"):
            return "Auto"
        value = self.image_diameter_mode_var.get().strip()
        return value if value in {"Auto", "Manual"} else "Auto"

    def _preview_trace_signature(self):
        return build_preview_trace_signature(
            row_specs_signature=_row_specs_signature(self._serializable_row_specs()),
            object_mode=self._current_object_mode(),
            field_type=self._current_field_type(),
            field_value=self._current_field_value(),
            field_count=self._current_field_count(),
            requested_trace_mode=self._requested_trace_mode(),
            aperture_type_label=self._current_aperture_type_label(),
            aperture_value=self._current_aperture_value(),
            wavelength=self._current_wavelength(),
            ray_count=self._current_ray_count(),
            ray_height_factor=self._current_ray_height_factor(),
            source_model=self._current_source_model(),
            pupil_pattern_label=self._current_pupil_pattern_label(),
            source_radius=self._current_source_radius(),
            source_cone_angle=self._current_source_cone_angle(),
            gaussian_input_mode=self._current_gaussian_input_mode(),
            gaussian_waist_radius=self._current_gaussian_waist_radius(),
            gaussian_waist_offset=self._current_gaussian_waist_offset(),
            gaussian_beam_diameter=self._current_gaussian_beam_diameter(),
            gaussian_full_divergence=self._current_gaussian_full_divergence(),
            gaussian_waist_after_input=self._current_gaussian_waist_after_input(),
            gaussian_m2=self._current_gaussian_m2(),
            pupil_rad=self._current_pupil_rad(),
            pupil_theta=self._current_pupil_theta(),
            source_power=self._current_source_power(),
            source_seed=self._current_source_seed(),
            source_origin=self._current_source_origin(),
            source_direction=self._current_source_direction(),
            source_angular_weight=self._current_source_angular_weight(),
            nonseq_energy_probability=self._current_nonseq_energy_probability(),
            nonseq_ns_limit=self._current_nonseq_ns_limit(),
            nonseq_target_surface_index=self._current_nonseq_target_surface_index(),
            full_pupil_mode=self._is_full_pupil_mode(),
        )

    def _build_temporary_preview_trace(self):
        wavelength = self._current_wavelength()
        max_radius = max_surface_radius(self.rows)
        previous_count = getattr(self, "_preview_field_ray_count", 1)
        previous_bundle_count = getattr(self, "_preview_field_bundle_count", 1)
        capture = io.StringIO()
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                with redirect_stdout(capture), redirect_stderr(capture):
                    system = self.build_system()
                    rays = Kos.raykeeper(system)
                    self._trace_preview_rays(
                        system,
                        rays,
                        wavelength,
                        max_radius,
                        allow_full_pupil=False,
                        sampling_mode="display_slice",
                    )
            captured = capture.getvalue()
            if captured:
                append_debug = self.__dict__.get("append_debug")
                if callable(append_debug):
                    append_debug(captured)
                elif "debug_text" in self.__dict__:
                    self.append_debug(captured)
            return system, rays
        finally:
            self._preview_field_ray_count = previous_count
            self._preview_field_bundle_count = previous_bundle_count

    def _traced_image_diameter_value(self) -> float | None:
        if not self.rows or self.rows[-1].surface != "Image":
            return None
        system = self.last_system
        rays = self.last_rays
        last_signature = self.__dict__.get("_last_preview_trace_signature")
        if system is None or rays is None or not preview_trace_signature_matches(last_signature, self._preview_trace_signature()):
            try:
                system, rays = self._build_temporary_preview_trace()
            except Exception:
                return None
        try:
            x_local, y_local, _z_local, _l_local, _m_local, _n_local = self._pick_image_plane_data(rays)
            x_local = np.asarray(x_local, dtype=float)
            y_local = np.asarray(y_local, dtype=float)
            final_surface = max(0, len(self.rows) - 1)
            reached_image = []
            for surfaces in getattr(rays, "SURFACE", ()):
                surface_arr = np.asarray(surfaces, dtype=int).ravel()
                reached_image.append(bool(surface_arr.size and int(surface_arr[-1]) == final_surface))
            if reached_image:
                reached_mask = np.asarray(reached_image, dtype=bool)
                if reached_mask.size != x_local.size:
                    return None
                x_local = x_local[reached_mask]
                y_local = y_local[reached_mask]
                if not x_local.size:
                    return None
            finite = np.isfinite(x_local) & np.isfinite(y_local)
            if not np.any(finite):
                return None
            x_local = x_local[finite]
            y_local = y_local[finite]
            diameter = max(
                float(np.ptp(x_local)),
                float(np.ptp(y_local)),
                2.0 * float(np.max(np.abs(x_local))),
                2.0 * float(np.max(np.abs(y_local))),
            )
            return max(diameter, 1.0)
        except Exception:
            return None

    def _auto_image_diameter_value(self) -> float:
        if not self.rows:
            return 3.0
        current_diameter = max(float(self.rows[-1].diameter), 1.0)
        sample_values = self._sample_field_values(self._current_field_value())
        if not sample_values:
            sample_values = [self._current_field_value()]
        height_key = "paraxial_image_height" if self._current_object_mode() == "Infinity" else "real_image_height"
        image_heights = [
            abs(float(self._field_metrics_for_value(self._current_field_type(), value).get(height_key, 0.0)))
            for value in sample_values
        ]
        traced_diameter = self._traced_image_diameter_value()
        candidates = [2.0 * max(image_heights) if image_heights else 0.0]
        finite_magnification = self._current_finite_paraxial_magnification()
        if (
            self._current_object_mode() == "Finite"
            and finite_magnification is not None
            and np.isfinite(finite_magnification)
            and self.rows
        ):
            candidates.append(abs(float(finite_magnification)) * max(float(self.rows[0].diameter), 0.0))
        if traced_diameter is not None:
            candidates.append(float(traced_diameter))
        diameter = max(candidates, default=0.0)
        if self._has_off_axis_geometry():
            diameter = min(diameter, self._auto_image_diameter_off_axis_limit())
        if diameter <= 1e-9:
            if self._has_off_axis_geometry():
                return min(current_diameter, self._auto_image_diameter_off_axis_limit())
            return current_diameter
        return max(float(diameter), 1.0)

    def _auto_image_diameter_off_axis_limit(self) -> float:
        optical_diameters = [
            max(float(row.diameter), 0.0)
            for row in self.rows[1:-1]
            if row.surface not in {"Object", "Image"}
        ]
        reference = max(optical_diameters or [1.0])
        try:
            reference = max(reference, abs(float(self._current_aperture_value())))
        except Exception:
            pass
        return max(4.0 * reference, 25.0)

    def _apply_image_diameter_mode(self) -> bool:
        if not self.rows or self.rows[-1].surface != "Image":
            return False
        if self._current_image_diameter_mode() != "Auto":
            return False
        new_diameter = self._auto_image_diameter_value()
        if abs(float(self.rows[-1].diameter) - float(new_diameter)) <= 1e-9:
            return False
        self.rows[-1].diameter = float(new_diameter)
        return True

    def _sample_fan_angles_deg(self) -> list[float]:
        maximum = self._current_field_angle_deg()
        count = self._current_ray_count()
        if count == 1 or maximum <= 1e-9:
            return [0.0]
        return list(np.linspace(-maximum, maximum, count))

    def _build_default_finite_cone_preview_bundles(self) -> tuple[
        list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]],
        int,
    ]:
        if self._current_source_model() != SOURCE_MODEL_DEFAULT:
            return [], 0
        cone_deg = float(self._current_source_cone_angle())
        if cone_deg <= 1e-12:
            return [], 0
        ray_count = max(1, int(self._current_ray_count()))
        angles_deg = np.asarray([0.0] if ray_count == 1 else np.linspace(-cone_deg, cone_deg, ray_count), dtype=float)
        angles_rad = np.deg2rad(angles_deg)
        axis_index = 0 if self._current_display_slice_axis() == "x" else 1
        field_values = self._sample_field_values(self._current_field_height())
        bundles: list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = []
        for field_value in field_values:
            x_values = np.zeros(ray_count, dtype=float)
            y_values = np.zeros(ray_count, dtype=float)
            if axis_index == 0:
                x_values.fill(float(field_value))
            else:
                y_values.fill(float(field_value))
            l_values = np.zeros(ray_count, dtype=float)
            m_values = np.zeros(ray_count, dtype=float)
            if axis_index == 0:
                l_values = np.sin(angles_rad).astype(float)
            else:
                m_values = np.sin(angles_rad).astype(float)
            n_values = np.cos(angles_rad).astype(float)
            bundles.append(
                (
                    x_values,
                    y_values,
                    np.zeros(ray_count, dtype=float),
                    l_values,
                    m_values,
                    n_values,
                )
            )
        return bundles, ray_count

    def _build_default_finite_cone_world_bundles(self) -> tuple[
        list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]],
        int,
    ]:
        if self._current_source_model() != SOURCE_MODEL_DEFAULT:
            return [], 0
        cone_deg = float(self._current_source_cone_angle())
        if cone_deg <= 1e-12:
            return [], 0
        ray_count = max(1, int(self._current_ray_count()))
        from KrakenOS.UI.source_trace_helpers import finite_cone_direction_samples

        l_values, m_values, n_values = finite_cone_direction_samples(
            cone_deg,
            ray_count,
            pupil_pattern=self._current_pupil_pattern_label(),
            display_orientation=self._current_display_orientation(),
            pupil_rad=self._current_pupil_rad(),
            pupil_theta=self._current_pupil_theta(),
            seed=self._current_source_seed(),
        )
        ray_count = int(len(l_values))
        field_pairs = (
            [(0.0, 0.0)]
            if self._current_object_mode() == "Infinity"
            else self._sample_field_grid_pairs(self._launch_field_radial_max())
        )
        bundles: list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = []
        for field_x, field_y in field_pairs:
            bundles.append(
                self._orient_source_points_and_dirs(
                    np.full(ray_count, float(field_x), dtype=float),
                    np.full(ray_count, float(field_y), dtype=float),
                    np.zeros(ray_count, dtype=float),
                    l_values.copy(),
                    m_values.copy(),
                    n_values.copy(),
                )
            )
        return bundles, ray_count

    def _build_default_nonseq_reference_world_bundles(
        self,
        pupil_radius: float,
    ) -> tuple[
        list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]],
        int,
    ]:
        if self._current_source_model() != SOURCE_MODEL_DEFAULT:
            return [], 0
        ray_count = max(1, int(self._current_ray_count()))
        cone_deg = float(self._current_source_cone_angle())
        from KrakenOS.UI.source_trace_helpers import finite_cone_direction_samples

        cone_l, cone_m, cone_n = finite_cone_direction_samples(
            cone_deg,
            ray_count,
            pupil_pattern=self._current_pupil_pattern_label(),
            display_orientation=self._current_display_orientation(),
            pupil_rad=self._current_pupil_rad(),
            pupil_theta=self._current_pupil_theta(),
            seed=self._current_source_seed(),
        )
        ray_count = max(1, int(len(cone_l)))
        radius = max(float(self._current_source_radius()), 0.0)
        if radius <= 1e-9:
            radius = float(pupil_radius) if np.isfinite(float(pupil_radius)) else 0.0
        if radius <= 1e-9:
            radius = 1.0
        disk_pts = self._sample_reference_disk_points_3d(radius, ray_count)
        bundles: list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = []
        if self._current_object_mode() == "Infinity" or self._current_field_type() == "Angle":
            pairs = self._sample_field_grid_pairs(self._current_field_angle_deg())
            for field_x, field_y in pairs:
                tan_x = np.tan(np.deg2rad(float(field_x)))
                tan_y = np.tan(np.deg2rad(float(field_y)))
                direction = np.array([tan_x, tan_y, 1.0], dtype=float)
                norm = float(np.linalg.norm(direction))
                if norm <= 1e-12:
                    continue
                direction /= norm
                l_values, m_values, n_values = self._cone_directions_about_local_base(
                    direction,
                    cone_l,
                    cone_m,
                    cone_n,
                )
                bundles.append(
                    self._orient_source_points_and_dirs(
                        np.asarray(disk_pts[:, 0], dtype=float),
                        np.asarray(disk_pts[:, 1], dtype=float),
                        np.zeros(len(disk_pts), dtype=float),
                        l_values,
                        m_values,
                        n_values,
                    )
                )
        else:
            pairs = self._sample_field_grid_pairs(self._launch_field_radial_max())
            for field_x, field_y in pairs:
                bundles.append(
                    self._orient_source_points_and_dirs(
                        np.asarray(disk_pts[:, 0], dtype=float) + float(field_x),
                        np.asarray(disk_pts[:, 1], dtype=float) + float(field_y),
                        np.zeros(len(disk_pts), dtype=float),
                        cone_l,
                        cone_m,
                        cone_n,
                    )
                )
        return bundles, int(len(disk_pts))

    def _entrance_radius(self, fallback_radius: float) -> float:
        object_radius = None
        if self.rows:
            object_radius = max(float(self.rows[0].diameter) / 2.0, 0.5)
        for row in self.rows[1:]:
            if row.surface not in {"Object", "Image"}:
                radius = max(row.diameter / 2.0, 0.5)
                if object_radius is not None:
                    return min(radius, object_radius)
                return radius
        if object_radius is not None:
            return min(fallback_radius, object_radius)
        return fallback_radius

    def _resolved_preview_pupil_radius(
        self,
        fallback_radius: float,
        *,
        system=None,
        wavelength: float | None = None,
    ) -> float:
        radius = max(self._entrance_radius(fallback_radius), 1e-6)
        aperture_radius = None
        aperture_value = abs(float(self._current_aperture_value()))
        if aperture_value > 1e-9:
            aperture_radius = aperture_value * 0.5
        if system is not None:
            try:
                pupil_system, _pupil_rows, pupil_surface_index = self._pupil_model_inputs(
                    system,
                    build_reference=True,
                )
                pupil = Kos.PupilCalc(
                    pupil_system,
                    pupil_surface_index,
                    self._current_wavelength() if wavelength is None else float(wavelength),
                    self._current_aperture_type(),
                    self._current_aperture_value(),
                )
                pupil_radius = float(getattr(pupil, "RadPupInp", 0.0))
                if np.isfinite(pupil_radius) and pupil_radius > 1e-9:
                    aperture_radius = pupil_radius
            except Exception:
                pass
        if aperture_radius is None or not np.isfinite(aperture_radius) or aperture_radius <= 1e-9:
            return radius
        return max(min(radius, float(aperture_radius)), 1e-6)

    def _launch_reference_entrance_pupil_z(self, system) -> float | None:
        """bugs/0100: world z of the FIRST-ORDER TRANSMISSIVE reference's entrance pupil.

        The correct aim point for finite-object WORLD bundles (envelope / cone / sparse). They aim
        at ``_current_object_distance`` (= rows[0].thickness), which an in-path beam-splitter / plate
        promotion shrinks from object->lens to object->cube -- so the bundle converged ON the splitter
        ("beam focuses at the splitter") instead of filling the lens pupil. The reference (cube reduced
        to its transmissive plate, mirrors folded out) lets the sequential PupilCalc find the true lens
        entrance pupil (``PosPupInp`` z). The grid sampler already aims off this via
        ``Kos.PupilCalc.Pattern2Field``; the world samplers did not. Returns None on failure (the caller
        falls back to ``object_distance``)."""
        if system is None:
            return None
        try:
            pupil_system, _pupil_rows, pupil_index = self._pupil_model_inputs(system, build_reference=True)
            pupil = Kos.PupilCalc(
                pupil_system,
                pupil_index,
                self._current_wavelength(),
                self._current_aperture_type(),
                self._current_aperture_value(),
            )
            z = float(np.asarray(getattr(pupil, "PosPupInp", None), dtype=float).reshape(-1)[2])
            return z if np.isfinite(z) else None
        except Exception as exc:
            self._note_pupil_launch_fallback(exc)
            return None

    def _trace_preview_service(self) -> TracePreviewService:
        service = self.__dict__.get("_trace_preview_service_instance")
        if service is None:
            service = TracePreviewService(self)
            self._trace_preview_service_instance = service
        return service

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
        self._trace_preview_service()._trace_preview_rays(
            system,
            rays,
            wavelength,
            max_radius,
            allow_full_pupil=allow_full_pupil,
            sampling_mode=sampling_mode,
        )

    def _trace_preview_bundles(
        self,
        system,
        rays,
        wavelength: float,
        bundles: list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]],
        *,
        bundle_sources: list[SceneSource3D | None] | None = None,
    ) -> None:
        self._trace_preview_service()._trace_preview_bundles(
            system,
            rays,
            wavelength,
            bundles,
            bundle_sources=bundle_sources,
        )

    def _build_pupilcalc_preview_bundles(self, system, wavelength: float, pattern: str):
        return self._trace_preview_service()._build_pupilcalc_preview_bundles(system, wavelength, pattern)

    def _build_meridional_preview_bundles(self, pupil_radius: float, *, system=None, wavelength: float | None = None):
        return self._trace_preview_service()._build_meridional_preview_bundles(
            pupil_radius,
            system=system,
            wavelength=wavelength,
        )

    def _sequential_preview_image_catch_diameter(self, trace_state: dict[str, object] | None = None) -> float | None:
        if trace_state is not None and bool(trace_state.get("use_nonseq")):
            return None
        if not self.rows or str(self.rows[-1].surface) != "Image":
            return None
        try:
            current = max(float(self.rows[-1].diameter), 1.0)
        except Exception:
            current = 1.0
        axial_span = 0.0
        max_clear = current
        for row in self.rows:
            try:
                axial_span += abs(float(row.thickness))
            except Exception:
                pass
            try:
                max_clear = max(max_clear, abs(float(row.diameter)))
            except Exception:
                pass
        catch = max(current, 4.0 * axial_span, 20.0 * max_clear, 1000.0)
        return float(catch) if catch > current + 1e-9 else None

    @staticmethod
    def _temporarily_set_system_surface_diameter(system, surface_index: int, diameter: float):
        edits: list[tuple[object, float]] = []
        seen_surfaces: set[int] = set()
        if system is None or surface_index < 0:
            return lambda: None
        for attr in ("SDT", "SDT_0"):
            surfaces = getattr(system, attr, None)
            try:
                surface = surfaces[surface_index]
            except Exception:
                continue
            surface_id = id(surface)
            if surface_id in seen_surfaces:
                continue
            seen_surfaces.add(surface_id)
            if not hasattr(surface, "Diameter"):
                continue
            try:
                previous = float(surface.Diameter)
                surface.Diameter = float(diameter)
                edits.append((surface, previous))
            except Exception:
                continue

        def restore() -> None:
            for surface, previous in edits:
                try:
                    surface.Diameter = previous
                except Exception:
                    pass

        return restore

    def _is_full_pupil_mode(self) -> bool:
        emit_full_ray_var = self.__dict__.get("emit_full_ray_var")
        return bool(emit_full_ray_var and emit_full_ray_var.get())

    def _sample_pupil_disk(self, max_radius: float, rings: int | None = None) -> np.ndarray:
        """Generate a hexapolar grid of (x, y) points filling the full circular pupil.

        ``rings`` defaults to ``max(3, ray_count)``. Pass an explicit value for
        a coarser sampling — e.g. when sampling the field axis as well as the
        pupil axis, you typically want fewer field samples than pupil samples.
        """
        if max_radius <= 1e-9:
            return np.array([[0.0, 0.0]])
        if rings is None:
            rings = max(3, self._current_ray_count())
        rings = max(1, int(rings))
        pts = [[0.0, 0.0]]
        for j in range(1, rings + 1):
            r = max_radius * j / rings
            n_pts = max(6, j * 6)
            for k in range(n_pts):
                angle = 2.0 * np.pi * k / n_pts
                pts.append([r * np.cos(angle), r * np.sin(angle)])
        return np.array(pts, dtype=float)

    def _sample_pupil_rim(self, max_radius: float, samples: int | None = None) -> np.ndarray:
        """Generate center plus boundary pupil samples for source-driven 3D envelope views."""
        radius = float(max_radius) if np.isfinite(float(max_radius)) else 0.0
        if radius <= 1e-9:
            return np.array([[0.0, 0.0]], dtype=float)
        if samples is None:
            samples = max(8, min(12, self._current_ray_count()))
        samples = max(4, int(samples))
        angles = np.linspace(0.0, 2.0 * np.pi, samples, endpoint=False)
        rim = np.column_stack((radius * np.cos(angles), radius * np.sin(angles))).astype(float)
        return np.vstack((np.asarray([[0.0, 0.0]], dtype=float), rim))

    def _scene_breaks_rotational_symmetry(self) -> bool:
        """True if any element tilts, transversely decentres, or folds the path.

        An element rotated (any tilt) or slid OFF the optical axis
        (``desp_x`` / ``desp_y``) -- or a reflective fold (a sequential ``Mirror``
        surface OR a PROMOTED mirror cube whose ``OpticalSolidFaces`` carries a
        ``function == "Mirror"`` face) -- destroys the rotational symmetry that lets
        a non-sequential scene be sampled by a flat meridional fan; such a scene
        must keep the area-filling disk so the off-axis / folded deflection is
        captured. An axial slide (``desp_z`` only, an element moved ALONG the axis)
        preserves the symmetry and must NOT trip this -- unlike
        ``has_nonseq_geometry``, which counts any ``desp_z`` too. bugs/0186: a
        promoted right-angle mirror folds +Z -> +X but its row is ``surface =
        "Standard"`` with only ``desp_z``, so without the OpticalSolidFaces check
        the folded RA-mirror scene was misread as the bug-0126 in-line refractive
        solid and its launch collapsed to a flat fan instead of revolving a cone.
        """
        from KrakenOS.UI.trace_intent import _optical_solid_faces_have_mirror_fold

        for row in getattr(self, "rows", None) or []:
            if str(getattr(row, "surface", "") or "").strip().lower() == "mirror":
                return True
            advanced = getattr(row, "advanced", None)
            if isinstance(advanced, dict) and _optical_solid_faces_have_mirror_fold(
                advanced.get("OpticalSolidFaces")
            ):
                return True
            for attr in ("tilt_x", "tilt_y", "tilt_z", "desp_x", "desp_y"):
                try:
                    if abs(float(getattr(row, attr, 0.0) or 0.0)) > 1e-9:
                        return True
                except (TypeError, ValueError):
                    continue
        return False

    def _scene_has_promoted_mirror_fold(self) -> bool:
        """True iff a PROMOTED mirror cube folds the path (an ``OpticalSolidFaces``
        ``function == "Mirror"`` face). Unlike ``_scene_breaks_rotational_symmetry``
        this ignores a bare tilt / decentre and a sequential ``Mirror`` surface --
        only the promoted right-angle fold (the AZ85 RA-mirror, bugs/0185-0203) is
        traced through a straight-equivalent SEQUENTIAL system (bugs/0197), so its
        revolved launch cone is provably just the rotated sequential cone.
        """
        from KrakenOS.UI.trace_intent import _optical_solid_faces_have_mirror_fold

        for row in getattr(self, "rows", None) or []:
            advanced = getattr(row, "advanced", None)
            if isinstance(advanced, dict) and _optical_solid_faces_have_mirror_fold(
                advanced.get("OpticalSolidFaces")
            ):
                return True
        return False

    def _folded_scene_prefers_launch_cone(self) -> bool:
        """Whether a folded RA-mirror scene should launch a dense revolved 3D cone
        instead of the sparse area-filling ``world_envelope``.

        bugs/0203 (#2): the folded AZ85 resolves to ``use_nonseq`` (its promoted
        mesh mirror reads as an "STL optical solid"), so ``_preview_3d_sampling_mode``
        gave it ``world_envelope`` -- only ``Ray Count`` (~31) golden-angle pupil
        points. Over the slender f/13 fold that disk foreshortens to a sparse sheet
        and reads as a flat FAN, not a cone ("old bug resurface"). The envelope is
        only needed when paths BRANCH (beam splitter / diffuse / probabilistic
        split) and each branch's sagittal width must be preserved. A single fold has
        no branch and is traced through its straight-equivalent SEQUENTIAL rows, so
        it takes the dense structured cone like any sequential scene -- each pupil
        ray is still traced individually through the fold, so nothing is lost and
        the converged focus (bugs/0197 rigid flip) is preserved.
        """
        if self._is_full_pupil_mode():
            return False
        try:
            trace_state = self._resolved_trace_mode(system=self.__dict__.get("last_system"))
        except Exception:
            return False
        if not (bool(trace_state.get("use_folded")) or bool(trace_state.get("use_nonseq"))):
            return False  # a plain sequential scene already revolves via the fan gate
        if (
            bool(trace_state.get("has_beam_splitter"))
            or bool(trace_state.get("has_diffuse_scatter"))
            or bool(trace_state.get("has_probabilistic_nonseq"))
        ):
            return False  # branching: keep the per-branch area-filling envelope
        return self._scene_has_promoted_mirror_fold()

    def _launch_pupil_prefers_meridional_fan(self) -> bool:
        """Return whether the ``Ray Count`` pupil should be a uniform fan.

        Sequential, non-folded scenes draw a uniformly spaced meridional ray fan
        (Zemax-style tangential fan) so the 2D layout shows even gaps between the
        rays launched from a single object point.

        A non-sequential / folded scene keeps the area-filling disk when it can
        branch (beam splitter / probabilistic split / diffuse scatter), folds
        (mirror), or breaks rotational symmetry (a tilted / transversely
        decentred element) -- the disk preserves the sagittal width those paths
        need, so rays never silently vanish from a split or off-axis branch. Only
        a provably non-branching, rotationally-symmetric non-seq scene -- an
        in-line refractive solid slid along the axis -- collapses back to the
        cheap uniform Ray-Count fan. bugs/0126: that scene used to revolve Ray
        Count 20 into ``1 + (20//2)*20 = 201`` slow non-seq mesh traces, so
        "Show rays" ignored the ray count and "Trace Now" ran for ~70 s.

        bugs/0203 (#2): a folded RA-mirror scene is traced through its UNFOLDED,
        mirror-removed straight equivalent (bugs/0197). Those swapped-in rows read
        as a plain sequential scene, which would collapse the launch to a flat
        meridional fan -- but the REAL scene folds (breaks rotational symmetry) and
        must keep the area-filling disk. ``_trace_preview_rays_folded_aware`` sets
        ``_force_folded_cone_preview_trace`` around that trace so the launch follows
        the folded scene, not the equivalent rows.
        """
        if bool(self.__dict__.get("_force_folded_cone_preview_trace", False)):
            return False
        try:
            trace_state = self._resolved_trace_mode(system=self.__dict__.get("last_system"))
        except Exception:
            trace_state = {}
        if not (bool(trace_state.get("use_nonseq")) or bool(trace_state.get("use_folded"))):
            return True
        if bool(trace_state.get("use_folded")):
            return False
        if bool(trace_state.get("has_beam_splitter")):
            return False
        if bool(trace_state.get("has_probabilistic_nonseq")):
            return False
        if bool(trace_state.get("has_diffuse_scatter")):
            return False
        if self._scene_breaks_rotational_symmetry():
            return False
        # An unexplained ``use_nonseq`` fails toward the disk: only collapse to
        # the fan when the non-seq is positively a non-branching refractive solid.
        if not bool(trace_state.get("has_optical_stl_solid")):
            return False
        return True

    def _launch_cone_prefers_flat_fan(self) -> bool:
        """Whether the 3D launch CONE stays a flat meridional fan (vs revolving).

        bugs/0161: a plain sequential point source revolves into a real 3D cone
        (cheap sequential traces) so it reads as a cone, while its X=0 meridional
        slice stays the even Ray-Count fan -- an odd Ray Count makes that slice
        exactly N rays (hence the discrete odd Ray-Count steps). The flat fan is
        kept ONLY for the bug-0126 carve-out: a scene forced non-sequential by an
        in-line refractive mesh solid, whose mesh traces are too slow to revolve
        (Ray Count 20 -> 201 traces -> ~70 s). The 2D pupil
        (``_sample_ray_count_pupil_points``) still follows
        ``_launch_pupil_prefers_meridional_fan`` and stays a flat fan either way.
        """
        if not self._launch_pupil_prefers_meridional_fan():
            # Branching / folded / tilted scene: the area-filling revolved disk.
            return False
        # ``_launch_pupil_prefers_meridional_fan`` is True for BOTH a plain
        # sequential scene and the 0126 non-seq inline-solid carve-out. Revolve
        # the cheap sequential scene; keep the flat fan only for the non-seq solid.
        try:
            trace_state = self._resolved_trace_mode(system=self.__dict__.get("last_system"))
        except Exception:
            trace_state = {}
        return bool(trace_state.get("use_nonseq"))

    def _sample_ray_count_pupil_points(self, max_radius: float) -> np.ndarray:
        """Generate exactly ``Ray Count`` deterministic 3D pupil samples."""
        radius = float(max_radius) if np.isfinite(float(max_radius)) else 0.0
        if radius <= 1e-9 and self.rows:
            try:
                radius = max(float(self.rows[0].diameter) * 0.5, 0.0)
            except Exception:
                radius = 0.0
        if radius <= 1e-9:
            radius = 1.0
        count = max(1, int(self._current_ray_count()))
        if count == 1:
            return np.asarray([[0.0, 0.0]], dtype=float)
        if self._launch_pupil_prefers_meridional_fan():
            # Uniformly spaced fan along the display-slice meridian: even ray
            # gaps in the 2D layout and a clean planar fan in 3D.
            heights = np.linspace(-radius, radius, count)
            zeros = np.zeros(count, dtype=float)
            if self._current_display_slice_axis() == "x":
                return np.column_stack((heights, zeros)).astype(float)
            return np.column_stack((zeros, heights)).astype(float)
        points: list[list[float]] = [[0.0, 0.0]]
        golden_angle = np.pi * (3.0 - np.sqrt(5.0))
        denominator = max(1, count - 1)
        for index in range(1, count):
            fraction = float(index) / float(denominator)
            r = radius * np.sqrt(fraction)
            angle = float(index) * golden_angle
            points.append([float(r * np.cos(angle)), float(r * np.sin(angle))])
        return np.asarray(points[:count], dtype=float)

    def _cone_azimuth_count(self) -> int:
        """Azimuthal spokes used when the meridional fan is revolved into a 3D cone.

        Returns a multiple of 4 in ``[_CONE_AZIMUTH_MIN, _CONE_AZIMUTH_MAX]``.
        Divisibility by 4 guarantees spokes at 90 deg and 270 deg, i.e. rays in
        the YZ meridional plane -- these are exactly the 2D slice (bug 0041). The
        density also keeps the down-axis view a filled cone, not a crossing-fan
        asterisk (bug 0040).
        """
        count = max(1, int(self._current_ray_count()))
        clamped = max(_CONE_AZIMUTH_MIN, min(_CONE_AZIMUTH_MAX, count))
        return int(4 * round(clamped / 4.0))

    def _sample_ray_count_cone_points(self, max_radius: float) -> np.ndarray:
        """3D launch-cone pupil samples: the uniform meridional fan revolved about the axis.

        This is the single 3D-truth pupil for a sequential scene (bug 0041). The
        radial rings are ``count // 2`` (uniform out to the pupil rim), so the
        meridional spokes land exactly on the 2D fan heights
        ``radius * j / n_rings`` -- the 2D layout is the X=0 slice of this very
        cone, not a separate fan. The fan is revolved into ``_cone_azimuth_count``
        spokes (a multiple of 4 so the 90/270 deg meridional spokes exist, and
        dense enough that the down-axis view reads as a filled cone).
        """
        radius = float(max_radius) if np.isfinite(float(max_radius)) else 0.0
        if radius <= 1e-9 and self.rows:
            try:
                radius = max(float(self.rows[0].diameter) * 0.5, 0.0)
            except Exception:
                radius = 0.0
        if radius <= 1e-9:
            radius = 1.0
        count = max(1, int(self._current_ray_count()))
        if count == 1:
            return np.asarray([[0.0, 0.0]], dtype=float)
        if self._launch_cone_prefers_flat_fan():
            # bugs/0096 + 0126: a non-seq scene forced off-sequential ONLY by an
            # in-line refractive mesh solid keeps a FLAT fan of exactly N rays --
            # revolving it into 1 + (count//2)*azimuth slow mesh traces (N=20 ->
            # 201) ran ~70 s. bugs/0161: a plain SEQUENTIAL point source no longer
            # collapses here -- it revolves (below) into a real cone (cheap
            # sequential traces), and its X=0 slice stays the even N-ray fan
            # because an odd Ray Count lands the meridional spokes on
            # linspace(-radius, radius, count). Branching / folded scenes also
            # revolve into the area-filling disk the 3D envelope needs.
            heights = np.linspace(-radius, radius, count)
            zeros = np.zeros(count, dtype=float)
            if self._current_display_slice_axis() == "x":
                return np.column_stack((heights, zeros)).astype(float)
            return np.column_stack((zeros, heights)).astype(float)
        n_rings = max(1, count // 2)
        n_az = self._cone_azimuth_count()
        radii = radius * (np.arange(1, n_rings + 1, dtype=float) / float(n_rings))
        azimuths = np.linspace(0.0, 2.0 * np.pi, n_az, endpoint=False)
        points: list[list[float]] = [[0.0, 0.0]]
        for ring_radius in radii:
            for theta in azimuths:
                points.append([float(ring_radius * np.cos(theta)), float(ring_radius * np.sin(theta))])
        return np.asarray(points, dtype=float)

    def _sample_sparse_pupil_disk(self, max_radius: float) -> np.ndarray:
        """Sparse filled pupil used only to discover the through-going 3D envelope."""
        radius = float(max_radius) if np.isfinite(float(max_radius)) else 0.0
        if radius <= 1e-9:
            return np.array([[0.0, 0.0]], dtype=float)
        samples = max(8, min(12, self._current_ray_count()))
        pts: list[list[float]] = [[0.0, 0.0]]
        for fraction in (0.25, 0.5, 0.75, 1.0):
            r = radius * fraction
            for angle in np.linspace(0.0, 2.0 * np.pi, samples, endpoint=False):
                pts.append([float(r * np.cos(angle)), float(r * np.sin(angle))])
        unique = np.unique(np.round(np.asarray(pts, dtype=float), decimals=12), axis=0)
        return np.asarray(unique, dtype=float)

    def _build_world_envelope_bundles(self, pupil_radius: float, *, system=None):
        """Build source-driven 3D pupil bundles for 2D/Open 3D preview.

        This is trace sampling, not display decimation: the bundle contains
        exactly ``Ray Count`` pupil samples for each effective field point.
        """
        radius = float(pupil_radius) if np.isfinite(float(pupil_radius)) else 0.0
        if radius <= 1e-9 and self.rows:
            try:
                radius = max(float(self.rows[0].diameter) * 0.5, 0.0)
            except Exception:
                radius = 0.0
        if radius <= 1e-9:
            radius = 1.0
        pupil_pts = self._sample_ray_count_pupil_points(radius)
        return self._build_world_bundles_from_pupil_points(pupil_pts, system=system)

    def _build_world_cone_bundles(self, pupil_radius: float, *, system=None):
        """Build the 3D launch-cone pupil bundles (the revolved meridional fan)."""
        radius = float(pupil_radius) if np.isfinite(float(pupil_radius)) else 0.0
        if radius <= 1e-9 and self.rows:
            try:
                radius = max(float(self.rows[0].diameter) * 0.5, 0.0)
            except Exception:
                radius = 0.0
        if radius <= 1e-9:
            radius = 1.0
        pupil_pts = self._sample_ray_count_cone_points(radius)
        return self._build_world_bundles_from_pupil_points(pupil_pts, system=system)

    def _build_world_sparse_pupil_bundles(self, pupil_radius: float, *, system=None):
        radius = float(pupil_radius) if np.isfinite(float(pupil_radius)) else 0.0
        if radius <= 1e-9 and self.rows:
            try:
                radius = max(float(self.rows[0].diameter) * 0.5, 0.0)
            except Exception:
                radius = 0.0
        if radius <= 1e-9:
            radius = 1.0
        return self._build_world_bundles_from_pupil_points(self._sample_sparse_pupil_disk(radius), system=system)

    def _sample_world_section_pupil_points(self, max_radius: float) -> np.ndarray:
        radius = float(max_radius) if np.isfinite(float(max_radius)) else 0.0
        if radius <= 1e-9 and self.rows:
            try:
                radius = max(float(self.rows[0].diameter) * 0.5, 0.0)
            except Exception:
                radius = 0.0
        if radius <= 1e-9:
            radius = 1.0
        axis_samples = np.asarray(self._sample_ray_heights(radius), dtype=float)
        points: list[list[float]] = []
        for y_value in axis_samples:
            points.append([0.0, float(y_value)])
        for x_value in axis_samples:
            points.append([float(x_value), 0.0])
        for x_value, y_value in self._sample_pupil_rim(radius):
            points.append([float(x_value), float(y_value)])
        if not points:
            return np.asarray([[0.0, 0.0]], dtype=float)
        unique = np.unique(np.round(np.asarray(points, dtype=float), decimals=12), axis=0)
        return np.asarray(unique, dtype=float)

    def _field_cross_pairs_for_world_sections(self, maximum: float) -> list[tuple[float, float]]:
        if self._current_field_count() <= 1:
            # Field Samples = 1 -> a single on-axis (object-centre) field point.
            return [(0.0, 0.0)]
        values = [float(value) for value in self._sample_field_values(maximum)]
        if not values:
            values = [0.0]
        pairs: list[tuple[float, float]] = []
        seen: set[tuple[float, float]] = set()
        for value in values:
            for pair in ((float(value), 0.0), (0.0, float(value))):
                key = (round(pair[0], 12), round(pair[1], 12))
                if key in seen:
                    continue
                seen.add(key)
                pairs.append(pair)
        return pairs

    def _build_world_section_bundles(self, pupil_radius: float, *, system=None):
        pupil_points = self._sample_world_section_pupil_points(pupil_radius)
        if self._current_object_mode() == "Infinity":
            field_pairs = self._field_cross_pairs_for_world_sections(self._current_field_angle_deg())
        else:
            field_pairs = self._field_cross_pairs_for_world_sections(self._current_field_height())
        return self._build_world_bundles_from_pupil_points(pupil_points, field_pairs=field_pairs, system=system)

    def _build_world_bundles_from_pupil_points(
        self,
        pupil_points: np.ndarray,
        *,
        field_pairs: list[tuple[float, float]] | None = None,
        system=None,
    ):
        pupil_points = np.asarray(pupil_points, dtype=float)
        if pupil_points.ndim != 2 or pupil_points.shape[0] == 0 or pupil_points.shape[1] < 2:
            pupil_points = np.array([[0.0, 0.0]], dtype=float)
        bundles = []
        if self._current_object_mode() == "Infinity":
            pairs = field_pairs if field_pairs is not None else self._sample_field_grid_pairs(self._current_field_angle_deg())
            for field_x, field_y in pairs:
                tan_x = np.tan(np.deg2rad(float(field_x)))
                tan_y = np.tan(np.deg2rad(float(field_y)))
                direction = np.array([tan_x, tan_y, 1.0], dtype=float)
                norm = float(np.linalg.norm(direction))
                if norm <= 1e-12:
                    continue
                direction /= norm
                n_pts = len(pupil_points)
                bundle = (
                    np.asarray(pupil_points[:, 0], dtype=float),
                    np.asarray(pupil_points[:, 1], dtype=float),
                    np.zeros(n_pts, dtype=float),
                    np.full(n_pts, float(direction[0]), dtype=float),
                    np.full(n_pts, float(direction[1]), dtype=float),
                    np.full(n_pts, float(direction[2]), dtype=float),
                )
                bundle = self._center_infinity_bundle_on_launch_reference(bundle, system=system)
                bundles.append(bundle)
        else:
            object_distance = self._current_object_distance()
            # bugs/0100: aim finite-object world bundles at the first-order REFERENCE entrance pupil,
            # not rows[0].thickness -- an in-path beam-splitter/plate promotion shrinks it to
            # object->cube, so the bundle converged ON the splitter instead of filling the lens pupil.
            aim_z = self._launch_reference_entrance_pupil_z(system)
            if aim_z is None or not np.isfinite(aim_z):
                aim_z = object_distance
            pairs = (
                field_pairs
                if field_pairs is not None
                else self._sample_field_grid_pairs(self._launch_field_radial_max())
            )
            for field_x, field_y in pairs:
                origin = np.array([-float(field_x), -float(field_y), 0.0], dtype=float)
                x_vals: list[float] = []
                y_vals: list[float] = []
                z_vals: list[float] = []
                l_vals: list[float] = []
                m_vals: list[float] = []
                n_vals: list[float] = []
                for pupil_x, pupil_y in pupil_points[:, :2]:
                    target = np.array([float(pupil_x), float(pupil_y), aim_z], dtype=float)
                    direction = target - origin
                    norm = float(np.linalg.norm(direction))
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
                    bundles.append(
                        (
                            np.asarray(x_vals, dtype=float),
                            np.asarray(y_vals, dtype=float),
                            np.asarray(z_vals, dtype=float),
                            np.asarray(l_vals, dtype=float),
                            np.asarray(m_vals, dtype=float),
                            np.asarray(n_vals, dtype=float),
                        )
                    )
        return bundles, int(len(pupil_points))

    def _trace_world_envelope_rays(self, system, rays, wavelength: float, pupil_radius: float) -> bool:
        boundary_bundles, _boundary_count = self._build_world_envelope_bundles(pupil_radius, system=system)
        if not boundary_bundles:
            return False
        if self._trace_selected_through_envelope(system, rays, wavelength, boundary_bundles):
            return True

        sparse_bundles, _sparse_count = self._build_world_sparse_pupil_bundles(pupil_radius, system=system)
        if sparse_bundles and self._trace_selected_through_envelope(system, rays, wavelength, sparse_bundles):
            return True

        # If every sampled envelope is clipped, still show the physical
        # boundary rather than returning no rays; the status/debug output makes
        # the clipping explicit for diagnostics.
        rays.clean()
        self._trace_preview_bundles(system, rays, wavelength, boundary_bundles)
        self._preview_field_ray_count = max(1, int(_boundary_count))
        self._preview_field_bundle_count = int(len(boundary_bundles))
        self.append_debug("3D source envelope: no through-going boundary rays found; showing clipped launch boundary.")
        return True

    def _trace_world_cone_rays(self, system, rays, wavelength: float, pupil_radius: float) -> bool:
        """Trace the 3D launch cone (revolved meridional fan) for Open 3D."""
        boundary_bundles, boundary_count = self._build_world_cone_bundles(pupil_radius, system=system)
        if not boundary_bundles:
            return False
        if self._trace_selected_through_envelope(system, rays, wavelength, boundary_bundles):
            return True

        sparse_bundles, _sparse_count = self._build_world_sparse_pupil_bundles(pupil_radius, system=system)
        if sparse_bundles and self._trace_selected_through_envelope(system, rays, wavelength, sparse_bundles):
            return True

        rays.clean()
        self._trace_preview_bundles(system, rays, wavelength, boundary_bundles)
        self._preview_field_ray_count = max(1, int(boundary_count))
        self._preview_field_bundle_count = int(len(boundary_bundles))
        self.append_debug("3D source cone: no through-going boundary rays found; showing clipped launch cone.")
        return True

    def _trace_selected_through_envelope(self, system, rays, wavelength: float, bundles: list[tuple[np.ndarray, ...]]) -> bool:
        rays.clean()
        self._trace_preview_bundles(system, rays, wavelength, bundles)
        total_launches = 0
        max_group_count = 0
        for bundle in bundles:
            try:
                group_count = len(np.asarray(bundle[0], dtype=float).reshape(-1))
            except Exception:
                group_count = 0
            total_launches += int(max(group_count, 0))
            max_group_count = max(max_group_count, int(max(group_count, 0)))
        if _raykeeper_has_non_primary_branch_paths(rays, expected_launch_count=total_launches):
            self._preview_field_ray_count = max(1, int(max_group_count))
            self._preview_field_bundle_count = int(len(bundles))
            try:
                raw_paths = getattr(rays, "CC", [])
                traced_count = len(raw_paths) if raw_paths is not None else 0
            except Exception:
                traced_count = 0
            self.append_debug(
                "3D source envelope: splitter/branch paths detected; "
                f"kept full {total_launches}-ray launch bundle ({traced_count} displayed branch paths)."
            )
            return True
        final_surface = max(0, len(self.rows) - 1)
        surfaces = [np.asarray(seq, dtype=int).ravel() for seq in getattr(rays, "SURFACE", ())]
        through_total = 0
        for surface_ids in surfaces:
            if surface_ids.size and int(surface_ids[-1]) == final_surface:
                through_total += 1

        if through_total <= 0:
            rays.clean()
            return False

        self._preview_field_ray_count = max(1, int(max_group_count))
        self._preview_field_bundle_count = int(len(bundles))
        self.append_debug(
            f"3D source envelope: kept full {total_launches}-ray launch bundle "
            f"({through_total} through-going paths)."
        )
        return True

    def _full_pupil_grid_xy(self, half_extent: float, max_n: int | None = None):
        """N×N square grid in [-half_extent, +half_extent], where N = ray_count.

        ``max_n`` caps the per-axis grid size. Useful when each grid sample
        carries its own ray bundle (Infinity field axis: each field gets a
        full pupil bundle, so N² × pupil_samp can balloon at large ray_count).
        """
        n = max(1, self._current_ray_count())
        if max_n is not None:
            n = min(n, int(max_n))
        if n == 1:
            return np.array([0.0]), np.array([0.0])
        coords = np.linspace(-half_extent, half_extent, n)
        xx, yy = np.meshgrid(coords, coords, indexing="xy")
        return xx.flatten(), yy.flatten()

    def _build_grid_parallel_bundle(self, pupil_radius: float):
        """N×N grid of parallel rays from the object plane, all going +Z.

        Grid extent = entrance pupil radius if PupilCalc resolved one, else
        the first surface's half-diameter, else 1 mm.
        """
        radius = float(pupil_radius) if np.isfinite(pupil_radius) else 0.0
        if radius <= 1e-9 and self.rows:
            try:
                radius = max(float(self.rows[0].diameter) * 0.5, 0.0)
            except Exception:
                radius = 0.0
        if radius <= 1e-9:
            radius = 1.0
        x_values, y_values = self._full_pupil_grid_xy(radius)
        n_pts = len(x_values)
        if n_pts == 0:
            return None
        z_values = np.zeros(n_pts, dtype=float)
        l_values = np.zeros(n_pts, dtype=float)
        m_values = np.zeros(n_pts, dtype=float)
        n_values = np.ones(n_pts, dtype=float)
        return (x_values, y_values, z_values, l_values, m_values, n_values)

    def _note_pupil_launch_fallback(self, exc: Exception) -> None:
        """bugs/0094: surface (don't silently swallow) a PupilCalc failure on the
        first-order reference -- the launch then falls back to a coarse geometric aim."""
        try:
            self.append_debug(
                f"[pupil] reference launch failed, geometric fallback: {repr(exc)[:200]}\n"
            )
        except Exception:
            pass

    def _imaging_branch_leaves(self) -> dict:
        """DESIGN §5b: ``{branch_selector: leaf rows}`` for each IMAGING beam-splitter arm
        -- an arm tagged ``advanced.Element.branch_selector`` that carries its OWN stop
        (hence its own entrance pupil). Empty unless the layout has >= 2 such arms, which
        is what gates the per-branch launch so ordinary single-axis scenes are untouched.
        """
        try:
            from KrakenOS.UI.services.paraxial_tools import _scene_branch_selectors, _branch_leaf_rows
        except Exception:
            return {}
        rows = list(getattr(self, "rows", None) or [])
        leaves: dict = {}
        for selector in _scene_branch_selectors(rows):
            leaf = _branch_leaf_rows(rows, selector)
            if any(str(getattr(r, "surface", "") or "") == "Aperture" for r in leaf):
                leaves[selector] = leaf
        return leaves

    def _trace_per_branch_bundles(self, system, rays, wavelength: float, pupil_radius: float) -> bool:
        """DESIGN §5b per-branch launch. A beam splitter with > 1 IMAGING arm gives each
        arm its OWN entrance pupil, so a single launch sprays (it cannot even build the
        whole-layout reference -- the folded reflect arm makes it throw). Build a finite
        grid bundle PER arm, aimed at THAT arm's pupil (its leaf reference), and trace them
        together so each arm focuses on its own detector. Returns True when it launched
        (the caller then returns), False for non-two-arm scenes (fall through to the
        ordinary single-launch path).
        """
        leaves = self._imaging_branch_leaves()
        if len(leaves) < 2:
            return False
        all_bundles: list = []
        for _selector, leaf_rows in leaves.items():
            try:
                arm_bundles = self._build_grid_finite_object_bundles(
                    system, wavelength, pupil_radius, pupil_leaf_rows=leaf_rows
                )
            except Exception as exc:  # noqa: BLE001
                self._note_pupil_launch_fallback(exc)
                arm_bundles = []
            all_bundles.extend(arm_bundles)
        if not all_bundles:
            return False
        rays.clean()
        self._trace_preview_bundles(system, rays, wavelength, all_bundles)
        self._preview_field_ray_count = max((int(len(np.asarray(b[0]))) for b in all_bundles), default=0)
        self._preview_field_bundle_count = len(all_bundles)
        return True

    def _build_grid_angular_bundles(self, system, wavelength: float, pupil_radius: float):
        """Filled pupil bundles for infinity-object preview.

        Each field sample is represented by a parallel bundle spanning the
        entrance pupil. This avoids drawing artificial pre-focus cones before
        the first surface for on-axis collimated beams.
        """
        # bugs/0094: aim off the transmissive first-order reference (not the live system),
        # which the sequential PupilCalc cannot trace through a beam splitter / mesh solid.
        pupil_system, _pupil_rows, pupil_index = self._pupil_model_inputs(system, build_reference=True)
        try:
            pupil = Kos.PupilCalc(
                pupil_system,
                pupil_index,
                float(wavelength),
                self._current_aperture_type(),
                self._current_aperture_value(),
            )
            pupil.Ptype = self._current_analysis_pupil_pattern()
            # bugs/0095: "Ray Fan count = N" is a literal per-field ray count, not
            # a per-axis Samp -- invert Samp for the pattern so the display bundle
            # draws N rays per field (a Meridional fan of N), not ~50.
            pupil.Samp = kraken_pattern_samp_for_count(pupil.Ptype, self._current_ray_count())
            pupil.FieldType = "angle"
            bundles = []
            for field_x, field_y in self._sample_field_grid_pairs(self._current_field_angle_deg()):
                pupil.FieldX = float(field_x)
                pupil.FieldY = float(field_y)
                bundle = self._pupil_pattern_bundle(pupil)
                if bundle and len(np.asarray(bundle[0])) > 0:
                    bundle = self._center_infinity_bundle_on_launch_reference(bundle, system=system)
                    bundles.append(bundle)
            if bundles:
                return bundles
        except Exception as exc:
            self._note_pupil_launch_fallback(exc)

        radius = float(pupil_radius) if np.isfinite(pupil_radius) else 0.0
        if radius <= 1e-9 and self.rows:
            try:
                radius = max(float(self.rows[0].diameter) * 0.5, 0.0)
            except Exception:
                radius = 0.0
        if radius <= 1e-9:
            radius = 1.0
        disk_pts = self._sample_pupil_disk(radius)
        bundles = []
        for field_x, field_y in self._sample_field_grid_pairs(self._current_field_angle_deg()):
            tan_x = np.tan(np.deg2rad(float(field_x)))
            tan_y = np.tan(np.deg2rad(float(field_y)))
            direction = np.array([tan_x, tan_y, 1.0], dtype=float)
            norm = np.linalg.norm(direction)
            if norm <= 1e-12:
                continue
            direction /= norm
            n_pts = len(disk_pts)
            bundle = (
                np.asarray(disk_pts[:, 0], dtype=float),
                np.asarray(disk_pts[:, 1], dtype=float),
                np.zeros(n_pts, dtype=float),
                np.full(n_pts, float(direction[0]), dtype=float),
                np.full(n_pts, float(direction[1]), dtype=float),
                np.full(n_pts, float(direction[2]), dtype=float),
            )
            bundle = self._center_infinity_bundle_on_launch_reference(bundle, system=system)
            bundles.append(bundle)
        return bundles

    def _build_grid_finite_object_bundles(self, system, wavelength: float, pupil_radius: float, *, pupil_leaf_rows=None):
        """Filled pupil bundles for finite-object full-pupil preview.

        ``pupil_leaf_rows`` (DESIGN §5b, per-branch launch): aim at ONE beam-splitter
        arm's entrance pupil -- the leaf's own reference -- instead of the whole layout's.
        A two-arm scene's whole-layout reference cannot be built (the folded reflect arm),
        so a single launch sprays; each arm's leaf reference builds cleanly and aims that
        arm's bundle at its own pupil.
        """
        # bugs/0094: aim the source off the transmissive FIRST-ORDER REFERENCE, not the
        # live system -- the sequential PupilCalc cannot trace a beam splitter / mesh
        # solid (it branches and throws, after which the geometric fallback aimed the beam
        # at the cube). The reference also recomputes the stop index, fixing the in-path-
        # promotion row shift.
        pupil_system, _pupil_rows, pupil_index = self._pupil_model_inputs(
            system, build_reference=True, rows=pupil_leaf_rows
        )
        try:
            pupil = Kos.PupilCalc(
                pupil_system,
                pupil_index,
                float(wavelength),
                self._current_aperture_type(),
                self._current_aperture_value(),
            )
            pupil.Ptype = self._current_analysis_pupil_pattern()
            # bugs/0095: "Ray Fan count = N" is a literal per-field ray count, not
            # a per-axis Samp -- invert Samp for the pattern so the display bundle
            # draws N rays per field (a Meridional fan of N), not ~50.
            pupil.Samp = kraken_pattern_samp_for_count(pupil.Ptype, self._current_ray_count())
            pupil.FieldType = "height"
            bundles = []
            for field_x, field_y in self._sample_field_grid_pairs(self._launch_field_radial_max()):
                pupil.FieldX = float(field_x)
                pupil.FieldY = float(field_y)
                bundle = self._pupil_pattern_bundle(pupil)
                if bundle and len(np.asarray(bundle[0])) > 0:
                    bundles.append(bundle)
            if bundles:
                return bundles
        except Exception as exc:
            self._note_pupil_launch_fallback(exc)

        radius = float(pupil_radius) if np.isfinite(pupil_radius) else 0.0
        if radius <= 1e-9:
            radius = 1.0
        disk_pts = self._sample_pupil_disk(radius)
        object_distance = self._current_object_distance()
        bundles = []
        for field_x, field_y in self._sample_field_grid_pairs(self._launch_field_radial_max()):
            origin = np.array([-float(field_x), -float(field_y), 0.0], dtype=float)
            x_vals: list[float] = []
            y_vals: list[float] = []
            z_vals: list[float] = []
            l_vals: list[float] = []
            m_vals: list[float] = []
            n_vals: list[float] = []
            for pupil_x, pupil_y in disk_pts:
                target = np.array([float(pupil_x), float(pupil_y), object_distance], dtype=float)
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
                bundles.append(
                    (
                        np.asarray(x_vals, dtype=float),
                        np.asarray(y_vals, dtype=float),
                        np.asarray(z_vals, dtype=float),
                        np.asarray(l_vals, dtype=float),
                        np.asarray(m_vals, dtype=float),
                        np.asarray(n_vals, dtype=float),
                    )
                )
        return bundles



    def _current_ray_count(self) -> int:
        # bugs/0024: during an interactive placement drag with Live Mode on, the
        # inspector sets a reduced ray count so the live preview traces a sparse
        # fan (snappy feedback) instead of the full bundle. Cleared on release,
        # when the full-fidelity retrace runs.
        # __dict__.get, not getattr(): the editor is a Tk app whose __getattr__
        # recurses on a missing attribute (RecursionError), so getattr() with a
        # default is unsafe here.
        # bugs/0105: the forced post-promote retrace honours the same kind of
        # sparse-fan clamp so promoting a STEP solid (which permanently forces a
        # full branched retrace on every refresh) lands fast instead of stalling
        # ~90s on a beam-splitter scene. Cleared after the promote retrace, so
        # the next explicit trace restores full ray density.
        override = self.__dict__.get("_promote_preview_ray_count_override")
        if override is None:
            override = self.__dict__.get("_drag_preview_ray_count_override")
        if override is not None:
            try:
                return max(1, int(override))
            except (TypeError, ValueError):
                pass
        try:
            return max(1, int(self.ray_count_var.get()))
        except ValueError:
            return 5

    def _current_source_model(self) -> str:
        source_model_var = self.__dict__.get("source_model_var")
        value = str(source_model_var.get()).strip() if source_model_var is not None else SOURCE_MODEL_DEFAULT
        return value if value in SOURCE_MODEL_VALUES else SOURCE_MODEL_DEFAULT

    def _current_pupil_pattern_label(self) -> str:
        pupil_pattern_var = self.__dict__.get("pupil_pattern_var")
        value = str(pupil_pattern_var.get()).strip() if pupil_pattern_var is not None else PUPIL_PATTERN_DEFAULT
        return value if value in PUPIL_PATTERN_VALUES else PUPIL_PATTERN_DEFAULT

    def _current_kraken_pupil_pattern(self) -> str | None:
        return PUPIL_PATTERN_TO_KRAKEN.get(self._current_pupil_pattern_label())

    def _current_analysis_pupil_pattern(self, fallback: str = "hexapolar") -> str:
        return self._current_kraken_pupil_pattern() or fallback

    def _current_source_radius(self) -> float:
        source_radius_var = self.__dict__.get("source_radius_var")
        try:
            value = float(source_radius_var.get()) if source_radius_var is not None else 5.0
        except Exception:
            value = 5.0
        return max(float(value), 0.0)

    def _current_source_cone_angle(self) -> float:
        source_cone_angle_var = self.__dict__.get("source_cone_angle_var")
        try:
            value = float(source_cone_angle_var.get()) if source_cone_angle_var is not None else 0.0
        except Exception:
            value = 0.0
        return max(min(float(value), 89.9), 0.0)

    def _current_gaussian_input_mode(self) -> str:
        var = self.__dict__.get("gaussian_input_mode_var")
        value = str(var.get()).strip() if var is not None else GAUSSIAN_INPUT_MODE_DEFAULT
        return value if value in GAUSSIAN_INPUT_MODE_VALUES else GAUSSIAN_INPUT_MODE_DEFAULT
