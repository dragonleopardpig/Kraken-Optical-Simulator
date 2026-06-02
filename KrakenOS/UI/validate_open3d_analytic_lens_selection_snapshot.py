#!/usr/bin/env python3
"""Image-snapshot regression test for bugs/0002: a selected analytic lens must
NOT show a "ghost red block" trailing the pink translucent body.

Unlike the property-only contract test
(``validate_open3d_analytic_lens_select_not_all_red``), this renders the
*actual* selected scene to a PNG (off-screen, needs an X server) and inspects
PIXELS: the selected lens must be dominated by pink fill with only a negligible
amount of red (the handful of red pixels in the axis-origin marker), never a
red region the size of the body.

Why pixels and not vtkProperty assertions: the all-red fix (bugs/0001) passed
*every* property assertion -- yet a second, baseline-invisible companion
surface backing the analytic lens still painted solid red, because selection
bumped its opacity 0->0.75 and turned on red triangle edges (bugs/0002). No
property check on the actors we knew about could see that stray actor. Only a
rendered image catches it.

Run (boots its own private Xvfb if DISPLAY is unset):
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_analytic_lens_selection_snapshot

Exit: 0 = pass, 1 = regression (red block present / no pink fill),
      2 = environment can't render (no Xvfb, no DCV fixture).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Pixel-count thresholds for a PASS, calibrated on the post-fix render
# (1280x860 inspector window, full-window capture):
#   selected DCV  -> red=9   pink=2730
#   selected disc -> red=9   pink=1198..1717
#   baseline      -> red=9   pink=3
# The constant red=9 is the small red dot of the X-axis origin marker, a
# fixed UI element unrelated to the lens. A pre-fix "ghost red block" was the
# size of the body fill -> ~1000+ red pixels. These thresholds separate the
# two by more than an order of magnitude in both directions.
RED_MAX_PIXELS = 80
PINK_MIN_PIXELS = 500

# Pixel classifiers (RGB, 0-255). PINK fill is (255,115,166); RED edges/marker
# are saturated red. Kept loose enough to survive anti-aliasing / shading.
def classify_red_pink(png_path: "str | Path") -> tuple[int, int]:
    """Return (red_pixel_count, pink_pixel_count) for a rendered PNG."""
    import numpy as np
    from PIL import Image

    arr = np.asarray(Image.open(png_path).convert("RGB")).astype(int)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    red = (r > 120) & (g < 70) & (b < 70)
    pink = (r > 180) & (g >= 80) & (g <= 185) & (b >= 120) & (b <= 215)
    return int(red.sum()), int(pink.sum())


def render_window_to_png(inspector, png_path: "str | Path") -> None:
    """Capture the inspector's VTK render window to a PNG (off-screen safe)."""
    from vtkmodules.vtkIOImage import vtkPNGWriter
    from vtkmodules.vtkRenderingCore import vtkWindowToImageFilter

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
    writer.SetFileName(str(png_path))
    writer.SetInputConnection(capture.GetOutputPort())
    writer.Write()


# --- self-contained virtual display (mirrors tools/penta_validator_gate.py) --
def _free_display() -> int:
    for num in (94, 93, 92, 91, 90):
        if not Path(f"/tmp/.X11-unix/X{num}").exists():
            return num
    return 124


