# 0297 — Folded FOV solve targets a different first order than the readout (and the ray trace)

Recording `attachment/recorded_bug_repros/recording_20260713_200738.json`, scene
`attachment/machine_vision_AZ85_RA_Mirror.py` (two-fold AZ85 periscope: object → RA mirror →
ELS-85 → RA mirror → HR25 camera). Four flags:

| flag | description |
|---|---|
| `flag_20260713_200235_567` | "Defocus on launched." |
| `flag_20260713_200350_938` | "removed defocus." |
| `flag_20260713_200542_175` | "input 54x54 for FOV but get 58.8x58.8. Constraint last distance to 30mm. It should focus by shortening second last distance, but it is defocus." |
| `flag_20260713_200728_761` | "ISO view." |

All four are **one root cause**. The recorded popup action (event 66) was:

```
fov_solve {plane: object, mode: thickness, width: 54, height: 54,
           segment: [near, 50], image_segment: [far, 30]}
```

## What the ray trace actually says

Measured on the user's real scene (`bugs/diag_az85_true_trace.py`), by least-squares crossing of
the traced exit legs:

| | as loaded | after the recorded 54×54 solve |
|---|---|---|
| **true \|m\| (ray trace)** | 0.99998 | 0.39196 |
| `_current_finite_paraxial_magnification` (the readout) | 1.00000 ✅ | 0.39196 ✅ |
| the FOV solver's lens-only model | 1.26185 ❌ | 0.42667 ❌ |
| real defocus | −48.5 mm | −20.6 mm |
| traced on-axis spot RMS | 1.68 mm | 1.02 mm |

The **readout was right all along** — it matches the trace to five digits. The **solve** was wrong,
and the readout then honestly reported the FOV the wrong solve had produced: 58.8, not the 54 typed.

## Root cause

`_folded_conjugate_gaps_for_magnification` solved the conjugate against a hand-carved **LENS-ONLY**
first order: the rows between the first and last lens surface, with the **fold mirrors excluded**
(`lens_rows = equivalent[first_lens : gap_start+1]`, last thickness zeroed).

But an RA fold here is a **BK7 right-angle prism**, not a bare mirror: the beam enters a port face,
reflects off the hypotenuse and exits — ~25 mm of glass, i.e. a reduced (air-equivalent) path of
`t(1 − 1/n) ≈ 8.52 mm` on **each** leg. Dropping the prisms puts the solved object distance ~8.5 mm
out and the solved image distance ~8.5 mm out, so the solve:

* leaves the system **defocused** (~20 mm residual → a 1 mm RMS blur on the sensor), and
* lands ~9 % off the target magnification → the FOV reads **58.8** when the user typed **54**.

The magnification readout, meanwhile, reads the **straight-equivalent paraxial reference**, in which
a promoted RA prism is kept as the transmissive glass plate it physically is (bugs/0219 explicitly
preserved that: *"its glass shift is REAL for the SOLVE, so the shared walk must not merge it away"*).
Two models, one scene — they disagreed by 9 %.

A second defect surfaced from the same recording. The best-focus seat legitimately drives the
**trailing mirror's gap negative** (its row carries a 40 mm *axial reserve* that is not optical
path; the in-focus value is `−8.5179 mm` — exactly what the app wrote in flag 2). But
`_paraxial_total_image_gap` and `_folded_image_conjugate_split` summed gaps as `max(thickness, 0)`,
so the image distance read ~8.5 mm long and the user's pinned "mirror → sensor = 30 mm" silently
came out **21.48 mm**. (The recorded flag-3 state has `row 8 thickness = 21.4821` — reproduced
exactly.)

## Fix

1. **One shared first order.** New `ParaxialToolsMixin._shared_first_order_reference()` returns the
   cardinals **plus their absolute z** in the reference frame (which maps 1:1 onto path length along
   the folded beam): `f`, `ppa`, `ppp`, `object_principal` (object → H), `image_principal`,
   `h2_z` (H′ absolute), `image_z` (prescription image plane, absolute).
   `_current_finite_paraxial_magnification` **and** `_folded_conjugate_gaps_for_magnification` now
   both read it, so they cannot drift apart.

