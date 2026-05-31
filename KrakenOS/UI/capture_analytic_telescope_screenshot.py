"""Headless screenshot of the saved analytic-telescope layout.

Loads ``attachment/five_penta_prism_analytic_telescope_cascade.py``
into the layout editor + Open 3D inspector, runs a trace, fits the
camera to the scene, and writes a PNG to
``attachment/3D_analytic_check.png``.

The point: actually look at what the user sees, instead of trusting
pose-table dumps. Run::

    .devenv/state/venv/bin/python -m KrakenOS.UI.capture_analytic_telescope_screenshot
"""

from __future__ import annotations

import sys
import time
import traceback
from pathlib import Path

from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.render_layout_snapshot import (
    _load_layout_module,
    _rows_from_layout_info,
)
from KrakenOS.UI.validate_open3d_penta_telescope_chain import _open_inspector


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LAYOUT = PROJECT_ROOT / "attachment" / "five_penta_prism_analytic_telescope_cascade.py"
OUTPUT_PNG = PROJECT_ROOT / "attachment" / "3D_analytic_check.png"


def _load_layout(app: KrakenLayoutEditor) -> None:
    module = _load_layout_module(LAYOUT)
    surfaces = list(getattr(module, "SURFACES", []) or [])
    if not surfaces:
        raise RuntimeError(f"{LAYOUT.name} exposed no SURFACES")
    app.rows = _rows_from_layout_info({"surfaces": surfaces})
    settings = dict(getattr(module, "SETTINGS", {}) or {})
    try:
        app._apply_layout_settings(settings)
    except Exception:
        pass
    try:
        app._sync_table()
    except Exception:
        pass


def _write_png(inspector, path: Path) -> None:
    from vtkmodules.vtkIOImage import vtkPNGWriter  # type: ignore
    from vtkmodules.vtkRenderingCore import vtkWindowToImageFilter  # type: ignore

    render_window = inspector._vtk_widget.GetRenderWindow()
    render_window.Render()
    capture = vtkWindowToImageFilter()
    capture.SetInput(render_window)
    try:
        capture.SetInputBufferTypeToRGBA()
    except Exception:
        pass
    try:
        capture.ReadFrontBufferOff()
    except Exception:
        pass
    capture.Update()
    writer = vtkPNGWriter()
    writer.SetFileName(str(path))
    writer.SetInputConnection(capture.GetOutputPort())
    writer.Write()


def _row_pose_dump(app: KrakenLayoutEditor) -> str:
    lines = []
    z_station = 0.0
    for idx, row in enumerate(app.rows):
        try:
            name = getattr(row, "name", "") or ""
            dx = float(getattr(row, "desp_x", 0.0) or 0.0)
            dy = float(getattr(row, "desp_y", 0.0) or 0.0)
            dz = float(getattr(row, "desp_z", 0.0) or 0.0)
            tx = float(getattr(row, "tilt_x", 0.0) or 0.0)
            ty = float(getattr(row, "tilt_y", 0.0) or 0.0)
            tz = float(getattr(row, "tilt_z", 0.0) or 0.0)
            th = float(getattr(row, "thickness", 0.0) or 0.0)
            am = float(getattr(row, "axis_move", 0.0) or 0.0)
            sd = float(getattr(row, "diameter", 0.0) or 0.0)
            rc = float(getattr(row, "rc", 0.0) or 0.0)
            mat = str(getattr(row, "glass", "") or "")
            wx = z_station + dz  # rough world-z (no chain tilt accounted for)
            lines.append(
                f"  {idx:2d} {name[:34]:<34s} desp=({dx:+7.2f},{dy:+5.2f},{dz:+7.2f}) "
                f"tilt=({tx:+5.0f},{ty:+5.0f},{tz:+5.0f}) t={th:6.2f} AxMv={am:.0f} "
                f"sd={sd:5.2f} Rc={rc:+7.2f} mat={mat[:14]}"
            )
            if am < 0.5:
                z_station += th
        except Exception as exc:
            lines.append(f"  {idx:2d} <pose-dump-error: {exc}>")
    return "\n".join(lines)


def main() -> int:
    if not LAYOUT.exists():
        print(f"FATAL: {LAYOUT} does not exist", file=sys.stderr)
        return 2

    app = KrakenLayoutEditor()
    try:
        _load_layout(app)
        print(f"Loaded {len(app.rows)} rows from {LAYOUT.name}")
        print("Row pose dump:")
        print(_row_pose_dump(app))

        inspector = _open_inspector(app)
        inspector.geometry("1920x1200+80+60")
        inspector.update_idletasks()
        inspector.update()
        time.sleep(0.5)

        inspector.show_rays_var.set(True)
        try:
            inspector.show_cardinal_var.set(False)  # less clutter
        except Exception:
            pass
        inspector.refresh_from_editor(force_retrace=True)
        inspector.update_idletasks()
        inspector.update()

        try:
            inspector._trace_live_now()
        except Exception as exc:
            print(f"WARN: trace_live raised {exc}", file=sys.stderr)
        inspector.update_idletasks()
        inspector.update()
        time.sleep(0.5)

        # Fit camera so everything in the scene is in view.
        # Compute scene bounds from row world positions so we can
        # zoom in on the optics rather than the cardinal-axis halo.
        rows = list(app.rows)
        xs, ys, zs = [], [], []
        for row in rows:
            try:
                # Approximate world pos as desp + accumulated chain z.
                # Since AxisMove=0 throughout for the analytic file we
                # built, world Z = sum(prior thicknesses) + desp_z.
                dx = float(getattr(row, "desp_x", 0.0) or 0.0)
                dy = float(getattr(row, "desp_y", 0.0) or 0.0)
                dz = float(getattr(row, "desp_z", 0.0) or 0.0)
                xs.append(dx)
                ys.append(dy)
                zs.append(dz)
            except Exception:
                continue
        # Also include z_station accumulation roughly: object thickness
        # of 100 mm.
        zs = [z + 100.0 for z in zs]  # approx world Z
        try:
            ren = inspector._vtk_widget.GetRenderWindow().GetRenderers().GetFirstRenderer()
            cam = ren.GetActiveCamera()
            if xs and ys and zs:
                cx = 0.5 * (min(xs) + max(xs))
                cy = 0.5 * (min(ys) + max(ys))
                cz = 0.5 * (min(zs) + max(zs))
                # Diagonal of bounds gives a sensible focal distance.
                span = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs), 100.0)
                focal_dist = span * 1.5
                # Place camera looking from +Y above and slightly +X
                # forward so we see the cascade fold and the lens row
                # in one view.
                cam.SetFocalPoint(cx, cy, cz)
                cam.SetPosition(cx + focal_dist * 0.3, cy + focal_dist * 0.6, cz + focal_dist * 0.7)
                cam.SetViewUp(0.0, 1.0, 0.0)
                ren.ResetCameraClippingRange()
            else:
                ren.ResetCamera()
        except Exception as exc:
            print(f"WARN: camera fit failed: {exc}", file=sys.stderr)
        inspector.update_idletasks()
        inspector.update()
        time.sleep(0.3)

        OUTPUT_PNG.parent.mkdir(parents=True, exist_ok=True)
        _write_png(inspector, OUTPUT_PNG)
        print(f"\nWrote screenshot -> {OUTPUT_PNG}")
        if not OUTPUT_PNG.exists() or OUTPUT_PNG.stat().st_size < 1000:
            print("WARN: PNG missing or suspiciously small", file=sys.stderr)
            return 1
        return 0
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 1
    finally:
        try:
            app.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
