"""Generate and insert concept diagrams for Fundamentals of Photonics exercises.

The diagrams are intentionally source-native SVG.  Each one uses a
chapter-appropriate visual model and an explicit variable legend; no raster
asset or external font is required.  Running this script is idempotent.
"""

from __future__ import annotations

import html
import re
import textwrap
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / "docs" / "source"
COLLECTION = (
    SOURCE / "knowledge_base" / "worked_exercises" / "fundamentals_of_photonics"
)
ASSET_DIR = (
    SOURCE
    / "_static"
    / "knowledge_base"
    / "worked_exercises"
    / "fundamentals_of_photonics"
    / "exercise_illustrations"
)
ENTRY_RE = re.compile(
    r"^\.\. rubric:: (Exercise|Problem) (\d+)\.(\d+)-(\d+) — ([^\n]+)\n",
    re.MULTILINE,
)


@dataclass(frozen=True)
class DiagramMeta:
    given: str
    model: str
    result: str
    variables: str
    check: str


META = {
    "ray": DiagramMeta(
        "object and incident ray",
        "refraction at an interface",
        "bent transmitted ray",
        "n₁,n₂: refractive indices • θ₁,θ₂: angles from the normal",
        "shown for n₂ > n₁; Snell's law and the equal-index straight-ray limit",
    ),
    "matrix": DiagramMeta(
        "input ray (y, nθ)",
        "ordered ABCD product",
        "output ray (y′, nθ′)",
        "A–D: matrix elements • y: height • θ: angle • d: spacing",
        "multiplication order, dimensions, and determinant",
    ),
    "wave": DiagramMeta(
        "incident amplitude and phase",
        "propagation or interference",
        "field or intensity",
        "A: field amplitude • k: wavenumber • λ: wavelength • I: intensity",
        "phase sign, symmetry, and conservation of power",
    ),
    "gaussian": DiagramMeta(
        "waist and initial q",
        "Gaussian-beam propagation",
        "width and curvature",
        "W₀: waist • z₀: Rayleigh range • q: beam parameter • R: curvature",
        "waist limit, far-field divergence, and units",
    ),
    "fourier": DiagramMeta(
        "aperture or input field",
        "Fourier transform",
        "spectrum or focal pattern",
        "g: input • G: transform • fₓ,fᵧ: spatial frequencies • λf: scale",
        "transform scale, parity, and inverse transform",
    ),
    "field": DiagramMeta(
        "material and source field",
        "Maxwell / wave equation",
        "propagating E and H",
        "E: electric field • H: magnetic field • k: wavevector • ε: permittivity",
        "field units, boundary conditions, and energy flow",
    ),
    "polarization": DiagramMeta(
        "input Jones or Stokes state",
        "polarizing element",
        "output polarization",
        "Eₓ,Eᵧ: field components • J: Jones matrix • S₀…S₃: Stokes parameters",
        "normalization, handedness, and limiting orientations",
    ),
    "multilayer": DiagramMeta(
        "incident wave and layers",
        "interface/phase matrices",
        "reflection and transmission",
        "nᵢ: layer index • dᵢ: thickness • r,t: amplitudes • Λ: period",
        "energy balance and matched-index limit",
    ),
    "waveguide": DiagramMeta(
        "core, cladding, and launch",
        "boundary and mode condition",
        "guided modal field",
        "n₁,n₂: indices • d/a: core size • β: propagation constant • V: normalized frequency",
        "cutoff, confinement, and power normalization",
    ),
    "fiber": DiagramMeta(
        "fiber profile and input state",
        "modal or polarization evolution",
        "output state and delay",
        "a: core radius • NA: numerical aperture • β: propagation constant • L: length",
        "cutoff, orthogonality, and limiting profile",
    ),
    "resonator": DiagramMeta(
        "mirror geometry and seed ray",
        "round-trip condition",
        "resonant modes",
        "L: cavity length • R₁,R₂: radii • g₁,g₂: stability factors • ν: frequency",
        "round-trip phase, stability interval, and mode spacing",
    ),
    "statistical": DiagramMeta(
        "random field or spectrum",
        "average / correlation",
        "coherence or distribution",
        "J: mutual intensity • g: degree of coherence • T₍c₎: coherence time • Δν: width",
        "normalization, bounds, and variance positivity",
    ),
    "quantum": DiagramMeta(
        "photon state or wavepacket",
        "quantum evolution / detection",
        "probability or uncertainty",
        "hν: photon energy • p: momentum • P: probability • σ: RMS width",
        "probability sum, dimensions, and uncertainty bound",
    ),
    "atomic": DiagramMeta(
        "atomic levels and population",
        "transition / thermal weighting",
        "spectrum or rate",
        "Eᵢ: energy levels • ν: transition frequency • Nᵢ: population • T: temperature",
        "energy conservation, normalization, and thermal limit",
    ),
    "amplifier": DiagramMeta(
        "pump and level populations",
        "rate / gain equations",
        "amplified signal",
        "Nᵢ: populations • Rₚ: pump rate • σ: cross section • G: gain",
        "population conservation and small-signal limit",
    ),
    "laser": DiagramMeta(
        "pump, gain, and cavity loss",
        "threshold / pulse dynamics",
        "laser modes or pulse",
        "N: inversion • g: gain • τ: lifetime • R: reflectance • P: power",
        "threshold balance, energy conservation, and time scale",
    ),
    "semiconductor": DiagramMeta(
        "bands and carrier populations",
        "occupation / transition model",
        "absorption or gain",
        "E₍c₎,E₍v₎: band edges • Fₙ,Fₚ: quasi-Fermi levels • n,p: carriers",
        "occupation bounds, charge neutrality, and band-gap limit",
    ),
    "source": DiagramMeta(
        "injected carriers",
        "radiative recombination",
        "LED / laser emission",
        "E₍g₎: bandgap • Fₙ,Fₚ: quasi-Fermi levels • λ: wavelength • η: efficiency",
        "carrier balance, spectral peak, and extraction cone",
    ),
    "detector": DiagramMeta(
        "photons and background",
        "conversion plus noise",
        "current and SNR",
        "Φ: photon flux • η: efficiency • ℛ: responsivity • B: bandwidth • i: current",
        "noise units, zero-background limit, and SNR scaling",
    ),
    "acousto": DiagramMeta(
        "optical and acoustic waves",
        "moving index grating",
        "diffracted order",
        "Λ: acoustic period • f: acoustic frequency • θᴮ: Bragg angle • D: aperture",
        "momentum matching, frequency shift, and angular units",
    ),
    "electro": DiagramMeta(
        "input field and voltage",
        "electro-optic phase/coupling",
        "modulated output",
        "V: voltage • Vπ: half-wave voltage • Δφ: phase • κ: coupling coefficient",
        "zero-voltage state, periodicity, and power conservation",
    ),
    "nonlinear": DiagramMeta(
        "input frequencies and fields",
        "nonlinear polarization",
        "mixed output frequency",
        "ωᵢ: frequencies • kᵢ: wavevectors • χ⁽ⁿ⁾: susceptibility • Δk: mismatch",
        "energy/momentum conservation and zero-nonlinearity limit",
    ),
    "pulse": DiagramMeta(
        "input pulse and chirp",
        "dispersion / phase operation",
        "output pulse",
        "T: pulse width • ζ: chirp • Dν: dispersion • z: distance",
        "transform limit, sign of chirp, and time-bandwidth product",
    ),
    "interconnect": DiagramMeta(
        "ports and channels",
        "mapping / switching network",
        "routed outputs",
        "M,L: port counts • B: spatial bandwidth • λᵢ: channels • V: control",
        "one-to-one mapping, capacity bound, and crosstalk",
    ),
}

