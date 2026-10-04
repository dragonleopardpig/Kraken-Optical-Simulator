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

from KrakenOS.UI.coherent_detector_analysis import COHERENT_SUM_MODE_VALUES
from KrakenOS.UI.source_trace_helpers import (ATMOS_PLOT_MODE_VALUES, GAUSSIAN_INPUT_MODE_VALUES,
                                              GAUSSIAN_WAIST_SIDE_VALUES, PUPIL_PATTERN_VALUES,
                                              RAY_FAN_COUNT_VALUES,
                                              SOURCE_ANGULAR_WEIGHT_VALUES,
                                              SOURCE_DIRECTION_PRESET_VALUES,
                                              SOURCE_MODEL_VALUES)
from KrakenOS.UI.tolerance_constants import TOLERANCE_COMPARE_VIEW_VALUES

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

#: the folded trace's detector policy and the wavefront plot's styles. Literals in
#: `layout_editor` until 0902; they live here so the catalogue need not import the editor, and
#: the editor re-exports them under the same names
FOLDED_DETECTOR_POLICY_TRACE = "Trace events"
FOLDED_DETECTOR_POLICY_DISPLAY = "Display compatibility"
FOLDED_DETECTOR_POLICY_VALUES = (FOLDED_DETECTOR_POLICY_TRACE, FOLDED_DETECTOR_POLICY_DISPLAY)
FOLDED_DETECTOR_POLICY_DEFAULT = FOLDED_DETECTOR_POLICY_TRACE
WAVEFRONT_FUNCTION_STYLE = "Wavefront Function"
WAVEFRONT_PHASE_STYLE = "Phase (unwrapped)"
WAVEFRONT_STYLE_DEFAULT = WAVEFRONT_FUNCTION_STYLE
WAVEFRONT_STYLE_VALUES = (
    WAVEFRONT_STYLE_DEFAULT,
    WAVEFRONT_PHASE_STYLE,
    "Wrapped phase",
    "Interferogram",
    "Slope X",
    "Slope Y",
    "Slope magnitude",
)
TRACE_MODES = ("Auto", "Non-Sequential Preview", "Sequential", "Folded Preview")
SPOT_VIEW_MODES = ("Grid", "Absolute", "Centroid")

APERTURE_TYPES = ("STOP", "EPD", "FNO")
OBJECT_MODES = ("Finite", "Infinity")
FIELD_TYPE_LABELS = tuple(FIELD_TYPE_DISPLAY_LABELS.get(value, value)
                          for value in FIELD_TYPE_CANONICAL_VALUES)


@dataclass(frozen=True)
class SystemControl:
    """One input: the variable it edits, what to call it, and what to do after a change.

    `kind` is "text", "choice" or "bool" (a checkbox over a boolean variable).
    """

    key: str
    label: str
    kind: str = "text"
    choices: tuple = ()
    #: the editor method to call once the value is committed
    commit: str = "commit_trace_controls"
    #: a model variable holding the label, when the label itself depends on the system
    label_key: str = ""
    #: the editor method saying whether this input matters right now; empty = always. These
    #: were lambdas inside the Tk layout (bugs/0902), so no other view could know them
    relevant: str = ""
    #: the editor method returning the choices, for a list the model fills at runtime
    choices_from: str = ""

    def is_relevant(self, owner) -> bool:
        """Whether the input applies to the system as it is now -- the model's own rule."""
        if not self.relevant:
            return True
        rule = getattr(owner, self.relevant, None)
        if rule is None:
            return True
        try:
            return bool(rule())
        except Exception:
            return True

    def choices_for(self, owner) -> tuple:
        """The choices to offer: the model's live list when it keeps one, else the fixed one."""
        if self.choices_from:
            source = getattr(owner, self.choices_from, None)
            if source is not None:
                try:
                    return tuple(str(choice) for choice in source())
                except Exception:
                    pass
        return tuple(str(choice) for choice in self.choices)

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
                  commit="_on_object_mode_changed", relevant="_default_source_selected"),
    SystemControl("wavelength_var", "Wavelength [um]"),
    SystemControl("ray_count_var", "Ray fan count", "choice", RAY_FAN_COUNT_VALUES),
    SystemControl("aperture_type_var", "Aperture type", "choice", APERTURE_TYPES),
    SystemControl("aperture_value_var", "Aperture value"),
    SystemControl("field_type_var", "Field type", "choice", FIELD_TYPE_LABELS,
                  commit="_on_field_type_changed",
                  relevant="_default_source_selected"),
    SystemControl("field_value_var", "Field value", commit="commit_field_controls",
                  label_key="field_value_label_var",
                  relevant="_default_source_selected"),
    SystemControl("field_count_var", "Field samples", commit="commit_field_controls",
                  relevant="_default_source_selected"),
)


