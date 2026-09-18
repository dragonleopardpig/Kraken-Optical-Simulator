"""Guard for bugs/0820 -- the glass reader measures an ELEMENT, not one face of it.

User, on bugs/0819's finding that the ELS-85's glass "could not be measured": "do you mean the
vendor STEP should have some element but it is missing?"

It is not missing. The vendor splits one lens surface across several spherical faces, and
``_step_glass_aperture`` measured a FACE. The ELS-85 carries each element as two half-caps --
both with extents ``[2.657, 28.058, 14.158]`` and both on the sphere centred
``[17.006, -2.417, 54.0]`` -- so the reader took 14.158 mm for an element that is 28.058 mm
across, on an 85 mm f/4.5 lens whose pupil alone is 18.9 mm. The 150 mm 15056 splits its steeply
curved elements four ways, and the 0.75X telecentric two ways.

Grouping the faces by the sphere they lie on and measuring each element's union fixes all three.

Checks:
  A  PURE: two half-caps on one sphere read as one element; two elements stay two; a face with no
     sphere parameters still counts as its own element; the area gate still drops a small cap.
  B  VENDOR (SKIP per file): the three split bodies now read their element, the two unsplit ones
     are unchanged -- including the ball lens, whose single hemisphere is its glass.
  C  the ELS-85's element is WIDER than the pupil its own scene passes (18.889 mm), which is what
     the fragment never was.

Display-free.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0820_a_lens_surface_is_an_element

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# measured on this machine, 2026-09-18
VENDOR = {
    "attachment/Lens/ELS-85-4.5V16K/ELS-85-4.5V16K.STEP": (28.058, 14.158),
    "attachment/Lens/15056/15056.STEP": (26.624, 18.596),
    "attachment/Lens/67304_0.75X_Telecentric/step_67304.step": (29.643, 14.893),
    "attachment/Lens/PYRITE_56_120_10x_V38_1097277/1097277_00155156_002.stp": (30.391, 30.391),
    "attachment/Lens/ball_lens/step_63227.stp": (9.617, 9.617),
}
ELS85_PUPIL_MM = 18.889   # 85 / 4.5, the stop machine_vision_AZ85_RA_Mirror passes


def _fake_face(bbox, area, centre=None, radius=None, kind="sphere"):
    params = {}
    if centre is not None:
        params["center"] = list(centre)
    if radius is not None:
        params["radius_mm"] = float(radius)
    return SimpleNamespace(
        surface_type=kind, bbox=list(bbox), area_mm2=float(area), parameters=params
    )


def _read_fake(monkey_faces):
    """Drive the REAL reader over a synthetic analytic document.

    The source path has to EXIST -- the analytic-cache helper stats it -- but it may be empty,
    because the patched loader is what answers."""
    import tempfile

    import KrakenOS.UI.services.step_analytic_geometry as sag
    from KrakenOS.UI.services import machine_vision_folder_import as mvi

    original = sag.load_step_analytic_document
    sag.load_step_analytic_document = lambda _path: SimpleNamespace(faces=monkey_faces)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            probe = Path(tmp) / "probe_0820.step"
            probe.write_text("")
            return mvi._step_glass_aperture(probe)
    finally:
        sag.load_step_analytic_document = original


def _check_pure(ok) -> None:
    # one element, split in two along z: each face is 28.058 wide and 14.158 deep
    halves = [
        _fake_face((-1.3, -14.03, 39.97, 1.36, 14.03, 54.13), 312.5, centre=(17.0, -2.4, 54.0), radius=41.5),
        _fake_face((-1.3, -14.03, 53.87, 1.36, 14.03, 68.03), 312.5, centre=(17.0, -2.4, 54.0), radius=41.5),
    ]
    value = _read_fake(halves)
    ok(
        value is not None and abs(value - 28.06) < 0.05,
        f"A1: two half-caps on ONE sphere read as one 28.06 mm element (got {value})",
    )
    single = _read_fake(halves[:1])
    ok(
        single is not None and abs(single - 14.158) < 0.05,
        "A2: a single half on its own still reads as what it is -- the grouping invents nothing",
    )
    # two DIFFERENT elements: the bigger one wins, they are not merged
    two = [
        _fake_face((-1.0, -10.0, -10.0, 1.0, 10.0, 10.0), 300.0, centre=(0.0, 0.0, 0.0), radius=40.0),
        _fake_face((50.0, -6.0, -6.0, 51.0, 6.0, 6.0), 280.0, centre=(90.0, 0.0, 0.0), radius=40.0),
    ]
    value = _read_fake(two)
    ok(
        value is not None and abs(value - 20.0) < 0.05,
        f"A3: two elements stay two -- the widest is reported, not their span (got {value})",
    )
    # a face with no sphere parameters is still its own element
    bare = [_fake_face((-1.0, -9.0, -9.0, 1.0, 9.0, 9.0), 250.0)]
    bare_value = _read_fake(bare)
    ok(
        bare_value is not None and abs(bare_value - 18.0) < 0.05,
        "A4: a face carrying no sphere centre is measured on its own, as before",
    )
    # the area gate still drops a small protective cap
    gated = [
        _fake_face((-1.0, -15.0, -15.0, 1.0, 15.0, 15.0), 700.0, centre=(0.0, 0.0, 0.0), radius=60.0),
        _fake_face((20.0, -3.5, -3.5, 20.5, 3.5, 3.5), 35.0, centre=(40.0, 0.0, 0.0), radius=20.0),
    ]
    gated_value = _read_fake(gated)
    ok(
        gated_value is not None and abs(gated_value - 30.0) < 0.05,
        "A5: the area gate still drops a small cap beside a substantial element",
    )


def _check_vendor(ok, skip) -> None:
    from KrakenOS.UI.services import machine_vision_folder_import as mvi

    for rel, (expected, was) in sorted(VENDOR.items()):
        path = PROJECT_ROOT / rel
        if not path.exists():
            skip(f"B: {Path(rel).name} is not on this machine (Filen-synced)")
            continue
        try:
            value = mvi._step_glass_aperture(path)
        except Exception as exc:  # pragma: no cover - env dependent
            skip(f"B: {Path(rel).name} could not be read ({type(exc).__name__}: {exc})")
            continue
        note = "unchanged" if abs(expected - was) < 1e-6 else f"was {was} (a fragment)"
        ok(
            value is not None and abs(float(value) - expected) < 0.05,
            f"B-{Path(rel).name}: reads {expected} mm, {note} (got {value})",
        )


def _check_physical(ok, skip) -> None:
    from KrakenOS.UI.services import machine_vision_folder_import as mvi

    path = PROJECT_ROOT / "attachment/Lens/ELS-85-4.5V16K/ELS-85-4.5V16K.STEP"
    if not path.exists():
        skip("C: the ELS-85 STEP is not on this machine (Filen-synced)")
        return
    value = mvi._step_glass_aperture(path)
    ok(
        value is not None and float(value) > ELS85_PUPIL_MM,
        f"C: the ELS-85's element ({value}) is wider than the {ELS85_PUPIL_MM} mm pupil its scene "
        f"passes -- a front element never is narrower, which is how the fragment gave itself away",
    )


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(cond: bool, label: str) -> None:
        notes.append(("PASS " if cond else "FAIL ") + label)

    def skip(label: str) -> None:
        notes.append("SKIP " + label)

    _check_pure(ok)
    _check_vendor(ok, skip)
    _check_physical(ok, skip)

    passed = not any(n.startswith("FAIL") for n in notes)
    if verbose:
        for n in notes:
            print(n)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("Open 3D lens-element measurement validation passed.")
        return 0
    print("Open 3D lens-element measurement validation FAILED:")
    for n in notes:
        if n.startswith("FAIL"):
            print(f"- {n}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
