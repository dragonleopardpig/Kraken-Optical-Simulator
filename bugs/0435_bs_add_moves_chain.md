# 0435 — Adding the BS plate moves the folded chain (+ aperture flip, + silent mirror delete)

**Flag `flag_20260726_094845_383`** ("after RA mirror delete, the imaging lens, 2nd RA mirror and
camera shifted down, the Aperture flip direction") + full recording
`recording_20260726_095434.json` (1053 events, per-event scene_state), on the pristine AZ85 scene.

## What the recording proves (event forensics)

The user attributes everything to the mirror delete — the recording says otherwise. Structural
change-trace (row_actor_bounds / step_actor_bounds / axis records / aperture extents per event):

| t | event | what changed |
|---|---|---|
| 12.3s | session start | chain rows (x 77.6…235.9) on the fold leg at **z=53.0** (= mirror-1 row center, station 40.5 + desp_z 12.5); lens STEP z=53, camera z=−23.8; axes: `axis:global` only |
| **29.2s** | **Add Beam Splitter to LED ▸ Plate** | **everything at once**: BS row appears at actor index 2 (right after the mirror row — its inserted thickness grows every downstream station); chain rows jump **z 53→115.5 (+62.5, x preserved)**; lens STEP 53→115.5; camera −23.8→+38.7; **Aperture flips** from leg-facing (extents (0, 18.9, 18.9), thin-X) to straight-facing ((18.9, 18.9, 0), thin-Z) while its center stays on the leg; `axis:global:split` appears |
| ~200/204s | two right-clicks | the user's mirror-delete attempts — **row set never renumbers, nothing is removed** |
| 227.2s | flag 1 | user reports the "shift down" + flip, believing the delete caused it |
| 362.6s → 374s → 446s | snap / undo / re-snap | the 0436 story (separate doc) |

So: **(a)** `add_beam_splitter_to_led` violates the stay-put requirement for an axis-introducing
element — the live fold walk re-sweeps the chain along the leg because the inserted BS row's
thickness/gap (+62.5) grows all downstream stations; **(b)** with the BS row in the follower chain
the Aperture row keeps its folded center but loses its folded ROTATION; **(c)** the mirror delete
the user then attempted was a silent no-op on this BS-present scene (mirror overlaps LED+BS —
mis-target or failed resolve), which is why the prism is merely hidden inside the LED envelope in
the flag screenshot and the fold stayed live.

The chain z uniformity (+62.5 on rows AND pinned mirror-2 AND both STEP bodies) plus preserved x
spacing rules out a freeze bug — 0433's delete-freeze never ran (no delete happened).

## Fixes (this bug)

1. Stay-put on BS ADD: inserting the BS row must be placement-neutral for every existing element
   (station-neutral insertion at the root, or the 0433 capture/re-bake applied to insertion).
2. Follower rotation with a BS row present: the Aperture (and any follower) keeps its fold-correct
   drawn orientation.
3. Mirror delete works on the BS-present scene (correct target resolution), and the 0433 freeze
   then holds — the user's full workflow add-BS → delete-mirror → nothing moves.

Also observed (report-only): at session start the 2-mirror folded scene drew NO reflected axis
guides (`axis:global` only) — check against 0429/0430 expectations separately.

## Verification

`bugs/probe_0435_bs_add_stay_put.py` — pristine AZ85 → add plate BS → assert every pre-existing
row/STEP world pose byte-stable (incl. aperture thin-axis) → delete mirror → freeze holds.
Validator `validate_open3d_0435_bs_add_stay_put.py`; penta phase to follow.
