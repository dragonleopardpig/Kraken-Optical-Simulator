"""The Beam Splitter row form (docs/design_qt_migration.md phase 3).

The settings, their validation, their summary and the coating they imply already live on the
editor (`services/layout_table_workbench.py`). This module is what a dialog needs on top: which
fields there are, what the row currently holds, and what applying means -- so the Tk dialog and
the Qt dialog agree by construction rather than by two implementations that happen to match.
"""
from __future__ import annotations

from KrakenOS.UI.row_forms.base import FormField, FormRefused, RowForm

TITLE = "Beam Splitter"
NOTE = (
    "Beam Splitter can spawn deterministic transmitted and reflected child paths in "
    "Non-Sequential Preview. For a finite plate, use this row as the coated front face, set Glass "
    "to the substrate and Thickness to the plate thickness, then add a following Standard rear "
    "face with Glass=AIR and the same TiltX for a parallel plate. Use a different rear tilt to "
    "model a wedge. Deterministic coating table mode reads the row Coating table at trace "
    "wavelength and incidence angle. Fresnel P/S mode uses KrakenOS dielectric/metal P and S "
    "coefficients with a scalar P-polarization fraction."
)

#: (settings key, label, hint) -- the Tk dialog's own order and wording
NUMBERS = (
    ("reflectance", "Reflectance R", "Fixed mode value; fallback for coating-table mode."),
    ("absorption", "Absorption A", "Fixed mode value; fallback for coating-table mode."),
    ("polarization_p_fraction", "P fraction",
     "Fresnel P/S mode: 1.0 pure P, 0.0 pure S, 0.5 equal P/S."),
    ("polarization_s_phase_deg", "S phase [deg]",
     "Relative S component phase for Jones metadata; 90 deg gives circular at Pfrac=0.5."),
    ("transmit_phase_deg", "T phase [deg]",
     "Metadata used by current coherent-detector diagnostics."),
    ("reflect_phase_deg", "R phase [deg]",
     "Metadata used by current coherent-detector diagnostics."),
    ("transmit_s_phase_deg", "T S phase [deg]", "S-component transmitted phase metadata."),
    ("reflect_s_phase_deg", "R S phase [deg]", "S-component reflected phase metadata."),
    ("min_branch_power", "Min branch power", "Child paths below this power are not spawned."),
)
INT_FIELDS = (("max_branch_depth", "Max branch depth", "How deep a split chain may go."),)


def model(owner):
    """The beam splitter's model side, wherever the caller keeps it.

    The METHODS (normalize / validate / summary / coating) are on the editor. The CONSTANTS are
    module-level -- `BEAM_SPLITTER_SURFACE` in `trace_intent.py`, the attribute name and the split
    modes in `services/beam_scatter_metadata.py` -- and are injected into the Tk dialog shell, so
    they are absent from the editor itself. Prefer whatever the owner carries and fall back to the
    defining module: one builder then serves the Tk shell and the editor alike.
    """
    from types import SimpleNamespace

    from KrakenOS.UI.services import beam_scatter_metadata as metadata
    from KrakenOS.UI.trace_intent import BEAM_SPLITTER_SURFACE

    def held(name, fallback):
        value = getattr(owner, name, None)
        return fallback if value is None else value

    return SimpleNamespace(
        surface=held("beam_splitter_surface", BEAM_SPLITTER_SURFACE),
        attr=held("beam_splitter_advanced_attr", metadata.BEAM_SPLITTER_ADVANCED_ATTR),
        split_modes=tuple(held("beam_splitter_split_modes", metadata.BEAM_SPLITTER_SPLIT_MODES)),
        normalize=held("normalize_beam_splitter_settings",
                       metadata._normalize_beam_splitter_settings),
        validate=held("validate_beam_splitter_settings",
                      metadata._validate_beam_splitter_settings),
        coating_for=held("beam_splitter_coating_for_settings",
                         metadata._beam_splitter_coating_for_settings),
        summary=held("beam_splitter_summary", metadata._beam_splitter_summary),
    )


def fields(owner) -> tuple[FormField, ...]:
    return (
        FormField("split_mode", "Split mode", kind="choice",
                  choices=model(owner).split_modes, width=30),
        *[FormField(key, label, kind="number", hint=hint) for key, label, hint in NUMBERS],
        *[FormField(key, label, kind="int", hint=hint) for key, label, hint in INT_FIELDS],
    )


def _candidate(owner, values: dict) -> dict:
    """Text fields -> the model's own normalised settings. Raises FormRefused on junk."""
    try:
        return model(owner).normalize({
            "split_mode": str(values.get("split_mode", "")).strip(),
            **{key: float(values[key]) for key, _label, _hint in NUMBERS},
            "max_branch_depth": int(float(values["max_branch_depth"])),
        })
    except FormRefused:
        raise
    except Exception as exc:
        raise FormRefused(str(exc)) from exc


def build_beam_splitter_form(owner, row_index: "int | None" = None) -> RowForm:
    """The form for one Beam Splitter row. Raises FormRefused when there is no such row."""
    if row_index is None:
        row_index = owner._selected_surface_row_index()
    if row_index is None or row_index < 0 or row_index >= len(owner.rows):
        raise FormRefused("Select a Beam Splitter row first.")
    parts = model(owner)
    row = owner.rows[row_index]
    if row.surface != parts.surface:
        raise FormRefused("Beam splitter settings apply only to Beam Splitter rows.")

    settings = parts.normalize(dict(row.advanced or {}).get(parts.attr))
    values = {"split_mode": str(settings["split_mode"]),
              "max_branch_depth": str(int(settings["max_branch_depth"]))}
    values.update({key: f"{float(settings[key]):.6g}" for key, _label, _hint in NUMBERS})

    def validate(candidate_values: dict) -> list[str]:
        try:
            candidate = _candidate(owner, candidate_values)
        except FormRefused as exc:
            return [str(exc)]
        return list(parts.validate(candidate))

    def describe(candidate_values: dict) -> str:
        return parts.summary(_candidate(owner, candidate_values))

    def apply(candidate_values: dict) -> str:
        candidate = _candidate(owner, candidate_values)
        errors = parts.validate(candidate)
        if errors:
            raise FormRefused("Fix these values before applying:\n\n"
                              + "\n".join(f"- {error}" for error in errors))
        owner._begin_history_capture()
        advanced = dict(owner.rows[row_index].advanced or {})
        advanced[parts.attr] = candidate
        advanced["Coating"] = parts.coating_for(candidate, advanced.get("Coating"))
        owner.rows[row_index].advanced = advanced
        owner.rows[row_index].surface = parts.surface
        if str(owner.rows[row_index].glass).upper() == "MIRROR":
            owner.rows[row_index].glass = "AIR"
        owner._sync_table()
        owner._select_table_row(row_index)
        owner._commit_history_capture()
        owner._mark_plot_update_pending()
        status = (f"Updated beam splitter S{row_index}: "
                  f"{parts.summary(candidate)}. Click Update.")
        # LAST, after the model's own selection and sync writes: the Tk dialog set it here too,
        # and a Qt status bar bound to status_var then shows the same line.
        owner.status_var.set(status)
        return status

    return RowForm(
        title=f"{TITLE} - S{row_index}: {row.name}",
        row_index=row_index,
        fields=fields(owner),
        values=values,
        summary=parts.summary(settings),
        validate=validate,
        apply=apply,
        describe=describe,
        note=NOTE,
    )


build_beam_splitter_form.TITLE = TITLE
