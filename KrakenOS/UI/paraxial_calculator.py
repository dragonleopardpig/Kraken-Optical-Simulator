"""The Paraxial Calculator's model (docs/design_qt_migration.md phase 3).

Extracted from the Tk dialog, where ~200 lines of paraxial arithmetic lived inside a closure. It
is physics, not layout: the thin-lens conjugate relations, the matrix-solution path when the
layout's own cardinal points are loaded, and what a solved value means when it is applied back to
the rows. Both toolkits now solve through this module.

Nothing here touches a toolkit. `owner` is the editor (or a panel that forwards to it) and is used
only for its model helpers: `_exact_paraxial_solution_for_rows`, the two gap solvers,
`_format_paraxial_value`, and the row list.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

import KrakenOS as Kos

SOLVE_TARGETS = ("Image distance", "Object distance", "Magnification",
                 "Distances from magnification")
OBJECT_MODES = ("Infinity", "Finite")
PROMPT = "Set known values, then click Solve."


class CalculatorFailed(Exception):
    """A solve that cannot be done, carrying the message the dialog should show."""


class NothingToApply(CalculatorFailed):
    """The solve succeeded but has no layout cell to write -- a status line, not an error box."""


@dataclass(frozen=True)
class CalculatorInputs:
    """Everything the form holds. Text, because that is what a field contains."""

    solve_for: str = SOLVE_TARGETS[0]
    effl: str = "0"
    ppa: str = "0"
    ppp: str = "0"
    object_mode: str = OBJECT_MODES[0]
    object_distance: str = "0"
    image_distance: str = "0"
    magnification: str = "0"


@dataclass
class CalculatorSolution:
    """What the dialog shows, and what Apply would write."""

    result: str = ""
    detail: str = ""
    #: values the form writes back into its own fields
    magnification: "float | None" = None
    object_distance: "float | None" = None
    image_distance: "float | None" = None
    payload: dict = field(default_factory=dict)


def initial_inputs(owner) -> CalculatorInputs:
    """What the form opens with: the EFL estimate, and the layout's own object/image gaps."""
    rows = getattr(owner, "rows", ()) or ()
    image_row = max(0, len(rows) - 2)
    try:
        effl = f"{float(owner._current_effl_estimate()):.6g}"
    except Exception:
        effl = "0"
    return CalculatorInputs(
        solve_for=SOLVE_TARGETS[0],
        effl=effl,
        ppa="0",
        ppp="0",
        object_mode=owner._current_object_mode(),
        object_distance=f"{(float(rows[0].thickness) if rows else 0.0):.6g}",
        image_distance=f"{(float(rows[image_row].thickness) if rows else 0.0):.6g}",
        magnification="0",
    )


def field_states(solve_for: str, object_mode: str) -> dict[str, str]:
    """Which distance fields the form may edit, per solve target -- "normal", "readonly" or
    "disabled", in tkinter's own words, mapped by each toolkit."""
    target = str(solve_for).strip()
    finite = str(object_mode).strip() != "Infinity"
    if target == "Image distance":
        return {"object_distance": "normal" if finite else "disabled",
                "image_distance": "disabled", "magnification": "readonly"}
    if target == "Object distance":
        return {"object_distance": "disabled", "image_distance": "normal",
                "magnification": "readonly"}
    if target == "Magnification":
        return {"object_distance": "normal" if finite else "disabled",
                "image_distance": "normal", "magnification": "disabled"}
    return {"object_distance": "disabled", "image_distance": "disabled",
            "magnification": "normal"}


def read_float(value, label: str) -> float:
    """The dialog's own parser, message for message."""
    text = str(value).strip()
    if not text:
        raise CalculatorFailed(f"{label} is required")
    try:
        number = float(text)
    except ValueError as exc:
        raise CalculatorFailed(f"{label} must be numeric") from exc
    if not np.isfinite(number):
        raise CalculatorFailed(f"{label} must be finite")
    return float(number)


def format_calc(value: float) -> str:
    return "Infinity" if not np.isfinite(value) else f"{float(value):.6g}"


