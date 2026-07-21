"""Display-free guard for bugs/0381 -- Swap/Import lens block safety.

Two defects behind the "after lens swap the whole scene is gone" flag:
  * ``_imaging_lens_block_indices`` spanned first-front -> LAST-rear, so a genuine swap on
    a two-lens / stray-"rear vertex" scene would splice away everything between. Now it
    returns the TIGHT single block (first front -> its FIRST rear) and refuses a block that
    contains a foreign element (a promoted solid / Object / Image).
  * "Import Lens from Folder" REPLACES the whole scene (distinct from Swap, which keeps it),
    and the two sit next to each other in the menu. ``_import_would_discard_scene`` drives a
    confirmation so Import can't silently wipe a real assembly.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_lens_swap_block_safety
"""

from __future__ import annotations


class _Row:
    def __init__(self, name):
        self.name = name


def _editor(rows, **paths):
    from KrakenOS.UI.services import layout_table_workbench as _ltw
    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin

    # ``Path`` is late-bound into this module by ``_sync_layout_globals`` at editor init;
    # a __new__ fake never ran it, so inject it here exactly as init would.
    if getattr(_ltw, "Path", None) is None:
        import pathlib

        _ltw.Path = pathlib.Path

    ed = LayoutTableWorkbenchMixin.__new__(LayoutTableWorkbenchMixin)
    ed.rows = [_Row(n) for n in rows]
    for k in ("imported_camera_step_path", "imported_led_step_path", "imported_optical_step_path"):
        setattr(ed, k, paths.get(k))
    return ed


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []

    def block(rows):
        return _editor(rows)._imaging_lens_block_indices()

    LENS = ["Blackbox Group 1", "Aperture Stop", "Blackbox Group 2"]

    # --- tight block detection ------------------------------------------------------
    cases = {
        "lens-datum naming": (["Object", "BS", "Lens Front Datum", *LENS, "Lens Rear Datum", "prism", "Image"], (2, 6)),
        "vertex naming": (["Object", "BS", "gap", "Front Optical Vertex Datum", *LENS, "Rear Optical Vertex Datum", "Image"], (3, 7)),
        "two blocks -> first tight": (["Object", "Front Datum", *LENS, "Rear Datum", "x", "Front Datum", *LENS, "Rear Datum", "Image"], (1, 5)),
        "stray camera rear later": (["Object", "Lens Front Datum", *LENS, "Lens Rear Datum", "Camera Rear Vertex", "Image"], (1, 5)),
    }
    for tag, (rows, expected) in cases.items():
        got = block(rows)
        if got != expected:
            failures.append(f"block({tag}): got {got}, expected {expected}")

    # a foreign element inside the block -> refuse to swap (never wipe it)
    if block(["Object", "Lens Front Datum", "Promoted OPTICAL STEP optical solid", "Lens Rear Datum", "Image"]) != (None, None):
        failures.append("block(promoted inside): must return (None, None) so the swap can't wipe the solid")
    if block(["Object", "BS", "Image"]) != (None, None):
        failures.append("block(no lens): must return (None, None)")
    # a lone front datum with no matching rear -> no block (no wild splice)
    if block(["Object", "Lens Front Datum", *LENS, "Image"]) != (None, None):
        failures.append("block(front, no rear): must return (None, None)")

    # --- import-would-discard-scene predicate --------------------------------------
    bare = _editor(["Object", "Lens Front Datum", *LENS, "Lens Rear Datum", "Image"])
    if bare._import_would_discard_scene():
        failures.append("discard(bare lens): a plain single-lens scene must NOT trigger the Import warning")

    for tag, kw in (
        ("camera overlay", {"imported_camera_step_path": "x.step"}),
        ("led overlay", {"imported_led_step_path": "x.step"}),
        ("optical overlay", {"imported_optical_step_path": "x.step"}),
    ):
        ed = _editor(["Object", "Lens Front Datum", "Lens Rear Datum", "Image"], **kw)
        if not ed._import_would_discard_scene():
            failures.append(f"discard({tag}): must trigger the Import warning")

    promoted = _editor(["Object", "Promoted OPTICAL STEP optical solid", "Lens Front Datum", "Lens Rear Datum", "Image"])
    if not promoted._import_would_discard_scene():
        failures.append("discard(promoted solid): a promoted solid must trigger the Import warning")

    # --- swap PRESERVES the lens overlay scene pose (bugs/0381 misplacement) --------
    ed = _editor(["Object", "Lens Front Datum", "Lens Rear Datum", "Image"])
    ed.imported_lens_step_path = "old.step"
    ed.lens_step_largest_component_only = True
    ed.lens_step_rotation_x_deg = 0.0
    ed.lens_step_rotation_y_deg = 90.0   # user aligned the lens onto the fold leg
    ed.lens_step_rotation_z_deg = 45.0
    ed.lens_step_axis_offset_xy = [0.5, 0.5]
    ed.lens_step_placement_offset_xyz = [1.0, 2.0, -3.849]
    ed.lens_step_reverse_direction = True
    # The fresh single-lens folder's settings carry a DEFAULT (on-axis) pose -- the swap
    # must NOT apply it over the user's fold-leg alignment.
    ed._apply_swapped_lens_step_settings({
        "lens_step_path": "new.step",
        "lens_step_largest_component_only": False,
        "lens_step_rotation_x_deg": 0.0, "lens_step_rotation_y_deg": 0.0, "lens_step_rotation_z_deg": 0.0,
        "lens_step_axis_offset_xy": [0.0, 0.0], "lens_step_placement_offset_xyz": [0.0, 0.0, 0.0],
        "lens_step_reverse_direction": False,
    })
    if str(getattr(ed, "imported_lens_step_path", "")) != "new.step":
        failures.append("pose: the STEP path must switch to the new lens")
    if getattr(ed, "lens_step_largest_component_only", None) is not False:
        failures.append("pose: largest-component flag must follow the new lens folder")
    if (getattr(ed, "lens_step_rotation_y_deg", 0.0), getattr(ed, "lens_step_rotation_z_deg", 0.0)) != (90.0, 45.0):
        failures.append("pose: the lens rotation must be PRESERVED across a swap (not reset to the folder default)")
    if getattr(ed, "lens_step_placement_offset_xyz", None) != [1.0, 2.0, -3.849]:
        failures.append("pose: the placement offset must be PRESERVED across a swap")
    if getattr(ed, "lens_step_axis_offset_xy", None) != [0.5, 0.5]:
        failures.append("pose: the axis offset must be PRESERVED across a swap")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("Lens-swap block-safety validation failed:")
        for name in failures:
            print(f"- {name}")
        return 1
    print(
        "Lens-swap block-safety validation passed: the block detector returns the TIGHT "
        "single lens block (refusing one that contains a foreign element), and Import warns "
        "before it would discard a real assembly (overlay / promoted solid)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
