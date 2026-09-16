"""Validate the ``KRAKEN_UI_SCALE`` helpers (HiDPI step 1).

Runs display-free under Xvfb. Checks a-d use bare Tk roots and the helpers
only; check e builds two headless editors in ONE subprocess so this process
never imports the editor and the no-compounding guarantee is proven on the
real thing.
"""

from __future__ import annotations

import gc
import os
import subprocess
import sys
import tkinter as tk
from tkinter import ttk

from KrakenOS.UI.modern_ttk_theme import UI_SCALE_ENV, apply_ui_scale, scaled_px, ui_scale_factor


_HEADLESS_EDITOR_SNIPPET = """
import os, tkinter as tk
from tkinter import ttk
env_scale = os.environ.pop("KRAKEN_UI_SCALE")
probe = tk.Tk(); probe.withdraw()
base = float(probe.tk.call("tk", "scaling"))
label = ttk.Label(probe, text="Hello world"); probe.update_idletasks()
print("UNSCALED=%r %d %d" % (base, label.winfo_reqheight(), probe.tk.call("font", "configure", "TkDefaultFont", "-size")))
probe.destroy()
os.environ["KRAKEN_UI_SCALE"] = env_scale
from KrakenOS.UI.layout_editor import KrakenLayoutEditor
for index in (1, 2):
    editor = KrakenLayoutEditor(headless=True)
    editor.update_idletasks()
    label = ttk.Label(editor, text="Hello world"); editor.update_idletasks()
    print("EDITOR%d=%s %r %d %d %d" % (
        index, editor.geometry(), float(editor.tk.call("tk", "scaling")), label.winfo_reqheight(),
        editor.tk.call("font", "configure", "TkDefaultFont", "-size"),
        editor.tk.call("font", "configure", "TkMenuFont", "-size")))
    editor.destroy()
"""


class _RecordingTk:
    """Stand-in root whose ``tk.call`` records every Tcl call it receives."""

    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []
        self.tk = self

    def call(self, *args: object) -> float:
        self.calls.append(args)
        return 1.3333333333333333


def _named_font_sizes(root: tk.Misc) -> dict[str, int]:
    return {
        str(name): int(root.tk.call("font", "configure", name, "-size"))
        for name in root.tk.call("font", "names")
    }


def _scaling_tolerance(root: tk.Misc, expected: float) -> float:
    # Tk stores ``tk scaling`` as an integer screen-mm width, so the readback is
    # quantized: bound the comparison by one mm.
    return expected / float(root.winfo_screenmmwidth()) + 1e-6


def _headless_editors(scale: str) -> tuple[int, dict[str, str], str]:
    env = dict(os.environ)
    env[UI_SCALE_ENV] = scale
    proc = subprocess.run(
        [sys.executable, "-c", _HEADLESS_EDITOR_SNIPPET],
        env=env,
        capture_output=True,
        text=True,
        timeout=240,
    )
    lines: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        for key in ("UNSCALED", "EDITOR1", "EDITOR2"):
            if line.startswith(key + "="):
                lines[key] = line[len(key) + 1 :]
    return proc.returncode, lines, proc.stderr[-800:]


