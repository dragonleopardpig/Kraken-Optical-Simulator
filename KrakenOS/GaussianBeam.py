from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np


@dataclass(frozen=True)
class GaussianBeamInput:
    """Input state for paraxial Gaussian beam propagation.

    Wavelength is in micrometers to match KrakenOS. All length outputs and
    inputs are in millimeters.
    """

    wavelength_um: float
    waist_radius_mm: float
    waist_offset_mm: float = 0.0
    m2: float = 1.0
    input_index: float | None = None


@dataclass(frozen=True)
class GaussianBeamStep:
    step_index: int
    surface_index: int
    surface_name: str
    kind: str
    label: str
    n_before: float
    n_after: float
    A: float
    B: float
    C: float
    D: float
    q_real_mm: float
    q_imag_mm: float
    beam_radius_mm: float
    beam_diameter_mm: float
    wavefront_radius_mm: float
    waist_radius_mm: float
    waist_offset_mm: float
    rayleigh_range_mm: float
    divergence_mrad: float
    gouy_phase_rad: float
    stable: bool


@dataclass(frozen=True)
class GaussianBeamTrace:
    beam: GaussianBeamInput
    steps: Tuple[GaussianBeamStep, ...]
    input_index: float
    input_q: complex
    input_rayleigh_range_mm: float
    wavelength_mm: float

    @property
    def final(self) -> GaussianBeamStep | None:
        return self.steps[-1] if self.steps else None


@dataclass(frozen=True)
class AstigmaticGaussianBeamInput:
    """Independent tangential/sagittal Gaussian beam input states."""

    tangential: GaussianBeamInput
    sagittal: GaussianBeamInput


@dataclass(frozen=True)
class AstigmaticGaussianBeamTrace:
    """Independent tangential/sagittal Gaussian q-parameter traces."""

    beam: AstigmaticGaussianBeamInput
    tangential: GaussianBeamTrace
    sagittal: GaussianBeamTrace

    @property
    def final_tangential(self) -> GaussianBeamStep | None:
        return self.tangential.final

    @property
    def final_sagittal(self) -> GaussianBeamStep | None:
        return self.sagittal.final

    @property
    def stable(self) -> bool:
        final_t = self.final_tangential
        final_s = self.final_sagittal
        return bool(final_t is not None and final_s is not None and final_t.stable and final_s.stable)


@dataclass(frozen=True)
class BranchGaussianQStep:
    """Astigmatic Gaussian q state after one traced branch hit.

    The step is intentionally tied to Ray Inspector style hit dictionaries:
    distance/op are in millimeters, wavelength is inherited from the input
    beam, and tangential/sagittal axes are the branch-local ``GB T``/``GB S``
    frame attached to the hit record.
    """

    step_index: int
    surface_index: int
    surface_name: str
    event: str
    branch_id: int
    branch_path: str
    distance_mm: float
    optical_path_mm: float
    n_before: float
    n_after: float
    incidence_deg: float
    tangential_A: float
    tangential_B: float
    tangential_C: float
    tangential_D: float
    sagittal_A: float
    sagittal_B: float
    sagittal_C: float
    sagittal_D: float
    tangential_q_real_mm: float
    tangential_q_imag_mm: float
    sagittal_q_real_mm: float
    sagittal_q_imag_mm: float
    tangential_beam_radius_mm: float
    sagittal_beam_radius_mm: float
    tangential_wavefront_radius_mm: float
    sagittal_wavefront_radius_mm: float
    tangential_waist_radius_mm: float
    sagittal_waist_radius_mm: float
    tangential_waist_offset_mm: float
    sagittal_waist_offset_mm: float
    tangential_rayleigh_range_mm: float
    sagittal_rayleigh_range_mm: float
    tangential_gouy_phase_rad: float
    sagittal_gouy_phase_rad: float
    tangential_stable: bool
    sagittal_stable: bool
    clear_radius_mm: float
    obscuration_radius_mm: float
    clip_transmission: float
    clip_loss: float
    cumulative_clip_transmission: float
    cumulative_clip_loss: float
    surface_power_applied: bool
    note: str


@dataclass(frozen=True)
class BranchGaussianQTrace:
    """Branch-carried tangential/sagittal Gaussian q propagation result."""

    beam: AstigmaticGaussianBeamInput
    steps: Tuple[BranchGaussianQStep, ...]
    input_index: float
    input_tangential_q: complex
    input_sagittal_q: complex
    wavelength_mm: float
    ray_index: int
    source_ray_index: int
    branch_id: int
    branch_path: str
    total_distance_mm: float
    total_optical_path_mm: float
    cumulative_clip_transmission: float
    cumulative_clip_loss: float

    @property
    def final(self) -> BranchGaussianQStep | None:
        return self.steps[-1] if self.steps else None

    @property
    def stable(self) -> bool:
        final = self.final
        return bool(final is not None and final.tangential_stable and final.sagittal_stable)


