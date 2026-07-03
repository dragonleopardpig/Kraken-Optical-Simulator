# 0218 — incoming optical axis pokes 5 mm past the first RA mirror (fold elbow off-centre)

**Status: FIXED. On the two-mirror AZ85 (ELS-85 surrogate) the incoming +Z optical-axis guide
(`axis:global`) ran 5 mm PAST the mirror-1 fold vertex — it ended at Z=76.9 while the +X middle
guide (`axis:global:reflected:1`) starts at the 71.9 vertex (= the mirror body centre). So
mirror-1's fold ELBOW looked off-centre, while every other element (the lenses, the 2nd RA
mirror) showed the axis through its centre. The incoming clamp now ends EXACTLY at the fold
vertex, so incoming → middle → outgoing form one connected polyline through the mirror centres.
Fixes the `flag_20260703_162409_478` follow-up "the optical axis is not centered at the first RA
mirror ... all other element can be shown optical axis at the center of the element, except the
first RA mirror."**

## What the user flagged

Looking at the ISO view of `flag_20260703_162409_478` (the 3-optical-axis confirmation scene),
the user noticed the optical axis is not centred on the FIRST RA mirror only — the fold corner
sits high on the prism instead of at its centre. They correctly guessed a UI (display-guide)
issue, not an optics one.

## Root cause — a 5 mm anti-over-extension margin on the incoming guide

`axis:global` is the INCOMING +Z guide (object → mirror-1). `_optical_axis_records_for_3d`
(`KrakenOS/UI/open3d_inspector.py`) clamps its far end so the +Z guide does not over-extend past
the mirror (bugs/0189 — the X-width of the folded branch otherwise inflated the +Z pad ~300 mm):

```python
fold_point_z = self._folded_axis_incoming_fold_point_z()          # = 71.897 (the true vertex)
if scene_is_folded:
    z1 = min(z1, float(fold_point_z) + _AXIS_FOLD_POINT_GUIDE_MARGIN_MM)   # 71.9 + 5.0 = 76.9
```

`_folded_axis_incoming_fold_point_z()` already returns the correct fold vertex (71.897 = mirror-1
body centre). But the `+ _AXIS_FOLD_POINT_GUIDE_MARGIN_MM` (= 5.0 mm) allowance pushed the drawn
end to **76.9** — 5 mm past the vertex, toward the top of the prism.

Meanwhile the reflected guides carry NO such margin:

- the MIDDLE guide `axis:global:reflected:1` (bugs/0216) starts exactly at the vertex `(0,0,71.9)`;
- the single-fold reflected guide `_folded_reflected_axis_guide_record` also starts at
  `(0,0,fold_point_z)`;
- at **mirror-2** the middle guide ENDS and the outgoing guide STARTS both at `(206.15,0,71.9)` —
  a clean vertex meet.

So the incoming guide was the ONLY axis carrying the 5 mm offset. Mirror-2's elbow was clean;
mirror-1's incoming leg overshot its elbow by 5 mm — exactly the off-centre look. Measured on
the flag scene: incoming END Z=76.897, next-axis START Z=71.897 → **+5.000 mm gap** (present on
the single-mirror scene too, just never scrutinised there). The optics are unaffected — rays
reflect at the 71.9 hypotenuse regardless.

## The fix — clamp the incoming guide to the fold vertex

`open3d_inspector.py` `_optical_axis_records_for_3d`: drop the `+ margin` so the incoming +Z
guide ends AT the vertex.

```python
if scene_is_folded:
    z1 = min(z1, float(fold_point_z))   # ends at the vertex where the reflected/middle guide begins
```

This is a tighter bound than 0189's `fold_point_z + margin`, so it still satisfies the
anti-over-extension intent (the guide reaches the mirror CENTRE, well inside the body, and stops).
The `_AXIS_FOLD_POINT_GUIDE_MARGIN_MM` constant stays defined (the 0189 guard imports it). Applies
to single AND multi-fold — the incoming leg now meets the reflected/middle leg exactly at the
vertex on both.

Result (rays OFF, the recording state):

```
                          incoming END z     next-axis START z    gap
TWO-MIRROR                71.897             71.897 (middle +X)   +0.000 mm
SINGLE-MIRROR             71.897             71.897 (reflected)   +0.000 mm
```

## Verification

Display-free guard `validate_open3d_incoming_axis_meets_fold_vertex` (4/4, rays OFF):

1. TWO-MIRROR: incoming `axis:global` END coincides with the middle `axis:global:reflected:1`
   START at the fold vertex (gap 0 µm), both at `(0,0,71.9)`, incoming rising +Z from below;
2. SINGLE-MIRROR: incoming END coincides with the outgoing `axis:global:reflected` START (gap
   0 µm), no `:1` middle;
3. **CAUSAL:** the incoming END is the vertex (71.897), NOT the old `fold_point_z +
   _AXIS_FOLD_POINT_GUIDE_MARGIN_MM` = 76.897 — the 5 mm poke the user saw, now gone (a revert to
   the `+margin` clamp fails this check);
4. the fix is wired (`z1 = min(z1, float(fold_point_z))`, the `+margin` clamp removed).

Regression sweep — re-ran 6 axis/fold guards green: `validate_open3d_multifold_reflected_axis_segments`
(0216), `validate_open3d_second_mirror_incoming_axis_placement` (0215),
`validate_open3d_ra_mirror_faint_line_folds` (0189, its clamp is a local replica bounded by
`fold_point_z + margin`, which the tighter vertex clamp still satisfies),
`validate_open3d_ra_mirror_reflected_axis_backward_extension`,
`validate_open3d_ra_mirror_folded_cone_focus` (0203),
`validate_open3d_beam_splitter_transmit_and_second_axis`.

Registered as penta **phase 193** (`phase_193_incoming_axis_meets_fold_vertex`), baseline `pass`.
The full validator marathon still SIGSEGVs on llvmpipe, so phases 0–192 are carried forward.

Scratch probe (untracked): `bugs/probe_0218_*` was folded into the confirmation runs; the
end-to-end before/after gap is reproduced by the guard itself.

## In-app eyeball — OWED

The headless guard proves the incoming guide now ends at the vertex (gap 0 µm) with rays OFF.
The rendered dotted axis on the two-mirror AZ85 scene should now show mirror-1's fold elbow ON
the prism centre, matching mirror-2. Awaiting the user's in-app confirmation.
