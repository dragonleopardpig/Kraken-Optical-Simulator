"""Prototype: the CORRECT two-arm beam-splitter architecture (display-fold, not non-seq).

The user's insight (2026-06-19), after a long fight with the non-sequential folded trace:

  1) The straight 150 mm MV lens already focuses perfectly.
  2) The straight 120 mm MV lens already focuses perfectly.
  3) Overlap them on a COMMON object grid.
  4) Pick where the beam splitter sits; bend ONE arm's *display* 90 deg there.
  5) Done. Cascades just straighten each leaf's path the same way.

Why this is right: folding an arm INSIDE the scene (tilt_x=-90 + decenter) forced the whole
thing through a non-sequential trace ACROSS the 50 mm splitter cube. That is where every bug
came from -- the beam-focuses-before-the-lens seam, the 199x ray bounce on the folded
detector, the cross-arm strays, and the exit-pupil detector placement. Traced STRAIGHT and
SEQUENTIAL, each arm's optics are always correct; the splitter becomes a pure DISPLAY fold.

This prototype traces each imaging arm's unfolded leaf reference sequentially and folds the
reflect arm's polylines +Y at the splitter plane. Both arms land their detector at the real
image (transmit z=596, reflect folded to Y=391). Run it to regenerate /tmp/proto_fold.png.

The production wiring replaces _trace_per_branch_bundles' non-seq launch with this:
per-arm sequential trace + per-arm detector at the real image + display fold of the bent arms.
"""
from __future__ import annotations

import numpy as np

Z_SPLITTER = 90.0


def fold_reflect_polyline(points: np.ndarray, z_splitter: float = Z_SPLITTER) -> np.ndarray:
    """Bend a straight reflect-arm polyline 90 deg +Y at the splitter plane (display only)."""
    out = np.asarray(points, dtype=float).copy()
    past = out[:, 2] > z_splitter
    z = out[past, 2].copy()
    y = out[past, 1].copy()
    out[past, 1] = z - z_splitter   # along-arm distance becomes +Y
    out[past, 2] = z_splitter + y   # transverse becomes z (a 90 deg fold at the splitter)
    return out


def build_two_arm_fold(rows, settings):
    """Trace each imaging arm STRAIGHT (sequential) and return per-arm (folded) polylines + detector."""
    import KrakenOS as Kos
    from KrakenOS.UI.layout_editor import SurfaceRow, _build_system_from_specs
    from KrakenOS.UI.render_layout_snapshot import _snapshot_editor
    from KrakenOS.UI.services.paraxial_tools import _branch_leaf_rows, ParaxialToolsMixin

    arms = []
    for selector in ("transmit", "reflect"):
        leaf = _branch_leaf_rows(rows, selector)
        ref, _ = ParaxialToolsMixin._paraxial_reference_rows_for_layout(None, leaf, unfold_branch_tilts=True)
        ref_rows = [SurfaceRow(**{f.name: getattr(r, f.name) for f in r.__dataclass_fields__.values()}) for r in ref]
        # GLASS-PLATE CORRECTION (essential): the splitter is a GLASS cube, not air. A glass
        # plate of thickness t in the converging beam pushes the focus further by t(1-1/n)
        # (~16.5 mm for a 50 mm BK7 cube). Trace the reference THROUGH the cube glass -- split
        # the splitter's air plate into [glass cube] + [residual air gap] -- so the detector
        # lands at the real image, not ~17 mm short.
        bs_index, cube_thickness, cube_glass = 1, 50.0, "BK7"  # object, splitter, lens...
        original_thickness = float(ref_rows[bs_index].thickness)
        if original_thickness > cube_thickness:
            ref_rows[bs_index].thickness = cube_thickness
            ref_rows[bs_index].glass = cube_glass
            ref_rows.insert(bs_index + 1, SurfaceRow(
                surface="Standard", name="bs_air_gap",
                thickness=original_thickness - cube_thickness,
                diameter=float(ref_rows[bs_index].diameter), glass="AIR"))
        cfg = dict(settings)
        cfg["trace_mode"] = "Sequential"
        editor = _snapshot_editor(ref_rows, cfg)
        editor.branch_detector_camera_assignments = {}
        system = _build_system_from_specs(editor._serializable_row_specs(), build=0)
        rays = Kos.raykeeper(system)
        max_radius = max(float(r.diameter) for r in ref_rows) / 2.0
        editor._trace_preview_rays(system, rays, 0.55, max_radius)
        bundle = editor._build_scene_bundle(system, rays, max_radius)
        polylines = [np.asarray(getattr(p, "points_world", np.empty((0, 3))), float)
                     for p in (getattr(bundle, "ray_paths", []) or [])]
        fold = selector == "reflect"
        polylines = [fold_reflect_polyline(pl) if fold else pl for pl in polylines if pl.shape[0] >= 2]
        # the real image z = the geometric chain end PLUS the glass-plate focus shift
        # t(1-1/n) (the cube before the lens pushes the focus further). For 1X this is just
        # t(1-1/n); production should read it from the converged trace.
        glass_shift = cube_thickness * (1.0 - 1.0 / 1.5168) if original_thickness > cube_thickness else 0.0
        image_z = sum(float(r.thickness) for r in ref_rows[:-1]) + glass_shift
        detector = np.array([0.0, image_z - Z_SPLITTER, Z_SPLITTER]) if fold else np.array([0.0, 0.0, image_z])
        arms.append((selector, polylines, detector))
    return arms


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from KrakenOS.UI.layout_editor import SurfaceRow
    from KrakenOS.common_optical_layouts.beam_splitter_dual_mv_150_120 import SURFACES, SETTINGS

    rows = [SurfaceRow(**{k: v for k, v in s.items() if k in SurfaceRow.__dataclass_fields__}) for s in SURFACES]
    arms = build_two_arm_fold(rows, SETTINGS)
    fig, ax = plt.subplots(figsize=(15, 7))
    for selector, polylines, detector in arms:
        color = "tab:blue" if selector == "transmit" else "tab:red"
        for pl in polylines:
            ax.plot(pl[:, 2], pl[:, 1], color=color, lw=0.5, alpha=0.5)
        ax.plot(detector[2], detector[1], "ks", ms=13, mfc="none", mew=2.5)
        print(f"{selector}: detector {np.round(detector, 0)}")
    ax.set_aspect("equal")
    ax.set_title("two-arm display-fold: straight per-arm traces (transmit=blue, reflect=red)")
    fig.tight_layout()
    fig.savefig("/tmp/proto_fold.png", dpi=80)
    print("saved /tmp/proto_fold.png")


if __name__ == "__main__":
    main()
