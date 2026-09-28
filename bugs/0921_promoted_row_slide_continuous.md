# 0921 -- promoted-row slide guard assumed snap steps; the full suite after 0916-0920 is green

**Full suite** (X299-SSD, inside `devenv shell`, after 0916-0920): **699 pass, 0 fail**. That
includes 0918's 2-D preview count and 0920's non-sequential edge-wall fix.

## `validate_open3d_promoted_row_slide` (stale)

A translate drag is CONTINUOUS by design ("the BS still moves in steps" request): the body moves
`pixels * step / pixels_per_step` mm per pixel, and only rotation, or a live "Snap mm", snaps.
The guard expected whole 18 px snap steps (6 x 1.784 = 10.703 mm for 120 px), but the product
moved 11.892 mm, which is exactly 120/18 steps. The expectation now follows the continuous law,
or the snap law when a snap is set. The rigid-slide and deferred-commit claims are unchanged and
pass.

## Held for a decision: the off-axis promoted STEP and the launch

`validate_open3d_face_assignment_sampling_stability` still fails. It was bisected to 596c8134
(05-25, "Center infinity field launches on stop"): the promoted prism becomes the
analysis/stop surface, so the launch moves onto its 42 mm decentre.

I tried keeping the launch on the axis (the axis point at the solid's z). That makes the rays
VANISH: with an optical-solid row present, the Image plane follows the prism's output port, the
on-axis rays meet no surface, and event-less paths are dropped. Either behaviour breaks one of
the user's rules ("element placement must not move the source" vs "rays must never vanish"), so
the change was reverted pending the user's choice.
