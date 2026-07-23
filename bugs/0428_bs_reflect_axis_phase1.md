# 0428 (Phase 1) — Beam splitter draws its reflect-branch optical axis

**Flag `flag_20260723_141437`** (`machine_vision_AZ85_RA_Mirror_BS.py`):
> "No second optical axis is created for the BS plate."

Per the proposal (`bugs/PROPOSAL_bs_two_optical_axes_and_predecessor_placement.md`), a BS transmits
straight **and** reflects, so it has **two** optical axes. Phase 1 draws the missing one — the reflect
branch — **display only**, even with rays off (the flag was captured rays-off). Placement (the camera/lens
misplacement) is Phase 2.

## What it does

- **`nonseq_output_ports.beam_splitter_reflect_axis_frames(rows)`** — returns each promoted beam
  splitter's reflect branch as `(fold_point, reflect_direction)` in world coords. It gets the BS coating
  interaction face via the existing `optical_solid_face_world_records`, then applies the **same specular
  reflection a mirror fold uses** — `d − 2(d·n)n` — to the coating normal (the BS face is rejected by
  `_is_specular_fold_interaction_face` because a BS *splits* rather than fully folds, so this is a
  dedicated, display-only path). The fold point is where the x=y=0 `axis:global` crosses the coating
  plane (`t = (point·n)/n_z`).
- **`Kraken3DInspector._bs_reflect_axis_guide_records(bounds)`** — turns those into
  `axis:global:split` dotted guides reaching to the scene extent, exactly like the mirror fold guide
  (`_folded_reflected_axis_guide_record`).
- **`_optical_axis_records_for_3d`** appends them, independent of the mirror-fold path, so it also works
  on a BS-only scene (RA mirror removed) with rays off.

`axis:global` (the transmit leg) is unchanged — it already continues straight through a BS.

## Display only — placement is Phase 2

Phase 1 does **not** touch the follower placement: `build_optical_solid_output_port_pose_overrides` still
skips the BS as a fold source (bugs/0396–0399, "the camera must not follow the BS"). So the camera/lens are
not re-aimed here — this slice only makes the second axis visible. The predecessor-chain placement that
fixes the RA-mirror-removal misplacement is the next phase.

## Verification (`validate_open3d_bs_reflect_axis`, penta phase 345)

Display-free:

| check | asserts |
|---|---|
| REFLECT-MATH | `d − 2(d·n)n` sends +Z off a 45° coating to +X; the axis crosses the coating at `t = (point·n)/n_z` |
| NO-BS | no promoted BS → no reflect frames |
| MECHANISM | `_bs_reflect_axis_guide_records` uses `beam_splitter_reflect_axis_frames` + emits `axis:global:split`; the assembler appends it |
| PLACEMENT-UNCHANGED | the follower builder still skips the BS (Phase 1 is display-only) |

4/4 pass. Baseline phase 345 = pass.

## Files

- `KrakenOS/UI/nonseq_output_ports.py` — `beam_splitter_reflect_axis_frames`.
- `KrakenOS/UI/open3d_inspector.py` — `_bs_reflect_axis_guide_records` + assembler call.
- `KrakenOS/UI/validate_open3d_bs_reflect_axis.py` — guard (phase 345).

## In-app eyeball still owed

On `machine_vision_AZ85_RA_Mirror_BS.py` (rays off), the BS plate now shows a **second dotted optical
axis** along its reflect branch, in addition to the straight transmit axis. (Geometric approximation of
the reflect leg when rays are off; the traced rays give the exact path when rays are on.) **Next: Phase 2**
— predecessor-chain placement so removing the RA mirror retains the lens+camera and the camera follows its
immediate predecessor.
