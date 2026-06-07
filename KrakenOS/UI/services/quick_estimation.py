"""Quick Estimation -- live object/image conjugate + FOV solve in Open 3D.

A constraint-solver over four axial quantities, each with a *role*:

    Object Plane     Object Thickness    Image Thickness     Image Plane
        |                  |                   |                  |
     (sensor study: pin the Image Plane / sensor, drag the Object Thickness,
      the Image Thickness re-solves to keep focus, FOV = sensor / |m| updates)

Roles
-----
* ``constant``     -- pinned (typed value, never solved).
* ``independent``  -- the user drives it (drag or type).
* ``dependent``    -- computed from the independent so the image stays focused.

The two *thickness* quantities form the conjugate pair tied by the lens:
``Object Thickness`` is ``rows[0].thickness`` (object distance) and
``Image Thickness`` is ``rows[-2].thickness`` (image distance). Setting one
re-solves the other through the existing paraxial engine
(``_compute_paraxial_solve_result``). Interacting with a thickness *promotes it
to independent* and demotes its partner to dependent -- the user's
"type/drag on either one and it immediately becomes the independent variable".

The two *plane* quantities are axial references; in the relative-thickness
model the Image Plane is always the terminal sensor station, so it reads
``constant`` by default and the solve lands focus on it.

The engine never retraces; callers (``apply_dimension_value``) own the retrace.
"""

from __future__ import annotations

from typing import Any

import numpy as np


OBJECT_PLANE = "object_plane"
OBJECT_THICKNESS = "object_thickness"
IMAGE_THICKNESS = "image_thickness"
IMAGE_PLANE = "image_plane"

QUANTITIES = (OBJECT_PLANE, OBJECT_THICKNESS, IMAGE_THICKNESS, IMAGE_PLANE)
THICKNESS_QUANTITIES = (OBJECT_THICKNESS, IMAGE_THICKNESS)

LABELS = {
    OBJECT_PLANE: "Object Plane",
    OBJECT_THICKNESS: "Object Thickness",
    IMAGE_THICKNESS: "Image Thickness",
    IMAGE_PLANE: "Image Plane",
}

ROLE_CONSTANT = "constant"
ROLE_INDEPENDENT = "independent"
ROLE_DEPENDENT = "dependent"
ROLES = (ROLE_CONSTANT, ROLE_INDEPENDENT, ROLE_DEPENDENT)

# Standard machine-vision sensor formats: (label, nominal sensor diagonal mm).
SENSOR_FORMATS = (
    ('1/4"', 4.5), ('1/3"', 6.0), ('1/2.5"', 7.2), ('1/2"', 8.0),
    ('1/1.8"', 9.0), ('2/3"', 11.0), ('1"', 16.0), ('4/3"', 22.5),
    ("APS-C", 28.3), ("Full-frame", 43.3),
)
SENSOR_ASPECT = (4.0, 3.0)  # default 4:3 machine-vision sensor


def _nearest_sensor_format(diagonal: float) -> tuple[str, float]:
    return min(SENSOR_FORMATS, key=lambda fmt: abs(fmt[1] - float(diagonal)))


