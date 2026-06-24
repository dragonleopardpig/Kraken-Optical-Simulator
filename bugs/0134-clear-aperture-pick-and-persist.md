# 0134 — a dedicated clear-aperture (CA) pick + persisted CA

## Symptom

The user right-clicked **"Center Picked Face → Optical Axis"** on the LED component
(`OPT-CO90-X-V1.6.2-H.STEP`) — aiming at the square rounded-corner **clear-aperture (CA)
window** on its front face — and filed flags:

- *"None of them highlight the CA edge."* The coarse pick grabbed a wrong housing face,
  never the CA window, so nothing useful was highlighted or centred.
- *"Please note that previously can highlight CA."* — a **regression**: the CA window used
  to be selectable.

The user also asked for better UX: *"Or do you have better idea to let user to select CA
out of a component?"*

## Root cause (two layers)

**(a) The LED is forced through coarse planar clustering.** `led` lives in
`ScenePlacementMixin._DISPLAY_ONLY_STEP_LABELS_NO_ANALYTIC`
(`scene_placement_commands.py:3808`, alongside `camera`/`lens`), so its generic right-click
face pick clusters near-coplanar polygons into big display-only groups. The CA window is a
small fine face; the coarse cluster swallowed it into a housing plane, so
"Center Picked Face → Optical Axis" could never resolve the CA itself.

**(b) The saved LED analytic vtp has 14 stray `VTK_LINE` cells** (a `clean()` artifact) at
cell ids 0–13. VTK's cell picker reports ids in the **full** `vtkPolyData` cell space
(verts, then lines, then polys). The `kraken_step_*face_index` cell-data arrays are stored
in that same full order — so `cell_data[cell_id]` is natively picker-aligned. But the
*reindexed poly-only* triangle array (60124 entries from index 0) is **off by 14** versus
the picker: resolving a picked cell id through the poly-only array returned a polygon 14
cells away, i.e. the wrong face.

The CA window's true identity: grouped selection face index **164**, area **4027.5 mm²**,
axis-facing (nz ≈ +1.000); `face_outline_from_face_indices(mesh, (164,))` draws its 972-pt
rounded-rect edge.

## Fix

Rather than loosen the LED's coarse clustering (which other LED interactions rely on), add a
**dedicated CA pick** that goes straight to the fine per-cell face index — sidestepping
layer (a) — and resolve the picked cell with a picker-aligned reader that tolerates the
stray lines — fixing layer (b).

- **L1 — `face_index_for_display_cell(mesh, cell_id)`** (`open3d_face_index_edges.py:447`):
  reads the full-cell-order `kraken_step_selection_face_index` (then `kraken_step_face_index`)
  only when its length equals the full cell count, and indexes it **directly** by the picker
  cell id — never the reindexed poly-only array. Returns the grouped face index, else the
  raw one, else `None` (e.g. a picked line/vert cell).

- **L2 — editor CA state** (`scene_placement_commands.py`):
  `clear_aperture_face_index_for_display_cell(label, cell_id)` (L1 + label→mesh),
  `set_step_clear_aperture(label, face_index)` records `{face_index, area_mm2}`,
  `step_clear_aperture(label)` reads it, `clear_step_clear_aperture(label)` forgets it, and
  `center_clear_aperture_on_optical_axis(label)` resolves the stored face's world centroid
  (`_step_overlay_fine_face_centroid_normal`) and hands it to the translate-only
  `center_step_feature_on_optical_axis` (x=0, y=0, keep z; **no rotation** — same contract
  as bugs/0111/0112).

- **L3 — inspector CA pick mode** (`open3d_inspector.py`): `start_step_clear_aperture_pick`
  arms a single-shot pick mode (mode badge "SET … CLEAR APERTURE"),
  `_update_clear_aperture_hover_highlight` hover-highlights the fine CA window face under the
  cursor, `_apply_step_clear_aperture_pick` records the picked face + exits, and
  `_add_clear_aperture_highlight_actor` draws the persistent cyan CA outline.

- **L4 — interaction wiring** (`open3d_interaction.py`): a click in CA mode applies the pick
  only on the wanted label (others nudge + ignore); hover routes to the CA highlight; CA mode
  is hover-critical.

- **L5 — right-click menu** (`open3d_face_assignment.py`): "Set Clear Aperture (pick window
  face)…", and (once a CA is recorded) "Center Clear Aperture → Optical Axis" / "Forget
  Clear Aperture".

- **L6 — persistent cyan CA outline** drawn in **both** STEP draw paths: the partial overlay
  refresh (`open3d_step_overlay_refresh.py`) and the full scene rebuild
  (`open3d_scene_refresh.py`).

- **L7 — persistence** (`layout_settings.py`): the recorded CA (`face_index`, `area_mm2`)
  is saved per label and restored on reload (only `face_index >= 0` survives).

## Test

- `KrakenOS/UI/validate_open3d_clear_aperture.py::run_checks` — display-free:
  - A **synthetic 18-cell mesh** with 14 stray line cells (ids 0–13) + 4 triangles proves
    the picker-aligned contract: `face_index_for_display_cell(mesh, 14) == 100`,
    `(mesh, 16) == 200`, `(mesh, 0) is None`; the poly-only array still has 4 entries.
  - A **fake editor** composing `ScenePlacementMixin` exercises `set_step_clear_aperture` →
    read-back → `center_clear_aperture_on_optical_axis` (centroid lands at (0,0,5) with no
    rotation) → `clear_step_clear_aperture`.
  - **Best-effort real LED vtp** (when the cad cache is present): finds an axis-facing
    ~4000 mm² face, resolves it, and outlines it.
  - **Source contracts**: pick routing, the inspector pick-mode tokens, the interaction
    handler calls, the three menu items + handlers, the CA outline in both refresh paths,
    and the layout-settings save+load round-trip.
- Penta phase **124**.

## Status

Fixed; guard green standalone and in the penta harness (phase 124, display-free). In-app
eyeball owed — the embedded-VTK CA hover/pick cannot be driven headless; the user should
confirm the CA window highlights on hover, the pick persists the cyan outline, and
"Center Clear Aperture → Optical Axis" lands the window on the axis.
