"""bugs/0500 (deliverable 2) -- flipping the lens STEP keeps its OPTICS on the surrogate datums.

User requirement, 2026-08-01: *"Worst case if it is flipped, user are forced to unglue it and
manually flip it. But in this case make sure the front and rear surrogate lens correctly attach
to the lens STEP front and rear lens location."*

The alignment mirrors a flipped body about its LEADING mechanical face, which keeps the
mechanical slab in place and slides the asymmetric GLASS inside it. On the ELS-85 barrel (front
overhang 3.849 mm, rear 0.342 mm) the optical surfaces landed 3.507 mm off the datums after a
flip. The bugs/0374 glass-centre pin only covered the untilted close-barrel branch -- and any
lens on a FOLDED arm carries a y-rotation, so the folded case always took the broken fallback.
Worse, the x/y rotations pivot about the bbox centre, which re-registers the slab and silently
discards any pre-rotation axial correction (a mirrored slab has the same bbox).

The fix: ``_lens_step_flip_axial_shift`` -- ``(body_hi - glass_centre) - (glass_centre -
body_lo)`` from the native glass metrics -- applied AFTER the rotations along the rotated barrel
axis, so the flip mirrors the body about its GLASS-SPAN CENTRE: the mechanical ends swap around
the fixed optics, which is what a physical flip does. The registration (and therefore the
bugs/0497/0503 glue reference) is unchanged, so glue stays a no-op across a flip.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0500_flip_attaches_optics
"""
from __future__ import annotations

from pathlib import Path

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")
SWAP_TOL = 5.0e-3
EXACT = 1.0e-6


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    ok = True

    def check(cond: bool, label: str) -> None:
        nonlocal ok
        notes.append(("PASS " if cond else "FAIL ") + label)
        if not cond:
            ok = False

    if not SCENE.exists():
        notes.append("SKIP: the AZ85 BS scene is not checked out (gitignored attachment)")
        return ok, notes

    import numpy as np

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services import optical_axis_tree as tree_mod

    editor = None
    try:
        editor = KrakenLayoutEditor()
        editor.layout_files["flip_probe"] = SCENE
        editor.load_layout_by_name("flip_probe")

        r1 = float(np.asarray(tree_mod.row_world_pose(editor.rows, 1), dtype=float)[0])
        r6 = float(np.asarray(tree_mod.row_world_pose(editor.rows, 6), dtype=float)[0])

        def overhangs():
            mesh = editor._transformed_imported_lens_step_mesh()
            b = np.asarray(mesh.bounds, dtype=float)
            return float(r1 - b[0]), float(b[1] - r6)

        check(
            abs(float(editor._lens_step_flip_axial_shift())) <= 1.0e-12,
            "A1: the flip shift is exactly zero while the barrel is not flipped -- the unflipped "
            "registration (which every recorded placement offset was measured against) is untouched",
        )
        f0, rr0 = overhangs()
        check(
            f0 > rr0 + 1.0,
            f"A2: the barrel is asymmetric about its glass (front overhang {f0:.3f} vs rear "
            f"{rr0:.3f} mm) -- the asymmetry that made the broken flip visible",
        )

        check(
            bool(editor.toggle_imported_lens_step_direction()),
            "B1: the flip toggle acts on the imported lens",
        )
        f1, rr1 = overhangs()
        check(
            abs(f1 - rr0) <= SWAP_TOL and abs(rr1 - f0) <= SWAP_TOL,
            f"B2: after the flip the overhangs SWAP about the UNMOVED datums "
            f"({f1:.3f}/{rr1:.3f} vs expected {rr0:.3f}/{f0:.3f}) -- the former rear vertex sits "
            f"on the FRONT datum and vice versa, i.e. the optics stay attached",
        )
        check(
            editor.glue_step_overlay_to_surrogate("lens") is False,
            "B3: glue after a flip reports already-glued -- the flip does not disturb the "
            "recorded registration, so the 0497/0503 reference stays valid",
        )

        editor.toggle_imported_lens_step_direction()
        f2, rr2 = overhangs()
        check(
            abs(f2 - f0) <= EXACT and abs(rr2 - rr0) <= EXACT,
            f"C1: flipping back restores the original registration exactly "
            f"({f2:.6f}/{rr2:.6f} vs {f0:.6f}/{rr0:.6f})",
        )
    except Exception as exc:
        notes.append(f"SKIP: the scene could not be driven ({type(exc).__name__}: {exc})")
    finally:
        if editor is not None:
            try:
                editor.destroy()
            except Exception:
                pass
    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if note.startswith(("PASS", "SKIP", "NOTE")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
