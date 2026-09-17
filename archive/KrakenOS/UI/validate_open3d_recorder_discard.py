"""Regression: discard() drops the in-progress recording without writing.

User asked for a Discard option so a mis-triggered recording does not
leave a stray ``recording_*.json`` behind. The contract:

* ``Open3DEventRecorder.discard()`` returns the count of dropped
  events.
* After discard, ``is_recording()`` is False, no JSON has been written
  under the recording directory since ``start()``, and the recorder is
  ready for the next ``start()``.

The test stands a tiny fake inspector up (no Tk/VTK), starts a
recording, appends a handful of synthetic events, calls discard, and
asserts the post-discard invariants.
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from KrakenOS.UI.services.open3d_event_recorder import (
    Open3DEventRecorder,
    RECORDING_DIR,
)


@dataclass
class _FakeEditor:
    def append_debug(self, message: str) -> None:
        return None


@dataclass
class _FakeInspector:
    """Minimal stand-in for Kraken3DInspector.

    Open3DEventRecorder only reads ``editor.append_debug`` and a handful
    of attributes on the inspector when snapshotting scene state. We
    skip the snapshot path entirely by inserting pre-built events
    through ``_append`` instead of ``record_mouse``.
    """

    editor: _FakeEditor = field(default_factory=_FakeEditor)


def _scan_new_recordings(since: float) -> list[Path]:
    if not RECORDING_DIR.exists():
        return []
    matches: list[Path] = []
    for path in RECORDING_DIR.glob("recording_*.json"):
        try:
            if path.stat().st_mtime > since:
                matches.append(path)
        except OSError:
            continue
    return matches


def _run() -> int:
    rec = Open3DEventRecorder(_FakeInspector())
    if rec.is_recording():
        print("FAIL: recorder reports active before start()", file=sys.stderr)
        return 1

    # discard with nothing to drop should be a benign no-op.
    if rec.discard() != 0:
        print("FAIL: discard() on idle recorder reported events to drop", file=sys.stderr)
        return 1

    before = time.time()
    # start() snapshots the inspector. The fake omits a renderer/camera
    # so the snapshot fields fall back to defaults; that's fine for
    # this contract test.
    rec.start(note="discard-test")
    if not rec.is_recording():
        print("FAIL: is_recording() False after start()", file=sys.stderr)
        return 1
    # Append a few synthetic events without going through the event-tap
    # paths so we don't need a real Tk event object.
    from KrakenOS.UI.services.open3d_event_recorder import RecordedEvent

    for kind in ("mouse_press", "mouse_move", "mouse_release", "key_press"):
        rec._append(RecordedEvent(timestamp_ms=float(len(rec.events) * 100.0), kind=kind))
    if len(rec.events) != 4:
        print(f"FAIL: expected 4 staged events, got {len(rec.events)}", file=sys.stderr)
        return 1

    dropped = rec.discard()
    if dropped != 4:
        print(f"FAIL: discard() reported {dropped} drops, expected 4", file=sys.stderr)
        return 1
    if rec.is_recording():
        print("FAIL: recorder still active after discard()", file=sys.stderr)
        return 1
    if rec.events:
        print(f"FAIL: events list non-empty after discard ({len(rec.events)})", file=sys.stderr)
        return 1
    if rec.prelude is not None:
        print("FAIL: prelude still set after discard()", file=sys.stderr)
        return 1

    new_files = _scan_new_recordings(before)
    if new_files:
        print(
            f"FAIL: discard() wrote files to disk: {[p.name for p in new_files]}",
            file=sys.stderr,
        )
        return 1

    # Ready for the next start() right away.
    rec.start(note="after-discard")
    if not rec.is_recording():
        print("FAIL: start() after discard() did not arm the recorder", file=sys.stderr)
        return 1
    rec.discard()

    print("PASS: discard() drops events, stops recording, and writes no file.")
    return 0


if __name__ == "__main__":
    raise SystemExit(_run())