# These variants share the ray-optics variable set but use distinct physical
# icons so a mirror is never drawn as a lens (and vice versa).
META["mirror"] = DiagramMeta(
    "object and incident ray",
    "reflection at mirror",
    "image or reflected ray",
    "y: ray height • θᵢ,θᵣ: incidence/reflection angles • R: radius • f: focal length",
    "reflection symmetry, sign convention, and paraxial limit",
)
META["lens"] = DiagramMeta(
    "object or incident beam",
    "refraction by lens",
    "image or focused beam",
    "n: lens index • y: ray height • R₁,R₂: surface radii • f: focal length",
    "thin-lens limit, ray intersection, and dimensions",
)
META["refracting"] = DiagramMeta(
    "object and curved interface",
    "Snell refraction at height y",
    "paraxial image point",
    "n₁,n₂: indices • θ₁,θ₂: normal-referenced angles • y: height • R: radius • z₁,z₂: conjugates",
    "bent ray, angle orientation, and spherical-surface imaging equation",
)
META["cartesian_oval"] = DiagramMeta(
    "two fixed conjugate points",
    "constant optical-path surface",
    "aberration-free image",
    "n₁,n₂: indices • y,z: surface point • z₁,z₂: axial conjugates",
    "equal optical path for upper, axial, and lower rays",
)
META["tir"] = DiagramMeta(
    "high-index block and internal ray",
    "total internal reflection",
    "trapped reflected ray",
    "n=3.6: block index • θᵢ: incidence angle • θᶜ=16.13°: critical angle",
    "θᵢ>θᶜ gives no propagating transmitted ray",
)
META["prism"] = DiagramMeta(
    "axial plane wave and wedge",
    "linear phase ramp",
    "deflected output wave",
    "d₀: reference thickness • a: wedge slope • n: index • k₀,kₓ: wavevectors • θ: deflection",
    "kₓ=(n−1)k₀a and the small-angle ray limit",
)
META["grin"] = DiagramMeta(
    "graded-index plate",
    "quadratic phase delay",
    "focused output",
    "n₀: axial index • d₀: thickness • a: gradient constant • ρ: radius • f: focal length",
    "f=(n₀d₀a²)⁻¹, dimensions, and zero-gradient limit",
)


CHAPTER_CATEGORY = {
    1: "ray",
    2: "wave",
    3: "gaussian",
    4: "fourier",
    5: "field",
    6: "polarization",
    7: "multilayer",
    8: "waveguide",
    9: "fiber",
    10: "resonator",
    11: "statistical",
    12: "quantum",
    13: "atomic",
    14: "amplifier",
    15: "laser",
    16: "semiconductor",
    17: "source",
    18: "detector",
    19: "acousto",
    20: "electro",
    21: "nonlinear",
    22: "pulse",
    23: "interconnect",
}


def clean_title(title: str) -> str:
    title = re.sub(r":math:`([^`]*)`", r"\1", title)
    title = title.replace("--", "–").replace("*", "")
    return title


def category_for(chapter: int, title: str) -> str:
    lower = title.lower()
    if chapter == 1:
        if "spherical refracting boundary" in lower:
            return "refracting"
        if "aberration-free refracting surface" in lower:
            return "cartesian_oval"
        if "trapped in a high-index block" in lower:
            return "tir"
        if "resonator" in lower:
            return "resonator"
        if "mirror" in lower:
            return "mirror"
        if "lens" in lower:
            return "lens"
        if any(word in lower for word in ("matrix", "plates")):
            return "matrix"
        if "fibre" in lower:
            return "waveguide"
    if chapter == 2 and "lens" in lower:
        return "lens"
    if chapter == 2 and "prism" in lower:
        return "prism"
    if chapter == 2 and "grin" in lower:
        return "grin"
    return CHAPTER_CATEGORY[chapter]


