"""bugs/0223 -- the off-thread (subprocess) preview trace.

The dense non-sequential preview trace is a pure-Python per-ray loop (~4-7 s on the AZ85
cone) that ran synchronously on the Tk main thread -- the "freeze". A Python thread cannot
help (the loop holds the GIL), so the trace runs in a WORKER PROCESS:

  main thread                                worker process
  -----------                                --------------
  capture_async_trace_payload(editor)
    -> _build_preview_system_rays_bundle
       in CAPTURE mode: sampling runs
       normally, _trace_preview_bundles
       records the exact launch arrays
       and traces NOTHING (fast)
    -> payload {row specs, settings,
       sampling mode, captured bundles}   -> run_async_trace_payload(payload)
                                               -> snapshot editor from the specs
                                               -> _build_preview_system_rays_bundle
                                                  in REPLAY mode: its sampling only
                                                  picks the dispatcher branch; the
                                                  rays actually traced are the main
                                                  thread's captured launch arrays
                                               -> full scene bundle (folded bend +
                                                  reconcile included)
  apply_async_trace_result(editor,        <- result {rays (SYSTEM detached),
    system, result)                            scene_bundle, backend, note}
    -> re-bind rays.SYSTEM, write the
       last_system/last_rays/_last_scene_
       bundle/signature state, dirty=False

Because the launch arrays are captured on the main thread, there is NO editor-replication
fidelity question (the earlier attempt to replicate sampling on a rebuilt editor produced a
33-ray fan instead of the 3249-ray cone). The worker's system is rebuilt from the same row
specs, which is deterministic (verified byte-identical across independent editors).

Transfer is a pickle file under /dev/shm (RAM-backed on Linux -- no disk I/O); the payload
is ~KBs of launch arrays, the result carries the raykeeper (SYSTEM detached -- the System
object holds an unpicklable build hook and is rebuilt/bound on the main side) plus the
finished scene bundle.

Scope (v1): scenes WITHOUT transient live STEP overlays (include_live_step_overlays=False;
a live carry preview keeps the synchronous trace) and a single traced system per refresh
(a multi-arm per-branch splitter capture returns None -> caller falls back to sync).

Worker entry:
    .devenv/state/venv/bin/python -m KrakenOS.UI.services.trace_preview_async payload.pkl result.pkl
"""
from __future__ import annotations

import contextlib
import io
import os
import pickle
import sys
import tempfile
import traceback
from typing import Any


def shm_scratch_dir() -> str:
    """A RAM-backed directory for the payload/result hand-off when available."""
    shm = "/dev/shm"
    if os.path.isdir(shm) and os.access(shm, os.W_OK):
        return shm
    return tempfile.gettempdir()


def capture_async_trace_payload(
    editor: Any,
    *,
    settings: dict,
    sampling_mode: str | None = None,
) -> "tuple[dict | None, Any]":
    """Main-thread phase A: run the preview pipeline in CAPTURE mode.

    Returns ``(payload, system)`` -- the worker payload plus the main-side system (kept for
    ``apply_async_trace_result``), or ``(None, system)`` when this scene cannot go async
    (nothing captured, several distinct traced systems, or an unpicklable payload) and the
    caller must fall back to the synchronous trace.
    """
    editor._preview_trace_bundle_capture = []
    try:
        system, _empty_rays, _none = editor._build_preview_system_rays_bundle(
            sampling_mode=sampling_mode,
            update_state=False,
            include_live_step_overlays=False,
        )
        capture = list(editor._preview_trace_bundle_capture or [])
    finally:
        # NEVER leak the capture flag -- a leaked list would silently swallow every
        # future synchronous trace.
        editor._preview_trace_bundle_capture = None
    if not capture:
        return None, system
    if len({entry.get("system_id") for entry in capture}) > 1:
        # Per-branch (multi-arm splitter) captures trace several systems; replaying them
        # onto the worker's single dispatcher route would mis-pair bundles and systems.
        return None, system
    resolved_mode = str(
        getattr(editor, "_active_preview_sampling_mode", None) or sampling_mode or ""
    ) or None
    payload = {
        "specs": [dict(spec) for spec in editor._serializable_specs_for_rows(editor.rows)],
        "settings": dict(settings or {}),
        "sampling_mode": resolved_mode,
        "capture": [
            {"bundles": entry["bundles"], "bundle_sources": entry.get("bundle_sources")}
            for entry in capture
        ],
        "total_launch_rays": int(
            sum(
                int(len(bundle[0]))
                for entry in capture
                for bundle in entry["bundles"]
            )
        ),
    }
    try:
        pickle.dumps(payload, protocol=pickle.HIGHEST_PROTOCOL)
    except Exception:
        return None, system
    return payload, system


