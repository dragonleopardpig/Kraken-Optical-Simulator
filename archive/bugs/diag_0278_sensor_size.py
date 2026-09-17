"""flag_20260709_125602_415 -- "I see 4 edges dark" on the REAL vendor scene.

The user's actual sensor is 23x23 (Image circle O32.6 = 23*sqrt2 diagonal), NOT the 39x39 FOV
the bugs/0277 headless fixture verified. On the coaxial-LED design the fold dark edges live at
+/-15..19.5 mm (BS stop STOP_HALF_X=15 under-fills the 39 mm FOV). A 23x23 sensor is only +/-11.5 mm
-- INSIDE the fully-lit fold region -- so the fold dark edges fall OFF this sensor. This repro
re-bins the SAME LED scatter over shrinking sensor windows (39 -> 30 -> 23) to see what the 23x23
heatmap actually reads: uniform, radial vignette, or 2-dark fold. Dumps edge/corner stats + PNGs."""
from __future__ import annotations
import os
import numpy as np

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from KrakenOS.UI.validate_open3d_illumination_heatmap_override import _build_override_only_overlay

RAYS = int(os.environ.get("DIAG_RAYS", "20000"))
SIZES = [39.0, 30.0, 23.0]
OUTDIR = os.path.dirname(__file__)


def edge_stats(rel: np.ndarray) -> dict:
    """Mean of each of the 4 edges + 4 corners of the relative grid (rel[y, x])."""
    ny, nx = rel.shape
    return {
        "left":   float(np.mean(rel[:, 0])),
        "right":  float(np.mean(rel[:, -1])),
        "bottom": float(np.mean(rel[0, :])),
        "top":    float(np.mean(rel[-1, :])),
        "corners": float(np.mean([rel[0, 0], rel[0, -1], rel[-1, 0], rel[-1, -1]])),
        "center": float(np.mean(rel[ny // 2 - 1:ny // 2 + 1, nx // 2 - 1:nx // 2 + 1])),
    }


def main() -> int:
    editor, system, bundle, det_index, fov = _build_override_only_overlay(RAYS)
    if editor is None:
        print("FIXTURE UNAVAILABLE"); return 1
    print(f"built fixture: det_index={det_index}, layout fov={fov}, rays={RAYS}\n")

    for size in SIZES:
        editor._camera_detector_active_dims_overrides = lambda s=size: {int(det_index): (s, s)}
        # The overlay spec is signature-cached on (preview_trace, surface, "source_illumination")
        # -- the sensor dims are NOT in the signature, so bust the cache to re-window per size.
        editor._source_illumination_overlay_cache = None
        samples = editor._source_illumination_hit_samples(system, det_index)
        tm = editor._source_illumination_target_model(samples)
        print(f"  target_model dims = {float(tm.get('active_width_mm',0)):.1f} x "
              f"{float(tm.get('active_height_mm',0)):.1f} mm")
        spec = editor.source_illumination_overlay_spec(system, bundle)
        if not spec:
            print(f"size {size}: NO SPEC"); continue
        rel = np.asarray(spec["relative"], float)
        fold = float(spec["x_edge_ratio"]); perp = float(spec["y_edge_ratio"])
        st = edge_stats(rel)
        dims = spec.get("dims")
        print(f"=== sensor {size:.0f}x{size:.0f}  (half {size/2:.1f} mm)  bins={dims} ===")
        print(f"  fold(x)_edge_ratio = {fold:.3f}   perp(y)_edge_ratio = {perp:.3f}")
        print(f"  L={st['left']:.3f} R={st['right']:.3f} | B={st['bottom']:.3f} T={st['top']:.3f}"
              f" | corners={st['corners']:.3f} center={st['center']:.3f}")
        # how dark is each edge vs center, in %
        c = st["center"] or 1.0
        print(f"  edge/centre: L {st['left']/c:.2f} R {st['right']/c:.2f} "
              f"B {st['bottom']/c:.2f} T {st['top']/c:.2f} corners {st['corners']/c:.2f}")

        pts = np.asarray(spec["points"], float); center = np.asarray(spec["center"], float)
        u = np.asarray(spec["tangent"], float); v = np.asarray(spec["bitangent"], float)
        half = max(float(np.max(np.abs((pts - center) @ u))), float(np.max(np.abs((pts - center) @ v))))
        fig, ax = plt.subplots(figsize=(5.4, 5.6))
        im = ax.imshow(rel, origin="lower", cmap=spec.get("cmap", "gray"), vmin=0.0, vmax=1.0,
                       extent=[-half, half, -half, half], interpolation="bilinear")
        ax.add_patch(Rectangle((-size/2, -size/2), size, size, fill=False, edgecolor="orange", linewidth=2))
        ax.set_title(f"sensor {size:.0f}x{size:.0f}  fold {fold:.3f} perp {perp:.3f}")
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        fig.tight_layout()
        out = os.path.join(OUTDIR, f"_0278_sensor_{int(size)}.png")
        fig.savefig(out, dpi=100); plt.close(fig)
        print(f"  wrote {out}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
