"""Validate the low-risk modern ttk theme layer."""

from __future__ import annotations

import tkinter as tk

from KrakenOS.UI.modern_ttk_theme import MODERN_TTK_PALETTE, apply_modern_ttk_theme


def main() -> int:
    root = tk.Tk()
    root.withdraw()
    try:
        style = apply_modern_ttk_theme(root)
        frame_bg = str(style.lookup("TFrame", "background") or "")
        button_bg = str(style.lookup("TButton", "background") or "")
        heading_bg = str(style.lookup("Treeview.Heading", "background") or "")
        backend = getattr(style, "kraken_theme_backend", "")
        checks = [
            ("modern palette defines accent color", MODERN_TTK_PALETTE.get("accent") == "#2563eb"),
            ("theme backend is recorded", backend.startswith("sv-ttk") or backend == "ttk-clam"),
            ("TFrame background uses modern palette", frame_bg == MODERN_TTK_PALETTE["background"]),
            ("TButton background is styled", bool(button_bg)),
            ("Treeview heading background is styled", bool(heading_bg)),
            ("classic escape hatch returns style", apply_modern_ttk_theme(root, mode="classic") is not None),
        ]
    finally:
        root.destroy()

    failed = [name for name, ok in checks if not ok]
    if failed:
        print("Modern ttk theme validation failed:")
        for name in failed:
            print(f"- {name}")
        return 1
    print("Modern ttk theme validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
