#!/usr/bin/env python3
"""Image-snapshot regression for bugs/0010: after a round lens is moved, its
hover edge-highlight must NOT be left stranded as a "ghost" at the body's
former position.

Why a rendered guard and not just the metadata assertion: the metadata-level
guard lives in ``validate_open3d_step_overlay_metadata_tracks_pose`` (every face
centroid tracks the move). But the *symptom* the user reported is a rendered one
-- a gold edge outline + surface-centre marker floating in empty space above the
moved lens, lighting up when the cursor re-enters the now-vacated region (flag
20260603_171626_741, scene idle, nothing selected).

The discriminator is subtle: the hover OUTLINE geometry is read from the moved
display mesh via ``triangle_indices``, so it always tracks the body -- a whole-
frame pixel diff of the outline has no teeth. The stale-able part is the cap
PICK (``round_lens_feature_for_display_xy`` -> ``_metadata_round_lens_cap_pick``),
which decides *which* cap the cursor is over from the cap's stored
``centroid_world`` / ``centroid`` + ``normal`` plane and reports its
``surface_center``. When the metadata is frozen at the pre-move pose:
  * a pick aimed at the moved cap's NEW screen position misses (the stale plane
    is still at the OLD screen position), so the highlight does not follow; and
  * a pick aimed at the VACATED OLD screen position hits the stale plane and
    returns a cap whose ``surface_center`` is still at the old z -- the ghost.

This boots the inspector, imports a round-lens-like body with grouped
axisymmetric caps (prefers a vendor achromat -- the very body the user flagged,
face S002/F002), frames it OBLIQUELY (a strong axial view component so the
cap-plane pick stays well-conditioned; a side-on view makes the optical axis
edge-on and the cap pick degenerates), picks a cap, then moves the body +DZ and
re-applies the same camera. It drives the pick at the new and the vacated-old
screen positions and asserts: the new pick tracks (same cap, surface_center z
follows), and the old pick is NOT a cap frozen at the pre-move z. A small marker
sphere is drawn at each pick's surface centre so the saved PNGs visibly show the
highlight following the body (or, on regression, stranded above it).

The rendered frames (pose_a_hover / pose_b_old_region / pose_b_new_hover) are
saved for eyeball inspection.

Run (boots its own private Xvfb if DISPLAY is unset):
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_step_overlay_hover_tracks_move_snapshot

Exit: 0 = pass, 1 = ghost regression, 2 = environment can't render (no Xvfb / no
      round-lens fixture with grouped caps).
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np

# A hover highlight (outline + surface-centre marker) visibly changes the frame;
# post-fix it changed many hundreds of pixels. 120 is a safe floor a real
# highlight clears and a no-hover frame stays well under (sibling 0005 snapshot).
MIN_HIGHLIGHT_CHANGED = 120
# Move far enough that the old/new cap centres are clearly separated on screen.
MOVE_MM = 25.0
# How close (mm) two cap centres must be to count as "the same z". Used both to
# confirm the moved hover tracked and to detect a pick frozen at the old pose.
TRACK_TOL_MM = 1.0
# Oblique view direction (camera -> focal is -this). A strong axial (z) component
# keeps the cap-plane ray test non-degenerate (denom = ray.normal != 0); a side-on
# view makes the optical axis edge-on so denom -> 0 and the cap pick never fires.
_VIEW_DIR = np.asarray([0.0, 0.6, 0.8], dtype=float)


def _load_rgb(png_path):
    from PIL import Image

    return np.asarray(Image.open(png_path).convert("RGB")).astype(int)


def _changed_pixels(arr, baseline) -> int:
    return int((np.abs(arr - baseline).sum(axis=2) > 30).sum())


def _grouped_cap_face(metadata):
    """Return a grouped axisymmetric cap face record with a finite centroid."""
    for face in list((metadata or {}).get("faces", []) or []):
        if not isinstance(face, dict):
            continue
        if not str(face.get("assignment_source", "") or "").startswith(
            "step_analytic_axisymmetric_group"
        ):
            continue
        try:
            centroid = np.asarray(
                face.get("centroid_world", face.get("centroid", ())), dtype=float
            ).reshape(-1)[:3]
        except Exception:
            continue
        if centroid.size >= 3 and np.all(np.isfinite(centroid)):
            return face, centroid
    return None, None


def _frame_oblique(inspector):
    """Aim the camera obliquely at the lens: the view direction keeps a strong
    axial component so the cap-plane pick stays well-conditioned, while an axial
    move still shifts the cap on screen. Returns the camera tuple to re-apply."""
    center, radius = inspector._scene_bounds()
    center = np.asarray(center, dtype=float).reshape(-1)[:3]
    radius = float(radius) if np.isfinite(radius) and radius > 1e-6 else 50.0
    position = tuple(float(v) for v in (center + 3.0 * radius * _VIEW_DIR))
    focal = tuple(float(v) for v in center)
    _reapply_camera(inspector, position, focal)
    return position, focal


def _reapply_camera(inspector, position, focal):
    camera = inspector._renderer.GetActiveCamera()
    camera.SetPosition(*position)
    camera.SetFocalPoint(*focal)
    camera.SetViewUp(0.0, 1.0, 0.0)
    inspector._renderer.ResetCameraClippingRange()
    inspector.render()


def _marker_sphere(center, scene_radius):
    """A small sphere at the pick's surface centre. This anchors on the cap's
    ``centroid_world``/``centroid`` (the field bug-0010 stranded), so when the
    pick centre is stale the marker visibly floats at the body's former pose --
    the rendered "ghost" the user reported -- and follows the body once fixed."""
    import pyvista as pv

    radius = max(float(scene_radius) * 0.06, 0.8)
    return pv.Sphere(radius=radius, center=tuple(float(v) for v in np.asarray(center, dtype=float).reshape(-1)[:3]))


def _render_hover_for_pick(inspector, label, display_xy, key, png_path):
    """Drive the round-lens cap pick at display_xy; if it selects a face, draw
    its hover outline plus a marker at the pick's surface centre. Render to
    png_path. Return the pick dict (or None)."""
    from KrakenOS.UI.services.open3d_round_lens_pick import round_lens_feature_for_display_xy
    from KrakenOS.UI.validate_open3d_analytic_lens_selection_snapshot import render_window_to_png

    inspector._set_step_hover_outline(None, None, render=False)
    pick = round_lens_feature_for_display_xy(inspector, label, display_xy)
    if pick is not None:
        face = pick.get("through_pick").face if pick.get("through_pick") is not None else None
        overlay = inspector._hover_overlay_for_step_face(label, face) if face else None
        center = _pick_surface_center(pick)
        if center is not None:
            try:
                _scene_center, scene_radius = inspector._scene_bounds()
                marker = _marker_sphere(center, scene_radius)
                overlay = marker if overlay is None else overlay.merge(marker)
            except Exception:
                pass
        if overlay is not None:
            inspector._set_step_hover_outline(overlay, key, render=False)
    inspector.update_idletasks()
    inspector.update()
    render_window_to_png(inspector, png_path)
    return pick


def _pick_surface_center(pick):
    if pick is None:
        return None
    try:
        center = np.asarray(pick.get("surface_center"), dtype=float).reshape(-1)[:3]
    except Exception:
        return None
    return center if center.size >= 3 and np.all(np.isfinite(center)) else None


def _round_lens_fixture_with_caps(app, inspector, fixtures):
    """Pick a fixture the cap-pick path actually accepts: it must be
    ``_step_label_is_round_lens_like`` AND expose grouped axisymmetric caps.
    Prefer a vendor achromat (the body the user flagged -- face S002/F002),
    then a DCV, then anything else qualifying. Ball lenses are NOT round-lens-
    like, so the cap pick is disabled on them -- skip."""
    from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _import_step

    def rank(fixture):
        name = str(fixture.get("name", "")).lower()
        return (0 if "achromat" in name else 1 if "dcv" in name else 2, name)

    for fixture in sorted(fixtures, key=rank):
        try:
            app.clear_step_imports()
        except Exception:
            pass
        _import_step(app, fixture["step"])
        app.optical_step_placement_offset_xyz = (0.0, 0.0, 30.0)
        inspector.refresh_from_editor(force_retrace=False)
        inspector.update_idletasks()
        if not inspector._step_label_is_round_lens_like("optical"):
            continue
        face, _centroid = _grouped_cap_face(app._step_overlay_face_metadata("optical"))
        if face is not None:
            return fixture
    return None


def _evaluate(out_dir: Path):
    """Boot, import a capped round lens, and exercise the move/ghost path.

    Returns (metrics_or_None, message). metrics is None on an environment skip.
    """
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor, SurfaceRow
    from KrakenOS.UI.validate_open3d_analytic_lens_selection_snapshot import render_window_to_png
    from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import (
        LENS_FIXTURES,
        _import_step,
        _open_inspector,
    )

    if not LENS_FIXTURES:
        return None, "no round-lens STEP fixtures checked out under attachment/Lens/"

    app = KrakenLayoutEditor()
    try:
        inspector = _open_inspector(app)
        for var in ("show_rotation_handles_var", "show_rays_var"):
            try:
                getattr(inspector, var).set(False)
            except Exception:
                pass
        app.rows = [
            SurfaceRow(label="0", surface="Object", element="", name="Object",
                       thickness=80.0, diameter=25.0, glass="AIR"),
            SurfaceRow(label="1", surface="Image", element="", name="Image",
                       thickness=0.0, diameter=25.0, glass="AIR"),
        ]
        app._sync_table()

        fixture = _round_lens_fixture_with_caps(app, inspector, LENS_FIXTURES)
        if fixture is None:
            return None, "no round-lens-like fixture with grouped caps under attachment/Lens/"

        app.clear_step_imports()
        _import_step(app, fixture["step"])
        # Park the body mid-scene so the cap stays framed before and after the move.
        app.optical_step_placement_offset_xyz = (0.0, 0.0, 30.0)
        inspector.refresh_from_editor(force_retrace=False)
        inspector.update_idletasks()
        inspector.update()

        seed_face, seed_centroid = _grouped_cap_face(app._step_overlay_face_metadata("optical"))
        if seed_face is None:
            return None, f"{fixture['name']}: no grouped axisymmetric cap face produced"

        position, focal = _frame_oblique(inspector)
        xy_seed = inspector._world_to_display_2d(seed_centroid)
        if xy_seed is None:
            return None, "could not project the seed cap centre to the screen"

        base_a = out_dir / "pose_a_base.png"
        render_window_to_png(inspector, base_a)
        pose_a = out_dir / "pose_a_hover.png"
        # Pick at the seed cap on screen; anchor everything on the pick's OWN
        # reported surface centre so projection and the tracking assertion agree
        # on the same cap (the seed centroid and the picked cap can differ).
        pick_a = _render_hover_for_pick(inspector, "optical", xy_seed, "cap_a", pose_a)
        sc_a = _pick_surface_center(pick_a)
        fid_a = None if pick_a is None else str(pick_a.get("face_id", "") or "")
        if sc_a is None:
            return None, f"{fixture['name']}: pose-A cap pick failed (cannot anchor the move test)"

        # Move the body +MOVE_MM along the optical axis and re-frame identically.
        inspector._set_step_hover_outline(None, None, render=False)
        app.optical_step_placement_offset_xyz = (0.0, 0.0, 30.0 + MOVE_MM)
        inspector.refresh_from_editor(force_retrace=False)
        inspector.update_idletasks()
        _reapply_camera(inspector, position, focal)

        sc_b = sc_a + np.asarray([0.0, 0.0, MOVE_MM], dtype=float)
        xy_old = inspector._world_to_display_2d(sc_a)   # vacated region
        xy_new = inspector._world_to_display_2d(sc_b)   # moved cap

        base_b = out_dir / "pose_b_base.png"
        render_window_to_png(inspector, base_b)

        old_png = out_dir / "pose_b_old_region.png"
        pick_old = _render_hover_for_pick(inspector, "optical", xy_old, "cap_old", old_png)
        sc_old = _pick_surface_center(pick_old)

        new_png = out_dir / "pose_b_new_hover.png"
        pick_new = _render_hover_for_pick(inspector, "optical", xy_new, "cap_new", new_png)
        sc_new = _pick_surface_center(pick_new)
        fid_new = None if pick_new is None else str(pick_new.get("face_id", "") or "")

        # The ghost signature: a pick aimed at the VACATED old screen location
        # returns a cap whose centre is STILL frozen at the pre-move pose
        # (sc_old.z ~ sc_a.z). With the metadata tracking the body, any pick
        # there is either empty or a correctly-moved cap (sc_old.z far from old).
        ghost_stale = bool(sc_old is not None and abs(float(sc_old[2]) - float(sc_a[2])) <= TRACK_TOL_MM)

        base_a_rgb = _load_rgb(base_a)
        base_b_rgb = _load_rgb(base_b)
        changed_a = _changed_pixels(_load_rgb(pose_a), base_a_rgb)
        changed_old = _changed_pixels(_load_rgb(old_png), base_b_rgb)
        changed_new = _changed_pixels(_load_rgb(new_png), base_b_rgb)

        metrics = {
            "fixture": fixture["name"],
            "face_id": fid_a,
            "new_face_id": fid_new,
            "sc_a_z": round(float(sc_a[2]), 3),
            "sc_b_z": round(float(sc_b[2]), 3),
            "xy_old": None if xy_old is None else [round(float(v), 1) for v in np.asarray(xy_old).reshape(-1)[:2]],
            "xy_new": None if xy_new is None else [round(float(v), 1) for v in np.asarray(xy_new).reshape(-1)[:2]],
            "pick_a": pick_a is not None,
            "pick_old": pick_old is not None,
            "old_center_z": None if sc_old is None else round(float(sc_old[2]), 3),
            "ghost_stale": ghost_stale,
            "pick_new": pick_new is not None,
            "new_center_z": None if sc_new is None else round(float(sc_new[2]), 3),
            "same_cap": bool(fid_new and fid_a and fid_new == fid_a),
            "changed_pose_a": changed_a,
            "changed_old_region": changed_old,
            "changed_new_hover": changed_new,
            "pngs": {
                "pose_a_hover": str(pose_a),
                "pose_b_old_region": str(old_png),
                "pose_b_new_hover": str(new_png),
            },
        }
        return metrics, f"exercised {fixture['name']} cap {fid_a}"
    finally:
        try:
            app.destroy()
        except Exception:
            pass


def main() -> int:
    from KrakenOS.UI.validate_open3d_analytic_lens_selection_snapshot import _ensure_display

    out_dir = Path(os.environ.get("KRAKEN_SNAPSHOT_DIR", "/tmp/kraken_0010_hover_snapshot"))
    out_dir.mkdir(parents=True, exist_ok=True)

    xvfb_proc, env_err = _ensure_display()
    if env_err is not None:
        print(f"[SKIP] cannot render snapshot: {env_err}")
        return 2
    try:
        metrics, message = _evaluate(out_dir)
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
    for key in (
        "face_id", "new_face_id", "same_cap", "sc_a_z", "sc_b_z", "xy_old", "xy_new",
        "pick_a", "pick_old", "old_center_z", "ghost_stale", "pick_new", "new_center_z",
        "changed_pose_a", "changed_old_region", "changed_new_hover",
    ):
        print(f"  {key:18s} = {metrics[key]}")
    for name, path in metrics["pngs"].items():
        print(f"    {name}: {path}")

    failures: list[str] = []
    if not metrics["pick_a"]:
        failures.append("pose A: the cap pick did not select the cap at its own centre (harness setup failed)")
    if metrics["changed_pose_a"] <= MIN_HIGHLIGHT_CHANGED:
        failures.append(
            f"pose A hover changed {metrics['changed_pose_a']} px (<= {MIN_HIGHLIGHT_CHANGED}): "
            "the cap highlight did not render -- cannot prove the move case"
        )
    if metrics["ghost_stale"]:
        failures.append(
            f"after the move, a pick aimed at the VACATED old location selected a cap whose centre is "
            f"still frozen at the former pose (old_center_z={metrics['old_center_z']} ~ sc_a_z={metrics['sc_a_z']}) "
            "-- bugs/0010 ghost: stale cap pick geometry stranded at the pre-move pose"
        )
    if not metrics["pick_new"]:
        failures.append("after the move, a pick at the NEW cap location failed to select the moved cap")
    elif metrics["new_center_z"] is not None and abs(metrics["new_center_z"] - metrics["sc_b_z"]) > TRACK_TOL_MM:
        failures.append(
            f"after the move, the selected cap centre z={metrics['new_center_z']} did not track to "
            f"the moved cap z={metrics['sc_b_z']} (tol {TRACK_TOL_MM} mm)"
        )
    if metrics["changed_new_hover"] <= MIN_HIGHLIGHT_CHANGED:
        failures.append(
            f"after the move, the hover at the new cap changed {metrics['changed_new_hover']} px "
            f"(<= {MIN_HIGHLIGHT_CHANGED}): the highlight did not follow the moved body"
        )

    if failures:
        print("[FAIL] bugs/0010 hover ghost snapshot")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] hover highlight follows the moved lens; no ghost at the old location")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
