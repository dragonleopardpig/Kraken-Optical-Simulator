"""Guard: the "Add Illumination Source (LED)" entry point (bugs/0284).

bugs/0283 made a scene source a first-class Open 3D object (glyph + browser group + hide/unhide).
bugs/0284 adds the way to CREATE one: right-click the browser's "Scene Sources" group -> "Add
Illumination Source (LED)". The editor appends a physical area-LED (a ``Random rectangle source``) to
``layout_scene_source_specs`` and the inspector re-traces so the 0283 glyph + browser row appear.

The one physics trap this guards: the add MUST start from the REAL normalized specs, never
``_scene_source_specs_for_direct_editing`` (whose empty-scene fallback injects the current Source panel).
On a pure-imaging scene the panel fallback is a NON-physical ``Pupil / field`` reference; injecting it
would draw a supernatural glyph and (bugs/0282) mis-gate the illumination heatmap. So adding to an
imaging scene must yield exactly ``[led]``. The same reasoning tightens the 0283 drawable filter to
PHYSICAL-only, matching exactly what ``_build_scene_source_bundles`` launches.

This guard is display-free (no renderer / no Tk / no llvmpipe segfault): it drives the real editor
add-action against a minimal stub, and asserts the browser/inspector plumbing via ``inspect.getsource``.

Checks
------
* ADD-SCHEMA -- adding to an empty scene yields exactly one physical, enabled ``Random rectangle
  source`` LED that resolves to the seeded origin/direction and square aperture (rx == ry).
* NO-FALLBACK -- adding to an EMPTY spec list yields ``[led]`` (length 1), never ``[pupil_field, led]``;
  adding to an existing source preserves it (length 2).
* UNIQUE-ID -- consecutive adds mint ``source:led-1`` then ``source:led-2`` (no id collision).
* DRAWABLE-GATE -- the new LED is drawable; a NON-physical ``Pupil / field`` reference and a face-bound
  marker are NOT (the tightened, physics-matching filter).
* WIRING -- the browser right-click -> menu -> inspector -> editor chain, and the "start from real
  specs" rule, are actually plumbed (source assertions).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_add_illumination_source

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect

import numpy as np

from KrakenOS.UI.open3d_inspector import Kraken3DInspector
from KrakenOS.UI.panels.open3d_step_admin import Open3DStepAdminPanel
from KrakenOS.UI.scene_source_analysis import (
    dedupe_scene_source_ids,
    normalize_scene_source_specs,
    scene_source_from_spec,
)
from KrakenOS.UI.services.source_modeling import SourceModelingMixin


def _existing_led_spec() -> dict:
    return {
        "source_id": "source:keep",
        "name": "Keep me",
        "model": "Random rectangle source",
        "physical": True,
        "enabled": True,
        "origin": [1.0, 2.0, 3.0],
        "direction": [0.0, 0.0, 1.0],
        "radius_x": 8.0,
        "radius_y": 8.0,
    }


def _pupil_field_reference_spec() -> dict:
    # The non-physical Pupil / field reference the Source-panel fallback would inject. It is a paraxial
    # sampling stand-in, NOT an emitter -- it must never draw an LED glyph.
    return {
        "source_id": "source:pupil-ref",
        "name": "Pupil / field reference",
        "model": "Pupil / field",
        "physical": False,
        "enabled": True,
        "origin": [0.0, 0.0, 0.0],
        "direction": [0.0, 0.0, 1.0],
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


class _StubAddEditor:
    """Drive the real add-action + drawable filter against a minimal, display-free editor stand-in.

    The Source panel is stubbed to fixed values (origin at 0, +Z, 5 mm, 30 deg cone) and
    ``_apply_scene_source_row_action_specs`` mirrors only ``_set_scene_source_specs``' effect on the
    stored spec list (normalize + dedupe) -- no Tk, table, or plot machinery.
    """

    add_illumination_led_source = SourceModelingMixin.add_illumination_led_source
    _drawable_scene_source_descriptors = SourceModelingMixin._drawable_scene_source_descriptors
    _dedupe_scene_source_ids = staticmethod(dedupe_scene_source_ids)

    def __init__(self, specs=None):
        self.layout_scene_source_specs = list(specs or [])
        self._last_status = ""

    def _current_source_origin(self):
        return (0.0, 0.0, 0.0)

    def _current_source_direction(self):
        return (0.0, 0.0, 1.0)

    def _current_source_radius(self):
        return 5.0

    def _current_source_cone_angle(self):
        return 30.0

    def _current_wavelength(self):
        return 0.55

    def _normalize_scene_source_specs(self, value):
        return normalize_scene_source_specs(value)

    def _scene_source_from_spec(self, spec, index, wavelength=0.55):
        return scene_source_from_spec(spec, index, wavelength=wavelength)

    def _apply_scene_source_row_action_specs(self, specs, *, record_history=True, status=""):
        self.layout_scene_source_specs = self._dedupe_scene_source_ids(
            self._normalize_scene_source_specs(specs)
        )
        self._last_status = status


def _check_add_schema(failures: list[str], notes: list[str]) -> None:
    editor = _StubAddEditor([])
    source_id = editor.add_illumination_led_source()
    if source_id != "source:led-1":
        failures.append(f"ADD-SCHEMA: first add should mint 'source:led-1', got {source_id!r}")
    drawn = editor._drawable_scene_source_descriptors()
    if len(drawn) != 1:
        failures.append(f"ADD-SCHEMA: expected exactly one drawable LED after add, got {len(drawn)}")
        return
    src = drawn[0]
    if str(src.source_id) != "source:led-1":
        failures.append(f"ADD-SCHEMA: resolved source_id wrong ({src.source_id!r})")
    if str(src.model) != "Random rectangle source":
        failures.append(f"ADD-SCHEMA: LED model should be 'Random rectangle source', got {src.model!r}")
    if not bool(src.physical) or not bool(src.enabled):
        failures.append("ADD-SCHEMA: the added LED must be physical + enabled")
    origin = np.asarray(src.origin, float).reshape(3)
    direction = np.asarray(src.direction, float).reshape(3)
    if not np.allclose(origin, [0.0, 0.0, 0.0], atol=1e-6):
        failures.append(f"ADD-SCHEMA: LED not seated at the source origin (got {origin.tolist()})")
    if not np.allclose(direction, [0.0, 0.0, 1.0], atol=1e-6):
        failures.append(f"ADD-SCHEMA: LED not aimed along the source direction (got {direction.tolist()})")
    rx = float(src.settings.get("radius_x", 0.0))
    ry = float(src.settings.get("radius_y", 0.0))
    if not (abs(rx - 5.0) < 1e-6 and abs(ry - 5.0) < 1e-6):
        failures.append(f"ADD-SCHEMA: default aperture should be a 5 mm square (rx={rx}, ry={ry})")
    if abs(float(src.settings.get("cone_deg", 0.0)) - 30.0) > 1e-6:
        failures.append("ADD-SCHEMA: default cone should be 30 deg")
    if not [f for f in failures if f.startswith("ADD-SCHEMA")]:
        notes.append("add-schema: add mints a physical Random-rectangle LED at the source pose (5mm/30deg)")


def _check_no_fallback(failures: list[str], notes: list[str]) -> None:
    # Empty imaging scene -> exactly [led], NOT [pupil_field, led] (the panel fallback would inject one).
    editor = _StubAddEditor([])
    editor.add_illumination_led_source()
    specs = editor.layout_scene_source_specs
    if len(specs) != 1:
        failures.append(
            f"NO-FALLBACK: adding to an empty scene must yield exactly [led], got {len(specs)} specs "
            f"({[s.get('source_id') for s in specs]!r}) -- the Source-panel fallback leaked in"
        )
    elif str(specs[0].get("source_id", "")) != "source:led-1":
        failures.append("NO-FALLBACK: the single spec is not the added LED")

    # Existing source preserved, LED appended.
    editor = _StubAddEditor([_existing_led_spec()])
    editor.add_illumination_led_source()
    ids = {str(s.get("source_id", "")) for s in editor.layout_scene_source_specs}
    if ids != {"source:keep", "source:led-1"}:
        failures.append(f"NO-FALLBACK: add must preserve the existing source, got ids {ids!r}")
    if not [f for f in failures if f.startswith("NO-FALLBACK")]:
        notes.append("no-fallback: add starts from the real specs (empty->[led]); existing sources kept")


def _check_unique_id(failures: list[str], notes: list[str]) -> None:
    editor = _StubAddEditor([])
    first = editor.add_illumination_led_source()
    second = editor.add_illumination_led_source()
    if (first, second) != ("source:led-1", "source:led-2"):
        failures.append(f"UNIQUE-ID: consecutive adds should be led-1, led-2; got {(first, second)!r}")
    if len(editor.layout_scene_source_specs) != 2:
        failures.append("UNIQUE-ID: two adds should leave two sources")
    if not [f for f in failures if f.startswith("UNIQUE-ID")]:
        notes.append("unique-id: consecutive adds mint distinct source:led-N ids")


def _check_drawable_gate(failures: list[str], notes: list[str]) -> None:
    # A non-physical Pupil / field reference must NOT draw a glyph (display follows physics).
    editor = _StubAddEditor([_pupil_field_reference_spec()])
    if editor._drawable_scene_source_descriptors():
        failures.append("DRAWABLE-GATE: a non-physical Pupil/field reference must not be drawable")
    # A face-bound marker must NOT draw a free-standing glyph (bugs/0264: it draws on its face).
    editor = _StubAddEditor([_marker_spec()])
    if editor._drawable_scene_source_descriptors():
        failures.append("DRAWABLE-GATE: a face-bound marker must not be a free-standing glyph")
    # A real physical LED IS drawable.
    editor = _StubAddEditor([_existing_led_spec()])
    if len(editor._drawable_scene_source_descriptors()) != 1:
        failures.append("DRAWABLE-GATE: a physical LED should be drawable")
    if not [f for f in failures if f.startswith("DRAWABLE-GATE")]:
        notes.append("drawable-gate: physical LED drawable; Pupil/field reference + marker excluded")


def _check_wiring(failures: list[str], notes: list[str]) -> None:
    for owner, attr in (
        (Kraken3DInspector, "add_illumination_led_source"),
        (SourceModelingMixin, "add_illumination_led_source"),
        (Open3DStepAdminPanel, "_show_scene_sources_context_menu"),
        (Open3DStepAdminPanel, "_add_illumination_led_source"),
    ):
        if not hasattr(owner, attr):
            failures.append(f"WIRING: {owner.__name__} missing {attr}")

    def _src(obj):
        try:
            return inspect.getsource(obj)
        except Exception:
            return ""

    insp_src = _src(Kraken3DInspector.add_illumination_led_source)
    if "self.editor.add_illumination_led_source" not in insp_src or "refresh_from_editor" not in insp_src:
        failures.append("WIRING: inspector add does not call the editor add + refresh_from_editor")

    editor_src = _src(SourceModelingMixin.add_illumination_led_source)
    if "_normalize_scene_source_specs" not in editor_src:
        failures.append("WIRING: editor add does not start from the real normalized specs")
    # Guard the CALL site, not a bare mention: the docstring names the fallback only to explain why it
    # is avoided. A real reintroduction would call ``self._scene_source_specs_for_direct_editing(...)``.
    if "self._scene_source_specs_for_direct_editing" in editor_src:
        failures.append("WIRING: editor add uses the panel fallback (would inject a Pupil/field ref)")
    if "Random rectangle source" not in editor_src or "physical" not in editor_src:
        failures.append("WIRING: editor add does not build a physical Random-rectangle LED")

    rc_src = _src(Open3DStepAdminPanel._on_tree_right_click)
    if "category:sources" not in rc_src or "empty:sources" not in rc_src:
        failures.append("WIRING: browser right-click does not intercept the Scene Sources group")
    if "Add Illumination Source (LED)" not in _src(Open3DStepAdminPanel._show_scene_sources_context_menu):
        failures.append("WIRING: Scene Sources menu has no 'Add Illumination Source (LED)' command")
    if "self.inspector.add_illumination_led_source" not in _src(Open3DStepAdminPanel._add_illumination_led_source):
        failures.append("WIRING: browser add handler does not call the inspector add")
    if "physical" not in _src(SourceModelingMixin._drawable_scene_source_descriptors):
        failures.append("WIRING: drawable filter no longer gates on physical (supernatural glyph risk)")
    if not [f for f in failures if f.startswith("WIRING")]:
        notes.append("wiring: browser menu -> inspector -> editor add + real-spec start plumbed end-to-end")


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    _check_add_schema(failures, notes)
    _check_no_fallback(failures, notes)
    _check_unique_id(failures, notes)
    _check_drawable_gate(failures, notes)
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