def icon_markup(category: str) -> str:
    icons = {
        "ray": '<line class="optic" x1="610" y1="180" x2="610" y2="360"/><line class="axis" x1="475" y1="270" x2="740" y2="270" stroke-dasharray="8 7"/><path class="accent" d="M480 205 L610 270 L738 315"/><path class="accent2" d="M566 270 A44 44 0 0 1 571 250 M654 270 A44 44 0 0 1 651 285"/>',
        "mirror": '<path class="optic" d="M690 185 Q625 270 690 355"/><path class="accent" d="M480 205 L675 270 L485 335"/><line class="axis" x1="475" y1="270" x2="735" y2="270"/><line class="thin" x1="675" y1="190" x2="675" y2="350" stroke-dasharray="8 7"/><path class="accent2" d="M630 270 A45 45 0 0 1 633 255 M630 270 A45 45 0 0 0 633 285"/>',
        "lens": '<path class="accent" d="M482 235 L604 270 L700 305 L735 318"/><path class="optic" d="M604 188 Q570 270 604 352 M604 188 Q638 270 604 352"/><line class="axis" x1="475" y1="305" x2="735" y2="305"/><circle class="point" cx="700" cy="305" r="6"/>',
        "refracting": '<path class="optic" d="M665 185 Q610 270 665 355"/><line class="axis" x1="475" y1="270" x2="740" y2="270" stroke-dasharray="8 7"/><path class="accent" d="M480 205 L610 270 L738 315"/><path class="accent2" d="M566 270 A44 44 0 0 1 571 250 M654 270 A44 44 0 0 1 651 285"/><line class="callout" x1="610" y1="270" x2="720" y2="270"/>',
        "cartesian_oval": '<path class="optic" d="M660 185 C585 210 585 330 660 355"/><path class="accent" d="M480 270 L625 205 L730 270 M480 270 L610 270 L730 270 M480 270 L625 335 L730 270"/><line class="axis" x1="475" y1="270" x2="740" y2="270" stroke-dasharray="8 7"/><circle class="point" cx="480" cy="270" r="7"/><circle class="point" cx="730" cy="270" r="7"/>',
        "tir": '<rect class="layer1" x="480" y="215" width="260" height="145"/><line class="optic" x1="480" y1="215" x2="740" y2="215"/><line class="axis" x1="610" y1="180" x2="610" y2="350" stroke-dasharray="8 7"/><path class="accent" d="M500 345 L610 215 L720 345"/><path class="accent2" d="M610 180 C640 190 680 190 720 180"/>',
        "prism": '<path class="layer1" d="M535 350 L585 185 L665 350 Z"/><path class="accent" d="M480 270 L560 270 L640 305 L738 330"/><line class="axis" x1="475" y1="270" x2="740" y2="270" stroke-dasharray="8 7"/><path class="accent2" d="M574 220 A36 36 0 0 1 604 225"/>',
        "grin": '<rect class="layer1" x="530" y="190" width="135" height="160"/><line class="axis" x1="475" y1="270" x2="740" y2="270" stroke-dasharray="8 7"/><path class="accent" d="M480 215 H530 C575 215 610 235 665 270 L720 270 M480 325 H530 C575 325 610 305 665 270"/><circle class="point" cx="720" cy="270" r="6"/>',
        "matrix": '<rect class="iconbox" x="520" y="205" width="75" height="75"/><path class="thin" d="M557 205 V280 M520 242 H595"/><rect class="iconbox" x="625" y="205" width="75" height="75"/><path class="thin" d="M662 205 V280 M625 242 H700"/><path class="accent" d="M595 242 H625"/>',
        "wave": '<path class="accent" d="M478 270 C505 210 535 330 565 270 S625 210 655 270 S715 330 738 270"/><line class="axis" x1="478" y1="270" x2="738" y2="270"/>',
        "gaussian": '<path class="accent" d="M480 185 Q600 265 738 205 M480 355 Q600 275 738 335"/><line class="axis" x1="480" y1="270" x2="738" y2="270"/><line class="thin" x1="600" y1="235" x2="600" y2="305"/>',
        "fourier": '<rect class="opticfill" x="500" y="205" width="18" height="130"/><path class="optic" d="M590 185 Q550 270 590 355 M590 185 Q630 270 590 355"/><circle class="point" cx="710" cy="270" r="13"/><path class="accent" d="M478 230 L590 230 L710 270 M478 310 L590 310 L710 270"/>',
        "field": '<path class="accent" d="M480 255 C510 190 540 320 570 255 S630 190 660 255 S710 320 738 255"/><path class="accent2" d="M480 290 C510 225 540 355 570 290 S630 225 660 290 S710 355 738 290"/>',
        "polarization": '<ellipse class="accent" cx="535" cy="270" rx="52" ry="82"/><line class="optic" x1="610" y1="185" x2="610" y2="355"/><path class="accent2" d="M665 315 L710 225 M665 225 L710 315"/>',
        "multilayer": '<rect class="layer1" x="520" y="185" width="45" height="170"/><rect class="layer2" x="565" y="185" width="45" height="170"/><rect class="layer1" x="610" y="185" width="45" height="170"/><rect class="layer2" x="655" y="185" width="45" height="170"/><path class="accent" d="M475 235 L520 270 L475 305 M520 270 H735"/>',
        "waveguide": '<rect class="layer2" x="478" y="190" width="260" height="55"/><rect class="layer1" x="478" y="245" width="260" height="55"/><rect class="layer2" x="478" y="300" width="260" height="55"/><path class="accent" d="M480 270 C520 220 555 320 595 270 S670 220 735 270"/>',
        "fiber": '<circle class="layer2" cx="610" cy="270" r="105"/><circle class="layer1" cx="610" cy="270" r="62"/><path class="accent" d="M492 270 L548 235 L610 300 L672 235 L728 270"/>',
        "resonator": '<path class="optic" d="M500 185 Q535 270 500 355 M720 185 Q685 270 720 355"/><path class="accent" d="M510 245 L710 295 M710 295 L510 245"/><path class="accent2" d="M515 270 C545 230 575 310 605 270 S665 230 705 270"/>',
        "statistical": '<path class="axis" d="M480 335 H738 M500 350 V180"/><path class="accent" d="M500 335 C535 332 550 300 575 245 C600 185 635 185 660 245 C685 300 700 332 738 335"/><path class="accent2" d="M510 285 C540 245 570 325 600 275 S660 235 705 295"/>',
        "quantum": '<path class="accent" d="M480 270 H575 M595 250 L625 280 M595 280 L625 250 M625 265 L718 205 M625 265 L718 330"/><circle class="point" cx="480" cy="270" r="11"/><circle class="point" cx="718" cy="205" r="11"/><circle class="point" cx="718" cy="330" r="11"/>',
        "atomic": '<path class="thin" d="M500 335 H720 M525 270 H695 M550 205 H670"/><path class="accent" d="M570 325 V220"/><path class="accent2" d="M645 215 V260"/>',
        "amplifier": '<path class="accent2" d="M500 325 V215"/><rect class="layer1" x="560" y="205" width="105" height="130"/><path class="accent" d="M480 270 H560 M665 270 H738"/><path class="thin" d="M580 305 H645 M590 270 H635 M600 235 H625"/>',
        "laser": '<path class="optic" d="M495 190 Q525 270 495 350 M720 190 Q690 270 720 350"/><rect class="layer1" x="570" y="225" width="75" height="90"/><path class="accent" d="M505 270 H710"/><path class="accent2" d="M607 350 V315"/>',
        "semiconductor": '<path class="accent" d="M485 225 Q610 185 735 225 M485 315 Q610 355 735 315"/><line class="thin" x1="485" y1="255" x2="735" y2="255" stroke-dasharray="8 7"/><line class="thin" x1="485" y1="285" x2="735" y2="285" stroke-dasharray="8 7"/><path class="accent2" d="M610 305 V235"/>',
        "source": '<path class="accent" d="M485 220 Q610 185 735 220 M485 320 Q610 355 735 320"/><path class="accent2" d="M580 305 V235"/><path class="thin" d="M610 245 L685 190 M625 265 L710 230"/>',
        "detector": '<path class="accent" d="M480 215 L555 255 M480 255 L555 285"/><path class="optic" d="M585 205 V335 M640 205 V335"/><path class="thin" d="M585 270 H555 M640 270 H720 M680 235 V305"/>',
        "acousto": '<path class="thin" d="M550 185 L500 355 M590 185 L540 355 M630 185 L580 355 M670 185 L620 355 M710 185 L660 355"/><path class="accent" d="M475 315 L610 270 L725 205"/><path class="accent2" d="M485 190 H700"/>',
        "electro": '<path class="optic" d="M480 225 C555 225 555 315 640 315 H738 M480 315 C555 315 555 225 640 225 H738"/><path class="accent2" d="M585 185 V355"/>',
        "nonlinear": '<path class="accent" d="M480 225 H585 M480 315 H585 M635 270 H738"/><circle class="point" cx="610" cy="270" r="34"/>',
        "pulse": '<path class="axis" d="M478 335 H738"/><path class="accent" d="M485 335 C535 335 545 190 590 190 C635 190 645 335 695 335"/><path class="accent2" d="M555 335 C580 335 585 245 610 245 C635 245 640 335 665 335"/>',
        "interconnect": '<path class="thin" d="M500 205 H720 M500 270 H720 M500 335 H720 M530 180 V360 M610 180 V360 M690 180 V360"/><circle class="point" cx="530" cy="205" r="9"/><circle class="point" cx="610" cy="270" r="9"/><circle class="point" cx="690" cy="335" r="9"/><path class="accent" d="M480 205 H530 M530 205 L610 270 L690 335 H738"/>',
    }
    return icons[category]


