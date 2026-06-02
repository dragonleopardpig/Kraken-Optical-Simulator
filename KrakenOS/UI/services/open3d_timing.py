"""Structured timing log for Open 3D responsiveness diagnostics.

Three layers, lightest-touch first:

* :func:`open3d_timing_event` / :func:`open3d_timing_span` are the
  baseline logger used everywhere. They write one JSON line per call
  to the path in :data:`OPEN3D_TIMING_LOG_PATH`.

* :func:`open3d_trace_event` / :func:`open3d_trace_span` are the
  *deep-trace* layer, gated by the ``KRAKEN_OPEN3D_TRACE`` environment
  variable. When unset (the default) they are no-ops, so callers can
  sprinkle them through hot paths (mouse-move handler, picker calls,
  Tk event hooks) without paying any cost in normal use. When set to a
  truthy value they fall through to the baseline logger and start
  emitting events into the same JSON stream.

* :func:`start_open3d_heartbeat` runs a daemon thread that writes a
  "main-thread alive" event every 250 ms regardless of what the GUI
  thread is doing. Without a heartbeat, a stall inside VTK or
  pythonocc-core looks identical to "no events for X seconds because
  nothing happened" -- the heartbeat makes hangs visible. The thread
  only touches this module's logger and never the GUI, so it is safe
  to run concurrently with Tk/VTK.

Enable both layers with ``KRAKEN_OPEN3D_TRACE=1 python -m
KrakenOS.UI.layout_editor``; tail the log with ``tail -f
~/.cache/krakenos/logs/open3d_timing_latest.jsonl``.
"""

from __future__ import annotations

from contextlib import contextmanager
import itertools
import json
import os
from pathlib import Path
import threading
import time
from typing import Iterator


OPEN3D_TIMING_LOG_PATH = Path(
    os.environ.get(
        "KRAKEN_OPEN3D_TIMING_LOG",
        str(Path.home() / ".cache" / "krakenos" / "logs" / "open3d_timing_latest.jsonl"),
    )
).expanduser()

_RUN_ID = f"{time.strftime('%Y%m%d-%H%M%S')}-{os.getpid()}"
_SEQ = itertools.count(1)


def open3d_timing_log_path() -> Path:
    return OPEN3D_TIMING_LOG_PATH


def _safe_payload(payload: dict[str, object]) -> dict[str, object]:
    try:
        json.dumps(payload, default=str)
        return payload
    except Exception:
        return {str(key): str(value) for key, value in payload.items()}


def reset_open3d_timing_log(*, reason: str = "open3d_start") -> Path:
    path = open3d_timing_log_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
    except Exception:
        return path
    open3d_timing_event("timing_log_reset", reason=reason, path=str(path))
    return path


def open3d_timing_event(event: str, **fields: object) -> None:
    payload = {
        "seq": next(_SEQ),
        "run_id": _RUN_ID,
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "perf_ms": round(time.perf_counter() * 1000.0, 3),
        "event": str(event),
        **fields,
    }
    path = open3d_timing_log_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(_safe_payload(payload), sort_keys=True, default=str) + "\n")
    except Exception:
        pass


@contextmanager
def open3d_timing_span(event: str, **fields: object) -> Iterator[None]:
    start = time.perf_counter()
    open3d_timing_event(f"{event}_start", **fields)
    status = "ok"
    try:
        yield
    except Exception as exc:
        status = "error"
        fields = {**fields, "error": f"{type(exc).__name__}: {exc}"}
        raise
    finally:
        duration_ms = (time.perf_counter() - start) * 1000.0
        open3d_timing_event(
            f"{event}_done",
            duration_ms=round(float(duration_ms), 3),
            status=status,
            **fields,
        )


# ---------------------------------------------------------------------------
# Deep-trace mode: ``KRAKEN_OPEN3D_TRACE=1`` (or "true" / "yes") flips these
# helpers from no-ops into real loggers. Callers in hot paths use these
# instead of the baseline functions so the cost of instrumenting every
# mouse-move + every picker call goes to zero unless the user is actively
# diagnosing a hang.
# ---------------------------------------------------------------------------

def _env_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


_TRACE_ENABLED = _env_truthy(os.environ.get("KRAKEN_OPEN3D_TRACE"))


def open3d_trace_enabled() -> bool:
    """Return True if deep-trace events should be emitted."""
    return _TRACE_ENABLED


def open3d_trace_event(event: str, **fields: object) -> None:
    if _TRACE_ENABLED:
        open3d_timing_event(event, trace=1, **fields)


@contextmanager
def open3d_trace_span(event: str, **fields: object) -> Iterator[None]:
    """Span variant that's a no-op unless deep-trace mode is on.

    The cheap-path branch yields immediately so call sites that wrap
    very small operations (a single VTK Pick, a status-bar update) pay
    only a function-call and a Python-level ``if`` when tracing is off.
    """
    if not _TRACE_ENABLED:
        yield
        return
    with open3d_timing_span(event, trace=1, **fields):
        yield


# ---------------------------------------------------------------------------
# Heartbeat. A daemon thread that writes a small event every 250 ms so a
# stall on the GUI thread shows up as a gap in the heartbeat stream
# (every other event is GUI-thread bound and stops with it). Picks the
# thread up by ``start_open3d_heartbeat`` and lets it run until the
# returned :class:`threading.Event` is set.
# ---------------------------------------------------------------------------


_HEARTBEAT_INTERVAL_S = 0.25


def start_open3d_heartbeat(*, interval_s: float = _HEARTBEAT_INTERVAL_S) -> threading.Event:
    """Start a heartbeat thread. Returns the stop signal.

    The heartbeat does not import psutil so it has no extra
    dependencies; we log thread count and the perf_counter timestamp,
    which is enough to spot a main-thread stall (heartbeat keeps
    ticking, everything else goes quiet) and a GIL-contention stall
    (heartbeat itself slows down because the daemon thread can't grab
    the GIL).
    """
    stop = threading.Event()

    def _beat() -> None:
        # Marker event so the post-mortem can find where the heartbeat
        # window started without having to count seq numbers.
        open3d_timing_event(
            "heartbeat_started",
            interval_s=float(interval_s),
            pid=int(os.getpid()),
        )
        while not stop.wait(float(interval_s)):
            open3d_timing_event(
                "heartbeat",
                threads=int(threading.active_count()),
            )
        open3d_timing_event("heartbeat_stopped")

    t = threading.Thread(target=_beat, name="open3d-heartbeat", daemon=True)
    t.start()
    return stop
