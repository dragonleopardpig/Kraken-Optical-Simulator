"""Headless repro for the two 0134-follow-up regressions.

A) After centering the LED clear aperture on the optical axis and then doing a
   plain refresh (deselect), the LED body actor goes degenerate -- "only edges
   shown" (flag_20260624_154216_516; recording idx 494).

Run under Xvfb:
    xvfb-run -a .devenv/state/venv/bin/python bugs/repro_0135_led_body.py
"""
from __future__ import annotations

from pathlib import Path

from KrakenOS.UI.layout_editor import KrakenLayoutEditor

_REPO = Path(__file__).resolve().parents[1]
_LED = _REPO / "attachment/LED/OPT-CO90-X-V1.6.2-H.STEP"
_CA_FACE = 164  # the LED clear-aperture window grouped face index


def _led_body_bounds(inspector):
    """Union bounds of the LED's pickable body actor(s) -- the same measure the
    recorder uses for step_actor_bounds. Returns None when degenerate/absent."""
    keys = list(inspector._step_actor_map.get("led", []) or [])
    by_key = inspector._actor_by_key or {}
    bmin = [float("inf")] * 3
    bmax = [float("-inf")] * 3
    found = False
    for k in keys:
        actor = by_key.get(k)
        if actor is None:
            continue
        ab = actor.GetBounds()
        if ab is None or len(ab) < 6:
            continue
        ab = [float(v) for v in ab]
        if any(ab[i] > ab[i + 1] for i in (0, 2, 4)):
            continue
        bmin = [min(bmin[j], ab[2 * j]) for j in range(3)]
        bmax = [max(bmax[j], ab[2 * j + 1]) for j in range(3)]
        found = True
    return (tuple(bmin), tuple(bmax)) if found else None


def main() -> int:
    if not _LED.exists():
        print(f"SKIP: LED STEP missing at {_LED}")
        return 0
    app = KrakenLayoutEditor()
    try:
        app.imported_led_step_path = _LED
        app.led_step_rotation_x_deg = 0.0
        app.led_step_rotation_y_deg = 0.0
        app.led_step_rotation_z_deg = 0.0
        app.select_step_component("led")
        app.open_3d_view()
        app.update_idletasks()
        app.update()
        inspector = app._three_d_inspector
        if inspector is None or not inspector.available:
            print("SKIP: inspector unavailable")
            return 0
        inspector.update_idletasks()
        inspector.update()

        print("counts:", dict(inspector._step_actor_map and {k: len(v) for k, v in inspector._step_actor_map.items()}))
        print("1. fresh import LED body bounds:", _led_body_bounds(inspector))

        # Set CA + center on optical axis (the snap).
        rec = app.set_step_clear_aperture("led", _CA_FACE)
        print("2. set CA:", rec)
        res = app.center_clear_aperture_on_optical_axis("led")
        print("3. center CA on axis ->", res)
        inspector.update_idletasks()
        inspector.update()
        print("4. after snap (partial refresh) LED body bounds:", _led_body_bounds(inspector))

        # Deselect + a full refresh, as a click on empty space would.
        app._selected_step_label = None
        inspector.refresh_from_editor(force_retrace=False)
        inspector.update_idletasks()
        inspector.update()
        print("5. after deselect+full refresh LED body bounds:", _led_body_bounds(inspector))

        # A second partial refresh of the LED overlay specifically.
        try:
            app._refresh_open_3d_views(step_label="led")
        except Exception as exc:
            print("   partial refresh raised:", repr(exc))
        inspector.update_idletasks()
        inspector.update()
        print("6. after partial LED refresh LED body bounds:", _led_body_bounds(inspector))
        return 0
    finally:
        try:
            app.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
