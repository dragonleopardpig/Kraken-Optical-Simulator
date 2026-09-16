"""Deferred ttk theme helpers for the KrakenOS UI.

The editor is still a Tk/ttk application. The production-readiness branch keeps
the native ttk look by default while preserving this adapter as a final polish
milestone hook.
"""

from __future__ import annotations

import math
import os
import tkinter as tk
from tkinter import ttk
from typing import Any


MODERN_TTK_PALETTE: dict[str, str] = {
    "background": "#edf2f7",
    "surface": "#f8fafc",
    "surface_alt": "#e2e8f0",
    "text": "#0f172a",
    "muted": "#475569",
    "border": "#cbd5e1",
    "accent": "#2563eb",
    "accent_hover": "#1d4ed8",
    "accent_pressed": "#1e40af",
    "selection": "#dbeafe",
    "warning": "#f59e0b",
}


def _safe_configure(style: ttk.Style, name: str, **options: Any) -> None:
    try:
        style.configure(name, **options)
    except tk.TclError:
        pass


def _safe_map(style: ttk.Style, name: str, **options: Any) -> None:
    try:
        style.map(name, **options)
    except tk.TclError:
        pass


def _apply_sv_ttk_if_available(style: ttk.Style, selected_mode: str) -> bool:
    """Apply sv-ttk when installed, returning whether it became the backend."""

    try:
        import sv_ttk  # type: ignore[import-not-found]
    except Exception:
        return False

    requested_theme = "light"
    if selected_mode in {"dark", "sv-dark", "sv_ttk_dark"}:
        requested_theme = "dark"
    try:
        sv_ttk.set_theme(requested_theme)
    except Exception:
        return False
    setattr(style, "kraken_theme_backend", f"sv-ttk:{requested_theme}")
    return True


# HiDPI step 1: ``KRAKEN_UI_SCALE`` multiplies Tk's own DPI-derived
# ``tk scaling`` (so point-sized fonts and the two window geometries grow) AND
# Tk's pixel-sized named fonts (TkDefaultFont & co., which ignore ``tk
# scaling``) at native resolution, instead of relying on compositor upscaling,
# which blurs XWayland/Tk apps. Widget pixel dims are step 2.
UI_SCALE_ENV = "KRAKEN_UI_SCALE"
UI_SCALE_MIN = 0.5
UI_SCALE_MAX = 4.0

# ``tk scaling`` is stored on the X display, which every ``tk.Tk()`` root in
# the process shares and which survives ``destroy()``: remember the un-scaled
# value per display so a second root sets base*factor instead of compounding.
_display_base_scaling: dict[str, float] = {}

# Named fonts are per interpreter; their un-scaled pixel sizes are kept in this
# Tcl array inside the interpreter so a repeat call re-derives from the base.
_FONT_BASE_VAR = "::kraken_ui_scale_font_base"


def ui_scale_factor() -> float:
    """Return the ``KRAKEN_UI_SCALE`` factor, or 1.0 when unset or unusable.

    Out-of-range values fall back to 1.0 rather than clamping: a typo such as
    ``99`` would otherwise silently produce an unusable 4x window.
    """

    raw = os.getenv(UI_SCALE_ENV, "")
    try:
        factor = float(raw.strip())
    except (TypeError, ValueError):
        return 1.0
    if not math.isfinite(factor) or not (UI_SCALE_MIN <= factor <= UI_SCALE_MAX):
        return 1.0
    return factor


def _scale_named_fonts(root: tk.Misc, factor: float) -> None:
    """Set every pixel-sized named font to ``round(base_px * factor)``.

    On X11 Tk's ttk/fonts.tcl gives all nine named fonts a NEGATIVE (pixel)
    size, and pixel sizes are immune to ``tk scaling``; in the default
    ``native`` theme mode every ttk widget, Menu, Text and Listbox renders in
    one of them, so without this the window grows but the text does not.
    Point-sized named fonts follow ``tk scaling`` on their own and are left
    alone. Named fonts propagate live, so widgets already built also grow.
    """

    call = root.tk.call
    for name in call("font", "names"):
        name = str(name)
        var = f"{_FONT_BASE_VAR}({name})"
        if int(call("info", "exists", var)):
            base_px = int(call("set", var))
        else:
            size = int(call("font", "configure", name, "-size"))
            if size >= 0:
                continue
            base_px = -size
            call("set", var, base_px)
        call("font", "configure", name, "-size", -max(1, int(round(base_px * factor))))


