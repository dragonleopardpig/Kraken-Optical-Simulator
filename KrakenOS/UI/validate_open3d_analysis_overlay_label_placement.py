"""Display-free guard for the grouped analysis-overlay legend placement (flag 20260708_161012).

The illumination heatmap + rays overlays (and the field-aberration overlays: best-focus, distortion,
astigmatism, spot map, pixel grid) all QUEUE their caption into one shared billboard drawn by
``Kraken3DInspector._add_grouped_analysis_overlay_label``. The legend used to anchor at ``sup*0.95*reach``
(just BELOW the figure's top edge) and draw TOP-justified, so the multi-line block grew DOWNWARD and
draped back over the detector figure -- exactly what the user flagged ("the text label overlap the
underlying figure, can space out?").

The fix anchors the block just ABOVE the figure's top edge (``sup*1.15*reach``) and draws it
BOTTOM-justified so it grows UPWARD, away from the figure. The anchor math is a pure static helper
(``_analysis_overlay_label_anchor``) so it is checkable without a renderer:

* GEOMETRY: for the canonical basis, a tilted (3/4-camera) basis, and the no-screen-axes fallback, the
  anchor clears the figure top edge along screen-up (>= reach) with margin, keeps a rightward bias, and
  offsets only slightly along the plane normal; a degenerate reach still yields a finite anchor above
  centre.
* WIRING (source inspection): the drawing method delegates to the helper AND flips the text block to
  bottom vertical justification (grows up, not down).
"""

from __future__ import annotations

import inspect
import os

import numpy as np

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")


def _orthonormal_tilt() -> "tuple[np.ndarray, np.ndarray, np.ndarray]":
    """A screen right/up/normal basis that is NOT axis-aligned (a 3/4 camera view), so the guard
    exercises the tilted case the flagged scene was captured in."""
    view = np.array([0.6, -0.4, 0.7])
    view = view / np.linalg.norm(view)
    up_hint = np.array([0.0, 1.0, 0.0])
    sright = np.cross(up_hint, view)
    sright = sright / np.linalg.norm(sright)
    sup = np.cross(view, sright)
    sup = sup / np.linalg.norm(sup)
    return sright, sup, view


def _check_geometry(failures: list[str]) -> None:
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    anchor_fn = Kraken3DInspector._analysis_overlay_label_anchor
    reach = 20.0
    center = np.array([0.0, 0.0, 657.0])
    normal = np.array([0.0, 0.0, 1.0])

    # Canonical basis: screen-up = world +Y, screen-right = world +X.
    sright, sup = np.array([1.0, 0.0, 0.0]), np.array([0.0, 1.0, 0.0])
    anchor = np.asarray(anchor_fn(center, normal, sright, sup, reach), dtype=float)
    rel = anchor - center
    up_amt = float(np.dot(rel, sup))
    if up_amt < reach:
        failures.append(
            f"GEOMETRY: legend anchor sits at {up_amt:.2f} along screen-up, INSIDE the figure edge "
            f"(reach={reach:.2f}); it must clear the top edge so the upward block does not overlap"
        )
    if up_amt < reach * 1.1:
        failures.append(f"GEOMETRY: legend anchor clears the figure edge by <10% margin (up={up_amt:.2f})")
    if float(np.dot(rel, sright)) <= 0.0:
        failures.append("GEOMETRY: legend anchor lost its rightward bias")
    normal_off = float(np.dot(rel, normal))
    if not (0.0 < normal_off < reach * 0.1):
        failures.append(f"GEOMETRY: legend anchor normal standoff {normal_off:.3f} not a small positive lift")

    # Tilted (3/4-camera) basis: the clear-the-edge invariant must still hold.
    tright, tup, tnormal = _orthonormal_tilt()
    tanchor = np.asarray(anchor_fn(center, tnormal, tright, tup, reach), dtype=float)
    if float(np.dot(tanchor - center, tup)) < reach:
        failures.append("GEOMETRY: under a tilted camera basis the anchor no longer clears the figure edge")

    # Fallback (no screen axes resolved): must still lift the block above centre along world +Y.
    fallback = np.asarray(anchor_fn(center, normal, None, None, reach), dtype=float)
    if float((fallback - center)[1]) < reach:
        failures.append("GEOMETRY: the no-screen-axes fallback anchor does not clear the figure edge")

    # Degenerate reach must not crash / must stay finite and above centre.
    for bad in (0.0, -3.0, float("nan")):
        got = np.asarray(anchor_fn(center, normal, sright, sup, bad), dtype=float)
        if not np.all(np.isfinite(got)) or float(np.dot(got - center, sup)) <= 0.0:
            failures.append(f"GEOMETRY: degenerate reach {bad!r} produced a bad anchor {got.tolist()}")


def _check_wiring(failures: list[str]) -> None:
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    try:
        draw_src = inspect.getsource(Kraken3DInspector._add_grouped_analysis_overlay_label)
    except Exception as exc:  # pragma: no cover - defensive
        draw_src = ""
        failures.append(f"WIRING: could not read _add_grouped_analysis_overlay_label source ({exc!r})")
    if "_analysis_overlay_label_anchor" not in draw_src:
        failures.append("WIRING: the grouped label must anchor via _analysis_overlay_label_anchor")
    if "SetVerticalJustificationToBottom" not in draw_src:
        failures.append(
            "WIRING: the grouped label must be BOTTOM justified so the block grows upward (away from the "
            "figure), not downward over it"
        )
    if "SetVerticalJustificationToTop" in draw_src:
        failures.append("WIRING: the grouped label still forces TOP justification (block would grow into the figure)")


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    _check_geometry(failures)
    _check_wiring(failures)
    notes = list(failures)
    if not failures:
        notes.append("legend anchors above the figure edge and grows upward (no figure overlap)")
    return (not failures), notes


def main() -> int:
    passed, messages = run_checks()
    for message in messages:
        print(("OK   " if passed else "FAIL ") + message)
    if not passed:
        print("[FAIL] analysis-overlay label placement")
        return 1
    print("[PASS] analysis-overlay label placement (legend clears the figure)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