@dataclass(frozen=True)
class GaussianCavityEigenmode:
    """Self-consistent Gaussian mode for an ABCD round-trip matrix."""

    wavelength_um: float
    m2: float
    input_index: float
    A: float
    B: float
    C: float
    D: float
    determinant: float
    stability_parameter: float
    stable: bool
    q_real_mm: float
    q_imag_mm: float
    beam_radius_mm: float
    wavefront_radius_mm: float
    waist_radius_mm: float
    waist_offset_mm: float
    rayleigh_range_mm: float
    divergence_mrad: float
    round_trip_gouy_rad: float
    message: str

    @property
    def beam(self) -> GaussianBeamInput:
        if not self.stable:
            raise ValueError(self.message)
        return GaussianBeamInput(
            wavelength_um=self.wavelength_um,
            waist_radius_mm=self.waist_radius_mm,
            waist_offset_mm=self.q_real_mm,
            m2=self.m2,
            input_index=self.input_index,
        )


def gaussian_beam_from_diameter_divergence(
    *,
    wavelength_um: float,
    beam_diameter_mm: float,
    full_divergence_mrad: float,
    m2: float = 1.0,
    input_index: float = 1.0,
    waist_after_input: bool = False,
) -> GaussianBeamInput:
    """Create a Gaussian beam from manufacturer-style diameter/divergence data.

    ``beam_diameter_mm`` is the 1/e^2 beam diameter at the input plane.
    ``full_divergence_mrad`` is the full far-field divergence angle. The
    returned ``waist_offset_mm`` is positive when the waist is before the input
    plane, which corresponds to a diverging beam at the input plane.
    """
    wavelength_mm = _positive_float(wavelength_um, "wavelength_um") * 1e-3
    beam_radius_mm = 0.5 * _positive_float(beam_diameter_mm, "beam_diameter_mm")
    half_divergence_rad = 0.5e-3 * _positive_float(full_divergence_mrad, "full_divergence_mrad")
    m2_value = _positive_float(m2, "m2")
    refractive_index = _positive_float(input_index, "input_index")
    waist_radius_mm = wavelength_mm * m2_value / (np.pi * refractive_index * half_divergence_rad)
    if beam_radius_mm + 1e-12 < waist_radius_mm:
        raise ValueError(
            "beam_diameter_mm and full_divergence_mrad are inconsistent: "
            "the input beam radius is smaller than the implied diffraction waist"
        )
    z_rayleigh_mm = np.pi * refractive_index * waist_radius_mm * waist_radius_mm / (wavelength_mm * m2_value)
    ratio = max((beam_radius_mm / waist_radius_mm) ** 2 - 1.0, 0.0)
    distance_mm = z_rayleigh_mm * float(np.sqrt(ratio))
    waist_offset_mm = -distance_mm if waist_after_input else distance_mm
    return GaussianBeamInput(
        wavelength_um=float(wavelength_um),
        waist_radius_mm=float(waist_radius_mm),
        waist_offset_mm=float(waist_offset_mm),
        m2=float(m2_value),
        input_index=float(refractive_index),
    )


def astigmatic_gaussian_beam_from_diameter_divergence(
    *,
    wavelength_um: float,
    tangential_beam_diameter_mm: float,
    tangential_full_divergence_mrad: float,
    sagittal_beam_diameter_mm: float,
    sagittal_full_divergence_mrad: float,
    tangential_m2: float = 1.0,
    sagittal_m2: float = 1.0,
    input_index: float = 1.0,
    waist_after_input: bool = False,
) -> AstigmaticGaussianBeamInput:
    """Create independent tangential/sagittal beams from datasheet values."""
    return AstigmaticGaussianBeamInput(
        tangential=gaussian_beam_from_diameter_divergence(
            wavelength_um=wavelength_um,
            beam_diameter_mm=tangential_beam_diameter_mm,
            full_divergence_mrad=tangential_full_divergence_mrad,
            m2=tangential_m2,
            input_index=input_index,
            waist_after_input=waist_after_input,
        ),
        sagittal=gaussian_beam_from_diameter_divergence(
            wavelength_um=wavelength_um,
            beam_diameter_mm=sagittal_beam_diameter_mm,
            full_divergence_mrad=sagittal_full_divergence_mrad,
            m2=sagittal_m2,
            input_index=input_index,
            waist_after_input=waist_after_input,
        ),
    )


