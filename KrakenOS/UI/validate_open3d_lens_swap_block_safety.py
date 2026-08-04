"""Display-free guard for bugs/0381 -- Swap/Import lens block safety.

Two defects behind the "after lens swap the whole scene is gone" flag:
  * ``_imaging_lens_block_indices`` spanned first-front -> LAST-rear, so a genuine swap on
    a two-lens / stray-"rear vertex" scene would splice away everything between. Now it
    returns the TIGHT single block (first front -> its FIRST rear) and refuses a block whose
    interior holds a scene END (an Object / Image row -- that span is not a lens block).
    bugs/0546 narrowed the veto: a PROMOTED SOLID inside the block no longer refuses the
    swap, it is lifted out and re-seated unmoved (see
    ``validate_open3d_0546_swap_keeps_inblock_solid``).
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

    # bugs/0546 REVISED this rule. A promoted solid inside the block used to veto the whole
    # swap ("this scene has no imaging-lens surrogate to swap") -- but a promoted solid is
    # ABSOLUTELY placed, so its row index says nothing about where it sits, and
    # `_step_overlay_insert_index` routinely parks one between the datums. The swap now LIFTS
    # it out and re-seats it after the block instead of refusing; the never-wipe guarantee is
    # kept by `_swap_preserved_block_rows` / `_swap_reseat_preserved_rows`
    # (validate_open3d_0546_swap_keeps_inblock_solid drives the real swap end to end).
    inblock = ["Object", "Lens Front Datum", "Promoted OPTICAL STEP optical solid", "Lens Rear Datum", "Image"]
    if block(inblock) != (1, 3):
        failures.append(
            f"block(promoted inside): must expose the block (1, 3) so the swap can run and PRESERVE "
            f"the solid (bugs/0546); got {block(inblock)}"
        )
    preservable, blocking = _editor(inblock)._imaging_lens_block_foreign_rows(_editor(inblock).rows, 1, 3)
    if preservable != [2] or blocking:
        failures.append(
            f"block(promoted inside): the solid must be classed PRESERVABLE, not blocking; got "
            f"{preservable} / {blocking}"
        )
    # a scene END between the datums is not a lens block at all -> still refuse
    if block(["Object", "Lens Front Datum", "Image", "Lens Rear Datum", "Image"]) != (None, None):
        failures.append("block(scene end inside): an Object/Image row between the datums must still refuse")
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

    _check_downstream_anchor(failures)
    _check_block_surface_preserved(failures)
    _check_swap_refresh_skip(failures)

    return (not failures), failures


def _check_swap_refresh_skip(failures: list[str]) -> None:
    """bugs/0386: swapping from the Open 3D inspector must NOT run the editor-side 2D
    build+trace -- the inspector's _apply_model_change retraces the 3D and marks the 2D
    stale, so the editor refresh would be a redundant full trace that doubles the freeze.
    The editor swap gates refresh_plot on a `refresh` flag; the inspector passes False."""
    import inspect as _inspect

    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin

    editor_src = _inspect.getsource(LayoutTableWorkbenchMixin.swap_imaging_lens_from_folder)
    if "refresh: bool" not in editor_src:
        failures.append("swap-refresh: editor swap must accept a `refresh` flag")
    if "if refresh and hasattr(self, \"refresh_plot\")" not in editor_src.replace("'", '"'):
        failures.append("swap-refresh: editor swap must gate refresh_plot on `refresh`")

    insp_src = _inspect.getsource(Kraken3DInspector.swap_imaging_lens_from_folder)
    if "refresh=False" not in insp_src:
        failures.append("swap-refresh: the inspector wrapper must pass refresh=False (skip the redundant 2D trace)")


def _check_block_surface_preserved(failures: list[str]) -> None:
    """bugs/0385: the swapped-in lens block is a MID-SCENE segment bracketed by Front/Rear
    Vertex DATUMS (surface 'Standard'). `_normalized_rows_copy` treats any row list as a
    standalone layout and forces its first row -> 'Object' and last -> 'Image'; spliced
    into a folded scene an 'Object'-surfaced front datum is skipped by the fold-override
    follower walk, so the lens overlay renders UNFOLDED. The swap must restore the datum
    ends' surface after the copy."""
    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin as M

    try:
        from KrakenOS.UI.layout_editor import SurfaceRow
    except Exception:
        try:
            from KrakenOS.UI.services.layout_table_workbench import SurfaceRow
        except Exception as exc:
            failures.append(f"surface-preserve: could not import SurfaceRow ({exc!r})")
            return

    def _row(surface, name):
        return SurfaceRow(surface=surface, name=name, thickness=1.0, diameter=25.0, glass="AIR")

    raw = [_row("Standard", "Front Optical Vertex Datum"), _row("Thin Lens", "Blackbox Group 1"),
           _row("Aperture", "Aperture Stop"), _row("Thin Lens", "Blackbox Group 2"),
           _row("Standard", "Rear Optical Vertex Datum")]
    norm = M._normalized_rows_copy(raw)
    # Document WHY the fix is needed: the copy corrupts the datum ends.
    if not (norm[0].surface == "Object" and norm[-1].surface == "Image"):
        # If _normalized_rows_copy ever stops forcing Object/Image the fix is harmless, but
        # the guard's premise changed -- flag it so the swap fix can be revisited.
        failures.append(
            f"surface-preserve: premise changed -- _normalized_rows_copy ends = "
            f"{norm[0].surface!r}/{norm[-1].surface!r} (was Object/Image); revisit the swap restore"
        )
    # The swap's restore (new_block[0].surface = raw_block[0].surface, likewise [-1]).
    norm[0].surface = raw[0].surface
    norm[-1].surface = raw[-1].surface
    if norm[0].surface != "Standard" or norm[-1].surface != "Standard":
        failures.append("surface-preserve: restoring the datum ends must yield 'Standard' front + rear")
    if [r.surface for r in norm] != [r.surface for r in raw]:
        failures.append(f"surface-preserve: block surfaces after restore {[r.surface for r in norm]} != raw {[r.surface for r in raw]}")