def _start_xvfb(display: int, timeout: float = 15.0):
    xvfb = shutil.which("Xvfb")
    if xvfb is None:
        return None, "Xvfb not found on PATH"
    proc = subprocess.Popen(
        [xvfb, f":{display}", "-screen", "0", "1600x1000x24"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    sock = Path(f"/tmp/.X11-unix/X{display}")
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            return None, f"Xvfb exited early (code {proc.returncode})"
        if sock.exists():
            return proc, None
        time.sleep(0.2)
    proc.terminate()
    return None, f"Xvfb :{display} did not come up within {timeout:.0f}s"


def _ensure_display():
    """Return (xvfb_proc_or_None, error_or_None). Sets os.environ['DISPLAY']."""
    if os.environ.get("DISPLAY"):
        return None, None  # caller-provided display (e.g. the gate's Xvfb)
    display = _free_display()
    proc, err = _start_xvfb(display)
    if proc is None:
        return None, err
    os.environ["DISPLAY"] = f":{display}"
    return proc, None


def _promote_and_select_dcv(out_dir: Path) -> "tuple[Path | None, str]":
    """Boot the inspector, promote the DCV fixture onto a clean Object+Image
    chain, select row 1 via the live recolor path, and render the result.

    Returns (png_path, message). png_path is None when the fixture is missing
    or no glassy body was produced (an environment skip, not a failure).
    """
    # Imported here -- after DISPLAY is guaranteed -- because constructing the
    # Tk app needs an X server.
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor, SurfaceRow
    from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import (
        _open_inspector,
        _import_step,
        LENS_FIXTURES,
    )

    fixture = next(
        (f for f in LENS_FIXTURES if "dcv" in f["name"].lower()
         or "double" in f["name"].lower() or "concave" in f["name"].lower()),
        None,
    )
    if fixture is None:
        return None, "no DCV (double-concave) STEP fixture checked out"

    app = KrakenLayoutEditor()
    inspector = _open_inspector(app)

    app.rows = [
        SurfaceRow(label="0", surface="Object", element="", name="Object",
                   thickness=50.0, diameter=12.0, glass="AIR"),
        SurfaceRow(label="1", surface="Image", element="", name="Image",
                   thickness=0.0, diameter=12.0, glass="AIR"),
    ]
    app._sync_table()
    try:
        app.clear_step_imports()
    except Exception:
        pass
    _import_step(app, fixture["step"])
    inspector.refresh_from_editor(force_retrace=True)
    inspector.update_idletasks()
    try:
        app.promote_imported_step_to_analytic_surfaces(
            "optical", glass_sequence=fixture["glass"],
            clear_overlay=True, refresh_open_3d=False,
        )
    except Exception as exc:
        return None, f"promote raised {exc!r}"
    inspector.refresh_from_editor(force_retrace=True)
    inspector.update_idletasks()

    coll = inspector._renderer.GetActors()
    coll.InitTraversal()
    glassy = any(
        bool(getattr(coll.GetNextActor(), "_kraken_glassy_lens_body", False))
        for _ in range(coll.GetNumberOfItems())
    )
    if not glassy:
        return None, f"{fixture['name']}: no glassy lens body produced"

    # Rays off so the capture isolates the lens body, then select row 1.
    try:
        inspector.show_rays_var.set(False)
    except Exception:
        pass
    inspector.refresh_from_editor(force_retrace=False)
    inspector.update_idletasks()
    inspector._set_row_highlights([1])
    inspector.update_idletasks()
    inspector.update()

    png_path = out_dir / "analytic_lens_selected_dcv.png"
    render_window_to_png(inspector, png_path)
    return png_path, f"rendered {fixture['name']} (glass={fixture['glass']})"


def main() -> int:
    out_dir = Path(os.environ.get("KRAKEN_SNAPSHOT_DIR", "/tmp/kraken_lens_snapshot"))
    out_dir.mkdir(parents=True, exist_ok=True)

    xvfb_proc, env_err = _ensure_display()
    if env_err is not None:
        print(f"[SKIP] cannot render snapshot: {env_err}")
        return 2
    try:
        png_path, message = _promote_and_select_dcv(out_dir)
    finally:
        if xvfb_proc is not None:
            xvfb_proc.terminate()
            try:
                xvfb_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                xvfb_proc.kill()

    if png_path is None:
        print(f"[SKIP] {message}")
        return 2

    red_px, pink_px = classify_red_pink(png_path)
    print(f"snapshot: {png_path}")
    print(f"  {message}")
    print(f"  red pixels  = {red_px:5d} (limit < {RED_MAX_PIXELS})")
    print(f"  pink pixels = {pink_px:5d} (need  > {PINK_MIN_PIXELS})")

    failures: list[str] = []
    if red_px >= RED_MAX_PIXELS:
        failures.append(
            f"red pixels {red_px} >= {RED_MAX_PIXELS}: a ghost red block is "
            "painting the selected lens (bugs/0002 regression)"
        )
    if pink_px <= PINK_MIN_PIXELS:
        failures.append(
            f"pink pixels {pink_px} <= {PINK_MIN_PIXELS}: the selected lens is "
            "not showing the expected pink translucent fill"
        )

    if failures:
        print("[FAIL] analytic-lens selection ghost-red-block snapshot")
        for item in failures:
            print("   -", item)
        return 1
    print(
        "[PASS] analytic-lens selection snapshot: selected DCV renders pink "
        "translucent fill with negligible red -- no ghost red block"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
