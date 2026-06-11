"""Guard: a promoted optical solid parked OFF the beam path stays inert and does
not flip a conventional finite-conjugate layout into non-sequential mode
(bugs/0064).

Reported: with the resize feature the user promoted a beam-splitter cube, parked
it ~149 mm off the optical axis, and the on-axis rays went "weird" -- the
conjugate focus moved short of the detector with extra diverging rays. Root
cause (display-free, in `resolve_trace_intent` / `_trace_flags`): the promoted
solid fired TWO mode-flips just by existing off to the side -- `Solid_3d_stl`
(STL optical solid) and its `desp` decenter (off-axis geometry) -- flipping the
whole conventional layout to non-sequential, whose launch no longer reproduces
the finite conjugate. An off-beam solid never touches a ray, so its presence
must not change the trace.

Fix: `_trace_flags` exempts an inert promoted solid whose lateral offset clears
the system aperture by its own radius -- it no longer contributes the STL or
off-axis-geometry triggers. On-beam solids, real beam-splitters, mirrors, tilted
elements, physical sources, etc. are unaffected.

This verifies the trace-MODE DECISION only (display-free). The rendered ray
geometry is verified in-app.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_offbeam_solid_trace_mode

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class _Row:
    surface: str = "Standard"
    diameter: float = 35.0
    thickness: float = 0.0
    desp_x: float = 0.0
    desp_y: float = 0.0
    desp_z: float = 0.0
    tilt_x: float = 0.0
    tilt_y: float = 0.0
    tilt_z: float = 0.0
    advanced: dict[str, Any] = field(default_factory=dict)


def _solid_row(**kw) -> _Row:
    adv = {"Solid_3d_stl": "/tmp/cube.stl"}
    adv.update(kw.pop("advanced", {}))
    return _Row(advanced=adv, **kw)


def _conventional_layout() -> list[_Row]:
    """A plain finite-conjugate machine-vision stack: Object, lens, Image.
    No physical source / target / tilt -> resolves Sequential on its own.
    """
    return [
        _Row(surface="Object", diameter=20.0, thickness=275.0),
        _Row(surface="Standard", diameter=35.0, thickness=5.0),
        _Row(surface="Standard", diameter=35.0, thickness=120.0),
        _Row(surface="Image", diameter=23.0, thickness=0.0),
    ]


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(cond: bool, label: str) -> None:
        notes.append(("PASS " if cond else "FAIL ") + label)

    from KrakenOS.UI.trace_intent import resolve_trace_intent, _solid_is_off_beam

    # --- baseline: the conventional layout alone is sequential ---------------
    base = resolve_trace_intent(_conventional_layout())
    ok(not base.use_nonseq, "A: a plain finite-conjugate layout resolves Sequential")

    # --- the user's case: an off-beam promoted solid must stay inert ---------
    off_beam = _conventional_layout()
    off_beam.append(_solid_row(diameter=55.0, desp_y=149.0, thickness=78.0))  # the parked cube
    intent = resolve_trace_intent(off_beam)
    ok(not intent.use_nonseq,
       "B1: an off-beam promoted solid does NOT flip the layout to non-sequential")
    ok(not intent.has_optical_stl_solid,
       "B2: the off-beam solid is not counted as an STL-solid nonseq trigger")
    ok(not intent.has_nonseq_geometry,
       "B3: the off-beam solid's decenter does not count as off-axis geometry")

    # --- an ON-beam solid still goes non-sequential --------------------------
    on_beam = _conventional_layout()
    on_beam.append(_solid_row(diameter=55.0, desp_y=0.0, thickness=78.0))  # on axis
    ok(resolve_trace_intent(on_beam).use_nonseq,
       "C: an on-axis promoted solid still triggers non-sequential")

    # --- a solid GRAZING the beam edge is not exempted -----------------------
    grazing = _conventional_layout()
    # aperture radius = 17.5 (the 35 dia rows); solid radius 27.5; offset 40 ->
    # 40 - 27.5 = 12.5 < 17.5 -> still overlaps the beam -> non-sequential.
    grazing.append(_solid_row(diameter=55.0, desp_y=40.0, thickness=78.0))
    ok(resolve_trace_intent(grazing).use_nonseq,
       "D: a solid grazing the aperture edge is NOT exempted (stays non-sequential)")

    # --- a real beam-splitter is never exempted, even off-beam ---------------
    splitter = _conventional_layout()
    splitter.append(_solid_row(surface="Beam Splitter", diameter=55.0, desp_y=149.0))
    ok(resolve_trace_intent(splitter).use_nonseq,
       "E1: an off-beam BEAM SPLITTER still goes non-sequential (folds must trace)")
    splitter_adv = _conventional_layout()
    splitter_adv.append(_solid_row(diameter=55.0, desp_y=149.0, advanced={"BeamSplitter": {}}))
    ok(resolve_trace_intent(splitter_adv).use_nonseq,
       "E2: off-beam solid with a BeamSplitter coating still goes non-sequential")

    # --- other nonseq triggers are unaffected by the exemption ---------------
    tilted = _conventional_layout()
    tilted[2].tilt_y = 8.0  # a tilted optical surface (on-beam) -> nonseq
    tilted.append(_solid_row(diameter=55.0, desp_y=149.0))  # plus an off-beam solid
    ok(resolve_trace_intent(tilted).use_nonseq,
       "F: an on-beam tilted element still forces non-sequential (exemption is solid-only)")

    # --- pure-solid scene (no conventional surface) is not exempted ----------
    pure = [_solid_row(diameter=55.0, desp_y=149.0)]
    ok(resolve_trace_intent(pure).use_nonseq,
       "G: with no conventional surface to preserve, the solid is not exempted")

    # --- the helper itself ---------------------------------------------------
    ok(_solid_is_off_beam(_Row(diameter=55.0, desp_y=149.0), 17.5) is True,
       "H1: _solid_is_off_beam True when offset clears the aperture by the radius")
    ok(_solid_is_off_beam(_Row(diameter=55.0, desp_y=0.0), 17.5) is False,
       "H2: _solid_is_off_beam False for an on-axis solid")

    passed = not any(n.startswith("FAIL") for n in notes)
    if verbose:
        for n in notes:
            print(n)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("Off-beam solid trace-mode validation passed.")
        return 0
    print("Off-beam solid trace-mode validation FAILED:")
    for n in notes:
        if n.startswith("FAIL"):
            print(f"- {n}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
