"""flag 103959 follow-ups: (a) only ONE launch point per face instead of 3,
(b) live ray count 13878. Group launch origins per face, print field/bundle
state + fallback counters + per-source path counts."""
from pathlib import Path
import numpy as np


def main():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["p"] = Path("attachment/om05a_folded_80mm.py").resolve()
    editor.load_layout_by_name("p")
    editor._preview_trace_deferred_until_requested = False
    editor._build_preview_system_rays_bundle(trace_rays=True)

    bundle = editor._last_scene_bundle
    paths = list(getattr(bundle, "ray_paths", []) or [])
    print("paths:", len(paths))
    by_source = {}
    origins_a, origins_b = {}, {}
    for p in paths:
        sid = str(getattr(p, "source_id", "") or "")
        by_source[sid] = by_source.get(sid, 0) + 1
        pts = np.asarray(getattr(p, "points_world", ()), dtype=float)
        if pts.ndim != 2 or pts.shape[0] < 1:
            continue
        o = pts[0]
        key = (round(float(o[0]), 1), round(float(o[1]), 1))
        if abs(float(o[2]) - 0.0) < 2.0:
            origins_a[key] = origins_a.get(key, 0) + 1
        elif abs(float(o[2]) + 50.0) < 2.0:
            origins_b[key] = origins_b.get(key, 0) + 1
    print("by_source:", by_source)
    print("faceA distinct origins:", len(origins_a), sorted(origins_a.items())[:8])
    print("faceB distinct origins:", len(origins_b), sorted(origins_b.items())[:8])
    for attr in ("_preview_field_bundle_count", "_preview_field_ray_count",
                 "_pupil_launch_fallback_count", "_active_preview_sampling_mode",
                 "_folded_preview_ray_count_override"):
        print(attr, "=", editor.__dict__.get(attr, getattr(editor, attr, "<unset>")))
    editor.destroy()


if __name__ == "__main__":
    main()
