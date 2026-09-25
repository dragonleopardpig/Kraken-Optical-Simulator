"""The Gaussian Beam Report's data (docs/design_qt_migration.md phase 3).

Extracted from the Tk dialog, which now renders what this returns. The report takes INPUTS -- the
wavelength and the input beam -- so the builder's keywords are its controls, defaulting to the
scene's own source beam when it has one.

`gaussian_cavity_eigenmode` is the "Use Cavity Eigenmode" button's model side, kept here so both
toolkits can offer it from one implementation.
"""
from __future__ import annotations

import numpy as np

import KrakenOS as Kos
from KrakenOS.UI.reports.base import (Report, ReportAction, ReportColumn, ReportFailed,
                                      ReportUpdate, ReportValue)

TITLE = "Gaussian Beam Report"

#: the Tk dialog's columns, headings and widths, in its order
_TEXT = {"name", "kind", "stable"}
_WIDE = {"q_real": 110, "q_imag": 110, "waist_offset": 110, "divergence_mrad": 110,
         "name": 150, "kind": 105}
COLUMNS = tuple(
    ReportColumn(key, heading, numeric=key not in _TEXT, width=_WIDE.get(key, 76),
                 stretch=key in {"name", "kind"})
    for key, heading in (
        ("step", "Step"), ("surface", "Surf"), ("name", "Name"), ("kind", "Kind"), ("n", "n"),
        ("A", "A"), ("B", "B"), ("C", "C"), ("D", "D"),
        ("q_real", "Re(q) [mm]"), ("q_imag", "Im(q) [mm]"), ("w_radius", "w [mm]"),
        ("w_diameter", "2w [mm]"), ("R", "Rwf [mm]"), ("waist_radius", "w0 [mm]"),
        ("waist_offset", "Waist offset [mm]"), ("z_rayleigh", "zR [mm]"),
        ("divergence_mrad", "Div [mrad]"), ("gouy_rad", "Gouy [rad]"), ("stable", "Stable"),
    )
)


def format_value(value) -> str:
    """The dialog's own formatter: a beam trace carries infinities (a collimated waist)."""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    if np.isposinf(numeric):
        return "inf"
    if np.isneginf(numeric):
        return "-inf"
    if not np.isfinite(numeric):
        return "-"
    return f"{numeric:.8g}"


def default_inputs(owner) -> dict[str, float]:
    """The values the Tk dialog opens with: the scene's source beam, or a 1 mm unit beam."""
    wavelength = float(owner._current_wavelength())
    beam = None
    try:
        if owner._current_source_model() == "Gaussian beam":
            beam = owner._current_gaussian_beam_input(wavelength)
    except Exception:
        beam = None
    return {
        "wavelength": wavelength,
        "waist": float(beam.waist_radius_mm) if beam is not None else 1.0,
        "offset": float(beam.waist_offset_mm) if beam is not None else 0.0,
        "m2": float(beam.m2) if beam is not None else 1.0,
    }


def _number(value, fallback: float) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return float(fallback)


