# 0960 -- every flag froze the app for 5-12 s: the snapshot rebuilt a refused STEP trace plan

Found while shipping bugs/0959 ("a flag takes about 5 s on om05a_folded, and it did before this
change"). Recommended next; the user's newest flag (`flag_20261005_072545_590`, "Seems correct
now.") confirms 0958 and 0959 on X299-SSD.

## Measured

On `om05a_folded` with the optical STEP overlay (`prism_assembly_chunk_armA.step`):

| | M90aPro | X299-SSD |
|---|---|---|
| one flag (`s` or Flag Bug) | ~5 s | ~12 s |
| one recorder snapshot | 8.1 s | 11.5 s |

The app is frozen for that long after the key.

## Cause

The recorder's scene snapshot -- taken by **every flag**, and by **every recorded mouse and key
event** while a recording runs -- asked the trace for the optical overlay's live pose:
`editor._live_step_overlay_trace_rows()`.

1. **That call builds the overlay's trace plan** (`_step_overlay_optical_solid_row_plan`): an STL
   inspection (4.1 s) and a STEP reconstruction (3.6 s) on M90aPro.
2. **On om05a the injection is then refused.** bugs/0725: tracing the overlay would move the seated
   optics ("row 24 'Image / Sensor' lost its traced pose"), so the scene is traced without it.
3. **A refused plan was never cached.** Only accepted plans were remembered, so the same rows built
   the same plan again on the next call.

So every snapshot paid the full plan, and so did every trace that includes the overlay: **Trace Now**
and the live preview, on every press. All of that bought two fields that come out empty when the
injection is refused.

## Change

- **A refused plan is kept**, with the reason (`injection_refused`), under the same key as an
  accepted one: the STEP file and pose plus the rows' signature. The same rows never build it
  again. A row edit builds it once more, as before. The safety check itself still runs on every
  call (0.13 s), so a refusal is never taken on trust.
- **The snapshot no longer works anything out.** `_known_live_step_overlay_trace()` returns what the
  trace already knows for the rows as they are -- the record, or the refusal -- and None when nothing
  has traced these rows with the overlay yet. It never builds a plan. The snapshot records:
  - `live_trace_known` (new): false until a trace with the overlay has run on these rows;
  - `live_trace_row_decenter_mm` and `live_trace_pose_source`, as before, when traced;
  - `live_trace_refused` (new): the reason, when refused. Before, a refusal recorded two empty
    fields and could not be told apart from "not traced".

Nothing reads these fields but a person reading a flag bundle.

## After

On om05a_folded, X299-SSD:

| | before | after |
|---|---|---|
| snapshot | 11.5 s | 0.12 s, builds nothing |
| flag | ~12 s | 0.65-0.80 s |
| trace with the overlay (Trace Now), first | 11.6 s | 12-15 s (builds the plan, once) |
| the same, every later time on the same rows | 11.6 s | 0.13 s |

## Guard: `validate_open3d_0960_snapshot_builds_no_plan` (phase 730)

In a real Qt shell on `beam_splitter_two_arm_doublets` (in git); the plan builder and the safety
check are counting stubs, so the claims need no vendor CAD.

- **C:** a refused plan is built once over three traces. Each trace returns the model's rows and no
  record. A row edit builds it again; undoing the edit builds nothing.
- **A:** an accepted plan is built once over three traces (as before).
- **S:** a snapshot builds no plan. It records `live_trace_known: False` when nothing is known, the
  reason after a refused trace, and the decenter and pose source after an accepted one.
- **F:** a flag builds no plan, from an empty cache and after a trace.
- **R:** on om05a_folded, when its vendor CAD is on the machine: the first snapshot after a load
  takes 0.10 s and builds nothing; the first trace with the overlay builds the real plan once
  (12.2 s); the second takes 0.13 s.

**Mutation-checked:**
- a refused plan not kept: C, S and R fail (R: the second trace 13.2 s);
- the snapshot asking the trace again: S, F and R fail (R: the first snapshot 11.9 s);
- the refusal marker ignored: S fails.

**Other guards run:** the 0725 pose guard, the transient-STEP guard, the Qt shell flag guard
(0959) and the flag build-stamp and discard guards pass.

## Gates (X299-SSD)

- **Full Tk gate, parallel: 727 of 729 pass** (90 min at `--jobs 6 --cores 0-13`). The two failures
  were the machine, not this change:
  - **523** missed its 50 ms bound (71.7 ms) under a load average near 30. Alone it takes 22-36 ms
    and passes three times out of three, and it passes in the re-gate.
  - **722** timed out: its every-entry driver has a fixed 900 s limit. On this CPU (i7-7820X, 8
    physical cores) the check alone takes 1122 s with this change and passes its own claim. At
    HEAD, in a clean worktree, it takes 938 s for fewer entries. Its scene has no optical STEP
    overlay, so the code changed here never runs in it.
- **Re-gate of 521-525, 721-724 and 730 with the whole machine: 9 of 10 pass**, 722 again by the
  timeout. The single gate's `--update-baseline` wrote 722 as "fail"; that was put back to "pass" by
  hand. The baseline's only other change is the new phase 730.
- **`--jobs 6 --cores 0-13` was too many groups for this machine.** CPU N and N+8 are one physical
  core, so each group had about one core. Next time: `--jobs 3`.

## Noticed: phase 722 depends on files that are not in git

On a clean checkout the table menu has 113 distinct entries and runs 98, so the check's own
`ran >= 100` bound fails. The user's checkouts carry untracked `machine_vision_*` layouts in
`common_optical_layouts/` that add menu entries (127 distinct, 112 run). The bound should count
entries that exist in git, and the 900 s limit should scale with the machine. Not changed here.

## Not changed

The FIRST trace with the overlay on om05a still builds the plan (12-15 s here) only to refuse it.
Whether it will be refused is not known before the plan exists. A cheaper test, or remembering the
refusal across sessions, would be a change of its own.