def apply_ui_scale(root: tk.Misc) -> float:
    """Scale ``tk scaling`` and the named fonts of ``root`` by the env factor.

    Call on each root BEFORE any point-sized font is configured: point sizes
    are resolved against ``tk scaling`` when the font is created. Idempotent
    per process: the display's un-scaled ``tk scaling`` is remembered on first
    use and every call sets ``base * factor`` (never ``current * factor``, which
    compounded across roots, and never a constant, which would break other
    DPIs). With the factor at 1.0 and no earlier scaled root, no Tk call is
    made at all, so the default path is untouched; after an earlier scaled
    root it restores the base.
    """

    factor = ui_scale_factor()
    if factor == 1.0 and not _display_base_scaling:
        return factor
    display = str(root.winfo_screen())
    base = _display_base_scaling.get(display)
    if base is None:
        base = float(root.tk.call("tk", "scaling"))
        _display_base_scaling[display] = base
        if factor == 1.0:
            return factor
    root.tk.call("tk", "scaling", base * factor)
    _scale_named_fonts(root, factor)
    return factor


def scaled_px(n: float, factor: float | None = None) -> int:
    """Return ``n`` pixels scaled by ``factor`` (default: the env factor)."""

    if factor is None:
        factor = ui_scale_factor()
    return int(round(n * factor))


