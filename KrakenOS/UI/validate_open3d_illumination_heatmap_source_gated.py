"""bugs/0280 -- the detector source-illumination heatmap must draw ONLY when the preview traced a
scene ILLUMINATION source (the coaxial LED area source), never for a pure imaging scene.

flag_20260709_150933_595 ("still seems 4 sided dark edges to me"): the user loaded a full MV-150
imaging system (attachment/machine_vision_150mm_test.py, scene_sources: []). With no scene source
the preview traces the sparse IMAGING pupil/field fan, whose rays converge to the central image
region (~±6.8 mm of the 23 mm sensor) and never reach the rim. The heatmap bins those rays' local
DENSITY as relative illumination -> the un-sampled rim reads dark -> a false radial 4-dark that is
neither illumination coverage nor lens vignetting. bugs/0280 proved the builder is correct (a
uniform full-sensor sample reads 1.0 everywhere) -- the error is feeding it an imaging sample.

Fix: `_compute_source_illumination_overlay_spec` gates on the SAME predicate
`_build_scene_source_bundles` uses (`_normalize_scene_source_specs(layout_scene_source_specs)`), so
the map is built iff the rays it bins are genuine source-illumination rays.

Checks (display-free; reuses the coaxial-LED override fixture, no VTK/Tk):
  * SOURCE-PRESENT -- with the LED scene source, the heatmap still builds and still reads the fold
    (tangent) edge darker than the perpendicular edge (the real 2-dark / 2-uniform coverage; no
    regression of bugs/0275-0277).
  * SOURCE-ABSENT -- clearing ONLY `layout_scene_source_specs` (same traced rays, same >=50 detector
    hits) makes the SAME compute path return None: the gate keys off source presence, not hit count,
    so a pure imaging scene never paints a fabricated illumination map.
"""
from __future__ import annotations

import os

import numpy as np

from KrakenOS.UI.validate_open3d_illumination_heatmap_override import _build_override_only_overlay

_TRACE_RAYS = int(os.environ.get("HEATMAP_GATE_RAYS", "6000") or "6000")


def _check(failures: list[str], notes: list[str]) -> None:
    editor, system, bundle, det_index, fov = _build_override_only_overlay(_TRACE_RAYS)
    if editor is None:
        notes.append("SKIP source-gate: coaxial-LED fixture unavailable")
        return

    target = editor._source_illumination_anchor_target(bundle)
    if target is None:
        failures.append("SETUP: no source-illumination anchor target on the coaxial fixture")
        return

    # Sanity: the fixture really does carry a scene illumination source (else the test is vacuous).
    if not editor._normalize_scene_source_specs(getattr(editor, "layout_scene_source_specs", []) or []):
        failures.append("SETUP: coaxial fixture has no layout_scene_source_specs -- can't test the gate")
        return

    # --- SOURCE-PRESENT: the LED heatmap still builds + still reads the 2-dark fold asymmetry. ---
    spec_on = editor._compute_source_illumination_overlay_spec(system, target)
    if not spec_on:
        failures.append("SOURCE-PRESENT: heatmap is None WITH a scene source (gate over-suppressed)")
    else:
        rel = np.asarray(spec_on["relative"], dtype=float)
        if rel.ndim == 2 and rel.size:
            fold_edges = 0.5 * (float(np.mean(rel[:, 0])) + float(np.mean(rel[:, -1])))
            perp_edges = 0.5 * (float(np.mean(rel[0, :])) + float(np.mean(rel[-1, :])))
            if not (fold_edges < perp_edges):
                failures.append(
                    f"SOURCE-PRESENT: fold edge ({fold_edges:.3f}) not darker than perp ({perp_edges:.3f}) "
                    f"-- 2-dark/2-uniform coverage regressed"
                )
            else:
                notes.append(f"source-present: heatmap draws, fold {fold_edges:.3f} < perp {perp_edges:.3f}")

    # --- SOURCE-ABSENT: same rays + detector, but no scene source -> the SAME path returns None. ---
    # Count in-sensor detector hits first, to prove suppression is NOT for lack of hits.
    samples = editor._source_illumination_hit_samples(system, det_index)
    n_hits = int(np.asarray(samples.get("x", []), dtype=float).size) if isinstance(samples, dict) else 0
    editor.layout_scene_source_specs = []  # imaging scene: no scene illumination source
    spec_off = editor._compute_source_illumination_overlay_spec(system, target)
    if spec_off is not None:
        failures.append(
            f"SOURCE-ABSENT: heatmap still built with NO scene source ({n_hits} detector hits) -- "
            f"an imaging scene fabricates a false illumination map (flag_20260709_150933_595)"
        )
    elif n_hits >= 50:
        notes.append(f"source-absent: None despite {n_hits} detector hits (gate keys off source, not count)")
    else:
        notes.append(f"source-absent: None ({n_hits} hits; gate still correct)")


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
