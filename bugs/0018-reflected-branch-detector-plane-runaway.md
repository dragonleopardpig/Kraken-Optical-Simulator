# 0018 — Reflected beam-splitter branch renders as a bent diagonal (runaway detector-plane projection)

**Status:** Fixed (2026-06-05).
**Component:** Open 3D / 2D scene builder — the escaped-ray detector-plane
projector `_detector_plane_miss_intersection`
(`KrakenOS/UI/scene_builder.py`).
**Reported via:** in-app recorder. **Repro bundles are gitignored**, so the
evidence below is transcribed here. Two flags:
`flag_20260605_110342_145` ("zoom in view." — pure-XZ zoomed view) and
`flag_20260605_113625_430` ("rays exit still bent." — normal zoom, follow-up to
bug 0017). Saved repro prescription:
`attachment/machine_vision_150mm_measured_test.py` (8 surfaces; S6 is a promoted
beam-splitter cube, BK7, mesh z≈200–225; the imaging lens datums S1–S5 sit at
z≈268–317; the Image plane S7 is authored at its real station z≈665).

## Symptoms (user's words)

> rays exit still bent.

and, on the zoomed recording:

> zoom in view.

The reflected branch off the 45° beam-splitter cube (the "second path", which
should fold a clean 90° to **pure +X** up its own optical axis) instead rendered
as a bright **diagonal band climbing up-and-to-the-right** (~27° above +Z) that
fanned out and *changed angle as the view zoomed*. The companion 2D layout
(`attachment/2D.png`) collapsed the whole scene to a dot: its "XZ full 3D" panel
auto-scaled X to ~600,000 mm and "YZ full 3D" scaled Y to ±30,000 mm.

## Root cause (confirmed 2026-06-05, headless)

The geometry is actually correct — the puzzle was that the band *looked* diagonal
while every reflected ray traced near-pure +X. A matplotlib (float64)
re-projection of the exact traced `points_world` drew the same data as a clean
**vertical** (+X) bundle, proving the diagonal was a **render artifact**, not a
trace error. The artifact's source is a single absurd coordinate:

`_detector_plane_miss_intersection` projects every escaped / "missed" ray onto a
detector (Image) plane to see if it still lands on the sensor:

```
denom    = dot(direction, normal)        # normal ≈ +Z for the z=665 image plane
distance = dot(center - origin, normal) / denom
point    = origin + direction * distance
```

There was **no guard on `denom`**. The reflected fold travels almost purely +X,
i.e. nearly *parallel* to the z=665 plane, so `denom ≈ dir_z ≈ 0.01`. `distance`
then ran away to ~10⁴–10⁵ mm and the segment was re-terminated hundreds of metres
off-axis (z snapped to 665, x to ~6×10⁵). That one ~600 m coordinate then broke
the renderer two ways the user saw:

