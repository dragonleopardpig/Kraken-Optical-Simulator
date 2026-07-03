# 0212 — Fix A: pin a free-placed 2nd RA mirror to where it was dropped (stop "misplaced by itself")

**Status: FIXED (Fix A, minimal). The 2nd promoted mirror now stays pinned at its placed
`center_world` instead of being swept onto mirror 1's fold leg. It is inert in the beam — making
it a real second fold is the follow-up (Fix B / task #77 / bugs/0213).**

This implements **direction A** from bugs/0211 (the user chose "A then B"). bugs/0211 is the
diagnosis; this file is the fix.

## Flag

`flag_20260703_082955_542` "After promotion: 2nd RA mirror misplaced by itself", pinned by the
before/after pair `flag_20260703_090116_325` "Before promotion" + `flag_20260703_090206_958`
"After promotion, 2nd RA mirror misplaced again" (`recording_20260703_090237.json`):

- **BEFORE (placed, not promoted):** the `optical` overlay is drawn at world centre
  **`[210.7, 0, 71.9]`** — on the +X leg between the rear datum (X≈125) and the camera (X≈264–337).
  The user placed it correctly.
- **AFTER (promoted):** the promote captured that pose (`promotion_center_world = [210.7, 0, 71.9]`,
  `desp = [210.7, 0, -275.32]`) yet the solid is **drawn** at centre **`[269, 6.25, 71.9]`**,
  rotated, on top of the image sensor (row 9 X`[259, 292]`). It moved +58 mm in X and rotated.

## Root cause (from bugs/0211)

Inserted as a plain downstream row, mirror 2 is repositioned by mirror-1's fold frame in
`build_optical_solid_output_port_pose_overrides` (`KrakenOS/UI/nonseq_output_ports.py`). The
follower loop unconditionally writes `overrides[follower_index]` from the upstream fold frame +
cumulative station (≈347 mm), carrying mirror 2 down the +X leg to X≈269 and applying the fold
rotation. The `desp` the promote wrote (encoding the placed X≈210.7 in the *unfolded* sequential
frame) is overridden at draw time. So the placement is real, but the fold-chaining treats mirror 2
as a follower of mirror 1.

## Fix A (minimal, inert 2nd mirror)

A promoted optical solid that carries a solid mesh (`advanced['Solid_3d_stl']` set →
`_row_has_optical_solid` True) but has **no assigned port faces** is not a fold participant — it is
a freshly promoted part with no ports, i.e. the user's free-placed 2nd mirror. It must stay where
it was dropped.

In the follower loop of `build_optical_solid_output_port_pose_overrides`, right after the
`Object`-skip and **before** the override is computed/written:

```python
if _row_has_optical_solid(follower) and not _optical_solid_has_assigned_faces(follower):
    break
```

New helper (pose-independent face-assignment count):

```python
def _optical_solid_has_assigned_faces(row) -> bool:
    try:
        records = optical_solid_face_world_records(row, 0.0, assigned_only=True)
    except Exception:
        return False
    return bool(records)
```

The `break` terminates the follower chain **exactly where the pre-existing no-face optical-solid
branch already terminated it today** (that branch also `break`s when the solid has no valid
exit) — the only change is that the spurious override is no longer written first. So:

- **Mirror 2 gets no override** → its authored `desp` governs the draw. Because the promote wrote
  `desp = center_world − sequential_station` (`desp_x = 210.7`, `desp_z = 71.9 − 347.2 = −275.3`),
  the unfolded sequential placement reconstructs `[210.7, 0, 347.2 − 275.3] ≈ [210.7, 0, 71.9]` —
  exactly where placed.
- **Every other row is untouched.** In the base single-fold AZ85 there is no no-face 2nd solid, so
  the guard never fires and the overrides are byte-identical (Image still folds onto X≈275.3).

## Why penta-safe

A working fold mirror and every penta prism carry **assigned** faces (input/output/interaction/
mirror roles), so `_optical_solid_has_assigned_faces` is True for them and the guard is inert. The
discriminator fires **only** on a no-face solid, which is uniquely the fresh free-placed 2nd mirror.
`validate_open3d_penta_cascade_prism_by_prism` PASSES under Xvfb after the fix — the chief-ray exit
direction stays well-defined through all five folds, unchanged.

## Verification

Display-free guard `validate_open3d_second_mirror_pinned_to_placed_pose` (7/7), on the AZ85 scene,
against the pure override builder (no VTK):

1. mirror 1 (the fold source) is an optical solid **with** assigned faces → never pinned;
2. the base single fold stays intact — the whole downstream chain incl. the Image folds onto the +X
   leg (X≈275.3), so the fix does not disturb the working single fold;
3. a fresh 2nd mirror (faces stripped) is an optical solid with **no** assigned faces — the exact
   condition the guard keys on;
4. **the fix:** inserting that no-face mirror before the Image gives its row **no** override
   (pinned), while the upstream fold chain (rows 2..insert−1) is byte-identical to the base;
5. **causal / non-vacuous:** the *identical* mirror with its faces **kept** IS overridden (a fold
   participant) — the lone difference is the face assignment, proving the no-face guard is exactly
   what pins it (pre-guard the pinned mirror would have been swept the same way);
6. the pinned mirror keeps its placed `desp_x` and takes no override — the recorded `center_world`
   governs the draw;
7. the guard line is actually wired into the follower loop (not vestigial).

Registered as penta **phase 188** (`phase_188_second_mirror_pinned_to_placed_pose`), baseline set
to `pass`. The full validator marathon still SIGSEGVs on llvmpipe, so phases 0–187 are carried
forward.

## Known limitation / what's next (Fix B)

Fix A makes mirror 2 **inert**: it renders where placed but does not bend the beam, so there is no
working second fold and the detector still images the single-fold focus. Making mirror 2 a real
second fold — its own output-port/fold frame that continues the beam onto a new leg and chains the
detector to follow it (generalising the 0192 meridional re-fold + 0207 `desp_z` mapping from one
fold to two) — is **Fix B** (task #77 / bugs/0213). That touches the same penta-shared override
chain and needs in-app verification with the penta gate kept green.

**In-app eyeball owed:** the headless guard proves the spurious override is gone and the chain is
untouched; the final rendered world pose (desp reconstruction through the full display build) should
be confirmed once in-app.
