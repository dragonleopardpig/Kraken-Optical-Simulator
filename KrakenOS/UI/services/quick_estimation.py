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


def folded_m_correction(editor) -> float:
    """The measured/first-order magnification ratio for the editor's scene (bugs/0591): what
    the TRACED machine delivered against what the station-frame first order promised. 1.0
    when unmeasured; cleared on load and on lens/camera swaps. Module-level so DISPLAY
    readouts outside QuickEstimationService (flag_20260810_164247: the green object-plane
    "FOV a x b" coverage label showed 55*c = 49.8 from the RAW paraxial m after a solve
    deliberately booked the corrected conjugate) share the same delivered-truth view. The
    raw helper `_current_finite_paraxial_magnification` must STAY raw -- the solve's
    booking math and QuickEstimationService.current_state() apply this factor themselves,
    and correcting at the source would double it."""
    record = getattr(editor, "_folded_m_correction_state", None)
    try:
        value = float(record) if record is not None else 1.0
    except Exception:
        return 1.0
    return value if np.isfinite(value) and 0.1 < value < 10.0 else 1.0


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

    #: bugs/0482: assembly clearance left between the camera body and the fold mirror once the
    #: body's own reach is accounted for. Explicit, because the floor is a hard geometric limit and
    #: landing exactly ON it means the body grazes the substrate.
    #:
    #: bugs/0486: raised 1.0 -> 5.0 mm on the user's call. At 1 mm a 40 x 40 field left the camera
    #: body's bounding box only 3.04 mm from the mirror's -- clear, and ``camera_body_collisions()``
    #: agreed, but too close to read as safe ("+3.04 ... should crash already"). This is the single
    #: knob for how much daylight a large field keeps.
    IMAGE_LEG_ASSEMBLY_MARGIN_MM = 5.0

    def _camera_body_image_leg_reach_mm(self) -> float:
        """bugs/0482: how far back up the sensor leg the CAMERA BODY reaches, in mm.

        A camera STEP is bolted to its sensor and extends the vendor front-to-sensor distance
        UPSTREAM of it (the same number ``seat_camera_on_sensor`` places the body by, bugs/0220
        / 0471). That body, not the sensor plane, is what meets the fold mirror first. 0.0 when
        no camera STEP is imported -- then the sensor plane really is the leading edge.
        """
        try:
            if self.editor._step_path_for_label("camera") is None:
                return 0.0
        except Exception:
            return 0.0
        try:
            reach = float(self.editor._current_camera_front_to_sensor_mm())
        except Exception:
            return 0.0
        return reach if (np.isfinite(reach) and reach > 0.0) else 0.0

    def _image_gap_collision_floor(self) -> float:
        """bugs/0468: the smallest image gap that does not drive the sensor into the fold mirror.

        The manual leg split already refuses to cross this floor ("Safe gap: mirror -> sensor
        must stay >= N mm so the mirror does not collide"), and it is measured from the mirror
        CENTRE -- half the mirror row's own along-axis extent sits on the sensor side of it. The
        FOV solve wrote its solved image distance straight into the row and never consulted the
        floor, so a large field could seat the sensor INSIDE the mirror: 35 x 35 on the user's
        scene solved to a 9.53 mm gap against a 12.5 mm floor. Returns 0.0 when the scene has no
        fold mirror to collide with.

        bugs/0482: that floor protects the SENSOR PLANE, and the sensor plane is not the leading
        edge -- the camera BODY is, reaching ``front_to_sensor`` back up the leg. On the reported
        scene (flag_20260730_103719, "the sensor misplaced to RA mirror, the camera crash to RA
        mirror") a 30 x 30 field solved to an 18.86 mm gap. That clears the 12.5 mm sensor floor,
        so this resolver stood down -- and the body, needing 11.48 mm of the remaining 6.36 mm,
        ended 5.3 mm inside the prism. The floor now includes the body's reach plus an assembly
        margin, which is what "the camera should not crash the RA mirror" actually requires.
        """
        try:
            split = self.editor._folded_image_conjugate_split()
        except Exception:
            return 0.0
        if not isinstance(split, dict):
            return 0.0
        try:
            sensor_floor = max(0.0, float(split.get("far_min", 0.0) or 0.0))
        except Exception:
            return 0.0
        if sensor_floor <= 0.0:
            return 0.0
        reach = self._camera_body_image_leg_reach_mm()
        if reach <= 0.0:
            return sensor_floor
        return sensor_floor + reach + float(self.IMAGE_LEG_ASSEMBLY_MARGIN_MM)

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
            # bugs/0562: the lens->mirror leg is a SUM over its span -- `_folded_image_conjugate_split`
            # computes `near = sum(th[gap_start:mirror_row])` -- not the single row at
            # `mirror_row - 1`. Reading one row was safe only while that row was the lens Rear
            # Vertex Datum carrying the whole leg; bugs/0546 re-seats a promoted solid there with a
            # ZERO gap, so this read returned 0 while the real leg was 83.4 mm, and the resolver
            # concluded there was no room to slide the mirror. Symptom: "I can't even solve for FOV
            # 35x35 now" and a refusal quoting "would leave only -22.04 mm from the lens" -- that
            # -22.04 is exactly `0 - deficit`, the giveaway that the leg read as zero.
            near_now = float(split.get("near", self.editor.rows[near_row].thickness))
        except Exception:
            return (None, None, 0.0, (
                f"That field needs a {gap:.4g} mm mirror->sensor gap, below the {floor:.4g} mm "
                "collision floor, and the lens->mirror leg could not be read to compensate."
            ))
        deficit = float(floor) - gap
        near_new = near_now - deficit
        if near_new < near_min - 1.0e-6:
            # bugs/0561: state the MOVE, not just the target gap. The old wording quoted the
            # required mirror->sensor distance, which the user cannot relate to what they see --
            # "I see plenty of room from camera edge to mirror", and they were right: on the
            # flagged scene the camera's top face sat 25.7 mm clear of the mirror. What the
            # message failed to say is how far the sensor must TRAVEL to reach best focus
            # (49.90 -> 6.94 mm, i.e. ~43 mm toward the mirror) and that the camera body would
            # end up INSIDE the prism. Quote the travel and the resulting overlap so the refusal
            # is checkable against the picture.
            try:
                far_now = float(split.get("far", float("nan")))
            except Exception:
                far_now = float("nan")
            travel = ""
            if far_now == far_now:  # not NaN
                # NB this is the shortfall against the FLOOR, which carries a clearance margin
                # on top of the physical extents -- so it is stated as "past the clearance floor",
                # not as raw mesh overlap, which is smaller by that margin.
                shortfall = float(floor) - gap
                travel = (
                    f" That is {abs(far_now - gap):.4g} mm of sensor travel toward the mirror "
                    f"from the present {far_now:.4g} mm gap, ending {shortfall:.4g} mm past the "
                    f"clearance floor."
                )
            return (None, None, 0.0, (
                f"Best focus needs a {gap:.4g} mm mirror->sensor gap, below the {floor:.4g} mm "
                f"body-clearance floor (the mirror's own half-extent plus how far the camera "
                f"body reaches back behind its sensor).{travel} Sliding the mirror to compensate would "
                f"leave only {near_new:.4g} mm from the lens (minimum {near_min:.4g} mm), so the "
                "defocus cannot be removed at this field. Use a smaller field, or move the "
                "mirror further from the lens first."
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
        # bugs/0519 (flag_20260803_140636 "couldn't change FOV to 55x55"): on a 0433-FROZEN
        # fold the straightened reference's LAST VERTEX is the prism placeholder sitting ON
        # the image plane (its gap row is zero-length), so ``ppp ~ -(H2->image)`` and this
        # formula measures the new gap from a zero-length anchor -- it crossed zero at
        # m=0.546 and refused the solve ("the image distance would go negative") for a
        # sensor move of just -10.8 mm. Re-anchor the infeasible regime on the WORLD far
        # leg: H2 and the fold stay put through a conjugate change, so the sensor's world
        # move is exactly ``ds_i = f(1+m) - image_principal``, and the downstream writers
        # (the 0482 collision resolver + the 0478 frozen writer) already speak far-leg
        # world terms. The previously-working regime (old value positive) is untouched, as
        # is every unfrozen scene (no frozen split -> no re-anchor).
        if np.isfinite(image_distance) and image_distance <= 1e-6:
            try:
                split = self.editor._folded_image_conjugate_split()
            except Exception:
                split = None
            if isinstance(split, dict) and bool(split.get("frozen_world")):
                first = None
                try:
                    first = self.editor._shared_first_order_reference()
                except Exception:
                    first = None
                if isinstance(first, dict):
                    d_img = float(first["f"]) * (1.0 + mag) - float(first["image_principal"])
                    image_distance = float(split["far"]) + d_img
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

    @staticmethod
    def _row_is_station_neutral(row) -> bool:
        """bugs/0435: a promoted solid marked STATION-NEUTRAL spans no distance on the imaging
        axis -- its thickness is pinned at 0 and its body is placed absolutely. Its row index is
        not its geometry either (bugs/0546: a beam splitter glued to the LED routinely lands
        AFTER the lens block). So its thickness is not a gap and no solve may write to it: every
        station-fed consumer downstream -- the pinned mirror pose, the sequential Image, the
        camera glued to it -- moves by whatever is written there.

        bugs/0571: delegates to the ONE definition in ``paraxial_tools`` -- the leg walks there
        need the same predicate, and two copies would grow two behaviours."""
        from KrakenOS.UI.services.paraxial_tools import row_is_station_neutral

        return bool(row_is_station_neutral(row))

    def _gap_row_for_delta(self, rows, candidate) -> "int | None":
        """The nearest row AT OR BEFORE ``candidate`` whose thickness is a real axial gap.

        bugs/0569: the folded solve's ``image_gap_row`` says where the image distance is
        MEASURED from, and on the reported scene that is the promoted beam-splitter row --
        station-neutral, and physically upstream of the lens. Writing the leg correction there
        pushed the RA mirror and the sensor 54 mm along the chain, off the beam ("camera and RA
        mirror misplaced"). Walk back to a row that can actually hold a distance.
        """
        index = int(candidate)
        while 0 <= index < len(rows) and self._row_is_station_neutral(rows[index]):
            index -= 1
        return index if 0 <= index < len(rows) else None

    def _glued_illumination_unit_rows(self) -> "list[int]":
        """Rows whose bodies are the FIXED coaxial illumination unit -- the beam splitter glued
        into the LED housing (bugs/0570).

        ``_object_locked_redirect_row`` already knows this unit must not move when the object
        distance changes, but it finds it POSITIONALLY (the row right after the object gap).
        bugs/0546 established that a promoted solid's row index is not its geometry: on the
        user's scene the BS is glued to the LED, physically upstream of everything, and its row
        sits at index 6 -- after the whole lens block. So the redirect never fired, the object
        delta went into row 0, and every WORLD-placed row downstream slid with it while the LED
        body (an overlay at an absolute offset) stayed: *"the BS plate is shifted down. It
        happened after FOV solve"* -- measured, the plate left its housing by exactly the
        28.462 mm the object gap grew.

        Identified by MARKER instead: a promoted solid that is station-neutral (bugs/0435) or
        flagged a beam splitter, in a scene that has an LED body or the LED glue set.
        """
        rows = list(getattr(self.editor, "rows", None) or [])
        if not rows:
            return []
        led_present = False
        try:
            led_present = self.editor._step_path_for_label("led") is not None
        except Exception:
            led_present = False
        if not (led_present or bool(getattr(self.editor, "_optical_led_glued", False))):
            return []
        unit: list[int] = []
        for index, row in enumerate(rows):
            advanced = getattr(row, "advanced", None)
            promotion = advanced.get("StepOverlayPromotion") if isinstance(advanced, dict) else None
            if not isinstance(promotion, dict):
                continue
            if promotion.get("station_neutral") or promotion.get("beam_splitter"):
                unit.append(index)
        return unit

    def _hold_glued_illumination_unit(self, rows, delta: float) -> "list[int]":
        """Keep the glued LED+BS unit at its world pose across an object-gap write of ``delta``.

        A WORLD-placed row's pose is ``station + desp_z`` (bugs/0526), so when the object gap
        cannot be redirected -- the frozen row order puts the BS after the lens, where no single
        gap write can move the lens while holding the splitter -- the unit is held by taking the
        slide back out of its own placement.  Returns the rows it held.
        """
        try:
            shift = float(delta)
        except (TypeError, ValueError):
            return []
        if abs(shift) <= 1.0e-9:
            return []
        from KrakenOS.UI.services import row_placement

        held: list[int] = []
        for index in self._glued_illumination_unit_rows():
            if not (0 <= index < len(rows)):
                continue
            row = rows[index]
            # A promoted solid is ABSOLUTELY placed -- ``axis_move`` 0, pose = station + desp_z
            # (bugs/0546) -- whether or not it also carries a 0433 freeze breadcrumb, and that
            # is the whole condition for the compensation to be exact. Gating on the breadcrumb
            # alone missed the flagged scene's beam splitter, which carries none.
            absolutely_placed = abs(float(getattr(row, "axis_move", 0.0) or 0.0)) <= 1e-9
            if not (absolutely_placed or row_placement.is_world_placed(row)):
                continue
            try:
                row.desp_z = float(row.desp_z) - shift
            except Exception:
                continue
            held.append(int(index))
        if held:
            # bugs/0571: this compensation is only correct when the row's STATION moved by the
            # same amount in the same write. It is invisible otherwise -- say it out loud.
            try:
                self.editor.append_debug(
                    f"hold illumination unit: rows {held} desp_z -= {shift:+.4f} mm "
                    f"(object gap write)"
                )
            except Exception:
                pass
        return held

    def _folded_image_leg_write_row(self, measured_from_row) -> "int | None":
        """The row whose thickness IS the mirror->sensor leg -- the one a conjugate correction
        may stretch without moving anything but the sensor.

        bugs/0569: the solve's ``image_gap_row`` is where the image distance is MEASURED from
        (it walks back off the fold mirror so the distance runs from the last LENS surface).
        Writing there stretches the leg BEFORE the mirror instead, so the mirror -- and the
        camera glued behind it -- slide off the beam. The fold split already names the right
        row; fall back to the last gap before the Image, and only then to a walk-back.
        """
        rows = getattr(self.editor, "rows", None) or []
        if not rows:
            return None
        try:
            split = self.editor._folded_image_conjugate_split()
        except Exception:
            split = None
        if isinstance(split, dict):
            far = int(split.get("far_gap_row", -1))
            if 0 <= far < len(rows) and not self._row_is_station_neutral(rows[far]):
                return far
        last_gap = len(rows) - 2
        if 0 <= last_gap < len(rows) and not self._row_is_station_neutral(rows[last_gap]):
            return last_gap
        return self._gap_row_for_delta(rows, measured_from_row)

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
                # bugs/0569 (flag_20260806_074148, "swapped lens, changed FOV, solve for
                # thickness, camera and RA mirror misplaced"): on a FROZEN image-side fold the
                # sensor is placed in WORLD terms -- the gap row after the mirror runs backwards
                # (bugs/0478), and the row this branch would otherwise write is the one the
                # distance is measured FROM, not a leg that may be stretched. Move the sensor
                # along its own leg by the solved correction; the mirror stays exactly put.
                obj_row = self._gap_row_for_delta(rows, og)
                img_row_write = self._folded_image_leg_write_row(ig)
                if obj_row is None or img_row_write is None:
                    return False, "No usable object/image gap row for the folded solve."
                # bugs/0571 (flag_20260806_125028 "swapped lens, elements dislocate"): on a frozen
                # FOLD the object distance cannot be changed by writing rows[0].thickness. A row's
                # pose is station + desp_z, so that write slides every downstream WORLD row along
                # +Z -- and the lens, the fold mirror and the sensor live on the splitter's +X leg.
                # Measured: a 23x23 solve moved all three 28.462 mm off the leg and no ray reached
                # the sensor. Move the LENS along its own leg instead, with the bugs/0526
                # compensated write-through, which is the same composite a lens DRAG uses (the
                # user's principle: a drag and a solve are the same gesture from opposite ends).
                object_slid = None
                try:
                    object_slid = self.editor.slide_lens_block_along_its_leg(
                        float(folded["object_delta"])
                    )
                except Exception as exc:
                    self.editor.append_debug(f"lens leg slide unavailable: {exc}")
                    object_slid = None
                    # bugs/0588 review: an exception AFTER the slide cleared its refusal channel
                    # used to leave it EMPTY, so the honest-refusal return below was skipped and
                    # the full object delta fell to the raw station write -- the 0571 dislocation
                    # mechanism, through the back door. A crashed slide is a refusal.
                    if not str(self.editor.__dict__.get("_lens_leg_slide_refusal", "") or ""):
                        self.editor._lens_leg_slide_refusal = (
                            f"the lens-leg slide failed ({type(exc).__name__}: {exc}) -- "
                            f"nothing was moved."
                        )
                # bugs/0572 (the user's Apo75 -> PYRITE 85 experiment, 35x35 then 55x55): when the
                # slide is REFUSED there is no safe fallback on a fold leg. Writing the object gap
                # instead is precisely the bugs/0571 dislocation -- measured, the 55x55 solve
                # after a 35x35 one moved the lens block 73.9 mm ACROSS its leg (z 54.283 ->
                # 128.18) because the first solve had spent the lens-to-fold room.
                #
                # bugs/0573: and when the shortfall is only ROOM, make it -- the optics reach these
                # fields (image distance +25.4 mm at 35x35, +5.0 mm at 55x55 on that scene; the
                # ceiling is ~63.9 mm square), the MACHINE is too short. So lengthen it at the
                # fold: slide the fold mirror, everything behind it and the camera body along the
                # leg by the shortfall, then take the slide the solve actually asked for.
                arm_slid = None
                if object_slid is None and abs(float(folded["object_delta"])) > 1.0e-6:
                    shortfall = float(self.editor.__dict__.get("_lens_leg_slide_shortfall", 0.0) or 0.0)
                    if shortfall > 1.0e-6:
                        try:
                            arm_slid = self.editor.slide_fold_arm_along_leg(shortfall + 1.0)
                        except Exception as exc:
                            self.editor.append_debug(f"fold arm slide unavailable: {exc}")
                            arm_slid = None
                        if arm_slid is not None:
                            try:
                                object_slid = self.editor.slide_lens_block_along_its_leg(
                                    float(folded["object_delta"])
                                )
                            except Exception:
                                object_slid = None
                if object_slid is None and abs(float(folded["object_delta"])) > 1.0e-6:
                    refusal = str(self.editor.__dict__.get("_lens_leg_slide_refusal", "") or "")
                    if refusal:
                        return False, f"FOV out of range on this fold: {refusal}"
                # bugs/0575 (flag_20260806_182735, "rays defocus at sensor"): the image write has
                # to happen AFTER the object move, and it has to be re-measured once it has.
                #
                # ``image_delta`` is an absolute z correction in the shared first-order frame, and
                # _folded_conjugate_gaps_for_magnification's docstring calls it "invariant" under
                # the object move. That was true when the object move was ``rows[0].thickness +=
                # d``, which grows EVERY downstream station -- H' and the image plane together, so
                # the correction between them does not change. Since bugs/0571 the object move is
                # the compensated leg slide, which deliberately leaves rows past the lens block
                # untouched (``rows[downstream].thickness -= d`` cancels the growth): H' still
                # gains d, the sensor's station gains nothing, so the true correction is now
                # ``image_delta + d`` and the old number is short by exactly the slide. Measured:
                # the finisher's residual after the slide was +28.4622 mm, the slide to 4 dp.
                #
                # Rather than hardcode that coupling, re-solve the conjugate on the scene as it
                # now stands: the object is already placed, so the fresh object_delta comes back
                # ~0 and the fresh image_delta is exactly the remaining correction. Self-checking,
                # and it also absorbs whatever the bugs/0573 fold-arm slide did on the way here.
                if object_slid is not None or arm_slid is not None:
                    try:
                        refreshed = self.editor._folded_conjugate_gaps_for_magnification(is_f / os_f)
                    except Exception:
                        refreshed = None
                    if isinstance(refreshed, dict):
                        self.editor.append_debug(
                            "folded solve: image delta re-measured after the object move "
                            "{was:+.4f} -> {now:+.4f} mm (object delta left {left:+.4f})".format(
                                was=float(folded["image_delta"]),
                                now=float(refreshed["image_delta"]),
                                left=float(refreshed["object_delta"]),
                            )
                        )
                        folded = refreshed
                # bugs/0588 review (temporal hole, pre-existing): frozen_world is established
                # at gate time, but the writer re-reads the geometry AFTER the slides -- if that
                # mid-flight read fails it returns False with an EMPTY refusal, which the code
                # below used to read as "unfolded, do the plain write" and booked a large
                # negative delta into a BACKWARDS frozen gap row (bugs/0478). Snapshot the
                # frozen verdict here: a frozen scene whose image write comes back empty-refusal
                # DEFERS to the traced-focus finisher, never the raw write.
                frozen_at_entry = False
                try:
                    _split_now = self.editor._folded_image_conjugate_split()
                    frozen_at_entry = bool(
                        isinstance(_split_now, dict) and _split_now.get("frozen_world")
                    )
                except Exception:
                    frozen_at_entry = False
                image_handled = False
                try:
                    image_handled = bool(
                        self.editor.shift_image_distance_frozen_aware(float(folded["image_delta"]))
                    )
                except Exception:
                    image_handled = False
                # bugs/0575: a frozen fold that REFUSED must not fall through to the plain
                # prescription write below -- that write runs backwards on a frozen fold
                # (bugs/0478), so an impossible request came out as a full-strength move in the
                # wrong direction. On the user's Apo75 -> PYRITE scene the solve asked for a
                # -10.29 mm mirror->sensor leg, the writer correctly refused, and the fallback
                # then drove the sensor +42.94 mm the wrong way.
                #
                # But a hard refusal here would be refusing on the wrong number. The target comes
                # from _shared_first_order_reference, whose image_z is a STATION sum -- the very
                # frame bugs/0576 measured as not-this-scene on a frozen fold (it reported a 60 mm
                # defocus as 5.7e-16). So when the paraxial image target is out of reach, DEFER:
                # write nothing here and let the traced-focus finisher below place the sensor,
                # which it does in world off the rays that actually traced. That is also the
                # user's own principle -- pin the section, refocus at the sensor, and let the FOV
                # readout follow -- so the object slide sets the conjugate and focus does the rest.
                image_deferred = False
                if not image_handled:
                    image_refusal = str(
                        self.editor.__dict__.get("_frozen_image_write_refusal", "") or ""
                    )
                    if not image_refusal and frozen_at_entry:
                        # bugs/0588 review: the scene WAS frozen when this solve started, so an
                        # empty refusal here means the writer's mid-flight geometry read failed,
                        # not that the scene is unfolded. Defer -- the finisher places the
                        # sensor in world off the rays that actually traced.
                        image_refusal = (
                            "the frozen image geometry could not be re-read after the object "
                            "move (deferring the sensor to the traced focus)."
                        )
                    if image_refusal:
                        image_deferred = True
                        self.editor.append_debug(
                            "folded solve: paraxial image write deferred to the traced focus "
                            f"({image_refusal})"
                        )
                obj_changes = (
                    []
                    if object_slid is not None
                    else self._distribute_folded_gap_delta(
                        rows, obj_row, float(folded["object_delta"]),
                        self._folded_conjugate_spill_row(obj_row, "object"),
                    )
                )
                img_changes = (
                    []
                    if (image_handled or image_deferred)   # bugs/0575
                    else self._distribute_folded_gap_delta(
                        rows, img_row_write, float(folded["image_delta"]),
                        self._folded_conjugate_spill_row(img_row_write, "image"),
                    )
                )
                if obj_changes is None or img_changes is None:
                    return False, (
                        "FOV out of range on the folded arms (the object or image leg would go "
                        "negative -- slide the fold mirrors first)."
                    )
                changes = obj_changes + img_changes
                for row_index, applied in changes:
                    rows[row_index].thickness = float(rows[row_index].thickness) + applied
                # bugs/0570: the object write slides every WORLD-placed row downstream of it,
                # and the LED housing is NOT one of them (it is an overlay at an absolute
                # offset), so the beam splitter glued inside it walks out of its own housing.
                # The plain branch avoids this by redirecting the write; when the row order
                # makes that impossible, hold the unit in place instead.
                held_rows: list[int] = []
                if obj_row == 0 and self._object_locked_redirect_row(0) is None:
                    object_applied = sum(
                        float(applied) for row_index, applied in obj_changes if int(row_index) == 0
                    )
                    held_rows = self._hold_glued_illumination_unit(rows, object_applied)
                # bugs/0236: the image-leg delta extends the beam along the first fold's
                # reflected direction, but a free-placed trailing mirror is pinned along
                # global +Z -- carry it (and any free-placed camera) back onto the beam.
                from KrakenOS.UI.nonseq_output_ports import carry_free_placed_followers_after_fold
                carry_free_placed_followers_after_fold(rows, changes)
                # bugs/0569: the FOLDED branch returns early, so it never reached the bugs/0490
                # finisher the plain branch ends with -- the solve landed the PARAXIAL plane and
                # left the traced focus wherever the real-ray aberration and the BS/prism glass
                # paths put it. That is the "solve for FOV, ray still defocus at the sensor"
                # complaint (0567's flag), on the very branch a folded scene always takes.
                focus_note = ""
                try:
                    focus_note = str(self._finish_solve_on_traced_focus() or "")
                except Exception as exc:
                    focus_note = f" Focus snap skipped ({type(exc).__name__}: {exc})."
                # bugs/0573: a machine that had to be lengthened says so -- the fold mirror and
                # the camera really did move, and the user must know by how much.
                room_note = (
                    ""
                    if arm_slid is None
                    else (
                        f" Made room first: the fold mirror and the camera moved "
                        f"{float(arm_slid['distance']):+.4g} mm along the leg."
                    )
                )
                if image_deferred:
                    # bugs/0575: the object conjugate was written and the sensor was placed by
                    # FOCUS rather than by the paraxial target, so quoting the target's |m| would
                    # be quoting a number the scene does not have. Say what actually happened and
                    # let the FOV readout report the field that resulted.
                    return True, (
                        f"Solved (folded): object->lens {folded['object_distance']:.6g} mm. The "
                        f"paraxial sensor plane was out of this fold's reach, so the sensor was "
                        f"placed at the traced focus instead -- read the FOV box for the field "
                        f"that actually results.{room_note}{focus_note}"
                    )
                if image_handled:
                    # Report what was actually applied: on a frozen fold the image side is a
                    # WORLD move of the sensor, not the gap-row sum ``image_distance`` quotes.
                    # bugs/0578: and when the writer lengthened the machine to book the leg,
                    # say so -- the camera really moved.
                    image_room_note = str(
                        self.editor.__dict__.get("_frozen_image_make_room_note", "") or ""
                    )
                    return True, (
                        f"Solved (folded): object->lens {folded['object_distance']:.6g} mm; the "
                        f"sensor moved {float(folded['image_delta']):+.4g} mm along its folded leg "
                        f"(the fold mirror stayed put) (|m|={folded['magnitude']:.4g})."
                        f"{image_room_note}{room_note}{focus_note}"
                    )
                return True, (
                    f"Solved (folded): object->lens {folded['object_distance']:.6g} mm, "
                    f"lens->sensor {folded['image_distance']:.6g} mm "
                    f"(|m|={folded['magnitude']:.4g}).{room_note}{focus_note}"
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
        # bugs/0482: remember where the image leg was SPLIT before anything is written, so the
        # rebalance at the end can share the change between both sections from the real starting
        # point rather than from wherever the writes leave them.
        try:
            _pre_image_split = self.editor._folded_image_conjugate_split()
        except Exception:
            _pre_image_split = None
        # bugs/0484: and the object split, for the same reason -- section 1 must be restored to
        # where it was so the BS stays on its LED and section 2 takes the whole change. The
        # BS -> LED glue vector is captured HERE, before any write moves either of them.
        try:
            _pre_object_split = self.editor._folded_object_conjugate_split()
        except Exception:
            _pre_object_split = None
        _pre_led_offset = None
        try:
            if isinstance(_pre_object_split, dict):
                _bs0 = self.editor._promoted_solid_current_center(int(_pre_object_split["mirror_row"]))
                _led0 = self.editor._step_body_world_center("led")
                if _bs0 is not None and _led0 is not None:
                    _pre_led_offset = np.asarray(_led0, dtype=float) - np.asarray(_bs0, dtype=float)
        except Exception:
            _pre_led_offset = None
        _collision_note = ""
        _resolved = self._resolve_image_gap_collision(image_distance)
        if _resolved is not None:
            _new_gap, _near_row, _near_delta, _note = _resolved
            if _new_gap is None:
                return False, _note
            # bugs/0486: on a FROZEN fold a station thickness is not a distance ALONG the mirror's
            # incoming leg. Sliding the mirror by writing rows[near].thickness moves it down the
            # station axis (+z here) while its incoming leg runs +x, so the fold point leaves the
            # beam by exactly the slide -- measured, the 6.12 mm deficit at 30 x 30 became 6.12 mm
            # of off-axis error, and the emitted leg then drew slanted 3.39 deg ("RA mirror
            # shifted, not centered to optical axis, the fold axis also slanted",
            # flag_20260730_160140). A fold point is BY DEFINITION on the axis feeding it.
            #
            # The frozen writer slides along ``in_dir`` and re-seats the sensor and camera on the
            # exit leg (bugs/0447), which is why the MANUAL leg constraint has always been clean
            # (measured 0.0 deg off axis). Route the same slide through it. The raw thickness write
            # is kept for straight/unfrozen scenes, where a station IS along the beam.
            _frozen_slide = False
            if bool((_pre_image_split or {}).get("frozen_world")) and _near_row is not None:
                try:
                    _target_near = float(_pre_image_split["near"]) + float(_near_delta)
                    _slid_ok, _slid_msg = self.editor._apply_folded_image_split("near", _target_near)
                    _frozen_slide = bool(_slid_ok)
                    if not _slid_ok:
                        _note += f" (frozen slide refused: {_slid_msg})"
                except Exception as exc:
                    _note += f" (frozen slide failed: {type(exc).__name__}: {exc})"
            if not _frozen_slide:
                self.editor.rows[_near_row].thickness = (
                    float(self.editor.rows[_near_row].thickness) + float(_near_delta)
                )
            image_distance = _new_gap
            _collision_note = _note
        # Object side first: the prescription write shifts stations, and the frozen image write
        # below re-bakes world centres, so it has to run last (bugs/0447's ordering rule).
        self.editor.rows[obj_row].thickness = float(object_distance)
        # bugs/0478: on a FROZEN folded scene the image gap row is not a signed distance along
        # the beam -- the world leg runs as ``const - thickness``, so the plain write below
        # moves the sensor the wrong way and leaves the defocus it was solving for. The
        # frozen-aware path places the sensor in WORLD terms and carries the camera; it returns
        # False on any straight/unfrozen scene, which keeps the original behaviour there.
        _frozen_note = ""
        if self.editor.apply_image_distance_frozen_aware(image_distance):
            _frozen_note = " (frozen scene: sensor re-seated in world terms, camera carried)"
        else:
            self.editor.rows[img_row].thickness = float(image_distance)
        # bugs/0482: LAST, after the frozen write has re-baked world centres (0447's ordering
        # rule) -- share the image-leg change across BOTH sections instead of leaving all of it
        # on the sensor leg.
        _share_note = self._rebalance_image_leg_sections(_pre_image_split)
        # bugs/0484 LAST: restoring section 1 is a rigid repackaging of the frozen chain (the
        # writer keeps every element's own path length), so it runs once the image side has
        # settled -- otherwise the image re-bake would be computed against a chain that is about
        # to translate.
        _object_note = self._rebalance_object_leg_sections(_pre_object_split, _pre_led_offset)
        _focus_note = self._finish_solve_on_traced_focus()
        return True, (
            f"Solved thickness: object {object_distance:.6g} mm, "
            f"image {image_distance:.6g} mm (|m|={mag:.4g}).{_frozen_note}"
            f"{_collision_note}{_share_note}{_object_note}{_focus_note}"
        )

    def _finish_solve_on_traced_focus(self) -> str:
        """bugs/0490: land the solve on the TRACED focus, not just the paraxial plane.

        The solve targets the prescription's paraxial image distance, and on a real scene the
        traced best focus is somewhere else -- measured on the AZ85 BS scene, solving for the field
        the system was ALREADY at took the residual from -0.0000 to -7.3808 and put the image
        distance back to the as-loaded 154.770 mm, undoing a snap that had it at 162.151. That gap
        is a genuine optical effect (real-ray aberration plus the glass paths through the BS cube
        and the prism), not an arithmetic error: it varies with conjugate, -7.38 mm at 1.15X and
        -3.69 mm at 28 x 28.

        So "click Solve for Thickness" could never focus by construction. Measured, the snap costs
        NOTHING in field accuracy -- solve then snap lands the field at exactly 23.000 mm AND the
        residual at -0.0000, in a single cycle, with no iteration -- so the solve now finishes with
        it. Repeating the solve afterwards would undo it again, which is why it belongs inside the
        solve rather than in the user's hands.

        Skipped when the sensor leg is pinned by hand (bugs/0489): the snap moves the detector
        along that leg, so honouring the pin has to win over auto-focusing.
        """
        if getattr(self.editor, "_solve_focus_finish_active", False):
            return ""
        pins = self._axis_section_pins()
        if pins.get("image_far") is not None:
            return " Sensor leg pinned by hand: left where you placed it, not snapped to focus."
        snap = getattr(self.editor, "snap_detector_to_image_plane", None)
        if not callable(snap):
            return ""
        try:
            before = float(self.editor._traced_bundle_best_focus_shift())
        except Exception:
            before = float("nan")
        self.editor._solve_focus_finish_active = True
        try:
            snap()
        except Exception as exc:
            return f" Focus snap skipped ({type(exc).__name__}: {exc})."
        finally:
            self.editor._solve_focus_finish_active = False
        try:
            after = float(self.editor._traced_bundle_best_focus_shift())
        except Exception:
            return " Snapped the detector to the traced focus."
        if not np.isfinite(before):
            return " Snapped the detector to the traced focus."
        return f" Focus: residual {before:+.4g} -> {after:+.4g} mm (snapped to the traced focus)."

    def _rebalance_object_leg_sections(self, pre: "dict | None", led_offset=None) -> str:
        """bugs/0484: put the whole object-side change into section 2, holding section 1.

        Sections, as the object split names them: 1 = ``object -> beam splitter``
        (``near``), 2 = ``beam splitter -> lens front`` (``far``). The solve changes their
        TOTAL and wrote all of it into the gap row -- which is section 1. Section 1 IS the BS's
        world position (the split's ``fold_point`` tracks it exactly), so the BS slid up the axis
        while its separately-anchored LED body stayed put: "the BS Plate is shifted down, the
        subsequent elements shifted down as well ... the BS should glue to the LED, cannot be
        displaced". Measured on the reported scene, section 1 went 53.803 -> 64.871 -> 90.696
        across 23x23 then 30x30 while section 2 never moved off 71.660.

        Holding section 1 at its pre-solve value pins BOTH ends of it -- the object plane is the
        station anchor and the BS crossing sits a fixed distance along the axis from it -- so
        section 2 absorbs the entire change and the LENS moves instead. That is the user's call
        ("just change the section 2 distance") and it is what bugs/0453's redirect was reaching
        for; its topology test could not fire here because it wants a promoted solid immediately
        after the object gap and this scene's BS is row 3, which is also why gluing by hand
        changed nothing.

        Growing section 2 only increases the mirror-to-lens clearance, so the common direction is
        always safe; a shrink is clamped at the split's own ``far_min`` ("so the mirror does not
        collide with the lens"), and because the writer holds the total the remainder then falls
        back onto section 1 -- moving the BS only when there is no alternative.

        ``led_offset`` is the BS -> LED world vector captured BEFORE the solve wrote anything. The
        glue is a fixed RELATIVE pose and has to be restored as one: the split writer slides the BS
        and the LED together by its own delta, which is right when a user drives it by hand but
        wrong here, because the solve had already moved the BS alone (through the station shift)
        and not the LED. Cancelling the BS's motion then leaves the LED displaced by the same
        amount -- measured, it drifted -11.07 / -36.89 / -55.34 / -73.79 mm across a 23/30/35/40
        sweep while the BS held. Measuring the vector any later than the caller does is the same
        bug one level down: by then it already carries the delta.
        """
        mirror_row = None
        try:
            mirror_row = int(pre["mirror_row"]) if isinstance(pre, dict) else None
        except (KeyError, TypeError, ValueError):
            mirror_row = None
        offset = np.asarray(led_offset, dtype=float) if led_offset is not None else None
        note = self._rebalance_split_sections(
            pre,
            side="object",
            reader=getattr(self.editor, "_folded_object_conjugate_split", None),
            writer=getattr(self.editor, "_apply_folded_object_split", None),
            target_from=lambda pre_near, delta: pre_near,  # section 1 HELD
            label="object",
        )
        if offset is not None and mirror_row is not None:
            try:
                bs_after = self.editor._promoted_solid_current_center(mirror_row)
                if bs_after is not None:
                    target = np.asarray(bs_after, dtype=float) + offset
                    if self.editor._seat_step_body_world_center("led", target):
                        note += " LED re-seated on the BS (glue held)."
            except Exception:
                pass
        return note

    def _rebalance_image_leg_sections(self, pre: "dict | None") -> str:
        """bugs/0482: share a solved image-leg change 50:50 between the fold's two sections.

        The solve fixes the lens->sensor TOTAL; how it splits between ``lens rear -> mirror`` and
        ``mirror -> sensor`` is a free mechanical choice (the same reasoning bugs/0468 used to
        slide the mirror rather than refuse). It was not a choice in practice: the whole change
        landed on the sensor leg because that is the row the solve writes. Measured on
        flag_20260730_103719's scene, 23x23 then 30x30 drove ``mirror -> sensor`` 51.500 ->
        38.728 -> 18.860 mm while ``lens rear -> mirror`` sat at 103.270 mm throughout, with room
        to spare -- and the camera crashed into the prism.

        With no user constraint the change is shared evenly, then clamped to the floors the split
        itself reports (``near_min``, and the bugs/0482 body-aware ``_image_gap_collision_floor``);
        the writer holds the total, so anything a clamp takes off one section lands on the other.
        Applied through ``_apply_folded_image_split`` rather than the rows because on a frozen
        scene that writer slides the breadcrumbed mirror and re-seats the sensor AND camera on the
        exit leg (bugs/0447) -- a raw thickness write does neither.

        Returns a status-line fragment (possibly empty). Never raises: a rebalance that cannot be
        applied leaves the already-correct conjugate alone.
        """
        return self._rebalance_split_sections(
            pre,
            side="image",
            reader=getattr(self.editor, "_folded_image_conjugate_split", None),
            writer=getattr(self.editor, "_apply_folded_image_split", None),
            target_from=lambda pre_near, delta: pre_near + delta / 2.0,  # shared 50:50
            label="image",
            far_floor_extra=self._image_gap_collision_floor,
        )

    def _axis_section_pins(self) -> dict:
        """Section values the user fixed by dragging (bugs/0489). Empty when nothing is pinned.

        Runtime state, deliberately: a pin records "I put this here", which belongs to the editing
        session rather than the prescription, and it is cleared when a layout is loaded so a scene
        never arrives silently over-constrained.
        """
        pins = getattr(self.editor, "_axis_section_pins_state", None)
        return dict(pins) if isinstance(pins, dict) else {}

    def _rebalance_split_sections(
        self,
        pre,
        *,
        side: str,
        reader,
        writer,
        target_from,
        label: str,
        far_floor_extra=None,
    ) -> str:
        """The shared body behind the object (bugs/0484) and image (bugs/0482) rebalances.

        Both do the same thing and differ only in ``target_from``: the image side shares the
        change evenly between its two sections, the object side holds section 1 so section 2 takes
        all of it. Extracted because two copies of a distance-distribution rule in this file is
        how bugs/0314, 0466, 0468, 0478 and 0479 each got their own subtly different arithmetic.

        Never raises. Any failure leaves the already-correct conjugate alone and says so, because
        a wrong redistribution is worse than none: the conjugate (focus, magnification) is right
        either way, and only the mechanical packaging is at stake.
        """
        if not isinstance(pre, dict) or reader is None or writer is None:
            return ""
        try:
            post = reader()
        except Exception:
            return ""
        if not isinstance(post, dict):
            return ""
        try:
            total_new = float(post["total"])
            delta = total_new - float(pre["total"])
            pre_near = float(pre["near"])
            post_near = float(post["near"])
            near_min = float(post.get("near_min", 0.0) or 0.0)
            far_min = float(post.get("far_min", 0.0) or 0.0)
        except (KeyError, TypeError, ValueError):
            return ""
        if not (np.isfinite(delta) and np.isfinite(total_new)) or abs(delta) < 1.0e-9:
            return ""
        far_floor = far_min
        if far_floor_extra is not None:
            try:
                far_floor = max(far_floor, float(far_floor_extra()))
            except Exception:
                pass
        if near_min + far_floor > total_new + 1.0e-6:
            # Both sections cannot clear at this total. The conjugate is already applied, so
            # report rather than thrash the geometry.
            return (
                f" Both {label} sections cannot clear at {total_new:.4g} mm "
                f"(near >= {near_min:.4g}, far >= {far_floor:.4g} mm)."
            )
        # bugs/0489: a drag is a CONSTRAINT. The user placing a folder by hand fixes that
        # section, and the solver's own default distribution (bugs/0482's 50:50 image share,
        # bugs/0484's hold of section 1) would overwrite exactly what the drag just set -- measured,
        # sliding the RA mirror 20 mm then clicking Solve for Thickness took the residual defocus
        # from -20.0000 to -25.5266, i.e. further from focus than before solving. A pin wins over
        # the default; the sibling section absorbs the change instead.
        pins = self._axis_section_pins()
        pinned_near = pins.get(f"{side}_near")
        pinned_far = pins.get(f"{side}_far")
        if pinned_near is not None and pinned_far is not None:
            return (
                f" Both {label} sections are pinned by hand ({pinned_near:.4g} + {pinned_far:.4g} mm); "
                f"the solve cannot reach {total_new:.4g} mm without releasing one."
            )
        if pinned_near is not None:
            wanted = float(pinned_near)
        elif pinned_far is not None:
            wanted = total_new - float(pinned_far)
        else:
            try:
                wanted = float(target_from(pre_near, delta))
            except Exception:
                return ""
        if not np.isfinite(wanted):
            return ""
        target = min(max(wanted, near_min), total_new - far_floor)
        if abs(target - post_near) < 1.0e-6:
            return ""
        try:
            ok, message = writer("near", float(target))
        except Exception as exc:
            return f" {label.capitalize()} section share skipped ({type(exc).__name__}: {exc})."
        if not ok:
            return f" {label.capitalize()} section share skipped: {message}"
        held = abs(target - pre_near) < 1.0e-6
        how = "section 1 held" if held else "shared 50:50"
        return (
            f" {label.capitalize()} change {how}: near {post_near:.4g} -> {target:.4g} mm, "
            f"far {total_new - target:.4g} mm (far floor {far_floor:.4g} mm)."
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
        derived from the circular object FOV diagonal.

        bugs/0609: this is a DISPLAY/prefill reader, so it uses the DELIVERED
        magnification (bugs/0602's rule) -- the raw folded first order would prefill
        a field that does not fill the sensor. Measured after a PYRITE swap: raw said
        15.27 while the machine needed 19.79 to fill the same 23 mm sensor.
        """
        mag = self._finite_mag()
        sensor_wh = self.sensor_active_dimensions()
        if mag is not None and sensor_wh is not None:
            sw, sh = sensor_wh
            m = abs(float(mag) * self._folded_m_correction())
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


    # ---------------------------------------------------------- bugs/0591: measured field fill
    def _folded_m_correction(self) -> float:
        """The measured/first-order magnification ratio for THIS scene (bugs/0591), 1.0 when
        unmeasured. Runtime state like the section pins: it records what the TRACED machine
        delivered against what the station-frame first order promised, and is cleared on load."""
        return folded_m_correction(self.editor)

    def _set_folded_m_correction(self, factor: float) -> None:
        try:
            factor = float(factor)
        except Exception:
            return
        if np.isfinite(factor) and 0.1 < factor < 10.0:
            self.editor._folded_m_correction_state = factor

    _FIELD_FILL_TOLERANCE = 0.01
    _FIELD_FILL_MAX_PASSES = 5
    _FIELD_FILL_PROBE_FRACTION = 0.7

    def _measured_delivered_image_semi(self, object_semi: float) -> "float | None":
        """The DELIVERED image semi-field for a requested object semi-field, measured by
        real-ray tracing (the bugs/0593 world-order instrument), or None where the first
        order is already trustworthy (sequential scenes) or nothing lands.

        Probes at a FRACTION of the field (the full corner of an over-magnified solve lands
        outside the image disc and would read as vignetted) and scales back up — the
        instrument's own field scan measured the heights exactly linear on this scene family.
        """
        editor = self.editor
        try:
            if not editor._world_placed_chain_rows():
                return None
            wavelength = float(editor._current_wavelength())
            acceptance = editor._world_launch_acceptance(wavelength)
            if acceptance is None:
                return None
            pupil_distance = editor._world_launch_pupil_distance_cached(wavelength, float(acceptance))
        except Exception:
            return None
        fraction = float(self._FIELD_FILL_PROBE_FRACTION)
        probe = float(object_semi) * fraction
        heights: list[float] = []
        for field_x, field_y in ((0.0, probe), (0.0, -probe)):
            try:
                bundle = editor._world_order_field_bundle(
                    "hexapolar", field_x, field_y, 30, float(acceptance), pupil_distance
                )
                x_local, y_local, _z, _l, _m, _n = editor._world_order_trace_landings(wavelength, bundle)
            except Exception:
                continue
            if np.asarray(x_local).size >= 5:
                heights.append(float(np.hypot(np.mean(x_local), np.mean(y_local))))
        if len(heights) < 2:
            return None
        return float(np.mean(heights)) / fraction

    def relearn_folded_m_correction(self) -> "float | None":
        """Re-measure the delivered/promised magnification ratio for the CURRENT optics and
        record it (bugs/0608), returning the factor or None when it cannot be measured.

        bugs/0591 invalidates the learned correction on a lens/camera swap -- the old glass's
        factor is meaningless on the new one -- but nothing re-measured it, so every readout
        between the swap and the user's next solve was the RAW folded first order. Measured on
        flag_20260811_133818 (Apo75 -> PYRITE 4.5/85): the readout promised |m| 1.506 while the
        real rays delivered 1.160, so the "FOV 15.3 x 15.3" label implied a full sensor while
        the traced field covered ~82% of its width. The swap's own refocus already knows the
        new conjugate; this pins the READOUT to what that conjugate actually delivers.

        Uses the same real-ray probe as the solve's refinement, so a scene where the first
        order is already trustworthy (sequential, no world-placed chain) simply gets None and
        keeps correction 1.0."""
        state = self.current_state()
        try:
            promised = abs(float(state.get("magnification")))
            object_semi = float(state.get("fov_semi"))
        except (TypeError, ValueError):
            return None
        if not (np.isfinite(promised) and promised > 1e-9 and np.isfinite(object_semi) and object_semi > 1e-9):
            return None
        # current_state() already multiplies by the standing correction; measure against the
        # RAW first order so the factor is absolute, not compounded.
        promised_raw = promised / max(self._folded_m_correction(), 1e-9)
        measured_semi = self._measured_delivered_image_semi(object_semi)
        if measured_semi is None or not np.isfinite(measured_semi) or measured_semi <= 0.0:
            return None
        factor = float(measured_semi / object_semi) / promised_raw
        if not np.isfinite(factor) or not (0.1 < factor < 10.0):
            return None
        self._set_folded_m_correction(factor)
        return factor

    def _refine_folded_field_fill(self, object_semi: float, target_image_semi: float) -> str:
        """bugs/0591: the folded first order books gaps for a magnification the machine does
        not deliver — measured on the flagged Apo75, the solve promised |m| = 0.4189 and the
        world delivered 0.534, so "Object 55 x 55 mm fills the sensor" actually put ~43 x 43
        of it on the glass. The station-frame first order cannot be trusted on a frozen fold
        (bugs/0576), so per the standing doctrine (measured shifts are under-measured —
        iterate, never single-shot): MEASURE the delivered field with real rays and re-book
        the conjugate against the measured error until the fill lands within 1%.

        Returns a message fragment; refusals from the re-book are surfaced verbatim (the
        0577-era refusal machinery stays authoritative — a refinement must never force a gap
        the machine cannot hold)."""
        measured = self._measured_delivered_image_semi(object_semi)
        if measured is None or not np.isfinite(measured) or measured <= 0:
            return ""
        target = float(target_image_semi)
        request = target / self._folded_m_correction()
        # SECANT update on measured(request): the fresh-swap deferred branch responds with a
        # DIFFERENT (even inverted) local slope than the frozen-world branch, and the naive
        # multiplicative fixed point diverged there (measured +7.3% after 3 passes while the
        # request walked the wrong way). The secant uses the actual local slope, sign included;
        # the multiplicative step only seeds it.
        previous_request = None
        previous_measured = None
        best = (abs(measured / target - 1.0), float(measured), float(request))
        for _pass in range(int(self._FIELD_FILL_MAX_PASSES)):
            error = measured / target - 1.0
            if abs(error) <= float(self._FIELD_FILL_TOLERANCE):
                # Learn the machine's measured/first-order ratio for the next booking AND for
                # the measured-aware readout (delivered == typed == readout).
                self._set_folded_m_correction(float(measured) / float(request))
                return (
                    f" Delivered field VERIFIED by real rays: {2.0 * measured:.4g} mm on the "
                    f"sensor diagonal (target {2.0 * target:.4g}, {100.0 * error:+.2f}%)."
                )
            if previous_measured is not None and abs(measured - previous_measured) > 1.0e-9:
                slope = (float(measured) - previous_measured) / (float(request) - previous_request)
                next_request = float(request) + (target - float(measured)) / slope if abs(slope) > 1.0e-9 else float(request) * target / float(measured)
            else:
                next_request = float(request) * target / float(measured)
            next_request = float(np.clip(next_request, 0.3 * target, 3.0 * target))
            previous_request, previous_measured = float(request), float(measured)
            request = next_request
            applied, note = self._apply_conjugate_pair(float(object_semi), float(request))
            if not applied:
                return (
                    f" Field-fill refinement stopped ({100.0 * error:+.1f}% residual): {note}"
                )
            measured = self._measured_delivered_image_semi(object_semi)
            if measured is None or not np.isfinite(measured) or measured <= 0:
                return " Field-fill refinement stopped: the delivered field became unmeasurable."
            if abs(measured / target - 1.0) < best[0]:
                best = (abs(measured / target - 1.0), float(measured), float(request))
        error = measured / target - 1.0
        self._set_folded_m_correction(float(measured) / float(request))
        return (
            f" Delivered field measured {2.0 * measured:.4g} mm vs target {2.0 * target:.4g} "
            f"({100.0 * error:+.1f}% after {int(self._FIELD_FILL_MAX_PASSES)} passes -- the "
            "folded first order disagrees with the traced machine; bugs/0591)."
        )

    def fov_solve(
        self,
        plane: str,
        mode: str,
        width: Any,
        height: Any = None,
        aspect: tuple[float, float] | None = None,
        branch: str | None = None,
    ) -> tuple[bool, str]:
        """Drive the click-on-plane FOV popup.

        ``plane`` is "object" or "image"; ``mode`` is "thickness" (move the
        object/image conjugate pair) or "sensor" (resize the sensor). ``width`` /
        ``height`` are the typed field dimensions -- object-side for the object
        plane, image-side (sensor) for the image plane. Either one may be omitted
        (blank): the missing side is derived from ``aspect`` (the live sensor's
        width:height, default 4:3), so the user can fill just one box. The optical
        model is left in focus and the caller owns the retrace.

        ``branch`` (detector redesign B3): on a tagged two-arm scene, route an
        object/thickness solve to ONE arm (``branch_fov_solve``) -- that arm's sensor
        sees the field, every other arm is re-focused at the shared new object gap.
        """
        if plane == "object":
            wh = self._sensor_wh(width, height, aspect)
            if wh is None:
                return False, "Enter a positive FOV width or height."
            obj_w, obj_h, obj_diag = wh
            semi = obj_diag / 2.0
            if mode == "thickness" and branch:
                return self.branch_fov_solve(branch, semi)
            if mode == "thickness":
                sensor = self._sensor_semi()
                if not sensor:
                    return False, "No sensor available to fill."
                # bugs/0591: the station-frame first order over-delivers on a frozen fold
                # (measured 27%). Book with the LEARNED measured correction so a re-solve of
                # the same field is idempotent (phase 444 C4), then verify with real rays and
                # update the correction.
                correction = self._folded_m_correction()
                ok, msg = self._apply_conjugate_pair(semi, float(sensor) / correction)
                if ok:
                    msg += self._refine_folded_field_fill(semi, float(sensor))
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
        # bugs/0591: the readout shares the solve's frame -- with the measured correction the
        # reported |m| / FOV are what the TRACED machine delivers, not the station-frame promise.
        if mag is not None:
            try:
                mag = float(mag) * self._folded_m_correction()
            except Exception:
                pass
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

    def _branch_solve_info(self, selector: str) -> dict[str, Any] | None:
        """One tagged arm's solve ingredients: its private gap-row index, terminal row,
        sensor semi and its own 0297 first order. None when the arm is not solvable."""
        editor = self.editor
        rows = list(getattr(editor, "rows", None) or [])
        try:
            from KrakenOS.UI.services.paraxial_tools import (
                _branch_leaf_rows,
                _row_branch_selector,
            )
        except Exception:
            return None
        arm_indices = [i for i, r in enumerate(rows) if _row_branch_selector(r) == str(selector)]
        if len(arm_indices) < 2:
            return None
        leaf = _branch_leaf_rows(rows, selector)
        if len(leaf) < 3:
            return None
        try:
            first = editor._first_order_reference_for_rows(leaf, unfold_branch_tilts=True)
        except Exception:
            first = None
        if not isinstance(first, dict):
            return None
        try:
            diameter = float(getattr(rows[arm_indices[-1]], "diameter", 0.0) or 0.0)
        except Exception:
            diameter = 0.0
        return {
            "gap_row": arm_indices[-2],
            "terminal_row": arm_indices[-1],
            "first": first,
            "sensor_semi": diameter / 2.0 if diameter > 0 else None,
        }

    def branch_fov_solve(self, selector: str, object_semi: Any = None) -> tuple[bool, str]:
        """Detector redesign B3 (solve side): drive ONE tagged arm's sensor to see the
        requested object field, keeping every OTHER arm in focus.

        Physics on a tagged two-arm scene: the object gap is COMMON, each arm's
        lens->detector gap is PRIVATE. The target arm's Gaussian pair comes off its own
        first order (|m| = arm sensor semi / object semi, ``s_o = f(1+1/m)``,
        ``s_i = f(1+m)``); the object-row write shifts EVERY arm's ``s_o`` by the same
        delta, so each other arm is then RE-FOCUSED (``s_i' = f s_o'/(s_o'-f)``) through
        its own private gap -- its magnification drifts, its focus does not. Delta-form
        writes only: the interior (splitter gaps, folded entry decenters) is untouched.
        The caller owns the retrace (same contract as ``fov_solve``)."""
        editor = self.editor
        rows = list(getattr(editor, "rows", None) or [])
        try:
            from KrakenOS.UI.services.paraxial_tools import _scene_branch_selectors

            selectors = [s for s in _scene_branch_selectors(rows) if s]
        except Exception:
            selectors = []
        selector = str(selector or "").strip()
        if len(selectors) < 2 or selector not in selectors:
            return False, "Per-arm solve needs a tagged two-arm scene and a valid arm."
        if not rows or str(getattr(rows[0], "surface", "")) != "Object":
            return False, "Per-arm solve needs a finite Object row."
        semi = None
        try:
            semi = float(object_semi) if object_semi is not None else None
        except (TypeError, ValueError):
            semi = None
        if semi is None:
            semi = self._target_object_semi
        if not semi or semi <= 0:
            return False, "Set a target object field first (Set Target FOV)."
        target = self._branch_solve_info(selector)
        if target is None:
            return False, f"Arm {selector!r} has no solvable first order."
        sensor = target["sensor_semi"]
        if not sensor:
            return False, f"Arm {selector!r} has no sensor to fill."
        f = float(target["first"]["f"])
        mag = float(sensor) / float(semi)
        if not (np.isfinite(f) and f > 0 and np.isfinite(mag) and mag > 1e-9):
            return False, "Per-arm solve: degenerate magnification."
        s_o_new = f * (1.0 + 1.0 / mag)
        s_i_new = f * (1.0 + mag)
        s_o_old = float(target["first"]["object_principal"])
        s_i_old = float(target["first"]["image_principal"])
        if s_o_new <= f + 1e-9:
            return False, "FORBIDDEN: that field puts the object inside the focal point."
        d_obj = s_o_new - s_o_old
        writes: list[tuple[int, float]] = [
            (0, float(rows[0].thickness) + d_obj),
            (target["gap_row"], float(rows[target["gap_row"]].thickness) + (s_i_new - s_i_old)),
        ]
        notes = [f"{selector}: |m|={mag:.4g}"]
        for other in selectors:
            if other == selector:
                continue
            info = self._branch_solve_info(other)
            if info is None:
                notes.append(f"{other}: unsolvable, gap left alone")
                continue
            fb = float(info["first"]["f"])
            s_ob = float(info["first"]["object_principal"]) + d_obj
            if not (np.isfinite(fb) and fb > 0) or s_ob <= fb + 1e-9:
                notes.append(f"{other}: virtual image, gap left alone")
                continue
            s_ib = fb * s_ob / (s_ob - fb)
            writes.append(
                (info["gap_row"], float(rows[info["gap_row"]].thickness) + (s_ib - float(info["first"]["image_principal"])))
            )
            notes.append(f"{other}: refocused")
        for row_index, new_gap in writes:
            if not np.isfinite(new_gap) or new_gap <= 0:
                return False, (
                    f"Per-arm solve infeasible: row {row_index} gap would become {new_gap:.4g} mm."
                )
        for row_index, new_gap in writes:
            editor.rows[row_index].thickness = float(new_gap)
        self.set_target_fov(float(semi))
        return True, (
            f"Solved arm {selector!r}: object {2.0 * float(semi):.6g} mm full fills its "
            f"{2.0 * float(sensor):.6g} mm sensor (object gap {d_obj:+.4g} mm; "
            + "; ".join(notes)
            + ")."
        )

    def branch_states(self) -> dict[str, dict[str, Any]]:
        """Detector redesign B3: per-imaging-arm first-order estimates.

        On a TAGGED two-arm splitter scene (``advanced.Element.branch_selector`` arms, e.g.
        the dual MV150/MV120 layout) the single-chain estimate answers for ONE arm at best;
        each arm has its own lens, sensor and conjugates. Extract each arm's row chain
        (``_branch_leaf_rows``), read its own 0297 first order
        (``_first_order_reference_for_rows(unfold_branch_tilts=True)`` -- the folded arm's
        tilts are placement, not prescription) and derive f / working distance /
        magnification / per-arm sensor / object FOV. ``{}`` on non-two-arm scenes -- the
        single-chain readout stands unchanged there."""
        editor = self.editor
        rows = list(getattr(editor, "rows", None) or [])
        try:
            from KrakenOS.UI.services.paraxial_tools import (
                _branch_leaf_rows,
                _scene_branch_selectors,
            )

            selectors = [s for s in _scene_branch_selectors(rows) if s]
        except Exception:
            return {}
        if len(selectors) < 2:
            return {}
        out: dict[str, dict[str, Any]] = {}
        for selector in selectors:
            try:
                leaf = _branch_leaf_rows(rows, selector)
            except Exception:
                continue
            if len(leaf) < 3:
                continue
            first = None
            try:
                first = editor._first_order_reference_for_rows(leaf, unfold_branch_tilts=True)
            except Exception:
                first = None
            if not isinstance(first, dict):
                continue
            state: dict[str, Any] = {
                "focal_length": float(first["f"]),
                "working_distance": None,
                "magnification": None,
                "sensor_semi": None,
                "fov_semi": None,
                "fov_full": None,
            }
            try:
                state["working_distance"] = float(leaf[0].thickness)
            except Exception:
                pass
            try:
                diameter = float(getattr(leaf[-1], "diameter", 0.0) or 0.0)
                state["sensor_semi"] = diameter / 2.0 if diameter > 0 else None
            except Exception:
                pass
            f = float(first["f"])
            s_o = float(first["object_principal"])
            # The same conjugate magnification the single-chain readout uses (bugs/0222):
            # m = f / (s_o - f), read at the Gaussian conjugate, magnitude convention.
            if np.isfinite(f) and np.isfinite(s_o) and abs(s_o - f) > 1e-9 and f > 0 and s_o > f:
                mag = f / (s_o - f)
                state["magnification"] = float(mag)
                sensor = state["sensor_semi"]
                if sensor and abs(mag) > 1e-9:
                    state["fov_semi"] = float(sensor) / abs(mag)
                    state["fov_full"] = 2.0 * state["fov_semi"]
            out[selector] = state
        return out

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
        # Detector redesign B3: per-arm lines on a tagged two-arm scene. One compact line per
        # imaging arm so the panel answers for BOTH sensors, not a single-chain blend.
        try:
            branches = self.branch_states()
        except Exception:
            branches = {}
        if branches:
            lines = []
            for selector in sorted(branches):
                bstate = branches[selector]
                mag = bstate.get("magnification")
                fov = bstate.get("fov_full")
                lines.append(
                    f"{selector}: f {_mm(bstate.get('focal_length'))}"
                    + (f" | m {mag:.4g}x" if mag else "")
                    + (f" | FOV {fov:.6g} mm" if fov else "")
                )
            out["branches"] = "\n".join(lines)
        else:
            out["branches"] = "--"
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
