"""Display-free contract for bugs/0005: the STEP face hover highlight must use
the shared hover-gold accent, never red.

Why this matters: ``_set_step_hover_outline`` paints the mouse-over highlight
for an imported STEP face. A lens viewed edge-on collapses that face outline to
a vertical line, so a *red* highlight rendered it as a thick red bar straight
through the glass -- the user's "ghost red edges" (flags 081 + 602). Red also
clashes with the rest of the inspector's language (pink = selection,
gold = hover). This pins the colour choice at its narrowest seam,
``Kraken3DInspector._step_hover_outline_style``; the rendered-pixel guarantee
lives in ``validate_open3d_step_face_hover_not_red_snapshot``.

Run from the repository root:

    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_step_face_hover_not_red
"""

from __future__ import annotations

from KrakenOS.UI.open3d_inspector import Kraken3DInspector

HOVER_GOLD = (1.0, 0.78, 0.08)


def _checks() -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []
    for has_surface in (True, False):
        color, opacity, line_width = Kraken3DInspector._step_hover_outline_style(has_surface)
        tag = "fill+edges" if has_surface else "edges-only"
        r, g, b = color
        # Not red: a red highlight is high-R / low-G / low-B. The fix's gold
        # has a large green component, which is exactly what separates it.
        checks.append((f"{tag}: highlight is not red (green channel present)", g >= 0.5, f"color={color}"))
        checks.append((f"{tag}: blue channel stays low (warm accent)", b <= 0.2, f"color={color}"))
        checks.append((f"{tag}: uses the shared hover-gold accent", color == HOVER_GOLD, f"color={color}"))
        checks.append((f"{tag}: opacity in (0, 1]", 0.0 < opacity <= 1.0, f"opacity={opacity}"))
        checks.append((f"{tag}: line width is a sane thin tube", 0.0 < line_width <= 5.0, f"line_width={line_width}"))
    # The two branches share the same accent so hover reads identically whether
    # or not the face outline came back with a fillable surface.
    fill = Kraken3DInspector._step_hover_outline_style(True)[0]
    edge = Kraken3DInspector._step_hover_outline_style(False)[0]
    checks.append(("both branches share one accent colour", fill == edge, f"fill={fill} edge={edge}"))
    return checks


def main() -> int:
    checks = _checks()
    failed = [(name, detail) for name, ok, detail in checks if not ok]
    if failed:
        print("Open 3D STEP face-hover colour validation failed:")
        for name, detail in failed:
            print(f"- {name}: {detail}")
        return 1
    print(f"Open 3D STEP face-hover colour validation passed ({len(checks)} checks).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
