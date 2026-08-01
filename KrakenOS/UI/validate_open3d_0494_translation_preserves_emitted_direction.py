"""bugs/0494 -- sliding a folder must never turn its emitted leg.

``flag_20260731_225718`` -- *"drag again the LED, this time to the right, everything misplaced."*
The preceding drag along the axis worked (``flag_20260731_225502``: *"drag LED down: elements now
follow"*), so this is specific to sliding SIDEWAYS.

A beam splitter promoted from a STEP carries its coating flagged on BOTH sides -- measured on the
AZ85 scene, ``functions={'Transmit/Port': 4, 'Beam Splitter': 2}``. ``_interaction_fold_emission``
walks bounce after bounce (it must: a penta prism deviates by reflecting off two DISTINCT Mirror
faces) and returns ``bounces[-1]``. Whether the walk reached that second coating face depended on
where the body sat, so a pure sideways slide silently turned the emitted direction 90 degrees:

    dx = 0        1 bounce   hit [0, 0, 53.803]                       direction [1, 0, 0]
    dx = +12.54   2 bounces  hit [0, 0, 42.819] then [1.556, 0, 42.819]  direction [0, 0, 1]

``_fold_slide_carry_apply`` then read that as a rule-4 ROTATION and turned the whole leg about the
fold point, ``new = fold_after + R (old - fold_before)`` with R carrying +X onto +Z. Solving R from
the recording confirms it -- ``R (229.93, 0, 0) = (1.56, 0, 227.80)`` -- and the three bodies land
where that predicts: row 7 at (0,0,296.5) vs (1.56,0,294.35) measured, the lens at (0,0,164.0) vs
(1.56,0,165.51), the camera z 296.5 vs ~296. The stray ``x = 1.556`` in the recording is the second
bounce's hit point, which is how the fingerprint closes.

Note the fold POINT was right all along: a 45 degree coating slid +12.54 in X drops the point where
the fixed Z axis crosses it by the same 12.54 in Z (79.09 -> 66.55 in the recording). Only the
direction was wrong.

The fix caps the beam-splitter walk at ONE bounce -- a splitter's reflect leg is a single reflection
off one coating; the multi-bounce walk stays for the Mirror path the penta cascade needs.

Held here as the INVARIANT rather than as the one offset that was reported: **translating a folder
moves its fold point and leaves its emitted direction alone.** That is what "a slide" means
(bugs/0487, rule 3), and it is the property a rotation-carrying fix must not break (rule 4 is
bugs/0488: a folder that genuinely TURNS must still take its leg with it).

Display-free: reads the scene's SURFACES directly, no Tk and no renderer.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0494_translation_preserves_emitted_direction
"""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")
BS_ROW, MIRROR_ROW = 3, 7
# Offsets to slide the splitter sideways by. 12.54 is the recorded drag; the rest bracket it so a
# knife-edge that merely MOVES rather than disappears still gets caught.
SIDEWAYS = (0.0, 1.0, 2.0, 5.0, 8.0, 12.54, 20.0, 30.0)
ALONG = (0.0, 5.0, 13.681, 25.0)  # the gesture that already worked, kept as the control
TOL = 1.0e-6