2. **Invert the Gaussian conjugate on that reference** instead of on a carved-out lens block:

   ```
   object → H   :  s_o = f (1 + 1/m)        → object_delta = f(1 + 1/m) − object_principal
   H′ → image   :  s_i = f (1 + m)          → image_delta  = (h2_z + f(1 + m)) − image_z
   ```

   Both deltas are exact in one shot: moving the object gap shifts H′, the image plane *and* the
   focus by the same amount (so `image_delta` is invariant to it), and sliding a fold prism along a
   leg moves `h2_vertex_z` and `ppp` by equal and opposite amounts (so the focus z is invariant to
   *that*). No iteration.

3. **Stop clamping the gap sums at zero** (`_paraxial_total_image_gap`, `_folded_image_conjugate_split`)
   so a negative trailing-mirror gap — which the app's own best-focus snap writes — is honoured, and
   a pinned image leg lands on the value the user typed.

## Result (the recorded solve, replayed on the real scene)

| | before | after |
|---|---|---|
| FOV readout (asked 54 × 54) | 58.78 × 58.78 | **54.0 × 54.0** |
| residual defocus | −20.6 mm | **0.000 mm** |
| traced on-axis spot RMS | 1.02 mm | **0.00001 mm** |
| pinned object → mirror (asked 50) | 50 ✓ | 50 ✓ |
| pinned mirror → sensor (asked 30) | 21.48 ✗ | **30.0 ✓** |

Starting from the file state *or* from the flag-2 (best-focus-seated) state now converges to the
**identical** row set — the solve no longer depends on how the scene happened to be seated.

## Flags 1 + 2

`flag_20260713_200235_567` ("Defocus on launched") is **real**: the saved prescription has the object
gap at exactly its in-focus 1X value (59.397 mm) but the image gap 48.5 mm long, so the scene loads
48.5 mm out of focus and the app renders that faithfully. The app is *not* wrong to show it — and
`flag_20260713_200350_938` ("removed defocus") is the app's best-focus snap landing exactly on the
traced focus (z = 11.248, `row 8 thickness = −8.5179`), which the trace confirms to 3 decimals.
The stale image gap is the kind of state the old solve produced; with 0297 in, a solve leaves the
scene in focus, so re-solving and re-saving the file clears it. Nothing auto-focuses on load —
that would hide real defocus and violate "display follows the physics engine".

`flag_20260713_200728_761` ("ISO view") is the same flag-3 state seen in 3D (same FOV 58.8 label,
same thicknesses) — no separate defect.

## Guard

`KrakenOS/UI/validate_open3d_folded_conjugate_first_order.py` (display-free, portable two-fold
fixture — no `attachment/` dependency), penta **phase 261**:

* **A** SOLVE HITS THE TARGET — the readout \|m\| after `fov_solve` equals the requested ratio.
* **B** SOLVE LANDS IN FOCUS — zero residual defocus *and* a tight spot from the real folded trace.
* **C** PINNED LEG SURVIVES A NEGATIVE GAP — pinning mirror → sensor yields exactly the typed value.
* **D** SHARED — readout and solve both read `_shared_first_order_reference` (structural: a refactor
  that re-forks them trips the guard).
* **E** NON-FOLDED UNTOUCHED — the folded helper still returns None on an unfolded scene.

Against the unfixed code the guard reproduces the user's numbers on the portable fixture:
FOV **58.781** (vs 54 typed), traced spot RMS **1.02145 mm**.

## Owed

In-app eyeball on the real scene (the headless trace + guard cover the physics; the 3D/2D redraw
after the solve has not been eyeballed on GLX).

Note: `validate_nonseq_best_image_solve` fails on this branch **before** this change too
(pre-existing, unrelated: "Expected row 5 thickness to allow Best Image Solve, got None").