def apply_modern_ttk_theme(root: tk.Misc, *, mode: str | None = None) -> ttk.Style:
    """Return the active style object, leaving native ttk untouched by default.

    Set ``KRAKEN_UI_TTK_THEME=modern`` to opt into the experimental style layer.
    The branch defaults to ``native`` until the final visual polish milestone.
    """

    selected_mode = (
        mode if mode is not None else os.getenv("KRAKEN_UI_TTK_THEME", "native")
    ).strip().lower()
    style = ttk.Style(root)
    if selected_mode in {"", "0", "false", "off", "native", "classic", "default"}:
        setattr(style, "kraken_theme_backend", "native")
        return style

    sv_ttk_active = _apply_sv_ttk_if_available(style, selected_mode)
    if not sv_ttk_active:
        try:
            if "clam" in style.theme_names():
                style.theme_use("clam")
        except tk.TclError:
            pass
        setattr(style, "kraken_theme_backend", "ttk-clam")

    palette = MODERN_TTK_PALETTE
    try:
        root.configure(background=palette["background"])
    except tk.TclError:
        pass

    _safe_configure(
        style,
        ".",
        background=palette["background"],
        foreground=palette["text"],
        font=("DejaVu Sans", 9),
    )
    _safe_configure(style, "TFrame", background=palette["background"])
    _safe_configure(
        style,
        "Card.TFrame",
        background=palette["surface"],
        bordercolor=palette["border"],
        relief="solid",
        borderwidth=1,
    )
    _safe_configure(
        style,
        "TLabelframe",
        background=palette["background"],
        bordercolor=palette["border"],
        relief="solid",
        borderwidth=1,
    )
    _safe_configure(
        style,
        "TLabelframe.Label",
        background=palette["background"],
        foreground=palette["muted"],
        font=("DejaVu Sans", 9, "bold"),
    )
    _safe_configure(style, "TLabel", background=palette["background"], foreground=palette["text"])
    _safe_configure(
        style,
        "Muted.TLabel",
        background=palette["background"],
        foreground=palette["muted"],
    )
    _safe_configure(
        style,
        "TButton",
        background=palette["surface_alt"],
        foreground=palette["text"],
        bordercolor=palette["border"],
        focusthickness=1,
        focuscolor=palette["accent"],
        padding=(8, 4),
        relief="flat",
    )
    _safe_map(
        style,
        "TButton",
        background=[
            ("pressed", palette["accent_pressed"]),
            ("active", palette["accent_hover"]),
            ("disabled", "#e5e7eb"),
        ],
        foreground=[("pressed", "white"), ("active", "white"), ("disabled", "#94a3b8")],
    )
    _safe_configure(
        style,
        "Accent.TButton",
        background=palette["accent"],
        foreground="white",
        bordercolor=palette["accent"],
        padding=(9, 4),
        relief="flat",
    )
    _safe_map(
        style,
        "Accent.TButton",
        background=[("pressed", palette["accent_pressed"]), ("active", palette["accent_hover"])],
        foreground=[("pressed", "white"), ("active", "white")],
    )
    _safe_configure(style, "Toolbutton", padding=(6, 3), relief="flat")
    _safe_map(style, "Toolbutton", background=[("active", palette["selection"]), ("pressed", palette["surface_alt"])])
    _safe_configure(style, "TCheckbutton", background=palette["background"], foreground=palette["text"])
    _safe_configure(style, "TRadiobutton", background=palette["background"], foreground=palette["text"])
    _safe_configure(
        style,
        "TEntry",
        fieldbackground="white",
        foreground=palette["text"],
        bordercolor=palette["border"],
        lightcolor=palette["border"],
        darkcolor=palette["border"],
        padding=(4, 3),
    )
    _safe_configure(
        style,
        "TCombobox",
        fieldbackground="white",
        foreground=palette["text"],
        bordercolor=palette["border"],
        arrowcolor=palette["muted"],
        padding=(4, 3),
    )
    _safe_map(
        style,
        "TCombobox",
        fieldbackground=[("readonly", "white"), ("disabled", "#f1f5f9")],
        foreground=[("disabled", "#94a3b8")],
    )
    _safe_configure(
        style,
        "TSpinbox",
        fieldbackground="white",
        foreground=palette["text"],
        bordercolor=palette["border"],
        arrowcolor=palette["muted"],
        padding=(4, 3),
    )
    _safe_configure(style, "TPanedwindow", background=palette["background"])
    _safe_configure(
        style,
        "TNotebook",
        background=palette["background"],
        borderwidth=0,
        tabmargins=(2, 2, 2, 0),
    )
    _safe_configure(
        style,
        "TNotebook.Tab",
        background=palette["surface_alt"],
        foreground=palette["muted"],
        padding=(10, 4),
    )
    _safe_map(
        style,
        "TNotebook.Tab",
        background=[("selected", palette["surface"]), ("active", palette["selection"])],
        foreground=[("selected", palette["text"]), ("active", palette["text"])],
    )
    _safe_configure(
        style,
        "Treeview",
        background="white",
        fieldbackground="white",
        foreground=palette["text"],
        bordercolor=palette["border"],
        rowheight=24,
    )
    _safe_configure(
        style,
        "Treeview.Heading",
        background=palette["surface_alt"],
        foreground=palette["text"],
        bordercolor=palette["border"],
        relief="flat",
        padding=(4, 3),
    )
    _safe_map(
        style,
        "Treeview.Heading",
        background=[("active", palette["selection"])],
        foreground=[("active", palette["text"])],
    )
    _safe_configure(
        style,
        "Horizontal.TProgressbar",
        background=palette["accent"],
        troughcolor=palette["surface_alt"],
        bordercolor=palette["border"],
        lightcolor=palette["accent"],
        darkcolor=palette["accent"],
    )
    _safe_configure(
        style,
        "Vertical.TProgressbar",
        background=palette["accent"],
        troughcolor=palette["surface_alt"],
        bordercolor=palette["border"],
        lightcolor=palette["accent"],
        darkcolor=palette["accent"],
    )
    return style
