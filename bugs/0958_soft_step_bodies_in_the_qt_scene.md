# 0958 -- imported STEP hardware drawn soft; the Qt shell's scene does by default

Flagged 2026-10-04, `flag_20261004_165652_107`: "the 3D scene now back to TK. Previous QT, those
STEP files drawn nicer look, this is sure a TK version, not qt."

## What changed under the user

It is not the Tk app, but the observation is right about the picture.

- Until bugs/0951 the Qt shell's central 3D view was a bare *preview*: each imported STEP body one
  smooth translucent solid, nothing else.
- Since 0951 the central view is the real inspector, hosted in a Qt widget. That is where the Nav
  Cube, the gizmos, picking and the readouts come from. It draws with the same code as the Tk
  app's 3D window, so it also drew STEP hardware the way that window does.
- That way is: a flat-shaded body, then **two passes of its feature edges**, 2.8 px dark teal and
  2.0 px teal (the "glass" palette of bugs/0020, made for prisms and lenses). A vendor lens barrel
  has about 27 000 edge points, a camera body 60 000. Under two thick passes that is a dense dark
  web.

Rendered side by side on the flagged scene (`machine_vision_Pyrite90_0.3X`): dark-teal outline
pixels 14 438 outlined, 1 385 soft.

## Change

A display switch, **Overlays > Soft STEP bodies**, in both shells.

| | Outlined (the Tk app's look) | Soft |
|---|---|---|
| Body | flat-shaded, opacity as before (lens 0.26, camera 0.38) | smooth-shaded, at least 0.45 |
| Edges | two passes, 2.8 px and 2.0 px, glass palette | one pass, 1.0 px, grey-blue at 0.6 opacity |

- **The edges stay drawn in the soft style**, with exactly the same points: Alt-hover picks the
  nearest *drawn* edge (bugs/0323), so removing them would have taken that away.
- **Default: on in the Qt shell, off in the Tk app.** The Tk app keeps the look it has had since
  bugs/0020; nothing there changes unless the switch is used.
- **One function decides the style** (`step_overlay_style` in `open3d_scene_refresh.py`). The full
  scene refresh and the single-body refresh each had their own copy of the drawing; both read it
  now.
- Only imported STEP *hardware* (lens, camera, LED, optical overlays) is affected. Optical
  elements in the table keep the glass palette.
- Display only: switching re-draws the bodies and traces nothing.

## Guard: `validate_open3d_soft_step_bodies` (phase 728)

- **P:** the style function, off and on.
- **Q:** in the Qt shell the switch and its menu entry are on by default; each body is smooth, 0.45
  opaque, with one soft edge actor and no glass pass. The real menu entry switches to the outlined
  look (flat body, two glass passes) and back.
- **E:** the soft edge actor has the same number of points as each outlined pass (lens 27 082,
  camera 59 940).
- **I:** by the picture: five times fewer dark-teal outline pixels soft than outlined (measured
  ten times).
- **T:** in the Tk app the switch is off by default, a body carries the two glass passes and a flat
  body, and the Overlays menu offers the same entry.

**Seen by eye:** the flagged scene and om05a_folded, soft and outlined; a selected body in the soft
style still shows its selection tint.

**Mutation-checked:**
- the shell not switching it on, and the soft style drawing no edges: P, Q, E and I fail;
- the Tk app defaulting to soft too: T fails.

**Other guards run:** the glass-palette guard (bugs/0020), the lens STEP face-pick guard, the
toolbar guard and the interaction contract pass.

## Gates

- **Full Tk gate with 0958: 727 of 727 phases pass**, in parallel (`tools/penta_parallel_gate.py
  --jobs 4`), 41.6 min. It also covers 0957.
- **The Qt-hosted harness (`--shell qt`): 352 of 352 pass** with the soft default.

## Noticed

The ribbon decides whether to start folded from the *screen's* height, not the window's. A
950-px-high window on a 1440-px-high screen starts with the ribbon open and leaves the 3D view
339 px. A maximised window is unaffected. Not changed here.
