# 1001 -- the full gate covers both interfaces

Phase 7g of the Qt migration (docs/design_qt_migration.md): "both interfaces gated". Both
interfaces stay (the user's decision, 2026-10-06), so both have to be held by the gate that is
actually run.

## What was there

Two suites, each with its own baseline:

- every phase on the Tk interface -- 761 phases with this one, `tools/penta_validator_baseline.json`;
- the harness's own phases run again with the 3D inspector hosted in the Qt shell -- 352 phases,
  `tools/penta_validator_baseline_qt.json`, `penta_validator_gate.py --shell qt`.

"Run the full gate" meant `tools/penta_parallel_gate.py`, and that ran the first only. The second
had to be remembered and run by hand, one process, about 44 minutes while the Qt shell still
carried its hidden Tk application. Its baseline was last touched on 2026-10-05; it was next run on
2026-10-09, by me, for another reason. A Qt-only regression in between would have gone unseen by
every full gate.

## Change

`tools/penta_parallel_gate.py` gates both by default. The Qt-hosted suite's phases -- the ones its
own baseline records -- are cut into groups like the Tk ones, queued after them, each run through
the single gate with `--shell qt` (which also selects that suite's baseline), on a display and
cores of its own. The summary adds each interface up separately:

    [parallel] Tk: 761 pass, 0 fail of 761 phases in 47 groups
    [parallel] Qt-hosted: 352 pass, 0 fail of 352 phases in 6 groups

and is OK only when every group of both ran, reported and passed. `--shell tk` and `--shell qt`
ask for one suite; `--phases` narrows each suite to what it has of the phases named.

Since bugs/1000 the Qt shell starts without Tk, and the Qt-hosted suite takes about 17 minutes of
one process instead of 44 -- as six groups among the others it adds little to the run.

## Proof

- A real run over both interfaces, small: `--jobs 2 --phases 300-306,700` -- 15 pass (8 Tk in two
  groups, 7 Qt-hosted in one), 0.3 min. The Qt-hosted group's log says "inspector hosted in the Qt
  shell (QVTKRenderWindowInteractor, host QtUiHost)" and phase 304's Tk menu replay "not
  applicable" there, "pass" in the Tk group.
- The first full run of both is the user's to start (the gate is run on their word).

## Guard: `validate_parallel_gate_both_interfaces` (phase 762)

It holds the runner's own logic without running a phase, so it needs no display:

- **P:** asked for nothing, the plan queues every Tk phase once and every Qt-hosted phase once,
  the Tk groups first; `--shell tk` / `--shell qt` queue one suite; `300-306,700` leaves 8 Tk and
  7 Qt-hosted phases.
- **C:** a Qt-hosted group's command ends in `--shell qt`, a Tk group's has none; each group has
  its own display across both suites.
- **R:** the summary: per-interface totals; a failed Qt-hosted group, a group that did not run,
  one that did not report, one that regressed, and an empty plan are each NOT OK, the group named
  with its interface.
- **D:** the real command line: `--dry-run` prints both suites with the counts the sources give;
  `--shell tk` the Tk one alone.

Ten mutations of the runner, all caught.

## What is left of phase 7g

Both suites are run by one command; what each suite covers is another matter. The Qt-hosted suite
is the harness's 352 phases; the Qt shell's own features are held by the Qt-era phases (633 on) of
the Tk baseline, which build a Qt shell themselves. What no phase holds in the Qt shell is not
measured yet.
