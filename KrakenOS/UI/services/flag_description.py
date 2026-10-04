"""What the bug-flag description prompt does, whichever toolkit shows it (bugs/0950).

The `s` flag writes its bundle (screenshot + state.json) at once, then asks for a description
WITHOUT taking the keyboard from a carry or a drag in progress. What the answer does -- write
description.txt, update state.json and the live recording's event, or delete the bundle -- is the
model's. A view collects the text and says which button was pressed.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

PROMPT = (
    "Describe the bug (carry / drag stays live while this is open).\n"
    "Save = keep with description · Keep screenshot = keep without · Discard = delete this flag.\n"
    "Closing with an empty box discards the flag (changed your mind)."
)


class FlagDescription:
    """One flagged bundle waiting for its description."""

    def __init__(self, *, bundle_dir, state_path, flag_event_payload=None,
                 set_status: Callable[[str], None], debug: Callable[[str], None],
                 discard: Callable[[], bool]) -> None:
        self.bundle_dir = Path(bundle_dir)
        self.state_path = Path(state_path)
        self.flag_event_payload = flag_event_payload
        self._set_status = set_status
        self._debug = debug
        self._discard = discard

    @property
    def title(self) -> str:
        return f"Flag: {self.bundle_dir.name}"

    @property
    def prompt(self) -> str:
        return PROMPT

    def save(self, text: str) -> None:
        """Keep the flag; with ``text``, write it into the bundle and the live recording."""
        text = str(text).strip()
        name = self.bundle_dir.name
        if not text:
            self._set_status(f"Flag kept without description: {name}")
            return
        try:
            (self.bundle_dir / "description.txt").write_text(text + "\n", encoding="utf-8")
        except Exception as exc:
            self._debug(f"Open 3D flag description save failed: {exc}")
        try:
            if self.state_path.exists():
                data = json.loads(self.state_path.read_text(encoding="utf-8"))
                data["description"] = text
                self.state_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as exc:
            self._debug(f"Open 3D flag state update failed: {exc}")
        if isinstance(self.flag_event_payload, dict):
            try:
                self.flag_event_payload["description"] = text
            except Exception:
                pass
        self._set_status(f"Flag description saved: {name}")

    def keep(self) -> None:
        """Keep the bundle even with an empty description (the mid-drag safety net)."""
        self._set_status(f"Flag kept (screenshot only): {self.bundle_dir.name}")

    def discard(self) -> None:
        name = self.bundle_dir.name
        ok = self._discard()
        self._set_status(f"Flag discarded: {name}" if ok else f"Flag discard failed (kept): {name}")

    def dismiss(self, text: str) -> None:
        """The prompt was closed without a button: an empty box means the flag was a mistake and
        is discarded; typed-but-unsaved text is saved, so the user's words are never thrown away."""
        if str(text).strip():
            self.save(text)
        else:
            self.discard()
