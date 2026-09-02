"""0692: why did the field-sweep grid patch produce ZERO binned chain launches?

Same load recipe as the 0672 guard + the sweep's grid patch, but report a census:
was the patch consumed, how many ray paths exist, what source_ids/launch points.
FAILS LOUDLY instead of printing empty tables.
"""
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

    calls = []
    ys = [float(y) for y in np.linspace(-16.0, 16.0, 33)]
    pairs = [(0.0, y) for y in ys]
    editor._sample_imaging_field_grid_pairs = lambda: (calls.append(1), list(pairs))[1]

    system, rays, bundle = editor._build_preview_system_rays_bundle(trace_rays=True)
    paths = list(getattr(bundle, "ray_paths", None) or [])
    print("grid patch consumed:", len(calls), "times")
    print("ray paths:", len(paths))
    print("pupil fallback count:", getattr(editor, "_pupil_launch_fallback_count", "n/a"))
    sids = Counter(str(getattr(rp, "source_id", "") or "") for rp in paths)
    print("source_id census:", dict(sids))
    shown = 0
    for rp in paths:
        sid = str(getattr(rp, "source_id", "") or "")
        if sid == "source:faceB":
            continue
        p = np.asarray(getattr(rp, "points_world", rp), dtype=float)
        if p.ndim != 2 or p.shape[0] < 2:
            print("  chain path with bad shape:", getattr(p, "shape", None))
            continue
        if shown < 8:
            print(f"  chain launch {np.round(p[0], 2)} -> end {np.round(p[-1], 2)} "
                  f"finite0={bool(np.all(np.isfinite(p[0])))}")
            shown += 1
    if not paths:
        raise SystemExit("FAIL LOUDLY: no ray paths at all")
    editor.destroy()


if __name__ == "__main__":
    main()
