# 0067 — Open 3D: a neutralized off-beam (uncoated) solid's body snaps to the optical axis

## Symptom (user's words)

Two in-app repro bundles, recorded back-to-back:

`attachment/recorded_bug_repros/flag_20260612_102753_518`:

> The beam splitter snap to optical axis as soon as it is coverted to optical
> row and face editor launched.

`attachment/recorded_bug_repros/flag_20260612_103030_081`:

> After assigning partial reflecting surface and closed the Face Editor.

The user promoted a cube to an optical-solid row **while it was parked off the
beam** and opened the Face Editor — *before* assigning any coating. The 3-D body
immediately jumped onto the optical axis. Only after a Beam-Splitter ("partial
reflecting") coating was assigned did the body return to its off-axis station.

The recorded `scene_state` makes the snap-then-recover explicit (row 6 is the
solid):

* `flag_20260612_102753_518` (still **uncoated**, Face Editor open):
  `row_actor_bounds["6"] = X[-39.0, 39.0] Y[-38.98, 38.98] Z[556.6, 635.0]` —
  the body is **centered on the X=0,Y=0 optical axis** (`placement_translate_handle_count = 6`,
  `placement_rotate_handle_count = 9`, i.e. the Face-Editor gizmos are live).
* `flag_20260612_103030_081` (now **coated**, Face Editor closed):
  `row_actor_bounds["6"] = X[68.3, 123.5] Y[57.7, 112.9] Z[353.1, 431.3]` —
  the body is back **off-axis** (its X-center ≈ 96 mm), and `stray_props_above_body`
  is empty.

So the coated end-state is correct (that is bugs/0066). The defect here is the
transient: while the solid is still **uncoated**, its body snaps to the axis.

## Root cause

bugs/0065 is working as designed and is *not* the bug. An off-beam **inert**
(uncoated) promoted solid is never hit by the beam, so
`offbeam_optical_solid.neutralize_offbeam_inert_solids` correctly drops it from
the optical trace: in the built system its surface decenter is zeroed
(`SDT[index].DespX/DespY = 0`) and its mesh slot `EEE[index]` is left as a
placeholder, not a real body. That makes the optical solve correct (focus is
restored — the whole point of bugs/0065).

The leak is in the **3-D display path**, `three_d_scene_tools._iter_3d_optical_surface_meshes`:

* The body **geometry** comes from the live row's STL (`self.rows[index]`,
  which still carries the real `desp_x`/`desp_y`).
* The body **placement** comes from `transforms[index]` — i.e.
  `system.TRANS_2A[index]`, the *neutralized* per-surface world transform, which
  is now on the axis.

Because the neutralized surface's `EEE[index]` is not a real mesh,
`_runtime_trace_surface_mesh(system, index)` returns `None`, so the code falls
through to:

```python
if row_transform is None:
    row_transform = transforms[index]          # neutralized, ON-AXIS
if file_backed_optical_solid and row_transform is not None and mesh is None:
    solid_mesh = self._stl_mesh_with_world_transform(row, row_transform)
```

`_stl_mesh_with_world_transform` transforms every STL vertex by `row_transform`
alone (the row's own decenter is **not** re-applied), so the live geometry is
planted at the on-axis station → the body snaps to the axis.

bugs/0065's docstring claimed the body "keeps drawing in 3-D but stays outside
the optical trace path … the inspector keys on the live row overlay, not on
these transient build specs." The first half is true (the geometry is the live
STL); the second half was aspirational — placement still flows through the
neutralized `TRANS_2A[index]`, so the body never actually stayed off-axis.

A probe (`_build_system_from_specs` with vs. without neutralization) confirms it
exactly: for a cube at `desp_x = −55`, neutralized `TRANS_2A[cube]` translation
is `[0, 0, 110]` (on-axis) while the non-neutralized build gives `[−55, 0, 110]`;
the rotation blocks are identical and the delta is precisely the decenter.

## Fix (display-only — the optical solve is untouched)

New pure helper `offbeam_optical_solid.offbeam_neutralized_body_transform(base_transform,
spec, built_desp_x, built_desp_y)`. It restores the body's lateral station for
**display only**:

```python
transform[:3, 3] = transform[:3, 3] + transform[:3, :3] @ desp
```

It fires only on the exact neutralization signature: the live `spec` is a
promoted optical solid carrying a real decenter, **yet** the built surface's
`DespX`/`DespY` came back ≈ 0. Otherwise it returns `None` and the caller keeps
the ordinary placement — so a coated splitter (whose build keeps `DespX ≠ 0`,
bugs/0066) is a no-op and stays exactly where the trace put it.

The restoration is **exact** for an untilted solid: the non-neutralized and
neutralized `TRANS_2A[index]` share their rotation block `R`, and their
translations differ by precisely `R @ desp` (derivation: a promoted solid
defaults `AxisMove = 0`, so the decenter contributes only at its own surface,
`TRANS_2A = inv(Dxyz · C)` = `inv(C)` with translation `+R @ desp`). Restoring a
neutralized solid's *own tilt* orientation is out of scope (rare; coated
splitters — which can be steeply tilted folds — are never neutralized in the
first place).

Wired into `_iter_3d_optical_surface_meshes` right after `row_transform`
resolves and before the file-backed body is placed; it reads
`system.SDT[index].DespX/DespY` and converts the live row via
`surface_row_to_spec`. The optical prescription, the bugs/0065 focus fix, and
the trace are all untouched.

## Test (fails before, passes after)

`KrakenOS/UI/validate_open3d_offbeam_body_stays_offaxis.py` (new, display-free,
16 checks):

* **A** — the pure helper contract: `None` base → `None`; non-promoted → `None`;
  on-axis solid → `None`; build-kept-decenter (`DespX ≠ 0`) → `None`
  (coated-splitter safe); identity base + decenter → translation == decenter;
  rotation block untouched.
* **B (killer)** — a real `_build_system_from_specs` round-trip: the production
  (neutralized) `TRANS_2A[cube]` is on-axis and **would snap** (B3), and the
  re-decentered transform reproduces the non-neutralized `TRANS_2A[cube]` station
  byte-for-byte (`[−55, 0, 110]`, B4). Stubbing the helper back to a no-op makes
  B4 fail (`restored = [0, 0, 110]`, the snap), proving the guard has teeth.
* **C** — a coated off-axis splitter keeps its decenter in the build and is
  **not** re-decentered.
* **D** — `three_d_scene_tools` actually imports the helper + `surface_row_to_spec`
  (the wiring is present, not dead).

## Integrated

Phase 72 of `validate_open3d_penta_telescope_comprehensive.py` (display-free
wrapper over the new guard). Baseline `tools/penta_validator_baseline.json`
updated (`"72": "pass"`).

## Verification note

The live render / Face-Editor refresh cannot be confirmed headless (this layout
class SIGSEGVs the offscreen Xvfb llvmpipe renderer). The fix is pinned by the
display-free guard above — which proves, against the real build transforms, that
the neutralized body would snap and that the re-decenter reproduces the
non-neutralized world station — plus the code-inspection wiring check; the user
confirms the body staying off-axis at promotion / Face-Editor-launch in-app.
