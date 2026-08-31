from pathlib import Path

import numpy as np


def main():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["p"] = Path("attachment/om05a_folded.py").resolve()
    editor.load_layout_by_name("p")
    try:
        editor._preview_trace_deferred_until_requested = False
    except Exception:
        pass
    system, rays, bundle = editor._build_preview_system_rays_bundle(trace_rays=True)
    print("folded_sequential engaged:", getattr(editor, "_last_preview_folded_sequential", None))
    overrides = getattr(system, "_optical_solid_output_port_pose_overrides", None)
    print("pose overrides rows:", sorted((overrides or {}).keys()))
    for idx, ov in sorted((overrides or {}).items()):
        org = ov.get("origin") if isinstance(ov, dict) else None
        print(f"  row {idx}: origin {np.round(np.asarray(org, dtype=float),1).tolist() if org is not None else ov}")
    # chief-like ray: the reached path closest to the axis at start
    best = None
    for rp in (getattr(bundle, "ray_paths", None) or []):
        if not bool(getattr(rp, "reaches_image", False)):
            continue
        p = np.asarray(getattr(rp, "points_world", rp), dtype=float)
        if p.ndim != 2 or not np.all(np.isfinite(p[0])):
            continue
        score = abs(p[0][1] - 5.0)
        if best is None or score < best[0]:
            best = (score, rp, p)
    if best:
        _s, rp, p = best
        print("chief hits:")
        sids = list(getattr(rp, "surface_ids", []) or [])
        for k, pt in enumerate(p):
            sid = sids[k] if k < len(sids) else "?"
            print(f"   {k:2d} s{sid}: {np.round(pt,1).tolist()}")
    editor.destroy()


if __name__ == "__main__":
    main()
