"""Guard: a scene source is a first-class Open 3D object (bugs/0283).

The parametric scene sources in ``layout_scene_source_specs`` (an emitting LED etc.) used to be
editable only through a 2-D table -- invisible in the Open 3D scene, absent from the scene browser, with
no hide/unhide. bugs/0283 makes each enabled, non-marker source draw as a first-class glyph (an emitting
aperture panel + a direction arrow) and appear under a "Scene Sources" browser group with the same
hide/unhide as a scene element.

This guard is display-free (no renderer / no Tk / no llvmpipe segfault): it exercises the production
logic against stub actors + stub self objects, exactly like validate_open3d_normal_to_sensor_gesture_leave.

Checks
------
* DESCRIPTORS -- ``_drawable_scene_source_descriptors`` keeps only the enabled, NON-marker source and
  resolves its geometry through the same ``scene_source_from_spec`` path the trace uses (a marker draws
  on its face per bugs/0264; a disabled source emits nothing).
* BASIS -- ``_scene_source_glyph_basis`` returns an orthonormal (d, u, v) with the aperture plane (u, v)
  perpendicular to the emission direction d, so the drawn panel is the plane the source samples over.
* VISIBILITY -- ``set_source_hidden`` turns the source's glyph actors invisible, the state survives a
  refresh (re-applied by ``_apply_scene_element_visibility``), and unhiding restores them.
* RESOLVER -- the browser iid resolver maps ``source:<id>`` to a source_id (and still maps scene rows).
* WIRING -- the glyph draw + browser group + source hide/unhide are actually plumbed into the refresh,
  the actor-add, the category list, and the tree build (source assertions).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_scene_source_object

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect

import numpy as np

from KrakenOS.UI.open3d_inspector import Kraken3DInspector
from KrakenOS.UI.panels.open3d_step_admin import Open3DStepAdminPanel
from KrakenOS.UI.scene_source_analysis import (
    normalize_scene_source_specs,
    scene_source_from_spec,
    scene_source_spec_is_face_bound_marker,
)
from KrakenOS.UI.services.open3d_scene_refresh import Open3DSceneRefreshService
from KrakenOS.UI.services.source_modeling import SourceModelingMixin


def _real_spec() -> dict:
    return {
        "source_id": "led1",
        "name": "LED (rectangle)",
        "model": "Random rectangle source",
        "enabled": True,
        "physical": True,
        "origin": [0.0, 0.0, 0.0],
        "direction": [0.0, 0.0, 1.0],
        "radius_x": 27.5,
        "radius_y": 39.0,
        "cone_deg": 30.0,
    }


def _marker_spec() -> dict:
    return {
        "source_id": "source:face:S001/F001",
        "name": "Illumination Source (into solid)",
        "model": "Collimated disk source",
        "enabled": True,
        "physical": True,
        "radius": 2.0,
        "face_anchor_row": 1,
        "face_anchor_face_id": "S001/F001",
    }


def _disabled_spec() -> dict:
    return {
        "source_id": "led_off",
        "name": "LED (disabled)",
        "model": "Random rectangle source",
        "enabled": False,
        "physical": True,
        "origin": [10.0, 0.0, 0.0],
        "direction": [0.0, 0.0, 1.0],
        "radius_x": 5.0,
        "radius_y": 5.0,
    }


class _StubEditor:
    """Bind the real descriptor enumerator onto a minimal editor stand-in (no Tk)."""

    _drawable_scene_source_descriptors = SourceModelingMixin._drawable_scene_source_descriptors

    def __init__(self, specs):
        self.layout_scene_source_specs = specs

    def _normalize_scene_source_specs(self, value):
        return normalize_scene_source_specs(value)

    def _scene_source_from_spec(self, spec, index, wavelength=0.55):
        return scene_source_from_spec(spec, index, wavelength=wavelength)


class _StubActor:
    def __init__(self):
        self._visible = 1

    def SetVisibility(self, value):
        self._visible = 1 if value else 0

    def GetVisibility(self):
        return self._visible


class _StubVizInspector:
    """Bind the real source visibility API onto a stub with two glyph actors under one source_id."""

    _all_actor_keys_for_source = Kraken3DInspector._all_actor_keys_for_source
    _set_actor_keys_visible = Kraken3DInspector._set_actor_keys_visible
    is_source_hidden = Kraken3DInspector.is_source_hidden
    set_source_hidden = Kraken3DInspector.set_source_hidden
    _apply_scene_element_visibility = Kraken3DInspector._apply_scene_element_visibility

    def __init__(self):
        self.a1 = _StubActor()
        self.a2 = _StubActor()
        self._actor_by_key = {"k1": self.a1, "k2": self.a2}
        self._source_actor_map = {"src1": ["k1", "k2"]}
        self._actor_source_map = {"k1": "src1", "k2": "src1"}
        self._hidden_source_ids = set()
        self._hidden_scene_rows = set()
        self._hidden_step_labels = set()

    def render(self):
        pass


class _StubPanel:
    _resolve_iid_target = Open3DStepAdminPanel._resolve_iid_target


def _check_descriptors(failures: list[str], notes: list[str]) -> None:
    # Predicate classification the enumerator relies on.
    if scene_source_spec_is_face_bound_marker(_real_spec()):
        failures.append("DESCRIPTORS: real LED spec misclassified as a face-bound marker")
    if not scene_source_spec_is_face_bound_marker(_marker_spec()):
        failures.append("DESCRIPTORS: marker spec (face_anchor_row>=0) not classified as a marker")

    editor = _StubEditor([_real_spec(), _marker_spec(), _disabled_spec()])
    drawn = editor._drawable_scene_source_descriptors()
    ids = [str(getattr(s, "source_id", "")) for s in drawn]
    if ids != ["led1"]:
        failures.append(f"DESCRIPTORS: expected only the enabled non-marker LED, got {ids!r}")
        return
    source = drawn[0]
    origin = np.asarray(source.origin, dtype=float).reshape(3)
    direction = np.asarray(source.direction, dtype=float).reshape(3)
    rx = float(source.settings.get("radius_x"))
    ry = float(source.settings.get("radius_y"))
    if not np.allclose(origin, [0.0, 0.0, 0.0], atol=1e-6):
        failures.append(f"DESCRIPTORS: origin not read from spec (got {origin.tolist()})")
    if not np.allclose(direction, [0.0, 0.0, 1.0], atol=1e-6):
        failures.append(f"DESCRIPTORS: direction not read from spec (got {direction.tolist()})")
    if not (abs(rx - 27.5) < 1e-6 and abs(ry - 39.0) < 1e-6):
        failures.append(f"DESCRIPTORS: rectangle half-sizes wrong (rx={rx}, ry={ry})")
    if not [f for f in failures if f.startswith("DESCRIPTORS")]:
        notes.append("descriptors: marker + disabled excluded; the LED resolves origin/dir/rx/ry from spec")


def _check_basis(failures: list[str], notes: list[str]) -> None:
    from KrakenOS.UI.services.source_modeling import SourceModelingMixin

    for direction in ((0.0, 0.0, 1.0), (0.0, 0.0, -1.0), (-0.7071, 0.0, 0.7071), (0.0, 1.0, 0.0)):
        d, u, v = Kraken3DInspector._scene_source_glyph_basis(direction)
        d = np.asarray(d, float); u = np.asarray(u, float); v = np.asarray(v, float)
        if abs(np.linalg.norm(d) - 1.0) > 1e-6:
            failures.append(f"BASIS: direction not unit for {direction}")
        if abs(np.linalg.norm(u) - 1.0) > 1e-6 or abs(np.linalg.norm(v) - 1.0) > 1e-6:
            failures.append(f"BASIS: aperture axes not unit for {direction}")
        if abs(float(np.dot(u, d))) > 1e-6 or abs(float(np.dot(v, d))) > 1e-6:
            failures.append(f"BASIS: aperture plane not perpendicular to emission dir for {direction}")
        if abs(float(np.dot(u, v))) > 1e-6:
            failures.append(f"BASIS: aperture axes u,v not orthogonal for {direction}")
        # bugs/0699: the glyph frame MUST be the frame the ray sampler orients bundles with --
        # a divergent construction drew the om05a faceB 50x1 emitter as a 1x50 vertical stripe.
        su, sv, sw = SourceModelingMixin._source_frame_vectors_from_direction(direction)
        if not (np.allclose(u, su, atol=1e-9) and np.allclose(v, sv, atol=1e-9)
                and np.allclose(d, sw, atol=1e-9)):
            failures.append(f"BASIS: glyph frame diverges from the sampler frame for {direction}")
    d, u, v = Kraken3DInspector._scene_source_glyph_basis((0.0, 0.0, -1.0))
    if abs(float(np.asarray(u, float)[1])) > 1e-9:
        failures.append("BASIS: z-facing source puts radius_x along vertical (0699 golden stripe)")
    if not [f for f in failures if f.startswith("BASIS")]:
        notes.append("basis: (d,u,v) orthonormal, matches the sampler frame; z-facing radius_x is horizontal")


def _check_visibility(failures: list[str], notes: list[str]) -> None:
    insp = _StubVizInspector()
    if insp.a1.GetVisibility() != 1 or insp.a2.GetVisibility() != 1:
        failures.append("VISIBILITY: source glyph actors should start visible")
    insp.set_source_hidden("src1", True)
    if insp.a1.GetVisibility() != 0 or insp.a2.GetVisibility() != 0:
        failures.append("VISIBILITY: Hide did not make the source glyph actors invisible")
    if not insp.is_source_hidden("src1"):
        failures.append("VISIBILITY: is_source_hidden should report True after Hide")
    # Simulate a full refresh: the rebuild re-creates the actors visible, then the browser hidden
    # state must be re-applied.
    insp.a1.SetVisibility(1)
    insp.a2.SetVisibility(1)
    insp._apply_scene_element_visibility()
    if insp.a1.GetVisibility() != 0 or insp.a2.GetVisibility() != 0:
        failures.append("VISIBILITY: hidden state lost after a refresh (not re-applied)")
    insp.set_source_hidden("src1", False)
    if insp.a1.GetVisibility() != 1 or insp.a2.GetVisibility() != 1:
        failures.append("VISIBILITY: Unhide did not restore the source glyph actors")
    if insp.is_source_hidden("src1"):
        failures.append("VISIBILITY: is_source_hidden should report False after Unhide")
    if not [f for f in failures if f.startswith("VISIBILITY")]:
        notes.append("visibility: Hide/Unhide toggles the glyph actors and survives a refresh")


def _check_resolver(failures: list[str], notes: list[str]) -> None:
    panel = _StubPanel()
    if panel._resolve_iid_target("source:led1") != ([], None, None, "led1"):
        failures.append("RESOLVER: 'source:led1' must resolve to source_id 'led1'")
    if panel._resolve_iid_target("scene-row:5") != ([5], None, None, None):
        failures.append("RESOLVER: 'scene-row:5' regressed (must still resolve to row 5)")
    if not [f for f in failures if f.startswith("RESOLVER")]:
        notes.append("resolver: source:/scene-row: iids resolve to (rows,label,display,source_id)")


def _check_wiring(failures: list[str], notes: list[str]) -> None:
    for attr in ("set_source_hidden", "is_source_hidden", "_all_actor_keys_for_source",
                 "_add_scene_source_glyphs", "_add_one_scene_source_glyph", "_scene_source_glyph_basis"):
        if not hasattr(Kraken3DInspector, attr):
            failures.append(f"WIRING: inspector missing {attr}")
    if not hasattr(SourceModelingMixin, "_drawable_scene_source_descriptors"):
        failures.append("WIRING: editor missing _drawable_scene_source_descriptors")

    def _src(obj):
        try:
            return inspect.getsource(obj)
        except Exception:
            return ""

    if "track_source_id" not in _src(Kraken3DInspector._add_mesh_actor):
        failures.append("WIRING: _add_mesh_actor has no track_source_id (glyphs can't key by source)")
    apply_src = _src(Kraken3DInspector._apply_scene_element_visibility)
    if "_hidden_source_ids" not in apply_src or "_all_actor_keys_for_source" not in apply_src:
        failures.append("WIRING: refresh does not re-apply hidden sources")
    refresh_src = _src(Open3DSceneRefreshService.refresh_scene)
    if "_add_scene_source_glyphs" not in refresh_src:
        failures.append("WIRING: refresh_scene does not draw the scene source glyphs")
    if "_source_actor_map" not in refresh_src:
        failures.append("WIRING: refresh_scene does not reset the source actor maps")
    if "sources" not in [key for key, _title, _labels in Open3DStepAdminPanel.CATEGORY_SPECS]:
        failures.append("WIRING: browser has no 'Scene Sources' category")
    build_src = _src(Open3DStepAdminPanel.refresh)
    if "_scene_source_browser_rows" not in build_src or "source:" not in build_src:
        failures.append("WIRING: browser refresh does not insert Scene Sources rows")
    if "set_source_hidden" not in _src(Open3DStepAdminPanel._set_element_hidden):
        failures.append("WIRING: browser _set_element_hidden does not route source hide/unhide")
    if not [f for f in failures if f.startswith("WIRING")]:
        notes.append("wiring: glyph draw + browser group + source hide/unhide plumbed end-to-end")


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    _check_descriptors(failures, notes)
    _check_basis(failures, notes)
    _check_visibility(failures, notes)
    _check_resolver(failures, notes)
    _check_wiring(failures, notes)
    return (not failures), (failures + notes)


def main() -> int:
    ok, messages = run_checks()
    for line in messages:
        print(("PASS " if ok else "") + line)
    print("RESULT:", "pass" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
