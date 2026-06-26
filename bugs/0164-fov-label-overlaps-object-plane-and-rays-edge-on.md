# 0164 — object FOV label overlaps the object plane + rays in the -YZ view

User report (two flags, *MV 150 mm 1X* machine-vision scene with the new Bopixel
BC-GN25M12X4 camera glued at the image): *"The FOV label overlaps both the image
plane and rays, can space out?"* In the -YZ view the green **FOV 12.8×12.8** label
sits right on the object plane disc and the ray bundle instead of standing clear.

## Root cause

`detector_coverage_label_specs` (services/detector_coverage_overlay.py) placed the
object FOV label *in* the object plane, offset purely in-plane at clock angle
**90°**. For the object axis `+Z`, `_basis` returns `u = +Y`, `v = −X`, and 90°
selects `sin(90°)·v = −X`. So the label's only offset was along **X**.

The user works in the **-YZ view** (looking along the X axis). An X-offset projects
to **nothing** edge-on, so the label landed exactly on the object-plane centre —
on top of the disc and the rays that launch from it.

The image-plane labels never had this problem: they are lifted *outward along the
detector normal* (away from the optics) before the in-plane clock placement, which
gives them a visible separation even edge-on. The object FOV label simply never got
the same treatment.

## Fix

Give the object FOV label the same normal-lift the image labels use: carry it
along the object-plane normal **away from the optics** (into the empty space behind
the object) by the label reach, and use clock angle **0°** so the residual in-plane
offset is `+Y` (vertical) rather than `−X` (invisible edge-on).

```
anchor = obj_pt − n̂·reach (lift behind the object)  +  reach·(+Y) (clear the axis)
```

For the MV150 1X scene (object FOV 12.8×12.8, reach ≈ 10.56 mm) the label moves to
`(0, +10.56, −10.56)`: ~10.6 mm up and ~10.6 mm behind the object plane. In the
-YZ view that is a ~14.9 mm diagonal step off the object plane — clear of the disc,
the rays, and the dotted optical axis. The label **text** is unchanged, infinite-
object scenes still draw no FOV label, and the image-plane labels are untouched.

## Guard

`KrakenOS/UI/validate_open3d_fov_label_edge_on_clearance.py` (display-free): the FOV
label anchor must lift behind the object (`dot(anchor−obj, img−obj) < 0`) and, in
the edge-on -YZ projection (drop X), separate from the object plane by more than the
FOV box half-diagonal — i.e. project clear of the box. Fail-before/pass-after: the
old in-plane −X placement projected to ~0 separation edge-on.

Penta phase 155.
