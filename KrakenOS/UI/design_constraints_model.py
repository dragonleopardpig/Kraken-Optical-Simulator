"""The design-constraint block's model (bugs/0930): pin first-order knowns, solve for the lens.

`panels/design_constraint_controls.py` wired Tk widgets to the Quick Estimation service; its rows,
the Design / Placement header, the pin collection and the evaluate / apply calls were written into
that Tk class, so a Qt view would have had to copy them. They live here; the Tk block and the Qt
3D Live dock both call them. All the optics stays in `quick_estimation` (`design_constraint_view`,
`placement_constraint_view`); advisory until Apply, which the inspector routes with history.
"""
from __future__ import annotations

from KrakenOS.UI.services.quick_estimation import (
    DESIGN_IMAGE_DISTANCE,
    DESIGN_MAGNIFICATION,
    DESIGN_OBJECT_DISTANCE,
    DESIGN_OBJECT_FOV_SEMI,
    DESIGN_TOTAL_TRACK,
)

#: (quantity, label, unit) in display order
ROWS = (
    (DESIGN_MAGNIFICATION, "Magnification", "x"),
    (DESIGN_OBJECT_DISTANCE, "Object distance", "mm"),
    (DESIGN_IMAGE_DISTANCE, "Image distance", "mm"),
    (DESIGN_TOTAL_TRACK, "Total track", "mm"),
    (DESIGN_OBJECT_FOV_SEMI, "Object FOV (semi)", "mm"),
)
LABELS = {quantity: label for quantity, label, _unit in ROWS}
#: a pinned FOV fixes its magnification twin and vice versa
TWIN = {DESIGN_MAGNIFICATION: DESIGN_OBJECT_FOV_SEMI, DESIGN_OBJECT_FOV_SEMI: DESIGN_MAGNIFICATION}
STATUS_COLORS = {"balanced": "#1a6d2f", "under": "#7a5b00", "over": "#8a2b2b", "invalid": "#8a2b2b"}
MODES = (("design", "Design (find lens)"), ("placement", "Placement (fixed lens)"))


def normal_mode(mode) -> str:
    return "placement" if str(mode or "").strip().lower() == "placement" else "design"


def header_text(mode: str) -> str:
    return ("Placement (fixed lens) -- pin one, solve & focus" if normal_mode(mode) == "placement"
            else "Design lens -- pin knowns, solve for the EFL")


def collect_pins(fixed: dict, values: dict) -> dict:
    """{quantity: float} for every row whose box is ticked and whose value parses."""
    pins = {}
    for quantity, is_fixed in fixed.items():
        if not is_fixed:
            continue
        raw = str(values.get(quantity, "") or "").strip()
        if not raw:
            continue
        try:
            pins[quantity] = float(raw)
        except ValueError:
            continue
    return pins


def clean_context(raw) -> dict:
    out = {}
    for quantity, value in dict(raw or {}).items():
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if number == number:  # not NaN
            out[quantity] = number
    return out


def evaluate(inspector, mode: str, pins: dict) -> "tuple[dict, dict]":
    """(states, result) from the service: states[q]["state"] is "locked" / "available", with the
    solved "value" for a locked one; result carries the "message" and the "status"."""
    service = inspector._quick_estimation_service()
    view = (service.placement_constraint_view(pins) if normal_mode(mode) == "placement"
            else service.design_constraint_view(pins))
    return dict(view.get("states", {}) or {}), dict(view.get("result", {}) or {})


def apply(inspector, mode: str, pins: dict) -> None:
    """Move the object / image gaps to the solved conjugates (the inspector owns history + retrace)."""
    if normal_mode(mode) == "placement":
        inspector._apply_placement_constraints(pins)
    else:
        inspector._apply_design_constraints(pins)
