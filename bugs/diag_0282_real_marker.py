"""diag for flag_20260709_200037_370 -- "it still look like symetrical dark, not 2-sided dark".

Faithful reproduction on the user's ACTUAL scene (attachment/machine_vision_150mm_test.py: a pure
IMAGING system, UI source_model 'Pupil / field', scene_sources: []). The screenshot shows the BS
diagonal face S001/F001 MARKED as an illumination source (green marker), so we mirror that: inject a
face-bound marker into layout_scene_source_specs, exactly what "Set as Illumination Source" records.

Claim under test: marking the face re-opens the bugs/0280 heatmap gate (a marker makes
`_normalize_scene_source_specs` non-empty) WITHOUT feeding the detector any real illumination -- the
marker is excluded from the imaging trace (bugs/0266) and the UI 'Pupil / field' reference is
non-physical, so `_build_scene_source_bundles` launches NOTHING. The heatmap then bins the sparse
imaging fan and re-fabricates the radial "symmetric dark" that 0280 killed for the no-marker case.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
os.environ.setdefault("MPLBACKEND", "Agg")

import numpy as np

from KrakenOS.UI.scene_source_analysis import scene_source_spec_is_face_bound_marker

REPO = Path(__file__).resolve().parents[1]
SCENE = REPO / "attachment" / "machine_vision_150mm_test.py"
HR25_MM = 23.04


def _load_scene():
    spec = importlib.util.spec_from_file_location("user_mv150_scene", SCENE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _marker_spec() -> dict:
    """What create_illumination_source_at_face records for a marked BS diagonal (face_anchor_row>=0)."""
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
    }


def _new_gate(editor) -> bool:
    specs = editor._normalize_scene_source_specs(getattr(editor, "layout_scene_source_specs", []) or [])
    return any(not scene_source_spec_is_face_bound_marker(s) for s in specs)


def main() -> int:
    import KrakenOS as Kos
    from KrakenOS.UI.render_layout_snapshot import _rows_from_layout_info, _snapshot_editor
    from KrakenOS.UI.scene_builder import build_scene_bundle

    module = _load_scene()
    surfaces = module.SURFACES
    settings = dict(module.SETTINGS)
    rows = _rows_from_layout_info({"surfaces": surfaces, "settings": settings})
    editor = _snapshot_editor(rows, settings)
    det_index = len(rows) - 1
    editor._camera_detector_active_dims_overrides = lambda: {int(det_index): (HR25_MM, HR25_MM)}

    system = module.build_runtime_system()
    rays = Kos.raykeeper(system)
    wl = float(settings.get("wavelength", "0.546") or 0.546)
    max_radius = max((max(r.diameter / 2.0, 0.5) for r in rows), default=1.0)
    editor._trace_preview_rays(system, rays, wl, max_radius, allow_full_pupil=False, sampling_mode="world_envelope")
    editor.last_system, editor.last_rays = system, rays

    def _rebuild_bundle():
        srcs = editor._collect_scene_sources(wavelength=wl)
        b = build_scene_bundle(
            rows=rows, system=system, rays=rays, sources=srcs,
            field_count=max(1, editor.__dict__.get("_preview_field_bundle_count", 1)),
            ray_count_per_field=max(1, editor.__dict__.get("_preview_field_ray_count", 1)),
        )
        editor._last_scene_bundle = b
        return b, srcs

    def _report(tag):
        b, srcs = _rebuild_bundle()
        target = editor._source_illumination_anchor_target(b)
        bundles, _ = editor._build_scene_source_bundles(wl)
        samples = editor._source_illumination_hit_samples(system, det_index)
        xs = np.asarray(samples.get("x", []), dtype=float)
        ys = np.asarray(samples.get("y", []), dtype=float)
        spec = editor._compute_source_illumination_overlay_spec(system, target) if target is not None else None
        n_src = len(editor._normalize_scene_source_specs(getattr(editor, "layout_scene_source_specs", []) or []))
        pattern = ""
        if spec:
            rel = np.asarray(spec["relative"], dtype=float)
            if rel.ndim == 2 and rel.size:
                cx = rel.shape[0] // 2
                centre = float(rel[cx, cx])
                edge = float(np.mean([rel[:, 0].mean(), rel[:, -1].mean(), rel[0, :].mean(), rel[-1, :].mean()]))
                corner = float(np.mean([rel[0, 0], rel[0, -1], rel[-1, 0], rel[-1, -1]]))
                pattern = f" pattern[centre={centre:.2f} edge={edge:.2f} corner={corner:.2f}]"
                if corner < edge < centre:
                    pattern += " RADIAL(4-dark)"
        print(f"[{tag}] scene_source_specs={n_src}  imaging-trace bundles launched={len(bundles)}  "
              f"detector hits={xs.size}")
        print(f"        OLD gate(any spec)={bool(n_src)}  NEW gate(non-marker src)={_new_gate(editor)}  "
              f"heatmap drawn={spec is not None}{pattern}")
        if xs.size:
            print(f"        hit span x=[{xs.min():.1f},{xs.max():.1f}] y=[{ys.min():.1f},{ys.max():.1f}] "
                  f"(sensor half={HR25_MM/2:.1f})")
        return spec

    print("=" * 82)
    print("A) SAVED scene as-is (scene_sources: [], no marker) -- bugs/0280 should suppress")
    editor.layout_scene_source_specs = []
    spec_a = _report("no-marker")

    print("=" * 82)
    print("B) USER ACTION: mark BS face S001/F001 as Illumination Source (the flag_200037 state)")
    editor.layout_scene_source_specs = [_marker_spec()]
    spec_b = _report("marked ")

    print("=" * 82)
    bug = (spec_a is None) and (spec_b is not None)
    print("VERDICT:",
          "REPRODUCED -- 0280 suppresses the bare imaging scene, but marking the BS face re-opens the\n"
          "          gate and the SAME sparse imaging fan paints the radial 'symmetric dark'. The NEW\n"
          "          gate (require a non-marker source) reports False in B -> the fix returns None."
          if bug else
          "NOT reproduced as expected -- inspect the per-step numbers above.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