def main() -> int:
    notes: list[str] = []

    def check(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    saved_env = os.environ.get(UI_SCALE_ENV)
    root = tk.Tk()
    root.withdraw()
    try:
        # a. unset: factor 1.0, tk scaling and named fonts untouched, no Tcl call.
        os.environ.pop(UI_SCALE_ENV, None)
        before = float(root.tk.call("tk", "scaling"))
        fonts_before = _named_font_sizes(root)
        factor = apply_ui_scale(root)
        after = float(root.tk.call("tk", "scaling"))
        check(factor == 1.0 and ui_scale_factor() == 1.0, "unset: ui_scale_factor() == 1.0")
        check(after == before, f"unset: tk scaling exactly unchanged ({before!r})")
        check(_named_font_sizes(root) == fonts_before, f"unset: named fonts unchanged ({fonts_before})")
        recorder = _RecordingTk()
        apply_ui_scale(recorder)  # type: ignore[arg-type]
        check(recorder.calls == [], "unset: apply_ui_scale makes no tk call")
        check(scaled_px(1400) == 1400 and scaled_px(720) == 720, "unset: scaled_px is identity")

        # b. 1.5: multiplies the CURRENT (DPI-derived, Xvfb is not 96 DPI) tk
        # scaling AND every pixel-sized named font; widgets built BEFORE the call
        # grow too because named fonts propagate live.
        pixel_fonts = {name: size for name, size in fonts_before.items() if size < 0}
        check(
            "TkDefaultFont" in pixel_fonts and "TkMenuFont" in pixel_fonts and "TkTextFont" in pixel_fonts,
            f"X11 named fonts are pixel-sized (negative) so tk scaling alone cannot grow them ({pixel_fonts})",
        )
        early_label = ttk.Label(root, text="Hello world")
        early_text = tk.Text(root, height=1)
        early_menu = tk.Menu(root, tearoff=False)
        early_menu.add_command(label="Hello world")
        early_point = tk.Label(root, text="Hello world", font=("DejaVu Sans", 9))
        root.update_idletasks()
        early_sizes = (early_label.winfo_reqheight(), early_text.winfo_reqheight(), early_menu.winfo_reqheight())
        early_point_height = early_point.winfo_reqheight()
        # Tk caches font specs while a widget holds them: release the 9pt one so
        # the post-scaling label below resolves it afresh (as production does,
        # where apply_ui_scale runs before any font exists).
        early_point.destroy()
        os.environ[UI_SCALE_ENV] = "1.5"
        factor = apply_ui_scale(root)
        after = float(root.tk.call("tk", "scaling"))
        expected = before * 1.5
        check(factor == 1.5, "1.5: ui_scale_factor() == 1.5")
        check(
            abs(after - expected) <= _scaling_tolerance(root, expected),
            f"1.5: real tk scaling {before!r} -> {after!r} (x1.5 within Tk's 1 mm quantization)",
        )
        expected_fonts = {name: -int(round(-size * 1.5)) for name, size in pixel_fonts.items()}
        got_fonts = {name: size for name, size in _named_font_sizes(root).items() if name in pixel_fonts}
        check(got_fonts == expected_fonts, f"1.5: pixel-sized named fonts x1.5 exactly ({got_fonts})")
        root.update_idletasks()
        late_sizes = (early_label.winfo_reqheight(), early_text.winfo_reqheight(), early_menu.winfo_reqheight())
        check(
            all(late >= early * 1.3 for early, late in zip(early_sizes, late_sizes)),
            f"1.5: ttk.Label/Text/Menu built before the call grew (reqheight {early_sizes} -> {late_sizes})",
        )
        late_point = tk.Label(root, text="Hello world", font=("DejaVu Sans", 9))
        root.update_idletasks()
        check(
            late_point.winfo_reqheight() >= early_point_height * 1.3,
            f"1.5: a 9pt font created after the call is x1.5 ({early_point_height} -> {late_point.winfo_reqheight()})",
        )
        check(scaled_px(1400) == 2100, "1.5: scaled_px(1400) == 2100")
        check(scaled_px(720) == 1080, "1.5: scaled_px(720) == 1080")
        check(scaled_px(1400, 1.5) == 2100, "1.5: explicit factor argument honoured")

        # c. no compounding: a repeat call on the same root, a second concurrent
        # root and a root built after destroy()+gc all land on base*1.5 (tk
        # scaling lives on the shared X display), each interpreter's named fonts
        # at x1.5; unsetting the factor afterwards restores the base.
        apply_ui_scale(root)
        again = float(root.tk.call("tk", "scaling"))
        check(
            abs(again - expected) <= _scaling_tolerance(root, expected) and got_fonts == {
                name: size for name, size in _named_font_sizes(root).items() if name in pixel_fonts
            },
            f"1.5: repeat call on the same root does not compound (tk scaling {again!r}, fonts {got_fonts})",
        )
        root2 = tk.Tk()
        root2.withdraw()
        try:
            inherited = float(root2.tk.call("tk", "scaling"))
            apply_ui_scale(root2)
            second = float(root2.tk.call("tk", "scaling"))
            check(
                abs(second - expected) <= _scaling_tolerance(root2, expected),
                f"1.5: second concurrent root inherits {inherited!r} and lands on base*1.5 = {second!r}, not x2.25",
            )
            check(
                {name: size for name, size in _named_font_sizes(root2).items() if name in pixel_fonts} == expected_fonts,
                "1.5: second root's own named fonts are x1.5",
            )
        finally:
            root2.destroy()
        gc.collect()
        root3 = tk.Tk()
        root3.withdraw()
        try:
            apply_ui_scale(root3)
            third = float(root3.tk.call("tk", "scaling"))
            check(
                abs(third - expected) <= _scaling_tolerance(root3, expected),
                f"1.5: root built after destroy()+gc lands on base*1.5 = {third!r}, not x3.375",
            )
            os.environ.pop(UI_SCALE_ENV, None)
            apply_ui_scale(root3)
            restored = float(root3.tk.call("tk", "scaling"))
            check(
                abs(restored - before) <= _scaling_tolerance(root3, before)
                and {name: size for name, size in _named_font_sizes(root3).items() if name in pixel_fonts} == pixel_fonts,
                f"unset after 1.5: tk scaling restored to base {restored!r} and fonts to {pixel_fonts}",
            )
        finally:
            root3.destroy()

        # d. garbage / out-of-range values fall back to 1.0 without raising.
        for raw in ("abc", "", "0", "99", "nan", "-1", "inf", " 1.5 "):
            os.environ[UI_SCALE_ENV] = raw
            expected_factor = 1.5 if raw.strip() == "1.5" else 1.0
            try:
                got = ui_scale_factor()
                ok = got == expected_factor
                detail = f"-> {got!r}"
            except Exception as exc:  # noqa: BLE001
                ok = False
                detail = f"raised {type(exc).__name__}: {exc}"
            check(ok, f"{raw!r}: ui_scale_factor() == {expected_factor!r} {detail}")
    finally:
        if saved_env is None:
            os.environ.pop(UI_SCALE_ENV, None)
        else:
            os.environ[UI_SCALE_ENV] = saved_env
        root.destroy()

    # e. two headless editors in one subprocess (~10 s): the first opens at the
    # scaled geometry with x1.5 named fonts and a grown ttk.Label; the second
    # gets the same scale, not 2.25x.
    code, lines, stderr_tail = _headless_editors("1.5")
    try:
        base_scaling, base_label, base_font = lines["UNSCALED"].split()
        geometry1, scaling1, label1, default1, menu1 = lines["EDITOR1"].split()
        geometry2, scaling2, label2, default2, menu2 = lines["EDITOR2"].split()
        ratio1 = float(scaling1) / float(base_scaling)
        ratio2 = float(scaling2) / float(base_scaling)
        parsed = True
    except (KeyError, ValueError):
        parsed = False
    check(code == 0 and parsed, f"headless editors subprocess ran (rc={code}, lines={lines})")
    if parsed:
        check(geometry1.startswith("2100x1275"), f"headless editor #1 with {UI_SCALE_ENV}=1.5 opens 2100x1275 (got {geometry1!r})")
        check(
            int(default1) == -int(round(-int(base_font) * 1.5)) and int(menu1) < int(base_font),
            f"headless editor #1 named fonts x1.5 (TkDefaultFont {base_font} -> {default1}, TkMenuFont {menu1})",
        )
        check(
            int(label1) >= int(base_label) * 1.3,
            f"headless editor #1 ttk.Label reqheight grew ({base_label} -> {label1})",
        )
        check(abs(ratio1 - 1.5) < 0.05, f"headless editor #1 tk scaling = base x{ratio1:.3f}")
        check(
            abs(ratio2 - 1.5) < 0.05 and default2 == default1 and label2 == label1,
            f"headless editor #2 in the same process is still x{ratio2:.3f} (fonts {default2}, label {label2}), not 2.25x",
        )
    if code != 0 and stderr_tail:
        notes.append(stderr_tail)

    for note in notes:
        print(note)
    passed = all(note.startswith("PASS") for note in notes)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
