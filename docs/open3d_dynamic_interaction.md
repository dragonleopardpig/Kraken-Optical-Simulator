# Open 3D: dynamic interaction guide (every CAD/Place/Orient command, in plain words)

Since flag_20260814 (bugs/0619), every command that acts on ONE element lives on that
element's **right-click** — 3D canvas and the Scene Components tree alike. The toolbar
menus keep the same entries for muscle memory, plus the scene-level operations that
have no single target (imports, export, clear). This page says what each command
actually does and how to reach it dynamically.

## The three direct-manipulation basics (no menu at all)

| Gesture | What happens |
|---|---|
| **Hold-drag a STEP body** (with "Move/Rotate whole body" ✔) | Lifts the body and moves it freely on the camera plane; release drops it. With the checkbox off, the same drag orbits the camera (bugs/0425: too easy to move things by mistake). Right-click → "Move Body" arms it for one body without the checkbox. |
| **Click/drag the red/green/blue arcs** on a selected body/row | Rotates it about world X/Y/Z in the "Rot" step (15…180°). Arcs appear via the checkbox or right-click → "Rotate Body". |
| **Left-drag on empty space** | Orbits the camera. Rubber-band select is armed from the right-click (below), then the drag draws the box. |

## Right-click an ELEMENT (row: lens surface, mirror, promoted solid)

**— Place this element —**
- **Move Row → Optical Axis** *(then click the dotted axis)* — translates the row so
  its centre sits on the axis you click. Rays are hidden while you aim so the dotted
  guides are clickable.
- **Snap Row → Target** *(then click a target row/face)* — translates this row's
  anchor exactly onto the target's anchor. Object/Image can be targets, not sources.

**— Orient this face —** (all of these ROTATE the element so its face normal points
along something; they write the row's TiltX/Y/Z and report the residual angle)
- **→ Target** *(click a row/face)* — normal parallel to that target's normal.
- **→ Ray** *(click a traced ray)* — normal along the ray direction near this row.
- **→ {Normal} Normal** — normal toward the named scene target chosen in the toolbar
  "Normal" box: **Detector** (the sensor plane), **Object**, or **Active target**.
- **→ own CAD axis {±X/±Y/±Z}** — snap the face normal onto the body's OWN local axis
  chosen in the toolbar "Axis" box (fixes an imported body whose face is tilted
  relative to its barrel).
- **→ Source-panel aim direction** — the direction typed in the Source panel.
- **→ Scene source emission** — the emission direction of the actual scene source
  object (the selected one, else the first enabled).
- **→ Path-view direction** — the direction of the currently chosen traced Path
  branch where it passes this row (choose a Path view first).
- **Preview normal error** — read-only: how many degrees the normal is off the
  chosen Normal target. Changes nothing.

## Right-click a STEP BODY (lens barrel / camera / LED / BS)

Already there from earlier work: Replace/Swap from folder, Flip direction, Glue to
surrogate ("Reset Camera to Image Plane" etc.), Resize, Promote, Hide, clear-aperture
tools, per-face role assignment. New:

**— Move / rotate this body —**
- **Move Body** *(then hold-drag it)* — arms the carry for THIS body; no checkbox needed.
- **Rotate Body** — shows the X/Y/Z arc handles for this body.
- **Center a Feature → Optical Axis** *(then click a planar/circular feature)* — the
  clicked feature's centre translates onto the optical axis.
- **Set Object-Distance Reference Edge** (LED only) *(then click an LED edge)* — that
  edge becomes the reference the Object↔LED distance dimension measures to, so
  distance edits slide the LED by the edge you care about, not a stray connector.
- **Delete {NAME} STEP** — removes this imported overlay (promoted rows survive).

**Face → axis, one step** (on the face you right-clicked — the toolbar versions need
a separate left-click first; these use the face under the cursor):
- **Snap Face Normal → Optical Axis (body centre lands)** *(then click the axis)* —
  rotates the body so this face's normal is parallel to the axis AND translates so
  the body centre lands at your axis click. The usual "put it on the axis, facing
  along it".
- **Snap Face Normal → Optical Axis (this point lands)** — same rotation, but the
  exact spot you right-clicked lands at the axis click (edge-precise).
- **Center This Face → Optical Axis (no rotation)** — pure translation of the face
  centre onto the axis; orientation untouched.

## Right-click with 2+ elements SELECTED

(Select several via right-click empty space → "Select Elements", then drag a box.)
- **Snap Selected → Optical Axis** *(click the axis)* — each selected element moves
  onto the clicked axis.
- **Group Selected as Assembly** — remembers the set as ONE rigid unit (a mirror's
  45° fold is preserved).
- **Snap Assembly → Optical Axis** — moves the whole rigid group.
- **Clear Assembly / Clear Selection.**

## Right-click EMPTY SPACE

- **Select Elements** *(then drag a box)* — rubber-band multi-select.
- **Select + Snap to Axis** — box first, then click the destination axis: one flow.
- **Move Elements Axis → Axis** *(click the OLD axis, then the NEW)* — every element
  on the old axis past the branch point relocates rigidly onto the new axis,
  distances preserved (re-solve afterwards).

## Still in the toolbar (scene-level, no single target)

Import STEP (4 kinds) · Import Lens from Folder (replaces scene) · Swap Imaging Lens
from Folder · Import Camera from Folder · Clear STEP Imports · Export STEP ·
Animate/Stop Galvo Scan (display-only animation of a mirror's configured scan list) ·
Measure / Measure E/E / Clear · the **Axis** and **Normal** boxes (they feed the
right-click Orient labels live) · "Faces..." (also on promoted rows as *Open Face
Editor...*) · "Source Target" (also: right-click a body/face → seat-source entries,
or right-click the source glyph itself).

## Notes

- Arm-a-pick commands always tell you the next click in the status bar; Esc or any
  other command cancels the mode.
- Everything here edits the same row fields the table shows (desp/tilt/thickness) —
  there is no hidden second transform (display follows physics).
