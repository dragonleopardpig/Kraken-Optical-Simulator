"""Display-free guard: scene annotation labels draw above the housings, the HUD and banner draw
above the labels, and the focus-plane label does not repeat the banner (bugs/0849).

flag_20260921_172317: with a camera STEP glued the sensor is INSIDE the camera housing, and so is
every image-plane label -- sensor size, field strips, the detached focus planes. In the main
renderer each translucent wall in front of them was blended over the text: dimmed, cross-hatched
by the camera's edges, unreadable. And on a split field the scene printed the same ~100-character
focus sentence twice, spot sizes included, over the rays -- the banner's FOCUS rows already carry
all of it.

Labels now go on the always-on-top layer (the gizmos' overlay renderer, bugs/0112), never
pickable (that layer is picked first). Moving them there alone put a label OVER the banner in a
real-inspector capture (bugs/diag_0849_label_layers.py), so the HUD and banner moved to the same
layer: 2-D actors render in a layer's overlay pass after its 3-D props, so they always cover the
labels. The capture after the fix: 9 labels, the HUD and the banner all on the top layer, the
banner drawn over the label that used to cover it.

  A  the annotation-layer helpers, bound onto a fake with two REAL vtkRenderers: attach puts a prop
     on the top layer only (and takes it off the main renderer), idempotently; detach removes it
     from both; with no top layer everything stays on the main renderer
  L  the REAL label builder: the actor goes through the helper and is not pickable; a fake with no
     helper falls back to the main renderer
  F  the focus label names the field, the distance and the side -- and no spot sizes
  W  the HUD and banner updaters attach through the helper (executable lines -- their real run
     needs the inspector; the diagnostic above is the rendered check)
"""
from __future__ import annotations

import inspect
from types import SimpleNamespace


def run_checks() -> tuple[bool, list[str]]:
    import vtk
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector as K
    from KrakenOS.UI.services import detector_coverage_overlay as dco

    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    class _Fake:
        _annotation_layer_renderer = K._annotation_layer_renderer
        _attach_annotation_prop = K._attach_annotation_prop
        _detach_annotation_prop = K._detach_annotation_prop
        _add_renderer_view_prop = K._add_renderer_view_prop

        def __init__(self, with_top=True):
            self._renderer = vtk.vtkRenderer()
            self._gizmo_overlay_renderer = vtk.vtkRenderer() if with_top else None

    # ---- A: the helpers ----------------------------------------------------------------------------
    fake = _Fake()
    label = vtk.vtkBillboardTextActor3D()
    fake._renderer.AddViewProp(label)                     # as the old code left it
    fake._attach_annotation_prop(label)
    fake._attach_annotation_prop(label)                   # idempotent
    top, main = fake._gizmo_overlay_renderer, fake._renderer
    ok(top.HasViewProp(label) and not main.HasViewProp(label) and top.GetViewProps().GetNumberOfItems() == 1,
       "A1: attach puts the label on the top layer once, and takes it off the main renderer")
    fake._detach_annotation_prop(label)
    ok(not top.HasViewProp(label) and not main.HasViewProp(label),
       "A2: detach removes it from both layers")
    bare = _Fake(with_top=False)
    hud = vtk.vtkTextActor()
    bare._attach_annotation_prop(hud)
    ok(bare._annotation_layer_renderer() is bare._renderer and bare._renderer.HasViewProp(hud),
       "A3: with no top layer the prop stays on the main renderer -- nothing is lost")

    # ---- L: the real label builder -----------------------------------------------------------------
    service = dco.DetectorCoverageOverlayService(SimpleNamespace(editor=SimpleNamespace(append_debug=print)), pv_module=None)
    fake = _Fake()
    service.inspector = fake
    drew = service._label_actor((1.0, 2.0, 3.0), "Sensor 23.0×23.0", (0.9, 0.5, 0.1))
    props = fake._gizmo_overlay_renderer.GetViewProps()
    props.InitTraversal()
    placed = props.GetNextProp() if props.GetNumberOfItems() else None
    ok(drew and placed is not None and fake._renderer.GetViewProps().GetNumberOfItems() == 0
       and not placed.GetPickable(),
       "L1: the REAL label builder puts the label on the top layer, not pickable")
    added = []
    legacy = SimpleNamespace(_add_renderer_view_prop=added.append)
    service.inspector = legacy
    ok(service._label_actor((0, 0, 0), "x", (1, 0, 0)) and len(added) == 1,
       "L2: an inspector without the helper still gets its label (main renderer)")

    # ---- F: the focus label ------------------------------------------------------------------------
    info = {"offset_mm": -0.1155, "side": "in front of", "rms_waist_mm": 0.000489, "rms_plane_mm": 0.00306,
            "images": [dict(name="Face A field", offset_mm=-0.1155, side="in front of", rms_waist_mm=0.000489, rms_plane_mm=0.00306, half_along_u_mm=11.52),
                       dict(name="Face B field", offset_mm=-0.1155, side="in front of", rms_waist_mm=0.000489, rms_plane_mm=0.00306, half_along_u_mm=11.52)]}
    texts = [str(spec["text"]) for spec in dco.focused_image_plane_label_specs((0, 0, 0), (0, 0, 1), info, 11.52)]
    ok(texts == ["Face A field: Focused image 0.1155 mm in front of the sensor",
                 "Face B field: Focused image 0.1155 mm in front of the sensor"],
       f"F: each focus plane names its field, distance and side, and no spot sizes -- {texts}")

    # ---- W: the HUD and banner share the layer -----------------------------------------------------
    def _code(fn):
        return [ln.split("#", 1)[0] for ln in inspect.getsource(fn).splitlines()]

    wired = all(
        any("self._attach_annotation_prop(actor)" in ln for ln in _code(fn))
        and not any("self._add_renderer_view_prop(actor)" in ln for ln in _code(fn))
        and any("self._detach_annotation_prop(actor)" in ln for ln in _code(fn))
        for fn in (K._update_system_info_hud, K._update_solve_refusal_banner)
    )
    ok(wired, "W: the HUD and the banner attach and detach through the annotation layer -- so they "
              "render in its overlay pass, after (over) the labels")
    return state["ok"], notes


def run() -> int:
    passed, notes = run_checks()
    print()
    for note in notes:
        print(("  " + note[2:]) if note.startswith("= ") else ("! " + note))
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
