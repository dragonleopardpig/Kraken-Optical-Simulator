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

## 2 — Force FOV (show collision)

`fov_solve(..., force=True)` / `solve_fov_to_inspection_face(fov=, force=True)`
book the conjugate move ANYWAY past the room / negative-gap guards, on both
the lens-leg-slide path (bugs/0571) and the direct object/image gap
distribution (the om05a path). Vendor hardware never moves; only the lens and
the gap rows (the user's design variables) do. After the move,
`_report_forced_lens_clearance` measures the lens body against every solid
row's mesh: a NEGATIVE closest distance (containment-tested) is reported as
"the lens PENETRATES <component> by X mm -- the working-condition limit made
visible", both in the status line and the banner.

The Device browser menu grows a "Force FOV <W> mm (show collision)" entry
whenever a refusal is stashed, keyed on the refused request.

## Scope note

On a scene that needs a different lens CLASS (om05a 15 mm device -> |m| 2.06),
no lens position images it; force books the overshoot so the 3D shows the
lens driven into the prism, which IS the answer -- "this lens cannot, here is
how far short." Changing the lens/prisms/machine is the engineer's call; the
tool shows the truth, never picks the remedy.

## Guard

`validate_open3d_0717_solve_refusal_banner` = penta phase 516 (A formatter
behavior incl. the penetration line; B wiring pins: stash clear/enrich, force
threaded to the slide + both room checks bypassed, banner painted from
refresh, Device menu force entry).
