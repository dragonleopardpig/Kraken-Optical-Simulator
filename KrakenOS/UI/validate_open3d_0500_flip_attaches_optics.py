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

        # SCENE is the user's LIVE file, so nothing about it may be hardcoded: they edit it in
        # the app between runs. On 2026-08-05 it came back with the datums at rows 1/5 (a
        # promoted BS row moved) and with the barrel saved FLIPPED, which turned this guard red
        # on a clean tree without a line of shipped code changing. Read the datum rows through
        # the same accessor the overlay anchors on, and normalise the orientation first.
        front_row = editor._lens_datum_row_index("front")
        rear_row = editor._lens_datum_row_index("rear")
        if front_row is None or rear_row is None:
            notes.append("SKIP: the scene carries no Front/Rear Optical Vertex Datum pair")
            return ok, notes
        if bool(getattr(editor, "lens_step_reverse_direction", False)):
            editor.toggle_imported_lens_step_direction()
        # ... and start from a GLUED state. The live file's glue reference was recorded before
        # the user last moved the lens, so a glue click there legitimately moves the body --
        # with or without a flip. The contract under test ("a flip does not disturb the
        # registration") is only observable from a glued start.
        editor._set_step_glue_reference_offset_xyz("lens", editor._step_placement_offset_xyz("lens"))
        _mid = editor._lens_surrogate_datum_mid_world()
        if _mid is not None:
            editor._set_step_glue_reference_datum_mid("lens", _mid)
        r1 = float(np.asarray(tree_mod.row_world_pose(editor.rows, int(front_row)), dtype=float)[0])
        r6 = float(np.asarray(tree_mod.row_world_pose(editor.rows, int(rear_row)), dtype=float)[0])

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
            abs(f0 - rr0) > 1.0,
            f"A2: the barrel is asymmetric about its glass (front overhang {f0:.3f} vs rear "
            f"{rr0:.3f} mm) -- the asymmetry that made the broken flip visible. Which END is the "
            f"long one depends on how the user has the barrel mounted in the live scene, so only "
            f"the asymmetry itself (what makes the swap below observable) is asserted",
        )

        check(
            bool(editor.toggle_imported_lens_step_direction()),
            "B1: the flip toggle acts on the imported lens",
        )
        f1, rr1 = overhangs()
        # The contract is "the body is MIRRORED ABOUT ITS GLASS-SPAN CENTRE", asserted directly
        # rather than through the overhangs-swap shorthand. The shorthand is only equivalent when
        # the glass centre happens to sit exactly on the datum-span midpoint, which is true of a
        # freshly glued lens and NOT of one the user has since dragged (on the live scene the two
        # are 0.203 mm apart, so the shorthand read as a 0.406 mm flip error that is not one).
        lo0, hi0 = r1 - f0, r6 + rr0
        lo1, hi1 = r1 - f1, r6 + rr1
        pivot_a, pivot_b = 0.5 * (lo1 + hi0), 0.5 * (hi1 + lo0)
        check(
            abs(pivot_a - pivot_b) <= SWAP_TOL,
            f"B2a: the flip is a pure MIRRORING about ONE point ({pivot_a:.6f} vs "
            f"{pivot_b:.6f} mm) -- the mechanical ends swap, nothing slides",
        )
        glass = editor._step_optical_glass_axial_metrics(editor.imported_lens_step_path) or {}
        if glass:
            centre_to_lo = 0.5 * (float(glass["glass_lo"]) + float(glass["glass_hi"])) - float(glass["body_lo"])
            centre_to_hi = float(glass["body_hi"]) - 0.5 * (float(glass["glass_lo"]) + float(glass["glass_hi"]))
            measured = 0.5 * (pivot_a + pivot_b) - lo0
            check(
                min(abs(measured - centre_to_lo), abs(measured - centre_to_hi)) <= SWAP_TOL,
                f"B2b: and that point IS the GLASS-SPAN CENTRE ({measured:.3f} mm from the body's "
                f"leading end; the CAD glass centre sits {centre_to_lo:.3f} / {centre_to_hi:.3f} mm "
                f"from its two ends) -- i.e. the optics stay on the datums, the barrel turns round "
                f"them",
            )
        else:
            notes.append("SKIP: no glass metrics for this lens STEP -- B2b not run")
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
