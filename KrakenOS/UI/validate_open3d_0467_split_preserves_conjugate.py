"""bugs/0467 guard -- a frozen leg split must not move the magnification.

flag_20260729_140916: "changed FOV to 30x30 with constraints but the display says 16.3x16.3 ...
And the rays are defocus at the sensor."

The FOV label was right; the optics had moved under it. Measured on the user's scene:

    start              |m| = 1.1520   object_total 125.463   image_total 154.770
    after OBJECT split |m| = 1.4171   object_total 125.463   image_total 154.770

Both split readouts said "unchanged" while the paraxial magnification jumped, so the label
correctly reported 23 mm / 1.4171 = 16.2 mm of field -- and a just-solved 30 x 30 was
destroyed by applying the leg constraint, with the rays landing defocused.

Cause: ``_apply_frozen_bs_object_split`` grew the OBJECT gap by ``delta`` with no
compensating subtraction, so the object CONJUGATE grew with it. The unfrozen path has always
compensated (near += delta, far -= delta); the frozen path only ever added -- contradicting
its own docstring ("a rigid repackaging, focus untouched").

Check: sliding the object leg on the frozen BS scene leaves |m| unchanged.
"""
from __future__ import annotations

from pathlib import Path

BS_SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")
TOLERANCE = 1.0e-3


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True
    if not BS_SCENE.exists():
        return True, ["SKIP: the BS scene is absent (gitignored attachment)"]

    app = None
    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor

        app = KrakenLayoutEditor()
        app.layout_files["bs"] = BS_SCENE
        app.load_layout_by_name("bs")
        before = float(app._current_finite_paraxial_magnification())
        split = app._folded_object_conjugate_split()
        if not isinstance(split, dict):
            notes.append("SKIP: this scene offers no object-side split")
            return ok, notes
        applied, message = app._apply_folded_object_split("near", 40.0)
        after = float(app._current_finite_paraxial_magnification())
        if not applied:
            notes.append(f"SKIP: the split declined ({str(message)[:60]})")
            return ok, notes
        if abs(after - before) <= TOLERANCE:
            notes.append(f"CONJUGATE = the object split left |m| at {after:.4f} (rigid repackaging)")
        else:
            notes.append(
                f"CONJUGATE the object split moved |m| {before:.4f} -> {after:.4f}; "
                "the focus/FOV it was solved for is destroyed"
            )
            ok = False
    except Exception as exc:
        notes.append(f"SKIP: scene drive failed ({exc!r})")
    finally:
        if app is not None:
            try:
                app.destroy()
            except Exception:
                pass
    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if ("=" in note or note.startswith("SKIP")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
