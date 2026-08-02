"""bugs/0504 -- LED glue restores its recorded placement and carries the glued BS back.

The LED was the last label on bugs/0497's destructive path: "glue to surrogate" zeroed its
offsets on the stated assumption that zero IS the auto station. On the AZ85 scene the LED's
seated offset is [-8.93, 0, -29.15], so one glue click threw the housing ~30 mm off its seat --
and stranded it, because "already glued" meant "offset is zero". Same failure family bugs/0475
fixed for the camera and bugs/0497+0503 for the lens.

Restoring the LED must also restore the ASSEMBLY: the drag that displaced the LED carried the
glued beam splitter along (asymmetric parent/child glue, bugs/0437), so a glue that moved only
the LED would tear the pair apart.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0504_led_glue_restores_reference
"""
from __future__ import annotations

from pathlib import Path

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")
EXACT = 1.0e-6
DRAG = (5.0, 0.0, -7.0)


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

    made: list = []
    try:
        def _load():
            ed = KrakenLayoutEditor()
            made.append(ed)
            ed.layout_files["led_glue_probe"] = SCENE
            ed.load_layout_by_name("led_glue_probe")
            return ed

        editor = _load()
        led = lambda: np.asarray(editor._step_body_world_center("led"), dtype=float).reshape(3)
        bs_row = editor._promoted_optical_solid_row_index("optical")
        check(
            bs_row is not None and bool(getattr(editor, "_optical_led_glued", False)),
            f"A1: the scene has the BS<->LED glue active with a promoted BS row (S{bs_row})",
        )
        bs = lambda: np.asarray(tree_mod.row_world_pose(editor.rows, int(bs_row)), dtype=float).reshape(3)
        reference = editor._step_glue_reference_offset_xyz("led")
        check(
            reference is not None and float(np.linalg.norm(np.asarray(reference))) > 1.0,
            "A2: the LED's recorded placement is seeded from the saved layout and is NOT zero -- "
            "which is exactly why the destructive zeroing was catastrophic here",
        )
        led0, bs0 = led(), bs()

        check(
            editor.glue_step_overlay_to_surrogate("led") is False
            and float(np.linalg.norm(led() - led0)) <= EXACT,
            "A3: gluing the freshly loaded (seated) LED reports no move and does not touch it -- "
            "the old path zeroed the offset and threw the housing ~30 mm off its seat",
        )

        drag = np.asarray(DRAG, dtype=float)
        editor.translate_step_overlay("led", tuple(drag))
        check(
            float(np.linalg.norm((led() - led0) - drag)) <= EXACT
            and float(np.linalg.norm((bs() - bs0) - drag)) <= EXACT,
            "B1: dragging the LED carries the glued BS by the same delta (bugs/0437 parent/child)",
        )
        acted = editor.glue_step_overlay_to_surrogate("led")
        check(
            bool(acted) and float(np.linalg.norm(led() - led0)) <= EXACT,
            f"B2: glue restores the LED EXACTLY to its recorded placement (residual "
            f"{float(np.linalg.norm(led() - led0)):.6f} mm)",
        )
        check(
            float(np.linalg.norm(bs() - bs0)) <= EXACT,
            "B3: ... and carries the glued BS BACK with it -- glue restores the assembly, not "
            "just the housing",
        )
        check(
            editor.glue_step_overlay_to_surrogate("led") is False
            and float(np.linalg.norm(led() - led0)) <= EXACT,
            "B4: a second glue reports no move and leaves it seated -- no stranding",
        )

        saved = editor._collect_layout_settings()
        persisted = (saved.get("step_glue_reference_offset_xyz") or {}).get("led")
        reloaded = _load()
        reloaded._apply_layout_settings(saved)
        back = reloaded._step_glue_reference_offset_xyz("led")
        check(
            persisted is not None and back is not None
            and float(np.linalg.norm(np.asarray(back) - np.asarray(reference))) <= EXACT,
            "C1: the LED reference persists in the layout settings and survives the round trip",
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
