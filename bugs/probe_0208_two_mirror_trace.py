"""Trace a real 2-promoted-mirror AZ85 variant and observe the DISPLAY rays: do they fold
at BOTH mirrors, stay a cone, and reach the camera? Or does the len(records)!=1 fallback
misbehave? Reports the on-axis ray vertices (the fold kinks) + the drawn row positions."""
from __future__ import annotations

import contextlib
import io
from dataclasses import asdict

import numpy as np

from KrakenOS.UI.layout_editor import SurfaceRow
from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor


def _dup(row):
    return SurfaceRow(**asdict(row))


def _onaxis(bundle):
    out = []
    for p in (getattr(bundle, "ray_paths", None) or []):
        pw = np.asarray(getattr(p, "points_world", None), dtype=float)
        if pw.ndim == 2 and pw.shape[0] >= 2 and pw.shape[1] >= 3 and np.linalg.norm(pw[0][:3]) <= 1.0:
            out.append(pw)
    return out


def main():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor = _build_editor(_AZ85)
        rows = list(editor.rows)
        mirror2 = _dup(rows[1])          # duplicate the promoted mirror
        mirror2.name = "Promoted OPTICAL STEP optical solid (2nd fold)"
        # shorten the long back gap (row 7 = 150.368) so mirror2 sits partway down the +X leg
        rows[7].thickness = 90.0
        mirror2.thickness = 60.0          # mirror2 -> Image distance along the folded leg
        new_rows = rows[:8] + [mirror2] + [rows[8]]   # ...lens gap, mirror2, Image
        editor.rows = new_rows
        editor._normalize_special_rows()
        system, _rays, bundle = editor._build_preview_system_rays_bundle(update_state=True)

    n = len(editor.rows)
    print(f"2-mirror scene: {n} rows (mirrors at 1 and 8)")
    diag = {}
    try:
        diag = editor._preview_sampling_diagnostics() if hasattr(editor, "_preview_sampling_diagnostics") else {}
    except Exception:
        pass
    print(f"folded_sequential_engaged? trace backend / mode via bundle tags below")

    print("\ndrawn row world refs (X,Y,Z):")
    for i in range(n):
        try:
            r = np.asarray(editor._surface_reference_world_point(i, system=system), dtype=float).reshape(3)
            print(f"  row {i:2d} [{str(getattr(editor.rows[i],'surface','?')):>10}] ({r[0]:8.2f},{r[1]:7.2f},{r[2]:8.2f})")
        except Exception as exc:
            print(f"  row {i:2d} ref FAILED {exc!r}")

    oa = _onaxis(bundle)
    print(f"\non-axis rays: {len(oa)}")
    if oa:
        p = oa[0]
        print("on-axis ray #0 vertices (X,Y,Z) -- each kink = a fold/refraction:")
        for v in p:
            print(f"   ({v[0]:8.2f},{v[1]:7.2f},{v[2]:8.2f})")
        end = np.asarray([q[-1][:3] for q in oa])
        print(f"\nendpoint mean=({end[:,0].mean():.2f},{end[:,1].mean():.2f},{end[:,2].mean():.2f}) "
              f"spread X{np.ptp(end[:,0]):.2f} Y{np.ptp(end[:,1]):.2f} Z{np.ptp(end[:,2]):.2f}")
        # bounding box of all ray vertices -> did the beam go anywhere sane?
        allv = np.vstack([q[:, :3] for q in oa])
        print(f"all on-axis vertices bbox: X[{allv[:,0].min():.1f},{allv[:,0].max():.1f}] "
              f"Y[{allv[:,1].min():.1f},{allv[:,1].max():.1f}] Z[{allv[:,2].min():.1f},{allv[:,2].max():.1f}]")


if __name__ == "__main__":
    main()
