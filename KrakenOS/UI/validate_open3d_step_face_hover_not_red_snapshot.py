#!/usr/bin/env python3
"""Image-snapshot regression test for bugs/0005: hovering an imported STEP face
must NOT paint a red highlight ("ghost red edges").

Why pixels and not a vtkProperty assertion: the property contract lives in
``validate_open3d_step_face_hover_not_red`` (the hover style is gold, not red).
But the *symptom* the user saw is a rendered one -- a lens viewed edge-on turns
a face outline into a vertical line, so the old red highlight became a thick red
bar straight through the glass. Only a rendered image proves the highlight no
longer reads as red, and that it is still visible at all. This boots the real
inspector, imports a lens STEP, and for every face renders the mouse-over
highlight off-screen, then checks:

  * the hover frame adds no meaningful red over the no-hover baseline
    (red stays at the handful of pixels in the X-axis origin marker), and
  * at least one face's highlight visibly changes the frame (the gold tint is
    actually drawn -- the test would otherwise pass trivially if hover did
    nothing).

Run (boots its own private Xvfb if DISPLAY is unset):
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_step_face_hover_not_red_snapshot

Exit: 0 = pass, 1 = regression (red highlight / no visible highlight),
      2 = environment can't render (no Xvfb, no lens fixture).
"""
from __future__ import annotations

import os
from pathlib import Path

from KrakenOS.UI.validate_open3d_analytic_lens_selection_snapshot import (
    _ensure_display,
    render_window_to_png,
)

# A red highlight bar was hundreds-plus pixels; the only red left in a clean
# frame is the ~9-pixel X-axis origin marker. 80 separates the two by an order
# of magnitude (matches the sibling 0002 snapshot threshold).
RED_MAX_PIXELS = 80
# At least one face's hover must change this many pixels vs the no-hover frame,
# proving the gold highlight actually renders (post-fix the rim face changed
# ~1600 px and the caps ~700; 120 is a safe floor across fixtures).
MIN_HIGHLIGHT_CHANGED = 120


def _load_rgb(png_path: "str | Path"):
    import numpy as np
    from PIL import Image

    return np.asarray(Image.open(png_path).convert("RGB")).astype(int)


def count_red(arr) -> int:
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    return int(((r > 120) & (g < 70) & (b < 70)).sum())


def changed_pixels(arr, baseline) -> int:
    import numpy as np

    return int((np.abs(arr - baseline).sum(axis=2) > 30).sum())


def _render_face_hovers(out_dir: Path) -> "tuple[dict | None, str]":
    """Boot the inspector, import the first available lens STEP, and render the
    no-hover baseline plus one hover frame per face.

    Returns (metrics, message). metrics is None on an environment skip.
    """
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor, SurfaceRow
    from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import (
        _open_inspector,
        _import_step,
        LENS_FIXTURES,
    )

    if not LENS_FIXTURES:
        return None, "no lens STEP fixtures checked out under attachment/Lens/"

    app = KrakenLayoutEditor()
    inspector = _open_inspector(app)
    # Gizmo OFF so no Move/Rotate handles are armed by selection -- we want to
    # isolate the face hover highlight, nothing else.
    try:
        inspector.show_rotation_handles_var.set(False)
    except Exception:
        pass
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

    chosen = None
    faces: list = []
    for fixture in LENS_FIXTURES:
        try:
            app.clear_step_imports()
        except Exception:
            pass
        _import_step(app, fixture["step"])
        inspector.refresh_from_editor(force_retrace=False)
        inspector.update_idletasks()
        meta = app._step_overlay_face_metadata("optical")
        faces = list(meta.get("faces", []) or []) if isinstance(meta, dict) else []
        if faces:
            chosen = fixture
            break
    if chosen is None:
        return None, "no imported STEP produced pickable faces"

    try:
        inspector.show_rays_var.set(False)
    except Exception:
        pass
    inspector.refresh_from_editor(force_retrace=False)
    inspector.update_idletasks()
    inspector.update()

    inspector._set_step_hover_outline(None, None, render=True)
    inspector.update_idletasks(); inspector.update()
    base_png = out_dir / "step_face_hover_baseline.png"
    render_window_to_png(inspector, base_png)
    baseline = _load_rgb(base_png)
    base_red = count_red(baseline)

    per_face = []
    worst_red = base_red
    best_changed = 0
    for i, face in enumerate(faces):
        fid = str(face.get("face_id", f"#{i}")).replace("/", "_")
        inspector._set_step_hover_outline(None, None, render=False)
        overlay = inspector._hover_overlay_for_step_face("optical", face)
        inspector._set_step_hover_outline(overlay, f"snap{i}", render=True)
        inspector.update_idletasks(); inspector.update()
        png = out_dir / f"step_face_hover_{fid}.png"
        render_window_to_png(inspector, png)
        arr = _load_rgb(png)
        red = count_red(arr)
        changed = changed_pixels(arr, baseline)
        per_face.append({"face": fid, "png": str(png), "red": red, "changed": changed})
        worst_red = max(worst_red, red)
        best_changed = max(best_changed, changed)

    metrics = {
        "fixture": chosen["name"],
        "baseline_red": base_red,
        "worst_red": worst_red,
        "best_changed": best_changed,
        "per_face": per_face,
    }
    return metrics, f"rendered {len(faces)} face hovers on {chosen['name']}"


def main() -> int:
    out_dir = Path(os.environ.get("KRAKEN_SNAPSHOT_DIR", "/tmp/kraken_face_hover_snapshot"))
    out_dir.mkdir(parents=True, exist_ok=True)

    xvfb_proc, env_err = _ensure_display()
    if env_err is not None:
        print(f"[SKIP] cannot render snapshot: {env_err}")
        return 2
    try:
        metrics, message = _render_face_hovers(out_dir)
    finally:
        if xvfb_proc is not None:
            xvfb_proc.terminate()
            try:
                xvfb_proc.wait(timeout=5)
            except Exception:
                xvfb_proc.kill()

    if metrics is None:
        print(f"[SKIP] {message}")
        return 2

    print(f"snapshot dir: {out_dir}")
    print(f"  {message}")
    print(f"  baseline red    = {metrics['baseline_red']:5d}")
    print(f"  worst hover red = {metrics['worst_red']:5d} (limit < {RED_MAX_PIXELS})")
    print(f"  best  changed   = {metrics['best_changed']:5d} (need  > {MIN_HIGHLIGHT_CHANGED})")
    for row in metrics["per_face"]:
        print(f"    face {row['face']:>10s}: red={row['red']:5d} changed={row['changed']:6d}  {row['png']}")

    failures: list[str] = []
    if metrics["worst_red"] >= RED_MAX_PIXELS:
        failures.append(
            f"hover red pixels {metrics['worst_red']} >= {RED_MAX_PIXELS}: a face "
            "hover is painting a red highlight (bugs/0005 'ghost red edges' regression)"
        )
    if metrics["best_changed"] <= MIN_HIGHLIGHT_CHANGED:
        failures.append(
            f"best hover change {metrics['best_changed']} <= {MIN_HIGHLIGHT_CHANGED}: the "
            "face hover highlight is not visibly rendering at all"
        )

    if failures:
        print("[FAIL] STEP face-hover ghost-red snapshot")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] STEP face-hover highlight renders gold, adds no red")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
