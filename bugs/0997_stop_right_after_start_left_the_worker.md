# 0997 -- Stop pressed right after Start did not stop the optimizer's worker

Found while widening the session of bugs/0993 (phase 7f of the Qt migration) to tolerances and the
optimizer. Like 0996 it is not about Tk: the Tk editor does it too.

## Symptom

Start an optimization and press Stop within the first seconds. The editor says "Optimization
stopped", but the worker process it started is still running. A few seconds later a traceback
appears on the terminal:

    File ".../multiprocessing/synchronize.py", line 115, in __setstate__
        self._semlock = _multiprocessing.SemLock._rebuild(*state)
    FileNotFoundError: [Errno 2] No such file or directory

Measured (`bugs/0997_stop_right_after_start.py`), the worker's state right after the editor shut
it down, by how long after Start the Stop came:

| Stop after | before | after |
|---|---|---|
| 0 s | ALIVE; dies later by itself, exit code 1 | stopped and reaped |
| 1 s | ALIVE; dies later by itself, exit code 1 | stopped and reaped |
| 3 s | stopped and reaped | stopped and reaped |
| 8 s | stopped and reaped | stopped and reaped |

Two tracebacks on stderr before, none after.

## Cause

`_shutdown_optimization_worker` stops the worker with `os.killpg(pid, ...)`: it signals the
worker's process GROUP, so that the pool of processes a multi-worker run starts goes with it. The
worker is a group of its own only after `os.setsid()`, which is the first line of its job -- and
its job begins seconds after the process does, once the new interpreter has started and imported
the editor. Until then there is no group with that number; `killpg` raises `ProcessLookupError`,
which was taken to mean "already gone", and nothing was killed.

The editor then let go of the queue and the stop event. When the worker finally got as far as
receiving them, they no longer existed -- that is the traceback, and that crash is what ended the
worker. It was never stopped; it failed to start.

## Fix

After signalling the group, if the process is still alive it is killed itself. Nothing else
changes: a run that is under way is still stopped by its group.

## Guard: `validate_editor_without_tk_root` (phase 759), extended

The session grew by seven steps on a plain lens (the double Gauss): a cell becomes an optimization
variable, the focal length is the operand, a tolerance Monte Carlo of three samples runs over it,
one worker is chosen, an optimization is started and stopped at once, the variable is unmarked.

- **R:** new facts -- a cell is an optimization variable and stops being one; the Monte Carlo
  gives 3 samples and 4 valid records with a worst merit; the optimization that was stopped at
  once leaves the lens as it was and says so; and **in both editors the worker is stopped and
  reaped by the time the editor has shut it down**.
- **S:** the optimization variables and the tolerance run are among what is compared after every
  step; the two editors still agree in every plain attribute, over 63 steps.

## A complete optimization, compared once

The guard does not run an optimization to its end: one takes a minute and a half.
`bugs/0997_full_optimization_both_editors.py` does, once on an editor with a hidden Tk root and
once on one without, in processes with different hash seeds: 12 generations, one worker, the
double Gauss's fourth thickness, the focal length as the merit.

Both: 94.8 s and 93.3 s, the thickness from 5.0 to 7.496737208955419, "Optimization finished:
3514.8 -> 3498.25", the same 26 progress lines, the same rows. Of 305 plain attributes compared
after the run one differs, `_spinner_phase` (864 and 851): it counts the frames of the progress
spinner's animation, which follow the clock -- not the model.

## Seen on the way, not changed

- With "Spot RMS" as the only operand the double Gauss's merit is 0 before and after ("Optimization
  finished: 0 -> 0", "Spot RMS: value=0"), and the thickness still moves, 5.0 to 6.48: on a flat
  merit the optimizer's champion is whatever its population holds. Whether a spot RMS of exactly 0
  is right for that operand's default settings, and whether a run that improves nothing should
  change the lens, is not decided here.
- On the two-arm beam-splitter scene the same operand gives the penalty value 1e+09 before and
  after, and the run takes 141 s.