def propagate_gaussian_beam(paraxial_trace, beam: GaussianBeamInput) -> GaussianBeamTrace:
    """Propagate a Gaussian beam through a KrakenOS paraxial matrix trace."""
    wavelength_mm = _positive_float(beam.wavelength_um, "wavelength_um") * 1e-3
    waist_radius_mm = _positive_float(beam.waist_radius_mm, "waist_radius_mm")
    m2 = _positive_float(beam.m2, "m2")
    input_index = _input_index(paraxial_trace, beam)
    rayleigh_range_mm = np.pi * input_index * waist_radius_mm * waist_radius_mm / (wavelength_mm * m2)
    input_q = complex(float(beam.waist_offset_mm), float(rayleigh_range_mm))
    q_value = input_q
    current_index = input_index
    rows: list[GaussianBeamStep] = []

    for step_index, step in enumerate(getattr(paraxial_trace, "steps", ())):
        matrix = np.asarray(step.abcd_matrix, dtype=float)
        if matrix.shape != (2, 2):
            raise ValueError(f"ABCD step {step_index} is not a 2x2 matrix")
        A, B, C, D = (float(matrix[0, 0]), float(matrix[0, 1]), float(matrix[1, 0]), float(matrix[1, 1]))
        denominator = C * q_value + D
        if abs(denominator) <= 1e-18:
            q_value = complex(np.nan, np.nan)
        else:
            q_value = (A * q_value + B) / denominator
        current_index = _safe_index(getattr(step, "n_after", current_index), current_index)
        rows.append(
            _make_step(
                step_index=step_index,
                step=step,
                matrix=(A, B, C, D),
                q_value=q_value,
                wavelength_mm=wavelength_mm,
                m2=m2,
                current_index=current_index,
            )
        )

    return GaussianBeamTrace(
        beam=beam,
        steps=tuple(rows),
        input_index=float(input_index),
        input_q=input_q,
        input_rayleigh_range_mm=float(rayleigh_range_mm),
        wavelength_mm=float(wavelength_mm),
    )


def propagate_astigmatic_gaussian_beam(paraxial_trace, beam: AstigmaticGaussianBeamInput) -> AstigmaticGaussianBeamTrace:
    """Propagate independent tangential/sagittal q parameters through a trace.

    The current KrakenOS paraxial trace is centered and rotationally symmetric,
    so both axes use the same ABCD sequence. This still models elliptical laser
    inputs with different X/Y waist, divergence, and M2 values. Future oblique
    or non-sequential matrices can feed separate axis matrices into the same
    per-axis propagation routine.
    """
    if abs(float(beam.tangential.wavelength_um) - float(beam.sagittal.wavelength_um)) > 1e-12:
        raise ValueError("tangential and sagittal Gaussian beams must use the same wavelength")
    return AstigmaticGaussianBeamTrace(
        beam=beam,
        tangential=propagate_gaussian_beam(paraxial_trace, beam.tangential),
        sagittal=propagate_gaussian_beam(paraxial_trace, beam.sagittal),
    )


