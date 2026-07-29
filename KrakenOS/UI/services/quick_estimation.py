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


# ----------------------------------------------------------------- design solve
# "What lens do I need?" -- invert the finite-conjugate relations for the FOCAL
# LENGTH given a set of pinned first-order constraints (design mode). Unlike the
# placement solve (fixed lens, 1 DOF, _conjugate_pair forward), design mode treats
# the lens as UNKNOWN, so it is a THIN-LENS first-order target (principal planes
# ppa = ppp = 0, since they belong to a lens not yet chosen) and the answer is
# advisory -- "pick a ~73 mm EFL". The conjugate geometry is 2 DOF:
#
#     s_o = f (1 + 1/m)      s_i = f (1 + m)      T = s_o + s_i      (m = |mag| > 0)
#
# determined by a "magnification" constraint (magnification OR object FOV via the
# fixed sensor) plus a "scale" constraint (one of object/image distance or total
# track); or by two length constraints (which jointly fix m AND the scale).
DESIGN_OBJECT_DISTANCE = "object_distance"
DESIGN_IMAGE_DISTANCE = "image_distance"
DESIGN_MAGNIFICATION = "magnification"
DESIGN_TOTAL_TRACK = "total_track"
DESIGN_OBJECT_FOV_SEMI = "object_fov_semi"
DESIGN_QUANTITIES = (
    DESIGN_OBJECT_DISTANCE,
    DESIGN_IMAGE_DISTANCE,
    DESIGN_MAGNIFICATION,
    DESIGN_TOTAL_TRACK,
    DESIGN_OBJECT_FOV_SEMI,
)
_DESIGN_LENGTHS = (DESIGN_OBJECT_DISTANCE, DESIGN_IMAGE_DISTANCE, DESIGN_TOTAL_TRACK)
DESIGN_FOCAL_LENGTH = "focal_length"


def _coerce_design_pins(pins: Any) -> dict[str, float]:
    out: dict[str, float] = {}
    if not isinstance(pins, dict):
        return out
    for q in DESIGN_QUANTITIES:
        if q not in pins:
            continue
        try:
            v = float(pins[q])
        except (TypeError, ValueError):
            continue
        if np.isfinite(v):
            out[q] = v
    return out


def resolve_design_system(pins: Any, sensor_semi: Any = None, *, rel_tol: float = 1e-4) -> dict[str, Any]:
    """Solve the thin-lens first-order system for the FOCAL LENGTH from a set of
    pinned constraints (design mode -- "what lens do I need?").

    ``pins`` -- ``{quantity: value}`` over ``DESIGN_QUANTITIES`` (magnitudes;
    ``magnification`` is ``|m| > 0``). ``sensor_semi`` -- terminal image-circle
    radius (mm); needed only to fold an ``object_fov_semi`` pin into a
    magnification.

    Returns a dict with ``status`` in {"balanced", "under", "over", "invalid"} and
    a ``message``; when ``balanced`` it also carries ``focal_length``,
    ``object_distance``, ``image_distance``, ``magnification``, ``total_track`` and
    (if a sensor is known) ``object_fov_semi``. The DOF accountant (under/over) is
    the same code path as the solve, so the UI's "balanced / pin one more / release
    one" indicator and the computed lens never disagree.
    """
    p = _coerce_design_pins(pins)
    try:
        sensor_semi = float(sensor_semi) if sensor_semi is not None else None
    except (TypeError, ValueError):
        sensor_semi = None

    def fail(status: str, message: str) -> dict[str, Any]:
        return {"status": status, "message": message}

    # 1) fold an object-FOV pin into a magnification (needs the fixed sensor).
    mag = p.get(DESIGN_MAGNIFICATION)
    if mag is not None and mag <= 0:
        return fail("invalid", "Magnification must be > 0.")
    if DESIGN_OBJECT_FOV_SEMI in p:
        fov = p[DESIGN_OBJECT_FOV_SEMI]
        if fov <= 0:
            return fail("invalid", "Object FOV must be > 0.")
        if sensor_semi is None or sensor_semi <= 0:
            return fail("invalid", "Object FOV needs a sensor size to set magnification.")
        mag_fov = sensor_semi / fov
        if mag is not None and abs(mag - mag_fov) > rel_tol * max(mag, mag_fov, 1.0):
            return fail("over", "Magnification and Object FOV conflict -- pin only one.")
        mag = mag_fov
    has_m = mag is not None

    lengths = [q for q in _DESIGN_LENGTHS if q in p]
    n_len = len(lengths)

    # 2) DOF accounting (design = 2 DOF: a magnification constraint + a scale one).
    if has_m:
        if n_len == 0:
            return fail("under", "Pin a distance (object or image) or the total track.")
        if n_len >= 2:
            return fail("over", "Too many lengths -- with a magnification, pin exactly one length.")
    else:
        if n_len < 2:
            return fail("under", "Pin two of {object distance, image distance, total track}, or a magnification + one length.")
        if n_len > 2:
            return fail("over", "Three lengths over-constrain the system -- release one.")

    # 3) solve thin-lens (ppa = ppp = 0).
    if has_m:
        m = float(mag)
        if DESIGN_OBJECT_DISTANCE in p:
            s_o = p[DESIGN_OBJECT_DISTANCE]; f = s_o * m / (m + 1.0); s_i = f * (1.0 + m)
        elif DESIGN_IMAGE_DISTANCE in p:
            s_i = p[DESIGN_IMAGE_DISTANCE]; f = s_i / (1.0 + m); s_o = f * (1.0 + 1.0 / m)
        else:  # total_track + m
            tt = p[DESIGN_TOTAL_TRACK]; f = tt / (2.0 + m + 1.0 / m); s_o = f * (1.0 + 1.0 / m); s_i = f * (1.0 + m)
    else:
        if DESIGN_OBJECT_DISTANCE in p and DESIGN_IMAGE_DISTANCE in p:
            s_o = p[DESIGN_OBJECT_DISTANCE]; s_i = p[DESIGN_IMAGE_DISTANCE]
        elif DESIGN_OBJECT_DISTANCE in p and DESIGN_TOTAL_TRACK in p:
            s_o = p[DESIGN_OBJECT_DISTANCE]; s_i = p[DESIGN_TOTAL_TRACK] - s_o
        else:  # image_distance + total_track
            s_i = p[DESIGN_IMAGE_DISTANCE]; s_o = p[DESIGN_TOTAL_TRACK] - s_i
        if s_o <= 1e-9 or s_i <= 1e-9:
            return fail("invalid", "Those lengths give a non-physical conjugate (check the total track).")
        m = s_i / s_o
        f = s_i / (1.0 + m)

    if not (np.isfinite(f) and f > 1e-9 and s_o > 1e-9 and s_i > 1e-9 and m > 1e-9):
        return fail("invalid", "No real-image solution for those constraints.")

    total_track = s_o + s_i
    result: dict[str, Any] = {
        "status": "balanced",
        "message": (
            f"Need EFL ~ {f:.4g} mm  (object {s_o:.4g} mm, image {s_i:.4g} mm, "
            f"|m| {m:.4g}, track {total_track:.4g} mm)."
        ),
        DESIGN_FOCAL_LENGTH: float(f),
        DESIGN_OBJECT_DISTANCE: float(s_o),
        DESIGN_IMAGE_DISTANCE: float(s_i),
        DESIGN_MAGNIFICATION: float(m),
        DESIGN_TOTAL_TRACK: float(total_track),
    }
    if sensor_semi is not None and sensor_semi > 0:
        result[DESIGN_OBJECT_FOV_SEMI] = sensor_semi / m
    return result


