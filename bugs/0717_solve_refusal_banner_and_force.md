# 0717 — refused solves alert in-scene + "Force FOV (show collision)"

USER DIRECTIVE (2026-09-04): "The user see the ray trace almost correctly
(with slight defocus). He thinks this lens can achieve this FOV. This is
misleading. The UI shouldn't silently fail and display as though it is
working. If it crashes, alert the customer with all parameters shown in the
3D scene. ... give an option to bypass constraint and let user actually see
the lens crashes to other component if the FOV is forced. ... Importantly, he
knows how exactly the lens crashes, the limitation of the correct working
condition of the lens." See [[feedback_no_silent_solve_failure]].

## 1 — the in-scene refusal banner (the safety fix)

Every FOV-solve refusal path now stashes `_fov_solve_refusal_info` on the
editor, and `Kraken3DInspector._update_solve_refusal_banner` (painted from the
scene refresh, so it survives every rebuild) renders a red panel under the
system HUD with all the numbers:

    SOLVE REFUSED -- the drawn scene does NOT deliver this request
    requested FOV 15.75 x 1.05 mm  (needs |m| 2.064)
    lens must move -187.7 mm along its leg
    delivered now: |m| 0.362  FOV 63.66 x 63.66 mm
    the object or image leg would go negative -- slide the fold mirrors first
    right-click the Device -> "Force FOV (show collision)" to SEE the limit

`fov_solve` clears the stash at entry, so a SUCCESS wipes the banner and a
refusal repaints it with this request's numbers. No more near-correct trace
masking a silent refusal.

## 2 — Force FOV (show collision) — the CARRY-MODEL move

`fov_solve(..., force=True)` short-circuits to `force_translate_lens_toward_object`.
Flag 143656 ("hay wired") exposed why every earlier cut exploded the scene: on
this chained frozen layout a `desp` write on row *i* shifts rows *i..N* TOGETHER,
so writing the move into all five block rows ACCUMULATES 1x/2x/.../5x (measured:
discs at 20/40/60/80/100 mm, the tail carried into Filter+camera+sensor at 5x).

The rigid move is the CARRY-MODEL two-write: put the whole move on the FRONT
datum row (carries the block AND the tail), then CANCEL it on the row after the
REAR datum (un-shifts the tail). Measured on om05a: rows 8-12 translate as one
(rigidity spread 0.000), the STEP body follows (anchored to the front datum), and
Filter / camera / sensor / every vendor solid stay byte-identical. `desp_z += amount`
with the conjugate's NEGATIVE object_delta drives the barrel toward the upstream
fold (RA mirror 1) = shorter WD. If a vendor solid sits immediately after the block
(no non-hardware cancel row), the force refuses rather than move hardware.

The crash metric is straight-frame STATION arithmetic (`_row_z_positions`): room =
along-axis gap from the front datum to the nearest upstream solid; penetration =
room − |move|. NO system rebuild (the prior cut's `_surface_origin_for_rows` loop
was ~17 full builds at ~50 s each = the "super long computation"; now ~8 s total).
The banner reports moved / clearance-or-penetration / obstacle.

VERIFIED on om05a (force at FOV 30/12/6): lens moves 97/163/186 mm, clearance
83.5 / 17.0 / −5.2 mm to RA mirror 1 (penetrates at FOV 6), hardware byte-identical
at every FOV, ~8 s each.


## Scope note

On a scene that needs a different lens CLASS (om05a resized small device ->
|m| ~2), the lens is driven toward the fold mirror until it penetrates it --
"this lens cannot, here is exactly where it crashes." Changing the
lens/prisms/machine is the engineer's call; the tool shows the truth, never
picks the remedy. NB: the penetration MAGNITUDE on a tight fold is an
approximation (the prescription-frame room measure); the in-app 3D overlap is
the ground truth, which is what the user inspects.

## Guard

`validate_open3d_0717_solve_refusal_banner` = penta phase 516 (A formatter
behavior incl. the penetration line; B wiring pins: stash clear/enrich, force
threaded to the slide + both room checks bypassed, banner painted from
refresh, Device menu force entry).
