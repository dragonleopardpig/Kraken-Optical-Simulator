"""Image-snapshot guarantee for bugs/0008: a bare Delete/BackSpace in the Open
3D view must not erase the imported optical lens when nothing is selected.

Boots its own Xvfb (when ``DISPLAY`` is unset), builds the flag-341 layout (a
clean Object + Image chain with a STEP optical overlay), and renders three
frames of the *real* inspector:

  A. lens present, nothing selected  -> baseline foreground pixels
  B. after ``delete_selected_step`` with nothing selected (the bug trigger)
  C. after selecting the overlay, then ``delete_selected_step`` (legit delete)

The fix means frame B keeps the lens (B ~= A) while frame C removes it
(C << A). The pixel ratios are self-calibrating -- no absolute thresholds that
drift across environments -- and frame C doubles as proof that the metric can
actually detect a disappearance (so "B keeps the lens" has teeth) and that a
genuinely selected delete still works.

Run from the repository root:

    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_step_delete_requires_selection_snapshot
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from KrakenOS.UI.services.prism_fixtures import PRISM_42779_STEP
from KrakenOS.UI.validate_open3d_analytic_lens_selection_snapshot import (
    _ensure_display,
    render_window_to_png,
)


def _foreground_pixels(png_path: "str | Path") -> int:
    """Count rendered (non-background) pixels in a captured frame.

    Background is the median of the four corners; any pixel that differs from it
    by more than a small Euclidean margin counts as scene content (lens body,
    optical axis, dimensions, gizmo, orientation widget). The lens body is by far
    the largest filled silhouette, so its removal dominates the count.
    """
    import numpy as np
    from PIL import Image

    arr = np.asarray(Image.open(png_path).convert("RGB")).astype(int)
    h, w = arr.shape[:2]
    k = 12
    corners = np.concatenate(
        [
            arr[:k, :k].reshape(-1, 3),
            arr[:k, w - k:].reshape(-1, 3),
            arr[h - k:, :k].reshape(-1, 3),
            arr[h - k:, w - k:].reshape(-1, 3),
        ]
    )
    bg = np.median(corners, axis=0)
    dist = np.sqrt(((arr - bg) ** 2).sum(axis=2))
    return int((dist > 45).sum())


def _build_and_capture(out_dir: Path) -> "tuple[dict | None, str]":
    # Imported after DISPLAY is guaranteed -- constructing Tk needs an X server.
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor, SurfaceRow
    from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import (
        _open_inspector,
        _import_step,
    )

    if not PRISM_42779_STEP.exists():
        return None, f"STEP fixture missing: {PRISM_42779_STEP}"

    app = KrakenLayoutEditor()
    inspector = _open_inspector(app)
    app.rows = [
        SurfaceRow(label="0", surface="Object", element="", name="Object",
                   thickness=100.0, diameter=25.0, glass="AIR"),
        SurfaceRow(label="1", surface="Image", element="", name="Image",
                   thickness=0.0, diameter=25.0, glass="AIR"),
    ]
    app._sync_table()
    try:
        app.clear_step_imports()
    except Exception:
        pass

    _import_step(app, PRISM_42779_STEP)
    try:
        inspector.show_rays_var.set(False)
    except Exception:
        pass
    inspector.refresh_from_editor(force_retrace=False)
    inspector.update_idletasks()

    def _deselect() -> None:
        try:
            inspector._clear_open3d_selection()
        except Exception:
            pass
        app._selected_step_label = None
        inspector._step_rotation_active_label = None
        inspector._step_carry_active_label = None
        inspector._picked_row_index = None
        inspector._stl_placement_row_index = None
        inspector._row_carry_hold_candidate_index = None

    def _refresh() -> None:
        inspector.refresh_from_editor(force_retrace=False)
        inspector.update_idletasks()
        inspector.update()

    # Frame A: lens present, nothing selected.
    _deselect()
    _refresh()
    frame_a = out_dir / "a_present_deselected.png"
    render_window_to_png(inspector, frame_a)

    # Frame B: the bug trigger -- delete with nothing selected.
    _deselect()
    inspector.delete_selected_step()
    _refresh()
    frame_b = out_dir / "b_after_unselected_delete.png"
    render_window_to_png(inspector, frame_b)
    path_after_unselected = app.imported_optical_step_path

    # Frame C: select the overlay, then delete (legit removal / positive control).
    app.select_step_component("optical")
    _refresh()
    inspector.delete_selected_step()
    _refresh()
    frame_c = out_dir / "c_after_selected_delete.png"
    render_window_to_png(inspector, frame_c)
    path_after_selected = app.imported_optical_step_path

    try:
        if app._three_d_inspector is not None:
            app._three_d_inspector._on_close()
    except Exception:
        pass
    try:
        app.destroy()
    except Exception:
        pass

    return (
        {
            "frame_a": frame_a,
            "frame_b": frame_b,
            "frame_c": frame_c,
            "path_after_unselected": path_after_unselected,
            "path_after_selected": path_after_selected,
        },
        "rendered prism 42779 optical overlay across delete states",
    )


def main() -> int:
    out_dir = Path(os.environ.get("KRAKEN_SNAPSHOT_DIR", "/tmp/kraken-step-delete-snapshot"))
    out_dir.mkdir(parents=True, exist_ok=True)

    xvfb_proc, env_err = _ensure_display()
    if env_err is not None:
        print(f"[SKIP] cannot render snapshot: {env_err}")
        return 2
    try:
        result, message = _build_and_capture(out_dir)
    finally:
        if xvfb_proc is not None:
            xvfb_proc.terminate()
            try:
                xvfb_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                xvfb_proc.kill()

    if result is None:
        print(f"[SKIP] {message}")
        return 2

    n_present = _foreground_pixels(result["frame_a"])
    n_after = _foreground_pixels(result["frame_b"])
    n_removed = _foreground_pixels(result["frame_c"])

    print(f"snapshot dir: {out_dir}")
    print(f"  {message}")
    print(f"  A present(deselected)   foreground = {n_present:6d}  {result['frame_a'].name}")
    print(f"  B after unselected del   foreground = {n_after:6d}  {result['frame_b'].name}")
    print(f"  C after selected delete  foreground = {n_removed:6d}  {result['frame_c'].name}")
    print(f"  path after unselected delete = {result['path_after_unselected']!r}")
    print(f"  path after selected delete   = {result['path_after_selected']!r}")

    failures: list[str] = []

    # The lens must actually have rendered, or the comparison is meaningless.
    if n_present < 1500:
        print(f"[SKIP] baseline lens body too small to judge (foreground={n_present}); fixture may not have framed.")
        return 2

    # PRIMARY fix proof (state level): an unselected delete leaves the import.
    if result["path_after_unselected"] is None:
        failures.append("unselected Delete cleared imported_optical_step_path (the lens was deleted with nothing selected)")
    if result["path_after_selected"] is not None:
        failures.append("selected Delete did not clear the overlay (legit delete regressed)")

    # Pixel proof: B keeps the lens (B ~= A); C removes it (C << A); clear gap.
    if n_after < 0.85 * n_present:
        failures.append(f"frame B lost lens pixels after an unselected delete: {n_after} < 0.85*{n_present}")
    if n_removed > 0.55 * n_present:
        failures.append(f"frame C still shows lens pixels after a selected delete: {n_removed} > 0.55*{n_present}")
    if n_after < 1.5 * max(n_removed, 1):
        failures.append(f"frames B/C not clearly separated: B={n_after} not >= 1.5*C={n_removed}")

    if failures:
        print("Open 3D STEP delete-requires-selection snapshot FAILED:")
        for detail in failures:
            print(f"- {detail}")
        return 1

    print("Open 3D STEP delete-requires-selection snapshot passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
