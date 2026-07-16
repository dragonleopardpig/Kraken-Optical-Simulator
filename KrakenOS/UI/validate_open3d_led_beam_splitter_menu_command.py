#!/usr/bin/env python3
"""Display-free guard for bugs/0320: the LED right-click "Add Beam Splitter to LED"
actions must be DIRECT single-click commands, never an "... > Cube/Plate" CASCADE.

Why (bugs/0320): the Open 3D inspector embeds a VTK render-window interactor that
competes for the pointer inside its window. A Tk cascade needs a hover/pointer-enter to
*post* its submenu; under the VTK interactor that submenu frequently never posts, so the
user clicks the "Add Beam Splitter to LED" parent, nothing opens, nothing fires, and
there is no status line (the 2026-07-16 07:47 recording -- "nothing happened, no status
bar message"). The command, the menu build, and a programmatic ``submenu.invoke`` all
work headless; only the interactive cascade in the VTK window is unreliable. A single-
click command needs no hover-to-post and fires reliably -- the same reason the direct
"Hide <STEP>" items in this very menu always worked. (The 2D main table's cascades are
fine: there is no VTK interactor there, so the guard is scoped to the LED menu.)

What it checks (behavioural, tk-free):
  A. the LED element menu adds NO cascade whose label mentions "Beam Splitter".
  B. it adds exactly two DIRECT commands -- "Add Beam Splitter to LED (Cube)" and
     "Add Beam Splitter to LED (Plate)".
  C. invoking each command reaches the real handler and calls
     ``editor.add_beam_splitter_to_led(kind)`` with the matching kind -- proving a single
     click actually fires the orchestration end to end.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_led_beam_splitter_menu_command

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

from types import SimpleNamespace


class _RecordingMenu:
    """Records menu entries (type + label + command) without a tk master."""

    def __init__(self) -> None:
        self.entries: list[dict] = []

    def add_command(self, label=None, command=None, **_kw) -> None:
        self.entries.append({"type": "command", "label": str(label), "command": command})

    def add_separator(self) -> None:
        self.entries.append({"type": "separator", "label": "---", "command": None})

    def add_cascade(self, label=None, menu=None, **_kw) -> None:
        self.entries.append({"type": "cascade", "label": str(label), "command": None})


def _build_service(recorded_kinds: "list[str]"):
    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService

    editor = SimpleNamespace(
        _step_overlay_display_label=lambda lbl: str(lbl),
        _step_path_for_label=lambda lbl: None,  # -> BS<->LED glue unavailable
        optical_led_glued=lambda: False,
        rows=[],
        _file_backed_stl_row_at=lambda i: None,
        _is_any_promoted_optical_solid_row=lambda r: False,
        open_optical_solid_face_role_editor=lambda *a, **k: None,
        # the real _add_beam_splitter_to_led_from_context calls this:
        add_beam_splitter_to_led=lambda kind: recorded_kinds.append(str(kind)),
        append_debug=lambda *a, **k: None,
        status_var=SimpleNamespace(set=lambda *a, **k: None),
    )
    inspector = SimpleNamespace(
        editor=editor,
        status_var=SimpleNamespace(set=lambda *a, **k: None),
        append_debug=lambda *a, **k: None,
    )
    return Open3DFaceAssignmentService(inspector)


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []

    recorded_kinds: list[str] = []
    svc = _build_service(recorded_kinds)
    menu = _RecordingMenu()
    added = svc.append_element_context_actions(menu, step_label="led")
    if not added:
        failures.append("FAIL: led element menu added nothing")

    labels = [e["label"] for e in menu.entries]

    # A) No Beam Splitter CASCADE -- the submenu won't post under the VTK interactor.
    bs_cascades = [
        e for e in menu.entries if e["type"] == "cascade" and "Beam Splitter" in e["label"]
    ]
    if bs_cascades:
        failures.append(
            "FAIL: LED menu still uses a Beam Splitter CASCADE "
            f"(submenu won't post over the VTK interactor): {[e['label'] for e in bs_cascades]}"
        )

    # B) Two DIRECT commands.
    cube = [
        e
        for e in menu.entries
        if e["type"] == "command" and e["label"] == "Add Beam Splitter to LED (Cube)"
    ]
    plate = [
        e
        for e in menu.entries
        if e["type"] == "command" and e["label"] == "Add Beam Splitter to LED (Plate)"
    ]
    if len(cube) != 1:
        failures.append(
            f"FAIL: expected one direct 'Add Beam Splitter to LED (Cube)' command, got {len(cube)} (labels={labels})"
        )
    if len(plate) != 1:
        failures.append(
            f"FAIL: expected one direct 'Add Beam Splitter to LED (Plate)' command, got {len(plate)} (labels={labels})"
        )

    # C) Invoking each direct command fires the real handler -> editor.add_beam_splitter_to_led(kind).
    if cube and callable(cube[0]["command"]):
        cube[0]["command"]()
    if plate and callable(plate[0]["command"]):
        plate[0]["command"]()
    if recorded_kinds != ["cube", "plate"]:
        failures.append(
            "FAIL: single-click commands did not fire add_beam_splitter_to_led('cube') then "
            f"('plate'); recorded={recorded_kinds}"
        )

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0320 LED 'Add Beam Splitter' must be direct commands, not a cascade")
        for item in failures:
            print(f"  - {item}")
        return 1
    print(
        "[PASS] LED 'Add Beam Splitter to LED (Cube/Plate)' are direct single-click commands "
        "that fire the orchestration (bugs/0320)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
