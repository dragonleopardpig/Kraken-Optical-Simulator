# 0100 — non-seq cube-before-lens focus bug (NEXT PRIORITY) + its display cascade

**Flagged:** `flag_20260621_144503` / `_144722` / `_145326` (2026-06-21), with the user notes
"transmit rays become less", "Object Plane missing", "ghost highlight on camera hover after BS".

## Root cause (ONE bug, four symptoms)
A glass plate/cube placed **before the lens** makes the non-sequential trace compute the wrong
first-order reference. Documented in `project_nonseq_first_order_seam`: the sequential PupilCalc
throws on a beam splitter → silent fallback aims the source at the cube → the transmit focus is pulled
**forward** instead of pushed back by the plate shift t(1−1/n).

Confirmed by `bugs/diag_1x_cube.py` on the 150mm 1X datasheet:
- NO plate : transmit converges z ≈ 186
- WITH 50mm BK7 plate: transmit converges z ≈ **78** (should be ≈ 613); shift **−107.75 mm** where a
  plane-parallel plate must give **+17.04 mm**.

## Cascade — all downstream of the wrong focus
1. **Transmit rays "become less"** — the beam converges at z≈78 then diverges; at the detector
   (595.8) it is a huge blur and most rays miss → fewer counted as transmitted. (The non-seq split
   itself is deterministic — `KrakenSys.py:3885` — so the loss is NOT the split mode.)
2. **Ghost highlight on the camera** (`flag_..._145326`) — the wrong focus relocates the
   detector/camera; the hover outline is drawn from the OLD pose (`hover_outline_bounds` z≈[590,640]).
   Same class as bugs 0085/0086 (stale hover geometry); may need the live-body refresh pattern even
   after the focus is fixed.
3. **Object Plane "missing"** — row 0 still has a drawn actor in `row_actor_bounds`, so it is not
   deleted; likely shoved off-screen by the broken scene scale. Verify in-app; should return once the
   focus is correct.
4. **-YZ flag** — a second view angle of the same scene.

## Fix (NEXT PRIORITY)
The **universal first-order reference** for the non-seq trace is the documented root, and Phase 1
(one-arm reference) + Phase 2 (per-branch pupil + per-branch launch) are **already shipped**
(`c86e23c`, `3b91f99`, `1188dd9`, `419e7df`, `0c3e0e2` …, see `project_nonseq_first_order_seam`) and
were confirmed in-app for the *dual-lens* two-arm scene. So the priority here is to find why **this**
scene still misbehaves and close the gap:

- `bugs/diag_1x_cube.py` exercises the RAW `Kos` core trace (focus z≈78) — the UI launch path
  (`_pupil_model_inputs` → first-order reference) is supposed to correct the *aim*, so the first job
  is to confirm in-app whether the transmit beam actually focuses on its detector here or not.
- This scene differs from the verified dual-lens case: a single imaging arm + a **promoted real cube
  with a partial-reflecting face** (a 2-arm split formed by promotion/face-edit, not a tagged
  two-arm layout). The Phase-2 per-branch launch is gated on `_imaging_branch_leaves` (arms with
  their own Aperture) — a promoted-cube split may not register as an imaging leaf, so the per-branch
  aim never fires and the transmit arm reverts to the wrong single-launch reference.

**Next step:** reproduce the promoted-cube-split scene in-app, check `sampling_diagnostics`
(active_preview_mode + whether per-branch launch fired), and either extend `_imaging_branch_leaves` /
the launch gating to cover a promoted-cube partial-reflecting split, or fix the reference for it.
Then re-check the ghost highlight (symptom 2) with the 0085/0086 hover-refresh pattern.

## Repro
`.devenv/state/venv/bin/python bugs/diag_1x_cube.py` — prints transmit focus z≈78 (with plate) vs the
expected ≈613, "BUG reproduced".
