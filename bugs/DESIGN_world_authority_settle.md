# DESIGN — world authority + settle: finishing the drift deliberately

Adopted 2026-08-07, from the user's direction after the 0574–0582 arc:

> The codebase has been drifting toward world authority for ~150 bugs (0433 freeze, breadcrumbs,
> `_rebake_frozen_row_world_center`, `apply_image_distance_frozen_aware`). Finish the drift
> deliberately. Swapping can only be guaranteed bug-free when "where things are" is stored as
> where things are.

## The disease, named once

The prescription chain (`station = Σ thickness`, `desp` as decoration) claims authority over a
product whose truth is WORLD POSE. Every writer that touches a thickness on a frozen scene must
remember to re-bake / hold / carry N other things, and each forgotten one is a numbered bug:

- 0456 — capture the camera before the gap write, or it double-counts
- 0571 — hold the glued illumination unit across the write ("the remedy has to be expressed in
  WORLD terms first")
- 0581 — the same hold, forgotten in the split writer; bookkeeping parked in a row a normaliser
  erases
- 0236 — carry free-placed followers after a fold-leg write
- 0383/0546/0547 — the swap's downstream-anchor arithmetic and preserved/frozen frames
- 0478/0575/0580 — the gap row runs backwards; raw writes invert; negative gaps poison

These are all manual approximations of ONE missing primitive.

## The settle contract

```
settle(targets) -> (ok, message)

(i)   every TARGETED row/body lands at its target world pose exactly;
(ii)  every world-anchored thing NOT targeted keeps its current world pose;
(iii) the books come out legal: thickness >= 0 everywhere, station-neutral rows stay 0
      (bugs/0435/0569), bookkeeping only in rows that survive normalisation;
(iv)  when (i)-(iii) cannot hold together, refuse with the numbers and write NOTHING
      (the bugs/0572 idiom -- no partial writes, no silent clamps).
```

Clause (ii) is where every historical bracket collapses to. Clause (iii) is the 0580 lesson: a
"works" flag can carry poison — LOOKS-right (world re-baked) is not IS-right (books legal), so
settle asserts legality at exit. Prescriptions remain — as DERIVED bookkeeping the sequential
engine consumes per arm (the two-arm display-fold north star is unchanged: world authority lives
in the EDITOR; the engine still receives straight per-arm prescriptions).

## Stages (no big bang)

- **(a) Safety net — DONE.** Phases 446–450 freeze the invariant set; the recorded-sequence
  replays (`bugs/diag_0580_pinned_leg_negative_gap.py`, `diag_0574_*`, `diag_0577_*`) are the
  behavioural fixtures.
- **(b) Image side first (the pain centre) — STARTED, this commit.**
  `_settle_image_fold_world` is the settle for the image fold's span, and the existing API
  (`_apply_frozen_image_split`, `apply_image_distance_frozen_aware`) now routes through it.
  Callers did not change. The duplicated make-room / hold / capture code between the two
  writers is deleted into it.
- **(c) Migrate the swap and the drag/solve composites.** The swap's splice re-derives
  downstream stations (0383 anchor + 0546 preserved rows + 0547 frozen frame are three partial
  world-preservations of the same thing); replace with: capture world for everything downstream,
  splice, settle. The 0526 drag composite's `desp_z -= slide` accompaniment and the 0571 lens-leg
  slide's carry+cancel become settle calls with the block targeted and everything else clause-(ii).
- **(d) Delete compensation machinery as each writer moves.** Each deletion gated on its
  validator staying green: the illumination brackets (0571/0581), the camera captures (0456),
  the follower carries (0236) on migrated paths, the swap anchors (0383/0546/0547).
- **(e) Delete-as-a-function.** Today's row deletion splices and shifts every downstream station
  — the same bug class. Delete = detach from the graph (settle everything downstream at its
  current world pose), optionally re-parent.

## Rules carried from the scars

1. World targets are computed BEFORE any bookkeeping (0456), from geometry measured on the live
   scene, never assumed.
2. Never book in a station-neutral row; never book where a normaliser will erase it (0581).
3. Books legal at exit or refuse-with-numbers at entry — never a partial write (0572/0580).
4. The table is a VIEW. Any settle that moves rows must leave the sync marker; a wholesale
   `_read_rows_from_table()` on a stale table reverts the model (the stale-table clobber, filed
   in bugs/0580).
5. Every migrated writer keeps its refusal strings — honesty is part of the contract, not UX
   polish (0566/0572/0577).
6. Validate by REPLAYING the user's recordings, not synthetic scenes (feedback: fixes must be
   general; the recorder's command payloads make every flag a fixture).
```
