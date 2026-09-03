# 0710 — "after adjusting device size, the two big RA mirror decentered"

(flag_20260903_151255)

## Root cause

The shared leg toward the lens runs AT the centre-V's z. The 0709 fix moved
the V (and so the beam's leg) to the new mirror plane, but the two big
tilted LEG FOLD mirrors — RA mirror 1 (50 mm) and RA mirror 2 (40 mm) — and
everything that walks from them (the lens block seat, the camera, the
sensor) stayed at the old leg z: the beam bends delta/2 off their centres.

## Fix

`_slide_far_tower_rows` gains a third stamped class: `leg_fold` — a TILTED
world-placed solid row whose z lies inside the old tower span. Leg folds
ride the MIRROR PLANE (half delta) like the V; the lens block, camera and
sensor follow automatically because their walks anchor on these rows
(0433-frozen contract). Stamped on first classification for the same
crossed-the-centre stability reason as the other classes.

## Guard

`validate_open3d_0704_device_resize_follow` (phase 513): A3b narrowed (near
tower + unpaired solid stay), NEW A3d leg fold rides the plane, A4 extended
— 10 checks green. End-to-end numbers in the commit message.
