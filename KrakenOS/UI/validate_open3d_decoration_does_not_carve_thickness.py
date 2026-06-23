"""Guard for bugs/0122 -- a DECORATION STEP overlay (LED illuminator / camera
body) must NOT carve an optical thickness dimension; only real optical bodies
(lens / beam splitter) may.

Regression context
------------------
An in-line LED illuminator placed in front of the lens straddles the optical
axis and sits inside the object->lens working-distance span (S0). The bugs/0009
overlay-carve therefore shortened the S0 arrow to END at the LED's object-side
face (object->LED ~= 200 mm), but because the carve left a SINGLE remaining gap
the label branch fell through to the full row thickness ("S0 Thickness = 275
mm"). So the drawn arrow pointed object->LED yet read 275 -- the user, who had
typed an LED edge distance of 200 mm, saw "the object->LED gap is 275 mm".

The LED is an independent decoration (a visual prop), not an optical element in
the beam path, so it must not carve the working-distance dimension at all. After
the fix S0 spans the full object->lens distance and its 275 mm label matches the
arrow length; the prop simply sits in the path. (The LED-in-front-of-lens
coupling and the BS<->LED glue are separate, later stages.)

This guard is display-free: it drives the REAL `_overlay_axial_spans_within`
and the static `split_span_at_overlays` off the service class against a fake
inspector whose `_axial_extent_from_actor_keys` returns canned extents. No VTK /
embedded window is needed.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_decoration_does_not_carve_thickness

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect

import numpy as np


def _extent(proj_min, proj_max, *, straddles=True, axis=(0.0, 0.0, 1.0)):
    axis = np.asarray(axis, dtype=float)
    center = 0.5 * (float(proj_min) + float(proj_max))
    return {
        "axis": axis,
        "proj_min": float(proj_min),
        "proj_max": float(proj_max),
        "proj_center": float(center),
        "centroid": np.array([0.0, 0.0, center], dtype=float),
        "straddles_axis": bool(straddles),
    }


class _FakeInspector:
    """Minimal surface for `_overlay_axial_spans_within`: a label->actor-keys map
    and a canned `_axial_extent_from_actor_keys`."""

    def __init__(self, extents: dict) -> None:
        self._extents = dict(extents)
        self._step_actor_map = {label: [f"k_{label}"] for label in extents}

    def _axial_extent_from_actor_keys(self, actor_keys, axis_unit):
        key = list(actor_keys or [])[0] if actor_keys else None
        if key is None:
            return None
        label = str(key)[2:]  # strip "k_"
        return self._extents.get(label)


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    passed = True

    from KrakenOS.UI.services.open3d_thickness_dimensions import Open3DThicknessDimensionService

    svc = Open3DThicknessDimensionService.__new__(Open3DThicknessDimensionService)
    axis = np.array([0.0, 0.0, 1.0], dtype=float)
    a0, a1 = 0.0, 275.0  # object plane -> lens front (the S0 working distance)

    # An in-line LED prop straddling the axis, ending just past the lens front.
    led_extent = _extent(200.0, 276.4)
    # A real beam-splitter body in the path (must still carve).
    bs_extent = _extent(120.0, 170.0)

    # A. A decoration LED alone must NOT carve S0 -> one full uncarved span, so
    #    the "S0 Thickness = 275" label matches the full-length arrow.
    svc.inspector = _FakeInspector({"led": led_extent})
    spans = svc._overlay_axial_spans_within(axis, a0, a1)
    if spans:
        notes.append(f"FAIL: decoration LED carved S0 (spans={spans}); a prop must not carve")
        passed = False
    gaps = Open3DThicknessDimensionService.split_span_at_overlays(a0, a1, spans)
    if gaps != [(a0, a1)]:
        notes.append(f"FAIL: LED-only S0 should be one full span {[(a0, a1)]}, got {gaps}")
        passed = False
    # The bug was a 200 mm arrow wearing a 275 mm label. Pin that the single
    # remaining gap now equals the full row span (label length == arrow length).
    if len(gaps) == 1 and abs((gaps[0][1] - gaps[0][0]) - (a1 - a0)) > 1e-6:
        notes.append(
            f"FAIL: single S0 gap {gaps[0]} != full span {(a0, a1)} -- a shortened arrow "
            "would still wear the full-thickness label (the bugs/0122 mislabel)"
        )
        passed = False

    # B. The camera body (the other decoration) must not carve either.
    svc.inspector = _FakeInspector({"camera": _extent(150.0, 210.0)})
    if svc._overlay_axial_spans_within(axis, a0, a1):
        notes.append("FAIL: camera decoration carved S0; a prop must not carve")
        passed = False

    # C. A real optical beam-splitter body MUST still carve (bugs/0009 preserved).
    svc.inspector = _FakeInspector({"optical": bs_extent})
    spans = svc._overlay_axial_spans_within(axis, a0, a1)
    if not spans:
        notes.append("FAIL: an optical beam-splitter body must still carve the dimension")
        passed = False
    gaps = Open3DThicknessDimensionService.split_span_at_overlays(a0, a1, spans)
    if len(gaps) < 2:
        notes.append(f"FAIL: an optical body should split S0 into two gaps, got {gaps}")
        passed = False

    # D. LED + BS together: only the BS carves; no span reaches the LED region.
    svc.inspector = _FakeInspector({"led": led_extent, "optical": bs_extent})
    spans = svc._overlay_axial_spans_within(axis, a0, a1)
    if not spans:
        notes.append("FAIL: with LED+BS the BS must still carve")
        passed = False
    elif any(float(pmax) > 171.0 for _pmin, pmax in spans):
        notes.append(f"FAIL: a carve span reached the LED region (spans={spans}); only the BS should carve")
        passed = False

    # E. Source contract: the decoration skip is present and uses the shared helper.
    try:
        src = inspect.getsource(Open3DThicknessDimensionService._overlay_axial_spans_within)
    except Exception as exc:
        notes.append(f"FAIL: cannot read _overlay_axial_spans_within source: {exc!r}")
        return False, notes
    if "is_step_overlay_decoration" not in src:
        notes.append(
            "FAIL: _overlay_axial_spans_within no longer consults is_step_overlay_decoration "
            "(a decoration overlay could carve an optical thickness dimension again)"
        )
        passed = False

    if verbose:
        for note in notes:
            print(note)
        print("PASS" if passed else "FAIL")
    return passed, notes


if __name__ == "__main__":
    import sys

    ok, msgs = run_checks(verbose=True)
    if not ok:
        for m in msgs:
            print(m)
    sys.exit(0 if ok else 1)
