"""Guard for bugs/0738 -- a bare "air" spacer row is not an optical surface.

Flag 20260907_112030_381, zoomed in on the sensor: "left shows focus rays, right shows defocus
rays, although they are not landed on sensor, but symmetry should applies."

om05a images two faces down two arms that are meant to be mirror images. One axis ray per face
showed them symmetric to the micron geometrically (114.907 mm each) and carrying 1.5 mm LESS glass
on arm A (17.770 vs 19.270 mm). Arm A has two bare ``air`` spacer rows between its solids that arm
B has none of; non-sequential mode meshes every row, so row 2's spacer becomes a real disc INSIDE
BS cube A, and the row-order medium bookkeeping declared the ray to be in AIR for 1.5 mm of the
cube's interior.

Now the chooser never interacts with a phantom spacer. The safety clause is that a bare AIR row is
only phantom when the medium in front of it is owned by an optical SOLID (which meshes its own exit
face); where the medium comes from a classical glass row, that bare row IS the exit face and must
keep refracting.

Checks (display-free -- surfaces are real Kos.surf objects, no VTK build):
  A  the rule on the REAL om05a rows: exactly the three bare spacers after solids are phantom,
     and the Filter's exit face and the sensor are not.
  B  the safety clause: a plano lens's flat back, and a bare row after any classical glass row,
     stay real -- skipping them would trap the ray in glass forever.
  C  anything with optical behaviour of its own is never a spacer: curvature, conic, axicon, thin
     lens, grating, annulus, mask, UDA, coating, error map, cylinder, sub-aperture, scatter, a
     designated stop (bugs/0179), a barrel wall (bugs/0623), a detector, a non-AIR glass, a body.
  D  wiring: the chooser consults the rule and skips those candidates, and the cache is cleared
     everywhere the other non-sequential caches are.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0738_phantom_spacer_surfaces
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from types import SimpleNamespace

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENE = PROJECT_ROOT / "attachment/om05a_folded_80mm.py"


def _scene_rows(path: Path) -> "list[dict]":
    src = path.read_text(encoding="utf-8")
    rows, pos = [], 0
    while True:
        i = src.find("surfaces.append({", pos)
        if i < 0:
            break
        j = src.find("})\n", i) + 2
        rows.append(ast.literal_eval(src[i + len("surfaces.append(") : j - 1]))
        pos = j
    return rows


def _surf(**kw):
    """A real surf object, so the rule is tested against the true field defaults."""
    import KrakenOS as Kos

    s = Kos.surf()
    for key, value in kw.items():
        setattr(s, key, value)
    return s


def _surf_from_scene_row(row: dict):
    """Rebuild a scene row as a surf, mirroring what build_system stamps on it."""
    advanced = dict(row.get("advanced") or {})
    solid = str(advanced.get("Solid_3d_stl", "None") or "None")
    kind = str(row.get("surface") or "Standard")
    surface_type = 3.0 if solid not in ("None", "") else (2.0 if kind == "Thin Lens" else 0.0)
    s = _surf(
        Name=str(row.get("name") or ""),
        Rc=float(row.get("rc") or 0.0),
        k=float(row.get("k") or 0.0),
        Axicon=float(row.get("axicon") or 0.0),
        Diff_Ord=float(row.get("diff_ord") or 0.0),
        Grating_D=float(row.get("grating_d") or 0.0),
        Thickness=float(row.get("thickness") or 0.0),
        Diameter=float(row.get("diameter") or 0.0),
        InDiameter=float(row.get("in_diameter") or 0.0),
        Glass=str(row.get("glass") or "AIR"),
        UDA=str(row.get("uda") or "None"),
        Surface_type=surface_type,
        Solid_3d_stl=solid,
        Drawing=float(row.get("drawing") or 0.0),
    )
    if advanced.get("OpticalSolidFaces"):
        s.OpticalSolidFaces = advanced["OpticalSolidFaces"]
    if kind == "Aperture":
        s.IsApertureStop = True
    # bugs/0623 stamps the surrogate datums as barrel walls at build time -- same test the
    # builder uses (layout_editor: "datum" plus "front" or "rear")
    lowered = str(row.get("name") or "").lower()
    if "datum" in lowered and ("front" in lowered or "rear" in lowered):
        s.HardApertureWall = True
    return s


def _rule(sdt):
    """Bind the real rule to a stub carrying only what it reads."""
    from KrakenOS.KrakenSys import system as KrakenSystem

    stub = SimpleNamespace(SDT=list(sdt), n=len(sdt), _ns_phantom_spacer_cache=None)
    for name in ("_ns_surface_has_solid_body", "_ns_surface_is_bare_spacer",
                 "_ns_phantom_spacer_surfaces"):
        setattr(stub, name, getattr(KrakenSystem, name).__get__(stub, SimpleNamespace))
    stub._ns_surface_field_active = KrakenSystem._ns_surface_field_active   # a staticmethod
    return stub


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    # ---- A: the real om05a rows ----------------------------------------------------------------
    rows = _scene_rows(SCENE)
    ok(len(rows) >= 24, f"A0: the om05a scene parsed ({len(rows)} rows)")
    names = [str(r.get("name") or "") for r in rows]
    stub = _rule([_surf_from_scene_row(r) for r in rows])
    phantom = set(stub._ns_phantom_spacer_surfaces())
    # bugs/0745 split row 7, so pin this by NAME rather than by index -- the scene gains and loses
    # scaffolding rows over time and a hardcoded index set only re-breaks.
    expected = {
        i for i, r in enumerate(rows)
        if str(r.get("name") or "") in ("air", "to lens (unfolded RA mirror 1)", "prism exit gap (air)")
    }
    ok(
        phantom == expected and len(phantom) >= 3,
        f"A1: exactly the bare undrawn spacers after solids are phantom -- "
        f"{sorted((k, names[k]) for k in phantom)}",
    )
    # by NAME (bugs/0745 split row 7, so the Filter's index moves)
    filt = next(i for i, r in enumerate(rows) if str(r.get("name") or "").startswith("Filter"))
    ok(
        (filt + 1) not in phantom and str(rows[filt].get("glass")).upper() == "N-BK7",
        f"A2: the row after the classical N-BK7 Filter (row {filt}) stays REAL -- it is that "
        f"element's exit face, and skipping it would trap the ray in glass",
    )
    # the image row must be safe on its OWN guard, not merely because it happens to be drawn
    undrawn_image = _rule([
        _surf(Name="object"),
        _surf(Name="solid", Surface_type=3.0, Solid_3d_stl="/tmp/s.stl"),
        _surf(Name="image", Drawing=0.0),
    ])
    ok(
        23 not in phantom
        and undrawn_image._ns_surface_is_bare_spacer(2)
        and 2 not in undrawn_image._ns_phantom_spacer_surfaces(),
        "A3: the image/target row is never phantom -- an UNDRAWN one that reads as a bare "
        "spacer in every other respect is still kept, so the guard is its own, not the "
        "drawing flag's",
    )
    ok(
        0 not in phantom,
        "A4: the object row is never phantom",
    )
    # the asymmetry the bug is about: arm A carries spacers between its solids, arm B none
    arm_a = [i for i in range(1, 6) if names[i] == "air"]
    arm_b = [i for i in range(16, 19) if names[i] == "air"]
    ok(
        arm_a == [2, 4] and arm_b == [],
        f"A5: the scene really is lopsided -- arm A rows {arm_a} are bare spacers, arm B has none",
    )

    # a SECOND scene family: a promoted STEP solid is written as the solid row plus a
    # "-> next gap (AIR)" row, and the surrogate lens block's datums are barrel walls
    gn = PROJECT_ROOT / "attachment/machine_vision_150mm_GN.py"
    gn_rows = _scene_rows(gn)
    gn_names = [str(r.get("name") or "") for r in gn_rows]
    gn_stub = _rule([_surf_from_scene_row(r) for r in gn_rows])
    gn_phantom = set(gn_stub._ns_phantom_spacer_surfaces())
    ok(
        gn_phantom == set() and float(gn_rows[2].get("drawing") or 0.0) != 0.0,
        f"A6: on a promoted-STEP scene the solid's AIR GAP row is DRAWN, so it is kept -- rays "
        f"must meet every drawn row (penta 185/186); nothing is skipped there "
        f"({sorted(gn_phantom)})",
    )
    ok(
        3 not in gn_phantom and "Datum" in gn_names[3],
        "A7: the surrogate's Lens Front Datum is a barrel wall (bugs/0623), never a spacer",
    )

    # ---- B: the safety clause ----------------------------------------------------------------------
    plano = _rule([
        _surf(Name="object"),
        _surf(Name="plano front", Rc=100.0, Glass="BK7"),
        _surf(Name="plano back", Drawing=0.0),   # flat, AIR, no body -- the EXIT face
        _surf(Name="image"),
    ])
    ok(
        plano._ns_surface_is_bare_spacer(2) and 2 not in plano._ns_phantom_spacer_surfaces(),
        "B1: a plano lens's flat back reads as bare but is NOT phantom -- the medium in front of "
        "it comes from a classical glass row, so it is that lens's exit face",
    )
    solid_lit = {"version": 1, "faces": []}
    run = _rule([
        _surf(Name="object"),
        _surf(Name="solid cube", Glass="BK7", Surface_type=3.0, Solid_3d_stl="/tmp/cube.stl"),
        _surf(Name="air", Drawing=0.0),
        _surf(Name="air", Drawing=0.0),
        _surf(Name="solid mirror", Surface_type=3.0, Solid_3d_stl="/tmp/mirror.stl"),
        _surf(Name="image"),
    ])
    ok(
        set(run._ns_phantom_spacer_surfaces()) == {2, 3},
        f"B2: a RUN of spacers walks back past itself to the owning solid "
        f"(got {sorted(run._ns_phantom_spacer_surfaces())})",
    )
    faces_only = _rule([
        _surf(Name="object"),
        _surf(Name="solid by faces", Surface_type=3.0, OpticalSolidFaces=solid_lit),
        _surf(Name="air", Drawing=0.0),
        _surf(Name="image"),
    ])
    ok(
        set(faces_only._ns_phantom_spacer_surfaces()) == {2},
        "B3: a solid identified by its OpticalSolidFaces owns its exit face too",
    )

    # ---- C: anything with optical behaviour is never a spacer -------------------------------------
    cases = {
        "curvature": dict(Rc=50.0),
        "conic": dict(k=-1.0),
        "axicon": dict(Axicon=0.5),
        "thin lens": dict(Thin_Lens=100.0),
        "grating": dict(Diff_Ord=1.0),
        "annulus": dict(InDiameter=4.0),
        "mask": dict(Mask_Type=1.0),
        "UDA": dict(UDA="rect.txt"),
        "coating": dict(Coating=[[1.38], [0.25], [], []]),
        "metal coating": dict(CoatingMet=1),
        "error map": dict(Error_map=[[0.0, 0.0, 1.0e-4]]),
        "cylinder": dict(Cylinder_Rxy_Ratio=2.0),
        "sub-aperture": dict(SubAperture=[0, 1, 0]),
        "shift": dict(ShiftX=1.0),
        "aspheric": dict(AspherData=np.concatenate(([1.0e-6], np.zeros(199)))),
        "glass": dict(Glass="BK7"),
        "special surface": dict(Surface_type=2.0),
        "body": dict(Solid_3d_stl="/tmp/x.stl"),
        "aperture stop": dict(IsApertureStop=True),
        "barrel wall": dict(HardApertureWall=True),
        "detector": dict(IsDetector=True),
        "diffuse scatter": dict(DiffuseScatter={"model": "lambertian"}),
    }
    for label, kw in cases.items():
        probe = _rule([
            _surf(Name="object"),
            _surf(Name="solid", Surface_type=3.0, Solid_3d_stl="/tmp/s.stl"),
            _surf(Name=label, Drawing=0.0, **kw),
            _surf(Name="image"),
        ])
        ok(
            2 not in probe._ns_phantom_spacer_surfaces(),
            f"C[{label}]: a row carrying {label} is never skipped",
        )
    plain = _rule([
        _surf(Name="object"),
        _surf(Name="solid", Surface_type=3.0, Solid_3d_stl="/tmp/s.stl"),
        _surf(Name="air", Drawing=0.0),
        _surf(Name="image"),
    ])
    ok(
        2 in plain._ns_phantom_spacer_surfaces(),
        "C[control]: the same row with none of those IS skipped, so the checks above are not "
        "passing for the wrong reason",
    )
    drawn = _rule([
        _surf(Name="object"),
        _surf(Name="solid", Surface_type=3.0, Solid_3d_stl="/tmp/s.stl"),
        _surf(Name="air", Drawing=1.0),
        _surf(Name="image"),
    ])
    ok(
        2 not in drawn._ns_phantom_spacer_surfaces(),
        "C[drawn]: the SAME inert row is kept when the scene draws it -- the display contract "
        "is that rays meet every drawn row (penta 185/186), and a drawn row marks a real "
        "station met in air, where keeping it changes nothing",
    )

    # ---- D: wiring ---------------------------------------------------------------------------------
    from KrakenOS import KrakenSys

    chooser = inspect.getsource(KrakenSys.system._system__NonSequentialChooser)
    ok(
        "phantom = self._ns_phantom_spacer_surfaces()" in chooser
        and "int(self.GlassOnSide[k]) in phantom" in chooser,
        "D1: the chooser consults the rule, keyed by the surface the mesh block belongs to",
    )
    ok(
        "if skip_this:" in chooser and "99999999999999.9" in chooser,
        "D2: a phantom candidate is pushed out of reach rather than dropped, so the chooser's "
        "index arithmetic is untouched",
    )
    src = Path(KrakenSys.__file__).read_text(encoding="utf-8")
    ok(
        src.count("self._ns_phantom_spacer_cache = None") == src.count("self._ns_intersection_policy_cache = None"),
        "D3: the cache is cleared everywhere the other non-sequential caches are, so a rebuilt "
        "system re-derives it",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0738 phantom-spacer validation PASSED")
        return 0
    print("0738 phantom-spacer validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
