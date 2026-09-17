"""0680: why do end-inserted pinned B wedges cost the chain its reach?
Compare the Image row's WORLD frame + chain endpoint census, stage 0 vs stage 2."""
from pathlib import Path

import numpy as np


def load(scene):
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["p"] = Path(scene).resolve()
    editor.load_layout_by_name("p")
    return editor


def probe(scene, tag):
    from KrakenOS.UI.nonseq_output_ports import build_optical_solid_output_port_pose_overrides

    editor = load(scene)
    overrides = build_optical_solid_output_port_pose_overrides(editor.rows)
    for i, row in enumerate(editor.rows):
        if str(row.surface) in ("Image",) or "mirror 2" in str(row.name).lower() or "prism B" in str(row.name):
            ov = overrides.get(i)
            pos = None
            if isinstance(ov, dict):
                pos = np.round(np.asarray(ov.get("position", (np.nan,) * 3), dtype=float), 1).tolist()
            print(f"{tag}: row {i} {row.name!r} override pos {pos}")
    editor._preview_trace_deferred_until_requested = False
    system, rays, bundle = editor._build_preview_system_rays_bundle(trace_rays=True)
    ends = []
    for rp in (bundle.ray_paths or []):
        sid = str(getattr(rp, "source_id", "") or "")
        if sid == "source:faceB":
            continue
        p = np.asarray(getattr(rp, "points_world", rp), dtype=float)
        if p.ndim == 2 and np.all(np.isfinite(p[-1])):
            ends.append(p[-1])
    ends = np.asarray(ends)
    if len(ends):
        print(f"{tag}: chain ends mean {np.round(ends.mean(axis=0),1).tolist()}, "
              f"x<-200: {int(np.sum(ends[:,0] < -200))}/{len(ends)}")
    editor.destroy()


if __name__ == "__main__":
    probe("attachment/om05a_folded.py", "stage0")
    probe("attachment/om05a_symB_work.py", "stage2")
