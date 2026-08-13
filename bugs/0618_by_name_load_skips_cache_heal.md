# 0618 — Loading by name skips the derived-cache heal; coating guard hid it (FIXED)

Surfaced by the 2026-08-13 baseline re-cut: phase 172 (promoted-solid per-face coating)
flipped PASS→FAIL with no code change that could explain it — the A/B (yesterday's full
`KrakenOS/` tree in today's environment) failed identically.

## The chain, measured

1. `attachment/penta.py` (saved in May) stores its four promoted prisms'
   `Solid_3d_stl` as ABSOLUTE legacy `~/.cache/krakenos/...` paths whose files do not
   exist anywhere on this machine; the source STEPs (attachment/prisms/*) all exist.
2. The bugs/0021 heal — regenerate a missing derived STL from its source STEP at load —
   runs ONLY in `open_layout` (File→Open). `load_layout_by_name` (Common Layout /
   Machine Vision menus, guards, headless probes) never healed: the bugs/0563
   two-loader trap, hit again. The system build then silently neutralises the dangling
   STL (`Solid_3d_stl='None'`) and substitutes the analytic single-face fallback — no
   `is_stl_solid` branch, no per-face coating chain, coating dead.
3. Guard 172's C-check compounded it: built rows from the RAW file parse (even below
   the by-name loader) and, when the trace produced NO energy data, SKIPPED — reading
   as PASS. Its historical "passes" never verified coating on this machine; whether C
   evaluated at all depended on whether the analytic fallback produced hits — which
   shifted with cache-stamp state (Filen re-touched two prism STEP mtimes on Jul 29,
   invalidating the analytic cache stamps) and the reboot.

## Fixes

- `load_layout_by_name` now runs `_regenerate_missing_optical_solid_caches()` exactly
  as `open_layout` does (placed with the 0563-precedent heals).
- Guard 172 builds its rows through a REAL editor load (healed path) and its
  no-energy branch is now a loud FAILURE, never a skip-as-pass.

Verified: penta's four prisms regenerate from their STEPs and trace as real solids —
bare RP max 0.042 → coated 0.960 (the 94% preset table). Phases 89/92/172/333 green.

## Lessons

- The two-loader trap (0563) generalises: ANY load-time heal must live in the seam
  BOTH loaders share, or be called from both — grep for the sibling loader when adding
  one.
- A guard that SKIPs on missing data reads as PASS in every report. Skip is only
  honest for missing OPTIONAL fixtures; missing *data the check exists to measure* is
  a failure.
