"""Diagnostic (#5 / bugs 0203): the current 0192 correction reflects the rotation-folded
tail across the flip-plane-through-ORIGIN and then translates it PER-RAY (tau) to anchor the
kink on the face -- the per-ray tau shears a full cone (36 mm short, 1.27 mm RMS).

Candidate fix: reflect the tail across the flip plane through a SINGLE anchor (the on-axis
fold point / folded face center) -- rigid, so it preserves the focus AND un-flips the
off-axis diagonal (rotation-fold -> physical reflection) for ALL rays at once.

This probe applies the REAL rotation fold, then this rigid flip, and measures the waist.
"""
from __future__ import annotations

import contextlib
import io
import sys

import numpy as np

from KrakenOS.UI.services.folded_sequential_fold import (
    fold_promoted_mirror_specs_to_sequential,
    mirror_reflection_flip_plane_normal,
    promoted_mirror_world_center,
)
from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor

from probe_0187_seq_mirror_focus import (  # type: ignore
    _onaxis_paths,
    _preview_2d_sampling_mode,
    _transverse_rms_at_x,
    _waist,
)


def _trace_bundle(editor):
    wavelength = float(editor._current_wavelength())
    max_radius = max((max(r.diameter / 2.0, 0.5) for r in editor.rows), default=1.0)
    system = editor.build_system(require_solids=True)
    folded_trace_rows = editor._folded_sequential_trace_rows(editor.rows)
    rays, fold_transform = editor._trace_preview_rays_folded_aware(
        system, wavelength, max_radius,
        sampling_mode=_preview_2d_sampling_mode(editor),
        folded_trace_rows=folded_trace_rows,
    )
    bundle = editor._build_scene_bundle(system, rays, max_radius)
    return system, bundle, fold_transform


def _fold_geometry(editor, fold_transform):
    specs = editor._serializable_specs_for_rows(list(editor.rows))
    _folded, records = fold_promoted_mirror_specs_to_sequential(specs)
    rec = records[0]
    row_index = int(rec.get("row_index", -1))
    face_normal = np.asarray(rec.get("face_normal"), dtype=float).reshape(-1)[:3]
    chief_in = np.asarray(rec.get("chief_in") or [0.0, 0.0, 1.0], dtype=float).reshape(-1)[:3]
    flip = mirror_reflection_flip_plane_normal(chief_in, face_normal)
    center = np.asarray(promoted_mirror_world_center(specs, row_index), dtype=float).reshape(3)
    M = np.asarray(fold_transform, dtype=float).reshape(4, 4)
    rot, trans = M[:3, :3], M[:3, 3]
    center_folded = rot @ center + trans
    # The flip normal is defined by the PHYSICAL outgoing geometry (d_out x s), which does
    # NOT rotate with the display fold: the rotation already turned the unfolded +Z tail to
    # the physical +X leg, and the reflection R' that converts rotation-fold -> mirror-fold
    # acts on that folded leg with normal d_out x s = [0,0,1] here (flips Z, keeps +X). Only
    # the anchor's Z matters, and the on-axis focus sits at center_folded.z, so a rigid flip
    # across that plane leaves the focus on the detector.
    flip_used = np.asarray(flip, dtype=float)
    flip_used = flip_used / np.linalg.norm(flip_used)
    return center_folded, flip_used


def _rigid_flip(points, anchor, flip, *, cos_fold_max=0.2):
    pts = np.asarray(points, dtype=float)
    if pts.ndim != 2 or pts.shape[0] < 3 or pts.shape[1] < 3:
        return None
    coords = pts[:, :3]
    seg = np.diff(coords, axis=0)
    ln = np.linalg.norm(seg, axis=1)
    valid = ln > 1e-9
    if int(valid.sum()) < 2:
        return None
    units = np.zeros_like(seg)
    units[valid] = seg[valid] / ln[valid, None]
    cos_turn = np.sum(units[:-1] * units[1:], axis=1)
    kink_seg = int(np.argmin(cos_turn))
    if cos_turn[kink_seg] > cos_fold_max:
        return None
    k = kink_seg + 1
    out = pts.copy()
    tail = coords[k:]
    s = (tail - anchor) @ flip
    out[k:, :3] = tail - 2.0 * s[:, None] * flip[None, :]
    return out


def main() -> int:
    lines: list[str] = []
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor = _build_editor(_AZ85)
        editor._build_preview_system_rays_bundle(update_state=True)
        editor.snap_detector_to_image_plane()
        system, bundle, ft = _trace_bundle(editor)
        # Real rotation fold (Stage A) -- lands focus on the drawn detector.
        editor._fold_straight_equivalent_display_rays(bundle, ft)
        anchor, flip = _fold_geometry(editor, ft)
        for path in getattr(bundle, "ray_paths", []) or []:
            folded = _rigid_flip(getattr(path, "points_world", None), anchor, flip)
            if folded is not None:
                path.points_world = folded
        nrows = len(editor.rows)
        drawn_x = float(np.asarray(
            editor._surface_reference_world_point(nrows - 1, system=system), dtype=float
        ).reshape(3)[0])
        paths = _onaxis_paths(bundle)
        wx, wrms = _waist(paths, 40.0, drawn_x + 30.0)

    lines.append("=== #5 candidate: rotation fold + RIGID flip about folded fold-point ===")
    lines.append(f"  anchor(folded C)={anchor}  flip_folded={flip}")
    lines.append(f"  on-axis rays: {len(paths)}   drawn sensor X={drawn_x:.3f}")
    if wx is not None:
        lines.append(f"  beam WAIST at X={wx:.3f} (RMS {wrms:.4f} mm), {drawn_x - wx:+.3f} mm from sensor")
    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