def design_quantity_states(pins: Any, sensor_semi: Any = None) -> dict[str, dict[str, Any]]:
    """Per-quantity checkbox state for the design dialog, so the UI can GRAY OUT
    the constraints the user can no longer change once enough are pinned.

    For each ``DESIGN_QUANTITIES`` entry returns ``{"state": ...}`` where state is:

    * ``"pinned"``   -- the user fixed it (carries ``value``);
    * ``"locked"``   -- determined by the current pins, so it must NOT be pinned
      (grayed). When the system is balanced it carries the solved ``value`` to show
      as the result; it is also locked when its magnification twin is pinned
      (magnification and object FOV are the SAME degree of freedom), or when the
      pins already over-constrain;
    * ``"available"`` -- still free to pin (its checkbox stays enabled).
    """
    p = _coerce_design_pins(pins)
    res = resolve_design_system(p, sensor_semi=sensor_semi)
    status = res.get("status")
    settled = status in ("balanced", "over")  # no further pins should be added
    twin = {
        DESIGN_MAGNIFICATION: DESIGN_OBJECT_FOV_SEMI,
        DESIGN_OBJECT_FOV_SEMI: DESIGN_MAGNIFICATION,
    }
    states: dict[str, dict[str, Any]] = {}
    for q in DESIGN_QUANTITIES:
        if q in p:
            states[q] = {"state": "pinned", "value": p[q]}
        elif settled:
            entry: dict[str, Any] = {"state": "locked"}
            if status == "balanced" and q in res:
                entry["value"] = res[q]
            states[q] = entry
        elif q in twin and twin[q] in p:
            # magnification and object FOV are one DOF -- pinning one locks the other.
            states[q] = {"state": "locked"}
        else:
            states[q] = {"state": "available"}
    return states


# -------------------------------------------------------------- placement solve
# Placement mode: the lens is FIXED (known focal length + real cardinal points), so
# the conjugate is 1 DOF -- pin ONE of {object distance, image distance, magnification,
# object FOV} and the rest are determined AND in focus. Unlike design mode this uses the
# lens's real ppa/ppp (not thin-lens), and Apply is focus-consistent with no lens swap.
# Total track is NOT a placement pin (with the lens fixed a track has two conjugate
# positions -- ambiguous); it is an output only.
_PLACEMENT_PINNABLE = (
    DESIGN_OBJECT_DISTANCE,
    DESIGN_IMAGE_DISTANCE,
    DESIGN_MAGNIFICATION,
    DESIGN_OBJECT_FOV_SEMI,
)


def resolve_placement_system(
    pins: Any, *, focal_length: Any, ppa: float = 0.0, ppp: float = 0.0,
    sensor_semi: Any = None, rel_tol: float = 1e-4,
) -> dict[str, Any]:
    """Solve the FIXED-lens (placement) first-order system from a single pinned
    constraint. ``focal_length``/``ppa``/``ppp`` are the lens cardinals (real, not
    thin-lens). Returns the same dict shape as ``resolve_design_system``; the solved
    conjugates are in focus for this lens. 1 DOF -> exactly one pin balances."""
    try:
        f = float(focal_length)
    except (TypeError, ValueError):
        f = float("nan")
    if not np.isfinite(f) or abs(f) < 1e-9:
        return {"status": "invalid", "message": "No focal length -- load or define a lens first."}
    try:
        ppa = float(ppa); ppp = float(ppp)
    except (TypeError, ValueError):
        ppa = ppp = 0.0
    p = _coerce_design_pins(pins)
    try:
        sensor_semi = float(sensor_semi) if sensor_semi is not None else None
    except (TypeError, ValueError):
        sensor_semi = None

    def fail(status: str, message: str) -> dict[str, Any]:
        return {"status": status, "message": message}

    if DESIGN_TOTAL_TRACK in p:
        return fail("over", "Total track is not a placement pin (lens fixed) -- pin object/image distance, magnification or FOV.")
    mag = p.get(DESIGN_MAGNIFICATION)
    if mag is not None and mag <= 0:
        return fail("invalid", "Magnification must be > 0.")
    if DESIGN_OBJECT_FOV_SEMI in p:
        fov = p[DESIGN_OBJECT_FOV_SEMI]
        if fov <= 0:
            return fail("invalid", "Object FOV must be > 0.")
        if sensor_semi is None or sensor_semi <= 0:
            return fail("invalid", "Object FOV needs a sensor size to set magnification.")
        mag_fov = sensor_semi / fov
        if mag is not None and abs(mag - mag_fov) > rel_tol * max(mag, mag_fov, 1.0):
            return fail("over", "Magnification and Object FOV conflict -- pin only one.")
        mag = mag_fov
    has_m = mag is not None

    lengths = [q for q in (DESIGN_OBJECT_DISTANCE, DESIGN_IMAGE_DISTANCE) if q in p]
    n = (1 if has_m else 0) + len(lengths)
    if n == 0:
        return fail("under", "Pin one: object distance, image distance, magnification or FOV.")
    if n > 1:
        return fail("over", "The lens is fixed (1 DOF) -- pin exactly one constraint.")

    if has_m:
        m = float(mag)
    elif DESIGN_OBJECT_DISTANCE in p:
        denom = p[DESIGN_OBJECT_DISTANCE] + ppa - f
        if denom <= 1e-9:
            return fail("invalid", "Object is inside the front focal point -- no real image.")
        m = f / denom
    else:  # image_distance
        m = (p[DESIGN_IMAGE_DISTANCE] - ppp - f) / f
        if m <= 1e-9:
            return fail("invalid", "Image is inside the rear focal point -- no real image.")

    s_o = f * (1.0 + 1.0 / m) - ppa
    s_i = f * (1.0 + m) + ppp
    if not (np.isfinite(s_o) and np.isfinite(s_i) and s_o > 1e-9 and s_i > 1e-9 and m > 1e-9):
        return fail("invalid", "No real-image conjugate for that constraint.")
    total_track = s_o + s_i
    result: dict[str, Any] = {
        "status": "balanced",
        "message": (
            f"Object {s_o:.4g} / image {s_i:.4g} mm at |m| {m:.4g}  "
            f"(EFL {f:.4g}, track {total_track:.4g} mm)."
        ),
        DESIGN_OBJECT_DISTANCE: float(s_o),
        DESIGN_IMAGE_DISTANCE: float(s_i),
        DESIGN_MAGNIFICATION: float(m),
        DESIGN_TOTAL_TRACK: float(total_track),
        DESIGN_FOCAL_LENGTH: float(f),
    }
    if sensor_semi is not None and sensor_semi > 0:
        result[DESIGN_OBJECT_FOV_SEMI] = sensor_semi / m
    return result


