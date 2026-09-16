"""bugs/0794 -- when the vendor ships no STEP, build the envelope from the drawing.

Several algorithms measure against the lens BODY: the camera-clearance clamp needs something to
clear, bugs/0656's working-distance placement needs a rim to measure to, and the scene has nothing
to draw. A vendor who ships a DWG but no STEP leaves all of them blind.

The drawing states the barrel in dimension entities that carry both a value and the two points
they span, so the envelope can be DERIVED rather than modelled by eye. On the SPO
TCL4.0X-65DI-5M (1:1 mm):

    0 .. 54.900    diameter 31        54.900 + 11.600 + 75.982 = 142.482
    54.900 .. 66.500   diameter 34    -- the bands close on the body length exactly,
    66.500 .. 142.482  diameter 30       which is the check that they were read, not guessed
    coaxial port diameter 16, standing 20.5 proud, 45.56 from the rim

Two rules make that derivation trustworthy, and this guard pins both:
  * each on-axis RADIAL dimension marks one band, at its own station -- that is what a diameter
    callout means; and
  * the port's own dimensions must not cut the profile. The drawing's parenthesised reference to
    the port centre sits between the 31 and 34 callouts and, taken as a step, moved the first
    band from 54.900 to 45.561.

Display-free; skips when libredwg or the drawing is absent.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DRAWING = (PROJECT_ROOT / "attachment/Information/RD-80000/Drawings/SPO TCL4.0X-65DI-5M"
           / "TCL4.0X-65DI-5M-V2.dwg")
BUILDER = PROJECT_ROOT / "bugs" / "build_step_from_dwg_profile.py"

EXPECTED_BANDS = ((0.0, 54.900, 31.0), (54.900, 66.500, 34.0), (66.500, 142.482, 30.0))


def _load_builder():
    spec = importlib.util.spec_from_file_location("build_step_from_dwg_profile", BUILDER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_checks(verbose: bool = False) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    problems: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)
        if not condition:
            problems.append(message)

    ok(BUILDER.is_file(), "the builder is present in bugs/")
    if not BUILDER.is_file():
        return False, notes
    builder = _load_builder()

    from KrakenOS.UI.services.dwg_spec_import import dwg_available

    if not (dwg_available() and DRAWING.exists()):
        notes.append("SKIP: libredwg or the SPO drawing is not in this checkout")
        return (not problems), notes

    dims = builder.read_dimensions(DRAWING)
    ok(len(dims) >= 10, f"the drawing yields its dimension entities ({len(dims)})")
    profile = builder.profile_from_dimensions(dims)

    # ---- A: the profile is the drawing's ------------------------------------------------------
    # the drawing stores its own float noise (the 16 mm bore reads 16.00007929), so every
    # comparison here is to a hundredth of a millimetre -- the precision a drawing HAS
    ok(abs(profile["axis_y"] - 184.5) < 1e-2, f"A: axis found at y {profile['axis_y']:.3f}")
    ok(abs(profile["length"] - 142.482) < 1e-3, f"A: body length {profile['length']:.3f}")
    ok(len(profile["bands"]) == len(EXPECTED_BANDS),
       f"A: {len(profile['bands'])} bands (expected {len(EXPECTED_BANDS)})")
    for got, want in zip(profile["bands"], EXPECTED_BANDS):
        ok(abs(got[0] - want[0]) < 1e-2 and abs(got[1] - want[1]) < 1e-2
           and abs(got[2] - want[2]) < 1e-2,
           f"A: band {got[0]:.3f}..{got[1]:.3f} diameter {got[2]:g}")

    # ---- B: the bands CLOSE -- the check that they were read, not guessed ----------------------
    total = sum(end - start for start, end, _d in profile["bands"])
    ok(abs(total - profile["length"]) < 1e-4,
       f"B: the bands close on the body length ({total:.4f} vs {profile['length']:.4f})")

    # ---- C: the port is found, and did NOT cut the profile -------------------------------------
    port = profile.get("port")
    ok(port is not None, "C: the coaxial port is found")
    if port:
        ok(abs(port["diameter"] - 16.0) < 1e-2 and abs(port["stand"] - 20.5) < 1e-2,
           f"C: port diameter {port['diameter']:.3f} standing {port['stand']:.3f}")
        ok(abs(port["station"] - 45.561) < 1e-2, f"C: port at {port['station']:.3f} from the rim")
        ok(not any(abs(start - port["station"]) < 1e-2 for start, _e, _d in profile["bands"]),
           "C: the port's own reference did NOT become a step in the profile")

    # ---- D: it builds a solid of the right envelope --------------------------------------------
    import tempfile

    from KrakenOS.UI.services.machine_vision_folder_import import _step_bounds_extents

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "envelope.step"
        builder.build_step(profile, out, "guard")
        ok(out.is_file() and out.stat().st_size > 1000, "D: a STEP is written")
        extents = _step_bounds_extents(out)
        if not extents:
            ok(False, "D: the STEP has no readable bounds")
        else:
            dx, dy, dz = (round(v, 3) for v in extents)
            ok(abs(dz - 142.482) < 1e-2, f"D: axial extent {dz} = the body length")
            ok(abs(dx - 34.0) < 1e-2, f"D: transverse extent {dx} = the largest diameter")
            ok(abs(dy - (34.0 / 2.0 + 20.5 + 34.0 / 2.0)) < 1e-2,
               f"D: the port stands proud ({dy} across)")
    return (not problems), notes


def main() -> int:
    try:
        passed, notes = run_checks()
    except Exception as exc:
        passed, notes = False, [f"FAIL: {type(exc).__name__}: {exc}"]
    for note in notes:
        print(note)
    print("bugs/0794 drawing-envelope validation " + ("PASSED." if passed else "FAILED."))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
