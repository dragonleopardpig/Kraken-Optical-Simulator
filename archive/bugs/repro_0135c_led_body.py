"""Faithful repro of regression A (flag_20260624_154216_516), exercising the ONE
in-app operation the earlier repros skipped: the CA-pick COMMIT path
`_apply_step_clear_aperture_pick` -> `set_step_clear_aperture` + `refresh_from_editor()`
(no force_retrace).

Recording recording_20260624_154740.json shows, at the CA commit (idx 489), the
lens+camera overlays VANISH from `_step_actor_map` (counts {lens,led,camera}->{led})
while the led survives; then after the center+deselect (idx 494) the led body bounds
go empty (= "only edges shown"). The earlier repros (a) loaded only lens+led and
(b) never ran the post-set-CA refresh_from_editor, so they never saw the drop.

This loads all three overlays like the recording and instruments per-overlay body
bounds at each step.

Run:  DISPLAY=:97 .devenv/state/venv/bin/python bugs/repro_0135c_led_body.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor

_REPO = Path(__file__).resolve().parents[1]
_LED = _REPO / "attachment/LED/OPT-CO90-X-V1.6.2-H.STEP"
_LENS = _REPO / "attachment/Lens/15056/15056.STEP"
_CAMERA = _REPO / "attachment/Cameras/3D_CAD_HR25xCXP.STEP"
_CA_FACE = 164


def _label_body_bounds(inspector, label):
    keys = list(inspector._step_actor_map.get(label, []) or [])
    by_key = inspector._actor_by_key or {}
    if not keys:
        return f"{label}: ABSENT (no actors in _step_actor_map)"
    out = []
    for k in keys:
        actor = by_key.get(k)
        if actor is None:
            out.append("MISSING")
            continue
        ab = actor.GetBounds()
        inverted = ab is None or len(ab) < 6 or any(ab[i] > ab[i + 1] for i in (0, 2, 4))
        out.append("INVERTED/empty" if inverted else "ok")
    return f"{label}: {out}"


def _counts(inspector):
    return {k: len(v) for k, v in (inspector._step_actor_map or {}).items()}


def _show(inspector, tag):
    print(f"\n[{tag}]  counts={_counts(inspector)}")
    for label in ("lens", "led", "camera"):
        print("   ", _label_body_bounds(inspector, label))


def main() -> int:
    if not _LED.exists():
        print(f"SKIP: LED STEP missing at {_LED}")
        return 0
    load_camera = _CAMERA.exists()
    app = KrakenLayoutEditor()
    try:
        app.imported_led_step_path = _LED
        if _LENS.exists():
            app.imported_lens_step_path = _LENS
            app.select_step_component("lens")
        if load_camera:
            app.imported_camera_step_path = _CAMERA
            app.select_step_component("camera")
        app.led_step_rotation_x_deg = 0.0
        app.led_step_rotation_y_deg = 0.0
        app.led_step_rotation_z_deg = 0.0
        app.select_step_component("led")
        app.open_3d_view()
        app.update_idletasks(); app.update()
        inspector = app._three_d_inspector
        if inspector is None or not inspector.available:
            print("SKIP: inspector unavailable")
            return 0
        inspector.update_idletasks(); inspector.update()

        _show(inspector, "1. fresh (all overlays)")

        # ---- mirror _apply_step_clear_aperture_pick EXACTLY ----
        app._selected_step_label = "led"
        inspector._set_step_highlight("led", render=False)
        rec = app.set_step_clear_aperture("led", _CA_FACE)
        print("\nset CA:", rec)
        # the in-app commit does these post-set steps:
        inspector._step_clear_aperture_pick_mode = False
        inspector._set_step_hover_outline(None, None)
        inspector.refresh_from_editor()  # <-- force_retrace=False, the in-app call
        inspector.update_idletasks(); inspector.update()
        _show(inspector, "2. after set CA + refresh_from_editor() [in-app commit]")

        # ---- right-click context: center clear aperture on optical axis ----
        res = app.center_clear_aperture_on_optical_axis("led")
        print("\ncenter ->", res)
        inspector.update_idletasks(); inspector.update()
        _show(inspector, "3. after center (still selected internally)")

        # ---- the deselect + force-retrace refresh ----
        app._selected_step_label = None
        inspector.refresh_from_editor(force_retrace=True)
        inspector.update_idletasks(); inspector.update()
        _show(inspector, "4. deselect + refresh_from_editor(force_retrace=True)")

        # ---- empty-space deselect click path ----
        try:
            inspector._set_step_highlight(None, render=False)
        except Exception as exc:
            print("  _set_step_highlight(None) raised:", repr(exc))
        try:
            inspector._clear_open3d_selection(render=False)
        except Exception as exc:
            print("  _clear_open3d_selection raised:", repr(exc))
        inspector.update_idletasks(); inspector.update()
        _show(inspector, "5. after _clear_open3d_selection (empty-click deselect)")
        return 0
    finally:
        try:
            app.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
