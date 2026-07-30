"""bugs/0480 probe -- WHICH detector target does the camera seating actually choose?

`seat_camera_on_sensor` seats the camera body onto a detector target it picks out of the
traced bundle. On a beam-splitter scene there is a detector per TERMINAL LEAF, and the
fallback was literally "the first is_detector target" -- with the leaves enumerated in
``sorted(leaves)`` order, i.e. alphabetically by branch path.

Measured here on the real reported scene, in BOTH states:
  as-loaded, and after "Snap detector to image plane (remove defocus)" -- the bugs/0477
  trigger that un-pins the imaging leaf and so drops the seating into that fallback.

Run:
    DISPLAY=:99 .devenv/state/venv/bin/python bugs/probe_0480_arm_selection.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")


def _designed_image_point(app):
    stations = app._row_z_positions()
    index = app._image_plane_row_index()
    if index is None:
        return None
    row = app.rows[int(index)]
    point = np.asarray(
        [float(row.desp_x), float(row.desp_y), float(stations[int(index)]) + float(row.desp_z)],
        dtype=float,
    )
    fold = app._optical_axis_fold_world_transform_for_row(int(index))
    if fold is not None:
        point = (np.asarray(fold, dtype=float) @ np.append(point, 1.0))[:3]
    return point


def dump(app, tag: str) -> None:
    print(f"\n================ {tag} ================")
    image_point = _designed_image_point(app)
    index = app._image_plane_row_index()
    print(f"image row {index} thickness(row7)={float(app.rows[7].thickness):.4f}  designed image pt={np.round(image_point, 4).tolist()}")
    print(f"camera_track_image_plane_z={float(app._camera_track_image_plane_z()):.4f} front_to_sensor={float(app._current_camera_front_to_sensor_mm()):.4f}")

    _s, _r, bundle = app._build_preview_system_rays_bundle(
        sampling_mode=None, update_state=False, trace_rays=True
    )
    dets = [t for t in (getattr(bundle, "targets", None) or []) if bool(getattr(t, "is_detector", False))]
    print(f"is_detector targets = {len(dets)}")
    for order, t in enumerate(dets):
        meta = getattr(t, "metadata", None) or {}
        centre = np.asarray(getattr(t, "center_world", (np.nan,) * 3), dtype=float).reshape(-1)[:3]
        print(
            f"  [{order}] row={getattr(t, 'row_index', None)} src={meta.get('target_source')!r} "
            f"focus_source={meta.get('focus_source')!r} reaches={meta.get('reaches_designed_image')!r} "
            f"cam={meta.get('assigned_camera_label')!r}"
        )
        print(
            f"        centre={np.round(centre, 4).tolist()} "
            f"d(image)={float(np.linalg.norm(centre - image_point)):.4f}  path={meta.get('branch_path')!r}"
        )

    def centre_of(t):
        return np.round(np.asarray(getattr(t, "center_world", (np.nan,) * 3), dtype=float).reshape(-1)[:3], 3).tolist()

    # --- what the SHIPPED code picks: reached_image, else the first detector -------------
    old = None
    for t in dets:
        if str(((getattr(t, "metadata", None) or {}).get("focus_source", ""))) == "reached_image":
            old = t
            break
        if old is None:
            old = t
    print(f"OLD  (reached_image else FIRST)      -> {centre_of(old) if old is not None else None}")

    # --- what the uncommitted WIP picks: reached_image, else nearest WITHIN 1 mm ---------
    wip, best = None, None
    for t in dets:
        meta = getattr(t, "metadata", None) or {}
        if str(meta.get("focus_source", "")) == "reached_image":
            wip = t
            break
        centre = np.asarray(getattr(t, "center_world", (np.nan,) * 3), dtype=float).reshape(-1)[:3]
        d = float(np.linalg.norm(centre - image_point))
        if d > 1.0:
            continue
        if best is None or d < best:
            best, wip = d, t
    print(f"WIP  (reached_image else <=1mm)      -> {centre_of(wip) if wip is not None else 'REFUSES TO SEAT'}")

    # --- what the 0480 ladder picks ------------------------------------------------------
    def rank(t):
        meta = getattr(t, "metadata", None) or {}
        if str(meta.get("assigned_camera_label") or "") == "camera":
            return 0
        if str(meta.get("target_source") or "") != "branch_detector":
            return 1
        if str(meta.get("focus_source", "")) == "reached_image":
            return 2
        if bool(meta.get("reaches_designed_image", False)):
            return 3
        return 9

    ranked = sorted(
        ((rank(t), float(np.linalg.norm(np.asarray(getattr(t, "center_world", (np.nan,) * 3), dtype=float).reshape(-1)[:3] - image_point)), order, t) for order, t in enumerate(dets)),
        key=lambda e: (e[0], e[1], e[2]),
    )
    pick = ranked[0] if ranked and ranked[0][0] < 9 else None
    if pick is None and len(dets) == 1:
        pick = (5, 0.0, 0, dets[0])
    print(
        "0480 (assigned>image>pinned>reaches)  -> "
        + (f"rank={pick[0]} {centre_of(pick[3])}" if pick is not None else "REFUSES TO SEAT (ambiguous)")
    )


def main() -> int:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    app = KrakenLayoutEditor()
    app.layout_files["bs"] = SCENE
    app.load_layout_by_name("bs")
    dump(app, "AS LOADED")

    moved = app.snap_detector_to_image_plane()
    print(f"\nsnap_detector_to_image_plane() -> {moved}: {app.status_var.get()!r}")
    dump(app, "AFTER REMOVE DEFOCUS (the 0477 trigger)")

    try:
        app.destroy()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
