"""Display-free guard for bugs/0384 -- the lens STEP overlay's fold anchor.

The lens overlay is folded onto a mirror/splitter leg by looking up a fold override keyed
on the lens FRONT-DATUM row (``_optical_axis_fold_world_transform_for_row`` /
``_lens_front_datum_row_index``). That finder used a NARROWER name test than the swap block
detector, so after swapping in a lens whose front row it did not recognise it fell back to
the first non-Object/Image/Aperture row = the FOLD-SOURCE promoted solid (an RA mirror),
which has no follower override -> fold transform None -> the lens rendered UNFOLDED (the
"lens misplaced / vertical after swap" symptom). ``_lens_datum_row_index`` now matches the
same names as the block detector (side + datum|vertex|edge) and never falls back onto a
promoted solid / mirror.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_lens_overlay_datum_anchor
"""

from __future__ import annotations

from types import SimpleNamespace as _R


def _finder(rows):
    from KrakenOS.UI.services.layout_polyline_display import LayoutPolylineDisplayMixin

    ed = LayoutPolylineDisplayMixin.__new__(LayoutPolylineDisplayMixin)
    ed.rows = rows
    return ed


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []

    def row(name, surface="Standard"):
        return _R(name=name, surface=surface)

    MIRROR = row("Promoted OPTICAL STEP optical solid", "Standard")  # the fold source
    LENS = [row("Blackbox Group 1", "Thin Lens"), row("Aperture Stop", "Aperture"),
            row("Blackbox Group 2", "Thin Lens")]

    # 1. Standard machine-vision surrogate naming (both finders agree).
    rows = [row("Object", "Object"), MIRROR, row("gap", "Standard"),
            row("Front Optical Vertex Datum"), *LENS, row("Rear Optical Vertex Datum"),
            MIRROR, row("Image", "Image")]
    ed = _finder(rows)
    if ed._lens_datum_row_index("front") != 3:
        failures.append(f"front(standard): got {ed._lens_datum_row_index('front')}, expected 3")
    if ed._lens_datum_row_index("rear") != 7:
        failures.append(f"rear(standard): got {ed._lens_datum_row_index('rear')}, expected 7")

    # 2. "Front/Rear Vertex" (no 'datum') -- must match via 'vertex', NOT the mirror at 1.
    rows = [row("Object", "Object"), MIRROR, row("Front Vertex"), row("Blackbox Group 1", "Thin Lens"),
            row("Rear Vertex"), row("Image", "Image")]
    ed = _finder(rows)
    if ed._lens_datum_row_index("front") != 2:
        failures.append(f"front('Front Vertex'): got {ed._lens_datum_row_index('front')}, expected 2 (not the fold-source mirror at 1)")
    if ed._lens_datum_row_index("rear") != 4:
        failures.append(f"rear('Rear Vertex'): got {ed._lens_datum_row_index('rear')}, expected 4")

    # 3. No datum-like name at all -- the fallback must SKIP the promoted mirror and land
    #    on the real lens row (never the fold source).
    rows = [row("Object", "Object"), MIRROR, row("Some Lens Body", "Thin Lens"), row("Image", "Image")]
    ed = _finder(rows)
    idx = ed._lens_datum_row_index("front")
    if idx != 2:
        failures.append(f"front(no-datum fallback): got {idx}, expected 2 (skip the promoted mirror at 1)")
    if idx is not None and "promoted" in (ed.rows[idx].name or "").lower():
        failures.append("front(no-datum fallback): must NEVER anchor to a promoted solid (the fold source)")

    # 4. Only a mirror + object/image -> None (nothing to anchor to; never the mirror).
    rows = [row("Object", "Object"), MIRROR, row("Image", "Image")]
    ed = _finder(rows)
    if ed._lens_datum_row_index("front") is not None:
        failures.append("front(mirror-only): must return None, never the fold-source mirror")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("Lens-overlay datum-anchor validation failed:")
        for name in failures:
            print(f"- {name}")
        return 1
    print(
        "Lens-overlay datum-anchor validation passed: the fold anchor matches the block "
        "detector's names (side + datum|vertex|edge) and never falls back onto the "
        "fold-source promoted solid -- so a swapped lens keeps its leg fold."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
