"""The optimisation panel's settings, toolkit-free (docs/design_qt_migration.md phase 6).

Which settings an operand has is already data -- `OperandSpec.controls`. What each setting IS --
its label, the per-operand model variable that holds it, and the choices a picker offers -- was
written into the Tk panel's `build()`, so the Qt shell could not offer optimisation (bugs/0904).
"""
from __future__ import annotations

import os
from dataclasses import dataclass

MTF_MODES = ("Average", "Tangential", "Sagittal")
MTF_ALGORITHMS = ("Diffraction FFT", "PSF FFT", "LSF FFT")


@dataclass(frozen=True)
class OperandControl:
    """One per-operand setting: the editor dict of variables (keyed by operand label) it uses."""

    name: str
    label: str
    variables: str
    kind: str = "text"
    choices: tuple = ()
    #: the editor method that returns the choices when they depend on the layout (bugs/0969)
    options: str = ""


#: every setting an OperandSpec may name in its `controls`, in the order the Tk card lays them out
OPERAND_CONTROLS = (
    OperandControl("weight", "Weight", "operand_weight_vars"),
    OperandControl("target", "Target", "operand_target_vars"),
    OperandControl("wavelength", "Wvl", "operand_wavelength_vars"),
    OperandControl("field", "Field", "operand_field_vars"),
    OperandControl("surface", "Surf", "operand_surface_vars", "choice", ("Auto",), "operand_surface_options"),
    OperandControl("frequency", "Freq", "operand_frequency_vars"),
    OperandControl("mtf_mode", "Mode", "operand_mtf_mode_vars", "choice", MTF_MODES),
    OperandControl("mtf_algorithm", "Alg", "operand_mtf_algorithm_vars", "choice", MTF_ALGORITHMS),
)
#: "field_xy" is a pair of variables rather than one
FIELD_XY_CONTROLS = (
    OperandControl("field_x", "Field X", "operand_field_x_vars"),
    OperandControl("field_y", "Field Y(s)", "operand_field_y_vars"),
)


def choices_for(control, editor) -> list:
    """What a choice setting offers NOW: the model's own list when the setting names one, else its
    fixed choices."""
    method = getattr(editor, control.options, None) if control.options else None
    if callable(method):
        try:
            return [str(value) for value in method()]
        except Exception:
            pass
    return [str(value) for value in control.choices]


def controls_for(spec) -> tuple:
    """The settings an operand shows, in card order -- `spec.controls` says which."""
    wanted = set(getattr(spec, "controls", ()) or ())
    shown = []
    for control in OPERAND_CONTROLS:
        if control.name in wanted:
            shown.append(control)
        if control.name == "field" and "field_xy" in wanted:
            shown.extend(FIELD_XY_CONTROLS)
    return tuple(shown)


#: Settings every operand HAS, whether or not its card shows them. The Tk card makes a variable
#: for each and hides the widgets `spec.controls` does not name; the values are saved with the
#: layout all the same. So a model without the Tk card must have them too (bugs/0995).
ALWAYS_HELD = ("weight", "target", "wavelength", "field", "surface")


def variables_for(spec) -> tuple:
    """Every setting an operand HOLDS a variable for, shown or not, in card order.

    Wider than `controls_for`: the five every operand holds, and the field point (x, y) an
    operand evaluated at a spatial frequency holds beside its field.
    """
    wanted = set(getattr(spec, "controls", ()) or ()) | set(ALWAYS_HELD)
    held = []
    for control in OPERAND_CONTROLS:
        if control.name in wanted:
            held.append(control)
        if control.name == "field" and ("field_xy" in wanted or "frequency" in wanted):
            held.extend(FIELD_XY_CONTROLS)
    return tuple(held)


#: a setting's starting value, exactly as the Tk card creates it; weight/target come from the
#: operand's own defaults and the wavelength from the system's
_FIXED_DEFAULTS = {"field": "0", "field_x": "0", "field_y": "0", "surface": "Auto",
                   "frequency": "5", "mtf_mode": "Average", "mtf_algorithm": "Diffraction FFT"}


def default_for(control, spec, owner) -> str:
    """What a setting starts as when no view has made its variable yet."""
    if control.name == "weight":
        return f"{spec.default_weight:g}"
    if control.name == "target":
        return f"{spec.default_target:g}"
    if control.name == "wavelength":
        variable = getattr(owner, "wavelength_var", None)
        return str(variable.get()) if variable is not None else "0.55"
    return _FIXED_DEFAULTS.get(control.name, "")


def worker_choices(cpu_total: "int | None" = None) -> list[str]:
    """What the Workers picker offers: Auto, 1, then a few counts up to the machine's."""
    total = max(1, int(cpu_total if cpu_total is not None else (os.cpu_count() or 1)))
    choices = ["Auto", "1"]
    for candidate in (2, 4, 6, 8, 12, 16, total):
        text = str(max(1, min(total, int(candidate))))
        if text not in choices:
            choices.append(text)
    return choices