VISIBLE_VARIABLES = {
    "ray": ("n₁", "n₂", "θ₁", "θ₂"),
    "mirror": ("y", "θᵢ", "θᵣ", "R", "f"),
    "lens": ("n", "y", "R₁", "R₂", "f"),
    "refracting": ("n₁", "n₂", "θ₁", "θ₂", "y", "R", "z₁", "z₂"),
    "cartesian_oval": ("n₁", "n₂", "y", "z", "z₁", "z₂"),
    "tir": ("n=3.6", "θᵢ", "θᶜ=16.13°"),
    "prism": ("d₀", "a", "n", "k₀", "kₓ", "θ"),
    "grin": ("n₀", "d₀", "a", "ρ", "f"),
    "matrix": ("A", "B", "C", "D", "y", "nθ", "y′", "nθ′", "d"),
    "wave": ("A", "k", "λ", "I"),
    "gaussian": ("W₀", "z₀", "q", "R"),
    "fourier": ("g", "G", "fₓ", "fᵧ", "λf"),
    "field": ("E", "H", "k", "ε"),
    "polarization": ("Eₓ", "Eᵧ", "J", "S₀", "S₁", "S₂", "S₃"),
    "multilayer": ("nᵢ", "dᵢ", "r", "t", "Λ"),
    "waveguide": ("n₁", "n₂", "d", "a", "β", "V"),
    "fiber": ("a", "NA", "β", "L"),
    "resonator": ("L", "R₁", "R₂", "g₁", "g₂", "ν"),
    "statistical": ("J", "g", "Tᶜ", "Δν"),
    "quantum": ("hν", "p", "P", "σ"),
    "atomic": ("Eᵢ", "ν", "Nᵢ", "T"),
    "amplifier": ("Nᵢ", "Rₚ", "σ", "G"),
    "laser": ("N", "g", "τ", "R", "P"),
    "semiconductor": ("Eᶜ", "Eᵥ", "Fₙ", "Fₚ", "n", "p"),
    "source": ("Eᵧ", "Fₙ", "Fₚ", "λ", "η"),
    "detector": ("Φ", "η", "ℛ", "B", "i"),
    "acousto": ("Λ", "f", "θᴮ", "D"),
    "electro": ("V", "Vπ", "Δφ", "κ"),
    "nonlinear": ("ω₁", "ω₂", "ω₃", "k₁", "k₂", "k₃", "χ⁽ⁿ⁾", "Δk"),
    "pulse": ("T", "ζ", "Dν", "z"),
    "interconnect": ("M", "L", "B", "λᵢ", "V"),
}


