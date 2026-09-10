# 0767 -- "land it" is a question about the PIXEL, not about millimetres

Flag `20260910_091428_853`, whose description was not a complaint but a confirmation:
*"30x30x1mm device focus correctly."* It carried the bugs/0764 fix working in the app --
0.05058 mm off the sensor, spot 0.224 um at the waist and **1.51 um on the sensor**, against a
**4.5 um pixel**. And the banner still ended with:

> Move the device stage / camera focus to land it -- vendor hardware untouched

There is nothing left to move. The blur is a third of a pixel. The gate was a hardcoded
`abs(offset) >= 0.05` mm, and that residual cleared it by **0.6 um**.

## The rule

A residual in millimetres is not a defect on its own. It is a defect when it costs sharpness the
detector can resolve. So the instruction is now gated on the traced blur against the pixel:

```
blur on the sensor <= pixel pitch   ->  "Landed: ... nothing to move"
blur on the sensor >  pixel pitch   ->  "Move the device stage / camera focus to land it"
```

A rectangular pixel is judged by its **smaller** side -- that is the finer sampling direction, so
it is the one that can still see the blur.

## The user's own numbers say the same thing

Production data for the three om05a configurations, at f/5.6:

| config | DOF | back-solved circle of confusion |
|---|---|---|
| FOV 20x20 | 86 um | **4.735 um** |
| ROI 34x29 | 195 um | **4.766 um** |
| ROI 54x29 | 410 um | **4.671 um** |

from `DOF = 2*N*c*(1+m)/m^2`. Every one lands on c ~ 4.7 um -- one pixel. The bench's own depth
of focus is *defined* by a one-pixel blur, which is the criterion above, arrived at independently.

## Not changed

- The measured offset is still reported. Landing is not a reason to hide where the image forms.
- With no usable pixel size (absent, empty, zero, junk) the old instruction stands. An unknown
  pixel is not a licence to declare success.
- `format_focus_summary_lines(None, ...)` still returns `[]` (the bugs/0728 contract).

The pixel comes from `_flag_camera_pixel_size_um()`, reading the same camera record the system
HUD prints, so the banner and the HUD cannot disagree about how big a pixel is while the user
reads both in one frame.

## Guard

`KrakenOS/UI/validate_open3d_0767_landed_is_within_a_pixel.py`, penta phase **552**: a sub-pixel
blur reports landed and never also asks for a move (A); a real miss still asks (B), including the
exactly-one-pixel and just-over-one-pixel edges and the rectangular-pixel case; an unknown pixel
keeps the old behaviour (C); the pixel comes from the HUD's own source and a scene with no camera
record yields None rather than raising into the banner (D).
