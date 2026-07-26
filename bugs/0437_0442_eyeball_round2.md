# 0437–0442 — Eyeball round 2 of the 0433 workflow (6 flags, one recording)

Recording `recording_20260726_111200.json` + flags on build `ea3d4aa0`, continuing the
bugs/0433/0435/0436 arc. **Flag `flag_20260726_110233` confirmed the core loop: "1st RA mirror
deleted, all components stay."** The remaining flags each yielded a fix:

| bug | flag | root cause | fix |
|---|---|---|---|
| **0437** | `110337` "drag it down and the LED STEP shifted as well … old bug resurface" | the BS↔LED glue was born symmetric (0103/0127/0133); 0432's `cb57bd23` only added an Alt-drag suspend — a plain BS drag still carried the LED, cancelling the relative move | asymmetry at the single decision point `_carry_glued_optical_led`: BS-drag moves the BS alone (all three drag paths), LED-drag still carries the assembly. Guard `validate_open3d_0437_bs_drag_glue` |
| **0438** | `110540` "highlight with flashes only" | `_arm_snap_to_axis` styled the selection then `_hide_regular_rays_for_center_axis_pick` ran an unconditional `refresh_from_editor` — every actor rebuilt unstyled, and `apply_row_selection`'s matching-model early-return made re-styling a no-op | `force` kwarg past the early-return; selection re-applied in the `refresh_scene` funnel (sync + async rebuilds); arm reordered; ray-hide refresh only when rays were visible. Guard `validate_open3d_0438_armed_highlight` |
| **0439** | `110657` "snapped correctly but shifted to the left (crashing to the LED)… fold optical axis of the 2nd RA mirror missing" | (a) the snap translated the selection origin onto the axis's **branch point**, ignoring the click; (b) a frozen/snapped fold mirror emits no override → no reflected guide; (c) a later single-element snap (the camera) was refused by the 0436 <2-row guard | (a) landing = `picked_world` projected onto the axis line (rows + STEP carry share it; no click → branch point, byte-identical); (b) synthetic pickable `axis:global:frozen-fold:<row>` guide from the baked Mirror-face pose; (c) ONE element snaps **translate-only** (orientation kept, slides to the click; camera/lens body follows; empty still refused; lens-block rows still expand). Guards `validate_open3d_0439_snap_anchor` / `_0439_frozen_fold_guide`; 0436's tests updated to the new semantics |
| **0440** | `111415` "Object Plane is missing after enabling the overlays" | frozen/snapped rows carry baked world desp/tilt → the paraxial reference raised its centered guard → shared first-order reference None → magnification None → no object-FOV rect | breadcrumbed rows UNFOLD in the reference (placement zeroed, gaps kept) like the branch-arm path; hand-tilted prescription rows still raise. Also repaired the stale phase-90 guard (source check predated the 0297 delegation) — phase 90 was **mis-binned in the 0434 "environmental" 34** and is genuinely green again. Guard `validate_open3d_0440_object_plane_frozen` |
| **0441** | `111606` "Aperture plane still flipped" | TWO template-normalize paths flattened the baked (0,−90,−180) aperture placement: `_normalize_special_rows` zeroes Aperture `tilt_y/tilt_z`, and every table round-trip's `_clear_disabled_surface_type_fields` zeroes all template-disabled pose fields (Aperture enables `tilt_x` only — the BS-add's row rebuild triggered it) | both sites exempt rows carrying the 0433 freeze/snap ScenePlacement breadcrumbs (any surface type); prescription rows keep normalizing. Guard `validate_open3d_0441_aperture_ring_orientation` |
| **0442** | (found under 0440) | `delete_optical_step_rows` silently dropped the deleted solid's axial span (row thickness + trailing AIR spacer) — the AZ85 mirror delete shrank the object distance ~90 mm; first-order mag read 2.52 instead of 1.15 | span handed back to the preceding row's gap, exactly like unpromote; the 0433 freeze re-bakes against the corrected stations so world poses are unchanged |

## Still owed in-app (round 3)

1. The fixed loop end-to-end: add BS (nothing moves) → drag BS alone into place → delete mirror
   (stays put, aperture ring leg-facing, object plane drawable, mag ≈ 1.15) → rubber-band chain →
   click MID-AXIS on the split guide (lands at the click, not in the LED) → rubber-band the camera
   alone → click the "Optical Axis (fold)" guide of the 2nd mirror (translate-only slide).
2. The armed highlight persisting (no flash), the fold guide's visual weight, the
   "single element / expanded to the full lens group" status wording.
3. The silent-delete live repro from round 2 remains unexplained (right-clicks that invoked no
   mutator) — flag it immediately if a context-menu delete ever no-ops again.
