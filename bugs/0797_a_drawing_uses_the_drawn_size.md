# 0797 -- a drawing uses the DRAWN size, not the trace mesh

`flag_20260916_135706_487` ("Original scene") with `attachment/freecad.png`: the user exported
the WWK10-110CP-111V3 scene to STEP, opened it in FreeCAD, and reported *"there are oversized
Object Plane + Surrogate"* -- two disc flanges punching out through a 44 mm barrel, and a huge
disc where the object plane should be.

They were right, and it is a recurrence: `bugs/0674` was flagged with almost the same words,
*"the lens surrogate is oversized"*.

## Measured, from the user's own export

`attachment/MV-CH120-60UM_WWK10-110CP-111V3_3d.step`, against what the app drew for the same
scene (`row_actor_bounds` in the flag's `state.json`):

| row | `row.diameter` | app drew | exported | built `SDT.Diameter` |
|---|---|---|---|---|
| 0 Object at 1X | 58.5390 | 58.539 | **112.018** | 112.0180 |
| 1 Front Optical Vertex Datum | 28.0045 | 28.004 | **56.009** | 56.0090 |
| 2 Blackbox Group 1 | 28.0045 | 28.004 | **56.009** | 56.0090 |
| 3 Aperture Stop | 10.0045 | 10.005 | 10.005 | 10.0045 |
| 4 Blackbox Group 2 | 28.0045 | 28.004 | **56.009** | 56.0090 |
| 5 Rear Optical Vertex Datum | 28.0045 | 28.004 | **56.009** | 56.0090 |
| 6 Image / Sensor at 1X | 17.5161 | 17.516 | 17.516 | 17.5161 |

The stop and the image came out right, and that is the tell: they are the two rows the build
leaves alone. The lens STEP body measures 44 mm across, so 56 mm of "glass" cannot fit inside
it -- hence the flanges.

## Root cause: exporting the TRACE mesh instead of the drawing

The inflation is not a defect. `layout_editor._build_system_from_specs` puts it there
deliberately, and bugs/0623/0624 states the contract in its own comment:

    rows between the datums REFRACT out to 2x their drawn diameter (the trace mesh
    extends; the DISPLAY keeps the row's drawn size), the STOP keeps sole aperture
    authority, and the datum walls remain only as a far backstop annulus (2x..4x)

A vendor blackbox's row diameters are paraxial bookkeeping, not glass sizes, so a corner pencil
that threads the datum and the stop must still refract rather than strike a wall. Separately the
Object row is built at a computed `clear_aperture`, not at its own diameter -- which is why it
came out at 112.018 (= 2 x 56.009) against its own 58.539.

`bugs/0674` honoured the display half of that contract for the 3D view, rescaling the runtime
disc meshes to `row.diameter`. The STEP export builds its own geometry and never received it:

* `cad_step_export._write_step_with_analytic_surfaces` and
  `_write_step_with_cad_shapes_and_rays` both revolve `sdt[j]` -- the BUILT surface -- even
  though `rows[j]` is already in hand two lines above (they use it for bugs/0301's
  non-physical-row skip);
* `optical_solid_workflow._collect_3d_step_export_meshes` (the faceted fallback) reads
  `system.AAA` directly.

So one scene drew 28.004 and wrote 56.009.

## Fix

A drawing is sized by what is drawn. `_make_occ_revolution_face` takes a `display_diameter`
override, `_drawn_surface_diameter(row)` supplies `row.diameter` when it is a real size, and
both analytic loops pass it; the faceted fallback rescales its meshes about their own centre
exactly as bugs/0674 does. `InDiameter` is left alone (it is not inflated) beyond a guard that
drops an inner radius that would now exceed the outer one.

Nothing about the trace changes: `SDT.Diameter` still carries the 2x extension, the stop still
holds sole aperture authority, and the datum backstop annulus is untouched. Only the exported
geometry moves, and it moves onto the number the user already sees on screen.

## Verified

Re-exported the same scene through both writers:

| | analytic writer | native writer (the path this scene takes) |
|---|---|---|
| object plane | 58.5390 | 58.539 |
| datums + groups | 28.0045 | 28.005 |
| stop | 10.0045 | unchanged |
| image | 17.5161 | unchanged |
| vendor lens / camera solids | -- | 47.625 x 73.813 x 156.470 / 30.882 x 30.927 x 46.978, unchanged |

Every exported optical face now equals its row diameter to four decimals, and equals what the
app draws.

## Guard

`python -m KrakenOS.UI.validate_open3d_0797_a_drawing_uses_the_drawn_size` -- display-free. It
pins the contract at its source (the build still inflates, so the export must compensate rather
than the build being "fixed"), that both analytic writers pass a display diameter, that the
faceted fallback rescales, and end to end that a real export of a 2x-inflated scene writes the
row diameters. Penta phase 580.