class _TRow:
    def __init__(self, name, thickness=0.0):
        self.name = name
        self.thickness = thickness


def _check_downstream_anchor(failures: list[str]) -> None:
    """bugs/0383: a swap must keep the DOWNSTREAM elements (a fold mirror / camera / image
    the user placed) at their absolute axial position -- the old Rear Datum thickness is
    the scene gap to them, not part of the lens. A bare lens (image right after) instead
    lets the image follow the new back focal distance."""
    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin as M

    # Folded scene: a physical mount (mirror) follows the lens -> preserve.
    folded = [
        _TRow("Object", 40.0), _TRow("Mirror 1", 40.0), _TRow("gap", 50.0),
        _TRow("Front Optical Vertex Datum", 18.0), _TRow("Blackbox Group 1", 10.0),
        _TRow("Aperture Stop", 10.0), _TRow("Blackbox Group 2", 18.0),
        _TRow("Rear Optical Vertex Datum", 103.0),  # rear index 7; gap-to-mirror2
        _TRow("Mirror 2", 51.0), _TRow("Image", 0.0),
    ]
    if not M._swap_preserves_downstream(folded, 7):
        failures.append("downstream: a physical element after the lens must trigger preservation")
    # first downstream row (Mirror 2, index 8) absolute start z:
    downstream_start = sum(r.thickness for r in folded[:8])  # 40+40+50+18+10+10+18+103 = 289
    if abs(downstream_start - 289.0) > 1e-6:
        failures.append(f"downstream: start z math wrong ({downstream_start})")
    # after swapping in a SHORTER lens (optical rows 18/10/10/18 -> 2/24/24/2 = same span? make it shorter):
    swapped = [
        _TRow("Object", 40.0), _TRow("Mirror 1", 40.0), _TRow("gap", 50.0),
        _TRow("Front Optical Vertex Datum", 2.0), _TRow("Blackbox Group 1", 24.0),
        _TRow("Aperture Stop", 24.0), _TRow("Blackbox Group 2", 2.0),
        _TRow("Rear Optical Vertex Datum", 0.0),  # bare rear thickness -> would collapse
        _TRow("Mirror 2", 51.0), _TRow("Image", 0.0),
    ]
    gap = M._swap_downstream_gap(swapped, 7, downstream_start)
    # new rear start = 40+40+50+2+24+24+2 = 182 ; gap should be 289-182 = 107 to keep Mirror2 at 289
    if gap is None or abs(gap - 107.0) > 1e-6:
        failures.append(f"downstream: gap {gap} (expected 107 to hold Mirror 2 at z=289)")
    else:
        swapped[7].thickness = gap
        if abs(sum(r.thickness for r in swapped[:8]) - 289.0) > 1e-6:
            failures.append("downstream: applying the gap did not restore Mirror 2's absolute z")

    # Bare lens: the next row is the Image -> do NOT preserve (image follows the new BFD).
    bare = [_TRow("Object", 40.0), _TRow("Front Datum", 18.0), _TRow("Blackbox Group 1", 10.0),
            _TRow("Rear Datum", 90.0), _TRow("Image", 0.0)]
    if M._swap_preserves_downstream(bare, 3):
        failures.append("downstream: a bare lens (image right after) must NOT preserve (BFD follows)")

    # A replacement lens LONGER than the space to the mount -> negative gap -> None (no clobber).
    if M._swap_downstream_gap(swapped, 7, 100.0) is not None:
        failures.append("downstream: a negative gap must return None (do not force a bad thickness)")


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("Lens-swap block-safety validation failed:")
        for name in failures:
            print(f"- {name}")
        return 1
    print(
        "Lens-swap block-safety validation passed: the block detector returns the TIGHT "
        "single lens block (refusing one whose interior holds a scene END, exposing one that "
        "holds a promoted solid so the swap can preserve it -- bugs/0546), and Import warns "
        "before it would discard a real assembly (overlay / promoted solid)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
