"""The inputs that define a system, toolkit-free (docs/design_qt_migration.md phase 6).

Object mode, wavelength, ray fan count, aperture and field: the handful of controls that decide
what is traced. Their labels and their choices were literals inside two Tk panels, so the Qt
shell -- which since 0899 can pick plots and press Update -- had nothing to set up (bugs/0900).

Each control names the MODEL VARIABLE it edits. Those variables are declared in
`model_variables.py` and carry `trace_add` whether a Tk panel or a UI host made them, so a view
binds to one exactly as the Qt status bar binds to `status_var`: no new plumbing, and the model
stays the only thing that decides what a value means.
"""
from __future__ import annotations

from dataclasses import dataclass

from KrakenOS.UI.source_trace_helpers import RAY_FAN_COUNT_VALUES

#: the field types a system can be specified in, and how the UI names each. They lived in
#: `layout_editor` with a second copy in `open3d_inspector`; both import them from here now, so
#: a view that needs the list does not have to import the editor (bugs/0900)
FIELD_TYPE_CANONICAL_VALUES = (
    "Angle",
    "Object Height",
    "Paraxial Image Height",
    "Real Image Height",
)
FIELD_TYPE_DISPLAY_LABELS = {
    "Angle": "Field Half-Angle",
    "Object Height": "Object Semi-Height",
    "Paraxial Image Height": "Paraxial Image Semi-Height",
    "Real Image Height": "Real Image Semi-Height",
}

APERTURE_TYPES = ("STOP", "EPD", "FNO")
OBJECT_MODES = ("Finite", "Infinity")
FIELD_TYPE_LABELS = tuple(FIELD_TYPE_DISPLAY_LABELS.get(value, value)
                          for value in FIELD_TYPE_CANONICAL_VALUES)


@dataclass(frozen=True)
class SystemControl:
    """One input: the variable it edits, what to call it, and what to do after a change."""

    key: str
    label: str
    kind: str = "text"
    choices: tuple = ()
    #: the editor method to call once the value is committed
    commit: str = "commit_trace_controls"
    #: a model variable holding the label, when the label itself depends on the system
    label_key: str = ""

    def label_for(self, owner) -> str:
        """The label to show -- the model's own when this control has a live one."""
        if self.label_key:
            variable = getattr(owner, self.label_key, None)
            if variable is not None:
                try:
                    text = str(variable.get()).strip()
                except Exception:
                    text = ""
                if text:
                    return text
        return self.label


SYSTEM_CONTROLS = (
    SystemControl("object_mode_var", "Object mode", "choice", OBJECT_MODES,
                  commit="_on_object_mode_changed"),
    SystemControl("wavelength_var", "Wavelength [um]"),
    SystemControl("ray_count_var", "Ray fan count", "choice", RAY_FAN_COUNT_VALUES),
    SystemControl("aperture_type_var", "Aperture type", "choice", APERTURE_TYPES),
    SystemControl("aperture_value_var", "Aperture value"),
    SystemControl("field_type_var", "Field type", "choice", FIELD_TYPE_LABELS,
                  commit="_on_field_type_changed"),
    SystemControl("field_value_var", "Field value", commit="commit_field_controls",
                  label_key="field_value_label_var"),
    SystemControl("field_count_var", "Field samples", commit="commit_field_controls"),
)


def control_for(key: str) -> "SystemControl | None":
    return next((control for control in SYSTEM_CONTROLS if control.key == key), None)
