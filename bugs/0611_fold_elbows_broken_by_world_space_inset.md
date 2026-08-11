# 0611 — "Broken reflection rays" at the BS and RA mirror (FIXED)

Flags `flag_20260811_201311_592` ("broken reflection rays at BS") and
`flag_20260811_201334_635` ("broken reflection rays at RA mirror"), build `e705e161`,
scene `machine_vision_Apo75.py`. Both screenshots are deep zooms into a fold solid:
every ray elbow renders as two disconnected stubs — a cross-hatch of vertical and
horizontal fragments instead of continuous bent rays.

## Root cause — a world-space display inset is zoom-false

Since "Render Open 3D rays as physical segments" (4a23587e, 2026-05-22) the 3-D ray
mesh pulls each segment back from its interior vertices by
`_ray_vertex_display_inset(radius)` = clamp(scene_radius × 0.0015, 0.035, 0.18) mm —
a WORLD-SPACE inset meant to stop a segment's line cap from poking through the mirror
surface at a fold vertex ("mimic transmission"). On the Apo75 scene the inset sits at
the 0.18 mm cap, so every elbow carries a ~0.36 mm gap. Zoomed out that is sub-pixel;
zoomed into the splitter/prism it is the dominant feature — and it is a physics lie:
the reflected ray touches the mirror AT the vertex (the display-follows-physics
principle).

Any world-space gap fails at SOME zoom — the class fix is zoom-invariance, not a
smaller constant.

## Fix

`_ray_vertex_display_inset` returns 0.0. The real fake-transmission defense was never
the inset: it is that segments are DISCONNECTED (no polyline miter join to overshoot
the bend), which stays. A butt cap's lengthwise overhang is sub-pixel at every zoom.
The `vertex_inset` parameter machinery stays for callers that pass an explicit value,
and the May guard's mechanism contract (explicit inset honored, endpoints exact,
segments disconnected) still passes.

Verified by rendered close-up at the RA-prism hypotenuse: elbows connect, and at
moderate zoom no ray continues past the mirror plane (no fake transmission).

Guard: phase 463 (`validate_open3d_0611_fold_elbows_connect`) — production inset is
0, the production-built mesh keeps interior event vertices EXACT while segments stay
disconnected, and an explicit inset is still honored.

Note: `validate_2d_3d_projection_sync` (the May standalone) crashes with a tkinter
RecursionError at HEAD with or without this change — pre-existing, not marathon-wired.
