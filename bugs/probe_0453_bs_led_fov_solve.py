"""bugs/0453 -- the FOV thickness solve must not slide a promoted BS off its LED body.

flag_20260727_132644 ("BS Cube detached from the LED STEP after changing FOV"): on the
coaxial 150 mm scene (Object -> promoted BS on the LED -> lens -> sensor), "Solve for
Thickness" wrote the OBJECT gap, sliding the BS row ~104 mm toward the object while the
LED STEP body -- anchored separately -- stayed put, so the BS detached from the LED.

Root: `_object_locked_redirect_row` (which keeps the LED+BS fixed and moves the lens
instead) only fired when `_optical_led_glued` was True. That bool used to be True by
accident (before bugs/0449 the settings service could not write it, so a stale runtime
True lingered); once 0449 made it restore correctly to the saved False, the redirect
stopped and the object gap started moving. Fix: the illumination unit is defined by
TOPOLOGY -- a promoted solid immediately after the object gap in a scene that imported
an LED STEP is the coaxial LED+BS unit, glued or not -- so the redirect fires for it too.

Run: DISPLAY=:N .devenv/state/venv/bin/python bugs/probe_0453_bs_led_fov_solve.py
"""
from __future__ import annotations

from pathlib import Path

FAILURES: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(("ok " if ok else "XX "), label, (" " + detail if detail else ""))
    if not ok:
        FAILURES.append(label)


class _Shim:
    """Minimal QuickEstimationService host: it only reads ``.editor``."""

    def __init__(self, editor):
        self.editor = editor


def _load(app):
    for name in ("machine_vision_150mm_test", "machine_vision_150mm_GN"):
        p = Path(f"attachment/{name}.py")
        if p.exists():
            app.layout_files[name] = p
            app.load_layout_by_name(name)
            return name
    return None


def main() -> int:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    app = KrakenLayoutEditor()
    try:
        name = _load(app)
        if name is None:
            print("SKIP: no coaxial 150 mm scene present (gitignored attachment)")
            return 0
        qe = QuickEstimationService(_Shim(app))

        led_present = app._step_path_for_label("led") is not None
        glued = bool(getattr(app, "_optical_led_glued", False))
        check("scene is the LED+BS coaxial unit with the glue bool OFF (the flag's config)",
              led_present and not glued, f"led={led_present} glued={glued}")

        obj_row = qe.object_thickness_row()
        solid = (obj_row or 0) + 1
        adv = getattr(app.rows[solid], "advanced", {}) or {}
        promoted = bool(adv.get("OpticalSolidFaces") or adv.get("Solid_3d_stl"))
        check("a promoted solid sits immediately after the object gap (the BS)", promoted, f"S{solid}")

        redirect = qe._object_locked_redirect_row(obj_row)
        check("redirect now fires on LED topology despite glue=False (the guard)",
              redirect is not None and redirect > solid, f"redirect={redirect}")

        obj_before = float(app.rows[obj_row].thickness)
        lens_before = float(app.rows[redirect].thickness) if redirect is not None else None

        ok, msg = qe.fov_solve("object", "thickness", 23.0, 23.0)
        obj_after = float(app.rows[obj_row].thickness)
        lens_after = float(app.rows[redirect].thickness) if redirect is not None else None
        check("fov_solve succeeded", ok, str(msg)[:80])
        check("the object gap is HELD -- the BS does not slide off the LED",
              abs(obj_after - obj_before) < 1e-6, f"{obj_before:.4g} -> {obj_after:.4g}")
        check("the lens gap absorbed the change instead (same conjugate, LED+BS fixed)",
              lens_before is not None and abs(lens_after - lens_before) > 1e-6,
              f"{lens_before:.4g} -> {lens_after:.4g}")

        # Negative control: no LED and not glued -> the redirect must NOT fire (a plain
        # imaging scene's object gap is free to move).
        saved = app.imported_led_step_path
        app.imported_led_step_path = None
        try:
            no_led = qe._object_locked_redirect_row(obj_row)
        finally:
            app.imported_led_step_path = saved
        check("no LED + not glued: redirect stands down (object gap free to move)",
              no_led is None, f"redirect={no_led}")
    finally:
        try:
            app.destroy()
        except Exception:
            pass

    if FAILURES:
        print(f"FAIL: {FAILURES}")
        return 1
    print("RESULT: PASS -- the FOV thickness solve holds the LED+BS fixed and moves the lens")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
