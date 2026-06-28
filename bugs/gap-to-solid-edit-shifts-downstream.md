# Editing "gap to solid" shifted the whole downstream + defocused the detector

## Symptom (recording_20260628_201449 + flag_20260628_203139 "YZ view")
Editing the **Object → BS** "gap to solid" dimension (~202 → 150 mm) shifted the BS AND the entire
downstream — the lens surrogate (rows 3-7) and the detector (row 8) ALL translated −52 mm rigidly,
while the object stayed fixed. Because the object→lens conjugate shortened by 52 mm but the
detector rode along, the image plane moved off the sensor → the detector **DEFOCUSED** (the YZ
flag shows the rays no longer converging at the sensor). User: "the surrogate should not move, but
it moves [the] same value… the detector is far from being focus now."

Confirmed from the recording's per-row rendered z-bounds:

| row | before | after | Δ |
|-----|--------|-------|---|
| 0 object | 0 | 0 | 0 |
| 1 BS solid | 201.7 | 149.6 | −52 |
| 3-7 surrogate | 275..324 | 223..272 | −52 |
| 8 detector | 614.6 | 562.4 | −52 |

(There was NO Quick-Estimation re-solve — the whole stack translated rigidly; my first read that
"QE did its job" was wrong.)

## Root cause
The "gap to solid" edit went through `apply_dimension_value`'s NORMAL path:
`rows[row_index].thickness = V` + a QE re-solve. A thickness change is CUMULATIVE — it shifts that
surface and everything downstream as a rigid block. For a beam splitter (no power) between a fixed
object and the lens, that's wrong: the user wants to SLIDE the BS, not translate the whole relay.

## Fix
`_solid_slide_compensation_row(row_index)`: when the next row is a promoted optical solid, return
the air-gap row immediately after the solid. `apply_dimension_value` then SLIDES the solid — sets
the gap to V AND subtracts the same delta from that trailing air gap — so the solid moves but the
downstream surrogate + detector (and the object→lens conjugate, hence the focus) stay put. The QE
re-solve is skipped for a slide (no conjugate change to chase). Falls back to the old cumulative +
QE path when there's no editable air gap after the solid (e.g. cemented).

## Verified (display-free)
MV150: editing the gap-to-solid to 150 mm → t[0]=150, trailing gap t[2] 17.85 → 70.0, BS z 202 →
150 (slides), lens z 275 → 275 and detector z 614.55 → 614.55 (BOTH preserved). guard
`validate_open3d_gap_to_solid_slide`. In-app eyeball still owed (the render/focus).
