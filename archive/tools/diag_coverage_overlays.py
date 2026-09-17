"""Headless diagnostic: enumerate every overlay actor drawn at the object/image
planes for the machine-vision layout + hr25MCX with the detector overlay on.

Run under Xvfb:
    xvfb-run -a .devenv/state/venv/bin/python tools/diag_coverage_overlays.py
"""
from __future__ import annotations

import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor

LAYOUT_NAME = "Machine Vision 150mm Measured"
CAMERA = "Allied Vision hr25MCX"


def _radius_or_extent(pts: np.ndarray, center: np.ndarray) -> str:
    d = np.linalg.norm(pts[:, :3] - center[:3], axis=1)
    rmin, rmax = float(d.min()), float(d.max())
    if rmax - rmin < 0.05 * max(rmax, 1.0):
        return f"circle r={rmax:.3f}"
    # rect: report half-extents along principal axes
    ex = 0.5 * (pts[:, 0].max() - pts[:, 0].min())
    ey = 0.5 * (pts[:, 1].max() - pts[:, 1].min())
    ez = 0.5 * (pts[:, 2].max() - pts[:, 2].min())
    return f"rect/other half=({ex:.3f},{ey:.3f},{ez:.3f}) rspan={rmin:.3f}..{rmax:.3f}"


def main() -> int:
    app = KrakenLayoutEditor()
    try:
        names = list(getattr(app, "machine_vision_names", []) or [])
        target = next((n for n in names if "Measured" in n and "150" in n), None) or (names[0] if names else None)
        print("available machine-vision layouts:", names)
        print("loading:", target)
        app.load_layout_by_name(target)
        app.update_idletasks()

        # Select the camera (triggers the bug-0032 auto-fill).
        try:
            app.camera_model_var.set(CAMERA)
            app._on_camera_model_changed()
        except Exception as exc:
            print("camera select failed:", repr(exc))
        app.update_idletasks()

        print("object_mode =", app._current_object_mode())
        print("|m| =", app._current_finite_paraxial_magnification())
        print("field type/value =", app.field_type_var.get(), "/", app.field_value_var.get())
        summ = app._field_metrics_summary()
        print("max_real_image_height =", summ.get("max_real_image_height"))
        try:
            qe = app._three_d_inspector._quick_estimation_service() if app._three_d_inspector else None
        except Exception:
            qe = None

        app.open_3d_view()
        app.update_idletasks(); app.update()
        insp = app._three_d_inspector
        if insp is None or not insp.available:
            print("inspector unavailable")
            return 0
        try:
            print("QE enabled =", insp._quick_estimation_service().is_enabled())
        except Exception as exc:
            print("QE state unknown:", repr(exc))

        insp.show_detector_overlays_var.set(True)

        # Instrument _add_mesh_actor to log overlay-coloured line actors.
        log: list[str] = []
        orig = insp._add_mesh_actor
        overlay_colors = {
            (0.2, 0.9, 0.35): "GREEN",
            (0.2, 0.7, 1.0): "CYAN",
            (1.0, 0.55, 0.1): "AMBER",
            (1.0, 0.9, 0.2): "YELLOW",
            (0.65, 0.65, 0.65): "GRAY",
        }

        def wrapped(mesh, *a, **k):
            color = k.get("color")
            try:
                ck = tuple(round(float(c), 3) for c in color) if color is not None else None
            except Exception:
                ck = None
            name = overlay_colors.get(ck)
            if name is not None:
                try:
                    pts = np.asarray(mesh.points, dtype=float)
                    c = pts.mean(axis=0)
                    log.append(f"  {name:6} {_radius_or_extent(pts, c)}  center_z={c[2]:.1f} width={k.get('line_width')}")
                except Exception as exc:
                    log.append(f"  {name:6} <pts err {exc!r}>")
            return orig(mesh, *a, **k)

        def dump_state(tag):
            log.clear()
            insp._add_mesh_actor = wrapped
            insp.refresh_from_editor(force_retrace=True)
            app.update_idletasks(); app.update()
            insp._add_mesh_actor = orig
            print(f"\n=== [{tag}] field={app.field_type_var.get()}/{app.field_value_var.get()} "
                  f"max_real_img={app._field_metrics_summary().get('max_real_image_height')} ===")
            # surface-disk radii via row actor bounds
            try:
                rb = insp._row_actor_bounds_snapshot() if hasattr(insp, "_row_actor_bounds_snapshot") else {}
            except Exception:
                rb = {}
            for line in log:
                print(line)
            try:
                ren = insp._renderer
                import vtk

                def headon(plane_z, halfspan, suffix):
                    cam = ren.GetActiveCamera()
                    cam.ParallelProjectionOn()
                    cam.SetFocalPoint(0.0, 0.0, plane_z)
                    cam.SetPosition(0.0, 0.0, plane_z - 200.0)  # look along +Z, down the axis
                    cam.SetViewUp(0.0, 1.0, 0.0)
                    cam.SetParallelScale(halfspan)
                    ren.GetRenderWindow().Render()
                    w2i = vtk.vtkWindowToImageFilter(); w2i.SetInput(ren.GetRenderWindow()); w2i.Update()
                    wr = vtk.vtkPNGWriter(); wr.SetFileName(f"/tmp/diag_{tag}_{suffix}.png")
                    wr.SetInputConnection(w2i.GetOutputPort()); wr.Write()
                    print(f"  screenshot -> /tmp/diag_{tag}_{suffix}.png")

                ren.GetRenderWindow().Render()
                w2i = vtk.vtkWindowToImageFilter(); w2i.SetInput(ren.GetRenderWindow()); w2i.Update()
                wr = vtk.vtkPNGWriter(); wr.SetFileName(f"/tmp/diag_{tag}.png")
                wr.SetInputConnection(w2i.GetOutputPort()); wr.Write()
                print(f"  screenshot -> /tmp/diag_{tag}.png")
                headon(0.0, 22.0, "obj")
                headon(625.0, 22.0, "img")
            except Exception as exc:
                print("  screenshot failed:", repr(exc))

        dump_state("covering")

        # Force the non-covering state the user recorded: shrink the field.
        app.field_value_var.set("11.52")
        app._last_field_type = app._last_field_type
        try:
            app._sync_field_mode_ui()
        except Exception:
            pass
        app.update_idletasks()
        dump_state("noncovering")
        return 0
    finally:
        try:
            app.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