def run_async_trace_payload(payload: dict) -> dict:
    """Worker phase B: rebuild the scene, REPLAY the captured launch arrays, trace, and
    assemble the full scene bundle. Runs in the worker process (or in-process for tests)."""
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.render_layout_snapshot import _snapshot_editor

    log = io.StringIO()
    with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        rows = [
            KrakenLayoutEditor._row_from_layout_item(dict(spec))
            for spec in payload.get("specs", [])
        ]
        editor = _snapshot_editor(rows, dict(payload.get("settings") or {}))
        try:
            editor._normalize_special_rows()
        except Exception:
            pass
        editor._preview_trace_bundle_replay = [dict(call) for call in payload.get("capture", [])]
        try:
            system, rays, scene_bundle = editor._build_preview_system_rays_bundle(
                sampling_mode=payload.get("sampling_mode"),
                update_state=True,
                include_live_step_overlays=False,
            )
            leftover = list(editor._preview_trace_bundle_replay or [])
        finally:
            editor._preview_trace_bundle_replay = None
        # Leftover captured calls are EXPECTED, not an error: under capture nothing is
        # traced, so the main-thread dispatcher cascades through its 0-ray fallback
        # branches and records every one of them. The worker (tracing real rays) stops at
        # the first branch that yields rays -- consuming exactly the prefix a synchronous
        # run would have traced. Only an UNDERRUN (worker wants more calls than captured,
        # raised inside _trace_preview_bundles) is a genuine mismatch.
    # The System object carries an unpicklable local build hook; the main side re-binds its
    # own (identical, spec-built) system before any consumer touches rays.SYSTEM.
    rays.SYSTEM = None
    return {
        "rays": rays,
        "scene_bundle": scene_bundle,
        "backend": str(getattr(editor, "_last_preview_trace_backend", "") or ""),
        "note": str(getattr(editor, "_last_preview_trace_note", "") or ""),
        "folded_sequential": bool(getattr(editor, "_last_preview_folded_sequential", False)),
        "ray_path_count": int(len(getattr(rays, "CC", []) or [])),
        "unconsumed_capture_calls": len(leftover),
        "sampling_mode": payload.get("sampling_mode"),
        "log_tail": log.getvalue()[-2000:],
    }


def apply_async_trace_result(editor: Any, system: Any, result: dict) -> tuple[Any, Any, Any]:
    """Main-thread phase C: bind the worker result onto the live editor.

    Mirrors the ``update_state`` block of ``_build_preview_system_rays_bundle`` so every
    downstream consumer (scene refresh, signature cache, 2D analysis) sees exactly the
    state a synchronous trace would have written. Returns ``(system, rays, scene_bundle)``.
    """
    rays = result["rays"]
    scene_bundle = result["scene_bundle"]
    rays.SYSTEM = system
    editor._last_preview_trace_backend = str(result.get("backend", "") or "")
    editor._last_preview_trace_note = str(result.get("note", "") or "")
    editor._last_preview_folded_sequential = bool(result.get("folded_sequential", False))
    editor.last_system = system
    editor.last_rays = rays
    editor._last_preview_trace_signature = editor._preview_trace_signature()
    editor._last_scene_bundle = scene_bundle
    editor._last_scene_trace_sampling_mode = result.get("sampling_mode") or getattr(
        editor, "_active_preview_sampling_mode", None
    )
    editor._preview_scene_trace_dirty = False
    return system, rays, scene_bundle


# ---------------------------------------------------------------------------
# Inspector orchestration (main thread only; completion via tk after() polling)

_ASYNC_PREVIEW_TRACE_ENABLED = True  # kill switch (repo precedent: _INPATH_AXIAL_PLACEMENT_ENABLED)
_ASYNC_POLL_MS = 250


def _project_root() -> str:
    import pathlib

    return str(pathlib.Path(__file__).resolve().parents[3])


