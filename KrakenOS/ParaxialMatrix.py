from dataclasses import dataclass
from typing import Tuple

import numpy as np


_FLAT_RADIUS = 9999999999999.9


def kraken_to_abcd(matrix):
    """Convert Kraken's paraxial (u, y) matrix into standard (y, u) ABCD."""
    mat = np.asarray(matrix, dtype=float)
    return np.array([[mat[1, 1], mat[1, 0]], [mat[0, 1], mat[0, 0]]], dtype=float)


def abcd_to_kraken(matrix):
    """Convert a standard (y, u) ABCD matrix into Kraken's (u, y) convention."""
    mat = np.asarray(matrix, dtype=float)
    return np.matrix([[mat[1, 1], mat[1, 0]], [mat[0, 1], mat[0, 0]]], dtype=float)


@dataclass(frozen=True)
class ParaxialStep:
    """One paraxial operation in both Kraken and conventional ABCD form."""

    surface_index: int
    kind: str
    label: str
    kraken_matrix: np.matrix
    abcd_matrix: np.ndarray
    n_before: float
    n_after: float
    radius: float
    thickness: float
    glass: str
    surface_name: str


@dataclass(frozen=True)
class ParaxialSurfaceMatrix:
    """Surface interaction plus the following axial translation."""

    surface_index: int
    surface_name: str
    glass: str
    n_before: float
    n_after: float
    radius: float
    curvature: float
    thickness: float
    is_mirror: bool
    is_thin_lens: bool
    refraction: ParaxialStep
    translation: ParaxialStep
    kraken_matrix: np.matrix
    abcd_matrix: np.ndarray


@dataclass(frozen=True)
class ParaxialMatrixTrace:
    """Structured result for KrakenOS paraxial matrix extraction."""

    wavelength: float
    surfaces: Tuple[ParaxialSurfaceMatrix, ...]
    steps: Tuple[ParaxialStep, ...]
    system_matrix_kraken: np.matrix
    system_matrix_abcd: np.ndarray
    kraken_a: float
    kraken_b: float
    kraken_c: float
    kraken_d: float
    effl: float
    ppa: float
    ppp: float
    curvatures: np.ndarray
    indices: np.ndarray
    thicknesses: np.ndarray

    @property
    def step_labels(self):
        return [step.label for step in self.steps]

    @property
    def step_matrices(self):
        return [step.kraken_matrix for step in self.steps]

    @property
    def abcd_step_matrices(self):
        return [step.abcd_matrix for step in self.steps]

    def as_legacy_tuple(self):
        return (
            self.system_matrix_kraken,
            self.step_matrices,
            self.step_labels,
            self.kraken_a,
            self.kraken_b,
            self.kraken_c,
            self.kraken_d,
            self.effl,
            self.ppa,
            self.ppp,
            self.curvatures,
            self.indices.tolist(),
            self.thicknesses,
        )


def build_paraxial_matrix_trace(N_Prec, SDT, SuTo, n, Gl, wavelength=0.0):
    """Build surface-by-surface paraxial matrices using Kraken's Parax rules."""
    prev_n = N_Prec[0]
    steps = []
    surfaces = []
    curvatures = []
    thicknesses = []

    for j in range(0, n + 0):
        radius = _paraxial_radius(SDT, SuTo, j)
        glass = Gl[j]
        if glass != "NULL":
            curr_n = N_Prec[j]
        else:
            curr_n = prev_n

        n1 = np.abs(prev_n)
        n2 = np.abs(curr_n)
        thickness = SDT[j].Thickness + SDT[j].DespZ
        is_mirror = glass == "MIRROR"
        is_thin_lens = SDT[j].Thin_Lens != 0

        if is_mirror:
            n1 = -n1

        if not is_thin_lens:
            refraction_matrix = np.matrix(
                [[(n1 / n2), ((n1 - n2) / (n2 * radius))], [0.0, 1.0]]
            )
        else:
            refraction_matrix = np.matrix(
                [[1.0, -1.0 / SDT[j].Thin_Lens], [0.0, 1.0]]
            )

        translation_matrix = np.matrix([[1.0, 0.0], [thickness, 1.0]])

        surface_name = getattr(SDT[j], "Name", "")
        refraction_step = ParaxialStep(
            surface_index=j,
            kind="refraction",
            label="R surf " + str(j),
            kraken_matrix=refraction_matrix,
            abcd_matrix=kraken_to_abcd(refraction_matrix),
            n_before=float(n1),
            n_after=float(n2),
            radius=float(radius),
            thickness=0.0,
            glass=glass,
            surface_name=surface_name,
        )
        translation_step = ParaxialStep(
            surface_index=j,
            kind="translation",
            label="T surf " + str(j) + " to " + str(j + 1),
            kraken_matrix=translation_matrix,
            abcd_matrix=kraken_to_abcd(translation_matrix),
            n_before=float(n2),
            n_after=float(n2),
            radius=float(radius),
            thickness=float(thickness),
            glass=glass,
            surface_name=surface_name,
        )
        steps.append(refraction_step)
        steps.append(translation_step)

        combined_kraken = np.dot(translation_matrix, refraction_matrix)
        combined_abcd = np.dot(
            translation_step.abcd_matrix, refraction_step.abcd_matrix
        )
        surfaces.append(
            ParaxialSurfaceMatrix(
                surface_index=j,
                surface_name=surface_name,
                glass=glass,
                n_before=float(n1),
                n_after=float(n2),
                radius=float(radius),
                curvature=float(1 / radius),
                thickness=float(thickness),
                is_mirror=bool(is_mirror),
                is_thin_lens=bool(is_thin_lens),
                refraction=refraction_step,
                translation=translation_step,
                kraken_matrix=combined_kraken,
                abcd_matrix=combined_abcd,
            )
        )

        curvatures.append(1 / radius)
        thicknesses.append(thickness)
        prev_n = curr_n

    system_matrix = np.matrix([[1.0, 0.0], [0.0, 1.0]])
    for step in steps[::-1]:
        system_matrix = np.dot(system_matrix, step.kraken_matrix)

    kraken_a = system_matrix[0, 0]
    kraken_b = system_matrix[0, 1]
    kraken_c = system_matrix[1, 0]
    kraken_d = system_matrix[1, 1]
    effl = (-1) / kraken_b
    ppa = (1 - kraken_a) / -kraken_b
    ppp = (kraken_d - 1) / -kraken_b

    return ParaxialMatrixTrace(
        wavelength=float(wavelength),
        surfaces=tuple(surfaces),
        steps=tuple(steps),
        system_matrix_kraken=system_matrix,
        system_matrix_abcd=kraken_to_abcd(system_matrix),
        kraken_a=kraken_a,
        kraken_b=kraken_b,
        kraken_c=kraken_c,
        kraken_d=kraken_d,
        effl=effl,
        ppa=ppa,
        ppp=ppp,
        curvatures=np.asarray(curvatures),
        indices=np.asarray(N_Prec),
        thicknesses=np.asarray(thicknesses),
    )


def _paraxial_radius(SDT, SuTo, surface_index):
    sag_rad = SDT[surface_index].Diameter / 400.0
    sag = SuTo.SurfaceShape(sag_rad, 0.0, surface_index)
    if sag != 0.0:
        radius = (sag_rad * sag_rad) / (2.0 * sag)
    else:
        radius = _FLAT_RADIUS
    if SDT[surface_index].Solid_3d_stl != "None":
        radius = _FLAT_RADIUS
    return radius
