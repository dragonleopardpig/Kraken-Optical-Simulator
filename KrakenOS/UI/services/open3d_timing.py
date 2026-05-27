"""Structured timing log for Open 3D responsiveness diagnostics."""

from __future__ import annotations

from contextlib import contextmanager
import itertools
import json
import os
from pathlib import Path
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
