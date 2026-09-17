"""Headless screenshot + assertions for the saved analytic-telescope layout.

Loads ``attachment/five_penta_prism_analytic_telescope_cascade.py``
into the layout editor + Open 3D inspector, runs a trace, fits the
camera to an iso view matching the user's compare pair, writes two
PNGs (rays off / rays on), and runs assertions on the row poses so
this serves as a runnable harness test (not just a visual aid).

Outputs:
  * ``attachment/3D_analytic_check_off.png`` -- rays toggled OFF
  * ``attachment/3D_analytic_check_on.png``  -- rays toggled ON

Exit code: 0 on all-green, non-zero on any failed assertion.

Run::

    .devenv/state/venv/bin/python -m KrakenOS.UI.capture_analytic_telescope_screenshot
"""

from __future__ import annotations

import sys
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.render_layout_snapshot import (
    _load_layout_module,
    _rows_from_layout_info,
)
from KrakenOS.UI.validate_open3d_penta_telescope_chain import _open_inspector


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LAYOUT = PROJECT_ROOT / "attachment" / "five_penta_prism_analytic_telescope_cascade.py"
OUTPUT_RAYS_OFF = PROJECT_ROOT / "attachment" / "3D_analytic_check_off.png"
OUTPUT_RAYS_ON = PROJECT_ROOT / "attachment" / "3D_analytic_check_on.png"
OUTPUT_TOPDOWN = PROJECT_ROOT / "attachment" / "3D_analytic_check_topdown.png"


# Expected row poses for the saved analytic layout. Tolerances are
# wide enough to absorb fit-residual jitter but tight enough to flag
# real regressions (e.g. an overlap at world origin or a swapped
# cement layer).
@dataclass(frozen=True)
class RowExpectation:
    label: str
    name_prefix: str
    desp: tuple[float, float, float]
    tilt: tuple[float, float, float]
    axis_move: float = 0.0
    glass: str = ""
    rc_min: float = -1e6
    rc_max: float = +1e6
    tol_pos_mm: float = 0.05
    tol_tilt_deg: float = 0.5


# Rows are now centred on each lens's anchor world position, so a
# 2-row lens's front and back sit at anchor +/- thickness/2 (giving
# a ball lens a single shared sphere centre at anchor).
EXPECTED_ROWS: list[RowExpectation] = [
    RowExpectation(
        label="Ball Lens 1 front",
        name_prefix="Ball Lens 1",
        desp=(+12.2625, 0.0, +97.50),  # anchor +R
        tilt=(0.0, -90.0, 0.0),
        glass="AL2O3",
        rc_min=+4.7, rc_max=+4.8,
    ),
    RowExpectation(
        label="Ball Lens 1 back",
        name_prefix="OPTICAL analytic S2",
        desp=(+2.7375, 0.0, +97.50),  # anchor -R
        tilt=(0.0, -90.0, 0.0),
        glass="AIR",
        rc_min=-4.8, rc_max=-4.7,
    ),
    RowExpectation(
        label="Ball Lens 2 front",
        name_prefix="Ball Lens 2",
        desp=(+1.3025, 0.0, +97.50),  # anchor -3.46 + R
        tilt=(0.0, -90.0, 0.0),
        glass="AL2O3",
        rc_min=+4.7, rc_max=+4.8,
    ),
    RowExpectation(
        label="Ball Lens 2 back",
        name_prefix="OPTICAL analytic S2",
        desp=(-8.2225, 0.0, +97.50),  # anchor -3.46 - R
        tilt=(0.0, -90.0, 0.0),
        glass="AIR",
        rc_min=-4.8, rc_max=-4.7,
    ),
    # DCV 32992: N-SF11 biconcave, f=-25.2 mm, R=+/-39.78 mm, t=2.5 mm
    RowExpectation(
        label="DCV front",
        name_prefix="DCV",
        desp=(-52.21, 0.0, +97.50),  # anchor -53.46 + 1.25 (half-thickness 2.5)
        tilt=(0.0, -90.0, 0.0),
        glass="N-SF11",
        rc_min=-41.0, rc_max=-38.0,
    ),
    RowExpectation(
        label="DCV back",
        name_prefix="OPTICAL analytic S2",
        desp=(-54.71, 0.0, +97.50),  # anchor -53.46 - 1.25
        tilt=(0.0, -90.0, 0.0),
        glass="AIR",
        rc_min=+38.0, rc_max=+41.0,
    ),
    # Achromat AC254-125-A: BK7 (R=+77.6, t=4.0) + SF5 (R=-55.9, t=2.83) + AIR (R=-160.8)
    # body thickness = 4.0 + 2.83 = 6.83 mm; half = 3.42; centred on anchor -153.46
    RowExpectation(
        label="Achromat front",
        name_prefix="Achromat",
        desp=(-150.04, 0.0, +97.50),
        tilt=(0.0, -90.0, 0.0),
        glass="N-BK7",
        rc_min=+75.0, rc_max=+80.0,
    ),
    RowExpectation(
        label="Achromat cement",
        name_prefix="OPTICAL native STEP S2",
        desp=(-154.04, 0.0, +97.50),
        tilt=(0.0, -90.0, 0.0),
        glass="N-SF5",
        rc_min=-58.0, rc_max=-54.0,
    ),
    RowExpectation(
        label="Achromat back",
        name_prefix="OPTICAL native STEP S3",
        desp=(-156.88, 0.0, +97.50),
        tilt=(0.0, -90.0, 0.0),
        glass="AIR",
        rc_min=-165.0, rc_max=-155.0,
    ),
]


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


