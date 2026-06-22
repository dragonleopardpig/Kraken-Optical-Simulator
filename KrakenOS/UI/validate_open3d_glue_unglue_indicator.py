#!/usr/bin/env python3
"""Display-free guard for bugs/0103: the beam-splitter<->LED rigid glue (item 3)
must be (a) UNGLUEable for as long as it is active and (b) VISIBLE in the browser.

Why it exists (the flag "No glue/unglue indicator. After glue, no unglue option."):
  The BS<->LED glue is a persistent editor flag (`_optical_led_glued`, saved to disk).
  The right-click "Glue/Unglue BS to LED" used to be gated behind BOTH overlays still
  being imported AS overlays. Promoting the beam splitter ("optical" overlay) into an
  optical solid removes that overlay, so the Unglue command vanished from every menu
  while the glue stayed ON (and survived save/reload) -- stuck, with no indicator.

What it checks:
  A. UNGLUE reachability -- when glued, "Unglue BS from LED" is offered on the LED
     overlay EVEN WHEN the "optical" overlay is gone (promoted away). The LED is a
     decoration (never promoted, bugs/0101), so it is the stable anchor.
  B. GLUE direction still gated -- when NOT glued, "Glue BS to LED" appears only when
     BOTH overlays are imported; a lone overlay offers neither (but always keeps the
     unrelated "Glue STEP to Surrogate" reset).
  C. The promoted beam-splitter ROW also offers Unglue: `_row_is_glued_optical_bs`
     is True only for a promoted "optical" solid while glued (source-checks that both
     promoted-row branches emit the Unglue command behind that guard, since a live
     row-actions cascade needs a tk master).
  D. The browser indicator: `_glue_partner_suffix` tags the led/optical elements with
     "glued to BS/LED" when glued, and nothing otherwise; refresh() applies it.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_glue_unglue_indicator

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
from types import SimpleNamespace


_LED_SUFFIX = "  — glued to BS"
_OPTICAL_SUFFIX = "  — glued to LED"


class _FakeMenu:
    """Records the labels a menu builder adds (tk-free)."""

    def __init__(self) -> None:
        self.labels: list[str] = []

    def add_command(self, label=None, **_kw) -> None:
        self.labels.append(str(label))

    def add_separator(self) -> None:
        self.labels.append("---")

    def add_cascade(self, label=None, **_kw) -> None:
        self.labels.append(str(label))


def _make_service(**editor_attrs):
    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService

    defaults = dict(
        optical_led_glued=lambda: False,
        _step_path_for_label=lambda lbl: None,
        rows=[],
        _file_backed_stl_row_at=lambda i: None,
        _is_any_promoted_optical_solid_row=lambda r: False,
        _is_open3d_promoted_optical_solid_row=lambda r: False,
        _open3d_step_label_for_optical_solid_row=lambda r: "optical",
        open_optical_solid_face_role_editor=lambda *a, **k: None,
    )
    defaults.update(editor_attrs)
    editor = SimpleNamespace(**defaults)
    inspector = SimpleNamespace(
        editor=editor,
        status_var=SimpleNamespace(set=lambda *a, **k: None),
        append_debug=lambda *a, **k: None,
    )
    return Open3DFaceAssignmentService(inspector)


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []

    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService

    # A) Glued, and the "optical" overlay was promoted away (only "led" remains):
    #    right-clicking the LED still offers Unglue.
    svc = _make_service(
        optical_led_glued=lambda: True,
        _step_path_for_label=lambda lbl: "/led.step" if lbl == "led" else None,
    )
    m = _FakeMenu()
    svc.append_element_context_actions(m, step_label="led")
    if "Unglue BS from LED" not in m.labels:
        failures.append(f"FAIL: glued LED overlay must offer Unglue even when BS is promoted (labels={m.labels})")
    if "Glue STEP to Surrogate" not in m.labels:
        failures.append(f"FAIL: LED overlay lost the unrelated 'Glue STEP to Surrogate' reset (labels={m.labels})")

    # B) Not glued, both overlays imported -> offer Glue (not Unglue).
    svc2 = _make_service(
        optical_led_glued=lambda: False,
        _step_path_for_label=lambda lbl: f"/{lbl}.step" if lbl in ("optical", "led") else None,
    )
    m2 = _FakeMenu()
    svc2.append_element_context_actions(m2, step_label="optical")
    if "Glue BS to LED (move together)" not in m2.labels:
        failures.append(f"FAIL: ungued + both imported should offer Glue BS to LED (labels={m2.labels})")
    if "Unglue BS from LED" in m2.labels:
        failures.append(f"FAIL: not-glued must NOT offer Unglue (labels={m2.labels})")

    # B') Not glued, only the optical overlay imported -> no BS<->LED item at all,
    #     but the "Glue STEP to Surrogate" reset is still present.
    svc3 = _make_service(
        optical_led_glued=lambda: False,
        _step_path_for_label=lambda lbl: "/optical.step" if lbl == "optical" else None,
    )
    m3 = _FakeMenu()
    svc3.append_element_context_actions(m3, step_label="optical")
    if any("BS to LED" in lbl or "Unglue BS" in lbl for lbl in m3.labels):
        failures.append(f"FAIL: a lone overlay should offer no BS<->LED glue/unglue (labels={m3.labels})")
    if "Glue STEP to Surrogate" not in m3.labels:
        failures.append(f"FAIL: lone overlay lost 'Glue STEP to Surrogate' (labels={m3.labels})")

    # C) The promoted beam-splitter ROW is recognised as the glued BS.
    bs_row = SimpleNamespace(name="S1 BS", advanced={"StepOverlayPromotion": {"step_label": "optical"}})
    svc_row = _make_service(
        optical_led_glued=lambda: True,
        rows=[bs_row],
        _is_open3d_promoted_optical_solid_row=lambda r: True,
        _open3d_step_label_for_optical_solid_row=lambda r: "optical",
    )
    if not svc_row._row_is_glued_optical_bs(0):
        failures.append("FAIL: a glued promoted 'optical' solid row should be recognised as the BS (offer Unglue)")
    # not glued -> not recognised
    svc_row_ung = _make_service(
        optical_led_glued=lambda: False,
        rows=[bs_row],
        _is_open3d_promoted_optical_solid_row=lambda r: True,
        _open3d_step_label_for_optical_solid_row=lambda r: "optical",
    )
    if svc_row_ung._row_is_glued_optical_bs(0):
        failures.append("FAIL: when not glued, the row must NOT be flagged as the glued BS")
    # a promoted LENS row (not the BS) -> not recognised even while glued
    svc_lens = _make_service(
        optical_led_glued=lambda: True,
        rows=[SimpleNamespace(name="S2 lens", advanced={})],
        _is_open3d_promoted_optical_solid_row=lambda r: True,
        _open3d_step_label_for_optical_solid_row=lambda r: "lens",
    )
    if svc_lens._row_is_glued_optical_bs(0):
        failures.append("FAIL: a promoted non-'optical' solid must NOT be flagged as the glued BS")

    # C-source) Both promoted-row branches emit the Unglue command behind the guard
    #           (the live cascade needs a tk master, so we can't build it headless).
    helper_src = inspect.getsource(Open3DFaceAssignmentService.append_element_context_actions)
    if helper_src.count("_row_is_glued_optical_bs(row_index)") < 2:
        failures.append("FAIL: both promoted-row branches must gate Unglue on _row_is_glued_optical_bs")
    if "Unglue BS from LED" not in helper_src:
        failures.append("FAIL: the shared helper no longer offers 'Unglue BS from LED'")
    # The overlay unglue must NOT be gated behind the both-overlays availability check
    # (that gate is the regression that hid Unglue after promotion).
    overlay_block = helper_src.split("if step_label in (\"optical\", \"led\"):", 1)
    if len(overlay_block) == 2:
        after = overlay_block[1].split("return True", 1)[0]
        if "optical_led_glued()" not in after:
            failures.append("FAIL: overlay Unglue should be gated on optical_led_glued(), not availability")

    # D) The browser indicator suffix.
    from KrakenOS.UI.panels.open3d_step_admin import Open3DStepAdminPanel

    panel = object.__new__(Open3DStepAdminPanel)
    panel.editor = SimpleNamespace(optical_led_glued=lambda: True)
    if panel._glue_partner_suffix("led") != _LED_SUFFIX:
        failures.append(f"FAIL: glued LED indicator wrong ({panel._glue_partner_suffix('led')!r})")
    if panel._glue_partner_suffix("optical") != _OPTICAL_SUFFIX:
        failures.append(f"FAIL: glued BS indicator wrong ({panel._glue_partner_suffix('optical')!r})")
    if panel._glue_partner_suffix("lens") != "":
        failures.append("FAIL: an unrelated element must carry no glue indicator")
    panel.editor = SimpleNamespace(optical_led_glued=lambda: False)
    if panel._glue_partner_suffix("led") != "" or panel._glue_partner_suffix("optical") != "":
        failures.append("FAIL: no glue indicator when nothing is glued")

    # D-source) refresh() actually applies the suffix to the overlay + promoted-row text.
    refresh_src = inspect.getsource(Open3DStepAdminPanel.refresh)
    if refresh_src.count("_glue_partner_suffix(") < 2:
        failures.append("FAIL: refresh() must apply _glue_partner_suffix to overlays AND promoted rows")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0103 BS<->LED glue must stay UNGLUEable + show a browser indicator")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] glue stays unglueable (LED anchor + promoted BS row) and shows a 'glued to ...' indicator (bugs/0103)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