def variable_markup(category: str) -> str:
    """Place every legend symbol next to the feature it identifies."""

    labels = {
        "ray": '<text class="var" x="505" y="190">n₁</text><text class="var" x="690" y="342">n₂ &gt; n₁</text><text class="var" x="548" y="245">θ₁</text><text class="var" x="670" y="300">θ₂</text>',
        "mirror": '<line class="callout" x1="505" y1="270" x2="505" y2="214"/><text class="var" x="492" y="242">y</text><text class="var" x="625" y="245">θᵢ</text><text class="var" x="625" y="305">θᵣ</text><text class="var" x="706" y="205">R</text><text class="var" x="590" y="292">f</text>',
        "lens": '<line class="callout" x1="500" y1="305" x2="500" y2="240"/><text class="var" x="487" y="270">y</text><text class="var" x="607" y="230">n</text><text class="var" x="555" y="205">R₁</text><text class="var" x="650" y="205">R₂</text><line class="callout" x1="604" y1="335" x2="700" y2="335"/><path class="tick" d="M604 329 V341 M700 329 V341"/><text class="var" x="652" y="355">f</text>',
        "refracting": '<text class="var" x="500" y="190">n₁</text><text class="var" x="700" y="342">n₂</text><text class="var" x="548" y="245">θ₁</text><text class="var" x="670" y="300">θ₂</text><line class="callout" x1="595" y1="270" x2="595" y2="330"/><text class="var" x="582" y="312">y</text><text class="var" x="690" y="260">R</text><text class="var smallvar" x="530" y="325">z₁</text><text class="var smallvar" x="710" y="325">z₂</text>',
        "cartesian_oval": '<text class="var" x="510" y="190">n₁</text><text class="var" x="700" y="190">n₂</text><text class="var" x="600" y="205">y</text><text class="var" x="645" y="335">z</text><text class="var smallvar" x="525" y="300">z₁</text><text class="var smallvar" x="700" y="300">z₂</text>',
        "tir": '<text class="var" x="520" y="335">n=3.6</text><text class="var" x="575" y="260">θᵢ</text><text class="var" x="670" y="205">θᶜ=16.13°</text>',
        "prism": '<text class="var" x="555" y="335">d₀</text><text class="var" x="590" y="215">a</text><text class="var" x="600" y="300">n</text><text class="var" x="500" y="255">k₀</text><text class="var" x="690" y="315">kₓ</text><text class="var" x="710" y="350">θ</text>',
        "grin": '<text class="var" x="590" y="255">n₀</text><text class="var" x="595" y="345">d₀</text><text class="var" x="545" y="210">a</text><text class="var" x="640" y="220">ρ</text><text class="var" x="700" y="255">f</text>',
        "matrix": '<text class="var smallvar" x="539" y="233">A</text><text class="var smallvar" x="576" y="233">B</text><text class="var smallvar" x="539" y="268">C</text><text class="var smallvar" x="576" y="268">D</text><text class="var smallvar" x="642" y="233">A</text><text class="var smallvar" x="680" y="233">B</text><text class="var smallvar" x="642" y="268">C</text><text class="var smallvar" x="680" y="268">D</text><text class="var" x="490" y="190">y, nθ</text><text class="var" x="685" y="310">y′, nθ′</text><text class="var" x="610" y="225">d</text>',
        "wave": '<text class="var" x="500" y="220">A</text><text class="var" x="530" y="315">λ</text><text class="var" x="650" y="215">k →</text><text class="var" x="705" y="315">I</text>',
        "gaussian": '<text class="var" x="575" y="225">W₀</text><text class="var" x="545" y="325">z₀</text><text class="var" x="620" y="300">q</text><text class="var" x="700" y="220">R</text>',
        "fourier": '<text class="var" x="490" y="198">g</text><text class="var" x="710" y="248">G</text><text class="var" x="678" y="345">fₓ</text><text class="var" x="720" y="345">fᵧ</text><text class="var" x="620" y="205">λf</text>',
        "field": '<text class="var" x="520" y="210">E</text><text class="var" x="550" y="335">H</text><text class="var" x="680" y="205">k →</text><text class="var" x="700" y="335">ε</text>',
        "polarization": '<text class="var" x="482" y="270">Eₓ</text><text class="var" x="535" y="180">Eᵧ</text><text class="var" x="600" y="205">J</text><text class="var smallvar" x="662" y="205">S₀</text><text class="var smallvar" x="700" y="205">S₁</text><text class="var smallvar" x="662" y="345">S₂</text><text class="var smallvar" x="700" y="345">S₃</text>',
        "multilayer": '<text class="var smallvar" x="535" y="210">nᵢ</text><text class="var smallvar" x="542" y="345">dᵢ</text><text class="var" x="485" y="225">r</text><text class="var" x="715" y="255">t</text><text class="var" x="620" y="180">Λ</text>',
        "waveguide": '<text class="var" x="495" y="230">n₂</text><text class="var" x="495" y="285">n₁</text><text class="var" x="715" y="230">n₂</text><text class="var" x="560" y="330">d, a</text><text class="var" x="650" y="255">β →</text><text class="var" x="700" y="330">V</text>',
        "fiber": '<line class="callout" x1="610" y1="270" x2="672" y2="270"/><text class="var" x="640" y="260">a</text><text class="var" x="505" y="210">NA</text><text class="var" x="680" y="225">β →</text><text class="var" x="700" y="330">L</text>',
        "resonator": '<line class="callout" x1="510" y1="365" x2="710" y2="365"/><path class="tick" d="M510 359 V371 M710 359 V371"/><text class="var" x="610" y="355">L</text><text class="var" x="485" y="205">R₁</text><text class="var" x="710" y="205">R₂</text><text class="var smallvar" x="530" y="230">g₁</text><text class="var smallvar" x="685" y="230">g₂</text><text class="var" x="620" y="215">ν</text>',
        "statistical": '<text class="var" x="540" y="210">J</text><text class="var" x="635" y="205">g</text><text class="var" x="555" y="315">Tᶜ</text><text class="var" x="680" y="315">Δν</text>',
        "quantum": '<text class="var" x="500" y="255">hν</text><text class="var" x="545" y="255">p →</text><text class="var" x="690" y="190">P</text><text class="var" x="690" y="350">σ</text>',
        "atomic": '<text class="var" x="715" y="330">Eᵢ</text><text class="var" x="552" y="270">ν</text><text class="var" x="690" y="260">Nᵢ</text><text class="var" x="690" y="195">T</text>',
        "amplifier": '<text class="var" x="600" y="255">Nᵢ</text><text class="var" x="485" y="315">Rₚ</text><text class="var" x="645" y="200">σ</text><text class="var" x="705" y="255">G</text>',
        "laser": '<text class="var" x="590" y="255">N</text><text class="var" x="625" y="255">g</text><text class="var" x="607" y="340">τ</text><text class="var" x="485" y="205">R</text><text class="var" x="700" y="255">P</text>',
        "semiconductor": '<text class="var" x="500" y="210">Eᶜ</text><text class="var" x="500" y="340">Eᵥ</text><text class="var" x="680" y="250">Fₙ</text><text class="var" x="680" y="305">Fₚ</text><text class="var" x="580" y="225">n</text><text class="var" x="625" y="330">p</text>',
        "source": '<text class="var" x="500" y="270">Eᵧ</text><text class="var" x="680" y="245">Fₙ</text><text class="var" x="680" y="300">Fₚ</text><text class="var" x="680" y="190">λ</text><text class="var" x="715" y="235">η</text>',
        "detector": '<text class="var" x="490" y="195">Φ</text><text class="var" x="565" y="245">η</text><text class="var" x="660" y="245">ℛ</text><text class="var" x="690" y="215">B</text><text class="var" x="715" y="290">i</text>',
        "acousto": '<text class="var" x="550" y="205">Λ</text><text class="var" x="655" y="205">f</text><text class="var" x="635" y="300">θᴮ</text><text class="var" x="500" y="345">D</text>',
        "electro": '<text class="var" x="600" y="180">V</text><text class="var" x="625" y="205">Vπ</text><text class="var" x="680" y="300">Δφ</text><text class="var" x="535" y="300">κ</text>',
        "nonlinear": '<text class="var" x="515" y="215">ω₁, k₁</text><text class="var" x="515" y="345">ω₂, k₂</text><text class="var" x="685" y="255">ω₃, k₃</text><text class="var" x="610" y="277">χ⁽ⁿ⁾</text><text class="var" x="685" y="310">Δk</text>',
        "pulse": '<text class="var" x="570" y="180">T</text><text class="var" x="540" y="315">ζ</text><text class="var" x="620" y="230">Dν</text><text class="var" x="700" y="325">z →</text>',
        "interconnect": '<text class="var" x="500" y="190">M</text><text class="var" x="525" y="350">L</text><text class="var" x="600" y="195">B</text><text class="var" x="635" y="255">λᵢ</text><text class="var" x="700" y="320">V</text>',
    }
    return labels[category]


