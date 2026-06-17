# 0082 — Open 3D: "Promote and set <face function>" raised TypeError → promote silently did nothing

## Symptom (user)

> [flag_20260617_100505_707] click twice direct promote the selected surface to
> partial reflecting, not functioning.

State: the cube is still an `optical` STEP overlay — **no promoted row**
(`promoted_solid_rows = []`, table rows only 1–3), `show_rays = false`,
`use_nonseq = false`. Nothing happened when the user picked
**"Promote and set Partial Reflecting / Transmitting"** on the overlay face.

## Root cause (my regression, from the 0079→0081 kill-switch churn)

The debug log (`~/.cache/krakenos/logs/kraken_debug_latest.log`) has the exact
fault, twice:

```
Open 3D STEP promotion for face assignment failed:
ScenePlacementMixin.promote_imported_step_to_optical_solid_row()
got an unexpected keyword argument 'inpath_axial_placement'
```

bugs/0079 added an `inpath_axial_placement` kwarg and threaded it through the
**callers** — `open3d_face_assignment._promote_step_and_assign_face_function`
(`inpath_axial_placement=True`, the direct "Promote and set …" right-click) and
`open3d_step_state.promote_imported_overlay_to_row` (the "Promote to Optical
Element" path, which forwards it on to the editor). The underlying service method
`step_overlay_promotion.promote_imported_step_to_optical_solid_row` was given the
parameter too. **But the editor-facing wrapper that both paths actually call —
`ScenePlacementMixin.promote_imported_step_to_optical_solid_row`
(`scene_placement_commands.py`) — was never given the parameter.** So every
promote attempt died at kwarg binding with a `TypeError`, before any promotion
logic ran. Both promote gestures were broken, not just the face-assign one
(they funnel through the same wrapper).

The 0081 kill-switch (`_INPATH_AXIAL_PLACEMENT_ENABLED = False`) is unrelated to
this raise: it gates the placement *body* deep inside the service method; the
`TypeError` happened earlier, at the wrapper signature, so the kill-switch never
got a chance to neutralize it.

## Fix (this commit)

Add the keyword-only `inpath_axial_placement: bool = False` to
`ScenePlacementMixin.promote_imported_step_to_optical_solid_row` and forward it to
`self._step_overlay_promotion_service().promote_imported_step_to_optical_solid_row(...)`.
The service method already accepts it and still gates the actual behavior behind
the `_INPATH_AXIAL_PLACEMENT_ENABLED` kill-switch, so the value is threaded but
inert — the promote now runs via the historic append path, exactly as the menu
"Promote to Optical Element" does. This restores both promote gestures.

## Regression gate (display-free)

`validate_open3d_step_state_service.py` already exercised
`promote_imported_overlay_to_row("optical", …)` with a valid label, so it was
**red** with the same `TypeError`. Updated its `_Editor` stub to mirror the real
editor signature (accept + record `inpath_axial_placement`) and added an explicit
check that `inpath_axial_placement=True` threads all the way to the editor
promote call. The validator is now green and locks the forwarding contract. No
penta render phase is needed — the fault is a Python signature contract, not a
render outcome, and the penta comprehensive validator calls the promote with
default args (it never exercised the kwarg).

## Note for the user — why the beam still wasn't splitting

Two further conditions are independent of this fix and are needed to see the
split once the promote works: **Show Rays must be ON** (the recording had
`show_rays = false`, zero ray actors) and **Scene trace must be Auto /
Non-Sequential** (it was Sequential). Restart the app to pick up this fix, then
re-run "Promote and set Partial Reflecting / Transmitting".

## Status: FIXED (both promote gestures restored; step-state validator green)
