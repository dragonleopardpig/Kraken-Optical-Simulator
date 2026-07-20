"""Display-free guard for bugs/0360 -- browser parent Hide cascades to all children.

Right-clicking a PARENT node in the elements browser (a group, or an element with
children) and choosing Hide hides the parent (when it has an element identity) and
every resolvable descendant; Show reverses it. Unresolvable descendants are skipped.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_browser_group_hide
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace

from KrakenOS.UI.panels.open3d_step_admin import Open3DStepAdminPanel


class _FakeTree:
    def __init__(self, children):
        self._children = dict(children)

    def get_children(self, iid=""):
        return tuple(self._children.get(str(iid), ()))

    def item(self, _iid, _field):
        return "Group"


class _FakePanel:
    _iter_descendant_iids = Open3DStepAdminPanel._iter_descendant_iids
    _set_element_hidden_cascade = Open3DStepAdminPanel._set_element_hidden_cascade

    def __init__(self, children, targets):
        self._tree = _FakeTree(children)
        self._targets = dict(targets)
        self.calls: list[tuple] = []
        self.inspector = SimpleNamespace(status_var=SimpleNamespace(set=lambda _s: None))

    def _resolve_iid_target(self, iid):
        return self._targets.get(str(iid), ([], None, None, None))

    def _set_element_hidden(self, rows, label, hidden, display_key, source_id):
        self.calls.append((tuple(rows), label, bool(hidden), display_key, source_id))


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []

    children = {"group": ("a", "b"), "b": ("b1",)}
    targets = {
        "a": ([2], None, None, None),
        "b": ([], "led", None, None),
        "b1": ([], None, None, "source:led-1"),
        # "group" itself resolves to nothing -- a pure group node
    }
    panel = _FakePanel(children, targets)
    panel._set_element_hidden_cascade("group", [], None, True, None, None)
    hidden_calls = {call[:2] + call[3:] for call in panel.calls if call[2]}
    if len(panel.calls) != 3:
        failures.append(f"cascade must hide the 3 resolvable descendants, got {panel.calls!r}")
    if ((2,), None, None, None) not in hidden_calls or ((), "led", None, None) not in hidden_calls:
        failures.append("cascade missed a row/label descendant")
    if ((), None, None, "source:led-1") not in hidden_calls:
        failures.append("cascade must recurse into grandchildren (the scene source)")

    # A parent WITH its own identity hides itself first, then descendants.
    panel2 = _FakePanel({"led": ("bs",)}, {"led": ([], "led", None, None), "bs": ([3], None, None, None)})
    panel2._set_element_hidden_cascade("led", [], "led", True, None, None)
    if len(panel2.calls) != 2 or panel2.calls[0][1] != "led":
        failures.append(f"a parent element must hide itself and its child, got {panel2.calls!r}")

    # Show reverses with hidden=False.
    panel3 = _FakePanel(children, targets)
    panel3._set_element_hidden_cascade("group", [], None, False, None, None)
    if any(call[2] for call in panel3.calls):
        failures.append("Show must cascade hidden=False")

    menu_src = inspect.getsource(Open3DStepAdminPanel._show_element_context_menu)
    for needle in ("_set_element_hidden_cascade", "has_children"):
        if needle not in menu_src:
            failures.append(f"the browser context menu lost its {needle} wiring")

    # bugs/0361: the 0348 trap class -- the group menu can be perfect while the ROUTER
    # swallows the right-click before it. Probe _on_tree_right_click routing directly.
    class _RouterTree:
        def __init__(self, iid):
            self._iid = iid

        def identify_row(self, _y):
            return self._iid

        def selection_set(self, _iid):
            pass

        def focus(self, _iid):
            pass

    class _RouterPanel:
        _on_tree_right_click = Open3DStepAdminPanel._on_tree_right_click

        def __init__(self, iid):
            self._tree = _RouterTree(iid)
            self.menu_iids: list[str] = []
            self.sources_menu = 0

        def _show_element_context_menu(self, _event, iid):
            self.menu_iids.append(str(iid))

        def _show_scene_sources_context_menu(self, _event):
            self.sources_menu += 1

        def _on_tree_select(self, *_a, **_k):
            pass

    event = SimpleNamespace(y=10, x_root=0, y_root=0)
    router = _RouterPanel("category:optical")
    router._on_tree_right_click(event)
    if router.menu_iids != ["category:optical"]:
        failures.append(
            "right-clicking a category header must reach the group menu "
            f"(bugs/0361), got {router.menu_iids!r}"
        )
    router_sources = _RouterPanel("category:sources")
    router_sources._on_tree_right_click(event)
    if router_sources.sources_menu != 1 or router_sources.menu_iids:
        failures.append("category:sources must keep its Add-LED menu routing")
    router_empty = _RouterPanel("empty:optical")
    router_empty._on_tree_right_click(event)
    if router_empty.menu_iids or router_empty.sources_menu:
        failures.append("empty placeholders must stay menu-less")
    router_leaf = _RouterPanel("row:3")
    router_leaf._on_tree_right_click(event)
    if router_leaf.menu_iids != ["row:3"]:
        failures.append("leaf routing regressed")

    # bugs/0364: the MV surrogate's stop row belongs to Imaging Lens, so the category
    # Hide covers the whole imaging system; a Standard row that merely mentions
    # "aperture" (the teaching scene's BS-exit stop) stays under Layout.
    class _CatPanel:
        _scene_row_category = Open3DStepAdminPanel._scene_row_category

        def __init__(self):
            self.editor = SimpleNamespace(_file_backed_stl_row_at=lambda _i: None)

    cat = _CatPanel()
    stop_row = SimpleNamespace(surface="Aperture", name="Aperture Stop", element="Aperture Stop", glass="AIR")
    if cat._scene_row_category(5, stop_row) != "lens":
        failures.append("the Aperture Stop row must categorize under Imaging Lens (bugs/0364)")
    bs_stop = SimpleNamespace(
        surface="Standard",
        name="Beam-splitter exit aperture (55x55x78 cube, fold clear-aperture 30x78)",
        element="",
        glass="AIR",
    )
    if cat._scene_row_category(1, bs_stop) != "layout":
        failures.append("a Standard row mentioning 'aperture' must stay under Layout")

    # bugs/0366: the FIRST ACTIVE ENTRY of the Scene Sources group menu must be
    # Hide/Show (cascade), never the creator.
    sources_src = inspect.getsource(Open3DStepAdminPanel._show_scene_sources_context_menu)
    if "_set_element_hidden_cascade" not in sources_src:
        failures.append("the Scene Sources group menu lost its Hide/Show cascade (bugs/0366)")
    hide_at = sources_src.find('label="Hide"')
    add_at = sources_src.find("command=self._add_illumination_led_source")
    if hide_at < 0 or add_at < 0 or hide_at > add_at:
        failures.append("Hide must come BEFORE Add in the Scene Sources menu (bugs/0366)")

    # bugs/0365: analytic-row outline actors must be row-keyed so hides cover them.
    import KrakenOS.UI.services.open3d_scene_refresh as refresh_module

    refresh_src = inspect.getsource(refresh_module)
    if "track_row_index=row_index if row_index in file_backed_rows else None" in refresh_src:
        failures.append("the outline actors regressed to file-backed-only row keying (bugs/0365)")
    if "row_index if row_index in file_backed_rows else None" in refresh_src:
        failures.append("the rays-on outline twins regressed to unkeyed rows (bugs/0365)")
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    vp_src = inspect.getsource(Kraken3DInspector._add_virtual_plane_marker_actor)
    if vp_src.count("track_row_index") < 4:
        failures.append("virtual-plane marker actors must all carry their row key (bugs/0365)")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("Browser group-hide validation failed:")
        for name in failures:
            print(f"- {name}")
        return 1
    print(
        "Browser group-hide validation passed: right-clicking a parent node Hide/Show "
        "cascades over the parent and every resolvable descendant (rows, labels, scene "
        "sources), and pure group nodes now get their own Hide/Show menu."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
