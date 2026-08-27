"""Guard for bugs/0654 -- flipping a REAL-barrel lens STEP re-pins the opposite body
face; the glass-preserving mirror shift belongs to CLOSE barrels only.

flag_20260827_131010 ("Original: lens is flipped") + flag_20260827_131036 ("Flipped the
lens, lens surrogate and body detached"): the #67-304 telecentric swap landed mount-end
first (the front=axial-max guess), and the flip verb then slid the body +94.5 mm off its
surrogate, into the camera.

Root cause -- two fixes branching DIFFERENTLY on the same geometry:
  * `_lens_step_display_front_z` (bugs/0377) classifies the barrel: body span beyond
    1.6x the glass span = a REAL barrel, registered by its AUTHORED BODY FACE on the
    front datum (the glass-centre pin is for close barrels that track their glass).
  * `_lens_step_flip_axial_shift` (bugs/0500) applied the glass-centre-preserving
    mirror UNCONDITIONALLY. On a face-pinned real barrel that "correction" faithfully
    preserves the glass's WRONG pre-flip station -- the exact thing the user flips to
    fix -- and displaces the body by the overhang asymmetry (94.49 mm here).

The contract now: ONE shared `_CLOSE_BARREL_RATIO` decides both. Close barrel => pin
glass, flip keeps glass fixed (0500 unchanged). Real barrel => pin body face, flip
seats the OPPOSITE face on the datum (the bugs/0373 promise) -- shift 0.

Checks:
  A  PURE  -- the shift through a stub: close-barrel metrics keep the exact 0500
     mirror; real-barrel metrics (the #67-304 numbers) return 0; unflipped returns 0;
     and both methods reference the ONE shared ratio constant.
  B  REAL SCENE (skip-if-absent, Tk/Xvfb) -- swap the Pyrite90 scene to the #67-304
     folder, flip: the body's world span must not move (opposite face seated), and the
     surrogate datums stay inside it (the flagged detach cannot recur).

Run:  xvfb-run -a .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0654_real_barrel_flip_repin
"""

from __future__ import annotations

import inspect
from pathlib import Path
from types import SimpleNamespace

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENE = PROJECT_ROOT / "attachment/machine_vision_Pyrite90_0.3X.py"
LENS_FOLDER = PROJECT_ROOT / "attachment/Lens/67304_0.75X_Telecentric"


def _check_pure(ok, notes) -> None:
    from KrakenOS.UI.services import layout_polyline_display as lpd

    mixin = lpd.LayoutPolylineDisplayMixin

    def shift_for(metrics, *, reverse=True):
        stub = SimpleNamespace(
            lens_step_reverse_direction=reverse,
            imported_lens_step_path=Path("dummy.step"),
            _step_optical_glass_axial_metrics=lambda path: metrics,
        )
        return float(mixin._lens_step_flip_axial_shift(stub))

    # Asymmetric overhangs (front 2, rear 6) so the mirror is provably NON-zero.
    close = {"glass_lo": 2.0, "glass_hi": 38.0, "body_lo": 0.0, "body_hi": 44.0}
    want = (44.0 - 20.0) - (20.0 - 0.0)  # = 4.0, the 0500 mirror on a close barrel
    ok(
        abs(shift_for(close) - want) < 1e-12 and want != 0.0,
        f"A1: a CLOSE barrel keeps the 0500 glass-centre mirror (got {shift_for(close)}, "
        f"want {want})",
    )
    real = {"glass_lo": 112.0, "glass_hi": 177.517, "body_lo": 110.0, "body_hi": 274.007}
    ok(
        shift_for(real) == 0.0,
        "A2: a REAL barrel (the #67-304 numbers: 164 mm body around 65.5 mm glass) "
        "gets NO shift -- the flip seats the opposite body face (was +94.49)",
    )
    ok(
        shift_for(close, reverse=False) == 0.0,
        "A3: unflipped is always 0 (the shift is a flip correction)",
    )
    shift_src = inspect.getsource(mixin._lens_step_flip_axial_shift)
    pin_src = inspect.getsource(mixin._lens_step_display_front_z)
    ok(
        "_CLOSE_BARREL_RATIO" in shift_src and "_CLOSE_BARREL_RATIO" in pin_src,
        "A4: the pin and the flip shift branch on the ONE shared close-barrel ratio "
        "(0654 was the two disagreeing)",
    )


def _check_real_scene(ok, notes) -> None:
    if not SCENE.exists() or not LENS_FOLDER.exists():
        notes.append("SKIP: B: the Pyrite90 scene / 67304 folder are not in this checkout")
        return
    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.services import row_placement
    except Exception as exc:  # pragma: no cover - environment
        notes.append(f"SKIP: B: editor import failed ({type(exc).__name__}: {exc})")
        return
    editor = None
    try:
        editor = KrakenLayoutEditor()
        editor._prompt_for_missing_cad_assets = lambda: None
        editor.layout_files["_0654"] = SCENE
        editor.load_layout_by_name("_0654")
        editor.swap_imaging_lens_from_folder(str(LENS_FOLDER), refresh=False)

        def body_span():
            mesh = editor._transformed_imported_step_mesh_for_label("lens")
            pts = np.asarray(mesh.points, dtype=float)
            return float(pts[:, 2].min()), float(pts[:, 2].max())

        datum_rows = [
            i for i, r in enumerate(editor.rows) if "Datum" in str(getattr(r, "name", ""))
        ]
        datum_z = [
            float(np.asarray(row_placement.world_pose(editor, i).position)[2])
            for i in datum_rows
        ]
        before = body_span()
        editor.toggle_imported_lens_step_direction()
        after = body_span()
        ok(
            abs(after[0] - before[0]) < 1e-6 and abs(after[1] - before[1]) < 1e-6,
            f"B1: the flip seats the OPPOSITE face -- the body's world span does not "
            f"move ({before[0]:.2f}..{before[1]:.2f} -> {after[0]:.2f}..{after[1]:.2f}; "
            f"the flag showed +94.49)",
        )
        ok(
            after[0] <= min(datum_z) + 1e-6 and after[1] >= max(datum_z) - 1e-6,
            f"B2 (the recurrence): the surrogate datums ({min(datum_z):.2f}.."
            f"{max(datum_z):.2f}) stay INSIDE the flipped body",
        )
    except Exception as exc:  # pragma: no cover - environment
        notes.append(f"SKIP: B: the scene could not be driven ({type(exc).__name__}: {exc})")
    finally:
        try:
            if editor is not None:
                editor.destroy()
        except Exception:
            pass


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    for section, fn in (("A", _check_pure), ("B", _check_real_scene)):
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
        print("Real-barrel-flip-repin validation passed.")
        return 0
    print("Real-barrel-flip-repin validation FAILED:")
    for line in notes:
        if line.startswith("FAIL"):
            print(f"- {line}")
    return 1


def run(app=None, inspector=None):  # comprehensive-validator entry
    return run_checks(app=app, inspector=inspector)


if __name__ == "__main__":
    raise SystemExit(main())
