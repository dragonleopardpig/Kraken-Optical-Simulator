# 0912 -- phase 329 (coaxial edge-profile selector) failed on moved code

The WIRING check searched `open_scene_source_edit_dialog` for six tokens. Since bugs/0885 that
function is a shim over the row form `row_forms/source_edit.py`, so all six failed while every
claim still held:
- the edge fields appear only for a coaxial source;
- they are seeded from `coaxial_edge_profile_and_width`;
- a save writes both keys through `coaxial_edge_penumbra_mm`.

The check now runs the REAL form on the validator's stub editor, which drives the real
`update_scene_source_spec`:
- the fields and their choices;
- the seed from the stored spec;
- Apply with Sharp stores `coaxial_edge_profile = Sharp` and `coaxial_penumbra_mm = 0.01`;
- a non-coaxial source gets no edge fields.

No product change.