def propagate_branch_gaussian_q(
    record_or_hits,
    beam: GaussianBeamInput | AstigmaticGaussianBeamInput,
    *,
    surfaces=None,
    branch_path: str | None = None,
    ray_index: int | None = None,
    source_ray_index: int | None = None,
    branch_id: int | None = None,
) -> BranchGaussianQTrace:
    """Propagate tangential/sagittal Gaussian q through traced branch hits.

    This is the first non-sequential Gaussian propagation contract. It consumes
    Ray Inspector/Trace Path style hit records, advances q through each branch
    segment, and applies conservative first-order surface power only when the
    hit carries enough information. Flat splitter/mirror/folded paths are
    therefore handled exactly as branch-local free-space propagation; powered
    oblique refraction remains intentionally limited until a full field solver
    is introduced.
    """
    astigmatic_beam = _as_astigmatic_beam(beam)
    if abs(float(astigmatic_beam.tangential.wavelength_um) - float(astigmatic_beam.sagittal.wavelength_um)) > 1e-12:
        raise ValueError("tangential and sagittal Gaussian beams must use the same wavelength")
    hits = _branch_hits(record_or_hits)
    wavelength_mm = _positive_float(astigmatic_beam.tangential.wavelength_um, "wavelength_um") * 1e-3
    input_index = _branch_input_index(hits, astigmatic_beam.tangential)
    q_t = _beam_input_q(astigmatic_beam.tangential, input_index, wavelength_mm)
    q_s = _beam_input_q(astigmatic_beam.sagittal, input_index, wavelength_mm)
    current_index = float(input_index)
    rows: list[BranchGaussianQStep] = []
    total_distance = 0.0
    total_optical_path = 0.0
    cumulative_clip = 1.0

    metadata = record_or_hits if isinstance(record_or_hits, dict) else {}
    trace_branch_path = str(
        branch_path
        if branch_path is not None
        else metadata.get("branch_path", "") if isinstance(metadata, dict) else ""
    )
    trace_ray_index = _safe_int(ray_index if ray_index is not None else metadata.get("ray_index", -1), -1)
    trace_source_ray_index = _safe_int(
        source_ray_index if source_ray_index is not None else metadata.get("source_ray_index", trace_ray_index),
        trace_ray_index,
    )
    trace_branch_id = _safe_int(branch_id if branch_id is not None else metadata.get("branch_id", 0), 0)

    for local_index, hit in enumerate(hits):
        distance = _finite_float(hit.get("distance", 0.0), 0.0)
        if distance < 0.0:
            distance = 0.0
        optical_path = _finite_float(hit.get("op", np.nan), np.nan)
        total_distance += distance
        if np.isfinite(optical_path):
            total_optical_path += optical_path
        n_before = _safe_index(hit.get("n0", current_index), current_index)
        n_after = _safe_index(hit.get("n1", n_before), n_before)
        if abs(n_before - current_index) > 1e-9 and current_index > 0.0:
            # Trust the trace hit over the previous bookkeeping at branch splits.
            current_index = n_before

        q_t_before_surface = q_t + distance
        q_s_before_surface = q_s + distance
        c_t, c_s, power_note = _branch_surface_power(hit, surfaces, n_before=n_before, n_after=n_after)
        index_scale = n_after / max(n_before, 1e-12)
        q_t = _apply_branch_q_step(q_t_before_surface, c_t, index_scale)
        q_s = _apply_branch_q_step(q_s_before_surface, c_s, index_scale)
        current_index = n_after

        t_quantities = _beam_quantities(
            q_t,
            wavelength_mm=wavelength_mm,
            m2=_positive_float(astigmatic_beam.tangential.m2, "m2"),
            refractive_index=current_index,
        )
        s_quantities = _beam_quantities(
            q_s,
            wavelength_mm=wavelength_mm,
            m2=_positive_float(astigmatic_beam.sagittal.m2, "m2"),
            refractive_index=current_index,
        )
        surface_index = _safe_int(hit.get("surface", -1), -1)
        step_branch_id = _safe_int(hit.get("branch", trace_branch_id), trace_branch_id)
        event = str(hit.get("event", "") or "")
        surface_name = str(hit.get("name", "") or "")
        incidence_deg = _finite_float(hit.get("gb_incidence_deg", np.nan), np.nan)
        clear_radius, obscuration_radius = _surface_aperture_radii(surfaces, surface_index)
        clip_transmission = _gaussian_clip_transmission(
            tangential_radius=t_quantities[0],
            sagittal_radius=s_quantities[0],
            clear_radius=clear_radius,
            obscuration_radius=obscuration_radius,
        )
        clip_loss = 1.0 - clip_transmission if np.isfinite(clip_transmission) else np.nan
        if np.isfinite(clip_transmission):
            cumulative_clip *= float(np.clip(clip_transmission, 0.0, 1.0))
        cumulative_loss = 1.0 - cumulative_clip
        rows.append(
            BranchGaussianQStep(
                step_index=_safe_int(hit.get("step", local_index), local_index),
                surface_index=surface_index,
                surface_name=surface_name,
                event=event,
                branch_id=step_branch_id,
                branch_path=trace_branch_path,
                distance_mm=float(distance),
                optical_path_mm=float(optical_path),
                n_before=float(n_before),
                n_after=float(n_after),
                incidence_deg=float(incidence_deg),
                tangential_A=float(index_scale),
                tangential_B=float(index_scale * distance),
                tangential_C=float(c_t),
                tangential_D=float(1.0 + c_t * distance),
                sagittal_A=float(index_scale),
                sagittal_B=float(index_scale * distance),
                sagittal_C=float(c_s),
                sagittal_D=float(1.0 + c_s * distance),
                tangential_q_real_mm=float(q_t.real),
                tangential_q_imag_mm=float(q_t.imag),
                sagittal_q_real_mm=float(q_s.real),
                sagittal_q_imag_mm=float(q_s.imag),
                tangential_beam_radius_mm=float(t_quantities[0]),
                sagittal_beam_radius_mm=float(s_quantities[0]),
                tangential_wavefront_radius_mm=float(t_quantities[1]),
                sagittal_wavefront_radius_mm=float(s_quantities[1]),
                tangential_waist_radius_mm=float(t_quantities[2]),
                sagittal_waist_radius_mm=float(s_quantities[2]),
                tangential_waist_offset_mm=float(t_quantities[3]),
                sagittal_waist_offset_mm=float(s_quantities[3]),
                tangential_rayleigh_range_mm=float(t_quantities[4]),
                sagittal_rayleigh_range_mm=float(s_quantities[4]),
                tangential_gouy_phase_rad=float(t_quantities[6]),
                sagittal_gouy_phase_rad=float(s_quantities[6]),
                tangential_stable=bool(t_quantities[7]),
                sagittal_stable=bool(s_quantities[7]),
                clear_radius_mm=float(clear_radius),
                obscuration_radius_mm=float(obscuration_radius),
                clip_transmission=float(clip_transmission),
                clip_loss=float(clip_loss),
                cumulative_clip_transmission=float(cumulative_clip),
                cumulative_clip_loss=float(cumulative_loss),
                surface_power_applied=bool(abs(c_t) > 0.0 or abs(c_s) > 0.0),
                note=power_note,
            )
        )

    return BranchGaussianQTrace(
        beam=astigmatic_beam,
        steps=tuple(rows),
        input_index=float(input_index),
        input_tangential_q=complex(_beam_input_q(astigmatic_beam.tangential, input_index, wavelength_mm)),
        input_sagittal_q=complex(_beam_input_q(astigmatic_beam.sagittal, input_index, wavelength_mm)),
        wavelength_mm=float(wavelength_mm),
        ray_index=int(trace_ray_index),
        source_ray_index=int(trace_source_ray_index),
        branch_id=int(trace_branch_id),
        branch_path=trace_branch_path,
        total_distance_mm=float(total_distance),
        total_optical_path_mm=float(total_optical_path),
        cumulative_clip_transmission=float(cumulative_clip),
        cumulative_clip_loss=float(1.0 - cumulative_clip),
    )


