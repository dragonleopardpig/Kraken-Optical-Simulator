"""bugs/0823: name the overlay family that drew a thing, instead of guessing.

Three Open 3D overlay families draw the SAME green (0.2, 0.9, 0.35) at the object
plane, scaled to the same field semi-diagonal. When a user says "toggle Refs off --
still showing", the only way to tell which family owns the disc has been to read a
memory note listing opacities, and bugs/0659 round 1 got it wrong and blamed Refs.

Optiland's NSQ viewer keeps a `_renderer_registry` mapping component type ->
renderer, so a drawn thing always has a declared owner. This is that idea aimed at
KrakenOS's actual problem: overlays are not per-component-type, so the registry maps
VISUAL SIGNATURE -> family, and answers "what drew this, and how do I turn it off?".

The registry is declarative data, and `verify_registry_against_source` re-reads the
real module constants so a drifted colour fails a guard instead of silently making
this file the next stale memory note.

Deliberately honest about what is NOT a constant: the reference-surface disc takes
its opacity from the scene bundle's mesh opacity, not a literal. That is precisely
why it cannot be identified by opacity, and why 0659 mis-blamed it.
"""

from __future__ import annotations

from dataclasses import dataclass, field


#: Colours match within this per-channel distance before two families are called
#: the same colour. The families that clash use byte-identical literals, so this
#: only needs to absorb float formatting, not perceptual similarity.
COLOR_MATCH_TOLERANCE: float = 1e-6

#: Opacity match window. Det fill (0.08) and QE disc (0.10) differ by 0.02, so the
#: window must stay well under that or the two become indistinguishable again.
OPACITY_MATCH_TOLERANCE: float = 0.005


@dataclass(frozen=True)
class OverlayFamily:
    """One overlay family: who draws it, what it looks like, how to turn it off."""

    name: str
    label: str
    toggle_var: str
    toggle_paths: tuple[str, ...]
    owner_module: str
    #: RGB literal, or None when the family has no single declared colour.
    color: tuple[float, float, float] | None
    #: Declared opacity literals. Empty when opacity is scene-derived.
    opacities: tuple[float, ...] = ()
    #: What the family actually draws, parallel to ``opacities`` where both are known.
    shapes: tuple[str, ...] = ()
    #: True when the service tracks and clears its own actors (the bugs/0660 law).
    owns_actors: bool = False
    #: Where a declared literal can be re-read from, for drift checking:
    #: {"attr or literal description": (module path, literal value)}
    source_literals: tuple[tuple[str, str, float], ...] = field(default_factory=tuple)
    notes: str = ""


OVERLAY_FAMILIES: tuple[OverlayFamily, ...] = (
    OverlayFamily(
        name="quick_estimation",
        label="Quick Estimation FOV",
        toggle_var="quick_estimation_var",
        toggle_paths=(
            'Left Panel > "Quick Estimation"',
            'Overlays > "FOV planes (QE)"',
        ),
        owner_module="KrakenOS.UI.services.quick_estimation_overlay",
        color=(0.2, 0.9, 0.35),
        opacities=(0.10, 1.0),
        shapes=("pick disc", "circle outline"),
        owns_actors=True,
        source_literals=(
            ("pick disc opacity", "KrakenOS/UI/services/quick_estimation_overlay.py", 0.10),
        ),
        notes=(
            "Silently ENABLED by several paths (the FOV dialog among them), so it can "
            "be on without the user having chosen it -- the usual reason a disc "
            "survives turning Refs off. Service owns its actors (bugs/0660)."
        ),
    ),
    OverlayFamily(
        name="detector_coverage",
        label="Detector coverage FOV",
        toggle_var="show_detector_overlays_var",
        toggle_paths=('Overlays > detector overlays',),
        owner_module="KrakenOS.UI.services.detector_coverage_overlay",
        color=(0.2, 0.9, 0.35),
        opacities=(0.08, 1.0),
        shapes=("pick fill", "FOV rectangle"),
        owns_actors=False,
        source_literals=(
            ("pick fill opacity", "KrakenOS/UI/services/detector_coverage_overlay.py", 0.08),
        ),
        notes=(
            "Draws a RECTANGLE where Quick Estimation draws a disc -- the shape "
            "separates them faster than the 0.02 opacity gap does."
        ),
    ),
    OverlayFamily(
        name="reference_surfaces",
        label="Reference surfaces",
        toggle_var="show_reference_surfaces_var",
        toggle_paths=('Overlays > reference surfaces',),
        owner_module="KrakenOS.UI.services.open3d_scene_refresh",
        color=None,
        opacities=(),
        shapes=("plane disc",),
        owns_actors=False,
        notes=(
            "NOT identifiable by opacity: the disc takes its opacity from the scene "
            "bundle's mesh opacity, which the refresh clamps per row -- there is no "
            "literal to match. bugs/0659 round 1 blamed this family for a disc it did "
            "not draw. Rule out the two green families by SHAPE first."
        ),
    ),
)


