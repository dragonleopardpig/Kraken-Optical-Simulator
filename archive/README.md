# archive/

Scripts moved here on 2026-09-17 because **nothing uses them**: none is imported by the app, the
git pre-push gate (`tools/penta_validator_gate.py`), the penta suite or `tests/`, and none is named
anywhere in the code, the Sphinx docs, `devenv.nix` or the git hooks.

Paths mirror where each file used to live, so `archive/tools/diag_objdisc.py` was
`tools/diag_objdisc.py`. To restore one, move it back (`git mv archive/<path> <path>` for tracked
files; plain `mv` for the few that were never committed).

| came from | files |
|---|---|
| `bugs/` | 145 investigation probes and diagnostics (the 172 cited in bug docs stayed) |
| `KrakenOS/UI/` | 31 standalone validators not run by the gate, 1 build script, 1 capture script, 1 spike |
| `KrakenOS/Examples/` | 29 upstream examples not used by the app, guards or docs |
| `tools/` | 9 one-off diagnostics |
| `KrakenOS/`, `KrakenOS/AstroAtmosphere/`, `KrakenOS/Optimization/` | 4 unreferenced modules and examples |
| repo top | `GPU_test.py` |

Nothing in this folder is imported or globbed by the project, so the whole folder can be deleted
once you are sure you do not want any of it back.
