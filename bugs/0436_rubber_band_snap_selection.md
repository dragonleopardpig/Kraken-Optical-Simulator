# 0436 — Rubber-band snap: chained selection collapses, camera unselectable, degenerate 1-row snap

**Flags `flag_20260726_095147_996`** ("only one element selected after clicking Place → rubberband
select + snap to optical axis") and **`flag_20260726_095224_331`** ("after clicking 2nd optical
axis, the element snap to the first optical axis instead … Both should select 3 elements: the
Lens, camera and the 3rd RA mirror … the lens surrogate is not following the imaging lens"), same
recording as bugs/0435. First real-world exercise of the 0433-B/C features.

## What the state snapshots prove

- Flag 2 (armed chained snap): `interaction_mode=snap_rows_to_axis`, `picked_row_indices=[3]` —
  exactly **min() of the intended set**, and no row highlight. The plain variant had highlighted 2
  elements moments earlier. → the chained handoff degrades the multi-selection to the singular
  (the plural/singular SelectionModel desync family) and drops the highlight.
- The camera/Image row appears in NO `row_actor_bounds` snapshot — the Image row has no row actor,
  and the v1 rubber-band candidate filter excluded actor-less rows → **the camera can never be
  box-selected**, which is why "3 elements" could not be reached.
- Flag 3: row 3 (lens front datum) sits at exactly **(0, 0, 37.3) = the split axis's branch
  point**. A 1-row selection has no first→last direction; the rigid transform degenerates to
  "teleport to the branch origin". The branch point lies ON `axis:global` (x=y=0), so the user
  read it as "snapped to the first optical axis instead". It happened twice (t=362.6s, undone at
  ~374s, re-done before the 446s flag).
- With only the front datum moved, the lens surrogate block (rows 4–7) and the barrel stayed —
  "the lens surrogate is not following the imaging lens" is the torn-surrogate artifact of the
  degenerate single-row move.

## Fixes (this bug)

1. Chained variant arms with the FULL selection, highlighted — identical to plain-select + menu.
2. The Image row (camera) is a rubber-band candidate by its world center — an actor is not
   required; Object + trailing-AIR spacers stay excluded.
3. Degenerate guard: a snap whose selection cannot define a direction (<2 rows) is refused with a
   clear status line; nothing moves. Applies to rubber-band, Snap Selected, and Snap Assembly.
4. Surrogate-group integrity: a selection covering part of the lens surrogate block auto-expands
   to the whole block (status note), so a snap can never tear the surrogate from the barrel.

## Verification

`bugs/probe_0436_rubber_band_snap.py` (chained-arm parity, camera-by-center selection, 1-row
refusal, partial-block expansion); validator `validate_open3d_0436_rubber_band_snap.py`; penta
phase to follow.
