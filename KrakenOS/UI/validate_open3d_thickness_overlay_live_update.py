#!/usr/bin/env python3
"""Regression test for bugs/0011: the persistent thickness overlay must follow
the lens when it is moved, instead of freezing the ``gap = .. mm`` arrows at the
body's pre-move position.

Why this lives behind a renderer (not a pure ``@staticmethod`` unit test): the
bug is in the *refresh routing* after a Move/Rotate gizmo commit. When live
physics is off, ``_finish_step_translate_drag`` took the fast per-label
``refresh_imported_step_overlay`` path, which rebuilds only the moved body and
never recomputes the thickness dimensions (they span every component). So the
body slid but the two ``gap`` arrows + framed labels stayed put -- the live drag
readout was correct, only the committed overlay went stale (flag
``flag_20260603_171735_941``: body at z=70.75..82.33 but the overlay still read
46.25 / 42.17, the lens's previous centre ~52). The fix does a full refresh when
the dimensions are shown.

This boots the real inspector (its own private Xvfb if ``DISPLAY`` is unset),
places the tracked prism between Object(z=0) and Image(z=100), turns the
dimensions on, commits an axial Move, and checks the *rendered* billboard label
text AND the gap-arrow actor world geometry both track the new position.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_thickness_overlay_live_update

Exit: 0 = pass, 1 = regression (overlay stale after the move),
      2 = environment can't render (no Xvfb) or fixture unavailable.
"""
from __future__ import annotations

import inspect

import numpy as np

from KrakenOS.UI.validate_open3d_analytic_lens_selection_snapshot import _ensure_display
from KrakenOS.UI.layout_editor import KrakenLayoutEditor, SurfaceRow
from KrakenOS.UI.services.prism_fixtures import PRISM_42779_STEP
from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import (
    _open_inspector,
    _import_step,
)

AXIAL_MOVE_MM = 24.0
# Gap labels must change by the moved distance (within snap/rounding slack).
TOL_MM = 0.6


def _gap_labels(inspector) -> list[str]:
    texts: list[str] = []
    for key in list(getattr(inspector, "_actor_thickness_dimension_map", {}).keys()):
        actor = inspector._actor_by_key.get(key)
        if actor is None:
            continue
        try:
            if actor.IsA("vtkBillboardTextActor3D"):
                texts.append(str(actor.GetInput()))
        except Exception:
            pass
    return texts


def _gap_values(labels: list[str]) -> list[float]:
    out: list[float] = []
    for text in labels:
        token = str(text)
        if "gap =" not in token:
            continue
        try:
            out.append(round(float(token.split("=")[1].strip().split()[0]), 3))
        except Exception:
            pass
    return sorted(out)


def _arrow_spans(inspector) -> list[tuple[float, float]]:
    """Per-actor axial [zmin, zmax] of the thickness-dimension *arrow* meshes
    (the vtkActor shafts, not the billboard labels)."""
    spans: list[tuple[float, float]] = []
    for key in list(getattr(inspector, "_actor_thickness_dimension_map", {}).keys()):
        actor = inspector._actor_by_key.get(key)
        if actor is None:
            continue
        try:
            if actor.IsA("vtkBillboardTextActor3D") or not actor.IsA("vtkActor"):
                continue
            b = np.asarray(actor.GetBounds(), dtype=float)
        except Exception:
            continue
        if b.size == 6 and b[4] <= b[5]:
            spans.append((float(b[4]), float(b[5])))
    return spans


def _arrow_covers(spans: list[tuple[float, float]], z: float, *, margin: float = 1.5) -> bool:
    """Is axial coordinate ``z`` inside some arrow's span (with a small margin
    so arrowhead overhang at the body face doesn't count as covering the body)?"""
    return any(lo + margin <= z <= hi - margin for lo, hi in spans)


def _optical_z_center(inspector):
    zmin, zmax = np.inf, -np.inf
    for key in (inspector._step_actor_map or {}).get("optical", []):
        actor = inspector._actor_by_key.get(key)
        if actor is None:
            continue
        b = np.asarray(actor.GetBounds(), dtype=float)
        if b.size == 6 and b[4] <= b[5]:
            zmin = min(zmin, float(b[4]))
            zmax = max(zmax, float(b[5]))
    if not (np.isfinite(zmin) and np.isfinite(zmax)):
        return None
    return 0.5 * (zmin + zmax)