def _color_matches(a, b, tol: float = COLOR_MATCH_TOLERANCE) -> bool:
    if a is None or b is None:
        return False
    return all(abs(float(x) - float(y)) <= tol for x, y in zip(a, b, strict=True))


def families_sharing_color(color) -> tuple[OverlayFamily, ...]:
    """Every family declaring this colour -- the clash set for that colour."""
    return tuple(f for f in OVERLAY_FAMILIES if _color_matches(f.color, color))


def identify_overlay(
    color=None,
    opacity: float | None = None,
    shape: str | None = None,
) -> tuple[OverlayFamily, ...]:
    """Families matching the given signature, most specific evidence first.

    Any argument may be omitted. A family whose opacity is scene-derived can never
    be excluded by an opacity argument -- it has no literal to contradict, so it
    stays a candidate rather than being wrongly ruled out.
    """
    out = []
    for fam in OVERLAY_FAMILIES:
        if color is not None and fam.color is not None and not _color_matches(fam.color, color):
            continue
        if opacity is not None and fam.opacities:
            if not any(abs(float(o) - float(opacity)) <= OPACITY_MATCH_TOLERANCE
                       for o in fam.opacities):
                continue
        if shape is not None and fam.shapes:
            if not any(shape.lower() in s.lower() for s in fam.shapes):
                continue
        out.append(fam)
    return tuple(out)


def overlay_clash_report() -> list[str]:
    """Name every colour drawn by more than one family, and how to tell them apart."""
    lines: list[str] = []
    seen: list[tuple[float, float, float]] = []
    for fam in OVERLAY_FAMILIES:
        if fam.color is None or any(_color_matches(fam.color, c) for c in seen):
            continue
        seen.append(fam.color)
        sharing = families_sharing_color(fam.color)
        if len(sharing) < 2:
            continue
        names = ", ".join(f.label for f in sharing)
        lines.append(f"{len(sharing)} families share RGB {fam.color}: {names}.")
        for f in sharing:
            op = ", ".join(f"{o:g}" for o in f.opacities) if f.opacities else "scene-derived"
            sh = ", ".join(f.shapes) if f.shapes else "unspecified"
            lines.append(f"  - {f.label}: opacity {op}; shape {sh}; toggle {f.toggle_var}")
    # Families with no declared colour cannot be excluded by colour at all.
    for fam in OVERLAY_FAMILIES:
        if fam.color is None:
            lines.append(
                f"{fam.label} declares no colour literal, so it can never be ruled "
                f"out by colour or opacity -- separate it by shape."
            )
    return lines


def describe_family(name: str) -> str:
    """User-facing description of one family, including how to turn it off."""
    for fam in OVERLAY_FAMILIES:
        if fam.name == name:
            paths = "; ".join(fam.toggle_paths)
            op = ", ".join(f"{o:g}" for o in fam.opacities) if fam.opacities else "scene-derived"
            owns = "owns and clears its own actors" if fam.owns_actors else "actors cleared by the scene refresh"
            body = [
                f"{fam.label} ({fam.name})",
                f"  toggle: {fam.toggle_var} -- {paths}",
                f"  drawn by: {fam.owner_module}",
                f"  colour: {fam.color if fam.color is not None else 'no literal'}; opacity {op}",
                f"  shapes: {', '.join(fam.shapes) if fam.shapes else 'unspecified'}",
                f"  lifecycle: {owns}",
            ]
            if fam.notes:
                body.append(f"  note: {fam.notes}")
            return "\n".join(body)
    raise KeyError(f"no overlay family named {name!r}")


def verify_registry_against_source(repo_root=None) -> list[str]:
    """Re-read each declared literal from its module; report drift.

    Without this the registry becomes the next stale note. Returns a list of
    problems; empty means every declared literal still appears in its source.
    """
    import pathlib

    root = pathlib.Path(repo_root) if repo_root is not None else pathlib.Path(__file__).resolve().parents[3]
    problems: list[str] = []
    for fam in OVERLAY_FAMILIES:
        for what, rel_path, value in fam.source_literals:
            path = root / rel_path
            if not path.is_file():
                problems.append(f"{fam.name}: {rel_path} does not exist")
                continue
            text = path.read_text()
            if f"opacity={value:g}" not in text and f"opacity={value}" not in text:
                problems.append(
                    f"{fam.name}: declared {what} {value:g} no longer appears in {rel_path}"
                )
        if fam.color is not None:
            path = root / fam.owner_module.replace(".", "/")
            path = path.with_suffix(".py")
            if path.is_file():
                text = path.read_text()
                literal = ", ".join(f"{c:g}" for c in fam.color)
                if literal not in text:
                    problems.append(
                        f"{fam.name}: declared colour ({literal}) no longer appears in "
                        f"{fam.owner_module}"
                    )
    return problems
