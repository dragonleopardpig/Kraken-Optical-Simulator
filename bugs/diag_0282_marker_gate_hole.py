"""diag for flag_20260709_200037_370 ("it still look like symetrical dark, not 2-sided dark").

Hypothesis: the user's scene is machine_vision_150mm_test.py (imaging, scene_sources: []) with the
BS diagonal face S001/F001 MARKED as an illumination source in the live session. A face-bound marker:
  * PASSES the bugs/0280 gate (`_normalize_scene_source_specs(layout_scene_source_specs)` is non-empty),
    so the on-detector density heatmap draws again, BUT
  * is EXCLUDED from the imaging trace by `_build_scene_source_bundles` (bugs/0266, so a marker never
    hijacks the imaging conjugates) -- so the traced rays are still the sparse IMAGING fan.
The heatmap therefore bins imaging rays and fabricates the radial "symmetric dark" that 0280 was meant
to kill. This proves the gate hole on the coaxial fixture, then shows the corrected predicate.
"""
from __future__ import annotations

import os

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
os.environ.setdefault("MPLBACKEND", "Agg")

import numpy as np

from KrakenOS.UI.scene_source_analysis import scene_source_spec_is_face_bound_marker
from KrakenOS.UI.validate_open3d_illumination_heatmap_override import _build_override_only_overlay


def _marker_spec() -> dict:
    """A face-bound illumination marker like the one `create_illumination_source_at_face` records for
    S001/F001 -- the ONLY distinguishing key the trace/gate care about is face_anchor_row >= 0."""
    return {
        "source_id": "source:face:S001/F001",
        "name": "Illumination Source (into solid)",
        "model": "Collimated disk source",
        "enabled": True,
        "physical": True,
        "radius": 2.0,
        "face_anchor_row": 1,
        "face_anchor_face_id": "S001/F001",
        "face_anchor_aim": "inward",
        "origin_x": 0.0, "origin_y": 0.0, "origin_z": 229.6,
        "dir_l": -0.7071, "dir_m": 0.0, "dir_n": 0.7071,
    }


def main() -> int:
    editor, system, bundle, det_index, fov = _build_override_only_overlay(6000)
    if editor is None:
        print("SKIP: coaxial-LED fixture unavailable")
        return 0

    target = editor._source_illumination_anchor_target(bundle)
    wl = float(getattr(editor, "_current_wavelength", lambda: 0.546)()) if callable(
        getattr(editor, "_current_wavelength", None)) else 0.546

    print("=" * 78)
    print("A) BASELINE -- fixture's real LED source (rectangle flood)")
    real_specs = list(getattr(editor, "layout_scene_source_specs", []) or [])
    norm_real = editor._normalize_scene_source_specs(real_specs)
    bundles_real, srcs_real = editor._build_scene_source_bundles(wl)
    spec_real = editor._compute_source_illumination_overlay_spec(system, target)
    print(f"   normalize -> {len(norm_real)} spec(s); markers among them:",
          [scene_source_spec_is_face_bound_marker(s) for s in norm_real])
    print(f"   _build_scene_source_bundles -> {len(bundles_real)} launched bundle(s)")
    print(f"   heatmap spec drawn? {spec_real is not None}")

    print("=" * 78)
    print("B) BUG REPRO -- replace the source list with ONLY a face-bound marker (user marked S001/F001)")
    editor.layout_scene_source_specs = [_marker_spec()]
    norm_mk = editor._normalize_scene_source_specs(editor.layout_scene_source_specs)
    is_marker = [scene_source_spec_is_face_bound_marker(s) for s in norm_mk]
    old_gate = bool(norm_mk)                                   # bugs/0280 predicate (has ANY spec)
    new_gate = any(not scene_source_spec_is_face_bound_marker(s) for s in norm_mk)  # proposed fix
    bundles_mk, srcs_mk = editor._build_scene_source_bundles(wl)
    spec_mk = editor._compute_source_illumination_overlay_spec(system, target)
    print(f"   normalize -> {len(norm_mk)} spec(s); markers among them: {is_marker}")
    print(f"   OLD gate (_normalize non-empty)          -> {old_gate}   (heatmap allowed)")
    print(f"   NEW gate (any NON-marker source present) -> {new_gate}   (heatmap allowed)")
    print(f"   _build_scene_source_bundles -> {len(bundles_mk)} launched bundle(s)  "
          f"(marker EXCLUDED per bugs/0266)")
    print(f"   heatmap spec drawn TODAY? {spec_mk is not None}   <-- BUG if True "
          f"(binning imaging rays, no source reaches the detector)")

    print("=" * 78)
    print("C) MIXED -- a real LED + a marker: the real source still qualifies")
    editor.layout_scene_source_specs = list(real_specs) + [_marker_spec()]
    norm_mix = editor._normalize_scene_source_specs(editor.layout_scene_source_specs)
    new_gate_mix = any(not scene_source_spec_is_face_bound_marker(s) for s in norm_mix)
    print(f"   normalize -> {len(norm_mix)} spec(s); NEW gate -> {new_gate_mix} (should stay True)")

    print("=" * 78)
    verdict_bug = (spec_mk is not None) and (len(bundles_mk) == 0) and old_gate and (not new_gate)
    print("VERDICT:", "REPRODUCED -- marker passes old gate, excluded from trace, heatmap still draws; "
          "NEW gate blocks it" if verdict_bug else "NOT reproduced (investigate)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
