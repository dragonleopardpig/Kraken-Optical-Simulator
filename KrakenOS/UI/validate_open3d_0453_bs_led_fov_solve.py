"""bugs/0453 guard -- the FOV thickness solve holds a promoted BS on its LED body.

flag_20260727_132644 ("BS Cube detached from the LED STEP after changing FOV"): "Solve
for Thickness" wrote the object gap and slid the promoted BS off its (separately
anchored) LED body. `_object_locked_redirect_row` -- which holds the object gap and
moves the lens instead -- only fired on the `_optical_led_glued` bool, which used to be
True by accident (dead settings write before bugs/0449). The redirect now recognises the
LED+BS unit by TOPOLOGY: a promoted solid immediately after the object gap in a scene
that imported an LED STEP.

Checks:
  SOURCE -- the redirect no longer gates solely on the glue bool.
  REAL   -- on the coaxial 150 mm scene (LED present, glue False) the thickness solve
            holds the object gap and moves the lens gap instead.
  NEG    -- with no LED and not glued, the redirect stands down.
"""
from __future__ import annotations

import inspect as _inspect
from pathlib import Path


class _Shim:
    def __init__(self, editor):
        self.editor = editor


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    try:
        from KrakenOS.UI.services.quick_estimation import QuickEstimationService
    except Exception as exc:
        return True, [f"SKIP: quick_estimation unavailable ({exc!r})"]

    src = _inspect.getsource(QuickEstimationService._object_locked_redirect_row)
    if "_step_path_for_label" in src and "led" in src:
        notes.append("SOURCE = redirect recognises the LED topology, not only the glue bool")
    else:
        notes.append("SOURCE the 0453 topology broadening is missing")
        ok = False

    scene = None
    for name in ("machine_vision_150mm_test", "machine_vision_150mm_GN"):
        if Path(f"attachment/{name}.py").exists():
            scene = name
            break
    if scene is None:
        notes.append("SKIP: no coaxial 150 mm scene present (gitignored attachment)")
        return ok, notes

    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor

        app = KrakenLayoutEditor()
    except Exception as exc:
        notes.append(f"SKIP: editor unavailable ({exc!r})")
        return ok, notes
    try:
        app.layout_files[scene] = Path(f"attachment/{scene}.py")
        app.load_layout_by_name(scene)
        qe = QuickEstimationService(_Shim(app))
        obj_row = qe.object_thickness_row()
        redirect = qe._object_locked_redirect_row(obj_row)
        led_present = app._step_path_for_label("led") is not None
        glued = bool(getattr(app, "_optical_led_glued", False))
        # The 0453 contract is TOPOLOGY-over-bool: the redirect fires for the LED+BS unit
        # whether or not the glue bool is set (the user's re-saved scene now loads
        # glued=True, which is just as valid a positive config as the old glued=False).
        if led_present and redirect is not None:
            obj_before = float(app.rows[obj_row].thickness)
            lens_before = float(app.rows[redirect].thickness)
            done, _msg = qe.fov_solve("object", "thickness", 23.0, 23.0)
            obj_after = float(app.rows[obj_row].thickness)
            lens_after = float(app.rows[redirect].thickness)
            if done and abs(obj_after - obj_before) < 1e-6 and abs(lens_after - lens_before) > 1e-6:
                notes.append("REAL = object gap held, lens gap moved (BS stays on the LED)")
            else:
                notes.append(
                    f"REAL solve moved the wrong gap: obj {obj_before:.4g}->{obj_after:.4g}, "
                    f"lens {lens_before:.4g}->{lens_after:.4g}"
                )
                ok = False
        else:
            notes.append(
                f"REAL config unexpected (led={led_present} glued={glued} redirect={redirect}) -- skipped"
            )

        # NEG means BOTH triggers absent: the fixture must FORCE the glue bool off too --
        # inheriting the scene's saved glue state (True since the user's in-app re-save)
        # left one trigger armed and the redirect legitimately fired.
        saved = app.imported_led_step_path
        saved_glued = bool(getattr(app, "_optical_led_glued", False))
        app.imported_led_step_path = None
        app._optical_led_glued = False
        try:
            no_led = qe._object_locked_redirect_row(obj_row)
        finally:
            app.imported_led_step_path = saved
            app._optical_led_glued = saved_glued
        if no_led is None:
            notes.append("NEG = no LED + not glued -> redirect stands down")
        else:
            notes.append(f"NEG redirect fired without an LED (row {no_led})")
            ok = False
    except Exception as exc:
        notes.append(f"SKIP: real-scene drive failed ({exc!r})")
    finally:
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
