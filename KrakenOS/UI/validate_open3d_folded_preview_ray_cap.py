"""Guard: sparse 3D-preview ray fan on expensive folded/prism scenes (bugs/0410).

A folded RA-mirror scene traces the REAL system through the BK7 fold prisms (~10 ms/ray), so a
full-density 3D preview is ~30 s (flag_20260722_155930 "with Ray On, really long ray tracing time").
The fix caps the SHOWN 3D preview ray count on this expensive path -- a TRANSIENT override set only
around ``_trace_preview_rays_folded_aware``'s preview trace and cleared in its ``finally``, so ONLY the
preview is sparse. The analysis modes (spot / heatmap / MTF) sample through their OWN paths at other
times, so they keep the user's full ray density.

Display-free: pure-logic on the cap + ``_current_ray_count`` override, plus getsource wiring/ordering.

Checks
------
* CAP-LOGIC  -- ``_folded_preview_ray_count_cap`` CAPS a high user count (to 15) and NEVER raises a low
  one (8 stays 8).
* OVERRIDE   -- ``_current_ray_count`` honours ``_folded_preview_ray_count_override``, while an active
  promote/drag override still takes precedence.
* TRANSIENT  -- ``_trace_preview_rays_folded_aware`` sets the override then POPS it in a ``finally`` (so
  it never leaks into the analysis modes), and only on the folded path (``folded_trace_rows`` present).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_folded_preview_ray_cap

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect

from KrakenOS.UI.services.three_d_scene_tools import ThreeDSceneToolsMixin
from KrakenOS.UI.services.trace_preview_sampling import TracePreviewSamplingMixin


class _Var:
    def __init__(self, n):
        self._n = n

    def get(self):
        return self._n


class _Stub:
    _current_ray_count = TracePreviewSamplingMixin._current_ray_count
    _folded_preview_ray_count_cap = ThreeDSceneToolsMixin._folded_preview_ray_count_cap

    def __init__(self, ray_count):
        self.ray_count_var = _Var(ray_count)


def _check_cap_logic(failures, notes):
    if _Stub(45)._folded_preview_ray_count_cap() != 10:
        failures.append("CAP-LOGIC: a high user ray count must cap to the sparse preview count (10, ~9s)")
    if _Stub(8)._folded_preview_ray_count_cap() != 8:
        failures.append("CAP-LOGIC: a low user ray count must NOT be raised (cap only lowers)")
    if _Stub(45)._current_ray_count() != 45:
        failures.append("CAP-LOGIC: the cap must read the user count (not mutate the panel)")
    if not [f for f in failures if f.startswith("CAP-LOGIC")]:
        notes.append("cap-logic = caps a high count to the sparse fan; never raises a low one")


def _check_override(failures, notes):
    s = _Stub(45)
    s.__dict__["_folded_preview_ray_count_override"] = 15
    if s._current_ray_count() != 15:
        failures.append("OVERRIDE: _current_ray_count must honour _folded_preview_ray_count_override")
    # promote/drag overrides must still win (interaction sparse fan is more urgent)
    s.__dict__["_drag_preview_ray_count_override"] = 5
    if s._current_ray_count() != 5:
        failures.append("OVERRIDE: a drag/promote override must take precedence over the folded cap")
    if not [f for f in failures if f.startswith("OVERRIDE")]:
        notes.append("override = _current_ray_count honours the folded cap; drag/promote precedence kept")


def _check_transient(failures, notes):
    src = inspect.getsource(ThreeDSceneToolsMixin._trace_preview_rays_folded_aware)
    set_at = src.find("_folded_preview_ray_count_override =")
    fin = src.find("finally")
    pop_at = src.find('pop("_folded_preview_ray_count_override"')
    if set_at < 0:
        failures.append("TRANSIENT: the folded trace never sets _folded_preview_ray_count_override")
    # the override must be POPPED in the finally (so it never leaks into the analysis modes)
    if pop_at < 0 or fin < 0 or not (fin < pop_at):
        failures.append("TRANSIENT: the override must be popped in a finally (else it leaks -> analysis density drops)")
    # only the folded path (folded_trace_rows present) is capped -- the non-folded early return isn't
    if "folded_trace_rows is None" not in src or not (0 <= src.find("folded_trace_rows is None") < set_at):
        failures.append("TRANSIENT: the cap must be on the folded path only (after the non-folded early return)")
    if not [f for f in failures if f.startswith("TRANSIENT")]:
        notes.append("transient = override set on the folded path + popped in finally (analysis unaffected)")


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    for check in (_check_cap_logic, _check_override, _check_transient):
        try:
            check(failures, notes)
        except Exception as exc:
            failures.append(f"{check.__name__}: raised {type(exc).__name__}: {exc}")
    info = [n if "=" in n else n.replace(":", " =", 1) for n in notes]
    return (not failures), (failures + info)


def run() -> int:
    passed, notes = run_checks()
    print("=== validate_open3d_folded_preview_ray_cap (bugs/0410) ===")
    for note in notes:
        print(f"  {'ok ' if '=' in note else 'XX '} {note}")
    if not passed:
        n = len([x for x in notes if "=" not in x])
        print(f"\n{n} failure(s).")
        return 1
    print("\nAll folded-preview ray-cap checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