def solve_gaussian_cavity_eigenmode(
    paraxial_trace_or_matrix,
    *,
    wavelength_um: float | None = None,
    m2: float = 1.0,
    input_index: float = 1.0,
) -> GaussianCavityEigenmode:
    """Solve the self-consistent Gaussian mode of an ABCD round-trip matrix.

    ``paraxial_trace_or_matrix`` can be a KrakenOS ``ParaxialMatrixTrace`` or a
    raw 2x2 ABCD matrix. The matrix must represent one complete cavity round
    trip at the chosen reference plane.
    """
    matrix = _abcd_matrix(paraxial_trace_or_matrix)
    A, B, C, D = (float(matrix[0, 0]), float(matrix[0, 1]), float(matrix[1, 0]), float(matrix[1, 1]))
    wavelength_value = wavelength_um
    if wavelength_value is None:
        wavelength_value = getattr(paraxial_trace_or_matrix, "wavelength", None)
    wavelength_value = _positive_float(wavelength_value, "wavelength_um")
    wavelength_mm = wavelength_value * 1e-3
    m2_value = _positive_float(m2, "m2")
    refractive_index = _positive_float(input_index, "input_index")
    determinant = float(A * D - B * C)
    stability_parameter = np.nan
    if determinant > 0.0:
        stability_parameter = float((A + D) / (2.0 * np.sqrt(determinant)))
    roots = _cavity_q_roots(A, B, C, D)
    candidates = [complex(root) for root in roots if np.isfinite(root.real) and np.isfinite(root.imag) and root.imag > 1e-12]
    stable_by_trace = bool(np.isfinite(stability_parameter) and abs(stability_parameter) < 1.0)
    if not candidates:
        return _unstable_cavity_mode(
            wavelength_um=wavelength_value,
            m2=m2_value,
            input_index=refractive_index,
            matrix=(A, B, C, D),
            determinant=determinant,
            stability_parameter=stability_parameter,
            message="ABCD round trip has no positive-imaginary q eigenmode",
        )
    q_value = max(candidates, key=lambda item: item.imag)
    beam_radius, wavefront_radius, waist_radius, waist_offset, z_rayleigh, divergence, gouy, q_is_valid = _beam_quantities(
        q_value,
        wavelength_mm=wavelength_mm,
        m2=m2_value,
        refractive_index=refractive_index,
    )
    stable = bool(stable_by_trace and q_is_valid)
    clipped_stability = float(np.clip(stability_parameter, -1.0, 1.0)) if np.isfinite(stability_parameter) else np.nan
    round_trip_gouy = float(np.arccos(clipped_stability)) if stable else np.nan
    message = "stable cavity eigenmode" if stable else "ABCD trace is outside the stable cavity range"
    return GaussianCavityEigenmode(
        wavelength_um=float(wavelength_value),
        m2=float(m2_value),
        input_index=float(refractive_index),
        A=A,
        B=B,
        C=C,
        D=D,
        determinant=determinant,
        stability_parameter=stability_parameter,
        stable=stable,
        q_real_mm=float(q_value.real) if stable else np.nan,
        q_imag_mm=float(q_value.imag) if stable else np.nan,
        beam_radius_mm=beam_radius if stable else np.nan,
        wavefront_radius_mm=wavefront_radius if stable else np.nan,
        waist_radius_mm=waist_radius if stable else np.nan,
        waist_offset_mm=waist_offset if stable else np.nan,
        rayleigh_range_mm=z_rayleigh if stable else np.nan,
        divergence_mrad=divergence if stable else np.nan,
        round_trip_gouy_rad=round_trip_gouy,
        message=message,
    )


