#!/usr/bin/env python3
"""Live image-snapshot regression for bugs/0047: toggling "Det" (detector
overlays) on a scene with NO detector configured must not blank the Object/Image
reference disks.

User flag (`attachment/recorded_bug_repros/flag_20260610_112814_029/`):
*"Clicking Refs show only the Object disk, click Det, Object Disk vanish, not
showing any Image Disk."* The cemented doublet is on-axis only, so its auto image
plane registers as a 1 mm "detector" while `max_real_image_height` is 0 -- the
detector coverage overlay therefore draws NOTHING, yet the old code still
suppressed the reference disks on the Det toggle, leaving the image plane empty.

This boots the real inspector (cemented doublet, rays ON, Refs ON), refreshes
with Det OFF then Det ON, and asserts -- at the live actor level and in a rendered
frame -- that the Object/Image reference-aperture disk bodies and their z~0 /
z~229 rim lines survive the Det toggle. It does NOT assert anything about the
Image disk's *size* (the 1 mm on-axis disk is a separate, open design item) --
only that the disks are not blanked.

Discriminator: a reference-aperture disk *body* carries the
`_kraken_reference_aperture_disk` actor tag (set in `open3d_scene_refresh`); a
rim is a flat polyline (lines > 0, polys == 0, thin in z) near z~0 (object) or
z~229 (image).

Run (boots its own private Xvfb if DISPLAY is unset):
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_det_mode_keeps_reference_disks

Exit: 0 = pass, 1 = regression (Det blanked the disks), 2 = environment cannot
render (no Xvfb).
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np

_VISIBLE_OPACITY = 0.01  # below this a disk body is effectively not drawn
_OBJECT_PLANE_Z = 0.0
_IMAGE_PLANE_Z = 229.0
_PLANE_TOL_MM = 6.0


def _doublet_rows():
    from KrakenOS.UI.layout_editor import SurfaceRow

    return [
        SurfaceRow(label="0", surface="Object", element="", name="Object", thickness=100.0, diameter=20.0, glass="AIR"),
        SurfaceRow(label="1", surface="Standard", element="", name="Stop", thickness=2.0, diameter=20.0, glass="AIR", rc=0.0),
        SurfaceRow(label="2", surface="Standard", element="", name="Crown front", thickness=8.0, diameter=30.0, glass="N-BK7", rc=52.46),
        SurfaceRow(label="3", surface="Standard", element="", name="Cement", thickness=0.0075, diameter=30.0, glass="N-SF2", rc=-55.46),
        SurfaceRow(label="4", surface="Standard", element="", name="Flint front", thickness=5.0, diameter=30.0, glass="F2", rc=-55.46),
        SurfaceRow(label="5", surface="Standard", element="", name="Flint back", thickness=114.0, diameter=30.0, glass="AIR", rc=-300.0),
        SurfaceRow(label="6", surface="Image", element="", name="Image", thickness=0.0, diameter=30.0, glass="AIR"),
    ]


def _disk_and_rim_counts(renderer) -> tuple[int, int, int]:
    """Return (visible reference-aperture disk bodies, rim lines near z~0, rim
    lines near z~229) currently in the renderer."""
    coll = renderer.GetViewProps()
    coll.InitTraversal()
    prop = coll.GetNextProp()
    visible_disks = 0
    rim_z0 = 0
    rim_z229 = 0
    while prop is not None:
        try:
            if prop.IsA("vtkActor"):
                if bool(getattr(prop, "_kraken_reference_aperture_disk", False)):
                    if float(prop.GetProperty().GetOpacity()) > _VISIBLE_OPACITY:
                        visible_disks += 1
                mapper = prop.GetMapper()
                data = mapper.GetInput() if mapper is not None else None
                if data is not None:
                    b = np.asarray(prop.GetBounds(), dtype=float)
                    if b.size == 6 and np.all(np.isfinite(b)):
                        zthk = float(b[5] - b[4])
                        zc = 0.5 * (b[4] + b[5])
                        if zthk < 2.0 and int(data.GetNumberOfLines()) > 0 and int(data.GetNumberOfPolys()) == 0:
                            if abs(zc - _OBJECT_PLANE_Z) < _PLANE_TOL_MM:
                                rim_z0 += 1
                            elif abs(zc - _IMAGE_PLANE_Z) < _PLANE_TOL_MM:
                                rim_z229 += 1
        except Exception:
            pass
        prop = coll.GetNextProp()
    return visible_disks, rim_z0, rim_z229


def _frame_whole_system(inspector) -> None:
    """Parallel framing of the whole doublet so both the Object plane (z=0) and
    the Image plane (z~229) are in view for the eyeball PNG."""
    cam = inspector._renderer.GetActiveCamera()
    cam.ParallelProjectionOn()
    cam.SetFocalPoint(0.0, 0.0, 114.0)
    cam.SetPosition(-197.0, 69.0, 329.0)
    cam.SetViewUp(0.15541934970884028, 0.9731788727770887, -0.16961045756791163)
    cam.SetParallelScale(135.0)
    try:
        inspector._renderer.ResetCameraClippingRange()
    except Exception:
        pass
    inspector.update_idletasks()
    inspector.update()


def _measure(out_dir: Path, app=None, inspector=None) -> dict:
    """Refresh the doublet with Det OFF then Det ON; return both disk/rim counts
    plus a Det-ON eyeball render. Reuses a provided ``(app, inspector)`` (Phase 52
    passes the shared harness inspector); otherwise boots its own."""
    from KrakenOS.UI.validate_open3d_analytic_lens_selection_snapshot import render_window_to_png

    if inspector is None:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _open_inspector

        app = KrakenLayoutEditor()
        inspector = _open_inspector(app)
    try:
        inspector.show_rays_var.set(True)
        inspector.show_rotation_handles_var.set(False)
        inspector.show_reference_surfaces_var.set(True)  # Refs ON
    except Exception:
        pass

    app.rows = _doublet_rows()
    app._sync_table()

    inspector.show_detector_overlays_var.set(False)  # Det OFF
    inspector.refresh_from_editor(force_retrace=True)
    inspector.update_idletasks()
    inspector.update()
    off = _disk_and_rim_counts(inspector._renderer)

    inspector.show_detector_overlays_var.set(True)  # Det ON -- the failing toggle
    inspector.refresh_from_editor(force_retrace=True)
    inspector.update_idletasks()
    inspector.update()
    on = _disk_and_rim_counts(inspector._renderer)

    _frame_whole_system(inspector)
    png = out_dir / "det_on_keeps_reference_disks.png"
    render_window_to_png(inspector, png)
    non_blank = False
    try:
        from PIL import Image

        arr = np.asarray(Image.open(png).convert("RGB"), dtype=float)
        non_blank = float(np.mean(np.any(arr < 250.0, axis=2))) > 0.005
    except Exception:
        non_blank = png.exists() and png.stat().st_size > 0

    return {
        "off_disks": off[0], "off_rim_z0": off[1], "off_rim_z229": off[2],
        "on_disks": on[0], "on_rim_z0": on[1], "on_rim_z229": on[2],
        "png": str(png), "non_blank": non_blank,
    }


def _evaluate(m) -> tuple[bool, list[str]]:
    """Turn raw counts into ``(passed, notes)``; notes prefixed FAIL/PASS so the
    comprehensive harness (Phase 52) can fold them in."""
    notes: list[str] = []
    notes.append(
        f"Det OFF: visible_disks={m['off_disks']} rim_z0={m['off_rim_z0']} rim_z229={m['off_rim_z229']}"
    )
    notes.append(
        f"Det ON : visible_disks={m['on_disks']} rim_z0={m['on_rim_z0']} rim_z229={m['on_rim_z229']}"
    )
    notes.append(f"rendered: {m['png']}")
    failures: list[str] = []
    # Det OFF baseline: both Object + Image reference disks present (>=2 bodies,
    # a rim at each plane) -- a sanity floor so the toggle comparison is meaningful.
    if m["off_disks"] < 2 or m["off_rim_z0"] < 1 or m["off_rim_z229"] < 1:
        failures.append(
            f"FAIL: with Det OFF the reference disks are already incomplete "
            f"(disks={m['off_disks']} rim_z0={m['off_rim_z0']} rim_z229={m['off_rim_z229']}) "
            "-- expected the Object and Image disks both drawn with Refs on"
        )
    # The bug 0047 assertion: the Det toggle must NOT blank them.
    if m["on_disks"] < 2:
        failures.append(
            f"FAIL: Det ON blanked the reference-aperture disks (visible_disks={m['on_disks']}, "
            "want >= 2) -- suppress_reference_aperture fired while the coverage overlay drew "
            "nothing (bugs/0047 regression)"
        )
    if m["on_rim_z0"] < 1:
        failures.append(
            f"FAIL: Det ON removed the Object-plane (z~0) reference rim (rim_z0={m['on_rim_z0']})"
        )
    if m["on_rim_z229"] < 1:
        failures.append(
            f"FAIL: Det ON removed the Image-plane (z~229) reference rim (rim_z229={m['on_rim_z229']})"
        )
    if not m["non_blank"]:
        failures.append(f"FAIL: Det-ON render is blank at {m['png']}")
    notes.extend(failures)
    if not failures:
        notes.append(
            "PASS: Object/Image reference disks survive the Det toggle with no detector configured"
        )
    return (not failures), notes


def run_checks(app=None, inspector=None) -> tuple[bool, list[str]]:
    """Boot (or reuse) the live inspector, toggle Det OFF->ON on the detector-less
    doublet, and assert the reference disks survive. Returns ``(passed, notes)``;
    SKIPs (passed=True with a SKIP note) when no renderer/Xvfb is available."""
    from KrakenOS.UI.validate_open3d_analytic_lens_selection_snapshot import _ensure_display

    out_dir = Path(os.environ.get("KRAKEN_SNAPSHOT_DIR", "/tmp/kraken_det_reference_disks"))
    out_dir.mkdir(parents=True, exist_ok=True)
    xvfb_proc = None
    if inspector is None:
        xvfb_proc, env_err = _ensure_display()
        if env_err is not None:
            return True, [f"SKIP: cannot render snapshot: {env_err}"]
    try:
        m = _measure(out_dir, app=app, inspector=inspector)
    except Exception as exc:  # a render crash is a real failure, not a skip
        return False, [f"FAIL: live Det-toggle render raised: {exc!r}"]
    finally:
        if xvfb_proc is not None:
            xvfb_proc.terminate()
            try:
                xvfb_proc.wait(timeout=5)
            except Exception:
                xvfb_proc.kill()
    return _evaluate(m)


def main() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    if not passed:
        print("[FAIL] Det toggle blanked the reference disks (bugs/0047)")
        return 1
    if any(n.startswith("SKIP") for n in notes):
        return 2
    print("[PASS] reference disks survive the Det toggle with no detector configured")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
