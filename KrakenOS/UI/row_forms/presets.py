"""Two more tail dialogs: the tolerance-solve preset and an optimisation variable's bounds
(docs/design_qt_migration.md phase 3).

Neither needed anything new from the framework. What they DID need was care about where the
error goes: the bounds dialog never showed a message box -- it wrote to the debug log and left
the dialog open -- and the preset dialog reports through `append_debug` as well as the status
line. A port that turned either into a modal error box would be a behaviour change, so the
builders raise `FormRefused` with the model's own wording and the panels decide where it lands.
"""
from __future__ import annotations

from KrakenOS.UI.row_forms.base import FormField, FormRefused, RowForm

PRESET_TITLE = "Save Tolerance Solve Preset"
PRESET_NOTE = ("A preset stores the Monte Carlo settings, the merit operands and the tolerance "
               "variable roles, so a solve can be repeated exactly. Save the layout to persist "
               "it.")
PRESET_FIELDS = (("name", "Preset name", "text"),
                 ("sample_count", "Monte Carlo samples", "int"),
                 ("seed", "Random seed", "int"),
                 ("compensator_steps", "Single-compensator steps", "int"),
                 ("multi_steps", "Multi-compensator steps", "int"),
                 ("multi_passes", "Multi-compensator passes", "int"))
BOUNDS_TITLE = "Optimisation bounds"


def compare_view_values(owner) -> tuple:
    """The compare-view list reaches the Tk shell as a CONSTRUCTOR KWARG, not an editor
    attribute, so read it off the owner when it has it and fall back to where it is defined."""
    from KrakenOS.UI.tolerance_constants import TOLERANCE_COMPARE_VIEW_VALUES

    held = getattr(owner, "tolerance_compare_view_values", None)
    return tuple(TOLERANCE_COMPARE_VIEW_VALUES if held is None else held)


def build_save_tolerance_preset_form(owner, *_args, **_kwargs) -> RowForm:
    """The Monte Carlo settings a tolerance solve is saved under."""
    active = owner._active_tolerance_solve_preset()
    roles = len(owner._current_tolerance_compensator_preset_payload())
    defaults = {"sample_count": 25, "seed": 12345, "compensator_steps": 9, "multi_steps": 5,
                "multi_passes": 2}

    form = RowForm(
        title=PRESET_TITLE,
        row_index=0,
        fields=(
            *(FormField(key, label, kind=kind, width=30)
              for key, label, kind in PRESET_FIELDS),
            FormField("tolerance_compare_view", "Tolerance compare view", kind="choice",
                      choices=compare_view_values(owner)),
        ),
        values={
            "name": str(active.get("name", "") or "Nominal tolerance solve"),
            **{key: str(active.get(key, defaults[key])) for key in defaults},
            "tolerance_compare_view": str(active.get(
                "tolerance_compare_view", owner._current_tolerance_compare_view())),
        },
        note=PRESET_NOTE,
        state={"owner": owner},
    )
    form.summary = f"Saves merit operands and {roles} tolerance variable role(s)."

    def collect(values: dict) -> dict:
        name = str(values.get("name", "")).strip()
        if not name:
            raise FormRefused("Give the preset a name.")
        numbers = {}
        for key, label, kind in PRESET_FIELDS:
            if kind != "int":
                continue
            try:
                numbers[key] = int(float(str(values.get(key, "")).strip()))
            except Exception as exc:
                raise FormRefused(f"{label} expects a whole number.") from exc
            if numbers[key] < 1:
                raise FormRefused(f"{label} must be at least 1.")
        return {"name": name, **numbers,
                "tolerance_compare_view": str(values.get("tolerance_compare_view", "")).strip()}

    def validate(values: dict) -> list[str]:
        try:
            collect(values)
        except FormRefused as exc:
            return [str(exc)]
        return []

    def describe(values: dict) -> str:
        parsed = collect(values)
        return (f"{parsed['name']}: {parsed['sample_count']} samples, seed "
                f"{parsed['seed']}, {roles} role(s)")

    def apply(values: dict) -> str:
        parsed = collect(values)
        owner._begin_history_capture()
        try:
            preset = owner.save_tolerance_solve_preset(
                parsed["name"],
                sample_count=parsed["sample_count"],
                seed=parsed["seed"],
                compensator_steps=parsed["compensator_steps"],
                multi_steps=parsed["multi_steps"],
                multi_passes=parsed["multi_passes"],
                tolerance_compare_view=parsed["tolerance_compare_view"],
            )
            owner._commit_history_capture()
        except Exception as exc:
            owner._history_pending_state = None
            raise FormRefused(str(exc)) from exc
        owner.append_debug(owner.tolerance_solve_preset_report_text(preset))
        message = (f"Saved tolerance solve preset '{preset.get('name')}'. "
                   "Save layout to persist it.")
        owner.status_var.set(message)
        return message

    form.validate = validate
    form.describe = describe
    form.apply = apply
    return form


def build_optimization_bounds_form(owner, row_index: "int | None" = None, *,
                                   spec=None) -> RowForm:
    """The lower and upper bound of one optimisation variable."""
    if spec is None or row_index is None or not (0 <= int(row_index) < len(owner.rows)):
        raise FormRefused("Right-click an optimisation variable cell first.")
    index = int(row_index)
    row = owner.rows[index]
    current = spec.get_bounds(row) or spec.default_bounds(spec.value_from_row(row))

    form = RowForm(
        title=f"Bounds for {row.name} {spec.label}",
        row_index=index,
        fields=(FormField("lower", "Lower", kind="number", width=16),
                FormField("upper", "Upper", kind="number", width=16)),
        values={"lower": f"{float(current[0]):g}", "upper": f"{float(current[1]):g}"},
        note=(f"The optimiser keeps {spec.label} between these values. "
              "Lower must be less than upper."),
        state={"owner": owner, "index": index, "spec": spec},
    )
    form.summary = f"S{index} {row.name}: {spec.label} is {spec.value_from_row(row):g} now."

    def collect(values: dict) -> tuple:
        try:
            lower = float(str(values.get("lower", "")).strip())
            upper = float(str(values.get("upper", "")).strip())
        except ValueError as exc:
            raise FormRefused("Invalid optimization bounds entry.") from exc
        if lower >= upper:
            raise FormRefused("Optimization bounds rejected: lower must be less than upper.")
        return lower, upper

    def validate(values: dict) -> list[str]:
        try:
            collect(values)
        except FormRefused as exc:
            return [str(exc)]
        return []

    def describe(values: dict) -> str:
        lower, upper = collect(values)
        return f"[{lower:g}, {upper:g}]"

    def apply(values: dict) -> str:
        lower, upper = collect(values)
        owner._begin_history_capture()
        spec.set_bounds(owner.rows[index], (lower, upper))
        owner._commit_history_capture()
        message = f"Bounds set for row {index} {spec.label}: [{lower:g}, {upper:g}]"
        owner.append_progress(message)
        return message

    form.validate = validate
    form.describe = describe
    form.apply = apply
    return form


build_save_tolerance_preset_form.TITLE = PRESET_TITLE
build_optimization_bounds_form.TITLE = BOUNDS_TITLE
