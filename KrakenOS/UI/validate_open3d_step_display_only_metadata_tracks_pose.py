#!/usr/bin/env python3
"""Display-free regression for bugs/0050 (bug 0010 resurfacing for display-only
STEP solids): moving an imported *display-only* overlay (camera/led/lens) via
the public placement API must update the cached per-face metadata so the hover
outline follows the body instead of stranding at the old pose.

bug 0010 was fixed for *analytic* labels (e.g. ``optical``) by adding the pose
to the face-metadata cache key. Display-only labels deliberately keep a
pose-blind, stat-only key -- recomputing their planar-clustering metadata on
every pose change risks the cold-load freeze. So after a gizmo translate the
LED/camera/lens kept handing back the body's *former* world coords, and the
gold face hover outline was redrawn at the now-empty old location ("the
residual highlight at old location bug surface again", flag 20260610_192731_451).

The fix invalidates the label's cached metadata inside the pose *setters*
(`_set_step_placement_offset_xyz` / `_set_step_axis_offset_xy` /
`_set_step_rotation_deg_tuple`), so the next hover re-derives geometry at the
new pose (lazy -- never during the move's own refresh, so no freeze).

This boots no inspector and needs no X server: it imports a STEP under the
display-only ``lens`` label, reads the metadata (caching it), moves the body
+20 mm in z through ``translate_step_overlay`` (the public API, which routes
through the invalidating setter), reads again WITHOUT a manual cache clear, and
asserts every face centroid tracked the move.

Exit: 0 = pass, 1 = regression (a face did not track / cache not invalidated),
      2 = environment can't import the CAD backend or the fixture is missing.
"""
from __future__ import annotations

import numpy as np

from KrakenOS.UI.validate_open3d_step_overlay_metadata_tracks_pose import (
    _consumer_centroids,
)

DISPLAY_ONLY_LABEL = "lens"


def main() -> int:
    from KrakenOS.UI import layout_editor as le
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services.prism_fixtures import PRISM_42779_STEP
    from KrakenOS.UI.services.scene_placement_commands import (
        ScenePlacementMixin,
    )

    le._load_3d_backends()
    if le.pv is None:
        print("[SKIP] PyVista/CAD backend unavailable; cannot build STEP metadata.")
        return 2
    if not PRISM_42779_STEP.exists():
        print(f"[SKIP] STEP fixture missing: {PRISM_42779_STEP}")
        return 2

    # Guard: this test is only meaningful while the label is genuinely
    # pose-blind (display-only). If that ever changes, the analytic
    # pose-aware path already covers it and this fixture should be revisited.
    if DISPLAY_ONLY_LABEL not in ScenePlacementMixin._DISPLAY_ONLY_STEP_LABELS_NO_ANALYTIC:
        print(
            f"[SKIP] {DISPLAY_ONLY_LABEL!r} is no longer a display-only label; "
            "the pose-aware analytic path now covers it."
        )
        return 2

    app = KrakenLayoutEditor(headless=True)
    app.imported_lens_step_path = PRISM_42779_STEP
    app._set_step_placement_offset_xyz(DISPLAY_ONLY_LABEL, (0.0, 0.0, 0.0))

    before_md = app._step_overlay_face_metadata(DISPLAY_ONLY_LABEL)
    before = _consumer_centroids(before_md)
    if not before:
        print(f"[SKIP] no {DISPLAY_ONLY_LABEL} face metadata produced; cannot evaluate.")
        return 2

    move_mm = 20.0
    tol = 0.5
    # The public move API; routes through _set_step_placement_offset_xyz, which
    # must invalidate the cached metadata. No render needed.
    app.translate_step_overlay(
        DISPLAY_ONLY_LABEL,
        (0.0, 0.0, move_mm),
        refresh=False,
        record_history=False,
    )

    after_md = app._step_overlay_face_metadata(DISPLAY_ONLY_LABEL)
    after = _consumer_centroids(after_md)

    # Match centroids as a *cloud*, not per face_id: the display-only planar
    # clusterer can reassign IDs between two faces (e.g. swap the two symmetric
    # side faces), which is harmless. What matters for bug 0050 is that every
    # face centroid is present at the moved pose -- i.e. the metadata recomputed
    # instead of returning the body's former (unmoved) coords.
    expected = [np.asarray(c, dtype=float) + np.array([0.0, 0.0, move_mm]) for c in before.values()]
    actual = [np.asarray(c, dtype=float) for c in after.values()]
    used = [False] * len(actual)
    unmatched: list[list[float]] = []
    worst = 0.0
    for exp in expected:
        best_i, best_err = -1, float("inf")
        for i, act in enumerate(actual):
            if used[i]:
                continue
            err = float(np.max(np.abs(act - exp)))
            if err < best_err:
                best_i, best_err = i, err
        if best_i >= 0 and best_err <= tol:
            used[best_i] = True
            worst = max(worst, best_err)
        else:
            unmatched.append([round(float(v), 3) for v in exp])

    print(
        f"display-only {DISPLAY_ONLY_LABEL!r}: faces={len(expected)} "
        f"matched={sum(used)} worst_track_err_mm={round(worst, 4)}"
    )
    if unmatched:
        print(
            f"[FAIL] {len(unmatched)}/{len(expected)} {DISPLAY_ONLY_LABEL} face centroid(s) "
            f"had no moved-pose match -- bugs/0050 pose-blind metadata not invalidated. "
            f"Expected-but-missing (moved) centroids: {unmatched}"
        )
        return 1

    print("STEP display-only metadata pose-tracking validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
