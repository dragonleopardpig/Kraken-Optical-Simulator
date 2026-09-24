"""The Diffuse / BRDF row form (docs/design_qt_migration.md phase 3).

Same shape as the beam splitter form, with two things the framework had not met: a MULTI-LINE
field (the pySCATMECH backend parameters) and a choice list COMPUTED from the layout (which other
surface to importance-sample towards).

The settings, their normalisation and their validation live in
`services/beam_scatter_metadata.py`; the backend probe and the parameter formatter live in
`KrakenOS/scatter_backend.py`. This module is what a dialog needs on top.
"""
from __future__ import annotations

from KrakenOS.UI.row_forms.base import FormField, FormRefused, RowForm

TITLE = "Diffuse / BRDF"
NOTE = (
    "Built-in Lambertian, Oren-Nayar, and Cosine Lobe scattering spawn deterministic "
    "non-sequential child rays. pySCATMECH BRDF keeps the same deterministic branch layout but "
    "uses SCATMECH BRDF weights when the optional SCATPY extension is installed."
)
MODELS = ("Lambertian", "Oren-Nayar", "Cosine Lobe", "pySCATMECH BRDF")
BACKENDS = ("Built-in", "pySCATMECH")

#: (key, label, kind, default shown in the hint, hint) -- the Tk dialog's own order and wording
SPEC = (
    ("model", "Model", "choice", "Lambertian",
     "Lambertian is matte, Oren-Nayar is rough diffuse, and Cosine Lobe is glossy/specular-lobe "
     "scatter."),
    ("backend", "Backend", "choice", "Built-in",
     "Use Built-in for dependency-free scatter, or pySCATMECH for an optional BRDF backend."),
    ("backend_model", "Backend model", "text", "Microroughness_BRDF_Model",
     "pySCATMECH only: BRDF model class name."),
    ("reflectance", "Reflectance", "number", "0.8", "Diffuse albedo in [0, 1]."),
    ("sample_count", "Scatter samples", "int", "9",
     "Number of deterministic child rays per hit."),
    ("max_scatter_angle_deg", "Max scatter angle [deg]", "number", "90",
     "90 deg is the physical Lambertian hemisphere; lower values are preview cones."),
    ("lobe_exponent", "Lobe exponent", "number", "20",
     "Cosine Lobe only: higher values make a narrower glossy lobe."),
    ("roughness_deg", "Roughness [deg]", "number", "20",
     "Oren-Nayar only: sigma roughness angle in degrees."),
    ("min_branch_power", "Min branch power", "number", "1e-4",
     "Branches below this total power are not spawned."),
    ("max_branch_depth", "Max scatter depth", "int", "2",
     "Maximum recursive diffuse hits per launched ray."),
    ("target_surface", "Guided target surface", "choice", "None",
     "Optional surface to importance-sample, such as a pupil, lens, detector, or Image."),
    ("target_radius_scale", "Target radius scale", "number", "1.0",
     "Scales the selected target surface clear radius for guided sampling."),
    ("backend_parameters", "Backend parameters", "textarea", "{}",
     "pySCATMECH only: JSON or Python dict. Use __model__ for nested SCATMECH model names, for "
     'example {"psd": {"__model__": "Gaussian_PSD_Function", "sigma": 0.05, "length": 1.0}}.'),
)


def model(owner):
    """The diffuse scatter model, wherever the caller keeps it (see row_forms.beam_splitter)."""
    from types import SimpleNamespace

    from KrakenOS.scatter_backend import format_pyscatmech_parameters, pyscatmech_status
    from KrakenOS.UI.services import beam_scatter_metadata as metadata
    from KrakenOS.UI.trace_intent import DIFFUSE_OBJECT_SURFACE

    def held(name, fallback):
        value = getattr(owner, name, None)
        return fallback if value is None else value

    return SimpleNamespace(
        surface=held("diffuse_object_surface", DIFFUSE_OBJECT_SURFACE),
        attr=held("diffuse_scatter_advanced_attr", metadata.DIFFUSE_SCATTER_ADVANCED_ATTR),
        defaults=dict(held("diffuse_scatter_default_settings",
                           metadata.DIFFUSE_SCATTER_DEFAULT_SETTINGS)),
        normalize=held("normalize_diffuse_scatter_settings",
                       metadata._normalize_diffuse_scatter_settings),
        validate=held("validate_diffuse_scatter_settings",
                      metadata._validate_diffuse_scatter_settings),
        status=held("pyscatmech_status", pyscatmech_status),
        format_parameters=held("format_pyscatmech_parameters", format_pyscatmech_parameters),
    )


