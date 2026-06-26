"""STEP overlay slot labels shared by Open 3D services."""

from __future__ import annotations


STEP_OVERLAY_LABELS = ("lens", "optical", "led", "camera")
STEP_OVERLAY_LABEL_SET = set(STEP_OVERLAY_LABELS)

# Decoration overlays represent a light source (LED), a detector body
# (camera), or an imaging lens -- not a refracting/reflecting optical element
# the user authors. They must never be promoted into an optical mesh-solid or be
# assigned an optical face function: a camera/LED can't physically be a beam
# splitter, and promoting their heavy CAD (e.g. a 160-face LED) into the traced
# system makes the non-seq trace pathologically slow. The imaging lens is vendor
# CAD whose optics we model with a native KrakenOS surrogate, NOT by tracing the
# STEP mesh: the lone synchronization is the surrogate's Front/Rear Datum tracking
# the STEP front/rear faces (see glue_selected_step_to_surrogate). This mirrors the
# live-trace rule that only the generic "optical" overlay is auto-traceable.
STEP_OVERLAY_DECORATION_LABELS = ("led", "camera", "lens")
STEP_OVERLAY_DECORATION_LABEL_SET = set(STEP_OVERLAY_DECORATION_LABELS)


def is_step_overlay_decoration(label) -> bool:
    """True for non-optical decoration overlays (LED source, camera body, imaging lens)."""
    return str(label or "").strip().lower() in STEP_OVERLAY_DECORATION_LABEL_SET