def _row_pose_dump(app: KrakenLayoutEditor) -> str:
    lines = []
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
            lines.append(
                f"  {idx:2d} {name[:34]:<34s} desp=({dx:+7.2f},{dy:+5.2f},{dz:+7.2f}) "
                f"tilt=({tx:+5.0f},{ty:+5.0f},{tz:+5.0f}) t={th:6.2f} AxMv={am:.0f} "
                f"sd={sd:5.2f} Rc={rc:+7.2f} mat={mat[:14]}"
            )
        except Exception as exc:
            lines.append(f"  {idx:2d} <pose-dump-error: {exc}>")
    return "\n".join(lines)


def _find_row_for_expectation(app: KrakenLayoutEditor, exp: RowExpectation, used: set[int]) -> int | None:
    """Return the row index that best matches ``exp`` and not in ``used``.

    Match by name-prefix first; if multiple rows share the prefix we
    take the one whose desp_x is closest to expected (so back-vs-front
    of a doublet doesn't collide).
    """
    candidates: list[int] = []
    for idx, row in enumerate(app.rows):
        if idx in used:
            continue
        name = str(getattr(row, "name", "") or "")
        if name.startswith(exp.name_prefix):
            candidates.append(idx)
    if not candidates:
        return None

    def _x_distance(idx: int) -> float:
        try:
            return abs(float(getattr(app.rows[idx], "desp_x", 0.0) or 0.0) - exp.desp[0])
        except Exception:
            return float("inf")

    candidates.sort(key=_x_distance)
    return candidates[0]