def main() -> int:
    if not PRISM_42779_STEP.exists():
        print("SKIP: tracked prism STEP fixture missing")
        return 2
    if not _ensure_display():
        print("SKIP: no usable display (Xvfb) for rendering")
        return 2

    failures: list[str] = []
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
    inspector.show_rays_var.set(False)
    try:
        inspector.show_rotation_handles_var.set(False)
    except Exception:
        pass

    _import_step(app, PRISM_42779_STEP)
    inspector.refresh_from_editor(force_retrace=False)
    inspector.update_idletasks()
    native_center = _optical_z_center(inspector)
    if native_center is None:
        print("SKIP: optical STEP overlay did not import")
        return 2
    app.optical_step_placement_offset_xyz = (0.0, 0.0, 40.0 - native_center)
    app.select_step_component("optical")
    inspector.refresh_from_editor(force_retrace=False)
    inspector.update_idletasks()
    try:
        inspector._clear_open3d_selection()
    except Exception:
        pass
    app._selected_step_label = None

    app.show_physical_distances_var.set(True)
    inspector.refresh_from_editor(force_retrace=False)
    inspector.update_idletasks()

    old_center = 40.0
    new_center = old_center + AXIAL_MOVE_MM

    before_labels = _gap_labels(inspector)
    before_gaps = _gap_values(before_labels)
    before_spans = _arrow_spans(inspector)
    print("before:", before_labels, "gaps:", before_gaps, "arrow spans:", before_spans)
    if len(before_gaps) != 2:
        failures.append(f"expected two gap dimensions before the move, got {before_labels!r}")
    if not before_spans:
        failures.append("no thickness-dimension arrow actors before the move")

    # Commit an axial Move (no live physics -> the formerly-stale fast path).
    state = {
        "label": "optical",
        "axis": "z",
        "applied_delta_mm": AXIAL_MOVE_MM,
        "axis_unit": np.array([0.0, 0.0, 1.0], dtype=float),
    }
    inspector._finish_step_translate_drag(state)
    inspector.update_idletasks()

    after_labels = _gap_labels(inspector)
    after_gaps = _gap_values(after_labels)
    after_spans = _arrow_spans(inspector)
    print("after: ", after_labels, "gaps:", after_gaps, "arrow spans:", after_spans)

    # The lens moved +AXIAL_MOVE_MM, so the near gap (Object->front) must grow by
    # that amount and the far gap (back->Image) must shrink by it. Equivalently:
    # the two gap values must differ from the pre-move pair by ~AXIAL_MOVE_MM.
    if len(after_gaps) != 2:
        failures.append(f"expected two gap dimensions after the move, got {after_labels!r}")
    elif before_gaps == after_gaps:
        failures.append(
            f"thickness overlay did not update after the move (stale): still {after_labels!r} "
            "(bugs/0011 regression -- the committed overlay froze at the old position)"
        )
    else:
        exp_near = before_gaps[0] + AXIAL_MOVE_MM   # smaller gap grows
        exp_far = before_gaps[1] - AXIAL_MOVE_MM    # larger gap shrinks
        expected = sorted([round(exp_near, 3), round(exp_far, 3)])
        if any(abs(a - e) > TOL_MM for a, e in zip(after_gaps, expected)):
            failures.append(
                f"thickness overlay updated but not by the moved distance: {after_gaps} "
                f"(expected ~{expected} after a {AXIAL_MOVE_MM:+g} mm move)"
            )

    # The arrow geometry must track the body too (not just the label string).
    # The two gap arrows always union to [Object, Image]; what moves is the
    # clear band they leave for the lens. Before the move that band is at the
    # old centre (so an arrow does NOT cover it) and an arrow DOES cover the new
    # centre; after the move it must be the other way round. A stale overlay
    # keeps the old split and fails both after-move checks.
    if before_spans and _arrow_covers(before_spans, old_center):
        failures.append(f"before move: an arrow already crosses the old lens centre z={old_center} {before_spans}")
    if after_spans:
        if not _arrow_covers(after_spans, old_center):
            failures.append(
                f"after move: no arrow covers the vacated old lens centre z={old_center} "
                f"(arrows did not slide) {after_spans}"
            )
        if _arrow_covers(after_spans, new_center):
            failures.append(
                f"after move: an arrow crosses the lens's new centre z={new_center} "
                f"(arrows did not split around the moved body) {after_spans}"
            )

    # Source-couple the fix: the translate-commit refresh routing must consult
    # show_physical_distances_var so it does a full refresh when the dimensions
    # are shown (otherwise the fast per-label path leaves them stale).
    try:
        src = inspect.getsource(type(inspector)._finish_step_translate_drag)
    except Exception:
        src = ""
    if "show_physical_distances_var" not in src:
        failures.append(
            "_finish_step_translate_drag no longer consults show_physical_distances_var "
            "(bugs/0011 fix removed -- the fast partial-refresh path can leave the overlay stale)"
        )

    if failures:
        print("\nFAIL: bugs/0011 thickness overlay live-update")
        for f in failures:
            print(f"  ! {f}")
        return 1
    print("\nPASS: thickness overlay follows the lens after a Move commit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