def build_gaussian_beam_report(owner, wavelength=None, waist=None, offset=None, m2=None) -> Report:
    """Propagate the input beam through the system's paraxial matrices, step by step."""
    defaults = default_inputs(owner)
    values = {
        "wavelength": _number(wavelength, defaults["wavelength"]),
        "waist": _number(waist, defaults["waist"]),
        "offset": _number(offset, defaults["offset"]),
        "m2": _number(m2, defaults["m2"]),
    }
    try:
        system = owner.build_system(force_rebuild=True)
        paraxial = system.ParaxMatrices(values["wavelength"])
        beam = Kos.propagate_gaussian_beam(paraxial, Kos.GaussianBeamInput(
            wavelength_um=values["wavelength"],
            waist_radius_mm=values["waist"],
            waist_offset_mm=values["offset"],
            m2=values["m2"],
        ))
    except Exception as exc:
        message = getattr(owner, "short_error_message", lambda e: str(e))(exc)
        raise ReportFailed(str(message)) from exc

    rows = [{
        "step": step.step_index, "surface": step.surface_index, "name": step.surface_name,
        "kind": step.kind, "n": step.n_after, "A": step.A, "B": step.B, "C": step.C, "D": step.D,
        "q_real": step.q_real_mm, "q_imag": step.q_imag_mm, "w_radius": step.beam_radius_mm,
        "w_diameter": step.beam_diameter_mm, "R": step.wavefront_radius_mm,
        "waist_radius": step.waist_radius_mm, "waist_offset": step.waist_offset_mm,
        "z_rayleigh": step.rayleigh_range_mm, "divergence_mrad": step.divergence_mrad,
        "gouy_rad": step.gouy_phase_rad, "stable": step.stable,
    } for step in beam.steps]

    final = beam.final
    if final is None:
        summary = "No paraxial steps available."
    else:
        summary = (
            "Gaussian beam | lambda={wl:.6g} um | input w0={w0:.6g} mm | M2={m2:.6g} | "
            "final w={wf} mm | final waist offset={offset} mm | final zR={zr} mm".format(
                wl=values["wavelength"], w0=values["waist"], m2=values["m2"],
                wf=format_value(final.beam_radius_mm),
                offset=format_value(final.waist_offset_mm),
                zr=format_value(final.rayleigh_range_mm)))

    return Report(
        title=TITLE,
        summary=summary,
        columns=COLUMNS,
        rows=rows,
        display_rows=[tuple(row[column.key] if column.key in _TEXT
                            else format_value(row[column.key]) for column in COLUMNS)
                      for row in rows],
        controls=(
            ReportValue("wavelength", "Wavelength [um]", f"{values['wavelength']:.6g}"),
            ReportValue("waist", "Waist radius [mm]", f"{values['waist']:.6g}"),
            ReportValue("offset", "Waist offset [mm]", f"{values['offset']:.6g}"),
            ReportValue("m2", "M2", f"{values['m2']:.6g}"),
        ),
        actions=(ReportAction("Use Cavity Eigenmode", lambda controls: cavity_eigenmode_update(
            owner, controls), needs_controls=True),),
        status="Gaussian beam report refreshed.",
    )


def gaussian_cavity_eigenmode(owner, wavelength, m2):
    """The "Use Cavity Eigenmode" button's model side: the resonator's own mode, or why not."""
    wavelength_value = _number(wavelength, default_inputs(owner)["wavelength"])
    system = owner.build_system(force_rebuild=True)
    paraxial = system.ParaxMatrices(wavelength_value)
    return Kos.solve_gaussian_cavity_eigenmode(
        paraxial, wavelength_um=wavelength_value,
        m2=_number(m2, default_inputs(owner)["m2"]))


def cavity_eigenmode_update(owner, controls) -> ReportUpdate:
    """"Use Cavity Eigenmode" as data: the waist and offset to adopt, or why the cavity cannot.

    An unstable resonator has no eigenmode, so nothing is written back and the message says what
    g was -- the Tk dialog has always reported that, and now Qt does too.
    """
    try:
        eigenmode = gaussian_cavity_eigenmode(owner, controls.get("wavelength"),
                                              controls.get("m2"))
    except Exception as exc:
        message = getattr(owner, "short_error_message", lambda e: str(e))(exc)
        return ReportUpdate(status=f"Cavity eigenmode failed: {message}", rebuild=False)
    if not eigenmode.stable:
        return ReportUpdate(
            status=(f"Cavity eigenmode unavailable: {eigenmode.message}; "
                    f"g={format_value(eigenmode.stability_parameter)}"),
            rebuild=False)
    return ReportUpdate(
        status=("Cavity eigenmode applied: "
                f"q={format_value(eigenmode.q_real_mm)}+i{format_value(eigenmode.q_imag_mm)} mm, "
                f"w0={format_value(eigenmode.waist_radius_mm)} mm, "
                f"g={format_value(eigenmode.stability_parameter)}, "
                f"Gouy/RT={format_value(eigenmode.round_trip_gouy_rad)} rad."),
        controls={"waist": format_value(eigenmode.waist_radius_mm),
                  "offset": format_value(eigenmode.q_real_mm)})


build_gaussian_beam_report.TITLE = TITLE
