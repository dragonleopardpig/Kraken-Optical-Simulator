#!/usr/bin/env python3
"""Image-snapshot regression for the promoted-row / analytic-row slide gap
readout (requests #65 + #66).

#66: dragging a row in "Slide along axis" mode used to show NO live gap
dimension -- the body's refresh is debounced, so ``_apply_axis_slide_drag_motion``
mutated the model thickness every frame but drew nothing. The fix wires
``_update_axis_slide_gap_overlay`` into the motion handler: it anchors the gap
arrow's far end to the previous *visible* component (static during the drag) and
places the near end exactly the live model gap (``preceding_thickness_after``)
along the axis, then issues the one render that makes the moving dimension show.

#65: that gap readout is drawn THICK and EMERALD GREEN (0.10, 0.90, 0.45),
deliberately distinct from the optical axis (blue 0,0.43,0.88) and the
highlighted optical axis (gold 1.0,0.68,0.05) it used to collide with.

This boots the real inspector (own Xvfb), loads the 5-penta cascade so a slid
element has a real body in front of it, runs a slide-along-axis drag, and
asserts:
  * the drag now produces transient gap actors (the #66 overlay appears);
  * the arrow mesh is emerald and the leaders are drawn thick (#65);
  * none of the gap actors reuse the optical-axis blue or highlight gold;
  * the overlay is cleared on release.
A PNG is written for eyeballing (per bugs/README: a count is not the whole story).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_axis_slide_gap_overlay_snapshot

Exit: 0 = pass, 1 = regression, 2 = environment can't render / fixture missing.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np

from KrakenOS.UI.validate_open3d_analytic_lens_selection_snapshot import (
    _ensure_display,
    render_window_to_png,
)
from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import (
    PENTA_CASCADE_PATH,
    _open_inspector,
)
from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.render_layout_snapshot import _load_layout_module, _rows_from_layout_info

EMERALD = (0.10, 0.90, 0.45)
LEADER_GREEN = (0.50, 0.95, 0.68)
AXIS_BLUE = (0.0, 0.43, 0.88)
HIGHLIGHT_GOLD = (1.0, 0.68, 0.05)
COLOR_TOL = 0.08


def _close(a, b, tol: float = COLOR_TOL) -> bool:
    return all(abs(float(x) - float(y)) <= tol for x, y in zip(a, b))


def _actor_color(actor):
    try:
        return tuple(float(c) for c in actor.GetProperty().GetColor())
    except Exception:
        return None


def _actor_line_width(actor) -> float:
    try:
        return float(actor.GetProperty().GetLineWidth())
    except Exception:
        return 0.0


def _candidate_rows(insp, app):
    """Body rows that can be slid: a valid lens group with a preceding and a
    trailing row to absorb the slide. The first element only has the body-less
    Object before it, so its gap overlay is legitimately empty -- we let the
    caller skip past such rows by trying each until one draws an overlay."""
    rows = []
    for index in sorted((insp._row_actor_map or {}).keys()):
        group = app._lens_row_group_for_row(index)
        if not group or group[0] - 1 < 0 or group[-1] + 1 >= len(app.rows):
            continue
        rows.append((index, list(group)))
    return rows


def main() -> int:
    if not PENTA_CASCADE_PATH.exists():
        print(f"SKIP: cascade fixture missing: {PENTA_CASCADE_PATH}")
        return 2
    if not _ensure_display():
        print("SKIP: no usable display (Xvfb) for rendering")
        return 2

    app = KrakenLayoutEditor()
    try:
        insp = _open_inspector(app)
        module = _load_layout_module(PENTA_CASCADE_PATH)
        app.rows = _rows_from_layout_info({"surfaces": list(getattr(module, "SURFACES", []) or [])})
        app._apply_layout_settings(dict(getattr(module, "SETTINGS", {}) or {}))
        # Flatten the penta fold (zero tilts/desp) so the prism bodies lie in
        # optical order along world +Z, and open positive air gaps so a slide
        # has room. This exercises the shared slide-along-axis handler on a
        # straight axis -- the common #66 case -- instead of the folded cascade.
        for index, row in enumerate(app.rows):
            row.tilt_x = row.tilt_y = row.tilt_z = 0.0
            row.desp_x = row.desp_y = row.desp_z = 0.0
            row.axis_move = 0.0
            if index < len(app.rows) - 1:
                row.thickness = 25.0
        app._sync_table()
        insp.refresh_from_editor(force_retrace=True)
        insp.update_idletasks()

        insp.slide_along_axis_mode_var.set(True)
        insp.update_idletasks()
        if not insp._axis_slide_mode_active():
            print("SKIP: slide-along-axis mode refused to engage")
            return 2

        # Find a row whose slide actually has a previous *visible* component to
        # measure against (the first element only has the body-less Object
        # before it, so its gap overlay is legitimately empty).
        failures: list[str] = []
        used_target = None
        actors = []
        ppx = insp._placement_drag_pixels_per_step()
        for target, group in _candidate_rows(insp, app):
            actor = None
            for key in dict.fromkeys(insp._row_actor_map.get(target, []) or []):
                actor = insp._actor_by_key.get(key)
                if actor is not None:
                    break
            if actor is None:
                continue
            direction = np.asarray(
                insp._placement_drag_display_direction("translate", "z", 1.0, actor),
                dtype=float,
            ).reshape(-1)[:2]
            snap_mm = insp._axis_slide_snap_step_for_row(target)
            insp._clear_step_translate_drag_overlay(render=False)
            insp._axis_slide_drag_state = {
                "row_index": target,
                "group_indices": list(group),
                "snap_mm": float(snap_mm),
                "display_direction": direction,
                "pixel_accumulator": 0.0,
                "applied_delta_mm": 0.0,
                "history_started": False,
                "last_result": None,
            }
            before = len(insp._step_translate_gap_actors)
            # Drive the cursor along the on-screen +Z direction so the snap-step
            # accumulator actually crosses a step (a fixed dx=60 misses when +Z
            # projects vertically on screen).
            dx = float(direction[0]) * 4.0 * ppx
            dy = -float(direction[1]) * 4.0 * ppx
            insp._apply_axis_slide_drag_motion(dx, dy)
            insp.update_idletasks()
            if before != 0:
                failures.append(f"gap actors were not empty before the drag on S{target} ({before})")
            if insp._step_translate_gap_actors:
                used_target = target
                actors = list(insp._step_translate_gap_actors)
                break
            insp._axis_slide_drag_state = None

        if used_target is None:
            failures.append("no slide-along-axis drag produced a gap overlay (#66 not wired in)")
            print("\nFAIL: axis-slide gap overlay")
            for f in failures:
                print(f"  ! {f}")
            return 1

        out_dir = Path(tempfile.gettempdir())
        png_path = out_dir / "krakenos_axis_slide_gap_overlay.png"
        render_window_to_png(insp, png_path)

        colors = [c for c in (_actor_color(a) for a in actors) if c is not None]
        has_emerald = any(_close(c, EMERALD) for c in colors)
        has_thick_leader = any(
            _close(_actor_color(a), LEADER_GREEN) and _actor_line_width(a) >= 4.0 for a in actors
        )
        reused_axis = [c for c in colors if _close(c, AXIS_BLUE) or _close(c, HIGHLIGHT_GOLD)]

        print(f"  slid row S{used_target}: {len(actors)} gap actors; colors={[tuple(round(v,2) for v in c) for c in colors]}")
        print(f"  PNG: {png_path}")

        if not has_emerald:
            failures.append(f"no emerald {EMERALD} gap arrow among the overlay actors (#65 colour lost)")
        if not has_thick_leader:
            failures.append("no thick (>=4 px) emerald leader line among the overlay actors (#65 thickness lost)")
        if reused_axis:
            failures.append(f"gap overlay reused an axis colour {reused_axis} (#65 distinctness lost)")

        # Teeth: the overlay must clear on release.
        state = insp._axis_slide_drag_state or {"group_indices": [used_target], "applied_delta_mm": 1.0}
        insp._finish_axis_slide_drag(state)
        insp.update_idletasks()
        if insp._step_translate_gap_actors:
            failures.append(f"gap overlay survived release ({len(insp._step_translate_gap_actors)} actors)")

        if failures:
            print("\nFAIL: axis-slide gap overlay (#65/#66)")
            for f in failures:
                print(f"  ! {f}")
            return 1
        print("\nPASS: slide-along-axis now draws a thick emerald live gap that clears on release.")
        return 0
    finally:
        try:
            app.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
