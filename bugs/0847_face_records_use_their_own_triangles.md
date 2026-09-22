# 0847 -- a STEP face record is built from its own triangles; a hover outline stays on its face

The yellow "ghost" outline, open since the first day of this run. Latest sighting:
flag_20260921_163121 -- a large tilted shape floating above the om05a housing while the cursor
hovered `OPTICAL STEP S006/F005`.

## Measured, not guessed

The flag recorded the outline's bounds and the hovered face. The drawn body, the mesh the hover
cuts from, and the face's own triangles all agree; the **outline** did not:

    face S006/F005 (its own triangles)   a flat face
    hover outline                        centred on that face's plane, but 46 mm deep across it

It was a "planar outline" drawn perpendicular to the record's **normal** --
(-0.206, 0.712, -0.671) -- which belonged to no face on the body.

### Defect 1: records built from someone else's triangles (the root cause)

The prism assembly's display mesh carries **32 degenerate `VTK_LINE` cells** (a `clean()`
artifact). VTK numbers cells verts -> lines -> polys, so every triangle's cell id sits after
them:

    cells 61,730 = lines 32 + triangles 61,698
    face tags (kraken_step_face_index)   61,730 -- one per CELL
    _triangle_array_from_polydata        61,698 -- polygons only

`_step_overlay_analytic_face_metadata` compared the two lengths, rejected the tags as
mismatched, and fell back to STEP **tessellation** indices -- which are shifted against the
displayed triangles by up to 32. **583 of 710 face records** were built from the wrong
triangles; normals off by up to **90 degrees**. The grouped (axisymmetric) records used the
same shifted indices directly.

`open3d_face_index_edges` had already met this exact artifact (its
`_triangle_only_surface_with_face_index` drops the line cells *with* their tags) -- the hover's
face lookup used that repair, the metadata builder did not. Two consumers, two numberings.

**Fix:** `triangle_array_and_cell_values(mesh, name)` returns the displayed triangles and any
per-cell array through that same repair. The builder selects every record's triangles -- plain
and grouped -- by the aligned face tag. The triangle list comes back byte-identical in order
(so the cached face-snap STL and its digest do not change); only the lookup is corrected.

This is the `optical` slot -- the one promotable STEP -- so its face normals and centroids feed
more than the hover. On the scenes present, only om05a (`prism_assembly_chunk_armA.step`) uses
an analytic optical STEP; the lens and camera slots take the display-only STL path and never
reached this builder.

### Defect 2: a planar outline for a face that is not a plane

`axisymmetric_step_selection_face_records` exists for **vendor lens** STEPs, whose optical
surface is split into patches. It also runs on this prism assembly (it has cylindrical side
walls) and merged two -z planes and two +y planes -- two perpendicular coplanar pairs -- into one
"face". `_fit_plane_group` correctly marks that group unsupported; the record is emitted anyway.
Its averaged normal drew the outline **29.8 mm outside the housing**.

The grouping is not changed here: it feeds round-lens promotion and the lens pick, and a lens
cap is legitimately curved. The hover now keeps the planar outline only while it lies within the
triangles it outlines (a lens cap's projected rim always does); otherwise it draws the face's
true boundary edges. 5 merged groups on this body fall back; all 494 grouped outlines stay on
the drawn body (worst 0.26 mm).

Emitting groups whose own fit says `supported=False` is left as a follow-up -- it needs a
round-lens scene to prove it does not ungroup a real lens surface.

## Guard

`validate_open3d_0847_face_records_use_their_own_triangles.py`, display-free, penta phase 626.

- **A** synthetic (runs anywhere): across a stray line cell the reader returns triangles and
  tags 1:1 where the raw array is one longer; selecting by tag gives the true normal; CONTROL:
  tessellation indices used as positions pull in the other face (normal tilted to
  [-0.316, 0, 0.949])
- **H** the stay-on-face test, pure
- **R** the real prism assembly (SKIP if not checked out): the stray cells are still there; all
  718 records are built from their own face's triangles with true normals (0 off by > 1 deg);
  CONTROL: the old indexing puts 1321 faces on someone else's triangles; no hover outline
  leaves the body; CONTROL: without the test the averaged plane reaches 29.8 mm outside

Existing guards: 17 of 19 display-free face/pick/hover guards pass; the other two
(`validate_step_analytic_import`, `validate_open3d_lens_step_face_pick`) fail identically on
the unpatched code -- pre-existing, not this change.
