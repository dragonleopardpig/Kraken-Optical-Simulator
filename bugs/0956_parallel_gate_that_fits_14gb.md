# 0956 -- a parallel gate that fits a 14 GB machine

User request, 2026-10-04, watching a gate run: "try to use more CPU threads."

## Why the existing tools used one core

- `tools/penta_validator_gate.py` runs every phase in one process: one core of fourteen.
- `tools/penta_shard_gate.py` runs a few big shards side by side, and budgets **7 GB per shard**:
  the size one long-lived validator process grows to. On M90aPro (14 GB, no swap, about 10 GB free)
  that budget allows one shard, so the sharded gate could not run in parallel there at all.
- The full gate therefore ran as seven sequential chunks: 1 h 54 min.

## The tool: `tools/penta_parallel_gate.py`

Many small contiguous groups instead of a few big shards. A group's validator process is young
when it ends, so it stays small, and several fit side by side.

- **Groups by band.** 60 phases per group where phases take about 3 s; 9, 8 or 4 per group in the
  slow bands (the solves around 448-474, the Qt shell guards).
- **Each group is one `penta_validator_gate.py --phases a-b` run** with its own display (passed
  explicitly: two gates starting together could otherwise pick the same one), its own `TMPDIR`
  (the gate's log and the validators' scratch files do not collide) and its own cores.
- **Memory decides, not a budget guessed in advance.**
  - Admission: a group starts only while `MemAvailable` is above `--start-gb` (5.5).
  - Watchdog: under `--min-gb` (2.5), the group started last is killed and queued again; it comes
    back when there is clear room. A group killed while it was the only one running is reported
    as a problem instead of being started again forever.
- **It never writes the baseline.** A phase that needs recording is re-run through the single
  gate with `--update-baseline`.
- Two cores are left for the desktop by default; every group runs at `nice 15`.

```
python tools/penta_parallel_gate.py --jobs 4          # inside `devenv shell`
python tools/penta_parallel_gate.py --phases 633-727
python tools/penta_parallel_gate.py --dry-run
```

## Measured (2026-10-04, M90aPro, at c45e41f6)

| | Sequential (7 chunks) | Parallel, 4 at a time |
|---|---|---|
| Wall time, full suite | 1 h 54 min | 44.5 min |
| Result | 724 of 724 | 726 of 726 |
| Load average | about 1.5 | about 10 |
| Lowest free memory | 2.9 GB | 1.9 GB |

- **The watchdog fired once, for a reason outside the gate.** Another program on the machine (a
  3.4 GB test run from a different project) started mid-gate. Free memory fell to 1.9 GB; the
  newest group was killed and re-run, and passed.
- **Four groups were the long pole** of that first run: 448-474 (1409 s as one group of 27),
  689-696 (1077 s), 705-712 (835 s), 721-727 (746 s). The bands were tightened afterwards (9 per
  group from 421, 4 per group from 689), so the next run should be shorter. That has not been
  measured on the full suite yet.

## Checked

- The first full run: 25 groups, every group reported, 726 pass, 0 fail.
- After the tuning: a real run of 114 phases in 3 groups (3.3 min, all pass), and a run with the
  watchdog forced (`--min-gb 999`): it ends with "NOT OK", exit 1, instead of looping.
