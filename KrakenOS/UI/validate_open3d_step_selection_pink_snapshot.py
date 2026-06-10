#!/usr/bin/env python3
"""Image-snapshot regression for bugs/0051: a selected imported STEP overlay
must read as the app-wide pink translucent "selected" body, NOT a muddy orange
blob.

The old `_set_step_actor_selected` painted orange per-triangle edges
(1.0, 0.48, 0.0) over the dense CAD tessellation with no body-fill change. On
the warm glass palette that read as a flat, low-contrast orange shape ("why is
this STEP orange, different from the rest? the edge has no contrast"). The fix
suppresses the triangle wireframe and fills the body pink (1.0, 0.45, 0.65) --
the same selection idiom promoted rows / optical solids already use
(bugs/0001-0003).

Like the analytic-lens snapshot, this inspects PIXELS, not vtkProperties: it
renders the STEP overlay unselected then selected (off-screen, needs an X
server) and asserts the selection introduces a body-sized region of pink that
was not there unselected.

Run (boots its own private Xvfb if DISPLAY is unset):
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_step_selection_pink_snapshot

Exit: 0 = pass, 1 = regression (no pink selection fill), 2 = environment can't
      render (no Xvfb) or fixture missing.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from KrakenOS.UI.validate_open3d_analytic_lens_selection_snapshot import (
    _ensure_display,
    classify_red_pink,
    render_window_to_png,
)

# The selected STEP body fill (255,115,166) lights up the shared pink
# classifier. Calibrated on the post-fix render: the translucent prism overlay
# (opacity ~0.65) gives selected~194 pink px vs unselected~4. A regression to
# the old orange edge-only style would leave the pink count at the unselected
# baseline, so the threshold sits well clear of both.
PINK_MIN_SELECTED = 100
PINK_MAX_UNSELECTED = 50


def main() -> int:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor, SurfaceRow
    from KrakenOS.UI.services.prism_fixtures import PRISM_42779_STEP
    from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import (
        _import_step,
        _open_inspector,
    )

    if not PRISM_42779_STEP.exists():
        print(f"[SKIP] STEP fixture missing: {PRISM_42779_STEP}")
        return 2
    xvfb, err = _ensure_display()
    if err is not None:
        print(f"[SKIP] cannot boot inspector: {err}")
        return 2

    try:
        app = KrakenLayoutEditor()
        inspector = _open_inspector(app)
        for var in ("show_rotation_handles_var", "show_rays_var"):
            try:
                getattr(inspector, var).set(False)
            except Exception:
                pass
        app.rows = [
            SurfaceRow(label="0", surface="Object", element="", name="Object",
                       thickness=50.0, diameter=25.0, glass="AIR"),
            SurfaceRow(label="1", surface="Image", element="", name="Image",
                       thickness=0.0, diameter=25.0, glass="AIR"),
        ]
        app._sync_table()
        _import_step(app, PRISM_42779_STEP)
        inspector.refresh_from_editor(force_retrace=False)
        inspector.update_idletasks()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            inspector._selection_representation.apply_step_selection(None)
            inspector.update_idletasks()
            render_window_to_png(inspector, tmp_path / "unselected.png")
            _red_u, pink_u = classify_red_pink(tmp_path / "unselected.png")

            inspector._selection_representation.apply_step_selection("optical")
            inspector.update_idletasks()
            render_window_to_png(inspector, tmp_path / "selected.png")
            _red_s, pink_s = classify_red_pink(tmp_path / "selected.png")
    finally:
        if xvfb is not None:
            xvfb.terminate()

    print(f"STEP overlay pink fill: unselected={pink_u} selected={pink_s}")
    failures: list[str] = []
    if pink_u > PINK_MAX_UNSELECTED:
        failures.append(
            f"unselected STEP already shows {pink_u} pink px (> {PINK_MAX_UNSELECTED}); "
            "selection fill is not distinct from the resting state"
        )
    if pink_s < PINK_MIN_SELECTED:
        failures.append(
            f"selected STEP shows only {pink_s} pink px (< {PINK_MIN_SELECTED}); "
            "the bugs/0051 pink selection fill is missing (regressed to orange/edge-only?)"
        )
    if pink_s <= pink_u:
        failures.append(
            f"selection did not add pink fill (selected={pink_s} <= unselected={pink_u})"
        )
    if failures:
        for message in failures:
            print(f"[FAIL] {message}")
        return 1
    print("STEP selection pink-fill snapshot validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
