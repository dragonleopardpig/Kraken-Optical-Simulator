# 0377 — Real lens STEP detached from the surrogate after 0374 (big mechanical barrel)

**Flag:** 20260721_082622 (build b8e6f3e2) — "the lens surrogate is detached from the Lens STEP",
on `attachment/machine_vision_150mm_test.py` (Edmund **15056** MV-150 lens). User: "after your fix
yesterday [0374], the lens STEP is detached from the surrogate." **Status:** SHIPPED 2026-07-21
(guard `validate_open3d_lens_step_glass_recenter`, bugs/0377 checks).

## Why it happened

bugs/0374 re-centred the lens STEP overlay so the optical **glass-block centre** lands on the
surrogate's datum-span centre. That is correct for a machine-vision surrogate whose STEP is a **close
barrel wrapping its glass** (PYRITE/ELS-85: body only ~1.1–1.2× the glass block, so the re-centre
barely moves the barrel). It is WRONG for a **real lens barrel**:

| lens | body span | glass span | datum span | 0374 shift from body-face pin |
|---|---:|---:|---:|---:|
| PYRITE 1072517 (surrogate) | 47.9 mm | 39.5 mm | 39.5 mm | ~0.5 mm (fine) |
| **Edmund 15056 (real barrel)** | **112.6 mm** | 52.9 mm | 48.8 mm | **−37 mm (detached)** |

The 15056 STEP is a 112 mm mechanical mount whose front sits ~35 mm AHEAD of the glass. Pinning the
glass to the datum then drags the whole barrel ~37 mm off the surrogate — the "detached" the user saw.
The AUTHORED registration for such a barrel is the **body-face pin at the front datum** (the pre-0374
behaviour), which the user relies on.

## The fix — gate 0374 to close barrels only

`_lens_step_display_front_z` now applies the glass re-centre ONLY when the body closely tracks the
glass extent:

```python
if glass_span <= 1e-6 or body_span > 1.6 * glass_span:
    return front_datum_z   # authored body-face pin (pre-0374 behaviour)
```

All the MV surrogates are body/glass ≈ 1.08–1.21 (re-centre applies, 0374's flip-fix preserved); the
15056 real barrel is 2.13 (gated out → body-face pin → attached again). Threshold 1.6 has wide margin
on both sides. Display-only, as before.

Verified headless: 15056 `_lens_step_display_front_z` returns the front datum for both orientations
(0 shift, attached); PYRITE still re-centres; the 0374 flip-invariance / vertex-Σd checks still pass.

## Files

- `KrakenOS/UI/services/layout_polyline_display.py` — the `body_span > 1.6 * glass_span` gate in
  `_lens_step_display_front_z`.
- `KrakenOS/UI/validate_open3d_lens_step_glass_recenter.py` — big-barrel (body >> glass → body-pin) +
  close-barrel (body ~ glass → re-centre) checks added to the 0374 guard.
