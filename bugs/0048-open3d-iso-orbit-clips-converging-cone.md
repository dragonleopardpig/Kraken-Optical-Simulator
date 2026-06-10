# 0048 — Orbiting the Open-3D view right after startup clips the converging cone

**Status:** Fixed (2026-06-10).
**Component:** Open-3D camera framing. `set_camera_preset` in
`KrakenOS/UI/open3d_inspector.py` (the "Iso" else-branch), with a defensive
clear-scene dolly in the same file and `open3d_scene_refresh.refresh_scene`.

## Symptom

Three sequential user flags
(`attachment/recorded_bug_repros/flag_20260610_130839_636/` → `_130854_277/` →
`_130912_090/`), captioned *"first view." → "second view, it starts clipping." →
"3rd view, clipped."* As the user orbited/zoomed the 3D view, the converging ray
cone and the image plane progressively disappeared — the far half of the scene
got sliced off mid-air (the optical axis dashed line truncated, the output cone
severed from its focus / the image marker).

The user's key scoping clarification: *"after clicking for example XZ view, then
rotation and zooming — no problem, no clipping. Clipping happens right after
Open-3D startup and start rotating and zooming."* So a **cardinal preset** cured
it permanently; the **startup / Iso** view did not.

## Root cause

The camera toolbar has seven buttons (`open3d_top_controls.build_view_toolbar`):
`Iso`, `+YZ`, `-YZ`, `+XY`, `-XY`, `+XZ`, `-XZ`. In `set_camera_preset` every
**cardinal** preset computes a `parallel_scale` and so ends on
`SetParallelProjection(1)` — an **orthographic** camera. The **`iso`** preset fell
through to the `else` branch, which set position/focal/view-up but left
`parallel_scale = None`, so it ended on `SetParallelProjection(0)` — a
**perspective** camera.

That single difference is the whole bug:

- In **parallel** projection the camera-to-focal distance is visually irrelevant
  (only `parallel_scale` sets the zoom), and VTK happily renders geometry that
  lies *behind* the camera position (the near plane may be negative). So a
  cardinal view can never clip on orbit/zoom — orbit preserves the distance and
  parallel zoom only changes the scale.
- In **perspective** projection the camera sits a finite distance from the focal
  point and the near clip plane is clamped strictly positive. The Iso framing put
  the camera close (recorded distance ≈ 66 mm, focal at the lens centre z ≈ 107.5,
  while the image plane is at z ≈ 229). Orbiting swings the image plane and the
  converging cone tip to a **negative** signed view-distance — *behind* the
  camera — where the near plane slices them off.

Headless confirmation: the recorded "clipped" camera
(`pos = (-35.2, 28.9, 155.25)`, `focal = (0, 0, 107.5)`) gives the image plane a
signed view-distance of **−21.9 mm** (behind the camera). Rendering that camera in
perspective reproduces the recording exactly (giant near lens, the output cone and
image plane gone). Rendering the *same* orientation in parallel shows the full
cone. Reproducing the Iso click against the **complete** scene placed the
perspective camera far out (distance ≈ 684, image plane at **+617**, in front) and
did **not** clip — confirming that the close, perspective Iso framing is the cause,
not the orbit itself.

## Fix

Make the Iso view orthographic like the cardinal presets. In the `else` branch of
`set_camera_preset`, project the eight scene-bounds corners onto the iso camera's
right/up axes and fit a `parallel_scale` (reusing
`_parallel_scale_for_orthographic_fit`), so the branch ends on
`SetParallelProjection(1)`:

```python
view_dir = -offset; right = normalize(cross(view_dir, up)); true_up = cross(right, view_dir)
rel = corners - center
horizontal_span = np.ptp(rel @ right); vertical_span = np.ptp(rel @ true_up)
parallel_scale = self._parallel_scale_for_orthographic_fit(horizontal_span, vertical_span, aspect)
```

The Iso **orientation** (looking from −X/+Y/+Z) is unchanged; only the projection
becomes orthographic — the same projection the six cardinal buttons already use.
Behind-camera geometry now renders, and the camera distance is visually free, so
orbit/zoom can never clip.

Backed by a defensive, **visually free** parallel dolly (the user asked for both a
"frame it right" fix and an "every-interaction backstop"):

- `_ensure_parallel_camera_clears_scene` (no-op unless the camera is parallel)
  dollies the camera back along its view axis until the whole scene's farthest
  corner is in front of it. In parallel projection this does not change the
  rendered image (distance is irrelevant; `parallel_scale` is untouched).
- `refresh_scene` calls it once after the complete scene is built (the first
  frame can otherwise be sized to an incomplete scene — only the lens bodies,
  radius ≈ 30 → distance ≈ 66 — which is exactly how the recording's camera ended
  up parked inside the scene's z-span).
- The interactor fires it on `InteractionEvent` / `EndInteractionEvent`, so any
  residual close-camera parallel state is pushed clear on the first orbit.

Ray tracing and the optical model are untouched; this is purely camera framing.

## Tests

`KrakenOS/UI/validate_camera_iso_orbit_no_clip.py` (live; SKIPs without a
renderer/Xvfb). It boots the cemented doublet (rays ON, refs ON) and asserts:

- **(A) root cause** — `set_camera_preset("iso")` yields
  `GetParallelProjection() == 1`. A revert to perspective fails here.
- **(B) no clip on orbit** — after an azimuth/elevation orbit (running the same
  `_on_camera_interaction` backstop the live interactor fires), all 8 corners of
  the complete scene bounding box have a **positive** signed view-distance, and so
  does the image plane (z ≈ 229) — the whole scene stays in front of the camera.
- **(C) backstop is free** — a direct `_ensure_parallel_camera_clears_scene` call
  leaves `parallel_scale` unchanged (zero visual change).
- **(D) image snapshot** — renders the fixed iso+orbit frame and, for contrast,
  the exact recorded perspective bug camera. Each frame is sampled (with its own
  camera's world→display projection) at the image-plane and cone-tip points: the
  fixed frame draws that geometry (patch coverage ≈ 0.04 / 0.06) while the buggy
  perspective frame clips it away (**0.0** — image plane at signed −21.9). Both
  PNGs are eyeballed (`iso_orbit_fixed.png`, `iso_orbit_buggy_perspective.png`).

A property-only check (just "is Iso parallel?") would pass for the projection flag
yet miss whether the rendered far geometry actually survives an orbit; the corner
signed-distance guard plus the fixed-vs-buggy snapshot contrast pin the visible
outcome. Folded into the comprehensive harness as **Phase 53** (reuses the shared
harness inspector; it is the last phase, so mutating its rows / camera is safe).

## Verification note

Rendered both frames under Xvfb and inspected them: the fixed Iso+orbit frame
shows the full input cone, the lens, the complete converging output cone reaching
the focus/image marker, and the full-length optical axis — nothing clipped. The
reproduced perspective camera shows the recorded symptom (an oversized near lens
with the output cone and image plane sliced off). The geometric guard reports the
whole scene 578.9 mm in front of the orbited camera, and the snapshot
discriminator is unambiguous (fixed draws the image-plane region, buggy reads 0.0).
