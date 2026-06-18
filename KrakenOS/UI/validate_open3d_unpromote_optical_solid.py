#!/usr/bin/env python3
"""Display-free guard for bugs/0093 right-click "Unpromote to STEP overlay":
``StepOverlayPromotionService.unpromote_optical_solid_to_overlay`` reverts a
promoted optical-solid row back to a decorative imported STEP overlay --
removing the solid row + its in-path AIR spacer, un-splitting the host gap
(downstream fixed), and restoring the overlay at the solid's CURRENT (slid) pose.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_unpromote_optical_solid

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace


def _stub_service(rows):
    """The service delegates every attr to ``self.editor`` -- so hold the state on a
    mock editor and let the real method run through the delegation."""
    from KrakenOS.UI.services.step_overlay_promotion import StepOverlayPromotionService

    ed = SimpleNamespace()
    ed.rows = rows
    ed.status_var = SimpleNamespace(set=lambda *a, **k: None)
    ed._selected_step_label = None
    ed._live_step_overlay_trace_plan_cache = {"stale": object()}
    ed.imported_optical_step_path = None
    ed.optical_step_rotation_x_deg = 0.0
    ed.optical_step_rotation_y_deg = 0.0
    ed.optical_step_rotation_z_deg = 0.0
    ed.optical_step_axis_offset_xy = (0.0, 0.0)
    ed.optical_step_placement_offset_xyz = (0.0, 0.0, 0.0)
    for name in (
        "_begin_history_capture", "_commit_history_capture", "_normalize_special_rows",
        "_sync_table", "_mark_plot_update_pending", "_invalidate_preview_scene_trace",
        "_refresh_open_3d_views",
    ):
        setattr(ed, name, lambda *a, **k: None)
    return StepOverlayPromotionService(ed), ed


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []

    promo = {
        "step_label": "optical", "source_step_path": "/x/cube.step",
        "center_world": [0.0, 0.0, 160.0], "placement_offset_xyz": [0.0, 0.0, 160.0],
        "step_rotation_deg": [0.0, 0.0, 0.0], "axis_offset_xy": [0.0, 0.0],
    }
    # Object(split gap 14) -> SOLID(50, promoted, slid up to y=80) -> AIR spacer(33)
    # -> Lens -> Image.  14+50+33 == 97 (the original host gap).
    rows = [
        SimpleNamespace(surface="Object", name="Object", thickness=14.0, glass="AIR", advanced={}),
        SimpleNamespace(surface="Solid 3D STL", name="Promoted OPTICAL STEP optical solid",
                        thickness=50.0, glass="BK7", desp_x=0.0, desp_y=80.0, desp_z=0.0,
                        advanced={"StepOverlayPromotion": promo}),
        SimpleNamespace(surface="Standard", name="Promoted OPTICAL STEP optical solid -> next gap (AIR)",
                        thickness=33.0, glass="AIR", advanced={}),
        SimpleNamespace(surface="Surface", name="Lens", thickness=0.0, glass="AIR", advanced={}),
        SimpleNamespace(surface="Image", name="Image", thickness=0.0, glass="AIR", advanced={}),
    ]
    svc, _ed = _stub_service(rows)
    out = svc.unpromote_optical_solid_to_overlay(1, refresh_open_3d=False)

    if out is None:
        failures.append("FAIL: unpromote returned None for a STEP-promoted row")
        return False, failures
    surfaces = [r.surface for r in svc.rows]
    if surfaces != ["Object", "Surface", "Image"]:
        failures.append(f"FAIL: solid + spacer not removed; rows = {surfaces}")
    if abs(float(svc.rows[0].thickness) - 97.0) > 1e-6:
        failures.append(f"FAIL: host gap not un-split (preceding = {svc.rows[0].thickness}, want 14+50+33=97)")
    if str(svc.imported_optical_step_path) != "/x/cube.step":
        failures.append(f"FAIL: overlay source path not restored: {svc.imported_optical_step_path}")
    if svc._selected_step_label != "optical":
        failures.append(f"FAIL: overlay label not re-selected: {svc._selected_step_label!r}")
    # placement carries the lateral slide: place0=(0,0,160) + (desp 0,80 - center 0,0) -> (0,80,160)
    place = tuple(float(v) for v in svc.optical_step_placement_offset_xyz)
    if abs(place[1] - 80.0) > 1e-6 or abs(place[2] - 160.0) > 1e-6:
        failures.append(f"FAIL: overlay placement didn't carry the slid pose: {place} (want (0,80,160))")

    # A non-promoted row is a no-op (returns None, rows untouched).
    plain = [SimpleNamespace(surface="Image", name="Image", thickness=0.0, glass="AIR", advanced={})]
    svc2, _ed2 = _stub_service(plain)
    if svc2.unpromote_optical_solid_to_overlay(0, refresh_open_3d=False) is not None:
        failures.append("FAIL: unpromote of a non-STEP-promoted row should be a no-op (None)")
    if len(svc2.rows) != 1:
        failures.append("FAIL: unpromote of a non-promoted row mutated the rows")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0093 unpromote optical solid to STEP overlay")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] right-click unpromote reverts a promoted solid to a STEP overlay (bugs/0093)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
