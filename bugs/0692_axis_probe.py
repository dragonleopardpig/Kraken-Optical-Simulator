"""0692: why is the drawn optical axis broken/slanted on the seated om05a scene?

Print every row's folded-axis anchor + direction (the inputs to the multi-fold
axis reconstruction) plus the branch grouping / vertices the builder derives,
so the slanted segment can be attributed to a specific branch or vertex.
"""
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
    editor.open_3d_view()
    editor.update_idletasks()
    editor.update()
    inspector = editor._three_d_inspector

    mirror_rows = set(editor._promoted_mirror_fold_row_indices())
    try:
        bs_rows = set(editor._promoted_beam_splitter_row_indices())
    except Exception:
        bs_rows = set()
    z_positions = editor._row_z_positions()
    print("mirror rows:", sorted(mirror_rows), " bs rows:", sorted(bs_rows))
    print(f"{'idx':>3} {'label':<32} {'anchor':<28} {'direction':<24} note")
    for idx, row in enumerate(editor.rows):
        label = str(getattr(row, "label", "") or getattr(row, "comment", "") or "")[:32]
        note = "MIRROR" if idx in mirror_rows else ("BS" if idx in bs_rows else "")
        anchor, direction = inspector._folded_axis_row_anchor_direction(idx, z_positions)
        if anchor is None:
            print(f"{idx:>3} {label:<32} {'(none)':<28} {'':<24} {note}")
            continue
        a = np.round(anchor, 2)
        d = np.round(direction, 3)
        print(f"{idx:>3} {label:<32} {str(a):<28} {str(d):<24} {note}")

    fold_z = inspector._folded_axis_incoming_fold_point_z()
    print("incoming fold point z:", fold_z)
    bounds = np.asarray([-80.0, 80.0, -80.0, 80.0, -80.0, 80.0], dtype=float)
    if fold_z is not None and np.isfinite(float(fold_z)):
        recs = inspector._folded_multifold_axis_guide_records(bounds, float(fold_z))
        print(f"multifold records: {len(recs)}")
        for r in recs:
            pts = np.round(np.asarray(r["points"], dtype=float), 2)
            seg = pts[1] - pts[0]
            seg = seg / max(np.linalg.norm(seg), 1e-9)
            print(f"  {r['axis_id']}: {pts[0]} -> {pts[1]}  dir {np.round(seg, 3)}")
    full = inspector._optical_axis_records_for_3d(bundle)
    print(f"full axis records: {len(full)}")
    for r in full:
        pts = np.asarray(r["points"], dtype=float)
        if pts.ndim == 2 and pts.shape[0] >= 2:
            seg = pts[-1] - pts[0]
            seg = seg / max(np.linalg.norm(seg), 1e-9)
            print(f"  {r['axis_id']} [{r['axis_kind']}]: {np.round(pts[0], 2)} -> "
                  f"{np.round(pts[-1], 2)}  dir {np.round(seg, 3)}  npts {pts.shape[0]}")
    editor.destroy()


if __name__ == "__main__":
    main()
