"""bugs/0282 -- the detector source-illumination heatmap must NOT re-open on a face-bound illumination
MARKER; it requires a REAL (non-marker) scene source that actually floods the detector.

flag_20260709_200037_370 ("it still look like symetrical dark, not 2-sided dark"): a direct follow-up
to bugs/0280. The user loaded a pure imaging scene (attachment/machine_vision_150mm_test.py, UI source
'Pupil / field', scene_sources: []) and MARKED the beam-splitter diagonal face as an illumination
source ("Set as Illumination Source"). That marker makes `_normalize_scene_source_specs` non-empty, so
0280's plain non-empty gate re-opened -- but a face-bound marker is a DISPLAY designation EXCLUDED from
the imaging trace (bugs/0266), and a marker-only scene falls through to the non-physical Pupil/field
reference, so `_build_scene_source_bundles` launches NOTHING onto the detector. The heatmap then re-binned
the same sparse imaging fan and re-fabricated the radial "symmetric dark" 0280 killed (reproduced on the
real scene: bundles launched=0, 117 imaging hits at +-6.8 mm -> centre 1.00 / edge 0.22 / corner 0.08).

Fix: `_compute_source_illumination_overlay_spec` gates on at least one NON-marker source (matching what
`_build_scene_source_bundles` actually launches), not just a non-empty spec list.

Checks (display-free; reuses the coaxial-LED override fixture, no VTK/Tk):
  * REAL-SOURCE -- the LED (non-marker) heatmap still builds and still reads the fold (tangent) edge
    darker than the perpendicular edge (no regression of bugs/0275-0277/0280).
  * MARKER-ONLY -- replacing the source list with ONLY a face-bound marker makes the SAME compute path
    return None, even though the fixture still has >=50 detector hits (the gate keys off a REAL source,
    not hit count) -- so marking a CAD face never re-paints the fabricated radial map.
  * MIXED -- a real LED alongside a marker still draws (the real source qualifies).
  * PREDICATE -- the marker spec is classified as a face-bound marker; the real LED spec is not.
"""
from __future__ import annotations

import os

import numpy as np

from KrakenOS.UI.scene_source_analysis import scene_source_spec_is_face_bound_marker
from KrakenOS.UI.validate_open3d_illumination_heatmap_override import _build_override_only_overlay

_TRACE_RAYS = int(os.environ.get("HEATMAP_MARKER_RAYS", "6000") or "6000")


def _marker_spec() -> dict:
    """What `create_illumination_source_at_face` records for a marked BS diagonal (bugs/0264). The only
    key the trace/gate care about is ``face_anchor_row`` >= 0 (scene_source_spec_is_face_bound_marker)."""
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


def _check(failures: list[str], notes: list[str]) -> None:
    editor, system, bundle, det_index, fov = _build_override_only_overlay(_TRACE_RAYS)
    if editor is None:
        notes.append("SKIP marker-gate: coaxial-LED fixture unavailable")
        return

    target = editor._source_illumination_anchor_target(bundle)
    if target is None:
        failures.append("SETUP: no source-illumination anchor target on the coaxial fixture")
        return

    real_specs = [dict(s) for s in (getattr(editor, "layout_scene_source_specs", []) or [])]
    norm_real = editor._normalize_scene_source_specs(real_specs)
    if not any(not scene_source_spec_is_face_bound_marker(s) for s in norm_real):
        failures.append("SETUP: coaxial fixture has no real (non-marker) scene source to test against")
        return

    # --- REAL-SOURCE: the LED heatmap still builds + still reads the 2-dark fold asymmetry. ---
    spec_real = editor._compute_source_illumination_overlay_spec(system, target)
    if not spec_real:
        failures.append("REAL-SOURCE: heatmap is None WITH a real LED source (gate over-suppressed)")
    else:
        rel = np.asarray(spec_real["relative"], dtype=float)
        if rel.ndim == 2 and rel.size:
            fold_edges = 0.5 * (float(np.mean(rel[:, 0])) + float(np.mean(rel[:, -1])))
            perp_edges = 0.5 * (float(np.mean(rel[0, :])) + float(np.mean(rel[-1, :])))
            if not (fold_edges < perp_edges):
                failures.append(
                    f"REAL-SOURCE: fold edge ({fold_edges:.3f}) not darker than perp ({perp_edges:.3f}) "
                    f"-- 2-dark/2-uniform coverage regressed"
                )
            else:
                notes.append(f"real-source: heatmap draws, fold {fold_edges:.3f} < perp {perp_edges:.3f}")

    # --- MARKER-ONLY: a face-bound marker opens the OLD gate but floods nothing -> the fix returns None. ---
    samples = editor._source_illumination_hit_samples(system, det_index)
    n_hits = int(np.asarray(samples.get("x", []), dtype=float).size) if isinstance(samples, dict) else 0
    editor.layout_scene_source_specs = [_marker_spec()]
    norm_marker = editor._normalize_scene_source_specs(editor.layout_scene_source_specs)
    if not norm_marker:
        failures.append("SETUP: the marker spec did not normalize -- the differential is vacuous")
    if any(not scene_source_spec_is_face_bound_marker(s) for s in norm_marker):
        failures.append("SETUP: the marker-only list contains a non-marker spec -- fixture leak")
    spec_marker = editor._compute_source_illumination_overlay_spec(system, target)
    if spec_marker is not None:
        failures.append(
            f"MARKER-ONLY: heatmap re-opened for a marker-only scene ({n_hits} detector hits) -- a marked "
            f"CAD face floods nothing onto the detector yet re-paints the fabricated radial map "
            f"(flag_20260709_200037_370)"
        )
    elif n_hits >= 50:
        notes.append(f"marker-only: None despite {n_hits} detector hits (gate keys off a REAL source)")
    else:
        notes.append(f"marker-only: None ({n_hits} hits; gate still correct)")

    # --- MIXED: a real LED alongside a marker still qualifies (the real source floods). ---
    editor.layout_scene_source_specs = list(real_specs) + [_marker_spec()]
    spec_mixed = editor._compute_source_illumination_overlay_spec(system, target)
    if spec_mixed is None:
        failures.append("MIXED: heatmap suppressed even with a real LED source alongside the marker")
    else:
        notes.append("mixed: a real source + a marker still draws (real source qualifies)")

    # --- PREDICATE: marker vs real-LED classification. ---
    if not scene_source_spec_is_face_bound_marker(_marker_spec()):
        failures.append("PREDICATE: the face-bound marker spec was not classified as a marker")
    if norm_real and scene_source_spec_is_face_bound_marker(norm_real[0]):
        failures.append("PREDICATE: the real LED spec was misclassified as a face-bound marker")
    if not [f for f in failures if f.startswith("PREDICATE")]:
        notes.append("predicate: marker flagged, real LED not")


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []
    notes: list[str] = []
    _check(failures, notes)
    return (not failures), (failures + notes)


def main() -> int:
    ok, messages = run_checks()
    for line in messages:
        print(("PASS " if ok else "") + line)
    print("RESULT:", "pass" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
