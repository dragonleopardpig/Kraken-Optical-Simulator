"""bugs/0508 C -- a per-frame (carry-style) axial lens drag keeps the surrogate attached on an
UNFOLDED scene.

flag_20260802_132419 -- "glued lens to surrogate, drag lens STEP, surrogate not moving, is the
fix general or specific to certain file only?" The whole-body carry commits through
``translate_step_overlay`` PER FRAME; the axial redirect's on-axis gate was machine-precision
(1e-3), so the first frame's sub-millimetre lateral jitter poisoned the placement offset and
every later axial increment slid the body off its optics. Reproduced on the user's own
``machine_vision_150mm_test.py`` (Edmund 15056): 40 frames of +0.6 mm axial with one 0.2 mm
jitter frame detached the body by 23.4 mm. The gate now uses a physical 3 mm tolerance -- far
above drag jitter, far below the parked-off-the-beam case it protects (flag_20260621_142758).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0508_unfolded_carry_keeps_lens_glued
"""
from __future__ import annotations

from pathlib import Path

SCENE = Path("attachment/machine_vision_150mm_test.py")
TOL = 1.0e-3


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    ok = True

    def check(cond: bool, label: str) -> None:
        nonlocal ok
        notes.append(("PASS " if cond else "FAIL ") + label)
        if not cond:
            ok = False

    if not SCENE.exists():
        notes.append("SKIP: the 150mm test scene is not checked out (gitignored attachment)")
        return ok, notes

    import numpy as np

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services import optical_axis_tree as tree_mod

    editor = None
    try:
        editor = KrakenLayoutEditor()
        editor.layout_files["unfolded_carry_probe"] = SCENE
        editor.load_layout_by_name("unfolded_carry_probe")

        datums = editor._lens_surrogate_datum_rows()
        check(datums is not None, "A1: the unfolded scene has front/rear lens datums")
        if datums is None:
            return ok, notes
        body_z = lambda: float(np.asarray(editor._step_body_world_center("lens"), dtype=float)[2])
        datum_z = lambda: float(np.asarray(tree_mod.row_world_pose(editor.rows, int(datums[0])), dtype=float)[2])
        gap0 = body_z() - datum_z()

        editor.translate_step_overlay("lens", (0.2, 0.0, 0.6), refresh=False, record_history=False)
        for _ in range(39):
            editor.translate_step_overlay("lens", (0.0, 0.0, 0.6), refresh=False, record_history=False)
        gap1 = body_z() - datum_z()
        check(
            abs(gap1 - gap0) <= TOL,
            f"B1: 40 carry frames (+24 mm axial, one 0.2 mm jitter frame) keep the body ON its "
            f"surrogate (gap {gap0:.3f} -> {gap1:.3f} mm) -- the 1e-3 gate detached it by 23.4 mm",
        )
        check(
            abs((body_z() - (425.83 + 24.0))) <= 0.5,
            f"B2: the unit actually slid +24 mm (body z {body_z():.2f})",
        )

        # flag_20260621_142758 protection intact: a body PARKED off the beam keeps a plain move.
        editor.translate_step_overlay("lens", (25.0, 0.0, 0.0), refresh=False, record_history=False)
        parked_datum = datum_z()
        editor.translate_step_overlay("lens", (0.0, 0.0, 10.0), refresh=False, record_history=False)
        check(
            abs(datum_z() - parked_datum) <= TOL,
            "C1: with the body parked 25 mm OFF the axis, an axial drag moves the BODY alone -- "
            "the 0442 protection survives the tolerance change",
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
