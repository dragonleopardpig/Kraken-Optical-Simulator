"""Validate that custom ttk theming is deferred by default."""

from __future__ import annotations

import tkinter as tk

from KrakenOS.UI.modern_ttk_theme import MODERN_TTK_PALETTE, apply_modern_ttk_theme


def main() -> int:
    root = tk.Tk()
    root.withdraw()
    try:
        style = apply_modern_ttk_theme(root)
        backend = getattr(style, "kraken_theme_backend", "")
        classic_style = apply_modern_ttk_theme(root, mode="classic")
        modern_style = apply_modern_ttk_theme(root, mode="modern")
        modern_backend = getattr(modern_style, "kraken_theme_backend", "")
        checks = [
            (
                "modern palette defines accent color",
                MODERN_TTK_PALETTE.get("accent") == "#2563eb",
            ),
            ("default theme backend is native", backend == "native"),
            (
                "classic escape hatch returns native style",
                getattr(classic_style, "kraken_theme_backend", "") == "native",
            ),
            (
                "modern theme remains opt-in",
                modern_backend.startswith("sv-ttk") or modern_backend == "ttk-clam",
            ),
        ]
    finally:
        root.destroy()

    failed = [name for name, ok in checks if not ok]
    if failed:
        print("Deferred ttk theme validation failed:")
        for name in failed:
            print(f"- {name}")
        return 1
    print("Deferred ttk theme validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