def svg_text_block(text: str, x: int, y: int, width: int = 24) -> str:
    """Return a centered SVG text element with deterministic word wrapping."""

    lines = textwrap.wrap(text, width=width, break_long_words=False) or [text]
    line_height = 27
    start_y = y - (len(lines) - 1) * line_height // 2
    spans = "".join(
        f'<tspan x="{x}" y="{start_y + index * line_height}">{html.escape(line)}</tspan>'
        for index, line in enumerate(lines)
    )
    return f'<text class="label" x="{x}">{spans}</text>'


def svg_for(identity: str, title: str, category: str, figure_number: int) -> str:
    meta = META[category]
    safe_title = html.escape(title)
    safe_desc = html.escape(
        f"Figure {figure_number}, a concept diagram for {identity}, {title}. "
        "The input, physical model, output, variables, and verification method "
        "are labeled."
    )
    given_text = svg_text_block(meta.given, 195, 285, 22)
    model_text = svg_text_block(meta.model, 607, 390, 27)
    result_text = svg_text_block(meta.result, 1005, 285, 22)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="560" viewBox="0 0 1200 560" role="img" aria-labelledby="title desc" data-category="{category}" data-figure="{figure_number}">
  <title id="title">Figure {figure_number} — {html.escape(identity)}: {safe_title}</title>
  <desc id="desc">{safe_desc}</desc>
  <defs>
    <style>
      .bg{{fill:#f7fafc}}.card{{fill:#fff;stroke:#b9c7d6;stroke-width:2}}.band{{fill:#eaf2f8}}.figureid{{font:700 14px sans-serif;fill:#286f9e;letter-spacing:1.2px}}.head{{font:700 25px sans-serif;fill:#18324a}}.sub{{font:17px sans-serif;fill:#486581}}.tag{{font:700 16px sans-serif;fill:#286f9e;letter-spacing:1px}}.label{{font:700 20px sans-serif;fill:#243b53;text-anchor:middle}}.legend{{font:18px sans-serif;fill:#334e68}}.check{{font:17px sans-serif;fill:#486581}}.accent{{fill:none;stroke:#d9485f;stroke-width:5;stroke-linecap:round;stroke-linejoin:round}}.accent2{{fill:none;stroke:#8b5cf6;stroke-width:4;stroke-linecap:round;stroke-linejoin:round}}.optic{{fill:none;stroke:#286f9e;stroke-width:5}}.thin{{fill:none;stroke:#61788a;stroke-width:3}}.axis{{fill:none;stroke:#8295a5;stroke-width:2}}.point{{fill:#173f5f}}.iconbox{{fill:#edf7ff;stroke:#286f9e;stroke-width:3}}.opticfill{{fill:#286f9e}}.layer1{{fill:#d9ecff;stroke:#286f9e;stroke-width:2}}.layer2{{fill:#e7f7ee;stroke:#2b7a78;stroke-width:2}}.icontext{{font:italic 22px serif;fill:#6d28d9}}.var{{font:italic 20px serif;fill:#54278f;text-anchor:middle;paint-order:stroke;stroke:#fff;stroke-width:5px;stroke-linejoin:round}}.smallvar{{font-size:17px}}.callout{{fill:none;stroke:#54278f;stroke-width:2}}.tick{{fill:none;stroke:#54278f;stroke-width:2}}.flow{{stroke:#334e68;stroke-width:3;marker-end:url(#arrow)}}
    </style>
    <marker id="arrow" markerUnits="userSpaceOnUse" markerWidth="13" markerHeight="13" refX="13" refY="6.5" orient="auto"><path d="M0,0 L13,6.5 L0,13 Z" fill="#334e68"/></marker>
  </defs>
  <rect class="bg" width="1200" height="560" rx="18"/>
  <text class="figureid" x="55" y="25">FIGURE {figure_number}</text>
  <text class="head" x="55" y="55">{safe_title}</text>
  <text class="sub" x="55" y="84">{html.escape(identity)} • illustrated calculation map</text>

  <rect class="card" x="45" y="120" width="300" height="295" rx="16"/>
  <rect class="card" x="450" y="120" width="315" height="295" rx="16"/>
  <rect class="card" x="855" y="120" width="300" height="295" rx="16"/>
  <text class="tag" x="70" y="153">GIVEN / DEFINITIONS</text>
  <text class="tag" x="475" y="153">MODEL / OPERATION</text>
  <text class="tag" x="880" y="153">RESULT / INTERPRETATION</text>
  {given_text}
  {model_text}
  {result_text}
  <line class="flow" x1="345" y1="270" x2="440" y2="270"/>
  <line class="flow" x1="765" y1="270" x2="845" y2="270"/>
  {icon_markup(category)}
  <g id="variable-labels">{variable_markup(category)}</g>

  <rect class="band" x="45" y="440" width="1110" height="85" rx="12"/>
  <text class="legend" x="65" y="474">Variables labeled on model — {html.escape(meta.variables)}</text>
  <text class="check" x="65" y="507">Independent check — {html.escape(meta.check)}</text>
</svg>
'''


def figure_block(
    chapter: int, section: str, item: str, title: str, figure_number: int
) -> str:
    filename = f"exercise_{chapter:02d}_{int(section):02d}_{int(item):02d}.svg"
    target = f"fop-exercise-{chapter}-{section}-{item}-illustration"
    return f'''.. _{target}:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/{filename}
   :alt: Illustrated calculation map for Exercise {chapter}.{section}-{item}, {title}
   :align: center
   :width: 95%

   **Figure {figure_number} — Exercise {chapter}.{section}-{item}: {title}.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.
'''


def transform_exercise_body(
    body: str,
    chapter: int,
    section: str,
    item: str,
    title: str,
    figure_number: int,
) -> str:
    filename = f"exercise_{chapter:02d}_{int(section):02d}_{int(item):02d}.svg"
    if filename not in body:
        required = (
            "**Definitions and setup.**",
            "**Mathematical formulas used.**",
            "**Worked derivation.**",
            "**Check.**",
        )
        missing = [marker for marker in required if marker not in body]
        if missing:
            raise RuntimeError(
                f"Exercise {chapter}.{section}-{item} is missing markers: {missing}"
            )

        body = body.replace(
            "**Definitions and setup.**", "**Step 1 — Definitions and setup.**", 1
        )
        body = body.replace(
            "**Mathematical formulas used.**",
            "**Step 2 — Mathematical formulas used.**",
            1,
        )
        body = body.replace(
            "**Worked derivation.**", "**Step 3 — Worked derivation.**", 1
        )
        body = body.replace(
            "**Numbered result.**", "**Step 4 — State the numbered result.**", 1
        )
        body = body.replace("**Check.**", "**Step 5 — Check.**", 1)

        step_two = "\n\n**Step 2 — Mathematical formulas used.**"
        body = body.replace(
            step_two,
            f"\n\n{figure_block(chapter, section, item, title, figure_number)}"
            f"{step_two}",
            1,
        )
        if "**Step 4 — State the numbered result.**" not in body:
            step_five = "\n\n**Step 5 — Check.**"
            interpretation = (
                "\n\n**Step 4 — Interpret the result.**  The final relation or "
                "conclusion in Step 3 is the requested result.  Read its sign, "
                "scale, or physical classification using the conventions fixed "
                "in Step 1."
            )
            body = body.replace(step_five, interpretation + step_five, 1)
    else:
        target = f"fop-exercise-{chapter}-{section}-{item}-illustration"
        existing_figure = re.compile(
            rf"\.\. _{re.escape(target)}:\n\n\.\. figure:: .*?"
            r"(?=\n\n\*\*Step 2 —)",
            re.DOTALL,
        )
        replacement = figure_block(
            chapter, section, item, title, figure_number
        ).rstrip()
        body, replacements = existing_figure.subn(replacement, body, count=1)
        if replacements != 1:
            raise RuntimeError(
                f"Exercise {chapter}.{section}-{item} figure block was not found"
            )
    return body


def number_snell_figure(body: str, figure_number: int) -> str:
    """Give the hand-authored Snell construction the same stable caption."""

    target = "fop-exercise-1-1-1-geometry"
    existing_figure = re.compile(
        rf"\.\. _{target}:\n\n\.\. figure:: .*?"
        r"(?=\n\n\*\*Definitions and assumptions\.\*\*)",
        re.DOTALL,
    )
    replacement = f'''.. _{target}:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/snells_law_geometry.svg
   :alt: Labeled geometry of a refracted ray from A through interface point P to B
   :align: center
   :width: 95%

   **Figure {figure_number} — Exercise 1.1-1: Snell's law from stationary
   optical path.** The crossing point has horizontal coordinate :math:`x`.
   Every geometrical variable used in the derivation is defined in the drawing.'''
    body, replacements = existing_figure.subn(replacement, body, count=1)
    if replacements != 1:
        raise RuntimeError("Exercise 1.1-1 figure block was not found")
    return body


def transform_chapter(
    text: str, figure_numbers: dict[tuple[int, int, int], int]
) -> tuple[str, int]:
    entries = list(ENTRY_RE.finditer(text))
    if not entries:
        return text, 0
    chunks = [text[: entries[0].start()]]
    changed = 0
    for entry_index, entry in enumerate(entries):
        end = entries[entry_index + 1].start() if entry_index + 1 < len(entries) else len(text)
        body = text[entry.end() : end]
        kind, chapter_s, section, item, raw_title = entry.groups()
        chapter = int(chapter_s)
        title = clean_title(raw_title)
        if kind == "Exercise":
            figure_number = figure_numbers[(chapter, int(section), int(item))]
            if chapter == 1 and section == "1" and item == "1":
                new_body = number_snell_figure(body, figure_number)
            else:
                category = category_for(chapter, title)
                filename = (
                    f"exercise_{chapter:02d}_{int(section):02d}_{int(item):02d}.svg"
                )
                svg_path = ASSET_DIR / filename
                svg = svg_for(
                    f"Exercise {chapter}.{section}-{item}",
                    title,
                    category,
                    figure_number,
                )
                if (
                    not svg_path.exists()
                    or svg_path.read_text(encoding="utf-8") != svg
                ):
                    svg_path.write_text(svg, encoding="utf-8")
                new_body = transform_exercise_body(
                    body, chapter, section, item, title, figure_number
                )
            changed += new_body != body
            body = new_body
        chunks.append(entry.group(0) + body)
    return "".join(chunks).rstrip() + "\n", changed


def exercise_figure_numbers() -> dict[tuple[int, int, int], int]:
    """Number every boxed exercise once, in documentation reading order."""

    identities: list[tuple[int, int, int]] = []
    for path in sorted(COLLECTION.glob("ch[0-9][0-9]_*.rst")):
        text = path.read_text(encoding="utf-8")
        for match in ENTRY_RE.finditer(text):
            kind, chapter, section, item, _ = match.groups()
            if kind == "Exercise":
                identities.append((int(chapter), int(section), int(item)))
    if len(identities) != 131 or len(set(identities)) != 131:
        raise RuntimeError(
            f"Expected 131 unique exercises for figure numbering, got "
            f"{len(identities)} entries and {len(set(identities))} unique IDs"
        )
    return {identity: index for index, identity in enumerate(identities, start=1)}


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    figure_numbers = exercise_figure_numbers()
    changed_entries = 0
    for path in sorted(COLLECTION.glob("ch[0-9][0-9]_*.rst")):
        original = path.read_text(encoding="utf-8")
        updated, count = transform_chapter(original, figure_numbers)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
        changed_entries += count

    generated = len(list(ASSET_DIR.glob("exercise_*.svg")))
    print(
        f"Generated {generated} exercise SVGs; "
        f"updated {changed_entries} exercise entries."
    )


if __name__ == "__main__":
    main()