def target_options(owner, row_index: int) -> tuple[str, ...]:
    """Every OTHER row, as the Tk dialog lists them, plus "None"."""
    options = ["None"]
    for index, row in enumerate(owner.rows):
        if index == row_index:
            continue
        options.append(f"{index}: {row.name or row.surface}")
    return tuple(options)


def target_label(settings, options: tuple[str, ...]) -> str:
    """The option that names the settings' target surface."""
    target = settings.get("target_surface")
    if target is None:
        return "None"
    prefix = f"{int(target)}:"
    return next((option for option in options if option.startswith(prefix)), prefix.rstrip(":"))


def build_diffuse_scatter_form(owner, row_index: "int | None" = None) -> RowForm:
    """The form for one Diffuse Object row. Raises FormRefused when there is no such row."""
    if row_index is None:
        row_index = owner._selected_surface_row_index()
    if row_index is None or row_index < 0 or row_index >= len(owner.rows):
        raise FormRefused("Select a Diffuse Object row first.")
    parts = model(owner)
    row = owner.rows[row_index]
    if row.surface != parts.surface:
        raise FormRefused("Diffuse scatter settings apply only to Diffuse Object rows.")

    settings = parts.normalize(dict(row.advanced or {}).get(parts.attr))
    options = target_options(owner, row_index)

    fields = []
    values: dict[str, str] = {}
    for key, label, kind, default, hint in SPEC:
        choices = ()
        if kind == "choice":
            choices = {"model": MODELS, "backend": BACKENDS}.get(key, options)
        fields.append(FormField(key, label, kind=kind, choices=tuple(choices),
                                hint=f"Default: {default}. {hint}",
                                width=34 if key == "target_surface" else 28 if choices else 18))
        if key == "target_surface":
            values[key] = target_label(settings, options)
        elif key == "backend_parameters":
            values[key] = parts.format_parameters(settings.get("backend_parameters"))
        else:
            values[key] = str(settings[key])

    def candidate(form_values: dict) -> dict:
        try:
            return parts.normalize({
                "model": str(form_values.get("model", "")).strip() or "Lambertian",
                "backend": str(form_values.get("backend", "")).strip() or "Built-in",
                "backend_model": (str(form_values.get("backend_model", "")).strip()
                                  or parts.defaults["backend_model"]),
                "backend_parameters": str(form_values.get("backend_parameters", "")).strip(),
                **{key: str(form_values.get(key, "")).strip()
                   for key, _label, kind, _default, _hint in SPEC
                   if kind in ("number", "int") or key == "target_surface"},
                "polarization": parts.defaults["polarization"],
            })
        except FormRefused:
            raise
        except Exception as exc:
            raise FormRefused(str(exc)) from exc

    def validate(form_values: dict) -> list[str]:
        try:
            return list(parts.validate(candidate(form_values)))
        except FormRefused as exc:
            return [str(exc)]

    def describe(form_values: dict) -> str:
        settings_now = candidate(form_values)
        return (f"{settings_now['model']} via {settings_now['backend']}, "
                f"reflectance {settings_now['reflectance']}, "
                f"{settings_now['sample_count']} samples")

    def apply(form_values: dict) -> str:
        errors = validate(form_values)
        if errors:
            raise FormRefused("Fix these values before applying:\n\n"
                              + "\n".join(f"- {error}" for error in errors))
        settings_now = candidate(form_values)
        owner._begin_history_capture()
        target_row = owner.rows[row_index]
        target_row.surface = parts.surface
        target_row.glass = "MIRROR"
        advanced = dict(target_row.advanced or {})
        advanced[parts.attr] = settings_now
        target_row.advanced = advanced
        owner._sync_table()
        owner._select_table_row(row_index)
        owner._commit_history_capture()
        owner._mark_plot_update_pending()
        status = f"Updated Diffuse Object settings on S{row_index}. Click Update to trace."
        owner.status_var.set(status)
        return status

    backend = parts.status()
    note = NOTE
    if not backend.get("available"):
        reason = str(backend.get("reason", "") or "").strip()
        note = f"{NOTE}\n\npySCATMECH is not available{f': {reason}' if reason else '.'}"

    return RowForm(
        title=f"{TITLE} - S{row_index}: {row.name}",
        row_index=row_index,
        fields=tuple(fields),
        values=values,
        summary=describe(values),
        validate=validate,
        apply=apply,
        describe=describe,
        note=note,
    )


build_diffuse_scatter_form.TITLE = TITLE
