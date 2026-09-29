"""The System Selection calculator as a form (bugs/0631; Qt port 0930).

Given the field of view, the object-space resolution and the minimum working distance, size the
camera and the lens -- pure first-order optics in `services/system_selection.py`. The Tk calculator
built its own widgets and parsed its own entries; the parsing and the answer now live in
`system_selection_text`, which this form and the Tk form both call. It REPORTS rather than edits
(`read_only`): every input re-computes the result, "From scene" re-reads the FOV / sensor / camera.
"""
from __future__ import annotations

from KrakenOS.UI.row_forms.base import FormAction, FormField, RowForm

TITLE = "System Selection Calculator"


def build_system_selection_form_model(owner) -> RowForm:
    """``owner`` is the editor (the prefill reads its scene and camera)."""
    from KrakenOS.UI.services.system_selection import (
        SYSTEM_SELECTION_INPUTS,
        system_selection_prefill_values,
        system_selection_text,
    )

    values = {key: "" for key, _short, _full in SYSTEM_SELECTION_INPUTS}
    values["wavelength"] = "0.55"
    state: dict = {"pixels": None}
    prefill, state["pixels"] = system_selection_prefill_values(owner)
    values.update(prefill)

    def recompute(form, _text: str = "") -> str:
        form.values["result"] = system_selection_text(form.values, form.state.get("pixels"))
        return ""

    fields = tuple(
        FormField(key, full, kind="text", on_change=recompute) for key, _short, full in SYSTEM_SELECTION_INPUTS
    ) + (FormField("result", "Result", kind="static"),)

    def from_scene(form, _host) -> str:
        filled, pixels = system_selection_prefill_values(owner)
        form.values.update(filled)
        form.state["pixels"] = pixels
        recompute(form)
        return "Re-read the FOV, sensor and camera from the scene."

    def compute(form, _host) -> str:
        recompute(form)
        return ""

    form = RowForm(
        title=TITLE,
        row_index=-1,
        fields=fields,
        values=values,
        summary=("Enter the requirement -- FOV, object-space resolution and the minimum working "
                 "distance -- to size the matching camera and lens. Sensor size is the candidate "
                 "camera's; leave it blank for the pixel count only."),
        actions=(FormAction("from_scene", "↺ From scene", from_scene), FormAction("compute", "Compute", compute)),
        state=state,
        read_only=True,
    )
    recompute(form)
    return form


build_system_selection_form_model.TITLE = TITLE