class QuickEstimationService:
    """Object/image conjugate + FOV solver wired to the 3D thickness handles."""

    def __init__(self, inspector: Any) -> None:
        self.inspector = inspector
        self.editor = inspector.editor
        # Default machine-vision study: pin the sensor, drive the object
        # distance, let the image distance solve for focus.
        self._roles: dict[str, str] = {
            OBJECT_PLANE: ROLE_CONSTANT,
            OBJECT_THICKNESS: ROLE_INDEPENDENT,
            IMAGE_THICKNESS: ROLE_DEPENDENT,
            IMAGE_PLANE: ROLE_CONSTANT,
        }
        # The real object semi-height the user wants to image (None = "fill the
        # sensor", i.e. the FOV that exactly maps to the sensor edge). When set,
        # the fill factor = target / FOV tells how much of the sensor the object
        # covers (>1 overfills/crops, <1 underfills).
        self._target_object_semi: float | None = None
        # The object FOV semi-height before the last change, for the before/after
        # ghost circle in the 3D overlay.
        self._previous_object_semi: float | None = None

    # ------------------------------------------------------------------ state
    def is_enabled(self) -> bool:
        try:
            return bool(self.inspector.quick_estimation_var.get())
        except Exception:
            return False

    def role(self, quantity: str) -> str:
        return self._roles.get(quantity, ROLE_CONSTANT)

    def object_thickness_row(self) -> int | None:
        return 0 if getattr(self.editor, "rows", None) else None

    def image_thickness_row(self) -> int | None:
        rows = getattr(self.editor, "rows", None) or []
        return len(rows) - 2 if len(rows) >= 2 else None

    def quantity_for_thickness_row(self, row_index: int) -> str | None:
        if self.object_thickness_row() == row_index:
            return OBJECT_THICKNESS
        if self.image_thickness_row() == row_index:
            return IMAGE_THICKNESS
        return None

    def row_for_quantity(self, quantity: str) -> int | None:
        if quantity == OBJECT_THICKNESS:
            return self.object_thickness_row()
        if quantity == IMAGE_THICKNESS:
            return self.image_thickness_row()
        return None

    @staticmethod
    def _partner(quantity: str) -> str | None:
        if quantity == OBJECT_THICKNESS:
            return IMAGE_THICKNESS
        if quantity == IMAGE_THICKNESS:
            return OBJECT_THICKNESS
        return None

    def is_independent_thickness_row(self, row_index: int) -> bool:
        quantity = self.quantity_for_thickness_row(int(row_index))
        return quantity is not None and self.role(quantity) == ROLE_INDEPENDENT

    # ------------------------------------------------------------------ roles
    def set_role(self, quantity: str, role: str) -> str:
        """Set a quantity's role, keeping the conjugate pair well-posed.

        Returns a short status message describing the resulting configuration.
        """
        if quantity not in QUANTITIES or role not in ROLES:
            return ""
        self._roles[quantity] = role
        if quantity in THICKNESS_QUANTITIES:
            partner = self._partner(quantity)
            if role == ROLE_INDEPENDENT and partner is not None:
                # the dragged/typed one is independent; its partner absorbs the
                # focus constraint unless the user pinned it constant.
                if self._roles.get(partner) != ROLE_CONSTANT:
                    self._roles[partner] = ROLE_DEPENDENT
            elif role == ROLE_DEPENDENT and partner is not None:
                if self._roles.get(partner) != ROLE_CONSTANT:
                    self._roles[partner] = ROLE_INDEPENDENT
            elif role == ROLE_CONSTANT and partner is not None:
                # pinning one thickness leaves the partner as the only free
                # focus gap -> it must be independent (the lens/object moves).
                self._roles[partner] = ROLE_INDEPENDENT
        self._sync_plane_roles()
        return self._role_summary()

    def promote_to_independent(self, quantity: str) -> None:
        """The user interacted with ``quantity`` -- make it the independent."""
        if quantity in THICKNESS_QUANTITIES:
            self.set_role(quantity, ROLE_INDEPENDENT)

    def _sync_plane_roles(self) -> None:
        # Object Plane mirrors the Object Thickness freedom; the Image Plane is
        # the pinned sensor reference in the sensor study.
        self._roles[OBJECT_PLANE] = (
            ROLE_INDEPENDENT if self._roles.get(OBJECT_THICKNESS) == ROLE_INDEPENDENT else ROLE_CONSTANT
        )
        self._roles[IMAGE_PLANE] = ROLE_CONSTANT

    def _role_summary(self) -> str:
        ind = next((LABELS[q] for q in THICKNESS_QUANTITIES if self._roles.get(q) == ROLE_INDEPENDENT), "?")
        dep = next((LABELS[q] for q in THICKNESS_QUANTITIES if self._roles.get(q) == ROLE_DEPENDENT), "?")
        return f"Quick Estimation: drive {ind}, {dep} solves for focus."

    # ------------------------------------------------------------------ solve
    def solve_dependent(self, independent_row_index: int) -> tuple[bool, str]:
        """Solve + apply the dependent thickness after the independent was set.

        ``editor.rows[independent_row_index].thickness`` is assumed already set.
        Mutates the dependent row's thickness in place; does NOT retrace.
        """
        obj_row = self.object_thickness_row()
        img_row = self.image_thickness_row()
        if obj_row is None or img_row is None or obj_row == img_row:
            return False, ""
        independent_row_index = int(independent_row_index)
        if independent_row_index == obj_row:
            target, dep_row, dep_q, ind_q = "image", img_row, IMAGE_THICKNESS, OBJECT_THICKNESS
        elif independent_row_index == img_row:
            target, dep_row, dep_q, ind_q = "object", obj_row, OBJECT_THICKNESS, IMAGE_THICKNESS
        else:
            return False, ""  # an internal lens gap -- not a conjugate quantity
        # interacting with a thickness promotes it to independent.
        self.set_role(ind_q, ROLE_INDEPENDENT)
        if self._roles.get(dep_q) == ROLE_CONSTANT:
            return False, f"{LABELS[dep_q]} pinned Constant -- image left unfocused."
        try:
            result = self.editor._compute_paraxial_solve_result(target)
        except Exception as exc:  # pragma: no cover - defensive
            return False, f"Quick Estimation solve failed: {exc}"
        solved = result.get("solved_distance")
        try:
            solved = float(solved)
        except (TypeError, ValueError):
            return False, "Quick Estimation: no finite conjugate solution."
        if not np.isfinite(solved) or solved <= 1e-6:
            return False, "Quick Estimation: conjugate out of range (near focal point)."
        self.editor.rows[dep_row].thickness = float(solved)
        return True, f"{LABELS[dep_q]} solved -> {solved:.6g} mm for focus."

    def preview_state(self, independent_row_index: int, pending_value: float) -> dict[str, Any] | None:
        """Conjugate state for a *pending* (uncommitted) thickness drag.

        Sets the independent gap to ``pending_value``, solves the dependent,
        reads the resulting state, then restores the committed thicknesses so
        nothing is mutated. Used for live drag feedback before release.
        """
        obj_row = self.object_thickness_row()
        img_row = self.image_thickness_row()
        if obj_row is None or img_row is None or obj_row == img_row:
            return None
        independent_row_index = int(independent_row_index)
        if independent_row_index not in (obj_row, img_row):
            return None
        rows = self.editor.rows
        saved = {obj_row: float(rows[obj_row].thickness), img_row: float(rows[img_row].thickness)}
        try:
            rows[independent_row_index].thickness = float(pending_value)
            ok, _note = self.solve_dependent(independent_row_index)
            if not ok:
                return None
            return self.current_state()
        except Exception:
            return None
        finally:
            for row_idx, value in saved.items():
                try:
                    rows[row_idx].thickness = value
                except Exception:
                    pass

    # --------------------------------------------------------------- readout
    def _sensor_semi(self) -> float | None:
        rows = getattr(self.editor, "rows", None) or []
        if not rows:
            return None
        try:
            diameter = float(getattr(rows[-1], "diameter", 0.0) or 0.0)
        except Exception:
            return None
        return diameter / 2.0 if diameter > 0 else None

    def _paraxial_solution(self):
        try:
            return self.editor._exact_paraxial_solution_for_rows(self.editor.rows)
        except Exception:
            return None

    def focal_length(self) -> float | None:
        sol = self._paraxial_solution()
        if sol is None:
            return None
        try:
            f = float(sol[4])
        except (TypeError, ValueError, IndexError):
            return None
        return f if np.isfinite(f) and abs(f) > 1e-9 else None

    def working_distance(self) -> float | None:
        rows = getattr(self.editor, "rows", None) or []
        if not rows:
            return None
        try:
            return float(rows[0].thickness)
        except Exception:
            return None

    def is_forbidden(self) -> tuple[bool, str]:
        """A finite object inside the front focal point gives no real image."""
        sol = self._paraxial_solution()
        wd = self.working_distance()
        f = self.focal_length()
        if sol is None or wd is None or f is None or f <= 0:
            return False, ""
        try:
            ppa = float(sol[5])
        except (TypeError, ValueError, IndexError):
            ppa = 0.0
        # object distance from the front principal plane must exceed f.
        object_principal = wd + ppa
        if object_principal <= f * (1.0 + 1e-6):
            return True, f"Working distance below focal length ({wd:.4g} < {f:.4g} mm) -- no real image."
        return False, ""

    def forbidden_for_object_distance(self, object_distance: float) -> bool:
        """Would this object distance put the object inside the front focal point
        (no real image)? Used for live drag feedback before committing."""
        sol = self._paraxial_solution()
        f = self.focal_length()
        if sol is None or f is None or f <= 0:
            return False
        try:
            ppa = float(sol[5])
            return (float(object_distance) + ppa) <= f * (1.0 + 1e-6)
        except (TypeError, ValueError, IndexError):
            return False

    def set_target_fov(self, object_semi: float | None) -> None:
        # Snapshot the current object extent (target, else the FOV that fills the
        # sensor) as "previous" so the overlay can ghost the before/after change.
        try:
            current_extent = self._target_object_semi
            if not current_extent:
                st = self.current_state()
                current_extent = st.get("fov_semi")
            if current_extent and current_extent > 0:
                self._previous_object_semi = float(current_extent)
        except Exception:
            pass
        if object_semi is None:
            self._target_object_semi = None
            return
        try:
            value = float(object_semi)
            self._target_object_semi = value if value > 0 else None
        except (TypeError, ValueError):
            self._target_object_semi = None

    def target_object_semi(self) -> float | None:
        return self._target_object_semi

    def previous_object_semi(self) -> float | None:
        return self._previous_object_semi

    def snap_to_fov(self, object_semi: float | None = None) -> tuple[bool, str]:
        """Set both gaps to the unique conjugate pair that images an object of
        semi-height ``object_semi`` to fill the sensor, in focus. No retrace."""
        target = object_semi if object_semi is not None else self._target_object_semi
        sensor = self._sensor_semi()
        if not sensor:
            return False, "No sensor (Image semi-height) available."
        if not target or target <= 0:
            return False, "Set a positive target Object Height first."
        sol = self._paraxial_solution()
        if sol is None:
            return False, "No paraxial solution."
        try:
            f = float(sol[4]); ppa = float(sol[5]); ppp = float(sol[6])
        except (TypeError, ValueError, IndexError):
            return False, "No valid lens solution."
        if not np.isfinite(f) or abs(f) < 1e-9:
            return False, "No valid focal length."
        mag = sensor / float(target)  # required |m|
        if mag <= 1e-9:
            return False, "Target Object Height too large for this sensor."
        object_distance = f * (1.0 + 1.0 / mag) - ppa
        image_distance = f * (1.0 + mag) + ppp
        if not (np.isfinite(object_distance) and np.isfinite(image_distance)
                and object_distance > 1e-6 and image_distance > 1e-6):
            return False, "No real-image conjugate for that Object Height."
        obj_row = self.object_thickness_row()
        img_row = self.image_thickness_row()
        if obj_row is None or img_row is None:
            return False, "Layout has no object/image gap."
        self.editor.rows[obj_row].thickness = float(object_distance)
        self.editor.rows[img_row].thickness = float(image_distance)
        return True, (
            f"Snapped to FOV {2 * float(target):.6g} mm: object {object_distance:.6g} mm, "
            f"image {image_distance:.6g} mm (|m|={mag:.4g})."
        )

    def recommended_sensor(self, aspect: tuple[float, float] = SENSOR_ASPECT) -> dict[str, Any] | None:
        """The rectangular sensor whose diagonal matches the image footprint of
        the object being imaged (the target Object Height, else the current FOV).

        Returns image-circle diameter, recommended sensor width/height/diagonal
        for ``aspect``, and the nearest standard format -- so the user can size /
        source a camera that the image circle perfectly covers.
        """
        try:
            mag = self.editor._current_finite_paraxial_magnification()
        except Exception:
            mag = None
        if mag is None or not np.isfinite(mag) or abs(mag) < 1e-9:
            return None
        sensor = self._sensor_semi()
        if not sensor:
            return None
        fov_semi = sensor / abs(mag)
        object_semi = self._target_object_semi if self._target_object_semi else fov_semi
        image_radius = abs(mag) * float(object_semi)  # image footprint of that object
        if not np.isfinite(image_radius) or image_radius <= 0:
            return None
        diagonal = 2.0 * image_radius
        aw, ah = float(aspect[0]), float(aspect[1])
        norm = (aw * aw + ah * ah) ** 0.5 or 1.0
        width = diagonal * aw / norm
        height = diagonal * ah / norm
        fmt, fmt_diag = _nearest_sensor_format(diagonal)
        return {
            "image_circle_diameter": diagonal,
            "diagonal": diagonal,
            "width": width,
            "height": height,
            "aspect": (aw, ah),
            "format": fmt,
            "format_diagonal": fmt_diag,
            "image_radius": image_radius,
            "current_sensor_semi": sensor,
        }

    def current_state(self) -> dict[str, Any]:
        rows = getattr(self.editor, "rows", None) or []
        state: dict[str, Any] = {
            "object_distance": None,
            "image_distance": None,
            "magnification": None,
            "sensor_semi": self._sensor_semi(),
            "fov_semi": None,
            "fov_full": None,
            "in_focus": None,
            "object_mode": None,
            "focal_length": self.focal_length(),
            "working_distance": self.working_distance(),
            "forbidden": False,
            "forbidden_reason": "",
            "target_object_semi": self._target_object_semi,
            "fill_factor": None,
        }
        forbidden, reason = self.is_forbidden()
        state["forbidden"] = forbidden
        state["forbidden_reason"] = reason
        if len(rows) < 3:
            return state
        try:
            state["object_mode"] = self.editor._current_object_mode()
            state["object_distance"] = float(rows[0].thickness)
            state["image_distance"] = float(self.editor._current_image_distance())
        except Exception:
            return state
        try:
            mag = self.editor._current_finite_paraxial_magnification()
        except Exception:
            mag = None
        state["magnification"] = float(mag) if mag is not None and np.isfinite(mag) else None
        sensor = state["sensor_semi"]
        if state["magnification"] and abs(state["magnification"]) > 1e-9 and sensor:
            state["fov_semi"] = sensor / abs(state["magnification"])
            state["fov_full"] = 2.0 * state["fov_semi"]
            # fill factor of the target object on the sensor: target / FOV.
            if self._target_object_semi and state["fov_semi"]:
                state["fill_factor"] = float(self._target_object_semi) / float(state["fov_semi"])
        state["recommended_sensor"] = self.recommended_sensor()
        # in-focus: does the conjugate solve reproduce the current image gap?
        try:
            result = self.editor._compute_paraxial_solve_result("image")
            solved = float(result.get("solved_distance"))
            img = state["image_distance"]
            if img is not None and np.isfinite(solved):
                state["in_focus"] = bool(abs(solved - img) <= max(0.05, 1e-3 * abs(img)))
        except Exception:
            pass
        return state

    def format_readout(self, state: dict[str, Any] | None = None) -> dict[str, str]:
        """Human-readable strings for the panel, keyed by quantity + metrics."""
        if state is None:
            state = self.current_state()
        out: dict[str, str] = {}

        def _mm(value: Any) -> str:
            try:
                return f"{float(value):.6g} mm"
            except (TypeError, ValueError):
                return "--"

        obj = state.get("object_distance")
        img = state.get("image_distance")
        out[OBJECT_PLANE] = f"[{self.role(OBJECT_PLANE)}]"
        out[OBJECT_THICKNESS] = f"{_mm(obj)}  [{self.role(OBJECT_THICKNESS)}]"
        out[IMAGE_THICKNESS] = f"{_mm(img)}  [{self.role(IMAGE_THICKNESS)}]"
        out[IMAGE_PLANE] = f"[{self.role(IMAGE_PLANE)}] (sensor)"

        mag = state.get("magnification")
        out["magnification"] = f"{mag:+.4g}x" if mag is not None else "--"
        out["sensor"] = _mm(state.get("sensor_semi")) + " (semi)" if state.get("sensor_semi") else "--"
        out["focal_length"] = _mm(state.get("focal_length"))
        out["working_distance"] = _mm(state.get("working_distance"))
        fov_semi = state.get("fov_semi")
        fov_full = state.get("fov_full")
        if fov_semi is not None:
            out["fov"] = f"{fov_semi:.6g} mm semi / {fov_full:.6g} mm full"
        else:
            out["fov"] = "--"
        target = state.get("target_object_semi")
        fill = state.get("fill_factor")
        if target:
            tline = f"{2 * float(target):.6g} mm full"
            if fill is not None:
                pct = 100.0 * float(fill)
                tag = "fills" if abs(pct - 100.0) < 1.0 else ("OVERFILLS" if pct > 100.0 else "underfills")
                tline += f" -> {pct:.1f}% ({tag})"
            out["target_fov"] = tline
        else:
            out["target_fov"] = "(fills sensor)"
        rec = state.get("recommended_sensor")
        if rec:
            out["recommended_sensor"] = (
                f"{rec['width']:.3g}×{rec['height']:.3g} mm (Ø{rec['diagonal']:.3g}, "
                f"~{rec['format']}) — image circle Ø{rec['image_circle_diameter']:.3g} mm"
            )
        else:
            out["recommended_sensor"] = "--"
        if state.get("forbidden"):
            out["focus"] = "FORBIDDEN: " + (state.get("forbidden_reason") or "no real image")
        else:
            focus = state.get("in_focus")
            out["focus"] = "in focus" if focus else ("out of focus" if focus is False else "--")
        return out

    def update_readout(self, state: dict[str, Any] | None = None) -> None:
        """Push a state (current, or a supplied preview) into the readout vars."""
        vars_map = getattr(self.inspector, "_quick_estimation_readout_vars", None)
        if not isinstance(vars_map, dict):
            return
        try:
            text = self.format_readout(state)
        except Exception:
            return
        for key, var in vars_map.items():
            try:
                var.set(text.get(key, "--"))
            except Exception:
                pass
