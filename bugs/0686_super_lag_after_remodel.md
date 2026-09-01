# 0686 — "super lagging ... right after clicking the .py file in Open menu"

## Symptom (user, live)
After 0684, opening `om05a_folded.py` froze the app: the UI thread ran ~81% CPU
sustained, the status showed "tracing 7300 rays", every interaction stalled.
Measured headless: load 65 s, first trace 58 s.

## Root cause — three findings, one real
1. NOT the far halves' `beam_splitter` marks (my first theory): removing them left
   the counts and times identical. They were still removed — the mark routes a row
   into the branch machinery, which is semantically wrong for a passive glass body —
   and replaced by a general walk fix: a PINNED follower with only an INFERRED
   output that the running beam line MISSES no longer re-sources the frame
   (nonseq_output_ports.py; the 0224 principle extended from full mirrors to any
   free-placed glass). Physics unchanged: chain 1083/924, faceB 361/4.
2. THE REAL COST: `normalize_optical_solid_face_record` ran **1.25 MILLION times
   in one load** (64 s of 147 s profiled). The real CAD solids carry ~45–130
   analytic face records each (the old synthesized wedges had ~5), and the
   paraxial reference, coverage blocks, and source-anchor queries re-normalized
   every record of every solid on every call (9,620 `optical_solid_face_world_records`
   calls per load).
3. The same per-query recomputation also dominated the trace and every UI refresh
   (`_update_results` alone ~23 s profiled).

## Fix (general, two memo layers in optical_solid_metadata.py)
- `_normalized_face_record_cached`: per RAW face record, keyed by the record's
  identity + a fingerprint of the user-editable assignment fields (the fields the
  face dialogs write in place); structural changes re-key by id. Hits return
  shallow copies — the exact aliasing the uncached path produced, so the
  splitter-demote pass and other mutating callers can never poison the cache.
- `optical_solid_face_world_records` memo: per (row, assigned_only), fingerprinted
  by row pose (tilts/desps/station) + per-face identity/assignment fingerprint.
  Entries hold references to the row and faces list so a GC-recycled id() can
  never false-hit; the cache clears wholesale at 1024 entries.

## Measured (headless, same scene, physics byte-identical throughout)
| stage | load | first trace |
|---|---|---|
| before | 65.5 s | 57.9 s |
| + record memo | 41.3 s | 45.2 s |
| + world-records memo | **20.3 s** | **33.6 s** |

The app's interactive refreshes (paraxial readouts, browsers, coverage) hit the
same memos, so the in-app lag drops accordingly. The remaining 33 s folded trace
is the known ~10 ms/ray folded-scene cost (0410-capped preview).

## Guards
- 0672 om05a guard: 15/15 PASS after the mark removal (A3b now pins the far
  halves as PLAIN glass, no branch mark).
- Penta smoke: phases 188 (pinned second mirror), 200 (off-beam promoted mirror
  inert) — the walk-gate semantics — plus the om05a family 495–507.