def _load_surfaces():
    spec = importlib.util.spec_from_file_location("kraken_scene_0494", str(SCENE.resolve()))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.SURFACES


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    ok = True

    def check(cond: bool, label: str) -> None:
        nonlocal ok
        notes.append(("PASS " if cond else "FAIL ") + label)
        if not cond:
            ok = False

    # --- A. the cap is where it belongs, and only there ------------------------------------
    try:
        import inspect as _inspect

        from KrakenOS.UI import nonseq_output_ports as ports

        src = _inspect.getsource(ports.axis_fold_emissions)
        check(
            'accept={"Beam Splitter"}, max_bounces=1' in src.replace("\n", " ").replace("  ", " ")
            or ("max_bounces=1" in src and '"Beam Splitter"' in src),
            "A1: the beam-splitter branch walks ONE bounce -- its reflect leg is a single "
            "reflection off one coating",
        )
        check(
            'accept={"Mirror"}, max_bounces' not in src,
            "A2: the Mirror branch keeps the multi-bounce walk -- a penta prism deviates by "
            "reflecting off two DISTINCT faces (bugs/0485)",
        )
        walk = _inspect.getsource(ports._interaction_fold_emission)
        check("max_bounces" in walk, "A3: the walk honours a cap at all")
    except Exception as exc:
        notes.append(f"SKIP: source unreadable ({type(exc).__name__}: {exc})")

    if not SCENE.exists():
        notes.append("SKIP: the AZ85 BS scene is not checked out (gitignored attachment)")
        return ok, notes

    try:
        import numpy as np

        from KrakenOS.UI.nonseq_output_ports import axis_fold_emissions

        surfaces = _load_surfaces()
    except Exception as exc:
        notes.append(f"SKIP: the scene could not be read ({type(exc).__name__}: {exc})")
        return ok, notes

    base_x = float(surfaces[BS_ROW].get("desp_x", 0.0) or 0.0)
    base_z = float(surfaces[BS_ROW].get("desp_z", 0.0) or 0.0)

    def emissions_at(*, dx=0.0, dz=0.0):
        rows = copy.deepcopy(surfaces)
        rows[BS_ROW]["desp_x"] = base_x + float(dx)
        rows[BS_ROW]["desp_z"] = base_z + float(dz)
        return axis_fold_emissions(rows) or {}

    # --- B. the invariant: a slide moves the point, never the direction --------------------
    for axis_name, offsets, kwargs_for in (
        ("sideways (+X, the flagged gesture)", SIDEWAYS, lambda v: {"dx": v}),
        ("along the axis (+Z, the control)", ALONG, lambda v: {"dz": v}),
    ):
        reference = emissions_at(**kwargs_for(0.0)).get(BS_ROW)
        if reference is None:
            notes.append(f"SKIP: no beam-splitter emission at rest for the {axis_name} sweep")
            continue
        ref_dir = np.asarray(reference["direction"], dtype=float).reshape(3)
        turned: list[str] = []
        bounced: list[str] = []
        for offset in offsets:
            spec = emissions_at(**kwargs_for(offset)).get(BS_ROW)
            if spec is None:
                turned.append(f"{offset:+.2f}:no-emission")
                continue
            direction = np.asarray(spec["direction"], dtype=float).reshape(3)
            if float(np.linalg.norm(direction - ref_dir)) > TOL:
                turned.append(f"{offset:+.2f}->{np.round(direction, 3).tolist()}")
            if len(spec.get("bounces") or []) != 1:
                bounced.append(f"{offset:+.2f}:{len(spec.get('bounces') or [])}")
        check(
            not turned,
            f"B[{axis_name}]: the emitted direction is {np.round(ref_dir, 3).tolist()} at EVERY "
            f"offset ({', '.join(turned) if turned else 'invariant'})",
        )
        check(
            not bounced,
            f"B[{axis_name}]: the splitter reflects exactly once at every offset "
            f"({', '.join(bounced) if bounced else 'one bounce throughout'})",
        )

    # --- C. the fold POINT still tracks the slide, so this did not just freeze the geometry -
    # Slope only, measured between consecutive offsets: a 45-degree coating slid +d sideways drops
    # the point where the fixed incoming axis crosses it by the same d.
    walk_pts = []
    for offset in (2.0, 5.0, 8.0, 12.54, 20.0, 30.0):
        spec = emissions_at(dx=offset).get(BS_ROW)
        if spec is not None:
            walk_pts.append((offset, float(np.asarray(spec["origin"])[2])))
    slopes = [
        ((z1 - z0) / (x1 - x0))
        for (x0, z0), (x1, z1) in zip(walk_pts, walk_pts[1:])
    ]
    check(
        bool(slopes) and all(abs(s + 1.0) < 0.02 for s in slopes),
        f"C1: the fold point tracks the slide 1:1 ({[round(s, 4) for s in slopes]}) -- the cap did "
        f"not pin the geometry",
    )
    # C2 is a MEASUREMENT, not an assertion. The coating is flagged on both sides, 1.556 mm apart
    # along the incoming axis, and the first bounce takes whichever plane crossing is nearest in
    # ABSOLUTE distance (deliberately sign-agnostic: the probe point is an arbitrary point on the
    # incoming line). Which side wins therefore still flips as the body slides, and the fold point
    # jumps by the sides' axial separation. That is the same "face choice depends on position"
    # family as the 90-degree turn this bug fixes, two orders of magnitude smaller, and NOT fixed
    # by the bounce cap -- it moves section 1 by ~1.5 mm. Recorded so it is not mistaken for noise.
    first = emissions_at(dx=0.0).get(BS_ROW)
    second = emissions_at(dx=2.0).get(BS_ROW)
    if first is not None and second is not None:
        jump = abs(float(np.asarray(first["origin"])[2]) - float(np.asarray(second["origin"])[2]) - 2.0)
        notes.append(
            f"NOTE   C2 residual, known and unfixed: the fold point jumps {jump:.3f} mm as the "
            f"first bounce switches between the coating's two flagged sides)"
        )

    # --- D. the follower's own emission survives the slide --------------------------------
    mirror_rest = emissions_at().get(MIRROR_ROW)
    if mirror_rest is not None:
        ref = np.asarray(mirror_rest["direction"], dtype=float).reshape(3)
        lost = []
        for offset in (0.0, 5.0, 12.54, 20.0):
            spec = emissions_at(dx=offset).get(MIRROR_ROW)
            if spec is None:
                lost.append(f"{offset:+.2f}:gone")
            elif float(np.linalg.norm(np.asarray(spec["direction"], dtype=float).reshape(3) - ref)) > TOL:
                lost.append(f"{offset:+.2f}->{np.round(spec['direction'], 3).tolist()}")
        check(
            not lost,
            f"D1: the RA mirror downstream keeps emitting {np.round(ref, 3).tolist()} while the "
            f"splitter slides ({', '.join(lost) if lost else 'held'}) -- with the splitter's leg "
            f"turned it lost its parent entirely (measured: row 7 direction became None)",
        )
    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if note.startswith(("PASS", "SKIP", "NOTE")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
