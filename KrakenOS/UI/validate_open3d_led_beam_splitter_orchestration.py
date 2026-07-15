#!/usr/bin/env python3
"""Display-free guard for bugs/0319 C3 -- the "Add Beam Splitter to LED" pipeline.

The one-click command generates a parametric BS (cube/plate), overlays it on the
imported LED STEP, centres it on the LED clear-aperture *opening*, glues it to the
LED, promotes it to a non-sequential optical solid, and auto-flags the 45-degree
diagonal as the BS coating.  The *visual* placement on a real LED is eyeball-owed
(no GLX render here); what this guard nails down is the **orchestration wiring** --
that every pipeline step fires, in order, with the right arguments -- using a spy
editor so no display, OCC, or STEP is required.

What it checks
--------------
  A. Full pipeline order + args: generate -> import(path=) -> set CA(led, opening) ->
     centre CA(led) -> place BS at the opening's on-axis centre -> glue(True) ->
     promote(optical, clear_overlay=True) -> auto-flag the diagonal coating; the BS is
     sized to the opening span; the returned summary carries the row + coating face.
  B. The coating picker grabs the largest ~45-degree face and ignores axis-aligned
     housing faces (so a plain box or a mis-picked face is never flagged).
  C. Graceful stops: an unknown kind and a missing LED both return None with a status
     line, never a half-built scene.
  D. ``_step_analytic_face_inplane_span`` returns the opening's smaller in-plane span
     from an analytic face bbox (the size a BS is cloned to).
  E. The PUBLIC ``import_optical_step`` wrapper accepts and forwards the ``path=``
     bypass the pipeline overlays the BS through -- a regression here dies with a
     TypeError before anything is placed (the spy in A can't catch it because it
     stubs the call; this exercises the real ScenePlacementMixin wrapper).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_led_beam_splitter_orchestration

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np

from KrakenOS.UI import optical_solid_metadata
from KrakenOS.UI.services import scene_placement_commands as spc
from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin

_SPLITTER = optical_solid_metadata.OPTICAL_SOLID_FACE_FUNCTION_UI_LABEL_SPLITTER  # "Partial Reflecting / Transmitting"


class _SpyEditor:
    """A minimal stand-in that records the pipeline collaborators the real
    orchestration calls, so we can assert the wiring without a live editor."""

    # The three real methods under test (bound to the spy instance).
    add_beam_splitter_to_led = ScenePlacementMixin.add_beam_splitter_to_led
    _led_beam_splitter_opening_plan = ScenePlacementMixin._led_beam_splitter_opening_plan
    _flag_beam_splitter_coating_face = ScenePlacementMixin._flag_beam_splitter_coating_face

    def __init__(self, *, led_present=True, opening_face_index=112,
                 opening_centroid=(7.3, -1.3, 36.5), opening_span=55.0,
                 auto_candidates=True, promoted_faces=None):
        self.calls: list[tuple] = []
        self.status_messages: list[str] = []
        self.status_var = SimpleNamespace(set=self.status_messages.append)
        self._led_present = bool(led_present)
        self._opening_face_index = int(opening_face_index)
        self._opening_centroid = np.asarray(opening_centroid, dtype=float)
        self._opening_span = float(opening_span)
        self._auto_candidates = bool(auto_candidates)
        self._promoted_faces = promoted_faces if promoted_faces is not None else _default_promoted_faces()

    # --- leaf collaborators (stubs) ---------------------------------------
    def _step_path_for_label(self, label):
        if str(label).strip().lower() == "led" and self._led_present:
            return Path("attachment/LED/OPT-CO90-X-V1.6.2-H.STEP")
        return None

    def auto_detect_step_clear_aperture_candidates(self, label):
        if str(label).strip().lower() == "led" and self._auto_candidates:
            return [SimpleNamespace(face_index=self._opening_face_index,
                                    span_mm=(self._opening_span, self._opening_span),
                                    area_mm2=462.0, score=0.93)]
        return []

    def step_clear_aperture(self, label):
        return None

    def _step_overlay_fine_face_centroid_normal(self, label, face_index):
        if int(face_index) == self._opening_face_index:
            return self._opening_centroid.copy(), np.asarray((0.0, 0.0, -1.0)), 462.0
        return None

    def _step_analytic_face_inplane_span(self, label, face_index):
        return self._opening_span

    def import_optical_step(self, dialog_parent=None, *, path=None, refresh_open_3d=True):
        self.calls.append(("import_optical_step", {"path": path, "refresh_open_3d": refresh_open_3d}))
        return Path(path) if path is not None else None

    def set_step_clear_aperture(self, label, face_index):
        self.calls.append(("set_step_clear_aperture", {"label": label, "face_index": int(face_index)}))
        return {"face_index": int(face_index)}

    def center_clear_aperture_on_optical_axis(self, label):
        self.calls.append(("center_clear_aperture_on_optical_axis", {"label": label}))
        return {"label": label}

    def _set_step_placement_offset_xyz(self, label, offset_xyz):
        self.calls.append(("_set_step_placement_offset_xyz",
                           {"label": label, "offset": tuple(float(v) for v in offset_xyz)}))

    def set_optical_led_glue(self, glued):
        self.calls.append(("set_optical_led_glue", {"glued": bool(glued)}))
        return True

    def promote_imported_step_to_optical_solid_row(self, label, *, insert_at=None, open_face_editor=True,
                                                   clear_overlay=False, refresh_open_3d=True,
                                                   inpath_axial_placement=False):
        self.calls.append(("promote", {"label": label, "open_face_editor": open_face_editor,
                                        "clear_overlay": clear_overlay, "refresh_open_3d": refresh_open_3d}))
        return {"label": label, "row_index": 5}

    def _optical_solid_face_metadata_for_row(self, row_index):
        return None, Path("promoted.stl"), {"faces": list(self._promoted_faces)}

    def assign_optical_solid_face_function(self, row_index, face_id, function_label):
        self.calls.append(("assign_face", {"row_index": int(row_index), "face_id": str(face_id),
                                            "function_label": str(function_label)}))
        return {"row_index": int(row_index), "face_id": str(face_id), "function": "Beam Splitter"}

    def _refresh_open_3d_views(self, *args, **kwargs):
        self.calls.append(("_refresh_open_3d_views", {}))

    # --- helpers ----------------------------------------------------------
    def call_names(self):
        return [name for name, _ in self.calls]

    def first(self, name):
        for n, payload in self.calls:
            if n == name:
                return payload
        return None


def _default_promoted_faces():
    """A cube's promoted faces: 4 axis-aligned housing faces + 1 big 45-degree
    diagonal (the coating) + a small 45-degree sliver (must lose to the big one)."""
    axis = (0.0, 0.0, 1.0)
    diag = (1.0, 0.0, -1.0)  # 45 degrees to +Z
    return [
        {"face_id": "F1", "normal": axis, "area_mm2": 3080.0},
        {"face_id": "F2", "normal": (1.0, 0.0, 0.0), "area_mm2": 3080.0},
        {"face_id": "F3", "normal": (0.0, 1.0, 0.0), "area_mm2": 3080.0},
        {"face_id": "F4", "normal": (0.0, 0.0, -1.0), "area_mm2": 3080.0},
        {"face_id": "DIAG_BIG", "normal": diag, "area_mm2": 4350.0},
        {"face_id": "DIAG_SLIVER", "normal": diag, "area_mm2": 12.0},
    ]


def _fake_generate(kind, *, force=False, **dimensions):
    """Stand in for the real OCC BS generator (verified separately in phase 281)."""
    if kind == "cube":
        params = {"side_mm": float(dimensions["side_mm"])}
    else:
        params = {k: float(v) for k, v in dimensions.items()}
    return SimpleNamespace(
        path=Path(f"attachment/cad_cache/beam_splitter_templates/bs_{kind}_spy.step"),
        kind=kind,
        params=params,
        coating_normal=(1.0, 0.0, -1.0),
        coating_tilt_deg=45.0,
    )


def _check_pipeline(failures: list[str], notes: list[str]) -> None:
    original = spc.generate_beam_splitter
    spc.generate_beam_splitter = _fake_generate
    try:
        ed = _SpyEditor(opening_centroid=(7.3, -1.3, 36.5), opening_span=55.0)
        result = ed.add_beam_splitter_to_led("cube")
    finally:
        spc.generate_beam_splitter = original

    if result is None:
        failures.append("FAIL(A): add_beam_splitter_to_led returned None on a valid LED scene")
        return

    order = ed.call_names()
    expected = [
        "import_optical_step",
        "set_step_clear_aperture",
        "center_clear_aperture_on_optical_axis",
        "_set_step_placement_offset_xyz",
        "set_optical_led_glue",
        "promote",
        "assign_face",
        "_refresh_open_3d_views",
    ]
    pruned = [name for name in order if name in set(expected)]
    if pruned != expected:
        failures.append(f"FAIL(A): pipeline call order wrong.\n    expected {expected}\n    got      {pruned}")

    imp = ed.first("import_optical_step") or {}
    if Path(imp.get("path", "")).name != "bs_cube_spy.step":
        failures.append(f"FAIL(A): BS not overlaid via import_optical_step(path=), got {imp.get('path')!r}")
    if imp.get("refresh_open_3d", True) is not False:
        failures.append("FAIL(A): the BS import should defer the 3D refresh (refresh_open_3d=False)")

    ca = ed.first("set_step_clear_aperture") or {}
    if (ca.get("label"), ca.get("face_index")) != ("led", 112):
        failures.append(f"FAIL(A): clear aperture should be set on (led, 112), got {ca}")

    offset = ed.first("_set_step_placement_offset_xyz") or {}
    if offset.get("label") != "optical":
        failures.append(f"FAIL(A): the BS ('optical') offset should be set, got label {offset.get('label')!r}")
    got_off = offset.get("offset", (None, None, None))
    if not (abs(got_off[0]) < 1e-9 and abs(got_off[1]) < 1e-9 and abs(got_off[2] - 36.5) < 1e-6):
        failures.append(f"FAIL(A): BS should centre on the on-axis opening (0,0,36.5), got {got_off}")

    glue = ed.first("set_optical_led_glue") or {}
    if glue.get("glued") is not True:
        failures.append("FAIL(A): the BS must be glued to the LED (set_optical_led_glue(True))")

    promo = ed.first("promote") or {}
    if promo.get("label") != "optical" or promo.get("clear_overlay") is not True:
        failures.append(f"FAIL(A): promote should consume the 'optical' overlay (clear_overlay=True), got {promo}")

    assign = ed.first("assign_face") or {}
    if assign.get("row_index") != 5 or assign.get("function_label") != _SPLITTER:
        failures.append(f"FAIL(A): coating flag should mark row 5 as '{_SPLITTER}', got {assign}")
    if assign.get("face_id") != "DIAG_BIG":
        failures.append(f"FAIL(A): coating should land on the big 45-degree diagonal, got {assign.get('face_id')!r}")

    if abs(float(result.get("side_mm", 0.0)) - 55.0) > 1e-6:
        failures.append(f"FAIL(A): BS should be sized to the opening span 55, got {result.get('side_mm')}")
    if result.get("coating_face") != "DIAG_BIG" or result.get("row_index") != 5:
        failures.append(f"FAIL(A): summary should report row 5 + coating DIAG_BIG, got {result}")

    notes.append(
        f"pipeline: {'->'.join(pruned)}; side={result.get('side_mm')}mm coating={result.get('coating_face')}"
    )


def _check_coating_picker(failures: list[str]) -> None:
    ed = _SpyEditor()
    # No ~45-degree face -> nothing flagged (a plain box must never be coated).
    box_faces = [
        {"face_id": "A", "normal": (0.0, 0.0, 1.0), "area_mm2": 100.0},
        {"face_id": "B", "normal": (1.0, 0.0, 0.0), "area_mm2": 100.0},
    ]
    box_ed = _SpyEditor(promoted_faces=box_faces)
    if box_ed._flag_beam_splitter_coating_face(5) is not None:
        failures.append("FAIL(B): a box with no 45-degree face must not be coated")
    if any(name == "assign_face" for name, _ in box_ed.calls):
        failures.append("FAIL(B): no face-function assignment should fire on a box with no diagonal")

    # With a diagonal, the biggest ~45-degree face wins over the sliver.
    picked = ed._flag_beam_splitter_coating_face(5)
    if not (isinstance(picked, dict) and picked.get("face_id") == "DIAG_BIG"):
        failures.append(f"FAIL(B): coating picker should choose DIAG_BIG, got {picked}")


def _check_graceful_stops(failures: list[str]) -> None:
    ed = _SpyEditor()
    if ed.add_beam_splitter_to_led("sphere") is not None:
        failures.append("FAIL(C): an unknown BS kind must return None")
    if not any("unknown kind" in m for m in ed.status_messages):
        failures.append("FAIL(C): an unknown kind should set an explanatory status line")

    no_led = _SpyEditor(led_present=False)
    if no_led.add_beam_splitter_to_led("cube") is not None:
        failures.append("FAIL(C): a missing LED must return None")
    if not any("import the LED" in m for m in no_led.status_messages):
        failures.append("FAIL(C): a missing LED should ask the user to import the LED")

    no_open = _SpyEditor(auto_candidates=False)
    if no_open.add_beam_splitter_to_led("cube") is not None:
        failures.append("FAIL(C): no detectable opening (and no manual pick) must return None")
    if not any("clear-aperture opening" in m for m in no_open.status_messages):
        failures.append("FAIL(C): no opening should point the user at the manual clear-aperture pick")


def _check_span(failures: list[str]) -> None:
    class _Doc:
        pass

    # bbox = (min xyz, max xyz): thin along Z (0.5), 40 x 55 in-plane -> span_a = 40.
    face = SimpleNamespace(bbox=(-20.0, -27.5, 10.0, 20.0, 27.5, 10.5))
    doc = _Doc()
    doc.outer_faces = [SimpleNamespace(bbox=(0, 0, 0, 1, 1, 1))] * 7 + [face]

    class _SpanEditor:
        _step_analytic_face_inplane_span = ScenePlacementMixin._step_analytic_face_inplane_span

        def _step_path_for_label(self, label):
            return Path("x.step")

        def _load_step_analytic_document(self, path):
            return doc

    span = _SpanEditor()._step_analytic_face_inplane_span("led", 7)
    if span is None or abs(float(span) - 40.0) > 1e-6:
        failures.append(f"FAIL(D): in-plane span should be the smaller face extent 40, got {span}")


def _check_import_bypass_forwarding(failures: list[str], notes: list[str]) -> None:
    """The one-click pipeline overlays the BS via ``import_optical_step(path=...)``.
    The PUBLIC editor method is the ScenePlacementMixin *wrapper*, which delegates to
    the overlay-import service -- so the wrapper must both accept ``path=`` AND forward
    it. It once forwarded ``refresh_open_3d`` but dropped ``path``, so the real command
    died with "unexpected keyword argument 'path'" before it overlaid or promoted
    anything (the A spy can't see this -- it stubs the call). Exercise the real wrapper
    through a fake service and prove the bypass reaches it."""
    recorded: dict = {}

    class _FakeService:
        def import_optical_step(self, dialog_parent=None, *, path=None, refresh_open_3d=True):
            recorded["path"] = path
            recorded["refresh_open_3d"] = refresh_open_3d
            return path

    class _WrapperEditor:
        import_optical_step = ScenePlacementMixin.import_optical_step

        def _step_overlay_import_service(self):
            return _FakeService()

    try:
        out = _WrapperEditor().import_optical_step(path="bs.step", refresh_open_3d=False)
    except TypeError as exc:
        failures.append(f"FAIL(E): import_optical_step rejects the path= bypass: {exc}")
        return
    if recorded.get("path") != "bs.step" or out != "bs.step":
        failures.append(f"FAIL(E): import_optical_step(path=) is not forwarded to the service; got {recorded!r}")
    if recorded.get("refresh_open_3d") is not False:
        failures.append("FAIL(E): import_optical_step should forward refresh_open_3d to the service")
    if not failures:
        notes.append("import_optical_step(path=) bypass reaches the overlay-import service")


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    _check_pipeline(failures, notes)
    _check_coating_picker(failures)
    _check_graceful_stops(failures)
    _check_span(failures)
    _check_import_bypass_forwarding(failures, notes)
    return (not failures), failures + notes


def main() -> int:
    passed, notes = run_checks()
    hard = [n for n in notes if n.startswith("FAIL")]
    soft = [n for n in notes if not n.startswith("FAIL")]
    if hard:
        print("[FAIL] LED beam-splitter orchestration (bugs/0319 C3)")
        for item in hard:
            print(f"  - {item}")
        return 1
    print("[PASS] Add Beam Splitter to LED: pipeline sequences generate->overlay->centre->"
          "glue->promote->coat; sizes to the opening; coats the diagonal; stops gracefully")
    for item in soft:
        print(f"  - {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
