"""Guard for bugs/0639 — the whole optical-axis line is selectable, not just the dashes.

User (empty scene): "click the blue dotted line -> highlights; click the empty space
between the dots -> doesn't. Supposed to be the case?" The guide is drawn DASHED, so only
the dots are solid pickable geometry. A plain left-click that hit nothing else now resolves
the axis by proximity to the guide line (`_optical_axis_info_near_display_xy`), so the whole
line highlights -- gated on an empty pick (actor_key is None) so a click on an element the
axis crosses still selects the element.

Check (source contract): the left-button handler proximity-resolves the axis in the plain
(no-mode) path, gated on `actor_key is None`.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0639_axis_gap_select
"""

from __future__ import annotations

import inspect


def run_checks():
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services import open3d_interaction as interaction_module

    # _on_left_button_press is timing-decorated (getsource returns the wrapper), so read the
    # module source, where the real handler body lives.
    src = inspect.getsource(interaction_module)
    gate = "if axis_info is None and actor_key is None:"
    resolve = "_optical_axis_info_near_display_xy((x, y), tolerance_px=12.0)"
    # The gate must appear, and immediately precede the proximity resolution (within a few
    # lines) -- the empty-pick fallback that makes the WHOLE dashed line selectable.
    ok_order = gate in src and resolve in src and 0 <= (src.index(resolve) - src.index(gate)) <= 200
    if not ok_order:
        ok = False
        notes.append(
            "FAIL: bugs/0639: the plain left-click does not proximity-resolve the axis when the "
            "pick is empty -- gap clicks on the dashed guide won't highlight the whole line"
        )
    else:
        notes.append("PASS: a plain click on an empty gap resolves the axis by proximity (whole line selectable)")

    # The helper it relies on must still exist on the inspector.
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    if not hasattr(Kraken3DInspector, "_optical_axis_info_near_display_xy"):
        ok = False
        notes.append("FAIL: bugs/0639: _optical_axis_info_near_display_xy is gone")
    else:
        notes.append("PASS: the proximity helper is present")

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for line in notes:
        print(line)
    print("Axis-gap-select validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
