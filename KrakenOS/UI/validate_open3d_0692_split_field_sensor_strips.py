"""Guard for bugs/0692 -- split-field scenes: circles stand down, cover strips draw.

flag_20260902_103541 ("big green circle in A object plane" + broken "Image circle
O0.5 / Needs O32.6" family) + the user's follow-up request ("draw 2 dotted line
edge at the Sensor to indicate actual cover area"):

  1. The Quick-Estimation overlay's single-axis FOV/image circles are the WRONG
     MODEL for a split-field scene (each face sees a one-sided band through its
     own arm) -- when `object_fov_bands` are authored the QE overlay stands down
     entirely (before even reading QE state).
  2. The detector-coverage overlay suppresses its circle-kind line specs and the
     "Image circle"/"Needs"/"FOV WxH" labels under bands -- the Ø0.5 collapsed
     metric drew nonsense rings on the seated scene.
  3. Each band may AUTHOR its MEASURED `image_strip` (world center on the sensor
     plane, in-plane `axis_v`, `v_lo`/`v_hi`, `half_width`); the overlay draws the
     two dashed edge lines per strip + the band name, against the kept sensor
     square. Numbers measured by bugs/0692_sensor_reach_sweep.py.

Checks (display-free -- recording subclasses, no VTK):
  A  QE gate: bands present -> add_overlays returns 0 WITHOUT reading QE state;
     bands absent -> QE state IS read.
  B  band normalizer: a valid image_strip is kept (axis_v normalized); an
     inverted/malformed strip is dropped while its band survives.
  C  coverage add_overlays on a stubbed split-field scene: no circle polyline,
     no circle/Needs/FOV labels, the sensor rectangle survives, and exactly four
     dashed strip-edge lines land at the authored sensor-plane offsets.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0692_split_field_sensor_strips
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np


class _StubEditor:
    def __init__(self, bands):
        self.layout_object_fov_bands = bands
        row = SimpleNamespace(tilt_x=0.0, tilt_y=0.0, tilt_z=0.0)
        self.rows = [row, SimpleNamespace(), SimpleNamespace()]
        self.debug = []

    def append_debug(self, msg):
        self.debug.append(str(msg))

    def _surface_reference_world_point(self, index, system=None):
        if index == 0:
            return np.array((0.0, 0.0, 0.0))
        return np.array((-272.65, -9.9, -25.0))


BANDS = [
    {"name": "Face A field", "center": [0.0, 0.0, 0.0], "axis": [0.0, 0.0, 1.0],
     "half_width": 27.5, "v_lo": -5.25, "v_hi": 3.1,
     "image_strip": {"center": [-272.65, -9.9, -25.0], "axis_v": [0.0, 0.0, 2.0],
                     "half_width": 11.52, "v_lo": -5.3, "v_hi": -2.1}},
    {"name": "Face B field", "center": [0.0, 0.0, -50.0], "axis": [0.0, 0.0, 1.0],
     "half_width": 27.5, "v_lo": -5.25, "v_hi": 3.1,
     "image_strip": {"center": [-272.65, -9.9, -25.0], "axis_v": [0.0, 0.0, 1.0],
                     "half_width": 11.52, "v_lo": 2.2, "v_hi": 6.8}},
]


def _check_qe_gate(ok, notes) -> None:
    from KrakenOS.UI.services.quick_estimation_overlay import QuickEstimationOverlayService

    for bands, expect_state_read in ((list(BANDS), False), (None, True)):
        calls = []

        class _QE:
            def is_enabled(self):
                return True

            def current_state(self):
                calls.append("state")
                return {"object_mode": "Finite"}  # mag None -> harmless late return

        editor = _StubEditor(bands)
        inspector = SimpleNamespace(editor=editor, _quick_estimation_service=lambda: _QE(),
                                    _renderer=None)
        svc = QuickEstimationOverlayService(inspector, pv_module=None)
        count = svc.add_overlays(system=None)
        if expect_state_read:
            ok(bool(calls) and count == 0,
               f"A: without bands the QE overlay proceeds to its state ({len(calls)} reads)")
        else:
            ok(not calls and count == 0,
               f"A: with authored bands the QE overlay stands down BEFORE reading state "
               f"({len(calls)} reads, count {count})")


class _RecordingCoverage:
    """Mixed into the real service: record draw calls instead of rendering."""

    def __init__(self, inspector):
        from KrakenOS.UI.services.detector_coverage_overlay import DetectorCoverageOverlayService

        self._svc = DetectorCoverageOverlayService(inspector, pv_module=None)
        self._svc.lines = []
        self._svc.labels = []
        svc = self._svc
        svc._line_actor = lambda points, color, width, dashed: (
            svc.lines.append((np.asarray(points, dtype=float), bool(dashed))) or True)
        svc.label_anchors = []
        svc._label_actor = lambda anchor, text, color: (
            svc.labels.append(str(text))
            or svc.label_anchors.append((str(text), np.asarray(anchor, dtype=float).reshape(3)))
            or True)
        svc._pick_fill_actor = lambda *a, **k: True
        svc._arrow_cone = lambda *a, **k: True
        svc._sensor_dimensions = lambda target: (23.04, 23.04)
        svc._target_has_real_sensor = lambda target: True
        svc._image_circle_radius = lambda: 0.5      # the degenerate seated-scene metric
        svc._magnification = lambda: 0.4066
        svc._is_finite_object = lambda: True


def _check_normalizer(ok, notes) -> None:
    from KrakenOS.UI.services.detector_coverage_overlay import DetectorCoverageOverlayService

    bad = [dict(BANDS[0]), dict(BANDS[1])]
    bad[1] = dict(bad[1])
    bad[1]["image_strip"] = {"center": [0, 0, 0], "axis_v": [0, 0, 1],
                             "half_width": 11.52, "v_lo": 5.0, "v_hi": 2.0}  # inverted
    editor = _StubEditor(bad)
    svc = DetectorCoverageOverlayService(SimpleNamespace(editor=editor), pv_module=None)
    bands = svc._normalized_object_fov_bands()
    strip0 = (bands[0] if bands else {}).get("image_strip")
    ok(
        len(bands) == 2
        and strip0 is not None
        and abs(float(np.linalg.norm(strip0["axis_v"])) - 1.0) < 1e-9
        and bands[1].get("image_strip") is None,
        f"B: normalizer keeps a valid image_strip (axis_v unit) and drops an inverted one "
        f"({len(bands)} bands, strip0 {strip0 is not None}, strip1 {bands[1].get('image_strip') is not None if len(bands) > 1 else '?'})",
    )


def _check_coverage_draw(ok, notes) -> None:
    editor = _StubEditor(list(BANDS))
    rec = _RecordingCoverage(SimpleNamespace(editor=editor))
    svc = rec._svc
    target = SimpleNamespace(
        is_detector=True, metadata={},
        center_world=np.array((-272.65, -9.9, -25.0)),
        normal_world=np.array((0.0, 1.0, 0.0)),
    )
    bundle = SimpleNamespace(targets=[target])
    svc.add_overlays(system=None, scene_bundle=bundle)

    circles = [pts for pts, _d in svc.lines if pts.shape[0] >= 30]
    strip_edges = [
        pts for pts, dashed in svc.lines
        if dashed and pts.shape[0] == 2 and np.allclose(pts[:, 1], -9.9, atol=0.2)
    ]
    edge_zs = sorted(round(float(np.mean(pts[:, 2])), 1) for pts in strip_edges)
    # bugs/0697: strip v offsets ride the LIVE detector's own in-plane basis (iv),
    # not the authored axis_v -- for normal (0,1,0) the shared _basis gives
    # iv = (0,0,-1), so an authored v maps to sensor z = center_z - v. (This stub
    # expectation had kept the pre-0697 +z mapping and failed at HEAD; scenes are
    # stamped in the detector frame, bugs/0692_stamp_strips.)
    want_zs = sorted([-25.0 + 5.3, -25.0 + 2.1, -25.0 - 2.2, -25.0 - 6.8])
    forbidden = [t for t in svc.labels
                 if "circle" in t.lower() or t.startswith("Needs")]
    names = [t for t in svc.labels if t in ("Face A field", "Face B field")]
    fov_labels = [(t, a) for t, a in svc.label_anchors if t.startswith("FOV ")]

    ok(not circles, f"C1: no circle polyline drawn under bands ({len(circles)} found)")
    # The REAL sensor square is the detector-footprint actor's job (a different
    # subsystem, untouched). Prove the suppression is scoped to CIRCLES: a bare
    # lens still gets its recommended inscribed-sensor rect under bands.
    editor2 = _StubEditor(list(BANDS))
    rec2 = _RecordingCoverage(SimpleNamespace(editor=editor2))
    svc2 = rec2._svc
    svc2._target_has_real_sensor = lambda target: False
    svc2.add_overlays(system=None, scene_bundle=SimpleNamespace(targets=[target]))
    rects2 = [pts for pts, _d in svc2.lines
              if pts.shape[0] == 5 and np.allclose(pts[:, 1], -9.9, atol=0.2)]
    ok(bool(rects2),
       f"C2: bare-lens recommended sensor rect still draws under bands ({len(rects2)} rects)")
    ok(
        len(strip_edges) == 4 and all(abs(a - b) < 0.15 for a, b in zip(edge_zs, want_zs)),
        f"C3: four dashed cover-strip edges at the authored sensor-plane offsets "
        f"({len(strip_edges)} edges at z {edge_zs}, want {[round(w, 1) for w in want_zs]})",
    )
    ok(not forbidden, f"C4: no Image-circle/Needs labels under bands ({forbidden[:3]})")
    ok(len(names) >= 2, f"C5: the band names label faces AND strips ({len(names)} name labels)")
    # bugs/0701 (flag 091545 "put in FOV values above the green object plane for each
    # A and B side"): each band now carries its own "FOV WxH" readout, anchored past
    # the band's -Y edge (above the plane, away from the prism towers). The old
    # single-axis full-FOV label stays suppressed -- these are the per-band values.
    want_text = f"FOV {2 * 27.5:.1f}×{3.1 - (-5.25):.1f}"
    texts_ok = len(fov_labels) == 2 and all(t == want_text for t, _a in fov_labels)
    band_top_y = -5.25  # v_lo: the band's -Y edge (b_u = +Y for a z-facing band)
    anchors_ok = (
        len(fov_labels) == 2
        and all(float(a[1]) < band_top_y - 0.5 for _t, a in fov_labels)
        and sorted(round(float(a[2]), 1) for _t, a in fov_labels) == [-50.0, 0.0]
    )
    ok(
        texts_ok,
        f"C6: one per-band FOV value label per face, band-sized "
        f"({[t for t, _a in fov_labels]}, want 2x {want_text!r})",
    )
    ok(
        anchors_ok,
        f"C7: FOV labels anchor ABOVE each band (-Y past the edge) at both faces "
        f"({[(round(float(a[1]), 1), round(float(a[2]), 1)) for _t, a in fov_labels]})",
    )


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    for check in (_check_qe_gate, _check_normalizer, _check_coverage_draw):
        try:
            check(ok, notes)
        except Exception as exc:
            notes.append(f"FAIL: {check.__name__} raised {type(exc).__name__}: {exc}")
    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("split-field sensor-strip validation PASSED")
        return 0
    print("split-field sensor-strip validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
