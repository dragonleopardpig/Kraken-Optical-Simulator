"""0694 (flag_20260902_143341: "Can check whether these rays focusing on sensor
correct?"): per-cone focus census on the saved om05a scene.

The 3D view shows six cones at the sensor (3 field points per arm). For each
(arm, field) group: extend every reached ray's final segment through a y-scan
around the sensor plane (y = -9.9), find the waist (min RMS transverse spread),
and report waist position vs the plane plus the spot size AT the plane.
"""
from collections import defaultdict
from pathlib import Path

import numpy as np


def main():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["p"] = Path("attachment/om05a_folded.py").resolve()
    editor.load_layout_by_name("p")
    editor._preview_trace_deferred_until_requested = False
    system, rays, bundle = editor._build_preview_system_rays_bundle(trace_rays=True)

    img_row = next(i for i, r in enumerate(editor.rows) if str(r.surface) == "Image")
    SENSOR_Y = float(np.asarray(
        editor._surface_reference_world_point(img_row, system=system), dtype=float)[1])
    print(f"live sensor y {SENSOR_Y:.3f}")
    groups = defaultdict(list)  # (arm, field) -> [(p_last-1, p_last)]
    launch_y = {}
    for rp in (getattr(bundle, "ray_paths", None) or []):
        sid = str(getattr(rp, "source_id", "") or "")
        arm = "B" if sid == "source:faceB" else "A"
        p = np.asarray(getattr(rp, "points_world", rp), dtype=float)
        if p.ndim != 2 or p.shape[0] < 2 or not np.all(np.isfinite(p)):
            continue
        end = p[-1]
        # only rays that made it to the final -y leg toward the sensor
        if not (abs(float(end[1]) - SENSOR_Y) < 6.0 and float(end[0]) < -250.0):
            continue
        a, b = p[-2], p[-1]
        if abs(float(b[1] - a[1])) < 1e-9:
            continue
        key = (arm, round(float(p[0][0]) / 4.0) * 4, round(float(p[0][1]) / 2.0) * 2)
        groups[key].append((a, b, end, p.shape[0]))
        launch_y.setdefault(key, (round(float(p[0][0]), 1), round(float(p[0][1]), 1)))

    print(f"{'arm':>3} {'field':>5} {'launch x,y':>12} {'rays':>5} | "
          f"{'waist y':>8} {'vs plane':>8} {'waist RMS':>10} | {'RMS @plane':>10}")
    ys = np.linspace(SENSOR_Y - 45.0, SENSOR_Y + 25.0, 351)
    for key in sorted(groups.keys()):
        segs = groups[key]
        if len(segs) < 8:
            continue
        nv = np.array([s[3] for s in segs])
        A = np.array([s[0] for s in segs])
        B = np.array([s[1] for s in segs])
        ends = np.array([s[2] for s in segs])
        D = B - A
        best = (None, np.inf)
        rms_plane = None
        for y in ys:
            t = (y - A[:, 1]) / D[:, 1]
            pts = A + t[:, None] * D  # x/z at this y plane
            c = pts.mean(axis=0)
            rms = float(np.sqrt(np.mean((pts[:, 0] - c[0]) ** 2 + (pts[:, 2] - c[2]) ** 2)))
            if rms < best[1]:
                best = (float(y), rms)
            if abs(y - SENSOR_Y) < 1e-6:
                rms_plane = rms
        if rms_plane is None:
            t = (SENSOR_Y - A[:, 1]) / D[:, 1]
            pts = A + t[:, None] * D
            c = pts.mean(axis=0)
            rms_plane = float(np.sqrt(np.mean((pts[:, 0] - c[0]) ** 2 + (pts[:, 2] - c[2]) ** 2)))
        arm = key[0]; field = f"{key[1]}/{key[2]}"
        dv = best[0] - SENSOR_Y
        end_note = (f" end x {ends[:,0].mean():+7.1f} z {ends[:,2].mean():+6.1f}"
                    f" verts {nv.min()}-{nv.max()} (med {int(np.median(nv))})")
        print(f"{arm:>3} {field:>7} {str(launch_y.get(key, '?')):>12} {len(segs):>5} | "
              f"{best[0]:>8.2f} {dv:>+8.2f} {best[1] * 1000:>8.1f}um | {rms_plane * 1000:>8.1f}um" + end_note)
    editor.destroy()


if __name__ == "__main__":
    main()
