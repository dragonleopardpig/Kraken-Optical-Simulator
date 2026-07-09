"""diag for flag_20260709_150933_595 -- "still seems 4 sided dark edges to me".

Loads the user's ACTUAL loaded scene (attachment/machine_vision_150mm_test.py -- a full
MV-150 imaging system: object -> BS cube -> real lens (thin-lens groups + aperture stop
r=9.678) -> 23.04x23.04 HR25 sensor, with scene_sources: []), traces it exactly as the Open
3D inspector does (world_envelope preview, HR25 camera override), computes the illumination
overlay spec, and dumps what actually reaches the detector so we can tell whether the radial
4-dark is CORRECT lens relative-illumination or a heatmap binning artifact.

Run: PYVISTA_OFF_SCREEN=true .devenv/state/venv/bin/python bugs/diag_0280_real_scene_heatmap.py
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
os.environ.setdefault("MPLBACKEND", "Agg")

import numpy as np

REPO = Path(__file__).resolve().parents[1]
SCENE = REPO / "attachment" / "machine_vision_150mm_test.py"
HR25_MM = 23.04  # Allied Vision hr25MCX active sensor (camera_database.py)


def _load_scene_module():
    spec = importlib.util.spec_from_file_location("user_mv150_scene", SCENE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    import KrakenOS as Kos
    from KrakenOS.UI.render_layout_snapshot import _rows_from_layout_info, _snapshot_editor
    from KrakenOS.UI.scene_builder import build_scene_bundle

    module = _load_scene_module()
    surfaces = module.SURFACES
    settings = dict(module.SETTINGS)

    rows = _rows_from_layout_info({"surfaces": surfaces, "settings": settings})
    editor = _snapshot_editor(rows, settings)

    det_index = len(rows) - 1
    print(f"rows={len(rows)}  det_index={det_index}  last_surface={rows[det_index].surface!r}")
    # HR25 vendor sensor lives in the runtime override (bugs/0276), not the row block.
    editor._camera_detector_active_dims_overrides = lambda: {int(det_index): (HR25_MM, HR25_MM)}

    system = module.build_runtime_system()
    rays = Kos.raykeeper(system)
    wavelength = float(settings.get("wavelength", "0.546") or 0.546)
    max_radius = max((max(r.diameter / 2.0, 0.5) for r in rows), default=1.0)

    # The 3D inspector traced with world_envelope (state.json committed_tag).
    editor._trace_preview_rays(
        system, rays, wavelength, max_radius,
        allow_full_pupil=False, sampling_mode="world_envelope",
    )
    editor.last_system, editor.last_rays = system, rays

    sources = editor._collect_scene_sources(wavelength=wavelength)
    print(f"scene_sources resolved: {len(sources)}  (settings scene_sources: {len(settings.get('scene_sources', []))})")

    bundle = build_scene_bundle(
        rows=rows, system=system, rays=rays, sources=sources,
        field_count=max(1, editor.__dict__.get("_preview_field_bundle_count", 1)),
        ray_count_per_field=max(1, editor.__dict__.get("_preview_field_ray_count", 1)),
    )
    editor._last_scene_bundle = bundle

    records = editor._collect_ray_analysis_records(scene_bundle=bundle)
    print(f"ray analysis records: {len(records)}")

    # Raw detector-hit samples (pre-binning): x/y spread tells us meridional-line vs 2D-cloud.
    samples = editor._source_illumination_hit_samples(system, det_index)
    xs = np.asarray(samples.get("x", []), dtype=float) if isinstance(samples, dict) else np.asarray([])
    ys = np.asarray(samples.get("y", []), dtype=float) if isinstance(samples, dict) else np.asarray([])
    print(f"detector hit samples: n={xs.size}")
    if xs.size:
        print(f"  x range [{xs.min():.3f}, {xs.max():.3f}]  spread(std)={xs.std():.3f}")
        print(f"  y range [{ys.min():.3f}, {ys.max():.3f}]  spread(std)={ys.std():.3f}")
        # How many DISTINCT x columns? A pure meridional fan collapses to x~0.
        ux = np.unique(np.round(xs, 2))
        print(f"  distinct x columns (rounded 0.01mm): {ux.size}")

    # Raw scatter over the sensor outline -- does the imaging sample TILE the 23mm sensor,
    # or cluster in the centre (leaving edges dark for lack of rays, not lack of light)?
    try:
        import matplotlib.pyplot as plt
        half = 0.5 * HR25_MM
        fig, ax = plt.subplots(figsize=(4, 4))
        ax.scatter(xs, ys, s=8, c="tab:blue")
        ax.add_patch(plt.Rectangle((-half, -half), HR25_MM, HR25_MM, fill=False, ec="orange", lw=1.5))
        ax.set_xlim(-half - 2, half + 2); ax.set_ylim(-half - 2, half + 2)
        ax.set_aspect("equal"); ax.set_title(f"{xs.size} detector hits vs 23mm sensor")
        out = REPO / "bugs" / "_0280_real_scene_scatter.png"
        fig.savefig(out, dpi=110, bbox_inches="tight"); plt.close(fig)
        print(f"wrote {out}")
    except Exception as exc:
        print(f"(no scatter PNG: {exc!r})")

    spec = editor.source_illumination_overlay_spec(system, bundle)
    if not spec:
        print("OVERLAY SPEC: None (fewer than 50 detector hits, or no target) -- the radial")
        print("  pattern the user sees is NOT this data-driven heatmap. Investigate other overlay.")
        return 0

    rel = np.asarray(spec["relative"], dtype=float)
    print(f"OVERLAY SPEC ok: grid {rel.shape}  fold(x_edge)={spec['x_edge_ratio']:.3f}  perp(y_edge)={spec['y_edge_ratio']:.3f}")
    if rel.ndim == 2 and rel.size:
        left = float(np.mean(rel[:, 0])); right = float(np.mean(rel[:, -1]))
        top = float(np.mean(rel[0, :])); bot = float(np.mean(rel[-1, :]))
        cx, cy = rel.shape[0] // 2, rel.shape[1] // 2
        centre = float(rel[cx, cy])
        corners = [float(rel[0, 0]), float(rel[0, -1]), float(rel[-1, 0]), float(rel[-1, -1])]
        print(f"  edges  L={left:.3f} R={right:.3f} T={top:.3f} B={bot:.3f}")
        print(f"  corners {['%.3f' % c for c in corners]}  mean={np.mean(corners):.3f}")
        print(f"  centre={centre:.3f}")
        edge_mean = np.mean([left, right, top, bot])
        corner_mean = float(np.mean(corners))
        print(f"  --> edge_mean={edge_mean:.3f}  corner_mean={corner_mean:.3f}")
        if corner_mean < edge_mean < centre:
            print("  PATTERN: RADIAL (corners darkest < edges < centre) -- consistent with a lens")
            print("           relative-illumination / cos^4 falloff (4-sided dark).")
        elif abs(left - right) > 0.15 and abs(top - bot) < 0.1:
            print("  PATTERN: 2-DARK fold (L/R columns dark, T/B uniform) -- coverage effect.")
        else:
            print("  PATTERN: other/mixed.")

    # Render the relative grid so we can eyeball vs the user's screenshot.
    try:
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(4, 4))
        ax.imshow(rel, origin="lower", cmap="gray", vmin=0.0, vmax=float(np.nanmax(rel)))
        ax.set_title(f"real scene heatmap {rel.shape}\nfold={spec['x_edge_ratio']:.2f} perp={spec['y_edge_ratio']:.2f}")
        out = REPO / "bugs" / "_0280_real_scene_heatmap.png"
        fig.savefig(out, dpi=110, bbox_inches="tight")
        print(f"wrote {out}")
    except Exception as exc:
        print(f"(no PNG: {exc!r})")

    # CONTROL: feed the SAME overlay builder a dense UNIFORM grid of hits that tiles the whole
    # 23mm sensor. If it reads ~uniform (centre~edge~corner), the density->relative method is
    # correct FOR A TILING SAMPLE -- proving the real-scene 4-dark is a SPARSE-SAMPLE artifact
    # (edges dark for lack of imaging rays), not lens relative-illumination.
    print("\n--- CONTROL: dense uniform tiling sample through the same overlay builder ---")
    try:
        from KrakenOS.UI.source_illumination_analysis import (
            source_illumination_map_data_from_samples,
        )
        from KrakenOS.UI.services.source_illumination_overlay import build_source_illumination_overlay
        half = 0.5 * HR25_MM
        gx, gy = np.meshgrid(np.linspace(-half, half, 80), np.linspace(-half, half, 80))
        ux, uy = gx.ravel(), gy.ravel()
        u_samples = {
            "x": ux, "y": uy, "count": ux.size,
            "target_surface": det_index, "target_name": rows[det_index].name,
            "extent": {"x_min": -half, "x_max": half, "y_min": -half, "y_max": half},
        }
        map_u = source_illumination_map_data_from_samples(u_samples, bins=10)
        ov_u = build_source_illumination_overlay(
            map_u, center=spec["center"], normal=spec["normal"], tangent=spec["tangent"],
        )
        if ov_u:
            ru = np.asarray(ov_u["relative"], dtype=float)
            cxy = ru.shape[0] // 2
            print(f"  uniform tiling: grid{ru.shape} centre={ru[cxy, cxy]:.2f} "
                  f"edge={np.mean([ru[:,0].mean(), ru[:,-1].mean(), ru[0,:].mean(), ru[-1,:].mean()]):.2f} "
                  f"corner={np.mean([ru[0,0], ru[0,-1], ru[-1,0], ru[-1,-1]]):.2f}  (expect ~1.0 all)")
        else:
            print("  uniform control: overlay None")
    except Exception as exc:
        print(f"  (control failed: {exc!r})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
