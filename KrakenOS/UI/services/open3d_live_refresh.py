"""Open 3D Live Mode refresh scheduling."""

from __future__ import annotations

from typing import Any


DEFAULT_LIVE_REFRESH_DELAY_MS = 180
MAIN_PANEL_LIVE_REFRESH_DELAY_MS = 220
PENDING_LIVE_REFRESH_RETRY_MS = 40
MAX_LIVE_REFRESH_DELAY_MS = 1000


def normalized_live_refresh_delay(delay_ms: int | float | str | None) -> int:
    """Clamp live refresh delays to the interactive budget."""

    try:
        delay = int(delay_ms) if delay_ms is not None else DEFAULT_LIVE_REFRESH_DELAY_MS
    except (TypeError, ValueError):
        delay = DEFAULT_LIVE_REFRESH_DELAY_MS
    return max(0, min(delay, MAX_LIVE_REFRESH_DELAY_MS))


class Open3DLiveRefreshService:
    """Own debounced Live Mode refresh state for an Open 3D inspector."""

    def __init__(self, inspector: Any) -> None:
        self.inspector = inspector
        self.after_id: str | None = None
        self.busy = False
        self.pending = False
        self.reason = ""

    def cancel(self) -> None:
        after_id = self.after_id
        self.after_id = None
        if after_id is not None:
            try:
                self.inspector.after_cancel(after_id)
            except Exception:
                pass
        self.pending = False

    def schedule(self, reason: str = "", *, delay_ms: int = DEFAULT_LIVE_REFRESH_DELAY_MS) -> bool:
        inspector = self.inspector
        if not inspector._live_mode_enabled():
            return False
        if not bool(getattr(inspector, "available", False)):
            return False
        self.reason = str(reason or "scene change")
        if self.busy:
            self.pending = True
            return True
        if self.after_id is not None:
            try:
                inspector.after_cancel(self.after_id)
            except Exception:
                pass
        delay = normalized_live_refresh_delay(delay_ms)
        self.after_id = inspector.after(delay, self.run)
        inspector.status_var.set(f"Live Mode: scheduled trace ({self.reason}).")
        return True

    def run(self) -> None:
        inspector = self.inspector
        self.after_id = None
        if not inspector._live_mode_enabled():
            return
        if self.busy:
            self.pending = True
            return
        self.busy = True
        reason = self.reason or "scene change"
        try:
            try:
                inspector.editor._sync_object_controls()
                inspector.editor._sync_left_mode_controls()
            except Exception:
                pass
            inspector._refresh_live_preview_scene(reason)
        except Exception as exc:
            message = str(exc).strip() or exc.__class__.__name__
            inspector.status_var.set(f"Live Mode trace failed: {message}")
            inspector.editor.append_debug(f"Open 3D live trace failed: {exc}")
        finally:
            self.busy = False
            if self.pending and inspector._live_mode_enabled():
                self.pending = False
                self.schedule("pending scene change", delay_ms=PENDING_LIVE_REFRESH_RETRY_MS)
