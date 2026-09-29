"""The CAD/STL placement assistant as a form (docs/design_qt_migration.md phase 5d).

"Place/Orient Selected CAD/STL Solid" opens a side panel beside the 3D view: pick which CAD-local
axis becomes layout +Z, nudge the solid by the toolbar rotation step about X, Y or Z, centre it on
the optical axis, seat its front face on the row station, and finish. The Tk panel is widgets
wired straight to the inspector; under a Qt shell that panel would be built inside the inspector's
withdrawn Toplevel and never seen. This is the same panel as a model: every button calls the same
inspector method the Tk button calls, and the status line is re-read after each one.

The form stays open across actions (a placement is a run of nudges) and closes on Done.
"""
from __future__ import annotations

from KrakenOS.UI.row_forms.base import FormAction, FormField, FormRefused, RowForm

TITLE = "Place/Orient CAD/STL Solid"
EXPLAINER = (
    "Fit Axis chooses which CAD-local axis becomes layout +Z. The +/-Rot buttons rotate the "
    "solid by the toolbar rotation step. Center X/Y moves it onto the optical axis; Front On Row "
    "places its minimum-Z face on the row station. Done -> 2D refreshes the main layout with the "
    "edited Tilt/Decenter fields."
)


def build_stl_placement_form(inspector, row_index: int) -> RowForm:
    """The placement assistant for one file-backed optical solid row of ``inspector``."""
    from KrakenOS.UI.open3d_inspector import STL_AXIS_TO_LAYOUT_Z_TILTS

    row_index = int(row_index)
    if inspector.editor._file_backed_stl_row_at(row_index) is None:
        raise FormRefused("Selected row is not a file-backed optical CAD/STL solid.")

    def status() -> str:
        return str(inspector._stl_placement_status_text(row_index))

    def set_axis(form, text: str) -> str:
        inspector.stl_axis_var.set(str(text).strip() or "+Z")
        return ""

    def step(method, *args):
        def run(form, _host) -> str:
            method(*args)
            form.values["status"] = status()
            return form.values["status"]
        return run

    def done(form, _host) -> str:
        inspector.finish_stl_placement()
        form.state["close_after"] = True
        return "Applied CAD/STL placement to the 2D layout."

    step_deg = inspector._rotation_handle_step_deg
    actions = [FormAction("fit", "Fit Axis", step(inspector._fit_stl_from_handler))]
    for axis in ("x", "y", "z"):
        actions.append(FormAction(f"{axis}_minus", f"{axis.upper()} -Rot",
                                  lambda form, host, a=axis: step(inspector._rotate_stl_from_handler,
                                                                  a, -step_deg())(form, host)))
        actions.append(FormAction(f"{axis}_plus", f"{axis.upper()} +Rot",
                                  lambda form, host, a=axis: step(inspector._rotate_stl_from_handler,
                                                                  a, step_deg())(form, host)))
    actions += [
        FormAction("center", "Center X/Y", step(inspector._center_stl_from_handler)),
        FormAction("front", "Front On Row", step(inspector._front_stl_from_handler)),
        FormAction("done", "Done -> 2D", done),
    ]
    return RowForm(
        title=f"{TITLE} (S{row_index})",
        row_index=row_index,
        fields=(
            FormField("axis", "Fit local axis to +Z", kind="choice",
                      choices=tuple(STL_AXIS_TO_LAYOUT_Z_TILTS.keys()), on_change=set_axis),
            FormField("status", "Pose", kind="static"),
        ),
        values={"axis": str(inspector.stl_axis_var.get() or "+Z"), "status": status()},
        summary=EXPLAINER,
        actions=tuple(actions),
        read_only=True,
    )
