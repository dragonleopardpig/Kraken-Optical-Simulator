# 0364 — "Imaging Lens" hide left a residual plane: the Aperture Stop row was under Layout

**Flag:** 20260720_082330_497 (build e00e2c1b). **Status:** FIXED 2026-07-20 (phase-311 guard).

The residual "plane" was the MV surrogate's **Aperture Stop disc (row 5)** — never hidden at all:
`_scene_row_category`'s token list bucketed it under "layout" ("aperture"/"stop" matched neither
the camera nor lens tokens), so the Imaging Lens cascade never reached it; its datum neighbours hid
only because their names contain "Lens". Fix: an "aperture stop" bigram OR `surface == "Aperture"`
now categorizes as **lens** (the stop sits between the two Thin-Lens groups — it IS the imaging
system). A Standard row merely mentioning "aperture" (the teaching scene's BS-exit stop) stays
under Layout — guarded both ways.
