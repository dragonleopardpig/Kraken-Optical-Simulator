from __future__ import annotations

import math
import sys

import numpy as np


_PROTECTED_GLOBALS = {
    "LayoutSceneBundleDisplayMixin",
    "_PROTECTED_GLOBALS",
    "_sync_layout_globals",
}

# bugs/0238: a kind="image" surface curve this far (mm) from every folded detector
# target is a STALE unfolded duplicate and is dropped (the "two image planes" fix).
_SUPERSEDED_IMAGE_CURVE_TOL_MM = 1.0

# bugs/0239: a detector target whose in-plane radius (hypot X,Y) exceeds this is FOLDED off
# the straight +Z axis -- the gate for re-seating the kind="image" surface MESH disc onto it.
_FOLDED_DETECTOR_OFF_AXIS_MM = 5.0


def _sync_layout_globals(source: dict[str, object]) -> None:
    target = globals()
    for name, value in source.items():
        if name.startswith("__") or name in _PROTECTED_GLOBALS:
            continue
        target[name] = value


def _current_pv_backend():
    value = globals().get("pv")
    if value is not None:
        return value
    layout_module = sys.modules.get("KrakenOS.UI.layout_editor")
    value = getattr(layout_module, "pv", None) if layout_module is not None else None
    if value is not None:
        globals()["pv"] = value
    return value


def _is_blocked_reference_ray_stub(path) -> bool:
    """A pupil/field reference ray blocked before it ever entered the optics.

    True only for a ``pupil_field_reference`` path that stopped at the first
    surface (``stopped_at_surface_0``), carries no branch power and reaches no
    image -- pure sampling scaffolding that never propagated. These are the
    stubs a promoted-mirror fold strands on the +Z axis (bugs/0189). A real
    launched ray (``missed_image`` or any that reaches the detector) is never a
    match, so the folded imaging cone is untouched.
    """
    if str(getattr(path, "source_role", "") or "") != "pupil_field_reference":
        return False
    if str(getattr(path, "termination_reason", "") or "") != "stopped_at_surface_0":
        return False
    if bool(getattr(path, "reaches_image", False)):
        return False
    power = getattr(path, "branch_power", None)
    if power is not None:
        try:
            if abs(float(power)) > 1e-9:
                return False
        except (TypeError, ValueError):
            return False
    return True


# bugs/0191: a folded ray that RETROREFLECTS at an ideal Thin Lens reverses its
# propagation ~180 deg. Measured on the AZ85 bundle the per-vertex turn is cleanly
# bimodal: the 53 retroreflections all fall at cos(turn) in [-1.0, -0.9], then a HARD
# empty gap [-0.9, -0.6], then every legitimate fold/refraction turn (the steepest is
# the ~90-120 deg mirror fold for a marginal FIELD ray) sits at cos >= -0.6. -0.75 is
# the middle of that gap, so it isolates the retroreflection with ~0.15 margin either
# way and never trips the mirror fold itself (which turns the imaging cone forward).
_FOLDED_RETROREFLECTED_TAIL_COS_MAX = -0.75


def _folded_retroreflected_tail_points(points, cos_max: float = _FOLDED_RETROREFLECTED_TAIL_COS_MAX):
    """Points truncated at the first ~180 deg propagation reversal, or None if none.

    Walks the display polyline; at the first vertex whose incoming vs outgoing unit
    direction dot is below ``cos_max`` (a retroreflection, not a fold/refraction) it
    keeps every point up to and INCLUDING that vertex (the ray stops at the lens where
    it turned around) and drops the non-physical tail (the double-pass return + the
    dive out the back of the fold hypotenuse). Returns ``None`` -- leave untouched --
    for a forward-only ray or a polyline too short / degenerate to judge.
    """
    try:
        pts = np.asarray(points, dtype=float)
    except (TypeError, ValueError):
        return None
    if pts.ndim != 2 or pts.shape[0] < 3 or pts.shape[1] < 3:
        return None
    segments = np.diff(pts[:, :3], axis=0)
    lengths = np.linalg.norm(segments, axis=1)
    for i in range(1, len(segments)):
        a, b = lengths[i - 1], lengths[i]
        if a <= 1e-9 or b <= 1e-9:
            continue
        if float(np.dot(segments[i - 1] / a, segments[i] / b)) < cos_max:
            return np.array(pts[: i + 1], dtype=float, copy=True)
    return None