def _as_astigmatic_beam(beam: GaussianBeamInput | AstigmaticGaussianBeamInput) -> AstigmaticGaussianBeamInput:
    if isinstance(beam, AstigmaticGaussianBeamInput):
        return beam
    if isinstance(beam, GaussianBeamInput):
        return AstigmaticGaussianBeamInput(tangential=beam, sagittal=beam)
    raise TypeError("beam must be GaussianBeamInput or AstigmaticGaussianBeamInput")


def _branch_hits(record_or_hits) -> list[dict[str, object]]:
    if isinstance(record_or_hits, dict):
        source = record_or_hits.get("hits", [])
    else:
        source = record_or_hits
    hits: list[dict[str, object]] = []
    for hit in list(source or []):
        if isinstance(hit, dict):
            hits.append(dict(hit))
    return hits


def _branch_input_index(hits: list[dict[str, object]], beam: GaussianBeamInput) -> float:
    if beam.input_index is not None:
        return _positive_float(beam.input_index, "input_index")
    for hit in hits:
        value = _finite_float(hit.get("n0", np.nan), np.nan)
        if np.isfinite(value) and abs(value) > 0.0:
            return abs(float(value))
    return 1.0


def _beam_input_q(beam: GaussianBeamInput, input_index: float, wavelength_mm: float) -> complex:
    waist_radius_mm = _positive_float(beam.waist_radius_mm, "waist_radius_mm")
    m2 = _positive_float(beam.m2, "m2")
    rayleigh_range_mm = np.pi * input_index * waist_radius_mm * waist_radius_mm / (wavelength_mm * m2)
    return complex(float(beam.waist_offset_mm), float(rayleigh_range_mm))


def _finite_float(value, fallback: float) -> float:
    try:
        numeric = float(value)
    except Exception:
        return float(fallback)
    return float(numeric) if np.isfinite(numeric) else float(fallback)


def _safe_int(value, fallback: int) -> int:
    try:
        return int(value)
    except Exception:
        return int(fallback)


def _surface_for_index(surfaces, surface_index: int):
    if surfaces is None or surface_index < 0:
        return None
    try:
        return list(surfaces)[surface_index]
    except Exception:
        return None


def _surface_numeric(surface, names: tuple[str, ...], fallback: float = 0.0) -> float:
    if surface is None:
        return float(fallback)
    for attr in names:
        if hasattr(surface, attr):
            value = _finite_float(getattr(surface, attr), fallback)
            return value if np.isfinite(value) else float(fallback)
    if isinstance(surface, dict):
        for key in names:
            if key in surface:
                value = _finite_float(surface.get(key), fallback)
                return value if np.isfinite(value) else float(fallback)
    return float(fallback)


def _surface_radius(surfaces, surface_index: int) -> float:
    surface = _surface_for_index(surfaces, surface_index)
    return _surface_numeric(surface, ("rc", "Rc", "radius", "Radius"), 0.0)


