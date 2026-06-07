"""Mouse-wheel scrolling for canvas-backed scrollable panels.

Binding the wheel to the canvas alone fails because the inner content frame and
its child widgets sit on top and swallow the event, so the wheel only worked
over the scrollbar. This binds the wheel globally and scrolls the given canvas
whenever the pointer is anywhere within its content subtree -- which avoids the
``<Enter>``/``<Leave>`` ``NotifyInferior`` flicker of the per-widget approach and
works for X11 (``<Button-4>``/``<Button-5>``) as well as ``<MouseWheel>``.
"""

from __future__ import annotations

from typing import Any


def bind_mousewheel_scroll(canvas: Any, content: Any) -> None:
    def _pointer_in_subtree(widget: Any) -> bool:
        while widget is not None:
            if widget is canvas or widget is content:
                return True
            widget = getattr(widget, "master", None)
        return False

    def _on_wheel(event):
        if not _pointer_in_subtree(getattr(event, "widget", None)):
            return None
        num = getattr(event, "num", None)
        if num == 4:
            canvas.yview_scroll(-1, "units")
        elif num == 5:
            canvas.yview_scroll(1, "units")
        else:
            delta = int(getattr(event, "delta", 0) or 0)
            if delta:
                canvas.yview_scroll(-1 if delta > 0 else 1, "units")
        return "break"

    for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
        try:
            canvas.bind_all(sequence, _on_wheel, add="+")
        except Exception:
            pass
