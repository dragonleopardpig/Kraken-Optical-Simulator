"""STEP overlay slot labels shared by Open 3D services."""

from __future__ import annotations


STEP_OVERLAY_LABELS = ("lens", "optical", "led", "camera")
STEP_OVERLAY_LABEL_SET = set(STEP_OVERLAY_LABELS)

# Decoration overlays represent a light source (LED) or a detector body
# (camera) -- not a refracting/reflecting optical element. They must never be
# promoted into an optical mesh-solid or be assigned an optical face function:
# a camera/LED can't physically be a beam splitter, and promoting their heavy
# CAD (e.g. a 160-face LED) into the traced system makes the non-seq trace
# pathologically slow. This mirrors the live-trace rule that only the generic
# "optical" overlay is auto-traceable.
STEP_OVERLAY_DECORATION_LABELS = ("led", "camera")
STEP_OVERLAY_DECORATION_LABEL_SET = set(STEP_OVERLAY_DECORATION_LABELS)


def is_step_overlay_decoration(label) -> bool:
    """True for non-optical decoration overlays (LED source, camera body)."""
    return str(label or "").strip().lower() in STEP_OVERLAY_DECORATION_LABEL_SET
