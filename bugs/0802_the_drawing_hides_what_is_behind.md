# 0802 -- the DXF draws only what is VISIBLE

Four reports against the DXF exports, one cause:

* `attachment/dxf.png` -- *"still have some stray lines"*, floating stubs inside the lens taper;
* *"those strays also break one of the supposed to be closed line"*;
* *"I think the camera is also quite messy"* -- `camera_top.png` / `camera_bottom.png`, from
  `MV-CH120-60UM_WWK10-110CP-111V3_Camera_6views.dxf`;
* *"some lines not closed or joined."*

## Three hypotheses killed by measurement first

Recorded because each looked right and cost time:

1. **The collinear merge moving endpoints** (bugs/0798's cause) -- already fixed; strays remained.
2. **The perturbed silhouette tilts** duplicating the cone's profile ~0.3-1.0 mm apart -- an
   export with a SINGLE tilt produced the identical strays (separations 0.996, 0.920, 0.871 mm,
   to the digit).
3. **Silhouette versus feature edges** -- a silhouette-only export and a feature-only export
   BOTH produced the same strays.

A fourth candidate rule -- *both ends free and strictly inside an outline* -- matched 383
polylines, 19% of the drawing. Rendered before trusting it, it would have deleted the flange
circles, the camera's real detail and the object-plane marker. Not shipped.

## Root cause: a see-through wireframe

The export projected EVERY edge of every body, front and back. Rasterising each body's depth and
testing its own feature edges against it:

| body | triangles | feature edges | occluded by the body itself |
|---|---|---|---|
| lens | 11272 | 4609 | **67.5%** |
| camera | 231606 | 57903 | **94.2%** |

94% of the camera's line work is geometry the viewer cannot see -- the thicket. The taper
"strays" are back-facing edges showing through the cone, which is exactly why no 2D rule could
separate them from genuine front detail: they lie inside the outline like real lines do. The
discriminator is DEPTH.

## Fix: hidden-line removal

`_SceneDepthBuffer` rasterises every solid in the view into one orthographic z-buffer (numpy
barycentric fill, 1400 px), and each body strip is cut to the runs that are not behind a solid.

* **Scene-wide**, not per mesh, so the lens occludes the camera too -- and the STEP companion
  EDGE actors (lines-only, the densest see-through source) are tested against it via the world
  points now carried on each body polyline.
* **Both exports**: the viewport DXF (one buffer) and the six-view component sheet (one buffer
  per view direction).
* **Only the BODIES layer.** Rays, axes and overlays draw over the scene in the 3D view, and the
  drawing follows the view (bugs/0800).
* **Closed outline rings are kept whole** -- cutting a ring into runs would stop it being a
  shape (bugs/0799).

Four details, each found by getting it wrong:

1. **VTK's projection direction points INTO the scene.** The first guard assumed the opposite and
   every verdict came out inverted -- the test's convention, not the buffer's.
2. **Sample ALONG segments, not only at vertices.** A merged straight edge is often one long
   2-point segment whose middle passes behind a body while both ends are visible.
3. **Outside the rasterised extent nothing is in front.** Samples beyond it had been clipped to
   the border pixel and inherited its depth, so a line leaving one side of a body read as hidden.
4. **A conservative test.** Sampling densely made lines lying ON rims and silhouettes flicker
   between hidden and visible at pixel pitch -- hole rims came apart into dots and flange edges
   turned dashed (six-view 1880 -> 6219 polylines). Each sample is now compared against the
   FARTHEST front depth in its 3x3 neighbourhood (a line truly behind a face still fails -- that
   face covers the whole neighbourhood), and hidden gaps of two samples or fewer inside a visible
   line are closed. Plus: zero-length polylines, which draw nothing, are dropped (92 on the
   camera sheet).

One refinement tried and **reverted**: dropping cut fragments under three pixels trimmed six-view
specks (3992 -> 3250) but the viewport buffer spans the whole scene at ~0.57 mm per pixel, so it
also cost 11 real lines over 5 mm. Not a clear win.

## Measured

| export | before | after |
|---|---|---|
| user's camera six-view sheet | **22223** polylines | **3900** |
| viewport, bodies layer | 7301 | **871** |
| lines over 5 mm, six-view | 186 (vertex-only test) | **227** |

The last row matters: the along-segment test keeps MORE long real lines than the first
vertex-only cut, which had been hiding some.

Rendered and looked at: the six-view TOP shows the connector and label recess instead of the PCB
and far wall; the FRONT shows the C-mount rings and sensor window; the viewport is a clean line
drawing of the lens, port and camera with no see-through edges.

## Honest residuals

* Small mount-hole rims on the six-view side views still break into dotted fragments -- the
  hole-bore edges sit at a depth discontinuity the 1400-px buffer resolves poorly on a small
  feature.
* Hidden-line removal cuts partially hidden loops, so the viewport now carries **15** closed-flag
  shapes where bugs/0799 had 105. That is the correct CAD behaviour -- a partly hidden circle is
  not a closed shape in a hidden-line drawing -- but it is a visible change.
* Export time is now ~48 s for the viewport and ~100 s for the six-view sheet.
* The viewport buffer's pixel size depends on the whole scene's extent; a large object plane
  coarsens the depth test for the small parts.

## Guard

`python -m KrakenOS.UI.validate_open3d_0802_the_drawing_hides_what_is_behind` -- display-free,
synthetic boxes. It pins that nothing is hidden with no solids; that a strip behind a solid is
removed, one in front kept end to end, and one ON the front face kept; that a strip passing
behind a body comes back as two runs cut at the body's edges, including a single long 2-point
segment; that a far body's edge is hidden by a near one where it covers it and drawn where it
does not; and that both collectors use the buffer, only on BODIES, keeping closed rings whole.
Penta phase 585.
