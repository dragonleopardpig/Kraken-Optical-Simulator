"""Faithful repro of regression A (flag_20260624_154216_516): the LED body goes
degenerate ("only edges shown") after Center-Clear-Aperture->Optical-Axis then a
deselect. Mirrors the right-click context path _center_clear_aperture_from_context
(center, _selected_step_label=None, refresh_from_editor(force_retrace=True)) and
then an empty-space deselect via the selection representation, with lens+led both
loaded. Instruments the LED body actor bounds + transformed-mesh NaN at each step.

Run:  DISPLAY=:97 .devenv/state/venv/bin/python bugs/repro_0135b_led_body.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor

_REPO = Path(__file__).resolve().parents[1]
_LED = _REPO / "attachment/LED/OPT-CO90-X-V1.6.2-H.STEP"
_LENS = _REPO / "attachment/Lens/15056/15056.STEP"
_CA_FACE = 164


def _body_actor_bounds(inspector):
    keys = list(inspector._step_actor_map.get("led", []) or [])
    by_key = inspector._actor_by_key or {}
    out = []
    for k in keys:
        actor = by_key.get(k)
        if actor is None:
            out.append((k, "MISSING"))
            continue
        ab = actor.GetBounds()
        inverted = ab is None or len(ab) < 6 or any(ab[i] > ab[i + 1] for i in (0, 2, 4))
        out.append((k, ("INVERTED" if inverted else "ok"), tuple(round(float(v), 2) for v in (ab or ()))))
    return out


def _mesh_stats(editor):
    try:
        m = editor._transformed_imported_led_step_mesh()
    except Exception as exc:
        return f"builder raised {exc!r}"
    if m is None:
        return "mesh None"
    npts = int(getattr(m, "n_points", 0))
    ncells = int(getattr(m, "n_cells", 0))
    try:
        pts = np.asarray(m.points, dtype=float)
        n_nan = int(np.count_nonzero(~np.isfinite(pts)))
        b = tuple(round(float(v), 2) for v in m.bounds)
    except Exception as exc:
        return f"n_points={npts} n_cells={ncells} points-read raised {exc!r}"
    return f"n_points={npts} n_cells={ncells} nan_coords={n_nan} bounds={b}"


def _show(inspector, editor, tag):
    print(f"\n[{tag}]")
    print("  led mesh:", _mesh_stats(editor))
    print("  led body actor(s):", _body_actor_bounds(inspector))


def main() -> int:
    if not _LED.exists():
        print(f"SKIP: LED STEP missing at {_LED}")
        return 0
    app = KrakenLayoutEditor()
    try:
        app.imported_led_step_path = _LED
        if _LENS.exists():
            app.imported_lens_step_path = _LENS
            app.select_step_component("lens")
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
        inspector.update_idletasks(); inspector.update()
        svc = inspector  # face-assignment helpers live on the inspector facade

        _show(inspector, app, "1. fresh")

        rec = app.set_step_clear_aperture("led", _CA_FACE)
        print("\nset CA:", rec)
        _show(inspector, app, "2. after set CA")

        # Select the LED as the right-click context would (picked + selected).
        app._selected_step_label = "led"
        try:
            inspector._set_step_highlight("led", render=False)
        except Exception as exc:
            print("  _set_step_highlight raised:", repr(exc))
        inspector.update_idletasks(); inspector.update()
        _show(inspector, app, "3. selected led")

        # ---- mirror _center_clear_aperture_from_context EXACTLY ----
        res = app.center_clear_aperture_on_optical_axis("led")
        print("\ncenter ->", res)
        _show(inspector, app, "4. after center (still selected internally)")

        app._selected_step_label = None
        inspector.refresh_from_editor(force_retrace=True)
        inspector.update_idletasks(); inspector.update()
        _show(inspector, app, "5. deselect + refresh_from_editor(force_retrace=True)")

        # ---- now the empty-space deselect click path ----
        try:
            inspector._set_step_highlight(None, render=False)
        except Exception as exc:
            print("  _set_step_highlight(None) raised:", repr(exc))
        try:
            inspector._clear_open3d_selection(render=False)
        except Exception as exc:
            print("  _clear_open3d_selection raised:", repr(exc))
        inspector.update_idletasks(); inspector.update()
        _show(inspector, app, "6. after _clear_open3d_selection (empty-click deselect)")

        # ---- a follow-up partial overlay refresh, as a later hover/refresh would ----
        try:
            app._refresh_open_3d_views(step_label="led")
        except Exception as exc:
            print("  partial refresh raised:", repr(exc))
        inspector.update_idletasks(); inspector.update()
        _show(inspector, app, "7. after partial led refresh")
        return 0
    finally:
        try:
            app.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
