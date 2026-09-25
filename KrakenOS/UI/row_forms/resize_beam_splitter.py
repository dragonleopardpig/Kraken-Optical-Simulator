"""The parametric beam-splitter resize row form (docs/design_qt_migration.md phase 3).

bugs/0423: type new dimensions and the solid is regenerated and replaced in place. A CUBE takes
one number, a PLATE takes four -- so the FIELDS THEMSELVES depend on the row, which is the model
reading `beam_splitter_resize_info` and building the form to match rather than a view branching
on a kind it would have to understand.
"""
from __future__ import annotations

from KrakenOS.UI.row_forms.base import FormField, FormRefused, RowForm

TITLE = "Resize Beam Splitter"
NOTE = ("New dimensions regenerate the parametric solid and replace it in place, keeping its "
        "pose and its face flags.")
CUBE_FIELDS = (("side_mm", "Side (mm)"),)
PLATE_FIELDS = (("width_mm", "Width (mm)"), ("height_mm", "Height (mm)"),
                ("thickness_mm", "Thickness (mm)"), ("tilt_deg", "Tilt (deg)"))


def build_resize_beam_splitter_form(owner, row_index: "int | None" = None) -> RowForm:
    """The dimensions of one parametric beam splitter."""
    if row_index is None:
        row_index = owner._selected_surface_row_index()
    info = owner.beam_splitter_resize_info(row_index) if row_index is not None else None
    if info is None:
        raise FormRefused("Resize Beam Splitter: this row is not a parametric beam splitter.")
    kind, params = info
    fields = CUBE_FIELDS if kind == "cube" else PLATE_FIELDS

    form = RowForm(
        title=f"Resize {str(kind).title()} Beam Splitter",
        row_index=int(row_index),
        fields=tuple(FormField(key, label, kind="number", width=12) for key, label in fields),
        values={key: f"{float(params.get(key, 0.0)):g}" for key, _label in fields},
        note=NOTE,
        state={"owner": owner, "kind": kind, "fields": fields, "index": int(row_index)},
    )
    form.summary = f"A {kind} beam splitter takes {len(fields)} dimension(s)."

    def collect(values: dict) -> dict:
        dimensions = {}
        for key, _label in fields:
            try:
                dimensions[key] = float(str(values.get(key, "")).strip())
            except (TypeError, ValueError) as exc:
                # the model's own wording: "side: enter a number."
                short = key.replace("_mm", "").replace("_deg", "")
                raise FormRefused(f"{short}: enter a number.") from exc
        return dimensions

    def validate(values: dict) -> list[str]:
        try:
            collect(values)
        except FormRefused as exc:
            return [str(exc)]
        return []

    def describe(values: dict) -> str:
        dimensions = collect(values)
        return ", ".join(f"{key.replace('_mm', '').replace('_deg', '')} {value:g}"
                         for key, value in dimensions.items())

    def apply(values: dict) -> str:
        dimensions = collect(values)
        if owner.resize_beam_splitter(form.state["index"], **dimensions) is None:
            # resize_beam_splitter reports its own reason on the status line
            raise FormRefused(str(owner.status_var.get()))
        return str(owner.status_var.get())

    form.validate = validate
    form.describe = describe
    form.apply = apply
    return form


build_resize_beam_splitter_form.TITLE = TITLE
