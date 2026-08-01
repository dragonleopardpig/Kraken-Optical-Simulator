"""bugs/0497 -- "glue to surrogate" restores the placement the body was PLACED at.

``flag_20260801_195042`` -- *"glue surrogate to LED misplaced the Lens STEP."* The menu zeroed the
lens offset ([97.41, 0, -105.10] -> [0,0,0]), dropping the body at the origin, and the
``already_glued`` short-circuit then refused every retry so only Ctrl-Z recovered it. bugs/0475 had
fixed exactly this for the CAMERA; the carve-out covered one label.

Why the pose cannot simply be recomputed, measured on this scene:

    datum stations        130.635 / 185.635  -> station midpoint 158.135
    c_zero (auto-aligned) z 160.230          =  station midpoint + 2.095
    world datums          x 71.66 / 126.66   -> world midpoint   99.160   (span 55.0 in BOTH)
    correct glued centre  x 97.406           =  world midpoint  - 1.754

Same span in both frames, so the auto-aligned pose maps to world 101.255 while the correct pose is
97.406 -- 3.849 mm apart AFTER accounting for the fold. The correct pose is not what the
auto-alignment produces, because this scene's lens was placed by the machine-vision folder importer.
That 3.849 mm lives only in the stored offset, which is what the menu destroyed. So the fix records
the placement and restores it rather than deriving anything.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0497_glue_restores_the_recorded_placement
"""
from __future__ import annotations

from pathlib import Path

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")
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

    made: list = []
    try:
        def _load():
            ed = KrakenLayoutEditor()
            made.append(ed)
            ed.layout_files["glue_ref_probe"] = SCENE
            ed.load_layout_by_name("glue_ref_probe")
            return ed

        editor = _load()
        reference = editor._step_glue_reference_offset_xyz("lens")
        check(
            reference is not None,
            "A1: a saved layout's stored placement seeds the glue reference -- layouts written "
            "before this key existed still work, which includes the scene that reported the bug",
        )
        base = editor._step_body_world_center("lens")
        check(base is not None, "A2: the lens body has a readable world centre")
        base = np.asarray(base, dtype=float).reshape(3)

        editor.translate_step_overlay("lens", (25.0, 0.0, 18.0))
        moved_away = float(
            np.linalg.norm(np.asarray(editor._step_body_world_center("lens"), dtype=float).reshape(3) - base)
        )
        check(moved_away > 1.0, f"B1: the drag actually moved the body ({moved_away:.2f} mm)")
        acted = editor.glue_step_overlay_to_surrogate("lens")
        after = np.asarray(editor._step_body_world_center("lens"), dtype=float).reshape(3)
        residual = float(np.linalg.norm(after - base))
        check(
            bool(acted) and residual <= EXACT,
            f"B2: glue restores the EXACT placement (residual {residual:.6f} mm) -- not the "
            f"surrogate-derived pose, which lands 3.849 mm short on an importer-placed lens",
        )

        editor.translate_step_overlay("lens", (-11.0, 0.0, 7.0))
        editor.glue_step_overlay_to_surrogate("lens")
        again = np.asarray(editor._step_body_world_center("lens"), dtype=float).reshape(3)
        check(
            float(np.linalg.norm(again - base)) <= EXACT,
            "B3: a SECOND drag-then-glue lands identically -- the stranding is gone (the old "
            "short-circuit refused every retry once the offset had been zeroed)",
        )
        check(
            editor.glue_step_overlay_to_surrogate("lens") is False,
            "B4: gluing an already-glued lens reports no move rather than nudging it",
        )
        check(
            float(np.linalg.norm(np.asarray(editor._step_body_world_center("lens"), dtype=float).reshape(3) - base)) <= EXACT,
            "B5: ... and leaves it exactly where it was",
        )

        saved = editor._collect_layout_settings()
        persisted = (saved.get("step_glue_reference_offset_xyz") or {}).get("lens")
        check(
            persisted is not None and len(persisted) == 3,
            "C1: the reference is written to the layout settings",
        )
        reloaded = _load()
        reloaded._apply_layout_settings(saved)
        back = reloaded._step_glue_reference_offset_xyz("lens")
        check(
            back is not None and float(np.linalg.norm(np.asarray(back) - np.asarray(reference))) <= EXACT,
            "C2: ... and survives the round trip (bugs/0492 is this settings block, and the facade "
            "shadowing it fixed is exactly what ate a key here before)",
        )
    except Exception as exc:
        notes.append(f"SKIP: the scene could not be driven ({type(exc).__name__}: {exc})")
    finally:
        for ed in made:
            try:
                ed.destroy()
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
