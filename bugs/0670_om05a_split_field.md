# 0670 — om05a two-side split-field station: one chain, two faces, one camera

**User (2026-08-31):** "The reason I needed a 3D object rather than 2D plane is that
I need to inspect object opposite 2-side" — with the real folded setup
`attachment/om05a_26_1_r03_2s_lr_asm.stp` (GP-600 prism assembly + RA mirror + MV85
imaging lens + Edmund 48-926 filter + RA mirror + 25 MP CXP camera) and the
Prism_Assembly.png explanation. "proceed" on modelling it in KrakenOS.

## The unfold insight (what makes this tractable)

The CAD measures EQUAL path lengths from both device end faces to the lens (gaps
5.35/5.35 mm, inward legs 22.25/22.15). Unfolding the five folds therefore yields
**ONE sequential chain** — the 0297 doctrine (one shared first order) exactly:

- one object plane holding BOTH device end faces side by side (two field patches,
  centres ±5.5 mm, the beam separation out of the centre prism);
- the three prism glasses as N-BK7 plates at their CAD air spacings
  (outer 4336A 10.5 + lower 4337A 15 + centre 4338A 18 mm);
- the MV85 surrogate — EFL 85, f/2.8 assumed, m = −85/195 so object→H =
  f(1+1/|m|) = **280.0 mm, the lens's own designation** (LEN-MV85-280);
- the 48-926 filter as a 1 mm plate at its CAD position; the two RA mirrors are
  front-surface → display geometry only;
- the 25 MP sensor (5120² × 4.5 µm, diag 32.58, Manual image diameter — Auto mode
  re-derives the row diameter from the traced field on every load).

The folds are geometry, not prescription. The scene is
`attachment/om05a_two_side.py` (Filen-synced, not in git), with the real camera and
lens bodies extracted from the assembly into `attachment/om05a_components/`
(8 STEPs, AABB-centred) and wired via `camera_step_path`/`lens_step_path`.

## Physics verified (guard = phase 503)

- Focus by TRACED CONVERGENCE (0109), not formula: the sensor sits at the measured
  convergence; per-field rms **0.7 µm**. The refocus landed +3.4 mm past the
  no-glass conjugate — matching Σt(1−1/n)·m² + filter = +3.2 mm to 0.2 mm.
- Traced magnification: edge field lands at 4.401 mm for 4.400 requested (0.02%).
- Split field: the two faces land on OPPOSITE sensor halves (+2.2..+4.4 /
  −2.2..−4.4 mm), inside the sensor.
- 0109 gotcha RE-LEARNED: the focus metric must group rays by FIELD — grouping by
  patch measures the field spread (mm), not the blur (µm), and drags the
  "best focus" off by ~1 mm.

## Engineering readouts for the user

- m = 0.436: the 23.04 mm sensor width sees 52.8 mm of device length per frame.
- FNO 2.8 is an assumption (not on the drawing) — swap in the real value when known.
- The device faces (9 mm tall, ±5.5 mm centres) use only ±4.4 mm of the ±11.5 mm
  sensor half — margin for taller devices or looser prism spacing.

## Follow-up (recommended)

Folded DISPLAY over this straight trace — the two-arm display-fold pattern
generalised to the five om05a folds (its `fold_points` assumes one +Y fold today),
so the 3D canvas shows the REAL folded geometry with the prism assembly, mirrors,
and camera in their CAD poses while the trace stays this verified chain.

## v2 — the REAL lens (user: "the MV85 lens is PYRITE F4.5/85 mm/0.5x-2.0x V38, ID 1072517")

Rebuilt on `attachment/Lens/PYRITE_45_85_05x-20x_V38_1072517`: exact two-group from
its datasheet (EFL 85.13, SF −62.45, S'F' 63.18, span 39.52, f/4.5), its own barrel
STEP wired for display. The object leg is the CAD-measured geometric path
face→front rim = 275.4 mm (5.35 | outer 10.5 | 1.0 | lower 15 | 12.0 | centre 18 |
213.55 to the unfolded RA mirror 1); the image side is the traced convergence.

**Measured (guard re-pinned):** per-field rms 0.1–0.2 µm at the sensor; |m| =
0.4298 → **effective glass-corrected conjugate 283.2 mm ≈ the assembly lens's own
"LEN-MV85-280" designation** — recovered purely from CAD geometry + datasheet
cardinals + plate physics (face→H 298 geometric − 14.8 mm equivalent-air shift).
The image INVERTS (real lens): device face at +y object → −y sensor half. The rear
leg converged to 21.6 + 1 + 77.5 ≈ 100 mm — matching the CAD rear-leg estimate.
Note |m| 0.43 sits just under the lens's rated 0.5–2.0 range: the designed operating
point per the CAD, worth confirming against the vendor's OEM spec.

**Loading:** File → Open → `attachment/om05a_two_side.py`. Loads defer the trace
(0646) — press **Trace Now** for rays. The PYRITE barrel + SV25 camera bodies draw;
the prisms appear as their unfolded TUNNEL DIAGRAM (glass plates) — the honest
straight-chain representation; the folded display over this trace is the follow-up.
