# 0087 — Open 3D: a dragged beam-splitter overlay snapped back to the optical axis when Show Rays was toggled off

## Symptom (user)

> [flag_20260617_213656_719] it snap back.
> [flag_20260617_211828_623] dragged out from the snapped axis, the beam splitter
> snap back again when ray off.
> [flag_20260617_211917_379] the gizmo is off body, not fixed.
> [flag_20260617_211953_617] right click on the beam splitter, become all pinks,
> and right click no promotion option, can't select individual face to direct
> assign beam splitting surface as well.

After snapping a beam-splitter overlay to the optical axis, turning Show Rays on,
dragging the cube off-axis, then turning Show Rays **off**, the cube's body
**snapped back onto the optical axis** while the user's placement was kept. The
displaced body then floated its rotation gizmo above itself, and right-clicking
the on-axis body could no longer resolve a face (faces sat at the dragged-off
pose), so there was no promote / face-assign option — just an all-pink whole-body
selection.

## Root cause (pinned by the new recorder diagnostics)

The recorder gained `step_overlay_poses` (bugs/0086 follow-up). The capture
settled it: `placement_offset_xyz` = `[-0.0, 42.933, 126.234]` (the drag y=42.9
**survived**) while `step_actor_bounds.optical` was on-axis (y ∈ [-25, 25]) and
`axis_anchor` was **null**. So the placement data was correct; only the **drawn
body reverted** — a pure display bug.

An imported overlay that an optical-axis snap has marked **physics-preview-ready**
is a **live-trace element**: with Show Rays on, the trace folds it in as a
transient row, and the cached scene bundle (`inspector._current_scene_bundle`)
holds that row at its current (pre-drag) pose. The live **carry-drag** moves the
body actors with `AddPosition` (cheap, for smooth motion) and commits the offset
**without rebuilding the bundle**. Toggling Show Rays then takes the fast
`can_reuse_current_scene_for_show_rays` path, which reused that **stale pre-drag
bundle** and redrew the body on-axis. The placement offset (42.9) was untouched,
so the gizmo / face-pick / right-click metadata stayed at 42.9 while the body
drew at 0 — the desync behind all four flags.

(Not reproducible until the overlay was marked physics-preview-ready: four
earlier headless replays drew the body at the live offset because the overlay
wasn't a live-trace element and so was drawn via the plain overlay path, not the
reused bundle.)

## Fix (this commit)

`can_reuse_current_scene_for_show_rays` now returns **False when the editor's
`_preview_scene_trace_dirty` flag is set**. A placement change routes through
`translate_step_overlay` → `_set_step_placement_offset_xyz` →
`_invalidate_preview_scene_trace()`, which sets that flag; a full rebuild
(`_build_preview_system_rays_bundle`) clears it. So after a drag the Show-Rays
toggle falls through to a full rebuild that redraws the body at its **live
placement** (stays where dragged — the user's "stay where I put it"), while a
clean scene (nothing changed) still takes the fast reuse path.

This resolves all four flags at once: no snap-back (body follows the drag), the
rotation gizmo is built around the body's real pose, and right-clicking the body
resolves its faces again (promote / assign-beam-splitter options return).

## Regression gate (display-free)

`validate_open3d_show_rays_toggle_rebuilds_moved_overlay.py` (`run_checks()`)
drives the real service: a dirtied scene is NOT reusable on a Show-Rays toggle
(rays on or off), a clean scene still fast-reuses, and a missing cached bundle is
never reused. Wired as penta **Phase 80**; baseline bumped to 81. End-to-end
proof (boots the inspector, marks the overlay physics-preview-ready, snap → rays
on → drag → rays off, asserts body follows to y≈42.9) verified during the fix.

## Status: FIXED
