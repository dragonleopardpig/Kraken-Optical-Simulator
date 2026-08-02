"""Visual proof for bugs/0207: on the folded AZ85 RA-mirror the reflected display rays now
REACH the drawn image plane / detector, instead of terminating ~desp_z (12.5 mm) short of it.

Renders the same X-vs-Z projection the user sees (looking down -Y): incoming beam rising in
+Z at X=0, folding at the '/' mirror, outgoing arm running +X at Z=71.897. Plots the traced
ray polylines, the NEW drawn detector (now coincident with the ray tips), and a dashed marker
at the OLD detector position (drawn +desp_z, where the rays used to fall short). No VTK -- pure
matplotlib, so it is segfault-safe headless.

Out: attachment/bugs_0207_rays_reach_detector.png (eyeball vs flag_20260702_183320_903)."""
from __future__ import annotations

import contextlib
import io
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor


def main() -> int:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor = _build_editor(_AZ85)
        system, _rays, bundle = editor._build_preview_system_rays_bundle(update_state=True)
        n = len(editor.rows)
        detector_x = float(
            np.asarray(editor._surface_reference_world_point(n - 1, system=system), dtype=float).reshape(3)[0]
        )
    paths = [np.asarray(getattr(p, "points_world", None), dtype=float) for p in (bundle.ray_paths or [])]
    paths = [p for p in paths if p.ndim == 2 and p.shape[0] >= 2 and p.shape[1] >= 3]

    fig, ax = plt.subplots(figsize=(13, 5))
    for p in paths:
        ax.plot(p[:, 0], p[:, 2], color="#7a9e2f", lw=0.35, alpha=0.5)
    # on-axis ray tips (where the rays actually land)
    tips = np.asarray(
        [p[-1, [0, 2]] for p in paths if np.linalg.norm(p[0, :3]) <= 1.0 and p[:, 0].max() > 250.0]
    )
    ray_end_x = float(tips[:, 0].mean()) if tips.size else float("nan")

    old_detector_x = detector_x + 12.5  # the pre-0207 overshoot (+desp_z)
    ax.axvline(detector_x, color="#1f77b4", lw=2.0, label=f"drawn detector (fixed) X={detector_x:.1f}")
    ax.axvline(old_detector_x, color="#d62728", lw=1.4, ls="--",
               label=f"OLD detector X={old_detector_x:.1f} (rays fell 12.5 short)")
    ax.axvline(ray_end_x, color="black", lw=0.8, ls=":", label=f"ray tips X={ray_end_x:.1f}")
    ax.set_xlabel("X (mm)  -- folded optical axis")
    ax.set_ylabel("Z (mm)")
    ax.set_title("bugs/0207: folded AZ85 rays now REACH the detector (blue) -- old detector (red dashed) was +desp_z beyond")
    ax.legend(loc="upper left", fontsize=8)
    ax.set_aspect("equal", adjustable="datalim")

    out = Path("attachment/bugs_0207_rays_reach_detector.png").resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out, dpi=130)
    print(f"ray tips X={ray_end_x:.3f} | fixed detector X={detector_x:.3f} | gap={detector_x-ray_end_x:+.3f} mm")
    print(f"old detector would have been X={old_detector_x:.3f} (gap {old_detector_x-ray_end_x:+.3f} mm)")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
