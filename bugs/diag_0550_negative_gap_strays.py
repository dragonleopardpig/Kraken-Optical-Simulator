"""bugs/0550 diagnostic -- "Extra rays out of bound" (flag_20260805_072959_035,
attachment/machine_vision_Apo75.py).

After the 0546/0547 swap the scene traces 558 paths of which 375 end in
``no_next_intersection`` and the drawn rays blow out to x 375 / z -366..+505.

The saved layout carries a NEGATIVE gap on the re-seated promoted BS row, so the station
chain runs BACKWARDS across it::

    s5 Rear Optical Vertex Datum   station 168.974   thickness  83.381
    s6 Promoted OPTICAL STEP solid station 252.355   thickness -13.595   <-- negative
    s7 Promoted OPTICAL STEP solid station 238.760                       <-- went backwards

This script measures whether that negative gap is the CAUSE: it traces the scene as saved,
then neutralises the gap (thickness -> 0 with ``desp_z`` compensated on every downstream row
so no pose moves by even a micron) and traces again. If the stray census collapses, the
negative gap is the cause; if it does not, the strays come from somewhere else and this
avenue is closed.

Run:  xvfb-run -a .devenv/state/venv/bin/python bugs/diag_0550_negative_gap_strays.py
"""

from __future__ import annotations

import sys
from pathlib import Path

SCENE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("attachment/machine_vision_Apo75.py")


def _stations(rows):
    out, total = [0.0], 0.0
    for row in rows[:-1]:
        total += float(getattr(row, "thickness", 0.0) or 0.0)
        out.append(total)
    while len(out) < len(rows):
        out.append(total)
    return out


def _poses(app):
    stations = _stations(app.rows)
    return [
        (
            float(getattr(r, "desp_x", 0.0) or 0.0),
            float(getattr(r, "desp_y", 0.0) or 0.0),
            stations[i] + float(getattr(r, "desp_z", 0.0) or 0.0),
        )
        for i, r in enumerate(app.rows)
    ]


def _drawn_ray_bounds(insp):
    """The DRAWN extent of every line prop -- the recorder's `ray_actor_bounds` equivalent."""
    lo = [float("inf")] * 3
    hi = [float("-inf")] * 3
    biggest = []
    try:
        props = insp._renderer.GetViewProps()
        props.InitTraversal()
        for _ in range(int(props.GetNumberOfItems())):
            prop = props.GetNextProp()
            try:
                if not bool(prop.GetVisibility()):
                    continue
                mapper = prop.GetMapper()
                data = mapper.GetInput() if mapper is not None else None
                if data is None or int(getattr(data, "GetNumberOfLines", lambda: 0)()) <= 0:
                    continue
                b = [float(v) for v in prop.GetBounds()]
                if any(b[i] > b[i + 1] for i in (0, 2, 4)):
                    continue
                biggest.append([round(v, 1) for v in b])
                for axis in range(3):
                    lo[axis] = min(lo[axis], b[2 * axis])
                    hi[axis] = max(hi[axis], b[2 * axis + 1])
            except Exception:
                continue
    except Exception:
        return None, []
    if lo[0] == float("inf"):
        return None, []
    return [lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]], sorted(biggest, key=lambda b: -b[1])[:6]


def _census(insp):
    bundle = insp.__dict__.get("_current_scene_bundle")
    paths = list(getattr(bundle, "ray_paths", None) or [])
    census: dict[str, int] = {}
    far_x = None
    for path in paths:
        reason = str(getattr(path, "termination_reason", "") or "")
        census[reason] = census.get(reason, 0) + 1
        pts = getattr(path, "points_world", None)
        if pts is None:
            continue
        try:
            top = max(float(p[0]) for p in pts)
        except Exception:
            continue
        far_x = top if far_x is None else max(far_x, top)
    return len(paths), census, far_x


def main() -> int:
    from KrakenOS.UI.capture_open3d_step_workflow_screenshots import _open_3d_inspector, _settle
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    app = KrakenLayoutEditor()
    try:
        app.layout_files["apo75"] = SCENE
        app.load_layout_by_name("apo75")
        insp = _open_3d_inspector(app)
        app._three_d_inspector = insp
        insp.refresh_from_editor(sampling_mode=app._preview_3d_sampling_mode(), force_retrace=True)
        _settle(insp)

        stations = _stations(app.rows)
        print(f"scene: {SCENE.name}")
        print(f"  {'row':<5}{'station':>10}{'thick':>11}  name")
        negative = []
        for index, row in enumerate(app.rows):
            thickness = float(getattr(row, "thickness", 0.0) or 0.0)
            mark = "  <-- NEGATIVE" if thickness < 0.0 else ""
            print(f"  S{index:<4}{stations[index]:>10.3f}{thickness:>11.3f}  {row.name}{mark}")
            if thickness < 0.0:
                negative.append(index)

        total, census, far_x = _census(insp)
        drawn, big = _drawn_ray_bounds(insp)
        print(f"\nAS SAVED:  {total} paths, TRACED far x = {far_x}")
        print(f"           DRAWN line bounds = {[round(v,1) for v in (drawn or [])]}")
        for b in big:
            print(f"             actor {b}")
        for reason, count in sorted(census.items(), key=lambda kv: -kv[1]):
            print(f"    {count:>5}  {reason or '(none)'}")

        if not negative:
            print("\nNo negative gap in this scene -- nothing to neutralise.")
            return 0

        poses_before = _poses(app)
        for index in negative:
            delta = -float(app.rows[index].thickness)  # what the station chain gains
            app.rows[index].thickness = 0.0
            # Hold every downstream pose: station grew by `delta`, so desp_z gives it back.
            for follower in range(index + 1, len(app.rows)):
                app.rows[follower].desp_z = float(app.rows[follower].desp_z) - delta
        poses_after = _poses(app)
        drift = max(
            max(abs(a - b) for a, b in zip(p0, p1)) for p0, p1 in zip(poses_before, poses_after)
        )
        print(f"\nneutralised {len(negative)} negative gap(s); max pose drift = {drift:.3e} mm")

        app._invalidate_preview_scene_trace()
        insp.refresh_from_editor(force_retrace=True)
        _settle(insp)
        total2, census2, far_x2 = _census(insp)
        print(f"\nGAP NEUTRALISED:  {total2} paths, far x = {far_x2}")
        for reason, count in sorted(census2.items(), key=lambda kv: -kv[1]):
            print(f"    {count:>5}  {reason or '(none)'}")

        stray_before = census.get("no_next_intersection", 0)
        stray_after = census2.get("no_next_intersection", 0)
        print(f"\nno_next_intersection: {stray_before} -> {stray_after}")
        if stray_after < stray_before * 0.5:
            print("VERDICT: the negative gap is the cause of the out-of-bound rays.")
        elif stray_after >= stray_before:
            print("VERDICT: NOT the cause -- the strays survive with the chain monotonic.")
        else:
            print("VERDICT: partial -- the negative gap contributes but is not the whole story.")
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
