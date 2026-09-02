"""0694: WHERE do the bad cones' paths diverge from the good ones?

The focus census found two focal planes (3 cones each) and a +-1 vertex-count
difference between bad and good cones of the same arm -- a path-class split.
Print one representative polyline per (arm, launch-x) group, vertex by vertex,
so the diverging station and the extra/missing crossing are visible.
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

    SENSOR_Y = -9.9
    groups = defaultdict(list)
    for rp in (getattr(bundle, "ray_paths", None) or []):
        sid = str(getattr(rp, "source_id", "") or "")
        arm = "B" if sid == "source:faceB" else "A"
        p = np.asarray(getattr(rp, "points_world", rp), dtype=float)
        if p.ndim != 2 or p.shape[0] < 2 or not np.all(np.isfinite(p)):
            continue
        end = p[-1]
        if not (abs(float(end[1]) - SENSOR_Y) < 6.0 and float(end[0]) < -250.0):
            continue
        key = (arm, round(float(p[0][0]) / 4.0) * 4)
        groups[key].append(p)

    for key in sorted(groups.keys()):
        plist = groups[key]
        if len(plist) < 8:
            continue
        # the most-typical polyline: median vertex count, then the ray whose
        # launch is closest to the group's mean launch
        counts = np.array([p.shape[0] for p in plist])
        med = int(np.median(counts))
        cands = [p for p in plist if p.shape[0] == med]
        mean_launch = np.mean([p[0] for p in plist], axis=0)
        rep = min(cands, key=lambda p: float(np.linalg.norm(p[0] - mean_launch)))
        print(f"\n=== arm {key[0]} launch x {key[1]:+d} ({len(plist)} rays, verts med {med}) ===")
        for i in range(rep.shape[0]):
            v = rep[i]
            seg = ""
            if i > 0:
                d = v - rep[i - 1]
                seg = f"  seg {np.linalg.norm(d):7.2f} dir ({d[0]/max(np.linalg.norm(d),1e-9):+.2f},{d[1]/max(np.linalg.norm(d),1e-9):+.2f},{d[2]/max(np.linalg.norm(d),1e-9):+.2f})"
            print(f"  v{i:02d} ({v[0]:+8.2f}, {v[1]:+8.2f}, {v[2]:+8.2f}){seg}")
    editor.destroy()


if __name__ == "__main__":
    main()
