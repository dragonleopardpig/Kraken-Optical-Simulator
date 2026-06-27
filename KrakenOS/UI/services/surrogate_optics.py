"""Detect ideal / surrogate imaging optics (so a spot diagram isn't mistaken for a lens).

A "surrogate" lens is a first-order stand-in built from KrakenOS ``Thin Lens`` (paraxial,
ideal) elements -- e.g. a vendor black-box represented as two thin lenses between
``Lens Front/Rear Datum`` planes. Such optics are aberration-free BY CONSTRUCTION, so a
ray-traced spot / PSF / MTF / pixel-grid footprint shows only DEFOCUS (uniform across the
field), never the real lens's coma / astigmatism / field curvature. The surrogate is right
for layout / packaging / first-order; it cannot represent image quality without the real
prescription.

Pure: takes the per-surface types (and element/names) and returns a verdict. The strongest
signal is the surface TYPE ``Thin Lens`` -- definitionally an ideal lens, so it never
false-trips a real prescription (which images through curved ``Standard`` glass surfaces).
"""

from __future__ import annotations

# KrakenOS surface types that are paraxial / ideal (aberration-free) lenses.
IDEAL_LENS_SURFACE_TYPES = frozenset({"Thin Lens"})
_BLACKBOX_HINT = "blackbox"


def detect_surrogate_optics(surface_types, element_names=None) -> dict:
    """Return ``{is_surrogate, ideal_lens_count, blackbox_count, reason}``.

    ``surface_types`` are the per-row surface kinds (``row.surface``); ``element_names`` the
    optional per-row element/name strings. ``is_surrogate`` is True when any imaging power
    comes from an ideal ``Thin Lens`` element (or a row explicitly named/grouped
    "Blackbox") -- meaning a ray-traced spot is defocus-only, not real aberration.
    """
    types = [str(t).strip() for t in (surface_types or [])]
    names = [str(n).strip() for n in (element_names or [])]

    ideal_lens_count = sum(1 for t in types if t in IDEAL_LENS_SURFACE_TYPES)
    blackbox_count = sum(1 for n in names if _BLACKBOX_HINT in n.lower())
    is_surrogate = ideal_lens_count > 0 or blackbox_count > 0

    if not is_surrogate:
        reason = ""
    elif ideal_lens_count > 0:
        plural = "s" if ideal_lens_count != 1 else ""
        reason = f"{ideal_lens_count} ideal Thin Lens element{plural}"
    else:
        reason = "black-box surrogate element(s)"

    return {
        "is_surrogate": bool(is_surrogate),
        "ideal_lens_count": int(ideal_lens_count),
        "blackbox_count": int(blackbox_count),
        "reason": reason,
    }
