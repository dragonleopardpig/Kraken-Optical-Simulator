"""0680: where do the aimed face-B rays die? Full-count endpoint census."""
from pathlib import Path

import numpy as np


def main():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["p"] = Path("attachment/om05a_symB_work.py").resolve()
    editor.load_layout_by_name("p")
    cls = type(editor)
    editor._build_additive_imaging_source_bundles = (
        lambda wl, full_count=False: cls._build_additive_imaging_source_bundles(
            editor, wl, full_count=True
        )
    )
    editor._preview_trace_deferred_until_requested = False
    system, rays, bundle = editor._build_preview_system_rays_bundle(trace_rays=True)
    zones = {
        "a_launch_leg (z<-40, x>-30)": 0,
        "b_train/column (x>-30)": 0,
        "c_leg -30..-150": 0,
        "d_lens block -150..-250": 0,
        "e_mirror2/sensor x<-250": 0,
    }
    reach = 0
    reach_x = []
    sensor_pts = []
    for rp in (bundle.ray_paths or []):
        if str(getattr(rp, "source_id", "") or "") != "source:faceB":
            continue
        p = np.asarray(getattr(rp, "points_world", rp), dtype=float)
        if p.ndim != 2 or len(p) < 2 or not np.all(np.isfinite(p[-1])):
            continue
        end = p[-1]
        if end[0] > -30:
            if end[2] < -40:
                zones["a_launch_leg (z<-40, x>-30)"] += 1
            else:
                zones["b_train/column (x>-30)"] += 1
        elif end[0] > -150:
            zones["c_leg -30..-150"] += 1
        elif end[0] > -250:
            zones["d_lens block -150..-250"] += 1
        else:
            zones["e_mirror2/sensor x<-250"] += 1
        if abs(end[0] + 272.7) < 25 and abs(end[1] + 11) < 25:
            reach += 1
            reach_x.append(p[0][0])
            sensor_pts.append(end)
    total = sum(zones.values())
    print(f"faceB rays: {total}, near-sensor: {reach}")
    for name, count in zones.items():
        print(f"  {name}: {count}")
    if reach_x:
        rx = np.asarray(reach_x)
        print(f"reaching launch x: {rx.min():.1f}..{rx.max():.1f}, mean {rx.mean():.1f}")
        sp = np.asarray(sensor_pts)
        print(f"sensor pts mean {np.round(sp.mean(axis=0),1).tolist()}, "
              f"y spread {sp[:,1].std():.1f}, z spread {sp[:,2].std():.1f}")
    # every faceB ray that makes it past the lens block: where does it end?
    ends_far = []
    launches_far = []
    for rp in (bundle.ray_paths or []):
        if str(getattr(rp, "source_id", "") or "") != "source:faceB":
            continue
        p = np.asarray(getattr(rp, "points_world", rp), dtype=float)
        if p.ndim != 2 or len(p) < 2 or not np.all(np.isfinite(p[-1])):
            continue
        if p[-1][0] < -250:
            ends_far.append(p[-1])
            launches_far.append(p[0])
    if ends_far:
        E = np.asarray(ends_far)
        L = np.asarray(launches_far)
        print(f"past-lens rays: {len(E)}")
        print(f"  end y: {E[:,1].min():.1f}..{E[:,1].max():.1f} mean {E[:,1].mean():.1f}")
        print(f"  end z: {E[:,2].min():.1f}..{E[:,2].max():.1f} mean {E[:,2].mean():.1f}")
        print(f"  launch y span: {L[:,1].min():.1f}..{L[:,1].max():.1f}")
        print(f"  launch z values: {sorted(set(np.round(L[:,2],1).tolist()))[:6]}")
    # chain comparison: where do reaching chain rays land?
    chain_ends = []
    for rp in (bundle.ray_paths or []):
        sid = str(getattr(rp, "source_id", "") or "")
        if sid == "source:faceB" or not bool(getattr(rp, "reaches_image", False)):
            continue
        p = np.asarray(getattr(rp, "points_world", rp), dtype=float)
        if p.ndim == 2 and np.all(np.isfinite(p[-1])):
            chain_ends.append(p[-1])
    if chain_ends:
        C = np.asarray(chain_ends)
        print(f"chain reachers: {len(C)}, end mean {np.round(C.mean(axis=0),1).tolist()}, "
              f"y {C[:,1].min():.1f}..{C[:,1].max():.1f}, z {C[:,2].min():.1f}..{C[:,2].max():.1f}")
    editor.destroy()


if __name__ == "__main__":
    main()