#: the SOURCE: what launches the light, as opposed to the system it goes through (bugs/0901)
SOURCE_CONTROLS = (
    SystemControl("source_model_var", "Source model", "choice", SOURCE_MODEL_VALUES,
                  commit="_on_source_model_changed"),
    SystemControl("pupil_pattern_var", "Pupil pattern", "choice", PUPIL_PATTERN_VALUES,
                  commit="_on_source_model_changed",
                  relevant="_default_source_selected"),
    SystemControl("source_radius_var", "Source radius [mm]", commit="commit_source_controls",
                  relevant="_source_radius_applies"),
    SystemControl("source_cone_angle_var", "Cone half-angle [deg]",
                  commit="commit_source_controls",
                  relevant="_source_cone_applies"),
    SystemControl("gaussian_input_mode_var", "GB input mode", "choice",
                  GAUSSIAN_INPUT_MODE_VALUES, commit="_on_source_model_changed",
                  relevant="_gaussian_source_selected"),
    SystemControl("gaussian_waist_radius_var", "GB waist [mm]", commit="commit_source_controls",
                  relevant="_gaussian_waist_inputs_apply"),
    SystemControl("gaussian_waist_offset_var", "GB waist offset [mm]",
                  commit="commit_source_controls",
                  relevant="_gaussian_waist_inputs_apply"),
    SystemControl("gaussian_beam_diameter_var", "GB diameter [mm]",
                  commit="commit_source_controls",
                  relevant="_gaussian_divergence_inputs_apply"),
    SystemControl("gaussian_full_divergence_var", "GB full div [mrad]",
                  commit="commit_source_controls",
                  relevant="_gaussian_divergence_inputs_apply"),
    SystemControl("gaussian_m2_var", "GB M2", commit="commit_source_controls",
                  relevant="_gaussian_source_selected"),
    SystemControl("gaussian_waist_side_var", "GB waist side", "choice",
                  GAUSSIAN_WAIST_SIDE_VALUES, commit="_on_source_model_changed",
                  relevant="_gaussian_divergence_inputs_apply"),
    SystemControl("pupil_rad_var", "Pupil r [0..1]", commit="commit_source_controls",
                  relevant="_pupil_r_theta_applies"),
    SystemControl("pupil_theta_var", "Pupil theta [deg]", commit="commit_source_controls",
                  relevant="_pupil_r_theta_applies"),
    SystemControl("source_power_var", "Source power [arb]", commit="commit_source_controls",
                  relevant="_physical_source_selected"),
    SystemControl("source_seed_var", "Random seed", commit="commit_source_controls",
                  relevant="_random_seed_applies"),
    SystemControl("source_x_var", "Source X [mm]", commit="commit_source_controls",
                  relevant="_physical_source_selected"),
    SystemControl("source_y_var", "Source Y [mm]", commit="commit_source_controls",
                  relevant="_physical_source_selected"),
    SystemControl("source_z_var", "Source Z [mm]", commit="commit_source_controls",
                  relevant="_physical_source_selected"),
    SystemControl("source_l_var", "Source L", commit="commit_source_controls",
                  relevant="_physical_source_selected"),
    SystemControl("source_m_var", "Source M", commit="commit_source_controls",
                  relevant="_physical_source_selected"),
    SystemControl("source_n_var", "Source N", commit="commit_source_controls",
                  relevant="_physical_source_selected"),
    SystemControl("source_direction_preset_var", "Direction preset", "choice",
                  SOURCE_DIRECTION_PRESET_VALUES,
                  commit="_on_source_direction_preset_changed",
                  relevant="_physical_source_selected"),
    SystemControl("source_angular_weight_var", "SourceRnd angular weight", "choice",
                  SOURCE_ANGULAR_WEIGHT_VALUES, commit="_on_source_model_changed",
                  relevant="_angular_weight_applies"),
)

