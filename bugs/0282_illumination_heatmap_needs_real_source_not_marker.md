# 0282 — the source-illumination heatmap needs a REAL source, not a face marker

## Symptom (flag_20260709_200037_370, a follow-up to bugs/0280)

> "it still look like symetrical dark, not 2-sided dark."

The Normal-to-Sensor detector heatmap shows a **radially symmetric** bowl — bright centre fading to
dark on all four sides/corners — not the 2-sided-dark / 2-uniform fold pattern the coaxial-LED geometry
predicts. This is the *fourth* recording of "the dark looks radial, not 2-sided"
(flag_125602 → flag_150933/0280 → flag_161538 → this one), so the earlier reads clearly missed the
mechanism. This time it was **reproduced on the user's actual scene** before any code changed.

## Root cause — a hole in the bugs/0280 gate

The scene is `attachment/machine_vision_150mm_test.py`: a **pure imaging** system (UI source model
`Pupil / field`, `scene_sources: []`). bugs/0280 already suppresses the heatmap there. But the
screenshot shows the beam-splitter diagonal face **S001/F001 marked as an illumination source** (the
green marker, "Set as Illumination Source", bugs/0264). That marker is what re-opened the gate:

* bugs/0280 gates on `bool(_normalize_scene_source_specs(layout_scene_source_specs))` — a **face-bound
  marker makes the list non-empty**, so the gate passed and the heatmap drew.
* But a face-bound marker is a **display designation, EXCLUDED from the imaging trace** (bugs/0266:
  `_build_scene_source_bundles` skips it so it can't hijack the imaging conjugates), and a marker-only
  scene falls through to the **non-physical** `Pupil / field` reference, which is *also* not launched.
* So **zero rays flood the detector from any source** — the heatmap re-binned the **same sparse imaging
  fan** that bugs/0280 proved is an artifact, and re-painted the radial "symmetric dark".

Reproduced headlessly on the real scene (`bugs/diag_0282_real_marker.py`):

| Case | scene specs | imaging-trace bundles launched | detector hits | old gate | heatmap | pattern |
|------|-------------|-------------------------------|---------------|----------|---------|---------|
| no marker (saved) | 0 | 0 | 117 @ ±6.8 mm | closed | **not drawn** ✓ | — |
| **BS face marked** | 1 (marker) | **0** | same 117 @ ±6.8 mm | **open** | **DRAWN** ✗ | centre 1.00 / edge 0.22 / **corner 0.08 → RADIAL** |

The marker changed **nothing** about the rays — the same 117-hit imaging fan, clustered in the central
±6.8 mm of the 23 mm sensor — it only flipped the gate open. That is the whole bug.

## Fix (`services/three_d_scene_tools.py`)

`_compute_source_illumination_overlay_spec` now gates on **at least one NON-marker source**, matching
exactly what `_build_scene_source_bundles` actually launches onto the detector:

```python
from KrakenOS.UI.scene_source_analysis import scene_source_spec_is_face_bound_marker
specs = self._normalize_scene_source_specs(getattr(self, "layout_scene_source_specs", []) or [])
has_scene_source = any(not scene_source_spec_is_face_bound_marker(spec) for spec in specs)
```

A face-bound marker no longer opens the gate; a real emitting LED (the coaxial layout) still does. This
is the faithful completion of 0280's own principle — *the map is drawn iff the rays it bins are genuine
source-illumination rays* — extended to the exact set of sources the trace launches.

## Why this is not a physics suppression

A marked CAD face **cannot** show its illumination through this heatmap: the heatmap bins the imaging
preview trace's detector hits, and the marker contributes none (bugs/0266). To actually see the 2-sided
coaxial illumination **on the sensor** you need a **real emitting source** — the
`machine_vision_150mm_coaxial_led.py` layout with its 55×78 rectangle LED (where the verified
2-dark/2-uniform lives, penta phases 175/176) — not a marker on a pure imaging scene. Tracing a marked
face's illumination *through the optics onto the detector* is the deferred Stage-3 coupling (bugs/0274),
a separate feature.

## Verification

New display-free guard `validate_open3d_illumination_heatmap_marker_gated` = penta phase **248**, on the
coaxial-LED override fixture:

* **REAL-SOURCE** — the LED heatmap still builds and reads fold (tangent) darker than perp (no
  regression of bugs/0275–0277/0280): fold 0.852 < perp 0.878.
* **MARKER-ONLY** — replacing the source list with a single face-bound marker makes the SAME compute
  path return **None despite 1283 detector hits** (the gate keys off a real source, not hit count).
* **MIXED** — a real LED alongside a marker still draws.
* **PREDICATE** — the marker spec is classified as a face-bound marker; the real LED spec is not.

Sibling heatmap guards (`_source_gated` / `_full_sensor` / `_override` / `_extent`, all coaxial-LED =
real non-marker source) still pass. Baseline: phase/title **248** added (pass).

## Notes

* **In-app eyeball owed.** Load `machine_vision_150mm_test.py`, mark the BS face as an illumination
  source → the radial map no longer appears. Load the coaxial-LED layout → the real 2-dark/2-uniform map
  still draws.
* Repro scripts: `bugs/diag_0282_real_marker.py` (faithful, real scene) and
  `bugs/diag_0282_marker_gate_hole.py` (predicate-level, coaxial fixture).
