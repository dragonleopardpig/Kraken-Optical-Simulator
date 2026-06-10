#!/usr/bin/env python3
"""Live regression for bugs/0048: orbiting/zooming the Open-3D view right after
startup must not clip the converging ray cone / image plane.

User flag (`attachment/recorded_bug_repros/flag_20260610_130912_090/` and the two
earlier frames 130839 / 130854): *"first view ... second view, it starts clipping
... 3rd view, clipped."* The user noted the clip happens **right after Open-3D
startup** when orbiting/zooming, but **never after first clicking a cardinal
preset** (XZ / YZ / ...).

Root cause: the "Iso" view used PERSPECTIVE projection (the else-branch of
`set_camera_preset` set no parallel_scale), while every cardinal preset is
PARALLEL. A perspective camera sits a finite distance from the scene, so an orbit
swings the far geometry (image plane at z~229 and the converging cone tip) BEHIND
the camera, where the clamped-positive near clip plane slices it off. Parallel
projection renders behind-camera geometry and makes the camera distance visually
irrelevant -- which is exactly why the cardinal presets never clip.

This guard boots the cemented doublet (rays ON, refs ON) and asserts:

  (A) ROOT CAUSE -- `set_camera_preset("iso")` yields an ORTHOGRAPHIC camera
      (`GetParallelProjection() == 1`), like the cardinal presets. A revert to
      perspective fails here.
  (B) NO CLIP ON ORBIT -- after an azimuth/elevation orbit, all 8 corners of the
      complete scene bounding box stay at a positive signed view-distance (the
      whole scene is in front of the camera, so nothing is near-clipped).
  (C) BACKSTOP IS FREE -- `_ensure_parallel_camera_clears_scene` may dolly the
      camera back but leaves `parallel_scale` unchanged (zero visual change).
  (D) IMAGE SNAPSHOT -- renders the fixed iso+orbit view and, for contrast, the
      exact recorded perspective bug camera; samples the projected image-plane
      patch in each. The fixed (parallel) frame draws the image-plane geometry
      that the buggy (perspective) frame clips away. Both PNGs are eyeballed.

Run (boots its own private Xvfb if DISPLAY is unset):
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_camera_iso_orbit_no_clip

Exit: 0 = pass, 1 = regression (clip / perspective iso), 2 = cannot render.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np

# The exact camera recorded in the "3rd view, clipped" bug bundle
# (attachment/recorded_bug_repros/flag_20260610_130912_090/state.json).
_BUG_CAM_POS = (-35.20184990789909, 28.932495688078973, 155.25037769579677)
_BUG_CAM_FOCAL = (0.0, 0.0, 107.50375)
_BUG_CAM_VIEWUP = (0.0, 1.0, 0.0)
_BUG_CAM_PSCALE = 61.519473040485096

_IMAGE_PLANE = (0.0, 0.0, 229.0075)
_CONE_TIP = (0.0, 0.0, 200.0)  # converging cone, well past the lens (z~115)
_PATCH = 18  # half-size of the display patch sampled around a projected point


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


def _signed_view_distance(cam, world) -> float:
    pos = np.asarray(cam.GetPosition(), float)
    foc = np.asarray(cam.GetFocalPoint(), float)
    n = foc - pos
    norm = float(np.linalg.norm(n))
    if norm < 1e-9:
        return 0.0
    n = n / norm
    return float(np.dot(np.asarray(world, float) - pos, n))


def _scene_corners(bounds: np.ndarray) -> np.ndarray:
    return np.array(
        [(bounds[i], bounds[j], bounds[k]) for i in (0, 1) for j in (2, 3) for k in (4, 5)],
        dtype=float,
    )


def _patch_coverage(renderer, png_path, world) -> float:
    """Project ``world`` to display coords with this renderer's own camera and
    return the fraction of non-white pixels in a patch around it. Projection-aware,
    so it is a fair comparison between a parallel and a perspective frame."""
    try:
        from PIL import Image
    except Exception:
        return 0.0
    try:
        renderer.SetWorldPoint(float(world[0]), float(world[1]), float(world[2]), 1.0)
        renderer.WorldToDisplay()
        dx, dy, _dz = renderer.GetDisplayPoint()
    except Exception:
        return 0.0
    arr = np.asarray(Image.open(png_path).convert("RGB"), dtype=int)
    h, w = arr.shape[:2]
    # VTK display y is bottom-up; image rows are top-down.
    px = int(round(dx))
    py = int(round(h - 1 - dy))
    x0, x1 = max(0, px - _PATCH), min(w, px + _PATCH + 1)
    y0, y1 = max(0, py - _PATCH), min(h, py + _PATCH + 1)
    if x0 >= x1 or y0 >= y1:
        return 0.0
    patch = arr[y0:y1, x0:x1]
    non_white = np.any(patch < 250, axis=2)
    return float(np.mean(non_white))


def _measure(out_dir: Path, app=None, inspector=None) -> dict:
    from KrakenOS.UI.validate_open3d_analytic_lens_selection_snapshot import render_window_to_png

    if inspector is None:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _open_inspector

        app = KrakenLayoutEditor()
        inspector = _open_inspector(app)
    try:
        inspector.show_rays_var.set(True)
        inspector.show_rotation_handles_var.set(False)
        inspector.show_reference_surfaces_var.set(True)
        inspector.show_detector_overlays_var.set(False)
    except Exception:
        pass

    app.rows = _doublet_rows()
    app._sync_table()
    inspector.refresh_from_editor(force_retrace=True)
    inspector.update_idletasks()
    try:
        inspector._trace_live_now()
    except Exception:
        pass
    inspector.update_idletasks()
    inspector.update()

    renderer = inspector._renderer
    cam = renderer.GetActiveCamera()

    # (A) Iso preset must be orthographic.
    inspector.set_camera_preset("iso")
    inspector.update_idletasks()
    inspector.update()
    iso_parallel = int(cam.GetParallelProjection())
    pscale_after_iso = float(cam.GetParallelScale())

    # The complete-scene bounding box (no guides/axis) for the corner test.
    bounds = inspector._visible_actor_bounds(include_guides=False)
    corners = _scene_corners(np.asarray(bounds, float)) if bounds is not None else np.empty((0, 3))

    # (B) Orbit like the user did right after startup, running the same backstop
    # the live interactor fires, then check the whole scene stays in front.
    for _ in range(8):
        cam.Azimuth(4.0)
        cam.Elevation(1.5)
        cam.OrthogonalizeViewUp()
        inspector._on_camera_interaction()
    inspector.update_idletasks()
    inspector.update()
    min_corner_signed = float(min((_signed_view_distance(cam, c) for c in corners), default=-1.0))
    image_signed_fixed = _signed_view_distance(cam, _IMAGE_PLANE)

    # (C) Backstop is visually free: a direct call must not change parallel_scale.
    pscale_before_backstop = float(cam.GetParallelScale())
    moved = bool(inspector._ensure_parallel_camera_clears_scene())
    pscale_after_backstop = float(cam.GetParallelScale())

    fixed_png = out_dir / "iso_orbit_fixed.png"
    render_window_to_png(inspector, fixed_png)
    fixed_image_patch = _patch_coverage(renderer, fixed_png, _IMAGE_PLANE)
    fixed_tip_patch = _patch_coverage(renderer, fixed_png, _CONE_TIP)

    # (D) Reproduce the exact recorded perspective bug camera for contrast.
    cam.SetParallelProjection(0)
    cam.SetFocalPoint(*_BUG_CAM_FOCAL)
    cam.SetViewUp(*_BUG_CAM_VIEWUP)
    cam.SetPosition(*_BUG_CAM_POS)
    cam.SetParallelScale(_BUG_CAM_PSCALE)
    try:
        inspector._reset_camera_clipping_range_for_scene()
    except Exception:
        pass
    inspector.update_idletasks()
    inspector.update()
    image_signed_bug = _signed_view_distance(cam, _IMAGE_PLANE)
    buggy_png = out_dir / "iso_orbit_buggy_perspective.png"
    render_window_to_png(inspector, buggy_png)
    buggy_image_patch = _patch_coverage(renderer, buggy_png, _IMAGE_PLANE)
    buggy_tip_patch = _patch_coverage(renderer, buggy_png, _CONE_TIP)

    return {
        "iso_parallel": iso_parallel,
        "pscale_after_iso": round(pscale_after_iso, 3),
        "n_corners": int(len(corners)),
        "min_corner_signed": round(min_corner_signed, 2),
        "image_signed_fixed": round(image_signed_fixed, 2),
        "image_signed_bug": round(image_signed_bug, 2),
        "backstop_moved": moved,
        "pscale_before_backstop": round(pscale_before_backstop, 4),
        "pscale_after_backstop": round(pscale_after_backstop, 4),
        "fixed_image_patch": round(fixed_image_patch, 4),
        "fixed_tip_patch": round(fixed_tip_patch, 4),
        "buggy_image_patch": round(buggy_image_patch, 4),
        "buggy_tip_patch": round(buggy_tip_patch, 4),
        "fixed_png": str(fixed_png),
        "buggy_png": str(buggy_png),
    }


def _evaluate(m) -> tuple[bool, list[str]]:
    notes: list[str] = []
    notes.append(f"iso parallel_projection={m['iso_parallel']} parallel_scale={m['pscale_after_iso']}")
    notes.append(
        f"after orbit: min scene-corner signed view-dist={m['min_corner_signed']} "
        f"(n={m['n_corners']}), image-plane signed={m['image_signed_fixed']}"
    )
    notes.append(
        f"backstop: moved={m['backstop_moved']} parallel_scale {m['pscale_before_backstop']}->"
        f"{m['pscale_after_backstop']}"
    )
    notes.append(
        f"image-plane patch (fixed/buggy)={m['fixed_image_patch']}/{m['buggy_image_patch']}  "
        f"cone-tip patch (fixed/buggy)={m['fixed_tip_patch']}/{m['buggy_tip_patch']}  "
        f"[bug image signed={m['image_signed_bug']}]"
    )
    notes.append(f"rendered: {m['fixed_png']} ; {m['buggy_png']}")

    failures: list[str] = []
    # (A) root cause: iso must be orthographic.
    if m["iso_parallel"] != 1:
        failures.append(
            "FAIL: set_camera_preset('iso') produced a PERSPECTIVE camera "
            "(parallel_projection=0) -- the Iso view must be orthographic like the "
            "cardinal presets or an orbit will clip the far cone (bugs/0048 regression)"
        )
    # (B) no clip: whole scene in front of the camera after orbiting.
    if m["n_corners"] != 8:
        failures.append(f"FAIL: could not read the complete scene bounds (n_corners={m['n_corners']})")
    elif m["min_corner_signed"] <= 0.0:
        failures.append(
            f"FAIL: after orbit a scene corner is BEHIND the camera "
            f"(min signed view-dist={m['min_corner_signed']} <= 0) -- it would be "
            "near-clipped (bugs/0048 regression)"
        )
    if m["image_signed_fixed"] <= 0.0:
        failures.append(
            f"FAIL: after orbit the image plane (z~229) is behind the camera "
            f"(signed={m['image_signed_fixed']}) -- clipped"
        )
    # (C) backstop must not change the parallel zoom.
    if abs(m["pscale_after_backstop"] - m["pscale_before_backstop"]) > 1e-3:
        failures.append(
            f"FAIL: clear-scene backstop changed parallel_scale "
            f"{m['pscale_before_backstop']}->{m['pscale_after_backstop']} (should be visually free)"
        )
    # (D) snapshot discriminator: the fixed frame draws the image-plane region the
    # buggy perspective frame clips. Sanity: the recorded bug camera really clips
    # (image plane behind it), and the fixed frame really keeps it in front.
    if m["image_signed_bug"] >= 0.0:
        failures.append(
            f"FAIL: the recorded perspective bug camera no longer reproduces the clip "
            f"(image signed={m['image_signed_bug']}, expected < 0) -- snapshot contrast is moot"
        )
    if m["fixed_image_patch"] <= m["buggy_image_patch"]:
        failures.append(
            f"FAIL: the fixed iso frame does not show more image-plane geometry than the "
            f"clipped perspective frame (fixed={m['fixed_image_patch']} <= buggy={m['buggy_image_patch']})"
        )

    notes.extend(failures)
    if not failures:
        notes.append(
            "PASS: Iso is orthographic; orbit keeps the whole scene in front of the camera; "
            "the converging cone / image plane never clip (bugs/0048)"
        )
    return (not failures), notes


def run_checks(app=None, inspector=None) -> tuple[bool, list[str]]:
    """Boot (or reuse) the live inspector, assert Iso is orthographic and an orbit
    never clips the far scene. Returns ``(passed, notes)``; SKIPs (passed=True with
    a SKIP note) when no renderer/Xvfb is available."""
    from KrakenOS.UI.validate_open3d_analytic_lens_selection_snapshot import _ensure_display

    out_dir = Path(os.environ.get("KRAKEN_SNAPSHOT_DIR", "/tmp/kraken_iso_orbit_no_clip"))
    out_dir.mkdir(parents=True, exist_ok=True)
    xvfb_proc = None
    if inspector is None:
        xvfb_proc, env_err = _ensure_display()
        if env_err is not None:
            return True, [f"SKIP: cannot render snapshot: {env_err}"]
    try:
        m = _measure(out_dir, app=app, inspector=inspector)
    except Exception as exc:
        return False, [f"FAIL: live iso-orbit clip guard raised: {exc!r}"]
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
        print("[FAIL] Iso orbit clips the far cone / image plane (bugs/0048)")
        return 1
    if any(n.startswith("SKIP") for n in notes):
        return 2
    print("[PASS] Iso is orthographic; orbit/zoom never clip the converging cone (bugs/0048)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
