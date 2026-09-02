# 0697 — flag_20260902_212316: "after rotation, the 4 green lines are not moved together"

The 0692 sensor cover strips (2 dashed edges per band) were drawn from their
AUTHORED world center/axis -- correct until the train rotates, after which the
sensor square follows the live detector while the 4 strip lines (and their
band labels) float at the old world spot.

FIX: the coverage overlay anchors the strips on the LIVE detector pose
(`img_pt` + the detector's own in-plane basis `iv`/`cross(normal, iv)`);
only the extents stay authored, now expressed IN THE DETECTOR FRAME
(bugs/0692_stamp_strips.py computes v_lo/v_hi along the live `iv` at stamp
time: A +0.845..+3.845, B -6.224..-3.114). Rotations carry the strips by
construction. Guard A8b re-pinned; om05a guard PASSED; verified on the saved
scene AND the rotated scene (the strips ride the sensor into the camera).

BONUS measured on the rotated render: faceB now SURVIVES a partial rotation
(the 0693-era "3 rays missing" limitation) -- the 0696 inline twin mirrors
the live launch, which then traces the real swung geometry.

Also in the flag: the "vertical golden straight line near the top of the
prism" = the PLACEMENT-HANDLE rail for S7 (mirror1), left active from the
rotate session (the flag's own status bar: "Placement handles: S7 | spacing
10 mm | extent 100 mm | placements 14 | handles 15"). UI, not scene geometry
-- dismiss by toggling placement handles off. If it keeps biting, an
auto-dismiss after rotate/drag commits is a candidate follow-up.
