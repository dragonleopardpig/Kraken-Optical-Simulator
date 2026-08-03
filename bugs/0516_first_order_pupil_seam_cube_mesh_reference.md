# 0516 — first-order pupil seam: the reference kept a cube-BS mesh that deflects its own probe rays

## Symptom

Sparse / thin ray bundles on frozen (0433 stay-put) beam-splitter chains — the long-standing
"non-seq first-order pupil seam" (`bugs/DESIGN_nonseq_first_order_reference.md`), forecast as
"likely next flag" after the 0433 arc. On `attachment/machine_vision_AZ85_RA_Mirror_BS.py` the
preview census was 837 paths with only 225 `hit_detector` (27% survival); the debug log showed,
on every launch:

```
[pupil] reference launch failed, geometric fallback:
IndexError('index 0 is out of bounds for axis 0 with size 0')
at trace_preview_sampling.py:813:_launch_reference_entrance_pupil_z <- PupilTool.py:638:__init__
```

so every world-bundle launch silently ran on the coarse geometric aim instead of the true
entrance pupil.

## Two stacked root causes

**(1) The 0465 centring was dead code.** `_center_reference_row` (paraxial_tools.py) — whose
docstring describes exactly this failure and its cure — contained a leftover measurement
kill-switch `return  # bugs/0465 A/B: centring disabled for this measurement`, accidentally
shipped inside the 0470 commit (822f6259, 2026-07-29). Since then the reference kept the frozen
rows' ABSOLUTE world desps/tilts, so PupilCalc's axial probe rays missed everything.
Fix: remove the dead return (the documented centring is active again).

**(2) The centred reference keeps promoted-solid MESHES, and a parametric CUBE beam splitter's
mesh is not straight-through-transparent.** Removing (1) alone changed nothing: the reference
rows came out perfectly centred, yet PupilCalc still died identically. Probe-traced by hand, the
axial chief ray enters the BS cube mesh at z≈157.4 and exits DEFLECTED (~0.5 slope in y: 0 →
0.24 → 5.21 → 13.53 across three surfaces), then dies before reaching the image. The 0094
choice to keep the mesh ("the mesh pose matches the live pupil") presumes a straight-through
mesh trace is straight — true for a tilted PLATE (lateral walk-off, direction unchanged), false
for the 0319 parametric cube: with the splitter coating stripped by
`_transmissive_reference_row`, its internal 45° diagonal face deflects/TIRs the probe ray.
PupilCalc's Newton iteration (`RMS_Pupil`) then diverges, its five probe rays vanish under
enforced vignetting, `raykeeper.pick()` comes back empty → the `L[0]` IndexError.

## Fix (root cause, shared path)

All three PupilCalc call sites route through `_pupil_model_inputs(build_reference=True)`
(analysis_compute_workflow.py), so the fix lives there:

- New invariant test `_reference_transports_axial_ray(system)`: trace ONE on-axis chief with
  vignetting ignored and accept the mesh-kept reference only if the exit DIRECTION is still
  axial (`N >= 0.999`). A plate's walk-off passes; a cube diagonal's bend fails; a dead trace
  fails.
- When the test fails, rebuild the reference with ANALYTIC flat plates: strip `Solid_3d_stl`
  from the reference rows (rc=k=0, matching `_transmissive_reference_row`'s no-mesh branch)
  and rebuild with `build=0`.

Verified on the frozen AZ85 scene: stripped reference → `PupilCalc OK,
PosPupInp=[0, 0, 158.78], RadPupInp=11.11` (pupil at the stop station, as expected).
Plain scenes and plate-BS scenes keep today's mesh-kept behaviour byte-identical (the test
passes, no rebuild).

## Guard

`validate_open3d_0516_pupil_reference_survives_cube_mesh.py` (penta phase 415): SOURCE — the
0465 kill-switch stays gone and the axial-transparency retry exists; REAL — on the frozen AZ85
scene `_pupil_model_inputs` + `PupilCalc` resolve a finite entrance pupil. `_note_pupil_launch_fallback`
now also increments `_pupil_launch_fallback_count` so probes can assert "no silent fallback"
without scraping the debug log.

## The 0507 marriage (0505 guard F1)

Making the true reference pupil win exposed a tracking gap the 0507 fallback used to cover:
the centred reference's pupil depth is a SUM OF ROW THICKNESSES, blind to a perpendicular
housing drag that moves the fold point by rewriting only world seats (0505 guard F1:
landed fell 188 → 162 = 86% < the 90% floor). The measured object → fold → stop path
(`_geometric_reduced_stop_aim_z`, 0507) does track live geometry. Fix in
`_launch_reference_entrance_pupil_z`: keep the reference's first-order content — the pupil's
OFFSET from the stop — but anchor the aim on the measured reduced stop distance whenever a
fold sits between object and stop (`aim = reduced + (pupil_z − stop_station)`); plain scenes
keep the raw reference z.

## Census note (after-fix)

Final state (anchored aim): 225/837 `hit_detector` — byte-identical categories to the 0507
fallback era on the AZ85 scene, because the reference's pupil-vs-stop offset there is only
+0.65 mm, so the anchored aim lands within a millimetre of the measured fallback aim. The wins
are mechanism-level, not census-level on this scene: 0 silent fallbacks (was 32+/session), the
true pupil (radius r=11.11, FNO 4.5) is now RESOLVED and available to consumers, and the aim
TRACKS live fold drags (0505 F1). The intermediate unanchored build — reference z applied as a
raw world depth — rendered a "fuller" fan but was mis-framed: it dropped landed rays to 188 and
failed F1; its census drop was the clue.