def load_from_layout(owner) -> tuple[dict, str, "dict | None"]:
    """EFL/H1/H2 from the layout's cardinal points and EP/XP from the aperture settings.

    Returns ``(field values, the note to show, the matrix solution or None)``.
    """
    notes: list[str] = []
    values: dict[str, str] = {}
    matrix_solution: "dict | None" = None
    try:
        a, b, c, d, effl_display, ppa, ppp = owner._exact_paraxial_solution_for_rows(owner.rows)
        values.update(effl=f"{float(effl_display):.6g}", ppa=f"{float(ppa):.6g}",
                      ppp=f"{float(ppp):.6g}")
        matrix_solution = {"a": float(a), "b": float(b), "c": float(c), "d": float(d),
                           "effl_display": float(effl_display), "ppa": float(ppa),
                           "ppp": float(ppp)}
        notes.append("Loaded EFL/H1/H2 from layout.")
    except Exception as exc:
        message = getattr(owner, "short_error_message", lambda e: str(e))(exc)
        notes.append(f"Cardinal extraction unavailable ({message}).")
    try:
        system = owner.build_system()
        pupil = Kos.PupilCalc(system, owner._analysis_surface_index(), owner._current_wavelength(),
                              owner._current_aperture_type(), owner._current_aperture_value())
        values.update(ep_z=format_calc(float(pupil.PosPupInp[2])),
                      xp_z=format_calc(float(pupil.PosPupOut[2])))
        notes.append("Loaded EP/XP from current aperture settings.")
    except Exception:
        values.update(ep_z="n/a", xp_z="n/a")
    return values, (" ".join(notes) if notes else "Using manual values."), matrix_solution


def matrix_solution_matches(inputs: CalculatorInputs, loaded: "dict | None") -> bool:
    """Is the form still showing the cardinal points that were loaded from the layout?"""
    if loaded is None:
        return False
    try:
        return (abs(read_float(inputs.effl, "EFL") - float(loaded["effl_display"])) <= 1e-6
                and abs(read_float(inputs.ppa, "H1 offset") - float(loaded["ppa"])) <= 1e-6
                and abs(read_float(inputs.ppp, "H2 offset") - float(loaded["ppp"])) <= 1e-6)
    except Exception:
        return False


def solve(owner, inputs: CalculatorInputs, loaded: "dict | None" = None) -> CalculatorSolution:
    """Solve for the selected unknown. Raises CalculatorFailed with the message to show."""
    show = owner._format_paraxial_value
    f = read_float(inputs.effl, "EFL")
    if abs(f) <= 1e-12:
        raise CalculatorFailed("EFL must be non-zero")
    h1 = read_float(inputs.ppa, "H1 offset")
    h2 = read_float(inputs.ppp, "H2 offset")
    target = str(inputs.solve_for).strip()
    mode = str(inputs.object_mode).strip()
    matrix = loaded if matrix_solution_matches(inputs, loaded) else None

    if target == "Image distance":
        if matrix is not None:
            object_distance = (0.0 if mode == "Infinity"
                               else read_float(inputs.object_distance, "Object distance"))
            image_distance = owner._compute_image_gap_from_paraxial_solution(
                matrix["a"], matrix["b"], matrix["c"], matrix["d"], object_distance, mode)
            object_principal = float("inf") if mode == "Infinity" else object_distance + h1
            image_principal = image_distance - h2
            magnification = 0.0 if mode == "Infinity" else (
                float(image_principal / object_principal)
                if np.isfinite(object_principal) and abs(object_principal) > 1e-12
                else float("inf"))
        elif mode == "Infinity":
            image_distance = f + h2
            object_principal = float("inf")
            image_principal = float(f)
            magnification = 0.0
        else:
            object_distance = read_float(inputs.object_distance, "Object distance")
            object_principal = object_distance + h1
            if abs(object_principal) <= 1e-12:
                raise CalculatorFailed("Object is on H1; cannot solve image distance")
            balance = (1.0 / f) - (1.0 / object_principal)
            if abs(balance) <= 1e-12:
                image_distance = float("inf")
                image_principal = float("inf")
                magnification = float("inf")
            else:
                image_principal = 1.0 / balance
                image_distance = image_principal + h2
                magnification = image_principal / object_principal
        return CalculatorSolution(
            result=f"Image distance = {show(image_distance)} mm",
            detail=f"s={show(object_principal)}, s'={show(image_principal)}, m={show(magnification)}",
            magnification=magnification,
            payload={"target": "image", "value": image_distance, "object_mode_after": mode})

    if target == "Object distance":
        image_distance = read_float(inputs.image_distance, "Image distance")
        if matrix is not None:
            object_distance = owner._compute_object_gap_from_paraxial_solution(
                matrix["a"], matrix["b"], matrix["c"], matrix["d"], image_distance)
            if not np.isfinite(object_distance) or abs(object_distance) > 1e9:
                object_principal = float("inf")
                object_distance = float("inf")
                mode_after = "Infinity"
            else:
                object_principal = object_distance + h1
                mode_after = "Finite"
            image_principal = image_distance - h2
        else:
            image_principal = image_distance - h2
            if abs(image_principal) <= 1e-12:
                raise CalculatorFailed("Image is on H2; cannot solve object distance")
            balance = (1.0 / f) - (1.0 / image_principal)
            if abs(balance) <= 1e-12:
                object_principal = float("inf")
                object_distance = float("inf")
                mode_after = "Infinity"
            else:
                object_principal = 1.0 / balance
                object_distance = object_principal - h1
                mode_after = ("Infinity" if (not np.isfinite(object_distance)
                                             or abs(object_distance) > 1e9) else "Finite")
        magnification = (image_principal / object_principal
                         if np.isfinite(object_principal) and abs(object_principal) > 1e-12
                         else float("inf"))
        return CalculatorSolution(
            result=f"Object distance = {show(object_distance)} mm",
            detail=f"s={show(object_principal)}, s'={show(image_principal)}, m={show(magnification)}",
            magnification=magnification,
            payload={"target": "object", "value": object_distance,
                     "object_mode_after": mode_after})

    if target == "Magnification":
        if mode == "Infinity":
            object_principal = float("inf")
            image_principal = read_float(inputs.image_distance, "Image distance") - h2
            magnification = 0.0
        else:
            object_distance = read_float(inputs.object_distance, "Object distance")
            image_distance = read_float(inputs.image_distance, "Image distance")
            object_principal = object_distance + h1
            image_principal = image_distance - h2
            if abs(object_principal) <= 1e-12:
                raise CalculatorFailed("Object is on H1; cannot solve magnification")
            magnification = image_principal / object_principal
        return CalculatorSolution(
            result=f"Magnification = {show(magnification)}",
            detail=f"s={show(object_principal)}, s'={show(image_principal)} from H1/H2",
            magnification=magnification,
            payload={"target": "magnification", "value": magnification,
                     "object_mode_after": mode})

    magnification = read_float(inputs.magnification, "Magnification")
    if abs(magnification) <= 1e-12:
        raise CalculatorFailed("Magnification too close to zero; object distance goes to infinity")
    if abs(1.0 + magnification) <= 1e-12:
        raise CalculatorFailed("Magnification of -1 makes object/image distance singular")
    object_principal = f * (1.0 + (1.0 / magnification))
    image_principal = f * (1.0 + magnification)
    object_distance = object_principal - h1
    image_distance = image_principal + h2
    mode_after = ("Infinity" if (not np.isfinite(object_distance) or abs(object_distance) > 1e9)
                  else "Finite")
    return CalculatorSolution(
        result=f"Object={show(object_distance)} mm, Image={show(image_distance)} mm",
        detail=f"From m={show(magnification)}: s={show(object_principal)}, s'={show(image_principal)}",
        object_distance=object_distance,
        image_distance=image_distance,
        payload={"target": "pair", "object_value": object_distance,
                 "image_value": image_distance, "object_mode_after": mode_after})


