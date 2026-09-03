# 0701 — faceB glyph gated + per-band FOV values (flag_20260903_091545)

Flag: "As usual practice, please put in FOV values above the green object plane
for each A and B side. I still see the golden line, this time lying
horizontally at side B top prism."

## Part 1 — the golden line, final act

bugs/0699 fixed the glyph's transposed SHAPE (vertical 1×50 stripe → a thin
horizontal 50×1 panel hugging face B), but the user's original words were "it
shouldn't be there" — and they're right on principle, not just aesthetics. The
gold panel is the scene-source glyph for `source:faceB`, a spec carrying
`mirror_launch_plane_z`: it NEVER samples its own model — its rays are the
chain's calibrated launch reflected through the symmetry plane (bugs/0696
inline twin). The descriptor filter's own rule ("the glyph never shows a
supernatural emitter — display follows physics") says such a spec draws no
emitter panel.

Fix: `_add_one_scene_source_glyph` returns False for any source whose settings
carry `mirror_launch_plane_z`, before any renderer work. The spec stays LISTED
in the scene-source browser (the management handle for cone/count/bounds); the
face's green object-FOV band still marks the field location at face B.

## Part 2 — per-band FOV values

The split-field bands (bugs/0683/0692) deliberately suppress the single-axis
"FOV W×H" object readout (its full-FOV rectangle is wrong for a split scene) —
but that removed the object-plane FOV numbers entirely, and the user wants the
usual readout back per side.

Fix (bands loop in `detector_coverage_overlay`): each band now draws its own
`FOV {2·half_width:.1f}×{v_hi−v_lo:.1f}` billboard (om05a: "FOV 55.0×8.3" per
face), anchored just past the band's −Y edge — above the green plane, away
from the prism towers, in the user's working view. The single-axis full-FOV
label stays suppressed.

## Guards

- `validate_open3d_scene_source_object`: mirror-spec glyph gate check (a bare
  `None` self proves the gate fires before any renderer/basis work).
- `validate_open3d_0692_split_field_sensor_strips` (penta phase 508): C4 now
  forbids only circle/Needs labels; new C6 (one band-sized FOV label per face)
  + C7 (anchored above the band at both faces). While here: C3's stub
  expectation still assumed the pre-0697 `axis_v` mapping and was FAILING AT
  CLEAN HEAD (stash-proven) — re-pinned to the 0697 detector-frame anchoring
  (`iv = (0,0,−1)` for a +Y sensor normal, so authored v maps to
  `center_z − v`).

## Verification

`bugs/0701_check_glyph_and_labels.py` on the live scene: zero gold glyph
actors, two "FOV 55.0×8.3" billboards at (y≈−8.3, z=0) and (y≈−8.3, z=−50) —
above face A and face B. Render `bugs/0701_fov_labels_after.png`.
