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
