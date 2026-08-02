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
        "surface geometry",
        "image or output ray",
        "n: refractive index • θ: ray angle • R: radius • f: focal length",
        "sign convention; equal-index and paraxial limits",
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
    "y: ray height • θ: angle • R: mirror radius • f: focal length",
    "reflection symmetry, sign convention, and paraxial limit",
)
META["lens"] = DiagramMeta(
    "object or incident beam",
    "refraction by lens",
    "image or focused beam",
    "n: refractive index • y: ray height • R₁,R₂: radii • f: focal length",
    "thin-lens limit, ray intersection, and dimensions",
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
    if chapter == 2 and any(word in lower for word in ("prism", "grin")):
        return "ray"
    return CHAPTER_CATEGORY[chapter]


def icon_markup(category: str) -> str:
    icons = {
        "ray": '<line class="optic" x1="610" y1="185" x2="610" y2="355"/><line class="thin" x1="610" y1="180" x2="610" y2="360" stroke-dasharray="8 7"/><path class="accent" d="M480 215 L610 270 L738 325"/><path class="accent2" d="M610 225 A48 48 0 0 0 565 245 M610 315 A48 48 0 0 1 650 295"/>',
        "mirror": '<path class="optic" d="M690 185 Q625 270 690 355"/><path class="accent" d="M480 205 L675 270 L485 335"/><line class="axis" x1="475" y1="270" x2="735" y2="270"/><line class="thin" x1="675" y1="190" x2="675" y2="350" stroke-dasharray="8 7"/>',
        "lens": '<path class="accent" d="M482 305 L592 248 L730 302"/><path class="optic" d="M604 188 Q570 270 604 352 M604 188 Q638 270 604 352"/><line class="axis" x1="475" y1="305" x2="735" y2="305"/>',
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
        "electro": '<path class="optic" d="M480 225 C555 225 555 315 640 315 H738 M480 315 C555 315 555 225 640 225 H738"/><path class="accent2" d="M585 185 V355"/><text class="icontext" x="600" y="180">V</text>',
        "nonlinear": '<path class="accent" d="M480 225 H585 M480 315 H585 M635 270 H738"/><circle class="point" cx="610" cy="270" r="34"/><text class="icontext" x="515" y="215">ω₁</text><text class="icontext" x="515" y="345">ω₂</text><text class="icontext" x="670" y="255">ω₃</text>',
        "pulse": '<path class="axis" d="M478 335 H738"/><path class="accent" d="M485 335 C535 335 545 190 590 190 C635 190 645 335 695 335"/><path class="accent2" d="M555 335 C580 335 585 245 610 245 C635 245 640 335 665 335"/>',
        "interconnect": '<path class="thin" d="M500 205 H720 M500 270 H720 M500 335 H720 M530 180 V360 M610 180 V360 M690 180 V360"/><circle class="point" cx="530" cy="205" r="9"/><circle class="point" cx="610" cy="270" r="9"/><circle class="point" cx="690" cy="335" r="9"/><path class="accent" d="M480 205 H530 M530 205 L610 270 L690 335 H738"/>',
    }
    return icons[category]


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


def svg_for(identity: str, title: str, category: str) -> str:
    meta = META[category]
    safe_title = html.escape(title)
    safe_desc = html.escape(
        f"Concept diagram for {identity}, {title}. The input, physical model, "
        "output, variables, and verification method are labeled."
    )
    given_text = svg_text_block(meta.given, 195, 285, 22)
    model_text = svg_text_block(meta.model, 607, 390, 27)
    result_text = svg_text_block(meta.result, 1005, 285, 22)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="560" viewBox="0 0 1200 560" role="img" aria-labelledby="title desc">
  <title id="title">{html.escape(identity)} — {safe_title}</title>
  <desc id="desc">{safe_desc}</desc>
  <defs>
    <style>
      .bg{{fill:#f7fafc}}.card{{fill:#fff;stroke:#b9c7d6;stroke-width:2}}.band{{fill:#eaf2f8}}.head{{font:700 27px sans-serif;fill:#18324a}}.sub{{font:18px sans-serif;fill:#486581}}.tag{{font:700 16px sans-serif;fill:#286f9e;letter-spacing:1px}}.label{{font:700 20px sans-serif;fill:#243b53;text-anchor:middle}}.legend{{font:18px sans-serif;fill:#334e68}}.check{{font:17px sans-serif;fill:#486581}}.accent{{fill:none;stroke:#d9485f;stroke-width:5;stroke-linecap:round;stroke-linejoin:round}}.accent2{{fill:none;stroke:#8b5cf6;stroke-width:4;stroke-linecap:round;stroke-linejoin:round}}.optic{{fill:none;stroke:#286f9e;stroke-width:5}}.thin{{fill:none;stroke:#61788a;stroke-width:3}}.axis{{fill:none;stroke:#8295a5;stroke-width:2}}.point{{fill:#173f5f}}.iconbox{{fill:#edf7ff;stroke:#286f9e;stroke-width:3}}.opticfill{{fill:#286f9e}}.layer1{{fill:#d9ecff;stroke:#286f9e;stroke-width:2}}.layer2{{fill:#e7f7ee;stroke:#2b7a78;stroke-width:2}}.icontext{{font:italic 22px serif;fill:#6d28d9}}.flow{{stroke:#334e68;stroke-width:3;marker-end:url(#arrow)}}
    </style>
    <marker id="arrow" markerUnits="userSpaceOnUse" markerWidth="13" markerHeight="13" refX="13" refY="6.5" orient="auto"><path d="M0,0 L13,6.5 L0,13 Z" fill="#334e68"/></marker>
  </defs>
  <rect class="bg" width="1200" height="560" rx="18"/>
  <text class="head" x="55" y="48">{safe_title}</text>
  <text class="sub" x="55" y="78">{html.escape(identity)} • illustrated calculation map</text>

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

  <rect class="band" x="45" y="440" width="1110" height="85" rx="12"/>
  <text class="legend" x="65" y="474">Variables — {html.escape(meta.variables)}</text>
  <text class="check" x="65" y="507">Independent check — {html.escape(meta.check)}</text>
</svg>
'''


def figure_block(chapter: int, section: str, item: str, title: str) -> str:
    filename = f"exercise_{chapter:02d}_{int(section):02d}_{int(item):02d}.svg"
    target = f"fop-exercise-{chapter}-{section}-{item}-illustration"
    return f'''.. _{target}:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/{filename}
   :alt: Illustrated calculation map for Exercise {chapter}.{section}-{item}, {title}
   :align: center
   :width: 95%

   The diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route.
'''


def transform_exercise_body(
    body: str, chapter: int, section: str, item: str, title: str
) -> str:
    filename = f"exercise_{chapter:02d}_{int(section):02d}_{int(item):02d}.svg"
    if filename in body:
        return body

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

    figure = figure_block(chapter, section, item, title)
    step_two = "\n\n**Step 2 — Mathematical formulas used.**"
    body = body.replace(step_two, f"\n\n{figure}{step_two}", 1)
    if "**Step 4 — State the numbered result.**" not in body:
        step_five = "\n\n**Step 5 — Check.**"
        interpretation = (
            "\n\n**Step 4 — Interpret the result.**  The final relation or "
            "conclusion in Step 3 is the requested result.  Read its sign, scale, "
            "or physical classification using the conventions fixed in Step 1."
        )
        body = body.replace(step_five, interpretation + step_five, 1)
    return body


def transform_chapter(text: str) -> tuple[str, int]:
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
        if kind == "Exercise" and not (chapter == 1 and section == "1" and item == "1"):
            category = category_for(chapter, title)
            filename = f"exercise_{chapter:02d}_{int(section):02d}_{int(item):02d}.svg"
            svg_path = ASSET_DIR / filename
            svg = svg_for(f"Exercise {chapter}.{section}-{item}", title, category)
            if not svg_path.exists() or svg_path.read_text(encoding="utf-8") != svg:
                svg_path.write_text(svg, encoding="utf-8")
            new_body = transform_exercise_body(body, chapter, section, item, title)
            changed += new_body != body
            body = new_body
        chunks.append(entry.group(0) + body)
    return "".join(chunks).rstrip() + "\n", changed


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    changed_entries = 0
    for path in sorted(COLLECTION.glob("ch[0-9][0-9]_*.rst")):
        original = path.read_text(encoding="utf-8")
        updated, count = transform_chapter(original)
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
