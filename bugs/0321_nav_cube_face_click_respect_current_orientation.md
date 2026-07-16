# 0321 — Nav Cube face click ignores the current roll ("upside-down TOP" flips right-side-up)

## Flags
- `flag_20260716_080215_410` — *"It is about the Nav Cube, notice the upside down 'TOP',
  it is before it is clicked, the scene is what I orbit to the view I want."*
- `flag_20260716_080327_789` — *"After clicking the 'TOP', it doesn't respect the upside
  down 'TOP'. Can make all section at the Nav Cube respect the current orientation when
  clicked?"*

The user orbited to a view where the cube's TOP face reads upside-down, then clicked TOP.
Instead of settling on the nearest upright-ISH version of the orientation they were already
looking at, the view snapped the picture right-side-up to the canonical TOP up (+X). Same
complaint would apply to any face/edge.

## Root cause — the roll snap was gated on CORNERS only
bugs/0257 ported FreeCAD's NaviCube `getNearestOrientation`: a cube pick keeps the CURRENT
view's roll, snapped to the nearest clean orientation about the pick's sight axis. But the
inspector only invoked it for a **corner** (`orientation_kind == "corner"`, nearest of six
rolls). A **face** or **edge** click fell through to the canonical absolute `view_up` from
`orientation_pose` — so TOP always forced +X up regardless of how the scene was rolled. That
is exactly the "doesn't respect the upside-down TOP" the user saw.

The math to do the right thing already existed: `nav_cube_orientation.nearest_orientation_up`
takes a `steps` count and works for any axis. A face/edge simply needs `steps=4` (four clean
90-deg rolls) where a corner uses `steps=6`.

## Fix
`open3d_inspector.py` `_apply_navigation_cube_orientation`: apply the roll snap for EVERY pick
kind, choosing the step count by kind:

```python
kind = orientation_kind(tuple(int(s) for s in sign))
if kind in ("face", "edge", "corner"):
    view_up = nearest_orientation_up(
        offset, view_up, -view_dir, current_up,
        steps=6 if kind == "corner" else 4,
    )
```

So clicking TOP while looking at an upside-down TOP now stays upside-down (up snaps to the
nearest of +X / -Z / -X / +Z to what you had), never the forced canonical +X. The absolute
canonical ups still live on the `+yz/...` **preset toolbar buttons** (`set_camera_preset`) and
on `orientation_pose`, which are unchanged — only the cube CLICK is relative.

## Verified (display-free)
`KrakenOS/UI/validate_open3d_nav_cube_face_local_up.py` — **PASS**:
- **A** unit / perpendicular-to-sight / clean-90-multiple roll across many (axis, up) samples
  for all 6 faces + 12 edges;
- **B** nearest-of-4 snap table (roll k about the TOP axis snaps to the nearest 90-gridpoint);
- **C** idempotence on the four clean rolls (0/90/180/270) for every face + edge;
- **D** the user regression: click TOP with live up -Z → -Z, up -X (flipped) → -X, up near -Z
  → -Z, and it NEVER returns the forbidden canonical +X; symmetric FRONT/RIGHT spot-checks;
- **E** degenerate fallbacks (antiparallel axis / up parallel to sight) still finite + valid;
- **F** inspector source contract: snap applies to `kind in ("face","edge","corner")` with
  `steps=6 if kind == "corner" else 4`.

Red-green confirmed: a synthetic pre-fix (corner-only, `steps=6` only) source trips check F;
the fixed source is green. The existing corner guard
(`validate_open3d_nav_cube_corner_local_up.py`) still PASSES — its check F was updated to the
new all-kinds contract, its corner nearest-of-6 math (A-E) is unchanged.

Penta **phase 285** (`phase_285_nav_cube_face_local_up`); baseline `"285": "pass"`.

## Files
- `KrakenOS/UI/open3d_inspector.py` — `_apply_navigation_cube_orientation`: corner-only gate →
  all pick kinds, `steps=6 if kind == "corner" else 4`; docstring updated.
- `KrakenOS/UI/validate_open3d_nav_cube_face_local_up.py` — the new guard (`phase_285`).
- `KrakenOS/UI/validate_open3d_nav_cube_corner_local_up.py` — check F + docstring updated to the
  all-kinds contract (corner math A-E unchanged).
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — `phase_285`.
- `tools/penta_validator_baseline.json` — phase 285 baseline + title.
