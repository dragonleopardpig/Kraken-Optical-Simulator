#!/usr/bin/env python3
"""Display-free guard for the persistent CA opening selection + menu (bugs/0334-0336).

User report (imported LED, three flags on the CLICK step after hover-highlight):
  1. "CA highlighted." -- GOOD (the 0327-0331 hover work).
  2. "Left click on the highlighted CA edge causing the whole STEP selected.
     Should select only the highlighted edge." -- a left-click discarded the
     opening detection and selected the whole STEP body (+ move gizmo).
  3. "Right click on the selected CA edge: the selection hop, causing the right
     click to show the menu of the STEP instead of the edge." -- the right-click
     re-picked a fresh cell that fell through the see-through hole to the body.
  Follow-ups: "Left click selection should make the selection permanent until user
  click elsewhere to disable it." and "the right click pop up menu can't be
  destroyed by clicking elsewhere in 3D scene." Plus: keep the body move gizmo, but
  on a separate toggle (the existing "Move/Rotate handles" checkbox).

Fix:
  0334. A left-click on a highlighted clear-aperture opening pins ONLY that opening
        as a PERSISTENT cyan rim (``_set_selected_step_opening`` /
        ``_clear_selected_step_opening`` / ``_has_selected_step_opening`` on the
        inspector; ``_select_step_opening_from_feature`` on the interaction service
        + a ``feature_pick.get("opening")`` branch in ``_on_left_button_press`` that
        returns BEFORE ``select_step_component`` -- so no body select, no gizmo).
        The pinned rim survives hover changes and is cleared only through
        ``_clear_open3d_selection`` (every deselect path) or a CA snap.
  0335. A right-click while an opening is pinned builds an OPENING-ONLY menu
        (``_show_selected_opening_context_menu``) straight from the pinned geometry
        -- guarded ahead of ``_right_click_pick_context`` so the selection cannot
        "hop" to the body behind the hole. Offers the CA actions only, never the
        whole-body promote items.
  0336. All right-click menus post through ``_popup_context_menu``, which -- because
        tk_popup releases its grab immediately on X11 and the heavyweight GL canvas
        swallows the next click -- binds the VTK widget's button-press to
        ``_dismiss_active_context_menu`` so a click anywhere in the 3D scene unposts
        the popup.

What it checks
--------------
  1. 0334: the inspector state round-trip (set/has/clear) and the interaction
     service's ``_select_step_opening_from_feature`` (pins finite geometry, refuses
     non-finite) + the left-click source branch.
  2. 0335: the opening-only menu builds the CA actions and NO promote items from the
     pinned geometry, refuses empty geometry, and is guarded ahead of the body
     re-pick.
  3. 0336: ``_popup_context_menu`` binds dismissal + records the live menu;
     ``_dismiss_active_context_menu`` unposts + unbinds and is re-entrancy safe; the
     body menu posts through it; deselect + CA snap both drop the pinned rim.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_led_ca_persistent_select

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
import types

import numpy as np


class _Status:
    def __init__(self):
        self.text = ""

    def set(self, value):
        self.text = str(value)

    def get(self):
        return self.text


def _section1(failures: list[str]) -> None:
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector as K
    from KrakenOS.UI.services.open3d_interaction import Open3DInteractionService

    # 1a) Inspector state round-trip -- set / has / clear (renderer=None => no actor).
    insp = types.SimpleNamespace(
        _renderer=None,
        _selected_opening_outline_actor=None,
        _selected_opening_label="",
        _selected_opening_face_id="",
        _selected_opening_center=None,
        _selected_opening_normal=None,
        # bugs/0339: _set_selected_step_opening also tears down any pinned FACE
        # selection (single persistent selection) via _clear_selected_step_face, so
        # the stub needs that method's state too or the set raises AttributeError.
        _selected_face_outline_actor=None,
        _selected_face_label="",
        _selected_face_id="",
        _selected_face_center=None,
        _selected_face_normal=None,
        render=lambda *a, **k: None,
        _remove_renderer_view_prop=lambda *a, **k: None,
        _add_renderer_view_prop=lambda *a, **k: None,
    )
    # These inspector methods call each other via ``self`` -- bind them.
    insp._set_selected_step_opening = types.MethodType(K._set_selected_step_opening, insp)
    insp._clear_selected_step_opening = types.MethodType(K._clear_selected_step_opening, insp)
    insp._has_selected_step_opening = types.MethodType(K._has_selected_step_opening, insp)
    insp._clear_selected_step_face = types.MethodType(K._clear_selected_step_face, insp)
    insp._set_selected_step_opening(
        "led", "F053", np.asarray([1.0, 2.0, 3.0]), np.asarray([0.0, 0.0, 1.0]), None
    )
    if insp._selected_opening_label != "led":
        failures.append("FAIL(1a): _set_selected_step_opening must store the STEP label")
    if insp._selected_opening_face_id != "F053":
        failures.append("FAIL(1a): _set_selected_step_opening must store the opening face_id")
    if insp._selected_opening_center is None or not np.allclose(insp._selected_opening_center, [1.0, 2.0, 3.0]):
        failures.append("FAIL(1a): _set_selected_step_opening must store the opening centre")
    if not insp._has_selected_step_opening():
        failures.append("FAIL(1a): _has_selected_step_opening must be True after a set")
    if not insp._clear_selected_step_opening():
        failures.append("FAIL(1a): _clear_selected_step_opening must report a change on the first clear")
    if insp._has_selected_step_opening():
        failures.append("FAIL(1a): _has_selected_step_opening must be False after a clear")
    if insp._clear_selected_step_opening():
        failures.append("FAIL(1a): a second _clear_selected_step_opening must be a no-op (idempotent)")

    # 1b) Interaction service pins finite opening geometry, refuses non-finite.
    class _Rec:
        def __init__(self):
            self.calls = []

        def __call__(self, *args, **kwargs):
            self.calls.append((args, kwargs))

    setter = _Rec()
    remember = _Rec()
    svc_insp = types.SimpleNamespace(
        _set_selected_step_opening=setter,
        _remember_selected_step_feature=remember,
        status_var=_Status(),
        render=lambda *a, **k: None,
    )
    svc = Open3DInteractionService(svc_insp)
    good_pick = {
        "feature": (np.asarray([9.0, 9.0, 9.0]), None, np.asarray([0.0, 0.0, 1.0])),
        "surface_center": np.asarray([1.0, 2.0, 3.0]),
        "face_id": "F053",
        "opening": True,
    }
    if svc._select_step_opening_from_feature("led", good_pick) is not True:
        failures.append("FAIL(1b): _select_step_opening_from_feature must return True for finite opening geometry")
    if not setter.calls:
        failures.append("FAIL(1b): a finite opening must call _set_selected_step_opening")
    else:
        args = setter.calls[-1][0]
        # (label, face_id, center, normal, outline_mesh)
        if str(args[0]) != "led" or str(args[1]) != "F053":
            failures.append("FAIL(1b): opening pin must carry the label + face_id")
        if not np.allclose(np.asarray(args[2], dtype=float), [1.0, 2.0, 3.0]):
            failures.append("FAIL(1b): opening pin must use surface_center as the centre")
    if not remember.calls:
        failures.append("FAIL(1b): pinning an opening must still remember the feature (for the CA menu/snap)")
    if "opening" not in svc_insp.status_var.text.lower():
        failures.append(f"FAIL(1b): status must name the selected opening, got {svc_insp.status_var.text!r}")

    setter2 = _Rec()
    svc_insp2 = types.SimpleNamespace(
        _set_selected_step_opening=setter2,
        _remember_selected_step_feature=_Rec(),
        status_var=_Status(),
        render=lambda *a, **k: None,
    )
    svc2 = Open3DInteractionService(svc_insp2)
    bad_pick = {
        "feature": (np.asarray([np.nan, 2.0, 3.0]), None, np.asarray([0.0, 0.0, 1.0])),
        "surface_center": np.asarray([np.nan, 2.0, 3.0]),
        "face_id": "F053",
        "opening": True,
    }
    if svc2._select_step_opening_from_feature("led", bad_pick) is not False:
        failures.append("FAIL(1b): a non-finite opening centre must return False (fall through to body select)")
    if setter2.calls:
        failures.append("FAIL(1b): a non-finite opening must NOT pin a selection")

    # 1c) Source: the left-click idle branch gates on the opening + returns early.
    # _on_left_button_press is decorated WITHOUT functools.wraps, so getsource on the
    # method returns the wrapper -- read the module text instead.
    import KrakenOS.UI.services.open3d_interaction as interaction_mod
    src = inspect.getsource(interaction_mod)
    if 'feature_pick.get("opening")' not in src:
        failures.append("FAIL(1c): the left-click path must detect an opening feature")
    if "_select_step_opening_from_feature(step_label, feature_pick)" not in src:
        failures.append("FAIL(1c): the left-click path must route an opening to _select_step_opening_from_feature")
    idx_open = src.find("if self._select_step_opening_from_feature(step_label, feature_pick):")
    idx_select = src.find("self.editor.select_step_component(step_label)")
    if idx_open < 0 or idx_select < 0 or idx_open > idx_select:
        failures.append("FAIL(1c): the opening branch must precede select_step_component (skip body select)")


def _section2(failures: list[str]) -> None:
    from KrakenOS.UI.services import open3d_face_assignment as fa_mod
    K_service = fa_mod.Open3DFaceAssignmentService

    # 2a) Source: the opening menu is guarded AHEAD of the body re-pick (no hop).
    src = inspect.getsource(K_service._show_surface_function_context_menu)
    if "_has_selected_step_opening()" not in src or "_show_selected_opening_context_menu" not in src:
        failures.append("FAIL(2a): the menu must branch to the opening menu when an opening is pinned")
    idx_open = src.find("_show_selected_opening_context_menu")
    idx_pick = src.find("_right_click_pick_context(event)")
    if idx_open < 0 or idx_pick < 0 or idx_open > idx_pick:
        failures.append("FAIL(2a): the opening menu must be tried BEFORE _right_click_pick_context (avoid the hop)")

    # 2b) Behavioural: opening menu offers CA actions only, from the pinned geometry.
    # _popup_context_menu is a REAL service method (not overridable via the fake
    # inspector), so let it run against a fully-featured fake menu + widget and read
    # the recorded menu back off ``_active_context_menu``.
    class _FakeMenu:
        def __init__(self, *a, **k):
            self.labels: list[str] = []
            self.posted = False

        def add_command(self, label=None, **k):
            self.labels.append(str(label))

        def add_separator(self):
            self.labels.append("---")

        def bind(self, *a, **k):
            pass

        def tk_popup(self, *a, **k):
            self.posted = True

        def unpost(self):
            pass

        def grab_release(self):
            pass

        def destroy(self):
            pass

    class _FakeWidget:
        def bind(self, seq, fn, add=None):
            return f"id::{seq}"

        def unbind(self, seq, bind_id):
            pass

    original_menu = fa_mod.tk.Menu
    fa_mod.tk.Menu = _FakeMenu
    try:
        fake = types.SimpleNamespace(
            _selected_opening_label="led",
            _selected_opening_center=np.asarray([1.0, 2.0, 3.0]),
            _selected_opening_normal=np.asarray([0.0, 0.0, 1.0]),
            _selected_opening_face_id="F053",
            editor=types.SimpleNamespace(
                _step_overlay_display_label=lambda _l: "LED",
                step_clear_aperture=lambda _l: object(),
            ),
            _vtk_widget=_FakeWidget(),
            _active_context_menu=None,
            _active_context_menu_binds=[],
            _snap_clear_aperture_to_optical_axis_from_context=lambda *a, **k: None,
            start_step_clear_aperture_pick=lambda *a, **k: None,
            _center_clear_aperture_from_context=lambda *a, **k: None,
            _clear_clear_aperture_from_context=lambda *a, **k: None,
            _clear_open3d_selection=lambda *a, **k: None,
        )
        svc = K_service(fake)
        event = types.SimpleNamespace(x_root=0, y_root=0)
        ok = svc._show_selected_opening_context_menu(event)
        posted_menu = fake._active_context_menu
        if ok is not True:
            failures.append("FAIL(2b): opening menu must return True when the pinned geometry is finite")
        if posted_menu is None or not getattr(posted_menu, "posted", False):
            failures.append("FAIL(2b): opening menu must post through _popup_context_menu")
        labels = " | ".join(getattr(posted_menu, "labels", []) if posted_menu else [])
        if "Snap Clear Aperture" not in labels:
            failures.append("FAIL(2b): opening menu must offer the center+normal axis snap")
        if "Set Clear Aperture" not in labels:
            failures.append("FAIL(2b): opening menu must offer Set Clear Aperture")
        if "Forget Clear Aperture" not in labels or "Center Clear Aperture" not in labels:
            failures.append("FAIL(2b): with a CA set, the opening menu must offer Center + Forget")
        if "Deselect opening" not in labels:
            failures.append("FAIL(2b): opening menu must offer Deselect opening")
        if "Promote" in labels:
            failures.append("FAIL(2b): opening menu must NOT offer whole-body promote items")

        # Empty geometry -> refuse, do not post.
        fake.__dict__["_active_context_menu"] = None
        fake.__dict__["_selected_opening_center"] = np.asarray([])
        if svc._show_selected_opening_context_menu(event) is not False:
            failures.append("FAIL(2b): opening menu must return False for empty/non-finite geometry")
        if fake._active_context_menu is not None:
            failures.append("FAIL(2b): opening menu must not post a menu when geometry is unresolved")
    finally:
        fa_mod.tk.Menu = original_menu


def _section3(failures: list[str]) -> None:
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector as K
    from KrakenOS.UI.services import open3d_face_assignment as fa_mod
    from KrakenOS.UI.services.open3d_interaction import Open3DInteractionService
    K_service = fa_mod.Open3DFaceAssignmentService

    # 3a) Behavioural: post binds dismissal + records the live menu; dismiss unwinds.
    class _FakeWidget:
        def __init__(self):
            self.binds: list[str] = []
            self.unbinds: list[tuple] = []

        def bind(self, seq, fn, add=None):
            self.binds.append(seq)
            return f"id::{seq}"

        def unbind(self, seq, bind_id):
            self.unbinds.append((seq, bind_id))

    class _FakeMenu:
        def __init__(self):
            self.posted = False
            self.unposted = 0
            self.bound: list[str] = []

        def bind(self, seq, fn, add=None):
            self.bound.append(seq)

        def tk_popup(self, x, y):
            self.posted = True

        def unpost(self):
            self.unposted += 1

        def grab_release(self):
            pass

        def destroy(self):
            pass

    widget = _FakeWidget()
    fake_insp = types.SimpleNamespace(
        _vtk_widget=widget,
        _active_context_menu=None,
        _active_context_menu_binds=[],
    )
    svc = K_service(fake_insp)
    menu = _FakeMenu()
    event = types.SimpleNamespace(x_root=10, y_root=20)
    svc._popup_context_menu(menu, event)
    if not menu.posted:
        failures.append("FAIL(3a): _popup_context_menu must tk_popup the menu")
    if fake_insp._active_context_menu is not menu:
        failures.append("FAIL(3a): _popup_context_menu must record the live menu")
    if len(widget.binds) != 3:
        failures.append(f"FAIL(3a): must bind 3 canvas button-press dismissals, got {widget.binds!r}")
    if len(fake_insp._active_context_menu_binds) != 3:
        failures.append("FAIL(3a): must stash the canvas bindings for later cleanup")

    svc._dismiss_active_context_menu()
    if menu.unposted < 1:
        failures.append("FAIL(3a): _dismiss_active_context_menu must unpost the menu")
    if len(widget.unbinds) != 3:
        failures.append(f"FAIL(3a): dismiss must unbind the 3 canvas dismissals, got {widget.unbinds!r}")
    if fake_insp._active_context_menu is not None:
        failures.append("FAIL(3a): dismiss must clear the live-menu reference")
    if fake_insp._active_context_menu_binds:
        failures.append("FAIL(3a): dismiss must clear the stashed bindings")
    # Re-entrancy / double-dismiss must be a harmless no-op.
    try:
        svc._dismiss_active_context_menu()
    except Exception as exc:  # pragma: no cover
        failures.append(f"FAIL(3a): a second dismiss must not raise, got {exc!r}")

    # 3b) Source: the body menu posts through _popup_context_menu (not raw tk_popup);
    #     deselect + CA snap both drop the pinned rim.
    body_src = inspect.getsource(K_service._show_surface_function_context_menu)
    if "_popup_context_menu(menu, event)" not in body_src:
        failures.append("FAIL(3b): the body menu must post through _popup_context_menu")
    if "menu.tk_popup" in body_src:
        failures.append("FAIL(3b): the body menu must not call tk_popup directly (bypasses dismissal)")
    clear_src = inspect.getsource(K._clear_open3d_selection)
    if "_clear_selected_step_opening" not in clear_src:
        failures.append("FAIL(3b): _clear_open3d_selection must drop the pinned opening (click-elsewhere)")
    snap_src = inspect.getsource(K._apply_step_feature_center_axis_pick)
    if "_clear_selected_step_opening" not in snap_src:
        failures.append("FAIL(3b): a CA snap must drop the now-stale pinned rim after the body moves")
    _ = Open3DInteractionService  # imported for symmetry / future use


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    _section1(failures)
    _section2(failures)
    _section3(failures)
    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] LED clear-aperture persistent selection + opening menu + dismiss")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] Left-click pins the CA opening only (persistent); right-click shows an "
          "opening-only menu (no hop); the popup dismisses on click-elsewhere")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
