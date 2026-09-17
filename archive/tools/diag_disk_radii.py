"""Authoritative world-space measurement: what radius are the translucent
object/image SURFACE disks actually drawn at, vs the detector-coverage overlay
circles, for machine-vision 150mm measured + hr25MCX with Det overlay on.

Avoids camera manipulation (which hung the earlier diag); just reads VTK actor
bounds after one refresh. Hard 180s alarm so it can never wedge.
"""
from __future__ import annotations

import signal
import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor

CAMERA = "Allied Vision hr25MCX"


def _alarm(*_):
    raise SystemExit("TIMEOUT")


def main() -> int:
    signal.signal(signal.SIGALRM, _alarm)
    signal.alarm(180)
    app = KrakenLayoutEditor()
    try:
        names = list(getattr(app, "machine_vision_names", []) or [])
        target = next((n for n in names if "Measured" in n and "150" in n), None) or (names[0] if names else None)
        app.load_layout_by_name(target)
        app.update_idletasks()
        app.camera_model_var.set(CAMERA)
        app._on_camera_model_changed()
        app.update_idletasks()
        print("object_mode =", app._current_object_mode(),
              "| |m| =", app._current_finite_paraxial_magnification(),
              "| field =", app.field_type_var.get(), "/", app.field_value_var.get(),
              "| max_real_img =", app._field_metrics_summary().get("max_real_image_height"))

        app.open_3d_view()
        app.update_idletasks(); app.update()
        insp = app._three_d_inspector
        insp.show_detector_overlays_var.set(True)
        insp.refresh_from_editor(force_retrace=True)
        app.update_idletasks(); app.update()

        def dump(tag):
            ren = insp._renderer
            actors = ren.GetActors()
            actors.InitTraversal()
            rows = []
            for _ in range(actors.GetNumberOfItems()):
                a = actors.GetNextActor()
                if a is None:
                    continue
                b = a.GetBounds()
                zc = 0.5 * (b[4] + b[5])
                hx = 0.5 * (b[1] - b[0]); hy = 0.5 * (b[3] - b[2]); hz = 0.5 * (b[5] - b[4])
                if abs(zc) < 12.0 or abs(zc - 625.0) < 12.0:
                    prop = a.GetProperty()
                    col = tuple(round(c, 2) for c in prop.GetColor())
                    op = round(prop.GetOpacity(), 2)
                    rep = prop.GetRepresentationAsString()
                    rows.append((zc, hx, hy, hz, col, op, rep))
            print(f"\n--- [{tag}] field={app.field_value_var.get()} "
                  f"max_real_img={app._field_metrics_summary().get('max_real_image_height')} ---")
            for zc, hx, hy, hz, col, op, rep in sorted(rows):
                plane = "OBJ" if abs(zc) < 12 else "IMG"
                rdiag = (hx * hx + hy * hy) ** 0.5
                shape = "circle?" if abs(hx - hy) < 0.05 else "RECT?"
                print(f"  [{plane}] z={zc:7.1f}  half=({hx:6.3f},{hy:6.3f})  diag={rdiag:6.3f}  "
                      f"{shape:7} color={col} op={op}")

        dump("COVERING auto-filled")

        # Non-covering: the state the user's recordings actually captured.
        app.field_value_var.set("11.52")
        try:
            app._sync_field_mode_ui()
        except Exception:
            pass
        app.update_idletasks()
        insp.refresh_from_editor(force_retrace=True)
        app.update_idletasks(); app.update()
        dump("NON-COVERING field=11.52")
        return 0
    finally:
        try:
            app.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
