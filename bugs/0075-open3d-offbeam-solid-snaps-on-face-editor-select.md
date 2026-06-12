# 0075 — Open 3D: a parked off-beam solid snaps onto the optical axis when the Face Editor selects it (display-only)

## Symptom (user's words)

Recordings `flag_20260612_210130_974` / `_212834_603` / `_213626_155` (layout
`machine_vision_120mm_65M`):

> This is after face editor launched.
> same behaviour
> I strongly believe the promotion or the face assignment algorithm require
> snapping to optical axis.

The user parks the beam-splitter cube **way off** the beam, right-clicks the
overlay → the bottom option **"Promote STEP to Optical Solid Row"** (which
promotes *and* opens the Face Editor), and the instant the Face Editor launches
the cube **snaps onto the optical axis**.

## Decisive evidence

This could not be diagnosed from the earlier recordings — `state.json` showed the
body on-axis (`row_actor_bounds`) but not the row pose, so there was no way to
tell a data bug (decenter zeroed) from a display bug (decenter survives, body
drawn on-axis). They need different fixes, and the snap only fires in the live Tk
Face-Editor flow, not headless. So the recorder was first taught to capture each
promoted solid's live pose (`promoted_solid_rows`, commit `720c24a`).

`flag_20260612_213626_155` then settled it. Row 6 (the cube):

```
desp:                 [72.9475, 88.3741, -189.6733]   <- LIVE decenter, OFF-axis
promotion_center_world:[72.9475, 88.3741, 291.4092]   <- off-axis
row_actor_bounds["6"]: X,Y in +/-25.34, centred on (0, 0, 481)   <- body ON-axis
```

The decenter **survives** in the data; only the **display** snaps. A DISPLAY bug.

## Root cause

A parked off-beam solid is neutralised out of the optical trace
(bugs/0065/0074), so its build transform `TRANS_2A[index]` sits **on the optical
axis**. bugs/0067 restores the body's decentered station — but only in
`three_d_scene_tools._iter_3d_optical_surface_meshes` (the body-mesh path).

**Every other consumer of the build transform reads it through
`Kraken3DInspector._runtime_transform_for_row`**, which returned the raw on-axis
`TRANS_2A` with no re-decenter: the selected-body redraw, the assigned-face
overlays (`_add_optical_solid_assigned_face_overlays`), the face markers, the
virtual-plane markers, and the placement gizmo. So the moment the Face Editor
**selected** the solid — drawing its faces and turning on the placement handles
(`placement_translate_handle_count` 0 → 6) — the whole cube was redrawn at the
on-axis station, snapping it onto the axis while the row `Desp` stayed off-axis.
0067 fixed the body mesh; the **shared transform helper was the gap**.

## Fix (display-only — the optical solve is untouched)

Apply the same bugs/0067 `offbeam_neutralized_body_transform` re-decenter inside
`Kraken3DInspector._runtime_transform_for_row`, after the build transform is
resolved and before it is returned:

```python
redecentered = offbeam_neutralized_body_transform(
    transform, surface_row_to_spec(rows[row_index]),
    built[row_index].DespX, built[row_index].DespY)
if redecentered is not None:
    return redecentered
return transform
```

For a neutralised off-beam solid (built `DespX/DespY ≈ 0` yet a live decenter) it
restores the off-axis station; for an on-/near-beam or **coated** solid (the
build keeps the `Desp`) it no-ops. Now the body, face overlays, markers, virtual
planes and placement gizmo all agree on the off-axis station — the parked solid
stays where it was put when the Face Editor selects it.

## Test (fails before, passes after)

`KrakenOS/UI/validate_open3d_offbeam_body_stays_offaxis.py` — new **Section E**
(display-free): **E1** the `_runtime_transform_for_row` source applies the
re-decenter (wiring); **E2 (killer)** building a neutralised off-beam cube and
calling `_runtime_transform_for_row` through a minimal inspector returns the
re-decentered station (`x = -55`, not `0`); **E3** a coated splitter's shared
transform keeps its decenter (`x = -55`, no double-decenter). E2 fails before the
fix (`x = 0`, the snap) and passes after.

## Integrated

Phase 72 wraps this guard (`detail["checks"]` 16 → 19, recorded dynamically), so
the baseline `"72": "pass"` is unchanged. The `_runtime_transform_for_row`
consumers (`validate_open3d_mxied_prism_selection`,
`validate_optical_solid_direct_mirror_faces`) are unaffected; the
`validate_open3d_center_row_face_visual` lens-pick failure is pre-existing branch
debt (confirmed via `git stash`).

## Verification note

The build-level fix is proven by the display-free Section E against the real
`_build_system_from_specs`. The live render of this machine-vision layout
SIGSEGVs the offscreen Xvfb llvmpipe renderer, so the on-screen body staying
off-axis when the Face Editor selects it is the user's in-app confirmation.
