# 0013 — Imported-lens rim shows as several "sub-edges" + a stray edge highlight in the face-roles editor

**Status:** Fixed (2026-06-04). Root cause found headless, fix verified by an
image-snapshot render (before/after), covered by a display-free grouping test,
an image-snapshot test, and validator **Phase 21** (gate baseline regenerated).
**Component:** the **Assign CAD/STL Optical Faces** dialog 3-D preview —
`MainOpticalSolidFaceRolesDialog._open_optical_solid_faces_for_row` /
its nested `render_face_preview`
(`KrakenOS/UI/panels/main_optical_solid_face_roles_dialog.py`) — for a STEP
solid imported as **native B-Rep faces**.
**Reported via:** four in-app recorder flags on 2026-06-04 ~08:00
(`flag_20260604_080028_567`, `_080113_*`, `_080230_*`, `_080317_235`). Repro
bundles are gitignored, so the evidence is transcribed here.

## Symptoms (user's words)

> there is a stray mesh highlight at the lens edge when the front surface is
> selected (also reported for the back surface, and when the edge is selected)

> why the lens edge split into 4 sub-edges? For a user they are just one lens
> edge. Any way to remedy this?

Fixture: `attachment/Lens/Aspherized_Achromatic_Lenses/step_49665.step`, a
cemented aspherized achromat promoted to an optical-solid row, its faces opened
in the face-roles editor.

## State evidence

The flags' `state.json` all show `screenshot_kind: "dialog"`,
`picked_row_index = 1`, empty `step_actor_*` and `hover_outline_bounds` — i.e.
the issue is **inside the face-roles Toplevel**, not the main inspector scene.

## Root cause (confirmed 2026-06-04, headless)

Two coupled seams, both in the face-roles dialog:

1. **B-Rep faces were never grouped.** The dialog grouped only the *planar
   STL-cluster* path (`group_optical_solid_face_candidates`); the B-Rep branch
   hard-coded `_face_group_ids = [-1] * len(records)` ("each B-Rep face is
   already one whole optical surface"). That is false for the **rim**: the
   importer splits a lens edge into several co-axial, co-radial **cylinder**
   faces. The achromat's 7 faces are 3 caps (1 sphere + 2 bspline) **plus a rim
   of 4 cylinder faces** — two co-axial half-cylinders per element (radius 12.5,
   axis = optical axis; `S001` pair at axis z≈2.89, `S002` pair at z≈6.37).
   Ungrouped, those 4 read as 4 separate "sub-edges."
2. **Per-face feature edges at `feature_angle=5`.** `render_face_preview` drew
   **every** face's `extract_feature_edges(feature_angle=5, …)` — and on a
   *curved* (cylinder/sphere/bspline) tessellated face, almost every triangle
   edge exceeds 5°, so each curved face draws its **entire wireframe**. Worse,
   it drew non-selected faces at **opacity 0.82, width 1.4** in their role
   colour. So selecting the front cap still lit up the rim's 4 cylinder faces as
   a busy coloured wireframe band — the **"stray highlight at the lens edge."**

A headless before/after render (oblique side view, front cap selected)
reproduces it: LEFT the whole rim is a dense wireframe band; RIGHT (fix) the rim
is one clean edge and only the selected cap is highlighted.

## Fix

1. **Group B-Rep rim faces.** New
   `group_brep_optical_solid_faces(records)` in
   `KrakenOS/UI/services/optical_solid_geometry.py` (exported via
   `layout_editor`) buckets **cylinder** faces by `(rounded radius, canonical
   axis-line)` — the perpendicular foot from the world origin to the axis, so
   co-axial cylinders at different axial positions and **different solids**
   (a cemented doublet's two elements) land in the same rim group. Non-cylinder
   faces and lone cylinders stay ungrouped (`-1`); groups are renumbered
   `0..k-1` by descending member count, matching
   `group_optical_solid_face_candidates`. Wired into the dialog's `brep_backed`
   branch, so the **Group column + right-click "Select all in group"** now let
   the user role-assign the whole rim at once — the requested remedy.
2. **Draw feature edges per GROUP, faint when not selected.**
   `render_face_preview` now collects each face's offset mesh, then draws edges
   **once per logical group**: merge the group's meshes, `clean()` to weld the
   split seams, and `extract_feature_edges(feature_angle=18, …)` so a curved
   surface's interior facets vanish and only its real boundary/edge rings show.
   The selected group is bright orange (width 4.0, opacity 1.0); every other
   group is faint (opacity 0.22, width 1.1). Ungrouped faces are singleton
   groups, so flat-prism facets are unchanged. This collapses the 4 rim
   sub-edges into one edge and removes the stray highlight.

## Tests

* **Display-free grouping test** —
  `KrakenOS/UI/validate_open3d_brep_lens_rim_grouping.py`. Imports the achromat
  STEP, builds the B-Rep records, and asserts `group_brep_optical_solid_faces`
  puts all 4 cylinder rim faces in **one** group and leaves every cap
  ungrouped. Teeth: reverting the grouping (all `-1`) flips it to FAIL.
* **Image-snapshot test** (visual bug, mandatory) —
  `KrakenOS/UI/validate_open3d_brep_lens_rim_preview_snapshot.py`. Renders the
  dialog's preview edge-drawing (front cap selected) off-screen to a PNG and
  checks that the rim band is **not** a dense wireframe (bounded non-selected
  edge-pixel fraction) and that the selected-colour highlight is concentrated on
  the cap, not the rim. Teeth: the pre-fix per-face/`angle=5`/opacity-0.82 path
  fails the rim-clutter bound.
* **Validator Phase 21** —
  `phase_21_brep_lens_rim_grouped` in
  `validate_open3d_penta_telescope_comprehensive.py` imports the display-free
  test's core and source-couples both seams (asserts the dialog calls
  `group_brep_optical_solid_faces` in its B-Rep branch and that
  `render_face_preview` draws edges per group). Gate baseline regenerated
  (`tools/penta_validator_baseline.json`).
