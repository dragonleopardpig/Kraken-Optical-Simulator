# 0939 -- Qt phase 5h: the penta harness re-run against the inspector hosted in the Qt shell

Phase 5h in `docs/design_qt_migration.md` is "re-prove the bug arc: every penta phase that drives
the inspector, re-run against the Qt interactor". The penta harness already encodes that arc. Its
352 own phases take a shared `(app, inspector)` and cover:
- picking, hover, drag and carry;
- the gizmos, the thickness dimensions;
- the solves, the folded scenes;
- the nav cube, the menus.

The other 363 phases wrap standalone validators that build their own Tk editor, so they say
nothing about Qt.

## What was added

**`KRAKEN_PENTA_SHELL=qt`** in `validate_open3d_penta_telescope_comprehensive.py`:
- builds the real Qt shell (`qt.app.build`) and hosts the inspector in its dock
  (`build_inspector_view`);
- refuses to run unless the inspector's VTK widget IS that dock's `QVTKRenderWindowInteractor`;
- hands the phases that editor and inspector;
- skips the standalone-validator phases.

The phases pump with `app.update()` / `inspector.update()`, which are Tk calls. Under the Qt shell
the inspector's timers and repaints live on the Qt loop (its host is a `QtUiHost`), so in this mode
both also call `QApplication.processEvents()`. Otherwise a debounced refresh or a trailing re-pick
would never run.

**`tools/penta_validator_gate.py --shell qt`** runs it as a gate against its own baseline,
`tools/penta_validator_baseline_qt.json`. A PASS->FAIL flip under Qt blocks, as the Tk gate does.
It takes about 15 minutes, against about 1-2 h for the Tk suite.

## Result

**352 / 352 harness phases pass with the inspector in the Qt shell** (X299-SSD, 2026-10-01; 14 min
of phase time).

Notes from the run:
- Phases 147 / 148 (nav cube) drive the cube through its own picking, not Tk widget events, so they
  are valid under Qt. Phase 147 notes the live cube viewport rectangle differs in the Qt dock
  (0.92, 0.712 vs the module's 0.815, 0.78) because the dock's aspect differs. That is a note, not
  a failure.
- Phase 299 (popup dismissal restores render-pane focus for the `s` hotkey) checks Tk focus
  bookkeeping. Under Qt it passes but proves little; Qt focus would need its own check, which is
  phase 7 work.

What this does NOT cover: real Qt *input*. These phases call the inspector's handlers directly, as
they did under Tk. Real-input parity was proved separately for each step: 5b hover (phase 705),
5d drags (704), 5e tools (706) and the 5f / 5g dialogs (707-716).

**Commit note:** committed on the direct 352/352 run. The `--shell qt` baseline file is added when its first gate run lands.
