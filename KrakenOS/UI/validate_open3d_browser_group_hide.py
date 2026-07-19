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
