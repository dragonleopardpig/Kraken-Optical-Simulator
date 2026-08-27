"""Guard for bugs/0657 -- body rotations pivot on the CLEAR-APERTURE axis, never the
centroid an illumination port has dragged sideways.

flag_20260827_145650: "I flipped the lens, then I rotated the lens to orientate the
in-line illumination port, but now it is off axis." The user's own diagnosis --
"the algorithm not taking the clear aperture lens as the center of rotation, it also
take into account the illumination port" -- confirmed to the millimetre:
``rotate_step_world_axis`` kept ``mesh.center`` fixed (offset += center_before -
center_after). On the #67-319 In-Line telecentric the port drags the centroid 5.35 mm
off the barrel, and the 270-degree roll swung the barrel 5.35*sqrt(2) = 7.566 mm off
the optical axis -- exactly the placement offset found stored in the flagged scene.

The fix: ``_step_rotation_pivot_world`` -- a point ON the CAD barrel axis for the lens
(the same clear-aperture anchor the alignment centres on, bugs/0077), the centroid
only for axis-less bodies. Plus a one-click transverse repair on the lens right-click
("Re-centre Body on Optical Axis"), reusing the bugs/0568 recentring.

Checks:
  A  REAL SCENE (skip-if-absent, Tk/Xvfb, the user's own Basler_Telecentric layout):
     the repair verb zeroes any stored transverse offset, then a roll/tilt sequence
     (z+90, z-45, x+10, x-10, z+315) leaves the barrel ON the axis (< 0.05 mm) --
     with the centroid pivot the FIRST roll alone displaced it millimetres.
  B  WIRING: the rotation uses the pivot helper; the helper anchors the lens on
     _lens_step_overlay_axis_world_line; the repair verb is on the body menu.

Run:  xvfb-run -a .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0657_rotation_pivot_clear_aperture
"""

from __future__ import annotations

import inspect
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENE = PROJECT_ROOT / "attachment/Basler_Telecentric.py"


def _check_real_scene(ok, notes) -> None:
    if not SCENE.exists():
        notes.append("SKIP: A: the Basler_Telecentric scene is not in this checkout")
        return
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = None
    try:
        editor = KrakenLayoutEditor()
        editor._prompt_for_missing_cad_assets = lambda: None
        editor.layout_files["_0657"] = SCENE
        editor.load_layout_by_name("_0657")
        surrogate = editor._lens_surrogate_optical_axis_line()
        if surrogate is None:
            notes.append("SKIP: A: no surrogate axis on this checkout's scene")
            return
        axis_point, axis_dir = surrogate

        def off_axis() -> float:
            line = editor._lens_step_overlay_axis_world_line()
            d = np.asarray(axis_point, dtype=float) - np.asarray(line[0], dtype=float)
            d = d - float(np.dot(d, axis_dir)) * np.asarray(axis_dir, dtype=float)
            return float(np.linalg.norm(d))

        diag = editor.center_lens_body_on_surrogate_axis(context="guard_0657")
        ok(
            diag is not None and off_axis() < 0.01,
            f"A1: the repair verb puts the barrel ON the axis (off {off_axis():.4f} mm; "
            f"was {None if diag is None else diag.get('before_mm')})",
        )
        worst = 0.0
        for axis, step in (("z", 90.0), ("z", -45.0), ("x", 10.0), ("x", -10.0), ("z", 315.0)):
            editor.rotate_step_world_axis("lens", axis, step, refresh=False)
            worst = max(worst, off_axis())
        ok(
            worst < 0.05,
            f"A2 (the recurrence): rolls AND tilts pivot on the clear aperture -- worst "
            f"off-axis {worst:.4f} mm across the sequence (the centroid pivot gave "
            f"7.566 mm on one roll)",
        )
    finally:
        try:
            if editor is not None:
                editor.destroy()
        except Exception:
            pass


def _check_wiring(ok, notes) -> None:
    from KrakenOS.UI.services import open3d_face_assignment as fa
    from KrakenOS.UI.services import scene_placement_commands as spc

    def _method_src(module, method):
        for cls in vars(module).values():
            if isinstance(cls, type) and method in vars(cls):
                return inspect.getsource(getattr(cls, method))
        return ""

    rotate_src = _method_src(spc, "rotate_step_world_axis")
    ok(
        "_step_rotation_pivot_world" in rotate_src and "mesh.center" not in rotate_src,
        "B1: the rotation compensation anchors on the pivot helper, not mesh.center",
    )
    pivot_src = _method_src(spc, "_step_rotation_pivot_world")
    ok(
        "_lens_step_overlay_axis_world_line" in pivot_src,
        "B2: the lens pivot is a point on the CAD barrel axis (clear aperture)",
    )
    menu_src = _method_src(fa, "append_step_body_actions")
    ok(
        "Re-centre Body on Optical Axis" in menu_src
        and "center_lens_body_on_surrogate_axis" in menu_src,
        "B3: the one-click transverse repair is on the lens body menu",
    )


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    for section, fn in (("A", _check_real_scene), ("B", _check_wiring)):
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
        print("Rotation-pivot-clear-aperture validation passed.")
        return 0
    print("Rotation-pivot-clear-aperture validation FAILED:")
    for line in notes:
        if line.startswith("FAIL"):
            print(f"- {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
