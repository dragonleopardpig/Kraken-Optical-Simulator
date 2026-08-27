"""Guard for bugs/0656 -- a FIXED-MAGNIFICATION (telecentric) lens mounts; it is never
solved into the camera, and the FOV dialog is never asked for a field that is not a
choice.

flag_20260827_140507: "this 0.75X telecentric lens supposed to get FOV 11.7x8.8. I
think the FOV pop up dialog should have option to let user to somehow no need to input
FOV for this kind of fixed magnificaiton lens. Anyway, I entered the FOV after swapped
lens pop up, the lens crash inside the camera, it should directly mount to the camera."

The mount law: a C-mount telecentric is fully determined -- object at the vendor WD,
BOTH principals coincident f(1+1/m)-WD behind the rim (the bugs/0653 EFL derivation is
exactly the coincident-principal identity), sensor at the mount flange FFD behind the
housing rear. The old refit preserved the builder's ppp, leaving the rear principal
elsewhere; the FOV solve then legally focused the sensor INSIDE the barrel's mount
overhang. And two thin groups have HH' = -f d^2/(f1 f2) -- exactly zero is degenerate,
so `solve_two_thin_groups` CANNOT land it (its silent best-effort regressed the WD
mismatch to 15.3): the fixed-conjugate refit CONSTRUCTS the honest shape directly
(full power in group 2 at the principal station, group 1 a near-flat f1=1e5 window)
and outcome-checks ppa afterwards.

Checks:
  A  IMPORT (skip-if-absent, Tk/Xvfb): the #67-304 library layout lands the full law
     -- WD mismatch ~0, HH' ~0, image at rim+L+FFD, object leg = WD.
  B  SWAP (the flagged flow, skip-if-absent): Pyrite90 -> #67-304: object->rim = 110,
     the LENS BODY REAR meets the CAMERA FRONT (gap in [-0.5, 5] mm -- the C-mount
     thread screws INSIDE the camera; the flag showed the barrel ~30 mm THROUGH it),
     the post-swap prompt STATES the fixed field instead of asking, a foreign FOV
     refuses honestly and the lens's own field confirms without moving anything.
  C  WIRING: the fov_solve gate, the swap WD placement, and the prompt branch exist.

Run:  xvfb-run -a .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0656_fixed_conjugate_mount_law
"""

from __future__ import annotations

import inspect
from pathlib import Path
from types import SimpleNamespace

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENE = PROJECT_ROOT / "attachment/machine_vision_Pyrite90_0.3X.py"
LENS_FOLDER = PROJECT_ROOT / "attachment/Lens/67304_0.75X_Telecentric"


def _check_import(ok, notes) -> None:
    if not LENS_FOLDER.exists():
        notes.append("SKIP: A: the 67304 folder is not in this checkout")
        return
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = None
    try:
        editor = KrakenLayoutEditor()
        editor._prompt_for_missing_cad_assets = lambda: None
        editor.import_machine_vision_lens_from_folder(str(LENS_FOLDER))
        reg = editor._lens_datasheet_wd_registration()
        if reg is None:
            ok(False, "A0: no registration after the telecentric import")
            return
        ok(
            abs(float(reg["mismatch"])) <= 0.05,
            f"A1: the WD law holds after import (mismatch {reg['mismatch']:+.3f} mm)",
        )
        ok(
            reg.get("mount_flange") == 17.526 and reg.get("fixed_magnification") == 0.75,
            f"A2: the registration carries the mount law (flange "
            f"{reg.get('mount_flange')}, fixed m {reg.get('fixed_magnification')})",
        )
        rows = editor.rows
        first = int(reg["first_src"])
        effl = float(reg["effl_scene"])
        f1 = float(rows[first + 1].rc)
        f2 = float(rows[first + 3].rc)
        g1 = float(rows[first].thickness)
        d = float(rows[first + 1].thickness) + float(rows[first + 2].thickness)
        g2 = float(rows[first + 3].thickness)
        span = g1 + d + g2
        ppa = g1 + effl * d / f2
        hh = span - ppa + (-(g2 + effl * d / f1)) - (span - ppa)  # rear - front station
        rear_principal = span - (g2 + effl * d / f1)
        ok(
            abs(rear_principal - ppa) <= 0.01,
            f"A3: the principals are COINCIDENT (HH' = {rear_principal - ppa:+.5f} mm; "
            f"two-group solve cannot land this -- the direct construction must)",
        )
        image_station = span + float(rows[first + 4].thickness)
        want = float(reg["rim_s"]) + 160.01 + 17.526
        ok(
            abs(image_station - want) <= 0.05,
            f"A4: the image sits AT the mount flange (station {image_station:.3f} vs "
            f"rim + L + FFD = {want:.3f})",
        )
        ok(
            abs(float(rows[0].thickness) - (110.0 + float(reg["rim_s"]))) <= 0.05,
            f"A5: the object leg is the vendor WD ({float(rows[0].thickness):.3f})",
        )
    finally:
        try:
            if editor is not None:
                editor.destroy()
        except Exception:
            pass