#: how the trace runs and what the analysis plots show (bugs/0902) -- the rest of the Tk
#: trace/display panel. Three lists here are the model's live ones (surfaces, analysis paths),
#: and five inputs only matter for particular plots or sources.
TRACE_CONTROLS = (
    SystemControl("ray_height_factor_var", "Pupil factor",
                  relevant="_default_source_selected"),
    SystemControl("analysis_surface_var", "Analysis stop surface", "choice", ("Auto",),
                  commit="_mark_plot_update_pending", choices_from="analysis_surface_options"),
    SystemControl("spot_view_mode_var", "Spot view", "choice", SPOT_VIEW_MODES,
                  commit="_mark_plot_update_pending"),
    SystemControl("trace_mode_var", "Scene trace", "choice", TRACE_MODES,
                  commit="_on_trace_mode_changed"),
    SystemControl("nonseq_target_surface_var", "NS target", "choice", ("Auto",),
                  commit="_mark_plot_update_pending", choices_from="analysis_surface_options"),
    SystemControl("nonseq_ns_limit_var", "NS hit limit"),
    SystemControl("folded_detector_policy_var", "Folded reach", "choice",
                  FOLDED_DETECTOR_POLICY_VALUES, commit="_mark_plot_update_pending",
                  relevant="_folded_detector_policy_control_enabled"),
    SystemControl("nonseq_energy_probability_var", "NS probabilistic coating split", "bool",
                  commit="_mark_plot_update_pending"),
    SystemControl("wavefront_style_var", "Wavefront style", "choice", WAVEFRONT_STYLE_VALUES,
                  commit="_mark_plot_update_pending"),
    SystemControl("tolerance_compare_view_var", "Tolerance compare", "choice",
                  TOLERANCE_COMPARE_VIEW_VALUES, commit="_mark_plot_update_pending",
                  relevant="_tolerance_compare_selected"),
    SystemControl("show_clipped_rays_var", "Show clipped rays", "bool",
                  commit="_mark_plot_update_pending"),
    SystemControl("analysis_branch_filter_var", "Analysis path", "choice", ("All paths",),
                  commit="_mark_plot_update_pending", choices_from="analysis_branch_options"),
    SystemControl("detector_bins_var", "Detector bins", relevant="_detector_plot_selected"),
    SystemControl("coherent_sum_mode_var", "Coherent sum", "choice", COHERENT_SUM_MODE_VALUES,
                  commit="_mark_plot_update_pending", relevant="_coherent_plot_selected"),
    SystemControl("branch_field_propagation_mm_var", "BField z [mm]",
                  relevant="_branch_field_selected"),
)

#: every group a shell can render, in the order the Tk panels stack them
CONTROL_GROUPS = (("System", SYSTEM_CONTROLS), ("Source", SOURCE_CONTROLS),
                  ("Trace", TRACE_CONTROLS))


def control_for(key: str) -> "SystemControl | None":
    for _title, group in CONTROL_GROUPS:
        for control in group:
            if control.key == key:
                return control
    return None



# ---- the atmosphere (bugs/0954) -----------------------------------------------------------------
ATMOSPHERE_TITLE = "Atmospheric Settings"
ATMOSPHERE_NOTE = ("Atmospheric refraction/dispersion settings are advanced analysis inputs. "
                   "Use the Atmos analysis button after changing these values.")
#: (label, model variable, default) of the ten numbers -- the Tk panel builds its entries from
#: this list and the Qt dialog its form, so the two cannot name a different set
ATMOSPHERE_CONTROL_SPECS = (
    ("Min wavelength [um]", "atmos_wavelength_min_var", "0.45"),
    ("Max wavelength [um]", "atmos_wavelength_max_var", "0.75"),
    ("Samples", "atmos_wavelength_count_var", "11"),
    ("Zenith angle [deg]", "atmos_zenith_deg_var", "45.0"),
    ("Temperature [K]", "atmos_temperature_k_var", "283.15"),
    ("Pressure [Pa]", "atmos_pressure_pa_var", "101300"),
    ("Humidity [0-1]", "atmos_humidity_var", "0.5"),
    ("CO2 [ppm]", "atmos_co2_ppm_var", "400"),
    ("Latitude [deg]", "atmos_latitude_deg_var", "31.0"),
    ("Altitude [m]", "atmos_altitude_m_var", "2800"),
)
#: the observatory preset fills six of the numbers; the plot choice and every number mark the
#: plot stale, as the Tk window's boxes do
ATMOSPHERE_CONTROLS = (
    SystemControl("atmos_observatory_var", "Observatory preset", "choice", ("Manual",),
                  commit="_on_atmos_observatory_changed", choices_from="_atmos_observatory_names"),
    SystemControl("atmos_plot_mode_var", "Atmos plot", "choice", ATMOS_PLOT_MODE_VALUES,
                  commit="_mark_plot_update_pending"),
) + tuple(SystemControl(variable, label) for label, variable, _default in ATMOSPHERE_CONTROL_SPECS)
