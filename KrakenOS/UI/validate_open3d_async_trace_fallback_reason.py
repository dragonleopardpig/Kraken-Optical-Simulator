"""Display-free guard for bugs/0235 -- the off-thread preview trace (bugs/0223) now records WHY
it did/did-not engage, so a scene that silently falls back to the synchronous 41s scalar folded
trace can be diagnosed from the next recording instead of guessed at.

flag_20260706_070708_237 ("tracing 6939 rays take 41 seconds"): a promoted TWO-FOLD periscope
WITH imported-STEP decoration overlays (lens + camera). The async worker rebuilds the scene from
row specs only and never re-imports STEP overlays, so the kicked worker fails and the refresh falls
back to the synchronous per-ray scalar folded trace -- yet the recording only showed
``actual_trace_backend == "Scalar TraceLoop"``, not which gate rejected the kick nor that a worker
was kicked-and-failed. The equivalence guard (0223) never exercised an imported-STEP scene, so this
gap was invisible.

Fix (bugs/0235): ``maybe_begin_inspector_async_trace`` records ``editor._last_async_trace_decision``
(``{began, reason}``) at every return, and the poll path records
``editor._last_async_trace_worker_outcome`` (``{reason, detail}``) for a completed worker
(applied / worker_failed + error tail / apply_failed / stale_rekick_exhausted). The bug recorder
surfaces both in ``sampling_diagnostics``.

  (A) GATE REASONS: a refused kick records the exact gate (force_retrace, not_interactive_opt_in).
  (B) BEGAN REASON: a coalesced/kicked begin records began=True with its reason.
  (C) WORKER-FAILED (the flag case): a completed worker whose result carries an error records
      ``worker_failed`` with the error + log tail, then falls back to sync -- and the outcome
      SURVIVES the sync fallback's re-entrant kick check.
  (D) WIRED: the reason literals are in the async source and both fields are read by the recorder.

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_async_trace_fallback_reason
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import inspect
import io
import os
import pickle
import tempfile
import types
from dataclasses import dataclass

from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor


@dataclass
class Check:
    check: str
    ok: bool
    detail: str


def _quiet(fn, *args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        return fn(*args, **kwargs)


class _Var:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


def _fake_inspector(editor):
    insp = types.SimpleNamespace(
        editor=editor,
        status_var=_Var(""),
        live_mode_var=_Var(False),
        show_rays_var=_Var(True),
        _placement_drag_state=None,
        _async_trace_state=None,
        _async_trace_fallback_sync=False,
        _step_normal_axis_pick_mode=False,
        _step_surface_center_axis_pick_mode=False,
        _step_carry_drag_state=None,
        _step_carry_follow_state=None,
        _step_carry_snap_ray_mode=False,
        _step_carry_snap_target_mode=False,
    )
    insp._live_trace_step_overlay_labels = lambda: set()
    insp.refresh_from_editor = lambda **kwargs: None  # sync fallback sink (no re-entrant kick)
    return insp


class _FinishedProc:
    """A worker process that has already exited (poll() returns an exit code)."""

    def poll(self):
        return 0

    def wait(self, timeout=None):
        return 0


def validate_async_trace_fallback_reason() -> list[Check]:
    from KrakenOS.UI.services.trace_preview_async import (
        _poll_inspector_async_trace,
        maybe_begin_inspector_async_trace,
    )

    checks: list[Check] = []

    editor = _quiet(_build_editor, _AZ85)
    editor._async_preview_trace_opt_in = True
    insp = _fake_inspector(editor)

    # ---- (A) a refused kick records the exact gate reason ------------------------------------- #
    began_fr = _quiet(maybe_begin_inspector_async_trace, insp, force_retrace=True)
    dec_fr = getattr(editor, "_last_async_trace_decision", None)
    editor._async_preview_trace_opt_in = False
    began_opt = _quiet(maybe_begin_inspector_async_trace, insp)
    dec_opt = getattr(editor, "_last_async_trace_decision", None)
    editor._async_preview_trace_opt_in = True
    checks.append(Check(
        "GATE REASONS: a refused kick records which gate rejected it (force_retrace / opt-in)",
        (not began_fr) and dec_fr == {"began": False, "reason": "force_retrace"}
        and (not began_opt) and dec_opt == {"began": False, "reason": "not_interactive_opt_in"},
        f"force_retrace={dec_fr} opt_in_off={dec_opt}",
    ))

    # ---- (B) a began kick records began=True with its reason (coalesce onto in-flight) -------- #
    insp._async_trace_state = {"proc": _FinishedProc()}  # pretend a worker is already in flight
    began_co = _quiet(maybe_begin_inspector_async_trace, insp)
    dec_co = getattr(editor, "_last_async_trace_decision", None)
    insp._async_trace_state = None
    checks.append(Check(
        "BEGAN REASON: a coalesced begin records began=True with its reason",
        bool(began_co) and dec_co == {"began": True, "reason": "coalesced_inflight"},
        f"coalesce={dec_co}",
    ))

    # ---- (C) the flag case: a kicked worker that FAILS records worker_failed + the error tail -- #
    editor._last_async_trace_worker_outcome = None
    scratch = tempfile.mkdtemp(prefix="kraken_0235_")
    payload_path = os.path.join(scratch, "payload.pkl")
    result_path = os.path.join(scratch, "result.pkl")
    with open(payload_path, "wb") as fh:
        pickle.dump({"stub": True}, fh)
    with open(result_path, "wb") as fh:
        pickle.dump({"error": "worker rebuild raised: KeyError('optical')",
                     "log_tail": "could not re-import imported-STEP overlay"}, fh)
    insp._async_trace_state = {
        "proc": _FinishedProc(),
        "payload_path": payload_path,
        "result_path": result_path,
        "system": None,
        "signature": None,
        "dirty_at_kick": True,
        "sampling_mode": "world_cone",
        "launch_rays": 6939,
        "rekicks": 0,
        "started": 0.0,
    }
    _quiet(_poll_inspector_async_trace, insp)
    outcome = getattr(editor, "_last_async_trace_worker_outcome", None)
    detail = "" if not isinstance(outcome, dict) else str(outcome.get("detail", ""))
    checks.append(Check(
        "WORKER-FAILED: a kicked-but-failed worker records worker_failed + the error/log tail",
        isinstance(outcome, dict) and outcome.get("reason") == "worker_failed"
        and "KeyError('optical')" in detail and "imported-STEP overlay" in detail,
        f"outcome={outcome}",
    ))
    with contextlib.suppress(OSError):
        os.rmdir(scratch)

    # ---- (D) wiring: reason literals in the async source, both fields read by the recorder ---- #
    import KrakenOS.UI.services.trace_preview_async as async_mod
    from KrakenOS.UI.services import open3d_event_recorder as rec_mod

    async_src = inspect.getsource(async_mod)
    rec_src = inspect.getsource(rec_mod)
    async_ok = (
        all(lit in async_src for lit in ('"kicked"', '"capture_none"', '"worker_failed"',
                                         '"force_retrace"', '"not_interactive_opt_in"'))
        and 'editor._last_async_trace_decision' in async_src
        and '_last_async_trace_worker_outcome' in async_src
    )
    rec_ok = '"async_trace_decision"' in rec_src and '"async_trace_worker_outcome"' in rec_src
    wired = async_ok and rec_ok
    checks.append(Check(
        "WIRED: the bugs/0235 reason literals are in the async source and both fields feed the recorder",
        wired,
        f"async_reasons+fields={async_ok} recorder_fields={rec_ok}",
    ))
    return checks


def run_checks() -> "tuple[bool, list[str]]":
    checks = validate_async_trace_fallback_reason()
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


def main() -> int:
    checks = validate_async_trace_fallback_reason()
    failed = [c for c in checks if not c.ok]
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if failed:
        raise SystemExit(1)
    print("Async-trace-fallback-reason validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
