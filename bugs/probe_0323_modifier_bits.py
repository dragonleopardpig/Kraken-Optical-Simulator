#!/usr/bin/env python3
"""bugs/0323 modifier probe -- run this in your NORMAL desktop session (from
Kitty, same display the KrakenOS app uses), NOT headless.

Why: the Open-3D hover reads the Alt key from the Tk event ``state`` bitmask
(the same way Control=orbit already works). If your compositor/WM grabs Alt for
window management, or Alt maps to a bit we don't check, the app never sees it and
"Alt hover" silently does nothing. This isolates that one unknown.

    .devenv/state/venv/bin/python bugs/probe_0323_modifier_bits.py

Then, over the window: move the mouse holding NOTHING, then Ctrl, then Shift,
then Alt, then Super/Win. Watch which named bits light up (and the raw hex).
Report the line you see while holding **Alt**. Ctrl/Shift are the controls: they
already work in-app, so they prove the readout is sane.
"""
import tkinter as tk

# X11 / Tk core modifier bits (a mouse/key event's ``state`` is an OR of these).
BITS = [
    (0x0001, "Shift"),
    (0x0002, "Lock(Caps)"),
    (0x0004, "Control"),
    (0x0008, "Mod1  (Alt on most X11)"),
    (0x0010, "Mod2  (NumLock)"),
    (0x0020, "Mod3"),
    (0x0040, "Mod4  (Super/Win)"),
    (0x0080, "Mod5  (AltGr/ISO_Level3)"),
    (0x0100, "Button1"),
    (0x0200, "Button2"),
    (0x0400, "Button3"),
    (0x20000, "0x20000 (extended Alt on some setups)"),
]


def decode(state: int) -> str:
    names = [name for bit, name in BITS if state & bit]
    return ", ".join(names) if names else "(none)"


def alt_seen(state: int) -> bool:
    # exactly what the app checks in Kraken3DInspector._event_alt_pressed
    return bool(state & 0x0008 or state & 0x20000)


def main() -> None:
    root = tk.Tk()
    root.title("bugs/0323 modifier probe -- move mouse holding each modifier")
    root.geometry("760x340")

    header = tk.Label(
        root,
        justify="left",
        anchor="w",
        font=("monospace", 11),
        text=(
            "Move the mouse OVER THIS WINDOW while holding, in turn:\n"
            "  nothing -> Ctrl -> Shift -> Alt -> Super/Win\n"
            "The app reads Alt as (state & 0x0008) or (state & 0x20000).\n"
            "If the 'app sees ALT' line never says YES while you hold Alt+move,\n"
            "the compositor is eating Alt (or it maps to a different bit).",
        ),
    )
    header.pack(fill="x", padx=10, pady=(10, 6))

    live = tk.Label(root, justify="left", anchor="w", font=("monospace", 12),
                    text="move the mouse...", fg="#003366")
    live.pack(fill="x", padx=10, pady=6)

    seen_box = tk.Label(root, justify="left", anchor="nw", font=("monospace", 10),
                        text="distinct states seen:\n", fg="#333333")
    seen_box.pack(fill="both", expand=True, padx=10, pady=6)

    seen: "dict[int, str]" = {}

    def on_motion(event):
        state = int(getattr(event, "state", 0) or 0)
        yes = "YES" if alt_seen(state) else "no"
        live.config(text=(
            f"raw state = 0x{state:05x}   bits = [{decode(state)}]\n"
            f"app sees ALT = {yes}"
        ), fg="#007700" if yes == "YES" else "#003366")
        if state not in seen:
            seen[state] = decode(state)
            line = f"0x{state:05x}  ALT={'YES' if alt_seen(state) else 'no ':<3}  {seen[state]}"
            print(line, flush=True)
            body = "distinct states seen (also printed to terminal):\n" + "\n".join(
                f"0x{s:05x}  ALT={'YES' if alt_seen(s) else 'no '}  {d}"
                for s, d in sorted(seen.items())
            )
            seen_box.config(text=body)

    # bind on the toplevel and to any keypress too (so Alt_L press is visible)
    root.bind("<Motion>", on_motion)
    root.bind("<KeyPress>", lambda e: on_motion(e))
    root.bind("<KeyRelease>", lambda e: on_motion(e))
    root.bind("<Escape>", lambda e: root.destroy())
    print("probe running -- move the mouse over the window holding each modifier; Esc to quit")
    root.mainloop()


if __name__ == "__main__":
    main()
