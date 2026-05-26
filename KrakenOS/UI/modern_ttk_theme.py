"""Modern ttk theme helpers for the KrakenOS UI.

The editor is still a Tk/ttk application. This module keeps the visual refresh
low-risk by styling existing widgets instead of replacing them with a different
widget toolkit.
"""

from __future__ import annotations

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


def apply_modern_ttk_theme(root: tk.Misc, *, mode: str | None = None) -> ttk.Style:
    """Apply the KrakenOS ttk style layer and return the active style object.

    Set ``KRAKEN_UI_TTK_THEME=classic`` or ``off`` to leave the native ttk theme
    untouched. This is useful for debugging platform-specific widget issues.
    """

    selected_mode = (mode or os.getenv("KRAKEN_UI_TTK_THEME", "modern")).strip().lower()
    style = ttk.Style(root)
    if selected_mode in {"", "0", "false", "off", "native", "classic"}:
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