* **3D** — VTK single-precision line clipping draws the ~600 m segment as a *bent
  diagonal* whose apparent angle shifts with the view transform (hence "still
  bent", and worse on zoom).
* **2D** — the layout auto-scales its axes to ±6×10⁵ mm, collapsing the scene.

Headless reproduction (`machine_vision_150mm_measured_test.py`), max |coordinate|
over every traced ray-path point:

| quantity | pre-fix | post-fix |
|---|---|---|
| max ‖ray point‖ (any axis) | **602,400.7 mm** | **665.0 mm** |
| worst reflected ray endpoint | **[602400.7, −14748.3, 665.0]** | **[244.7, …, ~210]** |
| reflected fold final direction | +X (correct) but length 6×10⁵ mm | +X, length **232.7 mm** |
| transmit rays imaging at z≈665 | preserved | preserved (279) |

The 665 in the runaway endpoint is the tell: the ray was *force-landed on the
detector plane* (z=665) at an absurd lateral distance, exactly as the unguarded
division dictates.

## Fix

`scene_builder.py` — reject the projection when the ray is not actually heading
toward the plane. An escaped ray is only meaningfully "imaged" when it propagates
toward the detector; a ray grazing/parallel to the plane (the beam-splitter's
folded branch) must keep its sane traced length instead.

```python
_DETECTOR_MISS_MIN_AXIAL_COS = 0.17364817766693041  # cos(80 deg)
...
denom = float(np.dot(direction, normal))
if not np.isfinite(denom) or abs(denom) < _DETECTOR_MISS_MIN_AXIAL_COS:
    # parallel to / grazing the detector plane: not heading toward it.
    continue
distance = float(np.dot(center - origin, normal) / denom)
```

The reflected fold (|dir_z| ≈ 0.01–0.06 ≪ cos 80°) is no longer projected; it
stays escaped at its native ~232 mm length up +X, near the cube. Genuine transmit
rays (dir ≈ +Z, |dir_z| ≈ 1) are well inside the cone and still image onto z≈665
unchanged. The threshold is a wide 80° half-cone, so only near-parallel rays — the
ones whose projection distance is physically meaningless — are dropped.

This is surgical: it only changes where an *escaped/grazing* ray terminates. It
does not touch the transmit imaging cone (all 279 transmit rays trace identically
pre/post), the optical-axis builder, or the trace physics.

## Physics corroboration (defocus is real, not auto-refocused)

The user also asked to confirm the cube produces *physical* defocus at the sensor
unless the image distance is adjusted. Verified headless on the same scene
(on-axis field, sensor fixed at z=665, identical 279-ray topology; only the cube
glass differs):

| cube glass | on-axis best-focus z | RMS @ best focus | RMS @ sensor z=665 |
|---|---|---|---|
| **BK7** (real) | 637.0 mm | 0.40 µm | **539 µm blur** |
| AIR (control) | 625.0 mm | 0.00 µm | 821 µm blur |

Inserting the 25 mm BK7 path shifts best focus **downstream by +12 mm**
(625→637) — correct sign; the paraxial plate estimate Δ = t(1−1/n) ≈ 8.5 mm plus
the plate's spherical-aberration contribution to the min-RMS plane accounts for
the rest. The Image row is **not** silently repositioned to chase focus (stays
z=665 in both runs), so rays at the sensor are a genuine ~539 µm defocus blur, and
best-focus RMS rises 0.00→0.40 µm (real residual aberration from the plate). The
simulation is physically faithful — it does not secretly refocus.

## Tests

* **Display-free unit** —
  `KrakenOS/UI/validate_open3d_reflected_branch_detector_bounds.py`
  (`python -m KrakenOS.UI.validate_open3d_reflected_branch_detector_bounds`).
  Mechanism guards (CAD-free): against a fixed z=665 plane a grazing +X ray
  (`dir_z≈0.01`) and a pure +X ray are **not** projected; an axial +Z ray still
  projects to z≈665 at a sane finite distance; the cos(80°) threshold is the exact
  crossover (|dir_z|=0.15 rejected, 0.20 projected); and disabling the guard
  reproduces the **45,302 mm** runaway distance the bug emitted. When the CAD cache
  is present it re-traces the user's real cube scene and asserts every ray-path
  coordinate stays ≤ 2000 mm (was 6×10⁵), the reflected fold rays exist and stay
  finite (count 279, max length 232.7 mm — not vanished, not exploded), and
  transmit rays still image onto z≈665. Verified fail-before / pass-after by
  stashing the fix (pre-fix max ‖coord‖ = 602,400.7 mm ≫ 2000 cap).
* **Regression / end-to-end** — `Phase 27`
  (`phase_27_reflected_branch_detector_bounds`) in
  `validate_open3d_penta_telescope_comprehensive.py` wraps `run_checks()`. Full
  harness: 28/28 phases pass. Gate baseline regenerated
  (`tools/penta_validator_baseline.json`).
* **Visual** — the real `machine_vision_150mm_measured_test` scene was rendered
  off-screen at the *exact recording camera* (flag_20260605_110342_145: parallel
  XZ, +X up, focal (56.25, 0, 230.94), scale 88.72) under Xvfb on 2026-06-05 and
  inspected by eye. The diagonal up-right band is **gone**: the transmit bundle
  passes cleanly +Z through the cube into the lens barrel, the reflected branch
  folds straight up +X at a finite length, and the camera-fit bounds are sane
  (no ±512 m). Compared directly against the recorded `screenshot.png` (which
  shows the bent diagonal climbing off-frame).