def _set_async_status(inspector: Any, text: str) -> None:
    """bugs/0598: the tracing badge used to OVERWRITE the status, so a solve's outcome --
    "mirror -> sensor 30 mm ..." or, worse, a refusal -- was clobbered by "Tracing 999 rays
    in the background..." before the user could read it (measured: both status bars read the
    badge right after a 55x55 solve with a section constraint; the user filed "the constraint
    is not working" with no way to see what the solve had actually said). A recent important
    message (a solve/split outcome, stashed by the FOV apply path) rides IN FRONT of the badge
    and survives its churn."""
    import time

    sticky = ""
    try:
        record = getattr(inspector.editor, "_sticky_status_message", None)
        if isinstance(record, dict):
            age = time.perf_counter() - float(record.get("time", 0.0))
            if age < 120.0:
                sticky = str(record.get("text", "") or "")
            else:
                inspector.editor._sticky_status_message = None
    except Exception:
        sticky = ""
    display = f"{sticky}  |  {text}" if sticky else text
    for var in (getattr(inspector, "status_var", None), getattr(inspector.editor, "status_var", None)):
        try:
            var.set(display)
        except Exception:
            pass


def _record_async_decision(inspector: Any, editor: Any, *, began: bool, reason: str) -> bool:
    """bugs/0235: record WHY the last refresh did/did-not KICK a background worker."""
    decision = {"began": bool(began), "reason": str(reason)}
    with contextlib.suppress(Exception):
        inspector._async_trace_last_decision = decision
    if editor is not None:
        with contextlib.suppress(Exception):
            editor._last_async_trace_decision = decision
    return began


def _record_async_worker_outcome(inspector: Any, editor: Any, *, reason: str, detail: str = "") -> None:
    """bugs/0235: record the completed worker's OUTCOME (applied / failed / stale). A kicked
    worker that then fails to rebuild the scene (e.g. an imported-STEP periscope the worker
    cannot re-import) falls back to the synchronous 41s trace -- so ``_last_async_trace_decision``
    reads ``kicked`` while the recording shows the sync backend. This field reveals the failure
    (and its error tail) so the next flag_* recording pins it. Survives the sync-fallback's
    re-entrant kick check, which only rewrites ``_last_async_trace_decision``."""
    outcome = {"reason": str(reason)}
    if detail:
        outcome["detail"] = str(detail)[-800:]
    with contextlib.suppress(Exception):
        inspector._async_trace_last_worker_outcome = outcome
    if editor is not None:
        with contextlib.suppress(Exception):
            editor._last_async_trace_worker_outcome = outcome


