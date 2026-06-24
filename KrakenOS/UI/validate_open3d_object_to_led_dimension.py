"""Guard for bugs/0123 + bugs/0125 -- a dedicated, clickable object->LED-edge
thickness overlay in Open 3D that tracks the LED's LIVE edge.

Feature
-------
After bugs/0122 made the optical S0 arrow a clean object->lens working distance,
the user still needs a SEPARATE object->LED-edge dimension (the LED is an
independent decoration). It is drawn amber from the object plane to the LED edge
at the distance the LED edge-distance dialog sets, and a plain click on it
re-opens that dialog (which MOVES the LED). It carries a SENTINEL row id so it
stays out of the table-row dimension dispatch, and registers NO drag yet (the
drag-to-re-anchor "re-measure to a different LED edge, LED stays put" is a later
increment).

bugs/0125: the dialog pins the chosen LED edge at object+distance, but a free
carry-drag of the LED adds led_step_placement_offset_xyz on top WITHOUT updating
led_object_edge_distance_mm. The arrow used to stay frozen at the typed value
while the dragged LED moved away (flag_20260624_075900_372). The overlay now
measures the LIVE object->edge distance = typed distance + placement_offset_z, so
the arrow + label follow the LED and still equal the typed value when undragged.

This guard is display-free: it drives the real `_emit_led_object_edge_dimension`
with `_emit_span_dimension` monkeypatched to capture the emitted geometry, and
checks the `edit_dimension` sentinel routing. No VTK / embedded window is needed.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_object_to_led_dimension

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect

import numpy as np


class _FakeStatus:
    def __init__(self) -> None:
        self.value = None

    def set(self, text) -> None:
        self.value = text


class _FakeEditor:
    def __init__(
        self, *, led: bool = True, distance: float = 191.7, led_offset_z: float = 0.0
    ) -> None:
        self.imported_led_step_path = "led.step" if led else None
        self.led_object_edge_distance_mm = float(distance)
        # bugs/0125: a free carry-drag of the LED records its axial slide here; the
        # live overlay reads it so the arrow tracks the dragged edge.
        self.led_step_placement_offset_xyz = (0.0, 0.0, float(led_offset_z))
        self.rows = [object(), object(), object()]  # >= 2 rows
        self.led_dialog_calls = 0

    def _surface_reference_world_point(self, idx, system=None):
        return (0.0, 0.0, 0.0)  # object plane at the origin

    def _step_placement_offset_xyz(self, label):
        value = getattr(self, f"{label}_step_placement_offset_xyz", (0.0, 0.0, 0.0))
        return (float(value[0]), float(value[1]), float(value[2]))

    def set_led_edge_distance(self) -> None:
        self.led_dialog_calls += 1


class _FakeInspector:
    def __init__(self) -> None:
        self.status_var = _FakeStatus()


def _service(editor):
    from KrakenOS.UI.services.open3d_thickness_dimensions import Open3DThicknessDimensionService

    svc = Open3DThicknessDimensionService.__new__(Open3DThicknessDimensionService)
    svc.editor = editor
    svc.inspector = _FakeInspector()
    return svc


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    passed = True

    from KrakenOS.UI.services.open3d_thickness_dimensions import Open3DThicknessDimensionService as Svc

    sentinel = Svc.LED_OBJECT_EDGE_DIM_ROW
    if sentinel >= 0:
        notes.append(f"FAIL: LED_OBJECT_EDGE_DIM_ROW must be a negative sentinel, got {sentinel}")
        passed = False

    vn = np.array([1.0, 0.0, 0.0])
    su = np.array([0.0, 1.0, 0.0])
    sr = np.array([1.0, 0.0, 0.0])

    # A. With an LED imported + a set distance, the overlay emits one dimension
    #    from the object plane to object+distance, amber, with the sentinel row and
    #    NO drag registration.
    editor = _FakeEditor(led=True, distance=191.7)
    svc = _service(editor)
    captured: dict = {}

    def fake_emit(**kwargs):
        captured.update(kwargs)
        return 1

    svc._emit_span_dimension = fake_emit  # type: ignore[assignment]
    n = svc._emit_led_object_edge_dimension(
        None, base_offset=10.0, scene_span=100.0, view_normal=vn, screen_up=su, screen_right=sr
    )
    if n != 1 or not captured:
        notes.append("FAIL: object->LED overlay did not emit a dimension when an LED is imported")
        passed = False
    else:
        if int(captured.get("row_index", 0)) != int(sentinel):
            notes.append(f"FAIL: overlay row_index={captured.get('row_index')!r}, expected sentinel {sentinel}")
            passed = False
        if captured.get("register_drag", True) is not False:
            notes.append("FAIL: object->LED overlay must register NO drag yet (register_drag=False)")
            passed = False
        base_lo = np.asarray(captured.get("base_lo", ()), dtype=float).reshape(-1)
        base_hi = np.asarray(captured.get("base_hi", ()), dtype=float).reshape(-1)
        if base_lo.size < 3 or not np.allclose(base_lo[:3], (0.0, 0.0, 0.0)):
            notes.append(f"FAIL: overlay base_lo={tuple(base_lo)} != object plane (0,0,0)")
            passed = False
        if base_hi.size < 3 or not np.allclose(base_hi[:3], (0.0, 0.0, 191.7)):
            notes.append(f"FAIL: overlay base_hi={tuple(base_hi)} != object+distance (0,0,191.7)")
            passed = False
        if tuple(captured.get("color", ())) != tuple(Svc.LED_OBJECT_EDGE_DIMENSION_COLOR):
            notes.append("FAIL: overlay is not drawn in the dedicated amber LED color")
            passed = False
        label = str(captured.get("label", ""))
        if "LED" not in label or "191.7" not in label:
            notes.append(f"FAIL: overlay label {label!r} should name the LED and the 191.7 mm distance")
            passed = False

    # B. No LED imported -> no overlay.
    svc_b = _service(_FakeEditor(led=False))
    cap_b: dict = {}
    svc_b._emit_span_dimension = lambda **k: cap_b.update(k) or 1  # type: ignore[assignment]
    if svc_b._emit_led_object_edge_dimension(None, base_offset=10.0, scene_span=100.0, view_normal=vn, screen_up=su, screen_right=sr) != 0 or cap_b:
        notes.append("FAIL: no LED imported must draw no object->LED overlay")
        passed = False

    # C. Zero / unset distance -> no overlay.
    svc_c = _service(_FakeEditor(led=True, distance=0.0))
    cap_c: dict = {}
    svc_c._emit_span_dimension = lambda **k: cap_c.update(k) or 1  # type: ignore[assignment]
    if svc_c._emit_led_object_edge_dimension(None, base_offset=10.0, scene_span=100.0, view_normal=vn, screen_up=su, screen_right=sr) != 0 or cap_c:
        notes.append("FAIL: a zero LED edge distance must draw no overlay")
        passed = False

    # F. bugs/0125: after a free LED carry-drag the overlay tracks the LED's LIVE
    #    object-side edge, not the stale typed distance. flag_20260624_075900_372:
    #    the LED was dragged -36.1658 mm toward the object, so the arrow endpoint and
    #    label must follow to object+(distance-36.1658), and must NOT still read the
    #    typed 191.7.
    DRAG_Z = -36.1658
    live = 191.7 + DRAG_Z  # 155.5342 mm
    editor_f = _FakeEditor(led=True, distance=191.7, led_offset_z=DRAG_Z)
    svc_f = _service(editor_f)
    cap_f: dict = {}
    svc_f._emit_span_dimension = lambda **k: cap_f.update(k) or 1  # type: ignore[assignment]
    nf = svc_f._emit_led_object_edge_dimension(
        None, base_offset=10.0, scene_span=100.0, view_normal=vn, screen_up=su, screen_right=sr
    )
    if nf != 1 or not cap_f:
        notes.append("FAIL: a dragged-LED object->LED overlay did not emit a dimension")
        passed = False
    else:
        bhi = np.asarray(cap_f.get("base_hi", ()), dtype=float).reshape(-1)
        if bhi.size < 3 or not np.allclose(bhi[:3], (0.0, 0.0, live)):
            notes.append(
                f"FAIL: dragged overlay base_hi={tuple(bhi)} must track the LIVE edge "
                f"(0,0,{live:.6g}), not the stale typed 191.7"
            )
            passed = False
        lab_f = str(cap_f.get("label", ""))
        if "191.7" in lab_f:
            notes.append(f"FAIL: dragged overlay label {lab_f!r} still shows the STALE typed 191.7 mm")
            passed = False
        if f"{live:.4g}" not in lab_f:
            notes.append(f"FAIL: dragged overlay label {lab_f!r} should show the LIVE {live:.4g} mm")
            passed = False

    # G. A drag that pushes the LED edge to/behind the object draws no degenerate
    #    (zero/negative-length) arrow.
    editor_g = _FakeEditor(led=True, distance=191.7, led_offset_z=-200.0)
    svc_g = _service(editor_g)
    cap_g: dict = {}
    svc_g._emit_span_dimension = lambda **k: cap_g.update(k) or 1  # type: ignore[assignment]
    if svc_g._emit_led_object_edge_dimension(None, base_offset=10.0, scene_span=100.0, view_normal=vn, screen_up=su, screen_right=sr) != 0 or cap_g:
        notes.append("FAIL: an LED dragged to/behind the object must draw no degenerate object->LED arrow")
        passed = False

    # D. A click on the overlay (edit_dimension at the sentinel row) routes to the
    #    LED edge-distance dialog -- NOT the table-row edit guard.
    editor_d = _FakeEditor(led=True, distance=191.7)
    svc_d = _service(editor_d)
    svc_d.edit_dimension(int(sentinel))
    if editor_d.led_dialog_calls != 1:
        notes.append("FAIL: clicking the object->LED overlay must open the LED edge-distance dialog")
        passed = False
    if svc_d.inspector.status_var.value == "Thickness dimension: choose a non-terminal table row.":
        notes.append("FAIL: the sentinel must bypass the table-row edit guard")
        passed = False

    # A genuinely invalid (non-sentinel) row still hits the guard and never opens
    # the LED dialog.
    editor_e = _FakeEditor(led=True)
    svc_e = _service(editor_e)
    svc_e.edit_dimension(99)
    if editor_e.led_dialog_calls != 0:
        notes.append("FAIL: a non-sentinel invalid row must NOT open the LED dialog")
        passed = False

    # E. Source contract: _emit_span_dimension gates drag on register_drag, and
    #    add_overlays draws the object->LED overlay.
    try:
        emit_src = inspect.getsource(Svc._emit_span_dimension)
        add_src = inspect.getsource(Svc.add_overlays)
        led_emit_src = inspect.getsource(Svc._emit_led_object_edge_dimension)
    except Exception as exc:
        notes.append(f"FAIL: cannot read service source: {exc!r}")
        return False, notes
    if "if register_drag" not in emit_src:
        notes.append("FAIL: _emit_span_dimension no longer gates _register_drag_actor on register_drag")
        passed = False
    if "_emit_led_object_edge_dimension" not in add_src:
        notes.append("FAIL: add_overlays no longer draws the object->LED overlay")
        passed = False
    # bugs/0125 source contract: the overlay measures the LIVE edge (typed distance
    # + LED placement offset) and no longer draws to the stale typed distance.
    if "_step_placement_offset_xyz" not in led_emit_src or "live_distance" not in led_emit_src:
        notes.append("FAIL: object->LED overlay no longer measures the LIVE edge (placement-offset-aware)")
        passed = False
    if "axis * distance" in led_emit_src:
        notes.append("FAIL: object->LED overlay still draws to the STALE typed distance (axis * distance)")
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