def _check_assertions(app: KrakenLayoutEditor) -> tuple[int, int, list[str]]:
    """Return (passed, failed, failure_messages) for EXPECTED_ROWS."""
    passed = 0
    failed = 0
    msgs: list[str] = []
    used: set[int] = set()
    for exp in EXPECTED_ROWS:
        idx = _find_row_for_expectation(app, exp, used)
        if idx is None:
            failed += 1
            msgs.append(f"FAIL {exp.label}: no row matched prefix {exp.name_prefix!r}")
            continue
        used.add(idx)
        row = app.rows[idx]
        problems: list[str] = []
        # Position
        for axis, expected_val, actual_attr in (
            ("X", exp.desp[0], "desp_x"),
            ("Y", exp.desp[1], "desp_y"),
            ("Z", exp.desp[2], "desp_z"),
        ):
            try:
                actual = float(getattr(row, actual_attr, 0.0) or 0.0)
            except Exception:
                actual = 0.0
            if abs(actual - expected_val) > exp.tol_pos_mm:
                problems.append(
                    f"desp_{axis.lower()}={actual:+.3f} expected {expected_val:+.3f} (tol {exp.tol_pos_mm:g})"
                )
        # Tilt
        for axis, expected_val, actual_attr in (
            ("X", exp.tilt[0], "tilt_x"),
            ("Y", exp.tilt[1], "tilt_y"),
            ("Z", exp.tilt[2], "tilt_z"),
        ):
            try:
                actual = float(getattr(row, actual_attr, 0.0) or 0.0)
            except Exception:
                actual = 0.0
            if abs(actual - expected_val) > exp.tol_tilt_deg:
                problems.append(
                    f"tilt_{axis.lower()}={actual:+.1f} expected {expected_val:+.1f} (tol {exp.tol_tilt_deg:g})"
                )
        # AxisMove
        try:
            actual_axmv = float(getattr(row, "axis_move", 0.0) or 0.0)
        except Exception:
            actual_axmv = 0.0
        if abs(actual_axmv - exp.axis_move) > 1e-6:
            problems.append(f"axis_move={actual_axmv:g} expected {exp.axis_move:g}")
        # Glass
        actual_glass = str(getattr(row, "glass", "") or "")
        if exp.glass and actual_glass != exp.glass:
            problems.append(f"glass={actual_glass!r} expected {exp.glass!r}")
        # Rc range
        try:
            actual_rc = float(getattr(row, "rc", 0.0) or 0.0)
        except Exception:
            actual_rc = 0.0
        if not (exp.rc_min <= actual_rc <= exp.rc_max):
            problems.append(
                f"rc={actual_rc:+.3f} outside [{exp.rc_min:+.2f}, {exp.rc_max:+.2f}]"
            )
        if problems:
            failed += 1
            msgs.append(f"FAIL {exp.label} (row {idx}): " + "; ".join(problems))
        else:
            passed += 1
    return passed, failed, msgs


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


def _aim_topdown_camera(app: KrakenLayoutEditor, inspector) -> None:
    """Place the VTK camera for a top-down (XZ plane) view, matching
    the user's compare 3D.png orientation: X up, Z right, Y into page."""
    rows = list(app.rows)
    xs: list[float] = []
    zs: list[float] = []
    for row in rows:
        try:
            xs.append(float(getattr(row, "desp_x", 0.0) or 0.0))
            zs.append(float(getattr(row, "desp_z", 0.0) or 0.0))
        except Exception:
            continue
    zs = [z + 100.0 for z in zs]
    if not xs:
        return
    cx = 0.5 * (min(xs) + max(xs))
    cz = 0.5 * (min(zs) + max(zs))
    span = max(max(xs) - min(xs), max(zs) - min(zs), 250.0)
    try:
        ren = inspector._vtk_widget.GetRenderWindow().GetRenderers().GetFirstRenderer()
        cam = ren.GetActiveCamera()
        d = span * 1.6
        # Camera straight along +Y axis looking back toward -Y, with
        # world +X as the camera "up". That gives a top-down XZ view
        # with X up the page and Z to the right -- the layout the
        # user shows in 3D.png.
        cam.SetFocalPoint(cx, 0.0, cz)
        cam.SetPosition(cx, +d, cz)
        cam.SetViewUp(1.0, 0.0, 0.0)
        cam.SetClippingRange(d * 0.02, d * 8.0)
        ren.ResetCameraClippingRange()
    except Exception as exc:
        print(f"WARN: top-down camera fit failed: {exc}", file=sys.stderr)