def maybe_begin_inspector_async_trace(
    inspector: Any,
    *,
    sampling_mode: str | None = None,
    force_retrace: bool = False,
    _rekicks: int = 0,
) -> bool:
    """Start a background (subprocess) trace for the inspector's next refresh.

    Returns True when the refresh will arrive asynchronously (the caller must NOT run the
    synchronous build) and False when the caller should fall through to the synchronous
    path. Conservative eligibility -- any doubt means False:

    - explicit force_retrace flows expect synchronous completion;
    - a placement drag uses the rays-only live path;
    - transient live STEP overlays (carry preview) keep the synchronous trace (their
      editor state is not row-backed, so the worker cannot rebuild them);
    - a plain scene without promoted STEP solids reuses the signature cache cheaply, so
      async buys nothing;
    - a capture that yields no payload (nothing captured / multi-system / unpicklable)
      falls back to sync.

    A request arriving while a worker is already in flight simply coalesces: the running
    trace's completion applies if the scene is unchanged, or re-kicks a fresh capture if
    the trace signature moved -- either way the new request is satisfied.
    """
    import time

    editor = getattr(inspector, "editor", None)

    def _record(began: bool, reason: str) -> bool:
        # bugs/0235: leave a breadcrumb for WHY async did/did-not engage. The flag scene
        # (a promoted two-fold periscope WITH imported-STEP decoration overlays) falls back
        # to the synchronous 41s scalar folded trace, but the recording only showed the
        # sync backend -- not which gate here rejected it. Record the decision so the next
        # flag_* recording's sampling_diagnostics pins the exact reason.
        return _record_async_decision(inspector, editor, began=began, reason=reason)

    if not _ASYNC_PREVIEW_TRACE_ENABLED:
        return _record(False, "kill_switch_off")
    if editor is None:
        return _record(False, "no_editor")
    # Interactive app only: the poll runs on the Tk mainloop. Headless editors (guards,
    # snapshot scripts) would kick a worker whose completion never fires -> keep sync.
    if not getattr(editor, "_async_preview_trace_opt_in", False):
        return _record(False, "not_interactive_opt_in")
    if getattr(inspector, "_async_trace_fallback_sync", False):
        return _record(False, "fallback_latched")
    if force_retrace:
        return _record(False, "force_retrace")
    # bugs/0400: Show Rays OFF (and no live physics) -> don't kick the expensive background
    # trace nobody is looking at. Fall to the SYNC refresh, which builds the bodies only
    # (trace_rays=False). Turning Show Rays on retraces via _on_show_rays_changed.
    try:
        service = editor._open3d_trace_refresh_service()
        rays_wanted = service.inspector_physics_requested(inspector) or bool(inspector.show_rays_var.get())
    except Exception:
        rays_wanted = True  # unknown ray state -> trace (safe default)
    if not rays_wanted:
        return _record(False, "rays_off_bodies_only")
    if getattr(inspector, "_placement_drag_state", None) is not None:
        return _record(False, "placement_drag")
    if getattr(inspector, "_async_trace_state", None) is not None:
        return _record(True, "coalesced_inflight")  # coalesce onto the in-flight worker
    try:
        service = editor._open3d_trace_refresh_service()
        if service.inspector_should_trace_step_overlays(inspector, force_retrace=False):
            return _record(False, "traceable_step_overlay")
        if not service.has_promoted_step_optical_solid_rows():
            return _record(False, "no_promoted_step_rows")
        settings = editor._layout_settings_service()._collect_layout_settings()
    except Exception:
        return _record(False, "settings_error")
    try:
        payload, system = capture_async_trace_payload(
            editor, settings=dict(settings or {}), sampling_mode=sampling_mode
        )
    except Exception:
        editor._preview_trace_bundle_capture = None
        return _record(False, "capture_error")
    if payload is None:
        return _record(False, "capture_none")
    import subprocess

    scratch = shm_scratch_dir()
    tag = f"kraken_async_trace_{os.getpid()}"
    payload_path = os.path.join(scratch, f"{tag}_payload.pkl")
    result_path = os.path.join(scratch, f"{tag}_result.pkl")
    try:
        with open(payload_path, "wb") as handle:
            pickle.dump(payload, handle, protocol=pickle.HIGHEST_PROTOCOL)
        with contextlib.suppress(OSError):
            os.remove(result_path)
        proc = subprocess.Popen(
            [sys.executable, "-m", "KrakenOS.UI.services.trace_preview_async",
             payload_path, result_path],
            cwd=_project_root(),
            # DEVNULL, not PIPE: nobody drains the pipes while polling, so a chatty
            # import (pyvista/OCC banners) would fill the 64KB buffer and DEADLOCK the
            # child. Diagnostics travel via the result file (error + log_tail fields).
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except Exception:
        with contextlib.suppress(OSError):
            os.remove(payload_path)
        return _record(False, "spawn_failed")
    inspector._async_trace_state = {
        "proc": proc,
        "payload_path": payload_path,
        "result_path": result_path,
        "system": system,
        "signature": editor._preview_trace_signature(),
        # The dirty flag is usually ALREADY True at kick time -- an invalidation is why
        # we are retracing at all -- and it stays True until a trace result is applied.
        # Staleness therefore means "the scene changed SINCE the capture": the signature
        # moved, or a NEW invalidation arrived mid-flight (dirty flipped False->True).
        "dirty_at_kick": bool(getattr(editor, "_preview_scene_trace_dirty", False)),
        "sampling_mode": payload.get("sampling_mode"),
        "launch_rays": int(payload.get("total_launch_rays", 0)),
        "rekicks": int(_rekicks),
        "started": time.perf_counter(),
    }
    _set_async_status(
        inspector, f"Tracing {int(payload.get('total_launch_rays', 0))} rays in the background..."
    )
    _schedule_async_poll(inspector)
    return _record(True, "kicked")


def _schedule_async_poll(inspector: Any) -> None:
    try:
        inspector.editor.after(_ASYNC_POLL_MS, lambda: _poll_inspector_async_trace(inspector))
        return
    except Exception:
        pass
    # Headless (no Tk mainloop, e.g. the equivalence guard): block until the worker
    # finishes, then complete inline -- deterministic instead of a poll recursion.
    state = getattr(inspector, "_async_trace_state", None)
    if state is not None:
        with contextlib.suppress(Exception):
            state["proc"].wait(timeout=600)
    _poll_inspector_async_trace(inspector)


def _fallback_sync_refresh(inspector: Any, state: dict) -> None:
    """Worker failed: run the ordinary synchronous refresh once (async disabled for it)."""
    inspector._async_trace_fallback_sync = True
    try:
        inspector.refresh_from_editor(sampling_mode=state.get("sampling_mode"))
    except Exception:
        pass
    finally:
        inspector._async_trace_fallback_sync = False


def _poll_inspector_async_trace(inspector: Any) -> None:
    import time

    state = getattr(inspector, "_async_trace_state", None)
    if state is None:
        return
    proc = state["proc"]
    if proc.poll() is None:
        elapsed = time.perf_counter() - state["started"]
        _set_async_status(
            inspector,
            f"Tracing {state['launch_rays']} rays in the background ({elapsed:.0f}s)...",
        )
        _schedule_async_poll(inspector)
        return
    inspector._async_trace_state = None
    editor = inspector.editor
    try:
        with open(state["result_path"], "rb") as handle:
            result = pickle.load(handle)
    except Exception as exc:
        result = {"error": f"worker result unreadable: {exc!r}"}
    for path in (state["payload_path"], state["result_path"]):
        with contextlib.suppress(OSError):
            os.remove(path)
    if result.get("error"):
        detail = str(result["error"])
        tail = str(result.get("log_tail", "") or "")
        if tail:
            detail = f"{detail} | log: {tail}"
        try:
            editor.append_debug("async trace worker failed: " + detail[-800:])
        except Exception:
            pass
        _record_async_worker_outcome(inspector, editor, reason="worker_failed", detail=detail)
        _fallback_sync_refresh(inspector, state)
        return
    # Discard a result whose scene changed SINCE the capture: the trace signature moved,
    # or a NEW invalidation arrived mid-flight (dirty flipped False -> True; dirty that
    # was already set at kick time is simply why we were retracing -- it clears when the
    # result applies, exactly like the synchronous update_state block). Re-kick a fresh
    # capture, but BOUNDED: after 2 re-kicks fall back to one synchronous refresh so a
    # pathological signature can never spawn workers forever.
    try:
        from KrakenOS.UI.layout_plot_controller import preview_trace_signature_matches

        newly_dirty = bool(getattr(editor, "_preview_scene_trace_dirty", False)) and not bool(
            state.get("dirty_at_kick", False)
        )
        stale = newly_dirty or not preview_trace_signature_matches(
            state["signature"], editor._preview_trace_signature()
        )
    except Exception:
        stale = True
    if stale:
        rekicks = int(state.get("rekicks", 0))
        if rekicks >= 2 or not maybe_begin_inspector_async_trace(
            inspector, sampling_mode=state.get("sampling_mode"), _rekicks=rekicks + 1
        ):
            _record_async_worker_outcome(
                inspector, editor, reason="stale_rekick_exhausted", detail=f"rekicks={rekicks}"
            )
            _fallback_sync_refresh(inspector, state)
        return
    try:
        import time as _time

        system, rays, scene_bundle = apply_async_trace_result(editor, state["system"], result)
        row_names = editor._preview_render_row_names(scene_bundle)
        inspector.refresh_scene(
            system, rays, row_names, scene_bundle=scene_bundle, reset_camera=False
        )
        editor._open3d_trace_refresh_service().remember_inspector_sampling_mode(
            inspector, result.get("sampling_mode")
        )
        elapsed = _time.perf_counter() - state["started"]
        _record_async_worker_outcome(
            inspector, editor, reason="applied", detail=f"{elapsed:.1f}s"
        )
        _set_async_status(inspector, f"3D inspector updated (background trace {elapsed:.1f}s).")
    except Exception as exc:
        try:
            editor.append_debug(f"async trace apply failed: {exc!r}")
        except Exception:
            pass
        _record_async_worker_outcome(inspector, editor, reason="apply_failed", detail=repr(exc))
        _fallback_sync_refresh(inspector, state)


def main(argv: "list[str] | None" = None) -> int:
    """Subprocess entry: ``python -m ...trace_preview_async payload.pkl result.pkl``.

    Always writes a result file (``{"error": ...}`` on failure) so the parent gets a
    diagnostic instead of a silent missing file; the write is atomic (tmp + replace).
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2:
        print("usage: trace_preview_async <payload.pkl> <result.pkl>", file=sys.stderr)
        return 2
    payload_path, result_path = args
    try:
        with open(payload_path, "rb") as handle:
            payload = pickle.load(handle)
        result = run_async_trace_payload(payload)
        status = 0
    except Exception:
        result = {"error": traceback.format_exc()[-4000:]}
        status = 1
    tmp_path = f"{result_path}.tmp"
    with open(tmp_path, "wb") as handle:
        pickle.dump(result, handle, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(tmp_path, result_path)
    return status


if __name__ == "__main__":
    raise SystemExit(main())
