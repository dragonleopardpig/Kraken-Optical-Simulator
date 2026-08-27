# 0658 — The ordinary Edmund fixed-focal stock page ("Is your fix general enough?")

**User (2026-08-27 15:17, error.png):** `attachment/Lens/85869_35mm` refused with
"the datasheet PDF did not yield an effective focal length" — right after 0653. The
user's question: "Is your fix general enough?" Honest answer: it was not — 0653
covered the TELECENTRIC Edmund format; the #85-869 is the ORDINARY fixed-focal page,
a third variant.

## What the sheet says and what now parses (general parser, not a branch)

- `Focal Length FL (mm):35.00` — the FL token between label and unit defeated every
  earlier pattern; a dedicated row pattern now reads it.
- `Aperture (f/#):f/1.8 - f/16` — fastest stop 1.8 (the field's meaning), now a
  general fallback (was telecentric-branch-only).
- `Maximum Image Circle (mm):11.00` — likewise generalized.
- `Working Distance (mm):100 - ∞` — a RANGE: variable focus, so NO fixed-conjugate
  law is fabricated (mount_flange/optimum_wd stay None; the 0656 machinery keys off
  them). The surrogate builds via the honest EFL + STEP-span nominal split, object
  at a nominal distance; the user focuses/solves in-scene.

## Deliberately NOT mapped

The sheet also states `Object Space Principal Plane (mm):41.43` / `Image Space
Principal Plane (mm):-21.33` / pupil positions. Their reference convention
(front face? flange? image plane?) is unverified — mapping them wrongly would
silently corrupt the exact two-group solve (the 0371 "honest subset" doctrine).
EFL alone is sufficient and safe; the principal rows can join once the convention
is pinned against a known lens.

## Verified

#85-869 imports end-to-end (EFL 35, surrogate saved). Telecentric #67-304 and
ELS-85 regressions byte-identical. Guard 0653 gained section E (the FL row, the
fastest stop, the image circle, and the no-fabricated-law refusal); phase 489
covers it.