def _aim_iso_camera(app: KrakenLayoutEditor, inspector) -> None:
    """Place the VTK camera to match the user's compare-pair iso view.

    The user's view (3D_ray_off.png) sits in the (+X, +Y, +Z) octant
    looking back toward scene centre, with Y as the up vector and
    enough zoom-out that the cardinal-axis halo is visible alongside
    the optics.
    """
    rows = list(app.rows)
    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    for row in rows:
        try:
            xs.append(float(getattr(row, "desp_x", 0.0) or 0.0))
            ys.append(float(getattr(row, "desp_y", 0.0) or 0.0))
            zs.append(float(getattr(row, "desp_z", 0.0) or 0.0))
        except Exception:
            continue
    # Approx world Z = desp_z + 100 (Object thickness; the rest of the
    # chain has thickness=0 in this layout).
    zs = [z + 100.0 for z in zs]
    if not xs:
        return
    cx = 0.5 * (min(xs) + max(xs))
    cy = 0.5 * (min(ys) + max(ys))
    cz = 0.5 * (min(zs) + max(zs))
    span = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs), 250.0)
    try:
        ren = inspector._vtk_widget.GetRenderWindow().GetRenderers().GetFirstRenderer()
        cam = ren.GetActiveCamera()
        cam.SetFocalPoint(cx, cy, cz)
        # Iso position in (+X, +Y, +Z) octant. Distance scales with
        # the scene span so adding elements that widen the layout
        # (e.g. the cyl lens out at world X = -265) doesn't crop the
        # camera into a fixed earlier framing.
        d = span * 1.8
        cam.SetPosition(cx + d * 0.9, cy + d * 0.7, cz + d * 1.1)
        cam.SetViewUp(0.0, 1.0, 0.0)
        cam.SetClippingRange(d * 0.02, d * 8.0)
        ren.ResetCameraClippingRange()
    except Exception as exc:
        print(f"WARN: camera fit failed: {exc}", file=sys.stderr)


def _refresh_and_settle(inspector, *, force_retrace: bool = False) -> None:
    inspector.refresh_from_editor(force_retrace=force_retrace)
    inspector.update_idletasks()
    inspector.update()
    time.sleep(0.25)


def _capture(
    inspector,
    app: KrakenLayoutEditor,
    path: Path,
    *,
    rays_on: bool,
    view: str = "iso",
) -> None:
    inspector.show_rays_var.set(bool(rays_on))
    _refresh_and_settle(inspector, force_retrace=True)
    if rays_on:
        try:
            inspector._trace_live_now()
        except Exception as exc:
            print(f"WARN: trace_live raised {exc}", file=sys.stderr)
        _refresh_and_settle(inspector)
    if view == "topdown":
        _aim_topdown_camera(app, inspector)
    else:
        _aim_iso_camera(app, inspector)
    inspector.update_idletasks()
    inspector.update()
    time.sleep(0.15)
    _write_png(inspector, path)
    if not path.exists() or path.stat().st_size < 1000:
        raise RuntimeError(f"PNG missing or too small: {path}")
    print(f"  wrote -> {path.name}")


def main() -> int:
    if not LAYOUT.exists():
        print(f"FATAL: {LAYOUT} does not exist", file=sys.stderr)
        return 2

    app = KrakenLayoutEditor()
    try:
        _load_layout(app)
        print(f"Loaded {len(app.rows)} rows from {LAYOUT.name}\n")
        print("Row pose dump:")
        print(_row_pose_dump(app))
        print("")

        passed, failed, failure_msgs = _check_assertions(app)
        print(f"Pose assertions: {passed} passed, {failed} failed")
        for msg in failure_msgs:
            print(f"  {msg}")
        print("")

        inspector = _open_inspector(app)
        inspector.geometry("1920x1200+80+60")
        # Force the embedded VTK widget to a known size -- when the
        # surface table grows (e.g. cyl lens adds 2 more rows) the
        # Tk geometry manager squeezes the 3D widget down to a few
        # pixels wide, producing a 12x568 PNG. Setting the render
        # window size directly bypasses that.
        try:
            inspector._vtk_widget.GetRenderWindow().SetSize(1280, 800)
        except Exception:
            pass
        _refresh_and_settle(inspector)

        OUTPUT_RAYS_OFF.parent.mkdir(parents=True, exist_ok=True)
        print("Capturing iso views:")
        _capture(inspector, app, OUTPUT_RAYS_OFF, rays_on=False, view="iso")
        _capture(inspector, app, OUTPUT_RAYS_ON, rays_on=True, view="iso")
        print("Capturing top-down view:")
        _capture(inspector, app, OUTPUT_TOPDOWN, rays_on=True, view="topdown")

        return 0 if failed == 0 else 1
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
