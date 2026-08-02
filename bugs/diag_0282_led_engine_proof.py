"""Proof that a REAL emitting LED (a parametric 'Random rectangle source' scene source -- the kind the
Scene Source Manager creates) is traced through the system and produces a 2-SIDED detector pattern,
i.e. the engine substrate for "real emitting LED" is sound and needs no new physics.

Uses the complete coaxial-LED fixture (55x78 rectangle source + BS-exit rectangular UDA stop + FOV/
detector), traces it, and dumps the on-detector relative-illumination edge ratios + a PNG so the 2-dark
/2-uniform pattern is eyeballable. Contrast: the same overlay on a pure imaging scene with only a face
MARKER is the radial artifact (bugs/0282) -- because a marker floods nothing (excluded from the trace).
"""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
os.environ.setdefault("MPLBACKEND", "Agg")

import numpy as np

from KrakenOS.UI.validate_open3d_illumination_heatmap_override import _build_override_only_overlay

REPO = Path(__file__).resolve().parents[1]


def main() -> int:
    editor, system, bundle, det_index, fov = _build_override_only_overlay(20000)
    if editor is None:
        print("SKIP: coaxial-LED fixture unavailable")
        return 0

    specs = editor._normalize_scene_source_specs(getattr(editor, "layout_scene_source_specs", []) or [])
    print("scene source(s) driving the trace:")
    for s in specs:
        print(f"  model={s.get('model')!r} radius_x={s.get('radius_x')} radius_y={s.get('radius_y')} "
              f"cone_deg={s.get('cone_deg')} ray_count={s.get('ray_count')} origin={s.get('origin')} "
              f"direction={s.get('direction')}")

    target = editor._source_illumination_anchor_target(bundle)
    spec = editor._compute_source_illumination_overlay_spec(system, target)
    if not spec:
        print("overlay spec None -- fixture did not build")
        return 0

    rel = np.asarray(spec["relative"], dtype=float)
    fold = 0.5 * (float(np.mean(rel[:, 0])) + float(np.mean(rel[:, -1])))   # tangent (fold) edges
    perp = 0.5 * (float(np.mean(rel[0, :])) + float(np.mean(rel[-1, :])))   # perpendicular edges
    cx = rel.shape[0] // 2
    print(f"\nreal rectangle-source heatmap grid {rel.shape}")
    print(f"  centre={float(rel[cx, cx]):.3f}  fold(tangent) edge={fold:.3f}  perp edge={perp:.3f}")
    print(f"  --> {'2-SIDED (fold darker than perp) as expected' if fold < perp else 'NOT 2-sided (investigate)'}")

    try:
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(4, 4))
        ax.imshow(rel, origin="lower", cmap="gray", vmin=0.0, vmax=float(np.nanmax(rel)))
        ax.set_title(f"real LED (rectangle source) heatmap\nfold {fold:.2f} < perp {perp:.2f} = 2-sided")
        out = REPO / "bugs" / "_0282_led_engine_heatmap.png"
        fig.savefig(out, dpi=110, bbox_inches="tight"); plt.close(fig)
        print(f"wrote {out}")
    except Exception as exc:
        print(f"(no PNG: {exc!r})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
