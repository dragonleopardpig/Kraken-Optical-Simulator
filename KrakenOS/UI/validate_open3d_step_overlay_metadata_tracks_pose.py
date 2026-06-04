#!/usr/bin/env python3
"""Display-free regression for bugs/0010 (stranded "ghost" hover edge
highlights): an imported STEP overlay's per-face metadata -- the world-space
centroids the round-lens cap pick and hover outline are built from -- must
follow the body when it is moved, instead of staying frozen at the former pose.

The hover outline / cap pick read ``_step_overlay_face_metadata(label)``, which
memoises analytic face records. Two seams stranded those records at the
pre-move pose, so re-hovering the now-empty old region re-picked a face there
and redrew its outline as a "ghost" floating above the moved lens (flag
20260603_171626_741):

  1. the metadata cache key omitted the placement/rotation pose, so a move
     returned the first-computed (stale) world coords; and
  2. even on recompute, the grouped axisymmetric *cap* faces derived their
     centroid by affine-transforming the source-frame analytic centroid -- and
     that fit silently degenerates (source vs display triangle-count mismatch
     -> affine None -> source coords), so the caps never moved.

This boots the inspector headless, imports an optical STEP, reads the metadata,
moves the overlay +20 mm in z (NO cache clear between reads -- exactly what the
hover path does), and asserts EVERY face centroid (including the grouped caps)
tracks the move. The tracked prism always runs (guards seam 1); a round lens,
when checked out under attachment/Lens/, additionally exercises the grouped
axisymmetric caps (seam 2). Rendered-pixel proof lives in
validate_open3d_step_overlay_hover_tracks_move_snapshot.

Run (boots its own private Xvfb if DISPLAY is unset):
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_step_overlay_metadata_tracks_pose

Exit: 0 = pass, 1 = regression (a face did not track), 2 = environment can't
      render (no Xvfb).
"""
from __future__ import annotations

import numpy as np

_GROUP_PREFIX = "step_analytic_axisymmetric_group"


def _consumer_centroids(metadata) -> dict[str, np.ndarray]:
    """face_id -> the centroid the cap pick / hover outline actually reads
    (``centroid_world`` if present, else ``centroid``)."""
    out: dict[str, np.ndarray] = {}
    for index, face in enumerate(list((metadata or {}).get("faces", []) or [])):
        if not isinstance(face, dict):
            continue
        face_id = str(face.get("face_id", "") or f"#{index}")
        for key in ("centroid_world", "centroid"):
            try:
                value = np.asarray(face.get(key), dtype=float).reshape(-1)[:3]
            except Exception:
                continue
            if value.size >= 3 and np.all(np.isfinite(value)):
                out[face_id] = value
                break
    return out


def _grouped_cap_face_ids(metadata) -> set[str]:
    out: set[str] = set()
    for index, face in enumerate(list((metadata or {}).get("faces", []) or [])):
        if not isinstance(face, dict):
            continue
        if str(face.get("assignment_source", "") or "").startswith(_GROUP_PREFIX):
            out.add(str(face.get("face_id", "") or f"#{index}"))
    return out


def metadata_pose_tracking_failures(
    app, *, move_mm: float = 20.0, tol: float = 0.5
) -> tuple[list[str], dict]:
    """Move the optical overlay +move_mm in z and check every face centroid
    follows. Assumes the optical STEP overlay is already imported.

    Reads the metadata twice WITHOUT clearing the cache in between, exactly as
    the hover path does -- so a pose-blind cache key (seam 1) is caught here,
    not just a stale grouped-cap centroid (seam 2).
    """
    failures: list[str] = []
    detail: dict = {}

    app.optical_step_placement_offset_xyz = (0.0, 0.0, 0.0)
    app.__dict__.pop("_step_overlay_face_metadata_cache", None)
    before_md = app._step_overlay_face_metadata("optical")
    before = _consumer_centroids(before_md)

    app.optical_step_placement_offset_xyz = (0.0, 0.0, float(move_mm))
    after_md = app._step_overlay_face_metadata("optical")
    after = _consumer_centroids(after_md)

    grouped = _grouped_cap_face_ids(after_md)
    detail["face_count"] = len(before)
    detail["grouped_cap_faces"] = sorted(grouped)
    if not before:
        failures.append("no optical face metadata produced; cannot evaluate pose tracking")
        return failures, detail

    if set(before) != set(after):
        failures.append(
            f"face set changed across the move: before={sorted(before)} after={sorted(after)}"
        )

    common = sorted(set(before) & set(after))
    stale: list[tuple[str, list[float]]] = []
    worst = 0.0
    worst_grouped = 0.0
    for face_id in common:
        delta = after[face_id] - before[face_id]
        err = max(abs(float(delta[0])), abs(float(delta[1])), abs(float(delta[2]) - move_mm))
        worst = max(worst, err)
        if face_id in grouped:
            worst_grouped = max(worst_grouped, err)
        if err > tol:
            stale.append((face_id, [round(float(v), 3) for v in delta]))
    detail["worst_track_err_mm"] = round(float(worst), 4)
    detail["worst_grouped_cap_err_mm"] = round(float(worst_grouped), 4)
    detail["moved_faces"] = len(common) - len(stale)
    if stale:
        failures.append(
            f"{len(stale)}/{len(common)} face(s) did not track the +{move_mm:g} mm z move "
            f"(expected delta ~[0,0,{move_mm:g}]) -- bugs/0010 stale overlay metadata: {stale}"
        )
    return failures, detail


