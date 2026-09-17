"""0695: where do the rays die on the rebuilt scene? Termination census + two
representative chain polylines."""
from collections import Counter
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

    paths = list(getattr(bundle, "ray_paths", None) or [])
    print("paths:", len(paths))
    for i, row in enumerate(editor.rows):
        print(f"  row {i:2d}: {str(row.surface):10s} {str(row.name)[:40]}")
    term = Counter()
    ends = Counter()
    shown = 0
    for rp in paths:
        sid = str(getattr(rp, "source_id", "") or "")
        p = np.asarray(getattr(rp, "points_world", rp), dtype=float)
        if p.ndim != 2 or p.shape[0] < 2:
            continue
        t = str(getattr(rp, "termination", "") or getattr(rp, "termination_reason", "") or "?")
        term[(sid or "chain", t)] += 1
        e = p[-1]
        ends[(sid or "chain", round(float(e[0]) / 20) * 20, round(float(e[1]) / 10) * 10,
              round(float(e[2]) / 20) * 20)] += 1
        want = (sid != "source:faceB" and t == "stopped_at_surface_10" and shown in (0, 1)) or                (sid == "source:faceB" and t == "stopped_at_surface_8" and shown in (2, 3))
        if want:
            shown += 1
            print(f"--- {sid or 'chain'} {t} launch {np.round(p[0], 2)} ({p.shape[0]} verts)")
            for v in p:
                print(f"    ({v[0]:+8.2f}, {v[1]:+8.2f}, {v[2]:+8.2f})")
    print("\nterminations:")
    for k, n in term.most_common(12):
        print(f"  {k}: {n}")
    print("\nend clusters (x,y,z rounded):")
    for k, n in ends.most_common(12):
        print(f"  {k}: {n}")
    editor.destroy()


if __name__ == "__main__":
    main()