class LayoutSceneBundleDisplayMixin:
    def _current_field_value(self) -> float:
        try:
            return float(self.field_value_var.get())
        except ValueError:
            return 0.0

    def _current_field_angle_deg(self) -> float:
        return float(self._field_metrics().get("angle_deg", 0.0))

    def _current_field_height(self) -> float:
        return float(self._field_metrics().get("object_height", 0.0))

    def _field_metrics_for_value(self, field_type: str, raw_value: float) -> dict[str, float]:
        object_distance = self._current_object_distance()
        effl = self._current_effl_estimate()
        image_distance = self._current_image_distance()
        finite_magnification = self._current_finite_paraxial_magnification()

        # bugs/0610: an image-height field (the camera coupling stores "Real Image Height" =
        # the sensor half-diagonal) is converted to an OBJECT height by dividing by the
        # magnification -- so it must divide by what the machine DELIVERS, not by the folded
        # first order's promise. Measured after a PYRITE swap: raw |m| 1.506 put the launched
        # field at 15.30 mm while the sensor needed 19.79, so the trace under-filled the glass
        # by ~18% and no FOV solve could re-frame it (the launcher never saw the new number).
        # This is the SHARED field converter -- every consumer (ray launcher, field samplers,
        # auto image diameter, the panel readout) inherits the fix, and on a sequential scene
        # the correction is 1.0 so nothing moves.
        try:
            from KrakenOS.UI.services.quick_estimation import folded_m_correction

            delivered_correction = float(folded_m_correction(self))
        except Exception:
            delivered_correction = 1.0
        with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
            if finite_magnification is not None:
                mag = max(abs(float(finite_magnification)) * delivered_correction, 1e-9)
                if field_type == "Angle":
                    angle_deg = raw_value
                    object_height = object_distance * np.tan(np.deg2rad(angle_deg))
                elif field_type == "Object Height":
                    object_height = raw_value
                    angle_deg = np.rad2deg(np.arctan2(object_height, object_distance))
                else:
                    object_height = raw_value / mag
                    angle_deg = np.rad2deg(np.arctan2(object_height, object_distance))
                paraxial_image_height = mag * object_height
                real_image_height = paraxial_image_height
            else:
                if field_type == "Angle":
                    angle_deg = raw_value
                    object_height = object_distance * np.tan(np.deg2rad(angle_deg))
                elif field_type == "Object Height":
                    object_height = raw_value
                    angle_deg = np.rad2deg(np.arctan2(object_height, object_distance))
                elif field_type == "Paraxial Image Height":
                    paraxial_image_height = raw_value
                    angle_deg = np.rad2deg(np.arctan2(paraxial_image_height, max(effl, 1e-6)))
                    object_height = object_distance * np.tan(np.deg2rad(angle_deg))
                else:
                    real_image_height = raw_value
                    # bugs/0168: an object-space field angle theta images to EFL*tan(theta)
                    # (the rear-nodal-to-image distance is the EFL), so a given real image
                    # height maps back through the EFL -- NOT the back-focal-distance
                    # ``image_distance`` (which is only the last-surface->image gap and
                    # underreads by EFL/BFD on any thick lens).
                    angle_deg = np.rad2deg(np.arctan2(real_image_height, max(effl, 1e-6)))
                    object_height = object_distance * np.tan(np.deg2rad(angle_deg))

                paraxial_image_height = effl * np.tan(np.deg2rad(angle_deg))
                # The non-tracing estimate of the real chief-ray image height is the
                # paraxial height (EFL*tan); true distortion comes from the traced image
                # diameter, not this quick estimator. Using ``image_distance`` here was the
                # 0168 bug (e.g. a Cooke triplet read 16x too small).
                real_image_height = paraxial_image_height

        if not np.isfinite(angle_deg):
            angle_deg = 0.0
        if not np.isfinite(object_height):
            object_height = 0.0
        if not np.isfinite(paraxial_image_height):
            paraxial_image_height = 0.0
        if not np.isfinite(real_image_height):
            real_image_height = 0.0
        return {
            "angle_deg": float(angle_deg),
            "object_height": float(object_height),
            "paraxial_image_height": float(paraxial_image_height),
            "real_image_height": float(real_image_height),
        }

    def _field_metrics(self) -> dict[str, float]:
        return self._field_metrics_for_value(self._current_field_type(), self._current_field_value())

    def _field_metrics_summary(self) -> dict[str, float]:
        field_type = self._current_field_type()
        sample_values = self._sample_field_values(self._current_field_value())
        if not sample_values:
            sample_values = [self._current_field_value()]
        metrics = [self._field_metrics_for_value(field_type, value) for value in sample_values]
        current_metrics = self._field_metrics()
        max_paraxial = max(abs(float(item.get("paraxial_image_height", 0.0))) for item in metrics) if metrics else 0.0
        max_real = max(abs(float(item.get("real_image_height", 0.0))) for item in metrics) if metrics else 0.0
        traced_image_diameter = self._traced_image_diameter_value()
        field_image_radius = max_paraxial if self._current_object_mode() == "Infinity" else max_real
        required_image_diameter = max(
            2.0 * field_image_radius,
            float(traced_image_diameter) if traced_image_diameter is not None else 0.0,
            1.0,
        )
        return {
            "current_angle_deg": float(current_metrics.get("angle_deg", 0.0)),
            "current_object_height": float(current_metrics.get("object_height", 0.0)),
            "current_paraxial_image_height": float(current_metrics.get("paraxial_image_height", 0.0)),
            "current_real_image_height": float(current_metrics.get("real_image_height", 0.0)),
            "max_paraxial_image_height": float(max_paraxial),
            "max_real_image_height": float(max_real),
            # bugs/0168: the object-mode-aware image radius -- for an INFINITY object
            # the chief-ray image height is EFL*tan(field) (= max_paraxial), NOT
            # image_distance*tan(field) (the back-focal-distance projection that
            # ``max_real`` uses, which underreads by EFL/BFD). The "image circle"
            # overlay must use this so it matches where the rays actually land.
            "field_image_radius": float(field_image_radius),
            "image_diameter": float(required_image_diameter),
        }

    def _current_effl_estimate(self) -> float:
        try:
            effl, _ppa, _ppp = self._exact_paraxial_cardinals(self._current_wavelength())
            return max(abs(float(effl)), 1e-6)
        except Exception:
            pass
        if self.last_system is not None:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", RuntimeWarning)
                    _a, _b, _c, _d, effl, *_rest = self.last_system.EFL(self._current_wavelength())  # type: ignore[misc]
                return max(abs(float(effl)), 1e-6)
            except Exception:
                pass
        return 100.0

    def _current_image_distance(self) -> float:
        if len(self.rows) >= 2:
            try:
                if self._scene_folds_for_paraxial_distance(self.rows):  # bugs/0219: promoted RA mirror too
                    distance, _last_source_index, _reference_rows = self._paraxial_total_image_gap(self.rows)
                else:
                    distance = float(self.rows[-2].thickness)
            except Exception:
                distance = float(self.rows[-2].thickness)
            return max(float(distance), 1e-6)
        return 100.0

    def _current_finite_paraxial_magnification(self) -> float | None:
        if self._current_object_mode() != "Finite" or len(self.rows) < 3:
            return None
        try:
            # The SHARED first-order reference (bugs/0297): a beam splitter / promoted mesh solid
            # (not just a folding mirror) has no clean sequential paraxial form, so the direct
            # conjugate solve throws on it -- the reference straightens it to the transmissive
            # (straight-through) equivalent, keeping a promoted RA-mirror prism as the glass plate
            # it physically is. Without this the conjugate solve returned None and the
            # detector-coverage object-FOV rectangle (the visible "object plane" when the Det
            # overlay is on) vanished after a cube promotion (bugs/0104). The FOV solve reads the
            # SAME reference, so the number this readout shows is the number the solve targets.
            first_order = self._shared_first_order_reference()
            if first_order is None:
                raise RuntimeError("no paraxial reference")
            f = float(first_order["f"])
            object_principal = float(first_order["object_principal"])
            image_principal = float(first_order["image_principal"])
            # bugs/0222: read the magnification at the CONJUGATE (where the object actually images),
            # not at the prescription Image ROW. On the folded RA-mirror scene the trailing mirror
            # pushes the Image row a plate PAST the true focus, so ``image_z - h2_z`` measured the mag at
            # a DEFOCUSED plane and inflated it. The Gaussian conjugate from the rear principal is
            # s_i = f*s_o/(s_o - f) with s_o = object->front-principal distance, so m = s_i/s_o =
            # f/(s_o - f). For an in-focus system the prescription Image row IS the conjugate, so this
            # equals the old value.
            if (
                self._scene_folds_for_paraxial_distance()
                and np.isfinite(object_principal)
                and np.isfinite(f)
                and abs(object_principal - f) > 1e-9
            ):
                return float(f / (object_principal - f))
            if (
                np.isfinite(object_principal)
                and np.isfinite(image_principal)
                and abs(object_principal) > 1e-9
            ):
                return float(image_principal / object_principal)
        except Exception:
            pass
        # Two-arm splitter fold: the single-axis paraxial solve can't handle the folded/branched
        # scene (returns None). Fall back to a fold arm's per-leaf magnification so the
        # quick-estimation / detector-coverage tools show a representative value, not "--".
        try:
            parts = self._two_arm_fold_parts(None)
            if parts is not None:
                for target in (parts[1] or []):
                    mag = (getattr(target, "metadata", None) or {}).get("two_arm_magnification")
                    if mag is not None and np.isfinite(float(mag)):
                        return float(mag)
        except Exception:
            pass
        return None

    def _paraxial_image_plane_z(self) -> float | None:
        """The axial z where the optics actually form the image (paraxial best focus), in the same
        cumulative-z frame as the rows. This is the "image plane" the detector defocuses against --
        a ROBUST Gaussian-conjugate value (no exit-pupil trap, unlike the ray-RMS focus diagnostic
        which lands on the exit pupil for multi-field bundles). Returns None when not computable
        (mirror/branched layouts -> caller falls back to the prescription Image z)."""
        if len(self.rows) < 3:
            return None
        if any(getattr(row, "surface", "") == "Mirror" for row in self.rows):
            return None  # folded/catadioptric: principal-plane conjugate not handled here
        equivalent = self._folded_optical_solid_straight_equivalent_rows()
        if equivalent is not None:
            # bugs/0194: a promoted mesh mirror folds the axis 90deg; its placement decenter
            # trips the centered-refractive guard below. Folding is rigid, so solve the unfolded
            # flat-plate equivalent (same cumulative-z frame -> the returned image_z is directly
            # the detector-frame best focus).
            return self._with_rows_swapped(equivalent, self._paraxial_image_plane_z)
        try:
            _a, _b, _c, _d, effl, ppa, ppp = self._exact_paraxial_solution_for_rows(self.rows)
            h1_vertex_z, h2_vertex_z = self._paraxial_vertex_zs(self.rows)
            h1_z = float(h1_vertex_z) + float(ppa)   # front principal plane z
            h2_z = float(h2_vertex_z) + float(ppp)   # rear principal plane z
            f = float(effl)
            if not np.isfinite(f) or abs(f) <= 1e-9:
                return None
            if self._current_object_mode() == "Infinity":
                image_z = h2_z + f
            else:
                # Object row at z=0 -> object distance from the front principal is h1_z (positive).
                # Gaussian conjugate from the rear principal: 1/s_i = 1/f - 1/s_o.
                s_o = h1_z
                if abs(s_o) <= 1e-9:
                    return None
                denom = (1.0 / f) - (1.0 / s_o)
                if abs(denom) <= 1e-12:
                    return None  # object at front focal point -> image at infinity
                image_z = h2_z + (1.0 / denom)
            return float(image_z) if np.isfinite(image_z) else None
        except Exception:
            return None

    def _schedule_refresh_plot(self, *_args) -> None:
        if not self.winfo_exists():
            return
        if hasattr(self, "_refresh_after_id") and self._refresh_after_id is not None:
            self.after_cancel(self._refresh_after_id)
        self._refresh_after_id = self.after(120, self._refresh_plot_from_controls)

    def _refresh_plot_from_controls(self) -> None:
        self._refresh_after_id = None
        if self.optimization_running:
            return
        self.refresh_plot()

    # _style_embedded_plot removed — now in scene_renderer_2d._style_surface_lines

    def _field_colors(self, count: int) -> list[str]:
        if count <= 1:
            return ["#39FF14"]
        cmap = [
            "#39FF14",
            "#00E5FF",
            "#FF9F1C",
            "#FF4D6D",
            "#9B5DE5",
            "#FFD166",
            "#2EC4B6",
            "#E71D36",
        ]
        return [cmap[i % len(cmap)] for i in range(count)]

    # _build_world_ray_paths, _build_display_ray_paths, _render_display_surface_paths
    # removed — now in scene_builder and scene_renderer_2d

    def _current_folded_surface_geometry(
        self,
        *,
        system=None,
    ) -> tuple[np.ndarray, np.ndarray, float, list[np.ndarray], list[tuple[str, np.ndarray, SurfaceRow, np.ndarray]]] | None:
        trace_state = self._resolved_trace_mode(system=system)
        if not bool(trace_state.get("use_folded")) or not self.rows:
            return None
        return self._compute_folded_layout_geometry()

    @staticmethod
    def _select_optical_solid_output_face(world_faces: list[dict[str, object]]) -> dict[str, object] | None:
        return select_optical_solid_output_face(world_faces)

    def _optical_solid_image_plane_overrides(self, *, system=None) -> dict[int, tuple[np.ndarray, np.ndarray]]:
        overrides: dict[int, tuple[np.ndarray, np.ndarray]] = {}
        if len(self.rows) < 2:
            return overrides
        if system is not None:
            pose_overrides = optical_solid_output_port_pose_overrides(system, self.rows)
        else:
            pose_overrides = build_optical_solid_output_port_pose_overrides(self.rows)
        for row_index, row in enumerate(self.rows):
            if row.surface != "Image":
                continue
            pose = pose_overrides.get(row_index)
            if not isinstance(pose, dict):
                continue
            center_world = np.asarray(pose.get("center", (np.nan, np.nan, np.nan)), dtype=float).reshape(-1)
            normal_world = np.asarray(pose.get("normal", (np.nan, np.nan, np.nan)), dtype=float).reshape(-1)
            if center_world.size < 3 or normal_world.size < 3:
                continue
            if not (np.all(np.isfinite(center_world[:3])) and np.all(np.isfinite(normal_world[:3]))):
                continue
            x0, y0 = self._project_xy([float(center_world[2])], [float(center_world[1])])
            x1, y1 = self._project_xy(
                [float(center_world[2] + normal_world[2])],
                [float(center_world[1] + normal_world[1])],
            )
            center = np.asarray((float(x0[0]), float(y0[0])), dtype=float)
            along = np.asarray((float(x1[0] - x0[0]), float(y1[0] - y0[0])), dtype=float)
            along_norm = float(np.linalg.norm(along))
            if along_norm <= 1e-12:
                along = np.asarray((0.0, 1.0), dtype=float)
                along_norm = 1.0
            overrides[row_index] = (center, along / max(along_norm, 1e-12))
        return overrides

    def _reference_plane_overrides(self, *, system=None) -> dict[int, tuple[np.ndarray, np.ndarray]]:
        trace_state = self._resolved_trace_mode(system=system)
        if bool(trace_state.get("use_folded")):
            return self._folded_plane_overrides()
        optical_solid_overrides = self._optical_solid_image_plane_overrides(system=system) if bool(trace_state.get("use_nonseq")) else {}
        if system is not None and self._has_off_axis_geometry():
            overrides = self._transform_reference_plane_overrides(system)
            if bool(trace_state.get("use_nonseq")):
                # KrakenOS TRANS_2A can place Object/Image reference rows at
                # internal solver stations for non-sequential scenes (notably
                # STL optical solids). The UI table still defines those
                # reference planes by row semantics instead. Preserve
                # transform-based aperture orientation only, and let Image use
                # the optical-solid output port pose when available.
                for row_index, row in enumerate(self.rows):
                    if row.surface in {"Object", "Image"}:
                        overrides.pop(row_index, None)
                overrides.update(optical_solid_overrides)
            if overrides:
                return overrides
        if optical_solid_overrides:
            return optical_solid_overrides
        return {}

    def _transform_reference_plane_overrides(self, system) -> dict[int, tuple[np.ndarray, np.ndarray]]:
        transforms = self._system_transform_list(system)
        if transforms is None:
            return {}
        overrides: dict[int, tuple[np.ndarray, np.ndarray]] = {}
        for row_index, row in enumerate(self.rows):
            if row.surface not in {"Object", "Image", "Aperture"} or row_index >= len(transforms):
                continue
            try:
                transform = np.asarray(transforms[row_index], dtype=float)
                center_z = float(transform[2, 3])
                center_y = float(transform[1, 3])
                axis_z = float(transform[2, 2])
                axis_y = float(transform[1, 2])
                axis_norm = float(np.hypot(axis_z, axis_y))
                if axis_norm <= 1e-12:
                    continue
                x0, y0 = self._project_xy([center_z], [center_y])
                x1, y1 = self._project_xy([center_z + axis_z / axis_norm], [center_y + axis_y / axis_norm])
                center = np.array([float(x0[0]), float(y0[0])], dtype=float)
                along = np.array([float(x1[0] - x0[0]), float(y1[0] - y0[0])], dtype=float)
                along_norm = float(np.linalg.norm(along))
                if along_norm <= 1e-12:
                    continue
                overrides[row_index] = (center, along / along_norm)
            except Exception:
                continue
        return overrides

    # _reference_plane_display_points, _build_reference_plane_surface_paths
    # removed — now in scene_builder

    @staticmethod
    def _unit_display_vector(vector, fallback: np.ndarray | None = None) -> np.ndarray:
        try:
            arr = np.asarray(vector, dtype=float).ravel()
        except Exception:
            arr = np.empty(0, dtype=float)
        if arr.size >= 2 and np.all(np.isfinite(arr[:2])):
            candidate = np.asarray(arr[:2], dtype=float)
        elif fallback is not None:
            candidate = np.asarray(fallback, dtype=float).ravel()[:2]
        else:
            candidate = np.asarray((1.0, 0.0), dtype=float)
        norm = float(np.linalg.norm(candidate))
        if norm <= 1e-12:
            candidate = np.asarray((1.0, 0.0), dtype=float)
            norm = 1.0
        return candidate / norm

    def _source_display_frame(self) -> tuple[np.ndarray, np.ndarray, float]:
        try:
            source_x, source_y, source_z = self._current_source_origin()
            del source_x
        except Exception:
            source_y, source_z = 0.0, 0.0
        x_vals, y_vals = self._project_xy([source_z], [source_y])
        center = np.asarray((float(x_vals[0]), float(y_vals[0])), dtype=float)
        try:
            _source_l, source_m, source_n = self._current_source_direction()
        except Exception:
            source_m, source_n = 0.0, 1.0
        axis_x, axis_y = self._project_xy([source_n], [source_m])
        axis = np.asarray((float(axis_x[0]), float(axis_y[0])), dtype=float)
        axis = self._unit_display_vector(axis, np.asarray((1.0, 0.0), dtype=float))
        tangent = self._unit_display_vector(np.asarray((-axis[1], axis[0]), dtype=float), np.asarray((0.0, 1.0)))
        source_radius = self._current_source_radius()
        if getattr(self, "rows", None):
            try:
                source_radius = max(source_radius, 0.5 * abs(float(self.rows[0].diameter)))
            except Exception:
                pass
        return center, tangent, float(max(source_radius, 0.0))

    def _branch_output_display_targets(self) -> dict[str, np.ndarray]:
        targets: dict[str, np.ndarray] = {}
        for row in getattr(self, "rows", []) or []:
            advanced = getattr(row, "advanced", {}) or {}
            if not isinstance(advanced, dict):
                continue
            display_settings = advanced.get("Display2D", {})
            if not isinstance(display_settings, dict):
                continue
            raw_targets = display_settings.get("branch_output_targets")
            if not isinstance(raw_targets, dict):
                continue
            for raw_code, raw_point in raw_targets.items():
                code = str(raw_code or "").strip().upper()
                if not code:
                    continue
                try:
                    point = np.asarray(raw_point, dtype=float).ravel()
                except Exception:
                    continue
                if point.size < 2 or not np.all(np.isfinite(point[:2])):
                    continue
                targets[code] = np.asarray(point[:2], dtype=float)
        return targets

    def _branch_output_display_target_frames(self) -> dict[str, tuple[np.ndarray, np.ndarray, float]]:
        source_center, source_tangent, source_radius = self._source_display_frame()
        frames: dict[str, tuple[np.ndarray, np.ndarray, float]] = {}
        for row in getattr(self, "rows", []) or []:
            advanced = getattr(row, "advanced", {}) or {}
            if not isinstance(advanced, dict):
                continue
            display_settings = advanced.get("Display2D", {})
            if not isinstance(display_settings, dict):
                continue
            raw_targets = display_settings.get("branch_output_targets")
            if not isinstance(raw_targets, dict):
                continue
            try:
                row_radius = 0.5 * abs(float(row.diameter))
            except Exception:
                row_radius = 0.0
            raw_tangent = display_settings.get("plane_tangent")
            for raw_code, raw_point in raw_targets.items():
                code = str(raw_code or "").strip().upper()
                if not code:
                    continue
                try:
                    point = np.asarray(raw_point, dtype=float).ravel()
                except Exception:
                    continue
                if point.size < 2 or not np.all(np.isfinite(point[:2])):
                    continue
                target = np.asarray(point[:2], dtype=float)
                if code in {"TT", "RR"}:
                    frames[code] = (target, source_tangent, source_radius)
                    continue
                fallback_axis = target - source_center
                fallback_tangent = np.asarray((-fallback_axis[1], fallback_axis[0]), dtype=float)
                tangent = self._unit_display_vector(raw_tangent, fallback_tangent)
                frames[code] = (target, tangent, max(row_radius, source_radius))
        return frames

    def _branch_output_display_path_overrides(self, rays) -> list[np.ndarray] | None:
        target_frames = self._branch_output_display_target_frames()
        if not target_frames or rays is None:
            return None
        source_center, source_tangent, _source_radius = self._source_display_frame()
        overrides: list[np.ndarray] = []
        used_override = False
        ray_paths = getattr(rays, "CC", ())
        if ray_paths is None:
            return None
        for ray_index, ray in enumerate(ray_paths):
            points_world = np.asarray(ray, dtype=float)
            if points_world.ndim != 2 or points_world.shape[0] < 2 or points_world.shape[1] < 3:
                overrides.append(np.empty((0, 2), dtype=float))
                continue
            x_vals, y_vals = self._project_xy(points_world[:, 2], points_world[:, 1])
            points_2d = np.column_stack((x_vals, y_vals)).astype(float)
            branch_path = str(self._raykeeper_value(rays, "BRANCH_PATH", ray_index, "") or "")
            code = "".join(self._branch_path_selector_sequence(branch_path))[-2:]
            target_frame = target_frames.get(code)
            if target_frame is not None and points_2d.shape[0] >= 2:
                target, target_tangent, max_offset = target_frame
                source_offset = float(np.dot(points_2d[0] - source_center, source_tangent))
                if abs(source_offset) <= 1e-12:
                    raw_offset = float(np.dot(points_2d[-1] - target, target_tangent))
                    if np.isfinite(raw_offset):
                        source_offset = raw_offset
                if np.isfinite(max_offset) and max_offset > 1e-9:
                    source_offset = float(np.clip(source_offset, -max_offset, max_offset))
                points_2d = np.asarray(points_2d, dtype=float).copy()
                points_2d[-1] = target + target_tangent * source_offset
                used_override = True
            overrides.append(points_2d)
        return overrides if used_override else None

    def _build_scene_bundle(self, system, rays, max_radius: float) -> SceneBundle:
        """Build a SceneBundle using the new Phase 3 pipeline."""
        orientation = self._current_display_orientation()
        trace_state = self._resolved_trace_mode(system=system)
        trace_note = str(trace_state.get("note", ""))
        trace_runtime_note = str(getattr(self, "_last_preview_trace_note", "") or "").strip()
        if trace_runtime_note:
            trace_note = f"{trace_note} {trace_runtime_note}".strip()
        folded_geometry = self._current_folded_surface_geometry(system=system)
        # Two-arm splitter scenes use the DISPLAY-FOLD architecture: each imaging arm is traced
        # straight + sequential (optics always correct) and the bent arm's rays + detector are
        # folded in (services/two_arm_display_fold.py). When active, override ray_paths/targets
        # below and let the 2D pane project the already-folded ray paths.
        two_arm_parts = self._two_arm_fold_parts(system)

        # Compute folded ray display overrides (pre-projected paths for folded layouts)
        folded_ray_display_paths = None
        folded_elements = None
        if folded_geometry is not None:
            _point, _direction, _mh, _ep, folded_elements = folded_geometry
            folded_ray_display_paths = self._display_path_overrides_for_current_layout(
                rays, max_radius,
                folded_elements=folded_elements,
                folded_orientation=orientation,
                system=system,
            )
        elif bool(trace_state.get("use_folded")) and orientation == "YZ":
            folded_ray_display_paths = self._display_path_overrides_for_current_layout(
                rays, max_radius,
                system=system,
            )
        if folded_ray_display_paths is None and not bool(trace_state.get("use_nonseq")):
            folded_ray_display_paths = self._branch_output_display_path_overrides(rays)
        if two_arm_parts is not None:
            folded_ray_display_paths = None  # 2D projects the already-folded ray_paths

        field_count = max(
            1,
            int(getattr(self, "_preview_field_bundle_count", self._current_field_count())),
        )

        bundle = build_scene_bundle(
            rows=self.rows,
            system=system,
            rays=rays,
            sources=self._collect_scene_sources(wavelength=self._current_wavelength()),
            display_orientation=orientation,
            show_clipped_rays=self.show_clipped_rays_var.get(),
            field_count=field_count,
            ray_count_per_field=max(1, self._preview_field_ray_count),
            field_colors=self._field_colors(field_count),
            # bugs/0558: hand the builder the field identity the LAUNCH recorded, so ray colour
            # cannot disagree with the trace that produced the rays.
            field_index_by_source_ray=getattr(self, "_preview_field_index_by_source_ray", None),
            folded_geometry=folded_geometry,
            row_polylines_fn=self._row_layout_polylines,
            surface_meshes_fn=(
                (lambda current_system: self._iter_3d_surface_meshes(current_system, include_reference_surfaces=True))
                if _current_pv_backend() is not None
                else None
            ),
            project_fn=self._project_xy,
            reference_plane_overrides=self._reference_plane_overrides(system=system),
            folded_ray_display_paths=folded_ray_display_paths,
            folded_terminal_policy=self._current_folded_detector_policy(),
            trace_mode_requested=str(trace_state.get("requested", "Auto")),
            trace_mode_active=str(trace_state.get("active", "Sequential")),
            trace_mode_note=trace_note,
            target_surface=(
                self._current_nonseq_target_surface_index()
                if bool(trace_state.get("use_nonseq"))
                else None
            ),
            detector_surface_indices=self._scene_detector_surface_indices(trace_state),
            detector_active_dims_overrides=self._camera_detector_active_dims_overrides(),
            allow_target_plane_contact=True,
            source_row_order=normalize_source_row_order(getattr(self, "layout_scene_row_order", SOURCE_ROW_ORDER_DEFAULT)),
            branch_camera_sensors=self._branch_detector_camera_sensors(),
        )
        if two_arm_parts is not None:
            fold_paths, fold_targets = two_arm_parts
            bundle.ray_paths = fold_paths
            bundle.targets = [t for t in bundle.targets if not getattr(t, "is_detector", False)] + fold_targets
            # The scene authored per-arm Detector surfaces (+ a global Image) at the PRESCRIPTION
            # focus; the fold detectors now sit at the PHYSICAL focus (ray convergence) and
            # supersede them. Drop the superseded terminal-plane curves so only ONE image plane
            # shows per arm -- the user's "two image planes" (prescription 595.8 + physics 615.1)
            # collapse to one at the physics focus.
            def _is_superseded_terminal(curve) -> bool:
                # ANY image-plane curve is superseded by the fold detectors. The scene draws the
                # global/prescription image as a kind="image" curve with row_index=-1 (no glass
                # correction -> it sits at the WRONG focus, the user's "image plane in front
                # without the 50mm cube correction"); a row-index check alone misses it.
                if str(getattr(curve, "kind", "") or "").strip().lower() == "image":
                    return True
                ri = getattr(curve, "row_index", None)
                try:
                    ri = int(ri)
                except (TypeError, ValueError):
                    return False
                if not (0 <= ri < len(self.rows)):
                    return False
                row = self.rows[ri]
                surface = str(getattr(row, "surface", "") or "").strip().lower()
                name = str(getattr(row, "name", "") or "").strip().lower()
                return surface == "image" or "detector" in name
            bundle.surface_curves = [
                c for c in (getattr(bundle, "surface_curves", None) or [])
                if not _is_superseded_terminal(c)
            ]
        else:
            # bugs/0188: a single promoted full-mirror cube folds the downstream chain
            # onto the reflected +X branch in the MESH system, but build_scene_targets
            # seats the table-row detector on the STRAIGHT +Z cumulative-thickness axis.
            # Carry it onto the branch here so EVERY consumer -- the 3-D footprint actor
            # (three_d_scene_tools._scene_detector_overlay_specs), the 2-D footprint
            # projection (scene_projector._project_detector_footprints) and the coverage
            # overlay (detector_coverage_overlay.add_overlays) -- draws on the folded
            # sensor. The two-arm splitter path above already replaced the detectors with
            # their own per-arm folded centres, so it is left untouched.
            if self._fold_promoted_mirror_table_row_targets(bundle):
                # bugs/0238: the surface curves were built on the UNFOLDED +Z axis (Non-
                # Sequential Preview does not fold them), so once the detector TARGET is
                # carried onto the branch its kind="image" curve is left behind on the
                # straight axis -- a SECOND image/detector plane off the beam (the user's
                # "two image and detector plane" on the two-fold periscope). The two-arm
                # splitter path above drops its superseded terminal curves; do the same for
                # the single promoted-mirror fold, but only for curves that no longer sit on
                # the folded detector (a coincident folded-sequential curve is kept).
                self._drop_unfolded_superseded_image_curves(bundle)
            # bugs/0193: build_scene_placements copies each row-backed placement's world
            # pose from the SAME unfolded +Z targets (scene_builder runs it before this
            # fold), so an aperture-stop / reference-grid placement on a folded row floats
            # on the straight axis (the user's misplaced reference grid). Carry it onto the
            # branch with the identical per-row rigid fold, so the grid overlay + drag gizmo
            # sit on the folded optics. The mirror pivot (no override) stays byte-identical.
            self._fold_promoted_mirror_scene_placements(bundle)
            # bugs/0189: the same promoted-mirror fold leaves the BLOCKED pupil/field
            # reference rays stranded on the unfolded +Z axis. They never reach the
            # mirror (stopped at surface 0, zero branch power, reaching no image), so the
            # display fold never carries them -- they draw as a faint +Z line past the
            # folded optics (the residual of flags 20260701_0817/0841/0847). Drop them.
            self._suppress_blocked_reference_ray_stubs(bundle)
            # bugs/0191: 0187 folds the running frame at a promoted full-mirror cube so the
            # ideal Thin Lenses downstream behave for the imaging cone -- but ~21% of the
            # MARGINAL rays still retroreflect at the first ideal Thin Lens (KrakenOS fakes
            # the ideal deflection as (L/N)*f, which back-bends a folded off-axis ray), then
            # double-pass back through the mirror and dive out the 45-deg hypotenuse to
            # ~250 mm behind it. That downward ray fan crossing the mirror is the user's
            # persistent "reflection still wrong at the hypotenuse". Trim each ray at its
            # retroreflection so it stops at the lens instead of plunging through the fold.
            self._truncate_folded_retroreflected_ray_tails(bundle)
        # bugs/0517 (detector redesign B2, the off-axis remainder): remember each branch
        # detector's WORLD frame so the camera STEP overlay can adopt its ASSIGNED branch's
        # frame (_camera_branch_world_transform). Merge-only: auxiliary builds (a per-arm
        # two-arm-fold part, an analysis sub-bundle) may carry no branch detectors and must
        # not wipe the frames the camera display relies on.
        try:
            frames: dict[str, dict] = {}
            for target in list(getattr(bundle, "targets", None) or []):
                meta = getattr(target, "metadata", None) or {}
                if not isinstance(meta, dict) or meta.get("target_source") != "branch_detector":
                    continue
                frames[str(meta.get("branch_path", ""))] = {
                    "center": tuple(
                        float(v) for v in np.asarray(target.center_world, dtype=float).reshape(-1)[:3]
                    ),
                    "normal": tuple(
                        float(v) for v in np.asarray(target.normal_world, dtype=float).reshape(-1)[:3]
                    ),
                    "focus_source": str(meta.get("focus_source", "") or ""),
                }
            if frames:
                self._branch_detector_world_frames = frames
        except Exception:
            pass
        return bundle

    def _suppress_blocked_reference_ray_stubs(self, bundle) -> int:
        """Drop blocked pupil/field reference-ray stubs stranded on the unfolded +Z axis.

        A promoted full-mirror cube folds the traced beam onto the reflected +X
        branch, but the pupil/field REFERENCE rays that never reach the mirror --
        blocked at the first surface, carrying no branch power, reaching no image --
        are seated on the STRAIGHT +Z cumulative-thickness axis and are never folded,
        so they draw a faint +Z line past the folded optics (bugs/0189). Only runs on
        a folded scene (>=1 row carries an optical-axis fold override, the same gate
        the detector/overlay fold uses), so plain / sequential-mirror / unfolded
        layouts keep every ray byte-identical. Returns the number dropped.
        """
        fold = getattr(self, "_optical_axis_fold_world_transform_for_row", None)
        if not callable(fold):
            return 0
        try:
            scene_is_folded = any(
                fold(row_index) is not None
                for row_index in range(len(getattr(self, "rows", []) or []))
            )
        except Exception:
            scene_is_folded = False
        if not scene_is_folded:
            return 0
        paths = list(getattr(bundle, "ray_paths", []) or [])
        if not paths:
            return 0
        kept = [p for p in paths if not _is_blocked_reference_ray_stub(p)]
        dropped = len(paths) - len(kept)
        if dropped:
            bundle.ray_paths = kept
        return dropped

    def _truncate_folded_retroreflected_ray_tails(self, bundle) -> int:
        """Trim each ray at its retroreflection on a promoted-mirror fold (bugs/0191).

        0187 represents a promoted full-mirror cube as a sequential ``Mirror`` so the
        running frame folds and the ideal Thin Lenses downstream behave for the imaging
        cone. But KrakenOS fakes an ideal Thin Lens deflection as ``(L/N)*f``, which
        back-bends a folded off-axis ray whose local axial cosine ``N`` has been driven
        small by the fold, so ~21% of the MARGINAL rays retroreflect at the first Thin
        Lens, double-pass back through the cube, and dive out the 45-deg hypotenuse to
        ~250 mm behind it -- the downward ray fan crossing the mirror the user keeps
        flagging. Truncating each ray at that ~180 deg reversal drops the non-physical
        tail so the ray stops at the lens instead. Only runs on a folded scene (the same
        fold-override gate the detector/stub fold uses), so plain / sequential-mirror /
        unfolded layouts keep every ray byte-identical. Returns the number truncated.
        """
        fold = getattr(self, "_optical_axis_fold_world_transform_for_row", None)
        if not callable(fold):
            return 0
        try:
            scene_is_folded = any(
                fold(row_index) is not None
                for row_index in range(len(getattr(self, "rows", []) or []))
            )
        except Exception:
            scene_is_folded = False
        if not scene_is_folded:
            return 0
        truncated = 0
        for path in list(getattr(bundle, "ray_paths", []) or []):
            forward = _folded_retroreflected_tail_points(getattr(path, "points_world", None))
            if forward is not None:
                path.points_world = forward
                truncated += 1
        return truncated

    def _fold_promoted_mirror_table_row_targets(self, bundle) -> int:
        """Fold every TABLE-ROW detector target onto a promoted mirror's reflected branch.

        ``build_scene_targets`` derives each table-row target's world pose from the
        unfolded cumulative-thickness +Z axis (it only knows ``editor.rows``, not the
        bugs/0185 fold, which lives in the optical-solid output-port pose overrides /
        the mesh system). A promoted full-mirror cube reflects the downstream chain --
        including the image surface disc -- onto +X, so an untouched detector target
        floats on the straight axis (the user's faint 45-deg "still in the wrong axis"
        line: flags ``flag_20260701_074930_725`` / ``flag_20260701_075019_938``). This
        applies the SAME rigid fold the lens/camera STEP overlays use
        (``_optical_axis_fold_world_transform_for_row``), which returns ``None`` for any
        row without a fold override -- so plain / sequential-mirror layouts and the
        upstream object reference are byte-identical. Returns the number folded.
        """
        folded = 0
        for target in list(getattr(bundle, "targets", []) or []):
            meta = getattr(target, "metadata", None) or {}
            if not isinstance(meta, dict) or str(meta.get("target_source", "") or "") != "table_row":
                continue
            if self._fold_table_row_target_world_pose(target):
                folded += 1
        return folded

    def _fold_table_row_target_world_pose(self, target) -> bool:
        """Carry one table-row target's ``center``/``normal``/``tangent`` world pose onto
        its row's folded branch in place. Returns ``True`` when a fold was applied
        (``False`` for an unfolded row or a non-finite result)."""
        fold = getattr(self, "_optical_axis_fold_world_transform_for_row", None)
        row_index = getattr(target, "row_index", None)
        if row_index is None or not callable(fold):
            return False
        try:
            transform = fold(int(row_index))
        except Exception:
            transform = None
        if transform is None:
            return False
        try:
            matrix = np.asarray(transform, dtype=float).reshape(4, 4)
            center = np.asarray(target.center_world, dtype=float).reshape(3)
            normal = np.asarray(target.normal_world, dtype=float).reshape(3)
            tangent = np.asarray(target.tangent_world, dtype=float).reshape(3)
            folded_center = (matrix @ np.append(center, 1.0))[:3]
            folded_normal = matrix[:3, :3] @ normal
            folded_tangent = matrix[:3, :3] @ tangent
        except Exception:
            return False
        if not (
            np.all(np.isfinite(folded_center))
            and np.all(np.isfinite(folded_normal))
            and np.all(np.isfinite(folded_tangent))
        ):
            return False
        target.center_world = np.asarray(folded_center, dtype=float)
        target.normal_world = np.asarray(folded_normal, dtype=float)
        target.tangent_world = np.asarray(folded_tangent, dtype=float)
        return True

    def _drop_unfolded_superseded_image_curves(self, bundle) -> int:
        """bugs/0238: drop any ``kind="image"`` surface curve that no longer coincides with
        a folded detector target.

        In Non-Sequential Preview the surface curves are built on the UNFOLDED +Z axis while
        ``_fold_promoted_mirror_table_row_targets`` carries the detector TARGET onto the
        promoted-mirror branch. The stale unfolded image curve then draws a SECOND image /
        detector plane off the beam (the user's "two image and detector plane" on the
        two-fold periscope). A curve that STILL sits on its detector -- a plain sequential
        scene, or a folded-sequential one whose curve was itself built folded -- is within
        the tolerance and kept, so only the genuine off-beam duplicate is removed. Returns
        the number of curves dropped."""
        detectors = [t for t in (getattr(bundle, "targets", None) or []) if getattr(t, "is_detector", False)]
        det_centers: list[np.ndarray] = []
        for target in detectors:
            try:
                center = np.asarray(target.center_world, dtype=float).reshape(3)
            except Exception:
                continue
            if np.all(np.isfinite(center)):
                det_centers.append(center)
        if not det_centers:
            return 0

        def _centroid(curve):
            pts = getattr(curve, "points_world", None)
            if pts is None:
                pts = getattr(curve, "points", None)
            if pts is None:
                return None
            try:
                arr = np.asarray(pts, dtype=float).reshape(-1, 3)
            except Exception:
                return None
            return arr.mean(axis=0) if arr.size else None

        kept: list = []
        dropped = 0
        for curve in (getattr(bundle, "surface_curves", None) or []):
            if str(getattr(curve, "kind", "") or "").strip().lower() == "image":
                centroid = _centroid(curve)
                if centroid is not None and min(
                    float(np.linalg.norm(centroid - dc)) for dc in det_centers
                ) > _SUPERSEDED_IMAGE_CURVE_TOL_MM:
                    dropped += 1
                    continue
            kept.append(curve)
        if dropped:
            bundle.surface_curves = kept
        return dropped

    def _reseat_superseded_image_meshes_to_folded_detector(self, bundle) -> int:
        """bugs/0239: translate every ``kind="image"`` surface MESH (the drawn sensor DISC) onto the
        nearest FOLDED detector target -- the physics focus where the rays actually converge.

        The image surface disc is built at the LENS-only paraxial image plane
        (``_paraxial_image_plane_z``) and folded onto the promoted-mirror branch, but the flattened
        mirror plates add a glass path the lens-only first order ignores, so the real ray waist --
        where ``_fold_promoted_mirror_table_row_targets`` seats the detector target and where the
        traced cone converges -- sits ~a plate-thickness (AZ85: ~20 mm) beyond it. The disc then
        floats off the beam: a SECOND image/detector plane (the user's "still 2 image and detector
        plane" after the folded FOV solve), the MESH sibling of the curve ``_drop_unfolded_superseded_
        image_curves`` (bugs/0238) removes. Re-seating (not dropping) keeps the solid sensor disc the
        unfolded scene draws, now coincident with the detector + rays -- display follows physics.

        Fires only on a FOLDED scene (detector carried off the straight +Z axis) for a disc that has
        DIVERGED from every detector, so plain / sequential / unfolded layouts keep every mesh byte-
        identical. The shift is recomputed from the live centroid each pass, so it is idempotent (a
        disc already on the detector is within tolerance and skipped). Returns the number reseated."""
        meshes = getattr(bundle, "surface_meshes", None) or []
        if not meshes:
            return 0
        det_centers: list[np.ndarray] = []
        for target in (getattr(bundle, "targets", None) or []):
            if not getattr(target, "is_detector", False):
                continue
            try:
                center = np.asarray(target.center_world, dtype=float).reshape(3)
            except Exception:
                continue
            if np.all(np.isfinite(center)) and float(np.hypot(center[0], center[1])) > _FOLDED_DETECTOR_OFF_AXIS_MM:
                det_centers.append(center)
        if not det_centers:
            return 0
        reseated = 0
        for item in meshes:
            if str(getattr(item, "kind", "") or "").strip().lower() != "image":
                continue
            mesh = getattr(item, "mesh", None)
            pts = getattr(mesh, "points", None) if mesh is not None else None
            if pts is None:
                continue
            try:
                arr = np.asarray(pts, dtype=float).reshape(-1, 3)
            except Exception:
                continue
            if not arr.size:
                continue
            centroid = arr.mean(axis=0)
            nearest = min(det_centers, key=lambda dc: float(np.linalg.norm(centroid - dc)))
            if float(np.linalg.norm(centroid - nearest)) <= _SUPERSEDED_IMAGE_CURVE_TOL_MM:
                continue
            try:
                mesh.points = arr + (nearest - centroid)
                reseated += 1
            except Exception:
                continue
        return reseated

    def _fold_promoted_mirror_scene_placements(self, bundle) -> int:
        """Fold every row-backed scene PLACEMENT onto a promoted mirror's reflected branch.

        ``build_scene_placements`` seats each placement's world pose on the unfolded
        cumulative-thickness +Z axis (scene_builder builds it from the pre-fold targets,
        before ``_fold_promoted_mirror_table_row_targets`` runs). A promoted full-mirror
        cube reflects the downstream chain onto +X, so an aperture-stop / reference-grid
        placement on a folded row floats on the straight axis (bugs/0193). Apply the SAME
        rigid fold the detector targets use (``_optical_axis_fold_world_transform_for_row``,
        ``None`` for any unfolded row -- so the mirror pivot and plain layouts stay
        byte-identical). Returns the number folded.
        """
        fold = getattr(self, "_optical_axis_fold_world_transform_for_row", None)
        if not callable(fold):
            return 0
        folded = 0
        for placement in list(getattr(bundle, "placements", []) or []):
            row_index = getattr(placement, "row_index", None)
            if row_index is None:
                continue
            try:
                transform = fold(int(row_index))
            except Exception:
                transform = None
            if transform is None:
                continue
            try:
                matrix = np.asarray(transform, dtype=float).reshape(4, 4)
                center = np.asarray(placement.center_world, dtype=float).reshape(3)
                normal = np.asarray(placement.normal_world, dtype=float).reshape(3)
                tangent = np.asarray(placement.tangent_world, dtype=float).reshape(3)
                folded_center = (matrix @ np.append(center, 1.0))[:3]
                folded_normal = matrix[:3, :3] @ normal
                folded_tangent = matrix[:3, :3] @ tangent
            except Exception:
                continue
            if not (
                np.all(np.isfinite(folded_center))
                and np.all(np.isfinite(folded_normal))
                and np.all(np.isfinite(folded_tangent))
            ):
                continue
            placement.center_world = np.asarray(folded_center, dtype=float)
            placement.normal_world = np.asarray(folded_normal, dtype=float)
            placement.tangent_world = np.asarray(folded_tangent, dtype=float)
            folded += 1
        return folded

    def _settings_for_two_arm_leaf_trace(self) -> dict:
        """The launch settings each per-arm sequential leaf trace needs (the rest default)."""
        out: dict = {}
        for key in ("object_mode", "wavelength", "ray_count", "ray_height_factor",
                    "source_model", "pupil_pattern", "aperture_type", "aperture_value",
                    "field_type", "field_value", "field_count"):
            var = getattr(self, f"{key}_var", None)
            if var is not None:
                try:
                    out[key] = var.get()
                except Exception:
                    pass
        return out

    def _two_arm_fold_parts(self, system):
        """Per-arm folded ray paths + detectors for a >=2-imaging-arm splitter scene (cached).

        Returns ``None`` for ordinary scenes (the normal trace stands). For a two-arm splitter
        it traces each arm straight + sequential and folds the bent arm -- see
        ``services/two_arm_display_fold.py`` and the ``two-arm-display-fold-architecture`` note.
        """
        try:
            leaves = self._imaging_branch_leaves()
        except Exception as exc:
            try:
                self.append_debug(f"[two-arm display-fold] imaging-leaf detection raised: {exc!r}")
            except Exception:
                pass
            return None
        if leaves:  # splitter scene with >=1 imaging arm -- log for diagnosis (single-axis scenes stay quiet)
            try:
                self.append_debug(f"[two-arm display-fold] {len(leaves)} imaging arm(s): {sorted(leaves)}")
            except Exception:
                pass
        if not leaves or len(leaves) < 2:
            return None
        settings = self._settings_for_two_arm_leaf_trace()
        try:
            from KrakenOS.UI.services.row_spec_contracts import _row_specs_signature
            sig = (_row_specs_signature(self._serializable_row_specs()), tuple(sorted(settings.items())))
        except Exception:
            sig = None
        cache = self.__dict__.get("_two_arm_fold_cache")  # __dict__ avoids the tkinter __getattr__ recursion
        if sig is not None and cache is not None and cache[0] == sig:
            return cache[1]
        try:
            from KrakenOS.UI.services.two_arm_display_fold import build_two_arm_fold_parts
            max_radius = max(float(r.diameter) for r in self.rows) / 2.0
            parts = build_two_arm_fold_parts(leaves, settings, self._current_wavelength(), max_radius)
            try:
                self.append_debug(
                    f"[two-arm display-fold] applied {len(parts[0])} folded paths"
                    if parts else "[two-arm display-fold] build returned None")
            except Exception:
                pass
        except Exception as exc:  # noqa: BLE001 -- degrade to the ordinary trace, but record why
            try:
                self.append_debug(f"[two-arm display-fold] disabled this refresh: {exc!r}")
            except Exception:
                pass
            parts = None
        self._two_arm_fold_cache = (sig, parts)
        return parts

    def _branch_detector_camera_sensors(self) -> dict | None:
        """B2 (vendor-step-import-semantics): map ``{branch_path -> (camera_label,
        (sensor_w_mm, sensor_h_mm))}`` from the per-branch camera registrations,
        resolved through the vendor camera DB. derive_branch_detectors blends each
        registered branch detector to its camera's active sensor."""
        # Read via __dict__: on a Tk-widget subclass a missing attribute falls into
        # tkinter's __getattr__, which here recurses (the 0082 trap) instead of
        # raising AttributeError, so getattr(..., default) never returns the default.
        assignments = self.__dict__.get("branch_detector_camera_assignments") or {}
        if not assignments:
            return None
        try:
            from KrakenOS.UI.camera_database import camera_sensor_active_mm
        except Exception:
            return None
        out: dict[str, tuple] = {}
        for branch_path, camera in dict(assignments).items():
            try:
                dims = camera_sensor_active_mm(str(camera))
            except Exception:
                dims = None
            if dims is not None:
                out[str(branch_path)] = (str(camera), (float(dims[0]), float(dims[1])))
        return out or None

    # _current_surface_scene, _render_current_layout_surfaces removed —
    # now in scene_builder.build_scene_bundle()

    # _build_folded_surface_paths, _surface_style_for_row, _polyline_vertical_extents,
    # _polyline_endpoints, _build_row_surface_groups, _build_curve_group_edge_paths,
    # _build_sequential_lens_edge_paths, _build_sequential_surface_paths
    # removed — now in scene_builder.py
    # _draw_colored_rays removed — now in scene_renderer_2d._draw_rays



    # --- Physical Distance overlay -------------------------------------------

    def _results_display_service(self) -> ResultsDisplayService:
        service = self.__dict__.get("_results_display_service_instance")
        if service is None:
            service = ResultsDisplayService(self)
            self._results_display_service_instance = service
        return service

    def _clear_physical_distance_artists(self) -> None:
        self._results_display_service()._clear_physical_distance_artists()

    def _on_toggle_physical_distances(self) -> None:
        self._results_display_service()._on_toggle_physical_distances()

    def _draw_physical_distances(self) -> None:
        self._results_display_service()._draw_physical_distances()

    def _update_results(self, system, rays, wavelength: float, optics_info: dict | None = None) -> None:
        self._results_display_service()._update_results(system, rays, wavelength, optics_info)

    # _set_plot_limits_from_layout removed — now in scene_renderer_2d.set_plot_limits

    def _set_plot_limits_from_drawn_data(self) -> None:
        x_values: list[float] = []
        y_values: list[float] = []
        for line in self.ax.lines:
            xdata = np.asarray(line.get_xdata(orig=False), dtype=float)
            ydata = np.asarray(line.get_ydata(orig=False), dtype=float)
            finite = np.isfinite(xdata) & np.isfinite(ydata)
            if np.any(finite):
                x_values.extend(xdata[finite].tolist())
                y_values.extend(ydata[finite].tolist())
        if not x_values or not y_values:
            return
        x_min = min(x_values)
        x_max = max(x_values)
        y_min = min(y_values)
        y_max = max(y_values)
        span_x = max(x_max - x_min, 1.0)
        span_y = max(y_max - y_min, 1.0)
        self.ax.set_xlim(x_min - 0.08 * span_x, x_max + 0.08 * span_x)
        self.ax.set_ylim(y_min - 0.12 * span_y, y_max + 0.12 * span_y)

    def _draw_input_ray_overlay(self, max_radius: float) -> None:
        if not self.rows:
            return
        if self._current_object_mode() == "Infinity":
            return
        object_distance = self._current_object_distance()
        if object_distance <= 1e-9:
            return
        field_samples = self._sample_field_values(self._current_field_height())
        angle_samples = self._sample_fan_angles_deg()
        colors = self._field_colors(len(field_samples))
        for field_index, field_height in enumerate(field_samples):
            color = colors[field_index]
            for angle_deg in angle_samples:
                angle_rad = np.deg2rad(angle_deg)
                pupil_y = float(field_height) + float(np.tan(angle_rad) * object_distance)
                x_vals, y_vals = self._project_xy([0.0, object_distance], [float(field_height), float(pupil_y)])
                self.ax.plot(
                    x_vals,
                    y_vals,
                    color=color,
                    linewidth=1.8,
                    alpha=0.95,
                )

    @staticmethod
    def _gaussian_radius_from_q(q_value: complex, wavelength_mm: float, m2: float, refractive_index: float) -> float:
        if not (np.isfinite(q_value.real) and np.isfinite(q_value.imag)) or abs(q_value) <= 1e-18:
            return np.nan
        inverse_q = 1.0 / q_value
        imag_inverse = float(np.imag(inverse_q))
        if imag_inverse >= 0.0:
            return np.nan
        return float(np.sqrt(-(wavelength_mm * m2) / (np.pi * max(float(refractive_index), 1e-12) * imag_inverse)))

    def _draw_gaussian_beam_overlay(self, system, wavelength: float) -> float | None:
        if self._current_source_model() != "Gaussian beam":
            return None
        source_direction = np.asarray(self._current_source_direction(), dtype=float)
        if np.linalg.norm(source_direction - np.asarray((0.0, 0.0, 1.0), dtype=float)) > 1e-9:
            self.append_debug(
                "Gaussian beam envelope skipped for non-+Z source direction; "
                "use traced source rays and Gaussian Beam Report data."
            )
            return None
        if any(row.surface == "Mirror" for row in self.rows) or self._has_off_axis_geometry():
            self.append_debug("Gaussian beam envelope skipped for folded/off-axis geometry; use Gaussian Beam Report for ABCD data.")
            return None
        try:
            paraxial_trace = system.ParaxMatrices(float(wavelength))
            input_beam = self._current_gaussian_beam_input(wavelength)
            beam_trace = Kos.propagate_gaussian_beam(paraxial_trace, input_beam)
        except Exception as exc:
            self.append_debug(f"Gaussian beam overlay unavailable: {_short_error_message(exc)}")
            return None

        wavelength_mm = float(beam_trace.wavelength_mm)
        m2 = float(input_beam.m2)
        current_z = 0.0
        source_x, source_y, source_z = self._current_source_origin()
        _unused_source_x = source_x
        q_before = complex(beam_trace.input_q)
        n_current = float(beam_trace.input_index)
        z_values: list[float] = [float(source_z)]
        radius_values: list[float] = [
            self._gaussian_radius_from_q(q_before, wavelength_mm, m2, n_current)
        ]

        for parax_step, beam_step in zip(paraxial_trace.steps, beam_trace.steps):
            q_after = complex(float(beam_step.q_real_mm), float(beam_step.q_imag_mm))
            n_after = max(float(beam_step.n_after), 1e-12)
            if str(getattr(parax_step, "kind", "")) == "translation":
                thickness = float(getattr(parax_step, "thickness", 0.0))
                sample_count = max(2, min(32, int(abs(thickness) / 5.0) + 2))
                for offset in np.linspace(0.0, thickness, sample_count)[1:]:
                    q_sample = q_before + float(offset)
                    z_values.append(float(source_z + current_z + float(offset)))
                    radius_values.append(self._gaussian_radius_from_q(q_sample, wavelength_mm, m2, n_after))
                current_z += thickness
            else:
                z_values.append(float(source_z + current_z))
                radius_values.append(self._gaussian_radius_from_q(q_after, wavelength_mm, m2, n_after))
            q_before = q_after
            n_current = n_after

        z_arr = np.asarray(z_values, dtype=float)
        r_arr = np.asarray(radius_values, dtype=float)
        finite = np.isfinite(z_arr) & np.isfinite(r_arr) & (r_arr >= 0.0)
        if np.count_nonzero(finite) < 2:
            return None
        z_arr = z_arr[finite]
        r_arr = r_arr[finite]
        y_center = float(source_y)
        upper_x, upper_y = self._project_xy(z_arr, y_center + r_arr)
        lower_x, lower_y = self._project_xy(z_arr, y_center - r_arr)
        center_x, center_y = self._project_xy(z_arr, np.full_like(z_arr, y_center))
        color = "#f59e0b"
        self.ax.plot(upper_x, upper_y, color=color, linewidth=1.8, linestyle="-", alpha=0.92, zorder=31.0)
        self.ax.plot(lower_x, lower_y, color=color, linewidth=1.8, linestyle="-", alpha=0.92, zorder=31.0)
        self.ax.plot(center_x, center_y, color=color, linewidth=0.85, linestyle=":", alpha=0.75, zorder=30.0)
        if self._current_display_orientation() == "YZ":
            self.ax.fill_between(
                z_arr,
                y_center - r_arr,
                y_center + r_arr,
                color=color,
                alpha=0.08,
                linewidth=0.0,
                zorder=29.0,
            )
        label_index = min(max(int(len(z_arr) * 0.12), 0), len(z_arr) - 1)
        self.ax.text(
            float(upper_x[label_index]),
            float(upper_y[label_index]),
            "Gaussian 1/e^2",
            color=color,
            fontsize=8,
            ha="left",
            va="bottom",
            zorder=61.0,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.7, "pad": 0.4},
        )
        return float(np.max(np.abs(y_center) + r_arr))

    def _apply_example_display_defaults(self, path: Path) -> None:
        code = path.read_text(encoding="utf-8", errors="ignore")
        self._apply_interferometer_example_defaults(path)

        wavelength_match = re.search(r"\bW\s*=\s*([0-9]*\.?[0-9]+)", code)
        if wavelength_match:
            self.wavelength_var.set(wavelength_match.group(1))

        aperture_type_match = re.search(r"\b(?:AperType|ApType)\s*=\s*['\"](STOP|EPD|FNO)['\"]", code)
        if aperture_type_match:
            self.aperture_type_var.set(aperture_type_match.group(1))

        aperture_value_match = re.search(r"\b(?:AperVal|ApVal)\s*=\s*([0-9]*\.?[0-9]+)", code)
        if aperture_value_match:
            self.aperture_value_var.set(aperture_value_match.group(1))

        surf_match = re.search(r"\b(?:Surf|sup)\s*=\s*([0-9]+)", code)
        if surf_match:
            surf_index = surf_match.group(1)
            label = None
            for option in self.analysis_surface_menu["values"]:
                if option.startswith(f"{surf_index}:"):
                    label = option
                    break
            if label is not None:
                self.analysis_surface_var.set(label)
            else:
                self.analysis_surface_var.set("Auto")
        else:
            self.analysis_surface_var.set("Auto")

        if self._example_requests_nonsequential(code) and hasattr(self, "trace_mode_var"):
            self.trace_mode_var.set("Non-Sequential Preview")
            self.trace_mode = "Non-Sequential Preview"

    def _apply_interferometer_example_defaults(self, path: Path) -> None:
        stem = path.stem.lower()
        is_michelson = stem == "examp_michelson_interferometer"
        is_twyman = stem == "examp_twyman_green_interferometer"
        is_mach_zehnder = stem == "examp_mach_zehnder_interferometer"
        if not (is_michelson or is_twyman or is_mach_zehnder):
            return

        def _set_text_var(name: str, value: str) -> None:
            var = getattr(self, name, None)
            if var is not None:
                try:
                    var.set(value)
                except Exception:
                    pass

        _set_text_var("object_mode_var", "Infinity")
        _set_text_var("display_orientation_var", "YZ")
        _set_text_var("wavelength_var", "0.6328")
        _set_text_var("ray_count_var", "1")
        _set_text_var("source_model_var", "Collimated disk source")
        _set_text_var("source_radius_var", "0.5")
        _set_text_var("source_cone_angle_var", "0.0")
        _set_text_var("source_power_var", "1.0")
        _set_text_var("source_seed_var", "1")
        _set_text_var("source_x_var", "0.0")
        _set_text_var("source_y_var", "0.0")
        _set_text_var("source_z_var", "0.0")
        _set_text_var("source_l_var", "0.0")
        _set_text_var("source_m_var", "0.0")
        _set_text_var("source_n_var", "1.0")
        _set_text_var("field_type_var", "Angle")
        _set_text_var("field_value_var", "0.0")
        _set_text_var("field_count_var", "1")
        _set_text_var("aperture_type_var", "EPD")
        _set_text_var("aperture_value_var", "1.0")
        _set_text_var("trace_mode_var", "Non-Sequential Preview")
        _set_text_var("nonseq_ns_limit_var", "140" if is_mach_zehnder else "80")
        self.trace_mode = "Non-Sequential Preview"
        self.selected_analysis_modes = []
        self.analysis_mode = "none"
        self.secondary_analysis_mode = None
        try:
            self._sync_analysis_mode_buttons()
        except Exception:
            pass

        if is_mach_zehnder:
            return
        self._apply_michelson_family_example_metadata(is_twyman=is_twyman)

    def _apply_michelson_family_example_metadata(self, *, is_twyman: bool = False) -> None:
        title = "Twyman-Green" if is_twyman else "Michelson"
        splitter_name = "Twyman-Green splitter" if is_twyman else "Michelson splitter"
        interferogram_settings = {
            "analysis_title": f"{title} Interferogram",
            "detector_port": "cross",
            "detector_size_mm": 12.0,
            "pixels": 256,
            "fringe_tilt_x_mrad": 2.0 if is_twyman else 1.5,
            "fringe_tilt_y_mrad": 0.0,
            "opd_offset_um": 0.0,
            "visibility": 1.0,
            "coherence_mode": COHERENT_SUM_MODE_DEFAULT,
        }
        for row in self.rows:
            text = f"{getattr(row, 'name', '')} {getattr(row, 'element', '')}".strip().lower()
            advanced = dict(getattr(row, "advanced", {}) or {})
            if row.surface == BEAM_SPLITTER_SURFACE or "splitter" in text:
                row.surface = BEAM_SPLITTER_SURFACE
                row.element = splitter_name
                advanced[BEAM_SPLITTER_ADVANCED_ATTR] = _normalize_beam_splitter_settings(
                    advanced.get(BEAM_SPLITTER_ADVANCED_ATTR, BEAM_SPLITTER_DEFAULT_SETTINGS)
                )
                row.advanced = advanced
                self._set_element_metadata(
                    row,
                    {
                        "element_id": "BS1",
                        "element_name": splitter_name,
                        "arm_role": "Common",
                        "parent_splitter": "",
                    },
                )
                continue
            if row.surface == "Mirror" and ("transmit" in text or "test optic" in text):
                row.element = "Test optic" if is_twyman else "Transmit return mirror"
                row.advanced = advanced
                self._set_element_metadata(
                    row,
                    {
                        "element_id": "M_TX",
                        "element_name": row.element,
                        "arm_role": "Return",
                        "parent_splitter": "BS1",
                        "branch_selector": "transmit",
                        "arm_distance": 80.0,
                    },
                )
                continue
            if row.surface == "Mirror" and ("reflect" in text or "reference" in text):
                row.element = "Reference flat" if is_twyman else "Reflect return mirror"
                row.advanced = advanced
                self._set_element_metadata(
                    row,
                    {
                        "element_id": "M_RX",
                        "element_name": row.element,
                        "arm_role": "Return",
                        "parent_splitter": "BS1",
                        "branch_selector": "reflect",
                        "arm_distance": 80.0,
                    },
                )
                continue
            if row.surface == "Image" or "detector" in text or "output port" in text:
                row.element = "Detector path"
                advanced["Display2D"] = {
                    "plane_center": [50.0, -70.0],
                    "plane_tangent": [1.0, 0.0],
                    "branch_output_targets": {
                        "TT": [0.0, 0.0],
                        "TR": [50.0, -70.0],
                        "RT": [50.0, -70.0],
                        "RR": [0.0, 0.0],
                    },
                }
                advanced["Interferogram"] = interferogram_settings
                row.advanced = advanced
                self._set_element_metadata(
                    row,
                    {
                        "element_id": "DET_1",
                        "element_name": "Detector path",
                        "arm_role": "Detector",
                        "parent_splitter": "BS1",
                        "branch_selector": "reflect",
                        "arm_distance": 70.0,
                    },
                )

    @staticmethod
    def _example_requests_nonsequential(code: str) -> bool:
        return bool(re.search(r"\bNsTraceLoop\s*\(|\.\s*NsTrace\s*\(", code))




    def _plot_fallback_preview(self, max_radius: float) -> None:
        positions = []
        z = 0.0
        last_index = len(self.rows) - 1
        for row_index, row in enumerate(self.rows):
            positions.append(z)
            radius = max(row.diameter / 2.0, 0.5)
            color = "#4f81bd" if row.glass.upper() != "AIR" else "#7f8c8d"
            x_vals, y_vals = self._project_xy([z, z], [-radius, radius])
            self.ax.plot(x_vals, y_vals, color=color, linewidth=2)
            if row.surface in {"Object", "Image", "Aperture"} or row_index in {0, last_index}:
                self.ax.text(
                    float(x_vals[0]),
                    float(np.max(y_vals) + max_radius * 0.08),
                    row.name,
                    rotation=0,
                    ha="center",
                    va="bottom",
                    fontsize=8,
                )
            z += row.thickness

        total_length = max(z, 1.0)
        margin = max(total_length * 0.05, 5.0)
        if self._current_display_orientation() in {"XZ", "XY"}:
            self._set_plot_limits_from_drawn_data()
        else:
            self.ax.set_xlim(-margin, total_length + margin)
            self.ax.set_ylim(-(max_radius * 1.4), max_radius * 1.4)
        axis_x, axis_y = self._project_xy([0.0, total_length], [0.0, 0.0])
        self.ax.plot(axis_x, axis_y, color="#2c3e50", linewidth=0.8)
        self.ax.text(
            0.01,
            0.99,
            "Fallback sequential preview",
            transform=self.ax.transAxes,
            ha="left",
            va="top",
            fontsize=8,
            color="#7f1d1d",
            bbox={"facecolor": "white", "edgecolor": "#7f1d1d", "alpha": 0.75, "pad": 2.0},
        )

    def _plot_trace_failure_diagnostic(self, exc: NonSequentialTracePreviewError) -> None:
        trace_state = dict(getattr(exc, "trace_state", {}) or {})
        reasons = ", ".join(str(reason) for reason in trace_state.get("reasons", ()) or ())
        lines = [
            "Non-sequential trace failed",
            _short_error_message(exc, limit=320),
            "Sequential fallback was not drawn.",
        ]
        if reasons:
            lines.append(f"Scene trigger: {reasons}")
        self.ax.set_axis_off()
        self.ax.text(
            0.5,
            0.58,
            "\n".join(lines),
            transform=self.ax.transAxes,
            ha="center",
            va="center",
            fontsize=10,
            color="#7f1d1d",
            bbox={"facecolor": "white", "edgecolor": "#7f1d1d", "alpha": 0.88, "pad": 8.0},
            wrap=True,
        )
