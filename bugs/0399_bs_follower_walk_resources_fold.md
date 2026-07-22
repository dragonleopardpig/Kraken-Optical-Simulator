# 0399 — an upstream mirror's follower walk RE-SOURCES the fold onto the BS

**Flag:** `flag_20260722_104808_017` — "not fixed." Build 7e53cd2d (= 0398), fresh app. The
0398 `bs_follower_diagnostics` instrumentation pinned it in one shot:

```
promoted:
  row 8 (mirror): is_marked=false, is_fold_override=true
  row 9 (BS):     is_marked=TRUE,  is_fold_override=true   <-- marked, yet the camera lands on it
```

Row 9 (the BS) **is** marked — so 0397's stamp works and 0398's top-of-loop skip sees it — yet
the camera (row 10) still folds onto the BS at `x~6`.

## Root cause (reproduced headlessly)

0398 skipped a BS only when it was a **top-level** fold source (the outer loop's `current`
row). But the real AZ85 scene has a **mirror upstream of the BS**. When the mirror is processed
as a source, its **follower walk** steps downstream through every follower, and on reaching the
BS — a promoted solid with an output face — it **RE-SOURCES the running fold onto the BS's
output face** (`nonseq_output_ports.py:1588-1599`), making the BS the new fold origin and
sweeping the camera onto it. The top-of-loop skip never runs for a row consumed inside a
follower walk.

Reproduced: `[object, MIRROR, BS, image]` → the image's fold `source_index` is the **BS** (row 2)
whether the BS is marked or not — the marker was ignored on this path.

## Fix

Skip a beam splitter as a **re-source inside the follower walk too** — analogous to the existing
free-placed full-mirror skip (bugs/0224). Right after the follower's faces are resolved:

```python
if _row_is_marked_beam_splitter(follower) or _solid_has_beam_splitter_interaction_face(follower_faces):
    follower_index += 1
    continue      # a BS never re-sources the fold; later followers keep the upstream frame
```

So a BS reached in a follower walk does not re-anchor the beam — the camera/image keep the
upstream **mirror's** frame (its correct RA-mirror leg), instead of being swept onto the BS. A
full mirror still re-sources; the cube straight-through + reflected 2nd axis are unchanged.

## Verification

- **Reproduced + fixed headlessly** (penta phase 26): `[object, MIRROR, BS, image]` — an UNMARKED
  BS re-sources the image fold onto the BS (`source_index=2`, the bug); a MARKED BS does NOT —
  the image stays folded by the MIRROR (`source_index=1`). Plus the full 0396–0398 suite and the
  real MV-150 BS-cube scene still pass.
- This is the path 0396/0397/0398 all missed; the 0398 recorder instrumentation
  (`bs_follower_diagnostics`) is what named it (marked-yet-folded).

## The four-attempt saga

0396 (coating check) + 0397 (explicit mark) — both gated inside the non-folding guard
(`inferred_output` only). 0398 — moved the skip to the top of the loop (frame-source
independent) + shipped the recorder diagnostic. 0399 — the diagnostic revealed the BS is marked
yet folded, pointing at the **follower-walk re-source** path, now skipped too.

## Files

- `KrakenOS/UI/nonseq_output_ports.py` — follower-walk BS skip.
- `KrakenOS/UI/validate_open3d_beam_splitter_transmit_and_second_axis.py` — multi-fold
  (mirror→BS→image) re-source test.

## In-app eyeball still owed

Add a BS plate to the LED — the camera should stay on the RA-mirror leg, not jump onto the BS.
If it still moves, `bs_follower_diagnostics` will show whether the BS row is a fold source again.
