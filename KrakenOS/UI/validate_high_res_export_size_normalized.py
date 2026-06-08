"""Guard: the high-res plot export is normalised to a window-independent size.

Clicking a plot opens a high-resolution image via
``_open_high_res_plot_in_system_viewer``. The embedded canvas shrinks with the
window (e.g. a Wayland compositor auto-tiling the app), so with fixed point-size
fonts a small clicked plot used to export cramped -- overlapping labels, the
field-curvature two-panel jumbling its x ticks -- looking different from a
fullscreen export. The fix scales the whole figure uniformly so the clicked
content reaches a fixed target width regardless of the on-screen window. This
guards ``_high_res_export_figure_scale`` (bug 0039):

A. A small (tiled-window) content width scales UP toward the target.
B. A large (fullscreen) content width scales DOWN toward the target.
C. Two different source widths normalise to the SAME exported width (so tiled
   and fullscreen exports match), within the clamp range.
D. Degenerate / extreme widths are clamped and never zero/negative.

All checks are pure-function and display-free (no Agg / Xvfb / editor needed).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_high_res_export_size_normalized

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

from KrakenOS.UI.services.layout_plot_interaction import LayoutPlotInteractionMixin

_scale = LayoutPlotInteractionMixin._high_res_export_figure_scale
TARGET = 8.0


def run_checks(verbose: bool = False) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    passed = True

    # A. Small content scales up toward the target.
    small_w = 3.2
    s_small = _scale(small_w)
    if not (s_small > 1.0 and abs(small_w * s_small - TARGET) < 1e-6):
        notes.append(f"FAIL: small width {small_w} -> scale {s_small:.3f}, not normalised up to {TARGET}")
        passed = False

    # B. Large content scales down toward the target.
    large_w = 12.0
    s_large = _scale(large_w)
    if not (s_large < 1.0 and abs(large_w * s_large - TARGET) < 1e-6):
        notes.append(f"FAIL: large width {large_w} -> scale {s_large:.3f}, not normalised down to {TARGET}")
        passed = False

    # C. Different source widths give the SAME exported width (consistency).
    widths = [3.2, 5.0, 8.0, 12.0]
    exported = [w * _scale(w) for w in widths]
    if max(exported) - min(exported) > 1e-6:
        notes.append(f"FAIL: exported widths differ across sources: {exported}")
        passed = False

    # D. Degenerate / extreme widths stay sane (clamped, positive).
    if _scale(0.0) != 1.0:
        notes.append("FAIL: zero width should fall back to scale 1.0")
        passed = False
    tiny = _scale(0.01)   # would be 800x -> clamped
    huge = _scale(1000.0)  # would be 0.008x -> clamped
    if not (0.5 <= huge <= tiny <= 4.0):
        notes.append(f"FAIL: extreme widths not clamped to [0.5, 4.0]: tiny={tiny}, huge={huge}")
        passed = False

    if verbose:
        notes.append(
            f"small {small_w}->{s_small:.2f}, large {large_w}->{s_large:.2f}, "
            f"exported={[round(v, 3) for v in exported]}"
        )
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        print(note)
    if passed:
        print("[PASS] High-res export normalises the clicked content to a window-independent size")
        return 0
    print("[FAIL] High-res export size-normalisation guard")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