def _surface_aperture_radii(surfaces, surface_index: int) -> tuple[float, float]:
    surface = _surface_for_index(surfaces, surface_index)
    diameter = _surface_numeric(surface, ("diameter", "Diameter"), 0.0)
    in_diameter = _surface_numeric(surface, ("in_diameter", "InDiameter"), 0.0)
    clear_radius = 0.5 * diameter if np.isfinite(diameter) and diameter > 0.0 else np.inf
    obscuration_radius = 0.5 * in_diameter if np.isfinite(in_diameter) and in_diameter > 0.0 else 0.0
    if np.isfinite(clear_radius):
        obscuration_radius = min(max(float(obscuration_radius), 0.0), float(clear_radius))
    return float(clear_radius), float(obscuration_radius)


def _gaussian_clip_transmission(
    *,
    tangential_radius: float,
    sagittal_radius: float,
    clear_radius: float,
    obscuration_radius: float = 0.0,
) -> float:
    radii = np.asarray((tangential_radius, sagittal_radius), dtype=float)
    if not np.all(np.isfinite(radii)) or np.any(radii <= 0.0):
        return np.nan
    if not np.isfinite(clear_radius):
        return 1.0
    if clear_radius <= 0.0:
        return 0.0
    equivalent_radius = float(np.sqrt(max(float(radii[0] * radii[1]), 1e-24)))
    outer_fraction = 1.0 - float(np.exp(-2.0 * (float(clear_radius) / equivalent_radius) ** 2))
    inner_radius = max(float(obscuration_radius), 0.0)
    inner_fraction = 0.0
    if inner_radius > 0.0:
        inner_fraction = 1.0 - float(np.exp(-2.0 * (inner_radius / equivalent_radius) ** 2))
    return float(np.clip(outer_fraction - inner_fraction, 0.0, 1.0))


def _branch_surface_power(hit: dict[str, object], surfaces, *, n_before: float, n_after: float) -> tuple[float, float, str]:
    surface_index = _safe_int(hit.get("surface", -1), -1)
    radius = _surface_radius(surfaces, surface_index)
    if not np.isfinite(radius) or abs(radius) <= 1e-12:
        return 0.0, 0.0, "flat/free-space"
    event = str(hit.get("event", "") or "").lower()
    incidence_deg = _finite_float(hit.get("gb_incidence_deg", 0.0), 0.0)
    cos_i = float(np.cos(np.deg2rad(abs(incidence_deg))))
    cos_i = max(cos_i, 1e-6)
    is_reflection = any(token in event for token in ("reflect", "mirror"))
    if is_reflection:
        c_t = -2.0 / (radius * cos_i)
        c_s = -2.0 * cos_i / radius
        return float(c_t), float(c_s), "oblique spherical reflection"
    if abs(float(n_after) - float(n_before)) <= 1e-12:
        return 0.0, 0.0, "same-index powered surface ignored"
    if abs(incidence_deg) > 1.0:
        return 0.0, 0.0, "oblique powered refraction deferred"
    c_value = (float(n_before) - float(n_after)) / (radius * max(float(n_after), 1e-12))
    return float(c_value), float(c_value), "near-normal spherical refraction"


def _apply_branch_q_step(q_value: complex, c_value: float, index_scale: float) -> complex:
    denominator = complex(c_value) * q_value + 1.0
    if abs(denominator) <= 1e-18:
        return complex(np.nan, np.nan)
    return complex(index_scale) * (q_value / denominator)


def _positive_float(value: float, name: str) -> float:
    try:
        numeric = float(value)
    except Exception as exc:
        raise ValueError(f"{name} must be a positive finite value") from exc
    if not np.isfinite(numeric) or numeric <= 0.0:
        raise ValueError(f"{name} must be a positive finite value")
    return numeric


def _abcd_matrix(paraxial_trace_or_matrix) -> np.ndarray:
    matrix = getattr(paraxial_trace_or_matrix, "system_matrix_abcd", paraxial_trace_or_matrix)
    arr = np.asarray(matrix, dtype=float)
    if arr.shape != (2, 2):
        raise ValueError("ABCD matrix must be 2x2")
    return arr


def _cavity_q_roots(A: float, B: float, C: float, D: float) -> tuple[complex, ...]:
    coefficients = [complex(C), complex(D - A), complex(-B)]
    while coefficients and abs(coefficients[0]) <= 1e-18:
        coefficients.pop(0)
    if not coefficients:
        return tuple()
    if len(coefficients) == 1:
        return tuple()
    roots = np.roots(np.asarray(coefficients, dtype=complex))
    return tuple(complex(root) for root in roots)


