# 0076 — Open 3D: promoting a solid parked far off-axis leaves a phantom disc on the optical axis (DEFERRED — cosmetic)

## Symptom (user's words)

`attachment/recorded_bug_repros/flag_20260612_215816_600` (and `_210130_974`,
`_212834_603`), layout `machine_vision_120mm_65M`:

> the ray still chasing the beam splitter as though it is in the optical axis, we
> can see the early focusing of the ray and the image is pulled forward. So the
> ray still actually see the beam splitter in the optical path.
> … as soon as I notice the snapping, I close the Face Editor without doing anything.

The user parks a beam-splitter cube **way off** the beam, right-clicks → the
bottom option "Promote STEP to Optical Solid Row" (which promotes *and* opens the
Face Editor), and a cube-shaped thing appears **on the optical axis** at the
focus, looking like the splitter snapped into the beam and the rays are catching
it. No coating is assigned (the editor is closed immediately).

## This is COSMETIC — the optics are correct

The cube is **uncoated**, so the build fully **neutralises** it (bugs/0065/0074):
`_build_system_from_specs` on the real layout + the recorded cube
(`desp=(79, 86, -181)`) produces a flat zero-thickness AIR surface — `DespX/Y/Z = 0`,
`thickness = 0`, `Glass = AIR` — and the Image stays at the baseline `Z = 481.08`,
**byte-for-byte the no-cube prescription**. The rays do **not** bend through the
solid, the focus does **not** move; it is purely a 3-D display artifact.

The recorder's `promoted_solid_rows` field (commit `720c24a`) confirms the live
row's `desp` is off-axis (not zeroed) while `row_actor_bounds["6"]` is the union
of the off-axis body **and** a separate on-axis cube-sized (50 mm) disc at the
surface's chain station `Z ≈ 481` (exactly where the lenses focus).

## Root cause

Promote parks the cube's optical **surface** at the end of the lens→image gap
(`Z ≈ 481`) and pulls the **body** back to `Z ≈ 300` with a large `desp_z = -181`.
bugs/0067 + bugs/0075 re-decenter the body **mesh** (`_iter_3d_optical_surface_meshes`)
and every `_runtime_transform_for_row` consumer (overlays / markers / gizmo) back
off-axis — but a *separate* on-axis actor at the chain station (the neutralised
surface's reference aperture) is **not** re-decentered, so it still draws on the
axis at the focus. `_iter_3d_side_body_meshes` skips file-backed solids
(`three_d_scene_tools.py:1608`), and `_scene_surface_meshes` caches
`bundle.surface_meshes` (`:1683`), so the exact actor needs a live render to pin.

## Investigation note — a DEAD END

Making a parked coated splitter inert by neutralising off-beam solids *regardless
of coating* was tried and **reverted**: it broke `validate_optical_solid_direct_mirror_faces`
— a Mirror/Beam-Splitter that **folds** the beam is also geometrically decentered
(off-beam by edge geometry) yet the rays **reach** it via reflection. Geometry
alone cannot tell a **parked** splitter (rays miss it) from a **folding** one
(rays reach it), which is exactly why bugs/0066 exempts coated solids. A correct
coated fix would need a ray-hit test, not geometry.

## Status: DEFERRED (cosmetic)

Per the user's call, off-axis promotion is treated as unsupported for now —
**workaround: don't promote a solid parked far off the beam; promote it on/near
the beam (then drag it off), or accept the on-axis display disc.** The optical
solve is unaffected either way.

If revisited, the fix is display-only: re-decenter (or suppress) the neutralised
solid's on-axis surface-station actor to match its body — or have promote insert
the solid at its parked `Z` instead of the gap end with a compensating `desp_z`.
This needs a live render of a minimal layout (the machine-vision layout SIGSEGVs
the offscreen Xvfb llvmpipe renderer) to identify the exact actor first.

## Not regressing the shipped fixes

bugs/0073 (beam-radius unit), 0074 (axial inertness) and 0075 (Face-Editor body
snap) are all shipped and verified; this deferred item is the residual *display*
of an off-axis-parked solid, not an optical defect.
