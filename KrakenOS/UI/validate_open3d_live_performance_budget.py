"""Validate Open 3D Live Mode debounce/performance budgets."""

from __future__ import annotations

from KrakenOS.UI.services.open3d_live_refresh import (
    DEFAULT_LIVE_REFRESH_DELAY_MS,
    MAIN_PANEL_LIVE_REFRESH_DELAY_MS,
    MAX_LIVE_REFRESH_DELAY_MS,
    PENDING_LIVE_REFRESH_RETRY_MS,
    Open3DLiveRefreshService,
    normalized_live_refresh_delay,
)


class _StatusVar:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def set(self, message: str) -> None:
        self.messages.append(str(message))


class _Editor:
    def __init__(self) -> None:
        self.debug: list[str] = []

    def _sync_object_controls(self) -> None:
        return None

    def _sync_left_mode_controls(self) -> None:
        return None

    def append_debug(self, message: str) -> None:
        self.debug.append(str(message))


class _Inspector:
    def __init__(self) -> None:
        self.available = True
        self.live = True
        self.cancelled: list[str] = []
        self.scheduled: list[tuple[str, int, object]] = []
        self.refreshes: list[str] = []
        self.status_var = _StatusVar()
        self.editor = _Editor()

    def _live_mode_enabled(self) -> bool:
        return self.live

    def after(self, delay_ms: int, callback: object) -> str:
        after_id = f"after-{len(self.scheduled) + 1}"
        self.scheduled.append((after_id, delay_ms, callback))
        return after_id

    def after_cancel(self, after_id: str) -> None:
        self.cancelled.append(after_id)

    def _refresh_live_preview_scene(self, reason: str) -> None:
        self.refreshes.append(reason)


def main() -> int:
    inspector = _Inspector()
    service = Open3DLiveRefreshService(inspector)

    checks: list[tuple[str, bool]] = [
        ("default debounce is interactive", 100 <= DEFAULT_LIVE_REFRESH_DELAY_MS <= 250),
        ("main-panel debounce is slightly more conservative", DEFAULT_LIVE_REFRESH_DELAY_MS <= MAIN_PANEL_LIVE_REFRESH_DELAY_MS <= 300),
        ("pending retry is quick but not zero-spin", 25 <= PENDING_LIVE_REFRESH_RETRY_MS <= 80),
        ("maximum delay keeps accidental long sleeps bounded", MAX_LIVE_REFRESH_DELAY_MS <= 1000),
        ("negative delays clamp to zero", normalized_live_refresh_delay(-10) == 0),
        ("large delays clamp to budget max", normalized_live_refresh_delay(50_000) == MAX_LIVE_REFRESH_DELAY_MS),
    ]

    checks.append(("first schedule accepted", service.schedule("first")))
    checks.append(("first schedule uses default budget", inspector.scheduled[-1][1] == DEFAULT_LIVE_REFRESH_DELAY_MS))
    checks.append(("second schedule cancels stale callback", service.schedule("second", delay_ms=MAIN_PANEL_LIVE_REFRESH_DELAY_MS)))
    checks.append(("stale callback cancelled", inspector.cancelled == ["after-1"]))
    checks.append(("second schedule uses main-panel budget", inspector.scheduled[-1][1] == MAIN_PANEL_LIVE_REFRESH_DELAY_MS))

    service.busy = True
    checks.append(("busy schedule records pending instead of queuing another callback", service.schedule("busy-change")))
    checks.append(("busy schedule sets pending", service.pending is True and len(inspector.scheduled) == 2))
    service.busy = False
    service.run()
    checks.append(("run refreshes current reason", inspector.refreshes == ["busy-change"]))
    checks.append(("pending retry reuses bounded retry delay", inspector.scheduled[-1][1] == PENDING_LIVE_REFRESH_RETRY_MS))

    service.cancel()
    checks.append(("cancel clears pending and active callback", service.after_id is None and service.pending is False))

    failed = [name for name, ok in checks if not ok]
    if failed:
        print("Open 3D Live Mode performance budget validation failed:")
        for name in failed:
            print(f"- {name}")
        return 1
    print("Open 3D Live Mode performance budget validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
