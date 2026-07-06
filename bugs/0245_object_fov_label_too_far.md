# 0245 — Object FOV label floats too far from the object plane at large FOV

## Symptom
After an object-FOV solve to a large FOV (user: "FOV 55x55"), the green **FOV WxH**
text label sits conspicuously far above/behind the object plane — "the FOV 55x55 text
label seems too far away from the object plane." At the earlier 23x23 FOV it looked
fine; the gap grew with the FOV.

## Root cause
`detector_coverage_label_specs` (KrakenOS/UI/services/detector_coverage_overlay.py)
lifts the object-FOV label off the object plane along the plane NORMAL, and it used the
**full** in-plane reach for that lift:

    fov_reach = fov_diag * (1.0 + _LABEL_MARGIN) + _LABEL_GAP   # ~ the FOV half-diagonal
    obj_label_center = obj_pt - normal_hat * fov_reach          # normal lift == full diagonal

`fov_reach` is sized to clear the FOV RECTANGLE **in-plane** (so the billboard doesn't
overprint the rect corner). Using that same magnitude for the perpendicular (normal)
lift floats the label a whole half-diagonal BEHIND the object — ~18.7 mm at 23x23 but
~44 mm at 55x55 (fov_diag scales with the FOV). The edge-on -YZ view the user works in
shows that perpendicular float directly, so a big FOV reads as "too far."

The image-plane labels already solved exactly this (a full-diagonal normal lift plus the
in-plane radius floated them ~1.5x off): they lift by only a small fraction,
`sensor_half_diagonal * _LABEL_NORMAL_LIFT_FRACTION + _LABEL_GAP`. The object label was
never given the same treatment.

## Fix
Lift the object-FOV label off the plane by the same small fraction the image labels use,
keeping the full `fov_reach` only for the IN-PLANE offset that clears the rectangle:

    _obj_lift = fov_diag * _LABEL_NORMAL_LIFT_FRACTION + _LABEL_GAP   # 0.2 * diag + gap
    obj_label_center = obj_pt - normal_hat * _obj_lift

55x55 now lifts ~8.5 mm off the plane (was ~44 mm); 23x23 ~3.8 mm (was ~18.7 mm). The
in-plane placement (which clears the FOV rect and gives the edge-on separation checked by
bugs/0164) is unchanged.

## Verification
`validate_open3d_fov_label_edge_on_clearance` (the bugs/0164 guard) gains check **3b**:
the label's off-plane NORMAL distance must not exceed the FOV box half-diagonal (it was
~fov_reach > half-diagonal before, ~0.2x half-diagonal after). Checks 1-6 (text, behind
the object, edge-on in-plane clearance, vertical offset, image labels lifted, infinite
object draws none) still hold.