def apply_solution(owner, payload: dict, result_text: str) -> str:
    """Write a solved value back into the layout. Returns the status line; raises on refusal.

    The object gap is row 0 and the image gap the second-to-last row -- the same cells the Tk
    dialog wrote.
    """
    if not payload:
        raise CalculatorFailed("No solved target to apply")
    target = str(payload.get("target", ""))
    mode_after = str(payload.get("object_mode_after", owner._current_object_mode()))
    image_row = max(0, len(owner.rows) - 2)

    if target == "image":
        value = float(payload.get("value", 0.0))
        if not np.isfinite(value):
            raise CalculatorFailed("Solved image distance is infinity and cannot be applied")
        owner.rows[image_row].thickness = value
        owner._select_table_row(image_row)
    elif target == "object":
        value = float(payload.get("value", 0.0))
        owner.object_mode_var.set(mode_after)
        if mode_after == "Finite":
            if not np.isfinite(value):
                raise CalculatorFailed(
                    "Solved object distance is infinity and cannot be applied in Finite mode")
            owner.rows[0].thickness = value
        owner._select_table_row(0)
    elif target == "pair":
        object_value = float(payload.get("object_value", float("nan")))
        image_value = float(payload.get("image_value", float("nan")))
        owner.object_mode_var.set(mode_after)
        if mode_after == "Finite":
            if not np.isfinite(object_value):
                raise CalculatorFailed(
                    "Solved object distance is infinity and cannot be applied in Finite mode")
            owner.rows[0].thickness = object_value
        if not np.isfinite(image_value):
            raise CalculatorFailed("Solved image distance is infinity and cannot be applied")
        owner.rows[image_row].thickness = image_value
        owner._select_table_row(image_row)
    elif target == "magnification":
        raise NothingToApply("Magnification computed. No layout cell to apply.")
    else:
        raise CalculatorFailed("No solved target to apply")

    owner._normalize_special_rows()
    owner._sync_table()
    owner._sync_object_controls()
    owner._mark_plot_update_pending()
    owner.append_progress(f"Paraxial calculator applied: {result_text}")
    return f"{result_text}  |  Click Update."