def _evaluate_fixture(app, inspector, step_path, *, move_mm: float = 20.0) -> tuple[list[str], dict]:
    from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _import_step

    try:
        app.clear_step_imports()
    except Exception:
        pass
    _import_step(app, step_path)
    inspector.refresh_from_editor(force_retrace=False)
    inspector.update_idletasks()
    failures, detail = metadata_pose_tracking_failures(app, move_mm=move_mm)
    try:
        app.clear_step_imports()
    except Exception:
        pass
    return failures, detail


def _first_lens_with_grouped_caps(app, inspector, fixtures):
    """Prefer a round-lens fixture that actually produces grouped axisymmetric
    cap faces, so seam 2 is exercised. Fall back to the first fixture."""
    from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _import_step

    fallback = fixtures[0] if fixtures else None
    for fixture in fixtures:
        try:
            app.clear_step_imports()
        except Exception:
            pass
        _import_step(app, fixture["step"])
        inspector.refresh_from_editor(force_retrace=False)
        inspector.update_idletasks()
        md = app._step_overlay_face_metadata("optical")
        if _grouped_cap_face_ids(md):
            try:
                app.clear_step_imports()
            except Exception:
                pass
            return fixture
    try:
        app.clear_step_imports()
    except Exception:
        pass
    return fallback


def main() -> int:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor, SurfaceRow
    from KrakenOS.UI.services.prism_fixtures import PRISM_42779_STEP
    from KrakenOS.UI.validate_open3d_analytic_lens_selection_snapshot import _ensure_display
    from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import (
        LENS_FIXTURES,
        _open_inspector,
    )

    xvfb_proc, env_err = _ensure_display()
    if env_err is not None:
        print(f"[SKIP] cannot boot inspector: {env_err}")
        return 2

    app = None
    failures: list[str] = []
    ran_any = False
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

        # Tracked prism: always runs, guards the pose-aware cache key (seam 1).
        if PRISM_42779_STEP.exists():
            ran_any = True
            prism_fail, prism_detail = _evaluate_fixture(app, inspector, PRISM_42779_STEP)
            print(f"prism 42779: {prism_detail}")
            failures += [f"[prism] {m}" for m in prism_fail]
        else:
            print("[skip] tracked prism fixture missing")

        # Round lens: best-effort, exercises the grouped axisymmetric caps (seam 2).
        lens_fix = _first_lens_with_grouped_caps(app, inspector, LENS_FIXTURES)
        if lens_fix is not None:
            ran_any = True
            lens_fail, lens_detail = _evaluate_fixture(app, inspector, lens_fix["step"])
            print(f"round lens {lens_fix['name']}: {lens_detail}")
            if not lens_detail.get("grouped_cap_faces"):
                print("  [note] this lens produced no grouped axisymmetric caps; seam 2 not exercised")
            failures += [f"[lens {lens_fix['name']}] {m}" for m in lens_fail]
        else:
            print("[skip] no round-lens fixture under attachment/Lens/ (grouped-cap seam not exercised)")

        if not ran_any:
            print("[SKIP] no STEP fixtures available")
            return 2
    finally:
        if app is not None:
            try:
                app.destroy()
            except Exception:
                pass
        if xvfb_proc is not None:
            xvfb_proc.terminate()
            try:
                xvfb_proc.wait(timeout=5)
            except Exception:
                xvfb_proc.kill()

    if failures:
        print("\n[FAIL] bugs/0010 overlay metadata pose tracking")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("\n[PASS] every imported STEP face centroid tracks the body move")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