def _unstable_cavity_mode(
    *,
    wavelength_um: float,
    m2: float,
    input_index: float,
    matrix: tuple[float, float, float, float],
    determinant: float,
    stability_parameter: float,
    message: str,
) -> GaussianCavityEigenmode:
    A, B, C, D = matrix
    return GaussianCavityEigenmode(
        wavelength_um=float(wavelength_um),
        m2=float(m2),
        input_index=float(input_index),
        A=A,
        B=B,
        C=C,
        D=D,
        determinant=float(determinant),
        stability_parameter=float(stability_parameter),
        stable=False,
        q_real_mm=np.nan,
        q_imag_mm=np.nan,
        beam_radius_mm=np.nan,
        wavefront_radius_mm=np.nan,
        waist_radius_mm=np.nan,
        waist_offset_mm=np.nan,
        rayleigh_range_mm=np.nan,
        divergence_mrad=np.nan,
        round_trip_gouy_rad=np.nan,
        message=message,
    )


def _input_index(paraxial_trace, beam: GaussianBeamInput) -> float:
    if beam.input_index is not None:
        return _positive_float(beam.input_index, "input_index")
    steps = tuple(getattr(paraxial_trace, "steps", ()) or ())
    if steps:
        return _safe_index(getattr(steps[0], "n_before", 1.0), 1.0)
    return 1.0


def _safe_index(value, fallback: float) -> float:
    try:
        numeric = abs(float(value))
    except Exception:
        numeric = float(fallback)
    if not np.isfinite(numeric) or numeric <= 0.0:
        return float(fallback)
    return float(numeric)


def _make_step(
    *,
    step_index: int,
    step,
    matrix: tuple[float, float, float, float],
    q_value: complex,
    wavelength_mm: float,
    m2: float,
    current_index: float,
) -> GaussianBeamStep:
    beam_radius, wavefront_radius, waist_radius, waist_offset, z_rayleigh, divergence, gouy, stable = _beam_quantities(
        q_value,
        wavelength_mm=wavelength_mm,
        m2=m2,
        refractive_index=current_index,
    )
    A, B, C, D = matrix
    return GaussianBeamStep(
        step_index=int(step_index),
        surface_index=int(getattr(step, "surface_index", -1)),
        surface_name=str(getattr(step, "surface_name", "") or ""),
        kind=str(getattr(step, "kind", "")),
        label=str(getattr(step, "label", "")),
        n_before=float(getattr(step, "n_before", current_index)),
        n_after=float(current_index),
        A=A,
        B=B,
        C=C,
        D=D,
        q_real_mm=float(np.real(q_value)),
        q_imag_mm=float(np.imag(q_value)),
        beam_radius_mm=beam_radius,
        beam_diameter_mm=2.0 * beam_radius if np.isfinite(beam_radius) else np.nan,
        wavefront_radius_mm=wavefront_radius,
        waist_radius_mm=waist_radius,
        waist_offset_mm=waist_offset,
        rayleigh_range_mm=z_rayleigh,
        divergence_mrad=divergence,
        gouy_phase_rad=gouy,
        stable=stable,
    )


def _beam_quantities(q_value: complex, *, wavelength_mm: float, m2: float, refractive_index: float):
    if not (np.isfinite(q_value.real) and np.isfinite(q_value.imag)) or abs(q_value) <= 1e-18:
        return (np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, False)
    if q_value.imag <= 0.0:
        return (np.nan, np.nan, np.nan, np.nan, float(q_value.imag), np.nan, np.nan, False)
    effective_wavelength = wavelength_mm * m2
    inverse_q = 1.0 / q_value
    imag_inverse = float(np.imag(inverse_q))
    real_inverse = float(np.real(inverse_q))
    if imag_inverse >= 0.0:
        beam_radius = np.nan
    else:
        beam_radius = float(np.sqrt(-effective_wavelength / (np.pi * refractive_index * imag_inverse)))
    if abs(real_inverse) <= 1e-18:
        wavefront_radius = np.inf
    else:
        wavefront_radius = float(1.0 / real_inverse)
    z_rayleigh = float(q_value.imag)
    waist_radius = float(np.sqrt(effective_wavelength * z_rayleigh / (np.pi * refractive_index)))
    waist_offset = float(-q_value.real)
    divergence = float(1000.0 * effective_wavelength / (np.pi * refractive_index * waist_radius))
    gouy = float(np.arctan2(q_value.real, q_value.imag))
    stable = bool(np.isfinite(beam_radius) and np.isfinite(waist_radius) and z_rayleigh > 0.0)
    return (beam_radius, wavefront_radius, waist_radius, waist_offset, z_rayleigh, divergence, gouy, stable)
