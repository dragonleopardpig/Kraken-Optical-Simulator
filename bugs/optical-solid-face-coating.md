# Merge: promoted-solid face coating ↔ the 2D "Coating..." library (+ apply it in the trace)

## Goal

The 2D **"Coating..."** editor edits a sequential surface's KrakenOS `Coating` table (`[R,A,W,THETA]`
→ `CoatingFun` Fresnel Rp/Rs/Tp/Ts). The **Face Editor** lets each face of a promoted CAD solid
carry a `coating` — but it was a free-text string that NEVER reached the trace (cosmetic).

Unify them: a face's coating is a name from the SAME `COATING_PRESETS` library, and the
non-sequential trace applies it through `CoatingFun` — the same physics as a sequential coating.

## Implementation (three layers)

1. **UI** (`main_optical_solid_face_roles_dialog.py`): the per-face "Coating" entry is a combobox
   over the shared `le.COATING_PRESET_NAMES` (editable — legacy free-text still loads).
2. **Resolver + build** (`layout_editor.py`): `resolve_optical_solid_face_coating(name)` maps a
   shared preset key → `(Coating table, CoatingMet=0)` (None for clear/empty/free-text). The
   system build resolves each promoted-solid face and stashes
   `surface.OpticalSolidFaceCoatingTables = {face_id: (table, met)}` (transient, never persisted).
3. **Engine** (`KrakenSys.py`): `__OpticalSolidFaceInteraction` adds `override["coating_table"]`/
   `["coating_met"]` from that map by `face_id`; `__CollectData`'s energy block
   `if (self.val == 1):` uses the per-face table in `CoatingFun` when present, else the surface
   table (additive — no per-face coating → byte-identical trace).

## Verified

- Resolver + build map: GREEN (penta.py / dove.py: a coated face → the map carries the 94%-mirror
  table).
- Physics, in the ACTUAL non-sequential trace: with "Protected mirror 94%" on a penta mirror face
  the face reflectance flips from **RP 0.042 (bare Fresnel) → 0.960** (the 94%-mirror table);
  cleared, it stays 0.042. Additive contract holds — `validate_open3d_first_order_reference` +
  `validate_open3d_promoted_step_refresh` unchanged.

## The override→collect seam (the subtlety that made it inert at first)

The override **carries** `coating_table` correctly (every hit, face_ids matched the map), but
`__CollectData` reads `self._collect_interaction_override`, which is **rebuilt** by 6 subset
builders (`KrakenSys.py` ~3737/3813/4133/4191/4369/4802) that copy only a few keys and **drop**
`coating_table` — so `CoatingFun` never received the per-face table (the change was inert).

**Fix (applied):** a dedicated channel `self._collect_face_coating_override` that bypasses the
subset rebuild —
- set per-face in `__OpticalSolidFaceInteraction`, UNCONDITIONALLY (None for an uncoated face, the
  `(table, met)` tuple when coated), so a previous coated face can never leak to this hit;
- read + reset (consume-once) in `__CollectData` alongside the other per-hit overrides, and used
  in the `if (self.val == 1):` energy block instead of the surface table;
- also reset at the other `_collect_interaction_override = None` boundary sites.

## Guard

`validate_optical_solid_face_coating` (display-free): A resolver, B build-map, C differential
physics (coated face → RP ~0.96 vs ~0.04 bare, near the table), D additive baseline — all GREEN.
Penta phase 172, baseline 173.
