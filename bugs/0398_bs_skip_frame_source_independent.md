# 0398 — the BS follower-skip must be frame-source independent (0396/0397 gated it out)

**Flag:** `flag_20260722_102908_919` — "quit Kitty, relaunch app, right click add BS plate to LED
STEP re-orientate the camera." Build 71ea555b (= 0397), **fresh relaunch** (camera actor still
jumps from `x[200,270]` onto the BS at `x[-29,41]`).

## Why 0396 AND 0397 both missed

Both prior fixes added their BS recognition (`_solid_has_beam_splitter_interaction_face`,
`_row_is_marked_beam_splitter`) INSIDE the non-folding guard:

```python
if str(frame_source).startswith("inferred_output") and ( ... or <BS check> ):
```

That guard only runs when the solid's exit resolves as **`inferred_output`**. A real promoted BS
plate's output resolves via a **different** `frame_source` (an explicit output port, or a
reflected/physics frame), so the `and` short-circuited and **neither BS check was ever reached**
— the camera folded onto the plate regardless. Both checks passed every *synthetic* test (which
happened to land on `inferred_output`) yet did nothing on the real plate. Verified: a BS with an
EXPLICIT folding output port folds the Image `[2]` and — before this fix — the mark did not stop
it.

## Fix

Skip a beam splitter as a fold source **at the TOP of the loop, BEFORE the exit frame is
computed** — so it can never re-aim the downstream imaging chain regardless of how its output
would resolve (inferred / explicit / reflected):

```python
world_faces = optical_solid_face_world_records(current, ...)
if _row_is_marked_beam_splitter(current) or _solid_has_beam_splitter_interaction_face(world_faces):
    row_index += 1
    continue      # a BS never folds followers; its reflected branch is handled separately
```

The 0396/0397 additions inside the non-folding guard are removed (subsumed). Recognition is
unchanged: an explicit BS mark (`add_beam_splitter_to_led` → `StepOverlayPromotion.beam_splitter`,
persisted through reload) OR a "Beam Splitter" interaction face (a manually-flagged coating). A
full MIRROR still folds; the BS cube's straight-through and its reflected 2nd axis are unchanged.

## Verification

- **Penta phase 26**, extended: an EXPLICIT (folding) output port repositions the Image `[2]`
  (precondition), but a BS mark on the same solid skips it `[]` — **frame-source independent**,
  the exact case 0396/0397 missed. Plus: unmarked plate folds `[2,3]`, marked plate skips `[]`,
  mark survives reload, tilted BS plate `[]`, mirror plate folds, cube `[]`, and the real MV-150
  BS-cube scene all still pass.
- **Instrumentation kept** (`bs_follower_diagnostics`, recorder): per promoted row — is it BS-
  marked, and is it a fold-override key? If the camera STILL re-aims after this, one flag names
  whether the mark is missing (add-BS not stamping it) or present-but-folded (a deeper gap).

## Files

- `KrakenOS/UI/nonseq_output_ports.py` — top-of-loop BS skip; guard reverted to non-folding only.
- `KrakenOS/UI/services/open3d_event_recorder.py` — `bs_follower_diagnostics`.
- `KrakenOS/UI/validate_open3d_beam_splitter_transmit_and_second_axis.py` — explicit-output +
  mark checks.

## In-app eyeball still owed

Can't drive `add_beam_splitter_to_led` headless (LED opening undetectable offscreen). Add a BS
plate to the LED — the camera should stay put. If not, the flag's `bs_follower_diagnostics` will
say exactly why.
