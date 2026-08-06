# 0574 — a solve slid the lens and left its body pinned

Flag `flag_20260806_182735_708`, "changed FOV, lens body detached from surrogate, rays defocus at
sensor" — the third of three flags recorded 18:25–18:27 on 2026-08-06 against
`machine_vision_Apo75.py`: load Apo75 (FOV 23×23, in focus), swap to the PYRITE 45-85 (FOV reads
15.3×15.3), solve back to 23×23.

This document covers the detach. The defocus is [0575](0575_frozen_image_refusal_inverts.md) and
[0576](0576_best_focus_measured_in_the_wrong_frame.md).

## What the flags measured

| | flag 1 load | flag 2 swap | flag 3 solve |
|---|---|---|---|
| surrogate rows 1–5, world X | 82.039 … 132.042 | 82.039 … 121.558 | **110.501 … 150.020** |
| lens STEP body bounds X | [78.4375, 131.3375] | [80.5287, 128.3287] | **[80.5287, 128.3287]** |
| lens `placement_offset_xyz` z | −94.283 | −87.0287 | **−115.491** |

The solve slid the surrogate **+28.4622 mm** and the body's bounds came back *bit-identical*,
because `placement_offset_xyz[2]` moved **−28.4622 mm** — exactly cancelling it.

## Root cause

`slide_lens_block_along_its_leg` (`scene_placement_commands.py`) wrote only one of the two terms
the lens overlay needs:

```python
offset[2] = float(offset[2]) - amount      # CANCEL the datum-station growth (bugs/0527)
```

The missing term is the **carry**, `offset += direction * amount`. A fold leg's position lives in
`desp` (bugs/0499) and the overlay's axial pin `_lens_front_datum_z` reads *stations only, never
desp*, so this offset is the sole channel through which the barrel can follow its surrogate. With
the cancel alone the body is pinned by construction.

The drag has always had both — `next_offset = current + applied` at `translate_step_overlay`, then
the same `next_offset[2] -= lens_leg_slide`. bugs/0571 lifted this composite out of the drag so the
SOLVE could share it, but lifted only the cancel: in a drag the carry *is* the user's cursor delta,
so there was nothing that looked liftable.

0568 cannot cover this — `center_lens_body_on_surrogate_axis` projects out the along-axis component
by construction, and flag 3's detach is entirely along the leg.

## Fix

Write what the drag writes: carry along the leg, then cancel the station growth.

```python
offset = np.asarray(self._step_placement_offset_xyz("lens"), dtype=float).reshape(3)
offset = offset + shift
offset[2] = float(offset[2]) - amount
```

## Measured after

`bugs/diag_0574_solve_carries_lens_body.py`, Apo75 → PYRITE 45-85, 23×23 object solve:

```
solve: body [28.4622, -0.0, 0.0] vs surrogate [28.4622, -0.0, 0.0]  ->  attach_err 0.000000 mm
drag : body [28.4622, -0.0, 0.0] vs surrogate [28.4622, -0.0, 0.0]  ->  attach_err 0.000000 mm
```

The solve's placement offset now lands on `[136.2478, -0.0, -115.491]` — bit-identical to what an
equal drag produces, which is the point: the two paths were supposed to be the same gesture from
opposite ends, and now they demonstrably are.

## Why it shipped

`validate_open3d_0571_solve_slides_the_lens_along_its_leg.py` asserts B2/B3 on the lens **row**
pose, B4 on the BS row, B5 on the LED **body**, B6/B7 on the mirror row — it never reads
`_transformed_imported_step_mesh_for_label("lens")`. "The lens moves along its leg" was verified for
the rows only. `bugs/diag_0571_swap_then_solve.py` prints rows, stations, desp_z, world poses and
the LED housing centre, and nothing about the lens overlay, so the detach was invisible to the
diagnostic that certified 0571.

The only body-follows-optics assertion in the repo was the drag-only one at
`validate_open3d_0524_lens_drag_writes_sections.py` ("bugs/0527: the STEP body must ride the
assembly"). Phase 449 restates it for the solve — the invariant, not the instance.