def _check_swap(ok, notes) -> None:
    if not SCENE.exists() or not LENS_FOLDER.exists():
        notes.append("SKIP: B: the Pyrite90 scene / 67304 folder are not in this checkout")
        return
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services import row_placement
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    editor = None
    try:
        editor = KrakenLayoutEditor()
        editor._prompt_for_missing_cad_assets = lambda: None
        editor.layout_files["_0656"] = SCENE
        editor.load_layout_by_name("_0656")
        editor.swap_imaging_lens_from_folder(str(LENS_FOLDER), refresh=False)

        lens_mesh = editor._transformed_imported_step_mesh_for_label("lens")
        pts = np.asarray(lens_mesh.points, dtype=float)
        obj = np.asarray(row_placement.world_pose(editor, 0).position, dtype=float)
        img = np.asarray(
            row_placement.world_pose(editor, len(editor.rows) - 1).position, dtype=float
        )
        axis = img - obj
        axis /= np.linalg.norm(axis)
        s = (pts - obj) @ axis
        ok(
            abs(float(s.min()) - 110.0) <= 0.05,
            f"B1: object->rim is the vendor WD ({float(s.min()):.2f} mm)",
        )
        cam_mesh = editor._transformed_imported_step_mesh_for_label("camera")
        if cam_mesh is not None:
            cs = (np.asarray(cam_mesh.points, dtype=float) - obj) @ axis
            gap = float(cs.min() - s.max())
            ok(
                -0.5 <= gap <= 5.0,
                f"B2 (the recurrence): the lens body rear MEETS the camera front "
                f"(gap {gap:+.3f} mm; the flag showed the barrel driven ~30 mm INSIDE)",
            )
        prompt = editor._prompt_fov_solve_after_swap(True)
        ok(
            "Fixed 0.75x" in prompt and "nothing to enter" in prompt,
            f"B3: the post-swap prompt STATES the fixed field instead of asking "
            f"({prompt.strip()[:80]})",
        )
        qe = QuickEstimationService(SimpleNamespace(editor=editor))
        before = [
            np.asarray(row_placement.world_pose(editor, i).position, dtype=float)
            for i in range(len(editor.rows))
        ]
        solved, msg = qe.fov_solve("object", "thickness", 20.0, 20.0)
        after = [
            np.asarray(row_placement.world_pose(editor, i).position, dtype=float)
            for i in range(len(editor.rows))
        ]
        drift = max(float(np.linalg.norm(a - b)) for a, b in zip(after, before))
        ok(
            (not solved) and "cannot be solved" in msg and drift < 1e-9,
            f"B4: a foreign field REFUSES honestly and moves NOTHING "
            f"(drift {drift:.2e}; {msg[:70]})",
        )
        fixed_semi = float(qe._sensor_semi()) / 0.75
        side = 2.0 * fixed_semi / float(np.sqrt(2.0))
        solved2, msg2 = qe.fov_solve("object", "thickness", side, side)
        ok(
            bool(solved2) and "focus confirmed" in msg2,
            f"B5: the lens's own field confirms ({msg2[:70]})",
        )
    finally:
        try:
            if editor is not None:
                editor.destroy()
        except Exception:
            pass


def _check_wiring(ok, notes) -> None:
    from KrakenOS.UI.services import layout_table_workbench as wb
    from KrakenOS.UI.services import quick_estimation as qe_mod
    from KrakenOS.UI.services import scene_placement_commands as spc

    def _method_src(module, method):
        for cls in vars(module).values():
            if isinstance(cls, type) and method in vars(cls):
                return inspect.getsource(getattr(cls, method))
        return ""

    solve_src = _method_src(qe_mod, "fov_solve")
    ok(
        "fixed_magnification" in solve_src and "cannot be solved" in solve_src,
        "C1: fov_solve gates fixed-magnification lenses (refusal, not a chase)",
    )
    swap_src = _method_src(wb, "swap_imaging_lens_from_folder")
    ok(
        "fixed_magnification" in swap_src,
        "C2: the swap sets the vendor working distance for fixed-conjugate lenses",
    )
    prompt_src = _method_src(wb, "_prompt_fov_solve_after_swap")
    ok(
        "fixed_magnification" in prompt_src,
        "C3: the post-swap prompt has the fixed-magnification branch",
    )
    refit_src = _method_src(spc, "refit_lens_principal_to_datasheet_wd")
    ok(
        "mount_flange" in refit_src and "solve_two_thin_groups(effl, ppa_new, ppp_now, span)" in refit_src,
        "C4: the refit constructs the coincident-principal shape for the mount law "
        "and keeps the two-group solve for variable-conjugate lenses",
    )


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    for section, fn in (("A", _check_import), ("B", _check_swap), ("C", _check_wiring)):
        try:
            fn(ok, notes)
        except Exception as exc:  # pragma: no cover - environment
            notes.append(f"FAIL: section {section} raised ({type(exc).__name__}: {exc})")

    passed = not any(line.startswith("FAIL") for line in notes)
    if verbose:
        for line in notes:
            print(line)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("Fixed-conjugate-mount-law validation passed.")
        return 0
    print("Fixed-conjugate-mount-law validation FAILED:")
    for line in notes:
        if line.startswith("FAIL"):
            print(f"- {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