def placement_quantity_states(
    pins: Any, *, focal_length: Any, ppa: float = 0.0, ppp: float = 0.0, sensor_semi: Any = None,
) -> dict[str, dict[str, Any]]:
    """Per-quantity checkbox state for the placement dialog (1 DOF). Total track is
    always ``locked`` (an output, never a placement pin); pinning one constraint locks
    the rest. Mirrors ``design_quantity_states`` but for the fixed-lens 1-DOF system."""
    p = _coerce_design_pins(pins)
    res = resolve_placement_system(
        p, focal_length=focal_length, ppa=ppa, ppp=ppp, sensor_semi=sensor_semi
    )
    status = res.get("status")
    settled = status in ("balanced", "over")
    twin = {DESIGN_MAGNIFICATION: DESIGN_OBJECT_FOV_SEMI, DESIGN_OBJECT_FOV_SEMI: DESIGN_MAGNIFICATION}
    states: dict[str, dict[str, Any]] = {}
    for q in DESIGN_QUANTITIES:
        if q == DESIGN_TOTAL_TRACK:
            entry: dict[str, Any] = {"state": "locked"}
            if status == "balanced" and q in res:
                entry["value"] = res[q]
            states[q] = entry
        elif q in p:
            states[q] = {"state": "pinned", "value": p[q]}
        elif settled:
            entry = {"state": "locked"}
            if status == "balanced" and q in res:
                entry["value"] = res[q]
            states[q] = entry
        elif q in twin and twin[q] in p:
            states[q] = {"state": "locked"}
        else:
            states[q] = {"state": "available"}
    return states


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

    # -------------------------------------------------------- design solve (EFL)
    def solve_design(self, pins: dict[str, Any]) -> dict[str, Any]:
        """Design-mode "what lens do I need?": invert the first-order system for the
        focal length from the pinned constraints. Reads the (vendor-fixed) sensor
        semi-height from the layout so an object-FOV pin folds to a magnification.
        Advisory only -- returns the required EFL + conjugates, does NOT mutate the
        layout (the lens isn't chosen yet). See module ``resolve_design_system``.
        """
        return resolve_design_system(pins, sensor_semi=self._sensor_semi())

    def design_constraint_view(self, pins: dict[str, Any]) -> dict[str, Any]:
        """One call for the design-constraint panel: per-quantity checkbox
        ``states`` (so the UI grays the spent-DOF constraints) plus the solve
        ``result`` (the advisory EFL + conjugates), both with the vendor sensor
        semi-height injected. Pure/read-only -- never mutates the layout."""
        sensor_semi = self._sensor_semi()
        return {
            "states": design_quantity_states(pins, sensor_semi=sensor_semi),
            "result": resolve_design_system(pins, sensor_semi=sensor_semi),
        }

    def apply_design(self, pins: dict[str, Any]) -> tuple[bool, str]:
        """Apply a balanced design solve to the LAYOUT: write the solved object and
        image distances into the conjugate gaps so the 3D/2D update -- not just a text
        readout. The EFL stays advisory (you cannot change an existing lens's focal
        length; fit a lens of the reported EFL for focus). Mutates rows in place; the
        caller owns history + retrace (mirrors the FOV solve)."""
        result = resolve_design_system(pins, sensor_semi=self._sensor_semi())
        if result.get("status") != "balanced":
            return False, result.get("message", "Design constraints are not solvable yet.")
        obj_row = self.object_thickness_row()
        img_row = self.image_thickness_row()
        if obj_row is None or img_row is None or obj_row == img_row:
            return False, "Layout has no object/image gap to apply to."
        try:
            obj_distance = float(result[DESIGN_OBJECT_DISTANCE])
            img_distance = float(result[DESIGN_IMAGE_DISTANCE])
            focal = float(result[DESIGN_FOCAL_LENGTH])
        except (KeyError, TypeError, ValueError):
            return False, "Design solve produced no finite conjugates."
        if not (np.isfinite(obj_distance) and np.isfinite(img_distance) and obj_distance > 0 and img_distance > 0):
            return False, "Design solve produced a non-physical conjugate."
        self.editor.rows[obj_row].thickness = obj_distance
        self.editor.rows[img_row].thickness = img_distance
        return True, (
            f"Applied object {obj_distance:.4g} / image {img_distance:.4g} mm -- "
            f"fit a ~{focal:.4g} mm EFL lens for focus."
        )

    # ------------------------------------------------------ placement solve (fixed lens)
    def _placement_lens_cardinals(self):
        """(f, ppa, ppp) of the live fixed lens, or None when there is no clean
        first-order form (e.g. a beam splitter with no paraxial reference)."""
        sol = self._paraxial_solution()
        if sol is None:
            return None
        try:
            f = float(sol[4]); ppa = float(sol[5]); ppp = float(sol[6])
        except (TypeError, ValueError, IndexError):
            return None
        if not np.isfinite(f) or abs(f) < 1e-9:
            return None
        return f, ppa, ppp

    def placement_constraint_view(self, pins: dict[str, Any]) -> dict[str, Any]:
        """One call for the placement panel/popups: per-quantity ``states`` + the solve
        ``result`` for the FIXED lens (1 DOF). Read-only; never mutates the layout."""
        cardinals = self._placement_lens_cardinals()
        sensor_semi = self._sensor_semi()
        if cardinals is None:
            states = {q: {"state": "available"} for q in DESIGN_QUANTITIES}
            return {"states": states, "result": {"status": "invalid", "message": "No focal length -- load or define a lens first."}}
        f, ppa, ppp = cardinals
        return {
            "states": placement_quantity_states(pins, focal_length=f, ppa=ppa, ppp=ppp, sensor_semi=sensor_semi),
            "result": resolve_placement_system(pins, focal_length=f, ppa=ppa, ppp=ppp, sensor_semi=sensor_semi),
        }

    def apply_placement(self, pins: dict[str, Any]) -> tuple[bool, str]:
        """Apply a balanced placement solve to the LAYOUT: write the solved object/image
        distances into the conjugate gaps. The lens is FIXED so the result is in focus --
        no lens swap. Mutates rows in place; the caller owns history + retrace."""
        cardinals = self._placement_lens_cardinals()
        if cardinals is None:
            return False, "No focal length -- load or define a lens first."
        f, ppa, ppp = cardinals
        result = resolve_placement_system(pins, focal_length=f, ppa=ppa, ppp=ppp, sensor_semi=self._sensor_semi())
        if result.get("status") != "balanced":
            return False, result.get("message", "Placement constraint is not solvable yet.")
        obj_row = self.object_thickness_row()
        img_row = self.image_thickness_row()
        if obj_row is None or img_row is None or obj_row == img_row:
            return False, "Layout has no object/image gap to apply to."
        try:
            obj_distance = float(result[DESIGN_OBJECT_DISTANCE])
            img_distance = float(result[DESIGN_IMAGE_DISTANCE])
            mag = float(result[DESIGN_MAGNIFICATION])
        except (KeyError, TypeError, ValueError):
            return False, "Placement solve produced no finite conjugates."
        self.editor.rows[obj_row].thickness = obj_distance
        self.editor.rows[img_row].thickness = img_distance
        return True, f"Placed object {obj_distance:.4g} / image {img_distance:.4g} mm at |m|={mag:.4g} (in focus)."

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
            rows = self.editor.rows
            solve_rows = rows
            # bugs/0106: a beam splitter / promoted mesh solid has no clean
            # sequential paraxial form, so _exact_paraxial_solution_for_rows
            # throws on the raw rows -> focal length, the conjugate solve and
            # is_forbidden all return None, and the FOV "Solve for Thickness"
            # silently fails ("no real-image conjugate") on a splitter scene.
            # Straighten to the transmissive (straight-through) reference -- the
            # same one the 0104 magnification fix and every other first-order
            # consumer use -- so the single imaging arm's solve succeeds.
            if self.editor._layout_needs_paraxial_reference(rows):
                solve_rows, _last_source_index = self.editor._paraxial_reference_rows_for_layout(rows)
            return self.editor._exact_paraxial_solution_for_rows(solve_rows)
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

    def set_target_fov_rect(
        self, width: Any, height: Any, aspect: tuple[float, float] | None = None
    ) -> tuple[bool, str, float, float]:
        """Store the target object FOV from an explicit Width x Height rectangle --
        the two-box "Set Target FOV" dialog, mirroring the canvas double-click popup's
        'Solve for Thickness' mapping (``fov_solve`` object/thickness above). Either
        side may be blank: the other is derived from ``aspect`` (default the live
        sensor shape). The rectangle's DIAGONAL becomes the disk-model target
        semi-height ``snap_to_fov`` uses, so a square 23.04 sensor takes 19.5 x 19.5
        -> snap fills 19.5 x 19.5 (not the 13.8 the old image-circle-diameter single
        box produced -- bugs/0154). No conjugate move -- the panel's Snap to FOV
        button owns that. Returns ``(ok, message, width, height)``."""
        if aspect is None:
            aspect = self.sensor_active_dimensions()
        wh = self._sensor_wh(width, height, aspect)
        if wh is None:
            return False, "Enter a positive FOV width or height.", 0.0, 0.0
        w, h, diagonal = wh
        self.set_target_fov(diagonal / 2.0)
        return True, f"Target FOV {w:.6g} x {h:.6g} mm", w, h

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
            f"Snapped to FOV {self.diagonal_to_height(2 * float(target)):.6g} mm: "
            f"object {object_distance:.6g} mm, "
            f"image {image_distance:.6g} mm (|m|={mag:.4g})."
        )

    # ----------------------------------------------- click-on-plane FOV solve
    # The FOV/sensor here is modelled as a circle (semi-height = radius,
    # ``diameter`` = the image circle), so a *horizontal* field width only
    # differs from the diameter once an aspect is assumed. Track the LIVE sensor
    # the 3D view draws -- a registered camera's vendor sensor (e.g. a square
    # 23.04x23.04 sets horizontal/diagonal = 1/sqrt2) -- falling back to the
    # working machine-vision 4:3 (-> 0.8) only when no sensor is known.
    def _aspect_horizontal_fraction(self) -> float:
        dims = self.sensor_active_dimensions()
        if dims:
            w, h = dims
            diag = (float(w) * float(w) + float(h) * float(h)) ** 0.5
            if diag > 1e-9 and float(w) > 1e-9:
                return float(w) / diag
        aw, ah = SENSOR_ASPECT
        norm = (aw * aw + ah * ah) ** 0.5 or 1.0
        return float(aw) / norm

    def horizontal_to_diagonal(self, horizontal: float) -> float:
        frac = self._aspect_horizontal_fraction()
        return float(horizontal) / frac if frac > 1e-9 else float(horizontal)

    def diagonal_to_horizontal(self, diagonal: float) -> float:
        return float(diagonal) * self._aspect_horizontal_fraction()

    def _aspect_vertical_fraction(self) -> float:
        """Sensor HEIGHT / diagonal for the live sensor (a square 23.04 -> 1/sqrt2),
        falling back to the 4:3 working sensor (-> 0.6) only when none is known.
        The vertical mirror of ``_aspect_horizontal_fraction`` -- so a typed object
        *side* (the canvas + popup speak in Height) maps to the image-circle diagonal
        the disk model and ``snap_to_fov`` use."""
        dims = self.sensor_active_dimensions()
        if dims:
            w, h = dims
            diag = (float(w) * float(w) + float(h) * float(h)) ** 0.5
            if diag > 1e-9 and float(h) > 1e-9:
                return float(h) / diag
        aw, ah = SENSOR_ASPECT
        norm = (aw * aw + ah * ah) ** 0.5 or 1.0
        return float(ah) / norm

    def height_to_diagonal(self, height: float) -> float:
        frac = self._aspect_vertical_fraction()
        return float(height) / frac if frac > 1e-9 else float(height)

    def diagonal_to_height(self, diagonal: float) -> float:
        return float(diagonal) * self._aspect_vertical_fraction()

    def object_fov_horizontal(self) -> float | None:
        """Current object-side field width (horizontal, mm), or None."""
        fov_full = self.current_state().get("fov_full")  # object-side image-circle Ø
        if fov_full and fov_full > 0:
            return self.diagonal_to_horizontal(float(fov_full))
        return None

    def sensor_horizontal(self) -> float | None:
        """Current sensor/image width (horizontal, mm), or None."""
        semi = self._sensor_semi()
        if semi and semi > 0:
            return self.diagonal_to_horizontal(2.0 * float(semi))
        return None

    def _finite_mag(self) -> float | None:
        try:
            mag = self.editor._current_finite_paraxial_magnification()
        except Exception:
            return None
        if mag is None or not np.isfinite(mag) or abs(mag) < 1e-9:
            return None
        return float(mag)

    def _image_gap_collision_floor(self) -> float:
        """bugs/0468: the smallest image gap that does not drive the sensor into the fold mirror.

        The manual leg split already refuses to cross this floor ("Safe gap: mirror -> sensor
        must stay >= N mm so the mirror does not collide"), and it is measured from the mirror
        CENTRE -- half the mirror row's own along-axis extent sits on the sensor side of it. The
        FOV solve wrote its solved image distance straight into the row and never consulted the
        floor, so a large field could seat the sensor INSIDE the mirror: 35 x 35 on the user's
        scene solved to a 9.53 mm gap against a 12.5 mm floor. Returns 0.0 when the scene has no
        fold mirror to collide with.
        """
        try:
            split = self.editor._folded_image_conjugate_split()
        except Exception:
            return 0.0
        if not isinstance(split, dict):
            return 0.0
        try:
            return max(0.0, float(split.get("far_min", 0.0) or 0.0))
        except Exception:
            return 0.0

    def _resolve_image_gap_collision(self, image_distance):
        """bugs/0468: keep the sensor off the fold mirror by SLIDING THE MIRROR, not by refusing.

        The optics fixes the TOTAL lens->sensor distance; how that total splits between
        ``lens rear -> mirror`` and ``mirror -> sensor`` is a free mechanical choice -- which is
        exactly what the manual leg split exists to let the user set. So when a solved field
        would seat the sensor inside the mirror, move the MIRROR toward the lens by the deficit
        and give that length to the sensor leg. The conjugate is untouched (the two legs sum to
        the same total), and the collision is gone.

        Returns ``(new_image_gap, near_gap_row, near_gap_delta, note)`` or ``None`` when nothing
        needs doing. Raises no exception; returns a refusal string as ``note`` only when even the
        redistribution cannot fit (the lens->mirror leg would go negative).
        """
        floor = self._image_gap_collision_floor()
        try:
            gap = float(image_distance)
        except Exception:
            return None
        if floor <= 0.0 or gap >= floor - 1.0e-6:
            return None
        try:
            split = self.editor._folded_image_conjugate_split()
            near_row = int(split["near_gap_row"])
            near_min = float(split.get("near_min", 0.0) or 0.0)
            near_now = float(self.editor.rows[near_row].thickness)
        except Exception:
            return (None, None, 0.0, (
                f"That field needs a {gap:.4g} mm mirror->sensor gap, below the {floor:.4g} mm "
                "collision floor, and the lens->mirror leg could not be read to compensate."
            ))
        deficit = float(floor) - gap
        near_new = near_now - deficit
        if near_new < near_min - 1.0e-6:
            return (None, None, 0.0, (
                f"That field needs a {gap:.4g} mm mirror->sensor gap (floor {floor:.4g} mm), and "
                f"sliding the mirror to make room would leave only {near_new:.4g} mm from the "
                f"lens (minimum {near_min:.4g} mm). Use a smaller field."
            ))
        return (
            float(floor),
            near_row,
            -deficit,
            (
                f" Mirror slid {deficit:.4g} mm toward the lens so the sensor clears it "
                f"(lens->mirror {near_new:.4g} mm, mirror->sensor {floor:.4g} mm)."
            ),
        )

    def _largest_feasible_object_semi(self, requested_semi: float, image_semi: float):
        """bugs/0466: the largest object semi-height that still has a REAL conjugate.

        Bisection on ``_conjugate_pair`` -- cheap (it is closed-form paraxial), and it turns
        a bare refusal into a number the user can act on. Returns None when even a tiny
        object fails (then the scene, not the size, is the problem) or when the request
        already works."""
        try:
            requested = float(requested_semi)
            image = float(image_semi)
            if not (requested > 0.0):
                return None
            if self._conjugate_pair(requested, image) is not None:
                return None
        except Exception:
            return None
        feasible = None
        probe = requested * 0.5
        for _ in range(40):
            if probe <= 1.0e-6:
                break
            try:
                if self._conjugate_pair(probe, image) is not None:
                    feasible = probe
                    break
            except Exception:
                pass
            probe *= 0.5
        if feasible is None:
            return None
        lo, hi = feasible, requested
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            try:
                ok = self._conjugate_pair(mid, image) is not None
            except Exception:
                ok = False
            if ok:
                lo = mid
            else:
                hi = mid
        return lo

    def _conjugate_pair(self, object_semi: Any, image_semi: Any):
        """``(object_distance, image_distance, |m|)`` imaging ``object_semi`` to
        ``image_semi`` in focus, or None when there is no real-image conjugate."""
        try:
            object_semi = float(object_semi)
            image_semi = float(image_semi)
        except (TypeError, ValueError):
            return None
        if object_semi <= 0 or image_semi <= 0:
            return None
        sol = self._paraxial_solution()
        if sol is None:
            return None
        try:
            f = float(sol[4]); ppa = float(sol[5]); ppp = float(sol[6])
        except (TypeError, ValueError, IndexError):
            return None
        if not np.isfinite(f) or abs(f) < 1e-9:
            return None
        mag = image_semi / object_semi
        if mag <= 1e-9:
            return None
        object_distance = f * (1.0 + 1.0 / mag) - ppa
        image_distance = f * (1.0 + mag) + ppp
        if not (np.isfinite(object_distance) and np.isfinite(image_distance)
                and object_distance > 1e-6 and image_distance > 1e-6):
            return None
        return object_distance, image_distance, mag

    def _object_locked_redirect_row(self, obj_row: int | None) -> int | None:
        """When a glued LED + a promoted optical solid sit right after the object gap, the LED+BS is
        a FIXED illumination constraint that must be EXCLUDED from QE. Return the first air gap AFTER
        that solid -- the lens gap QE should vary instead of the object gap -- or None when not in
        that locked configuration."""
        if obj_row is None:
            return None
        rows = getattr(self.editor, "rows", None) or []
        solid = int(obj_row) + 1
        if not (0 <= solid < len(rows)):
            return None
        advanced = getattr(rows[solid], "advanced", None) or {}
        if not isinstance(advanced, dict) or not (
            advanced.get("OpticalSolidFaces") or advanced.get("Solid_3d_stl")
        ):
            return None  # the row after the object gap isn't a promoted solid
        # bugs/0453 (flag_20260727_132644 "BS Cube detached from the LED STEP after changing
        # FOV"): the trigger USED to require the ``_optical_led_glued`` bool. That was only
        # ever reliable by accident -- before bugs/0449 the settings service could not write
        # the editor's ``_optical_led_glued`` (the delegation trap), so a stale runtime True
        # kept this firing; once 0449 made the flag restore correctly to the saved False, the
        # redirect stopped, the FOV thickness solve started writing the object gap, and the
        # promoted BS slid away from its LED body (which is anchored separately). The
        # illumination unit is defined by TOPOLOGY, not the bool: a promoted solid sitting
        # immediately after the object gap in a scene that has imported an LED STEP body IS
        # the coaxial LED+BS unit (glued or not), so hold the object gap and move the lens
        # for it too.
        led_present = False
        try:
            led_present = self.editor._step_path_for_label("led") is not None
        except Exception:
            led_present = False
        if not (bool(getattr(self.editor, "_optical_led_glued", False)) or led_present):
            return None
        cand = solid + 1
        if not (0 <= cand < len(rows) - 1):
            return None  # need a non-terminal air gap to absorb the change
        glass = str(getattr(rows[cand], "glass", "") or "").strip().upper()
        if glass not in ("", "AIR"):
            return None  # solid cemented to the next element -- no air gap to move the lens into
        return cand

    def _folded_conjugate_spill_row(self, primary_row: int, side: str) -> "int | None":
        """The fold leg that ABSORBS overflow when the primary conjugate gap row can't hold the
        whole distance correction: the sibling (far) leg of ``side``'s fold, so the correction
        slides the mirror instead of failing. None when there is no fold split, or its near leg
        is not the primary row (so the far row can't be trusted as the sibling)."""
        try:
            if side == "object":
                split = self.editor._folded_object_conjugate_split()
            else:
                split = self.editor._folded_image_conjugate_split()
        except Exception:
            return None
        if not isinstance(split, dict):
            return None
        if int(split.get("near_gap_row", -1)) != int(primary_row):
            return None
        far = int(split.get("far_gap_row", -1))
        return far if (far >= 0 and far != int(primary_row)) else None

    def _distribute_folded_gap_delta(self, rows, primary_row, delta, spill_row):
        """Apply ``delta`` (a change to a folded conjugate's leg TOTAL) to ``rows[primary_row]``.
        If that drives the primary leg negative, spill the overflow onto ``spill_row`` (the fold's
        other leg -- i.e. slide the mirror). Returns a list of ``(row, applied_delta)`` to write,
        preserving the total, or None if even the two legs together can't absorb it (truly out of
        range). Both legs are floored at 0; the collision floor is enforced by the constraint
        split that runs after the conjugate solve."""
        new_primary = float(rows[primary_row].thickness) + float(delta)
        if new_primary >= 0.0:
            return [(int(primary_row), float(delta))]
        if spill_row is None or not (0 <= int(spill_row) < len(rows)):
            return None
        if float(rows[int(spill_row)].thickness) + new_primary < 0.0:
            return None
        # primary gives up all it has (-> 0); the negative remainder lands on the sibling leg
        return [(int(primary_row), -float(rows[primary_row].thickness)), (int(spill_row), new_primary)]

    def _apply_conjugate_pair(self, object_semi: Any, image_semi: Any) -> tuple[bool, str]:
        # Folded-aware branch (feature): a promoted RA-mirror fold breaks the plain object/image
        # gap-row assumption -- object_thickness_row/image_thickness_row land on the mirror-adjacent
        # legs, and the whole-system principal planes are inflated by the flattened mirror plates
        # (ppp ~ -196 mm), so the plain _conjugate_pair yields a NEGATIVE image distance and the
        # FOV solve silently no-ops on a periscope. Solve against the LENS-only first order and
        # write the solved distances into the true folded object/image gap TOTALS.
        try:
            os_f, is_f = float(object_semi), float(image_semi)
        except (TypeError, ValueError):
            os_f = is_f = 0.0
        if os_f > 0 and is_f > 0:
            folded = self.editor._folded_conjugate_gaps_for_magnification(is_f / os_f)
            if folded is not None:
                rows = getattr(self.editor, "rows", None) or []
                og, ig = int(folded["object_gap_row"]), int(folded["image_gap_row"])
                if not (0 <= og < len(rows) and 0 <= ig < len(rows)):
                    return False, "Folded conjugate gap rows are unavailable."
                # bugs/0314: the object/image distance correction is a change to the leg TOTAL,
                # not to one row. A prior fold-leg constraint (a Solve pinning "object -> mirror")
                # can have drained the primary gap row, so dumping the whole delta on it alone
                # underflows and the solve silently no-ops -- even though the far leg has ample
                # room. Spill any overflow onto the fold's OTHER leg (slide the mirror), exactly
                # what the old error told the user to do by hand.
                obj_changes = self._distribute_folded_gap_delta(
                    rows, og, float(folded["object_delta"]),
                    self._folded_conjugate_spill_row(og, "object"),
                )
                img_changes = self._distribute_folded_gap_delta(
                    rows, ig, float(folded["image_delta"]),
                    self._folded_conjugate_spill_row(ig, "image"),
                )
                if obj_changes is None or img_changes is None:
                    return False, (
                        "FOV out of range on the folded arms (the object or image leg would go "
                        "negative -- slide the fold mirrors first)."
                    )
                changes = obj_changes + img_changes
                for row_index, applied in changes:
                    rows[row_index].thickness = float(rows[row_index].thickness) + applied
                # bugs/0236: the image-leg delta extends the beam along the first fold's
                # reflected direction, but a free-placed trailing mirror is pinned along
                # global +Z -- carry it (and any free-placed camera) back onto the beam.
                from KrakenOS.UI.nonseq_output_ports import carry_free_placed_followers_after_fold
                carry_free_placed_followers_after_fold(rows, changes)
                return True, (
                    f"Solved (folded): object->lens {folded['object_distance']:.6g} mm, "
                    f"lens->sensor {folded['image_distance']:.6g} mm (|m|={folded['magnitude']:.4g})."
                )
        pair = self._conjugate_pair(object_semi, image_semi)
        if pair is None:
            # bugs/0466: "No real-image conjugate" is TRUE but useless -- the user asked for
            # 55 x 55 mm, got this, and reported "Solve for Thickness. Nothing happen."
            # (flag_20260729_132816). The refusal is correct: on that scene the image gap
            # shrinks as the object grows (35 x 35 -> 9.5 mm left) and runs out around
            # 40 x 40, past which the sensor would have to sit inside the fold mirror. Say
            # so, and say what DOES fit, so the number is actionable instead of a dead end.
            limit_semi = self._largest_feasible_object_semi(object_semi, image_semi)
            if limit_semi:
                # Report it as a FRACTION of what was asked for. ``object_semi`` is a
                # semi-DIAGONAL, but the user types SIDES into the FOV box (55 x 55 became
                # 77.78 here), so quoting the raw number would answer a question nobody
                # asked. A percentage is exact in either convention.
                fraction = float(limit_semi) / float(object_semi)
                return False, (
                    "That field is beyond this lens's range on the current sensor -- the "
                    "image distance would go negative (the sensor would sit inside the "
                    f"optics). The largest field it can image is about "
                    f"{fraction * 100.0:.0f}% of the size you entered."
                )
            return False, "No real-image conjugate for that size (near the focal point?)."
        object_distance, image_distance, mag = pair
        obj_row = self.object_thickness_row()
        img_row = self.image_thickness_row()
        if obj_row is None or img_row is None:
            return False, "Layout has no object/image gap."
        # A glued LED+BS at the object side is a FIXED illumination constraint (kept as close to the
        # object as the machine allows, for uniform illumination) -- it must be EXCLUDED from Quick
        # Estimation (flag_20260628_212404). Instead of writing the object gap (which moves the unit
        # and detaches the LED from the BS), redirect the object-distance change to the gap AFTER the
        # solid: that MOVES THE LENS by the same delta, so object->lens + lens->detector -- the whole
        # conjugate, hence focus + FOV -- are identical, but the LED+BS stays put.
        lens_gap = self._object_locked_redirect_row(obj_row)
        if lens_gap is not None:
            try:
                delta = float(object_distance) - float(self.editor.rows[obj_row].thickness)
                new_lens = float(self.editor.rows[lens_gap].thickness) + delta
            except Exception:
                new_lens = -1.0
            if np.isfinite(new_lens) and new_lens >= 0.0:
                self.editor.rows[lens_gap].thickness = new_lens
                self.editor.rows[img_row].thickness = float(image_distance)
                return True, (
                    f"Solved (LED+BS held fixed): moved the lens {delta:+.4g} mm, "
                    f"image {image_distance:.6g} mm (|m|={mag:.4g})."
                )
            return False, (
                "FOV needs the lens nearer than the glued LED+BS allows (object unit is locked at "
                "its minimum). Unglue the LED or relax the FOV."
            )
        _collision_note = ""
        _resolved = self._resolve_image_gap_collision(image_distance)
        if _resolved is not None:
            _new_gap, _near_row, _near_delta, _note = _resolved
            if _new_gap is None:
                return False, _note
            self.editor.rows[_near_row].thickness = (
                float(self.editor.rows[_near_row].thickness) + float(_near_delta)
            )
            image_distance = _new_gap
            _collision_note = _note
        self.editor.rows[obj_row].thickness = float(object_distance)
        self.editor.rows[img_row].thickness = float(image_distance)
        return True, (
            f"Solved thickness: object {object_distance:.6g} mm, "
            f"image {image_distance:.6g} mm (|m|={mag:.4g})."
            f"{_collision_note}"
        )

    def apply_sensor_diagonal(self, diagonal: Any, horizontal: float | None = None) -> tuple[bool, str]:
        """Resize the terminal sensor to ``diagonal`` (image-circle Ø). No retrace."""
        rows = getattr(self.editor, "rows", None) or []
        if not rows:
            return False, "No layout to size a sensor on."
        try:
            diagonal = float(diagonal)
        except (TypeError, ValueError):
            return False, "Sensor size must be a number."
        if not np.isfinite(diagonal) or diagonal <= 0:
            return False, "Sensor size must be positive."
        rows[-1].diameter = float(diagonal)
        if horizontal is None:
            horizontal = self.diagonal_to_horizontal(diagonal)
        return True, (
            f"Sensor set to {float(horizontal):.6g} mm wide "
            f"(image circle Ø{diagonal:.6g} mm)."
        )

    def _terminal_detector_advanced(self, create: bool = False):
        """The terminal (sensor) row's ``advanced['Detector']`` dict, optionally
        creating it. That dict holds the rectangular ``active_width_mm`` /
        ``active_height_mm`` the detector overlay draws."""
        rows = getattr(self.editor, "rows", None) or []
        if not rows:
            return None
        row = rows[-1]
        advanced = getattr(row, "advanced", None)
        if not isinstance(advanced, dict):
            if not create:
                return None
            advanced = {}
            try:
                row.advanced = advanced
            except Exception:
                return None
        det = advanced.get("Detector")
        if not isinstance(det, dict):
            if not create:
                return None
            det = {}
            advanced["Detector"] = det
        return det

    def _live_sensor_active_dimensions(self) -> tuple[float, float] | None:
        """The terminal sensor ``(width, height)`` the 3D canvas actually draws.

        Mirrors ``scene_builder``'s precedence exactly: explicit rectangular
        detector dims on the terminal row first, then the registered camera's
        vendor sensor (the ``_camera_detector_active_dims_overrides`` the
        detector overlay blends to -- e.g. a square 23.04x23.04). None when
        neither is set -- the caller then folds the circular aperture."""
        det = self._terminal_detector_advanced(create=False) or {}
        try:
            width = float(det.get("active_width_mm", 0.0) or 0.0)
            height = float(det.get("active_height_mm", 0.0) or 0.0)
        except (TypeError, ValueError):
            width = height = 0.0
        if width > 0 and height > 0:
            return width, height
        try:
            overrides = self.editor._camera_detector_active_dims_overrides()
        except Exception:
            overrides = None
        if overrides:
            rows = getattr(self.editor, "rows", None) or []
            dims = overrides.get(len(rows) - 1)
            try:
                if dims and float(dims[0]) > 0 and float(dims[1]) > 0:
                    return float(dims[0]), float(dims[1])
            except (TypeError, ValueError, IndexError):
                pass
        return None

    def sensor_active_dimensions(self) -> tuple[float, float] | None:
        """Current sensor ``(width, height)`` in mm for the image popup prefill.

        Prefers the live sensor the 3D view draws -- the registered camera's
        vendor sensor (e.g. a square 23.04x23.04), else explicit rectangular
        detector dims. Only when neither is set does it fall back to a 4:3
        rectangle derived from the circular image-circle diameter."""
        live = self._live_sensor_active_dimensions()
        if live is not None:
            return live
        semi = self._sensor_semi()
        if not semi or semi <= 0:
            return None
        diagonal = 2.0 * float(semi)
        aw, ah = SENSOR_ASPECT
        norm = (aw * aw + ah * ah) ** 0.5 or 1.0
        return diagonal * aw / norm, diagonal * ah / norm

    def object_fov_dimensions(self) -> tuple[float, float] | None:
        """Current object field ``(width, height)`` in mm for the object popup
        prefill. The object field that maps onto the sensor is the sensor
        rectangle divided by the magnification; falls back to a 4:3 rectangle
        derived from the circular object FOV diagonal."""
        mag = self._finite_mag()
        sensor_wh = self.sensor_active_dimensions()
        if mag is not None and sensor_wh is not None:
            sw, sh = sensor_wh
            m = abs(mag)
            if m > 1e-9 and sw > 0 and sh > 0:
                return sw / m, sh / m
        fov_full = self.current_state().get("fov_full")
        if fov_full and fov_full > 0:
            aw, ah = SENSOR_ASPECT
            norm = (aw * aw + ah * ah) ** 0.5 or 1.0
            return float(fov_full) * aw / norm, float(fov_full) * ah / norm
        return None

    def _sensor_wh(self, width: Any, height: Any, aspect: tuple[float, float] | None = None):
        """Normalise a sensor request to ``(width, height, diagonal)``.

        Either ``width`` or ``height`` may be omitted (None / blank / unparseable)
        and the missing side is derived from ``aspect`` (default 4:3), so the user
        can fill just one box and the other auto-completes. A value that *is*
        supplied but is non-positive / non-finite is rejected. Returns None when
        neither side is usable or a supplied value is invalid."""
        aw, ah = aspect if aspect else SENSOR_ASPECT
        try:
            aw = float(aw)
            ah = float(ah)
        except (TypeError, ValueError):
            aw, ah = SENSOR_ASPECT
        if not (np.isfinite(aw) and np.isfinite(ah) and aw > 0 and ah > 0):
            aw, ah = SENSOR_ASPECT

        def _parse(value):
            """Blank / unparseable -> 'missing' (derive it); a parseable but
            non-positive / non-finite number -> 'bad' (reject the whole request)."""
            if value is None:
                return "missing", None
            try:
                x = float(value)
            except (TypeError, ValueError):
                return "missing", None
            if not np.isfinite(x) or x <= 0:
                return "bad", None
            return "ok", x

        state_w, w = _parse(width)
        state_h, h = _parse(height)
        if state_w == "bad" or state_h == "bad":
            return None
        if w is None and h is None:
            return None
        if h is None:
            h = w * ah / aw
        elif w is None:
            w = h * aw / ah
        diagonal = (w * w + h * h) ** 0.5
        return w, h, diagonal

    def apply_sensor_rect(self, width: Any, height: Any) -> tuple[bool, str]:
        """Resize the terminal sensor to an explicit width x height (mm). Sets the
        circular optical aperture (image-circle Ø = the rectangle's diagonal) and
        the rectangular detector dims so the overlay reads as the real sensor. No
        retrace."""
        wh = self._sensor_wh(width, height)
        if wh is None:
            return False, "Sensor width and height must be positive numbers."
        w, h, diagonal = wh
        rows = getattr(self.editor, "rows", None) or []
        if not rows:
            return False, "No layout to size a sensor on."
        rows[-1].diameter = float(diagonal)
        det = self._terminal_detector_advanced(create=True)
        if det is not None:
            det["active_width_mm"] = float(w)
            det["active_height_mm"] = float(h)
        return True, (
            f"Sensor set to {w:.6g} x {h:.6g} mm (image circle Ø{diagonal:.6g} mm)."
        )

    def fov_solve(
        self,
        plane: str,
        mode: str,
        width: Any,
        height: Any = None,
        aspect: tuple[float, float] | None = None,
    ) -> tuple[bool, str]:
        """Drive the click-on-plane FOV popup.

        ``plane`` is "object" or "image"; ``mode`` is "thickness" (move the
        object/image conjugate pair) or "sensor" (resize the sensor). ``width`` /
        ``height`` are the typed field dimensions -- object-side for the object
        plane, image-side (sensor) for the image plane. Either one may be omitted
        (blank): the missing side is derived from ``aspect`` (the live sensor's
        width:height, default 4:3), so the user can fill just one box. The optical
        model is left in focus and the caller owns the retrace.
        """
        if plane == "object":
            wh = self._sensor_wh(width, height, aspect)
            if wh is None:
                return False, "Enter a positive FOV width or height."
            obj_w, obj_h, obj_diag = wh
            semi = obj_diag / 2.0
            if mode == "thickness":
                sensor = self._sensor_semi()
                if not sensor:
                    return False, "No sensor available to fill."
                ok, msg = self._apply_conjugate_pair(semi, float(sensor))
                if ok:
                    self.set_target_fov(semi)
                    msg = f"Object {obj_w:.6g} x {obj_h:.6g} mm fills the sensor. " + msg
                return ok, msg
            if mode == "sensor":
                mag = self._finite_mag()
                if mag is None:
                    return False, "No magnification to size the sensor."
                self.set_target_fov(semi)
                ok, msg = self.apply_sensor_rect(abs(mag) * obj_w, abs(mag) * obj_h)
                if ok:
                    msg = f"Object {obj_w:.6g} x {obj_h:.6g} mm at |m|={abs(mag):.4g}: " + msg
                return ok, msg
        elif plane == "image":
            wh = self._sensor_wh(width, height, aspect)
            if wh is None:
                return False, "Enter a positive sensor width or height."
            img_w, img_h, img_diag = wh
            if mode == "sensor":
                return self.apply_sensor_rect(img_w, img_h)
            if mode == "thickness":
                target = self._target_object_semi
                if not target:
                    target = self.current_state().get("fov_semi")
                if not target or target <= 0:
                    return False, "No object field set to image onto this sensor width."
                ok, msg = self._apply_conjugate_pair(float(target), img_diag / 2.0)
                if ok:
                    msg = (
                        f"Image {img_w:.6g} x {img_h:.6g} mm for the current object "
                        "field. " + msg
                    )
                return ok, msg
        return False, "Unknown FOV solve request."

    def recommended_sensor(self, aspect: tuple[float, float] | None = None) -> dict[str, Any] | None:
        """The rectangular sensor whose diagonal matches the image footprint of
        the object being imaged (the target Object Height, else the current FOV).

        Returns image-circle diameter, recommended sensor width/height/diagonal
        for ``aspect``, and the nearest standard format -- so the user can size /
        source a camera that the image circle perfectly covers. ``aspect`` defaults
        to the LIVE sensor shape (a registered square 23.04x23.04 -> a square
        recommendation), folding 4:3 only when no sensor shape is known (bugs/0154).
        """
        if aspect is None:
            aspect = self._live_sensor_active_dimensions() or SENSOR_ASPECT
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
        # When a real rectangular/square sensor is live (a registered camera or
        # explicit detector dims), report Sensor / FOV / Target in sensor-RECTANGLE
        # terms -- the Height the canvas + double-click popup show -- not the
        # image-circle DIAGONAL the internal disk model (current_state) keeps. The
        # "(Image H)" / "(Object H)" labels finally read true. No-camera (penta)
        # scenes keep the diagonal strings verbatim (bugs/0154).
        live_dims = self._live_sensor_active_dimensions()
        if live_dims is not None:
            sw, sh = live_dims
            out["sensor"] = f"{sh:.6g} mm (H) / {sw:.6g} mm (W)"
            mag_abs = abs(mag) if mag else None
            if mag_abs and mag_abs > 1e-9:
                fov_h = sh / mag_abs
                out["fov"] = f"{0.5 * fov_h:.6g} mm semi / {fov_h:.6g} mm full"
            if target:
                target_h = self.diagonal_to_height(2.0 * float(target))
                tline = f"{target_h:.6g} mm full"
                if fill is not None:
                    pct = 100.0 * float(fill)
                    tag = "fills" if abs(pct - 100.0) < 1.0 else ("OVERFILLS" if pct > 100.0 else "underfills")
                    tline += f" -> {pct:.1f}% ({tag})"
                out["target_fov"] = tline
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
