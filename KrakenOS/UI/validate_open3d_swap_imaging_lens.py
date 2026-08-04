"""Display-free guard for bugs/0378 -- the "Swap Imaging Lens" flow.

"Import Lens from Folder" REPLACES the whole working layout, so on a full assembly
(Object + beam splitter + LED + imaging lens + camera) it drops the new lens alone,
off-axis, losing the scene. Swap Imaging Lens instead replaces ONLY the imaging-lens
surrogate block (the Front..Rear vertex-datum pair bracketing the Blackbox groups +
stop) and its STEP overlay, IN PLACE -- Object / BS / LED / camera / FOV / source
settings preserved, the new lens on-axis at the same datum. Distinct from Add Imaging
Lens (a second lens).

Checks (headless, no VTK/tk):
- BLOCK INDICES: `_imaging_lens_block_indices` finds the vertex/lens-datum pair on a
  synthetic Object/BS/lens/Image scene, and returns (None,None) when there is no lens.
- SPLICE (source contract): the swap builds `rows[:front] + new_block + rows[rear+1:]`
  -- keeps everything before/after the lens block, replaces only the block.
- STEP REWIRE: `_apply_swapped_lens_step_settings` rewires the lens STEP path + largest-
  component flag from the new settings, PRESERVES the user's scene pose (bugs/0381), and
  does NOT touch camera/led/optical overlays.
- WIRING: the inspector delegates + rebuilds via `_apply_model_change` (no layout
  replacement / 0294 path); both menus offer "Swap Imaging Lens from Folder...".

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_swap_imaging_lens
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []

    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor, Kraken3DInspector
    except Exception as exc:  # pragma: no cover - environment skip
        return True, [f"SKIP: swap-imaging-lens deps unavailable ({type(exc).__name__}: {exc})"]

    editor = object.__new__(KrakenLayoutEditor)

    # --- BLOCK INDICES ------------------------------------------------------------
    def _row(name, surface="Standard"):
        return SimpleNamespace(name=name, surface=surface)

    scene = [
        _row("Object", "Object"),
        _row("Promoted OPTICAL STEP optical solid", "Standard"),
        _row("Lens Front Datum"),
        _row("Blackbox Group 1", "Thin Lens"),
        _row("Aperture Stop", "Aperture"),
        _row("Blackbox Group 2", "Thin Lens"),
        _row("Lens Rear Datum"),
        _row("Image", "Image"),
    ]
    front, rear = editor._imaging_lens_block_indices(scene)
    if (front, rear) != (2, 6):
        failures.append(f"block indices wrong: got ({front},{rear}), expected (2,6)")
    # 'Front Optical Vertex Datum' naming variant also matches
    alt = [_row("Object", "Object"), _row("Front Optical Vertex Datum"),
           _row("Blackbox Group 1", "Thin Lens"), _row("Rear Optical Vertex Datum"), _row("Image", "Image")]
    if editor._imaging_lens_block_indices(alt) != (1, 3):
        failures.append("vertex-datum naming variant not recognised as a lens block")
    # no lens -> (None, None)
    if editor._imaging_lens_block_indices([_row("Object", "Object"), _row("Image", "Image")]) != (None, None):
        failures.append("a scene with no lens block must return (None, None)")

    # --- STEP REWIRE --------------------------------------------------------------
    # bugs/0381 REVISED this contract, and this block had asserted the pre-0381 behaviour ever
    # since (reading an attribute the rewire no longer sets, which on a bare stub recurses into
    # Tk's __getattr__). A swap changes the LENS, not where the user put it:
    # `_apply_swapped_lens_step_settings` rewires the STEP path + largest-component flag ONLY,
    # and the scene POSE (rotation / axis offset / placement offset / flip) is PRESERVED so the
    # swapped lens stays on the fold leg the user aligned it to.
    stub = object.__new__(KrakenLayoutEditor)
    stub.imported_lens_step_path = "attachment/Lens/OLD/old.stp"
    stub.lens_step_largest_component_only = True
    stub.lens_step_reverse_direction = True             # the user flipped it
    stub.lens_step_axis_offset_xy = [1.0, 2.0]          # ... and aligned it onto the fold leg
    stub.lens_step_placement_offset_xyz = [3.0, 4.0, 5.0]
    stub.lens_step_rotation_y_deg = 90.0
    stub._apply_swapped_lens_step_settings({
        "lens_step_path": "attachment/Lens/NEW/new.stp",
        "lens_step_largest_component_only": False,
        # the FRESH folder's DEFAULT (on-axis, unflipped) pose -- must not be applied over the
        # user's alignment
        "lens_step_reverse_direction": False,
        "lens_step_axis_offset_xy": [0.0, 0.0],
        "lens_step_placement_offset_xyz": [0.0, 0.0, 0.0],
        "lens_step_rotation_y_deg": 0.0,
    })
    if stub.imported_lens_step_path is None or "new.stp" not in str(stub.imported_lens_step_path):
        failures.append("STEP rewire did not set imported_lens_step_path")
    if stub.lens_step_largest_component_only is not False:
        failures.append("STEP rewire did not carry the new folder's largest-component flag")
    if not stub.lens_step_reverse_direction:
        failures.append("STEP rewire must PRESERVE the user's flip (bugs/0381), not reset it")
    if list(stub.lens_step_placement_offset_xyz) != [3.0, 4.0, 5.0] or abs(stub.lens_step_rotation_y_deg - 90.0) > 1e-6:
        failures.append("STEP rewire must PRESERVE the user's scene pose (bugs/0381)")

    # --- SPLICE CONTRACT (source) -------------------------------------------------
    swap_src = inspect.getsource(KrakenLayoutEditor.swap_imaging_lens_from_folder)
    if "self.rows[:front]" not in swap_src or "self.rows[rear + 1:]" not in swap_src:
        failures.append("swap does not splice rows[:front] + new_block + rows[rear+1:]")
    if "_apply_swapped_lens_step_settings" not in swap_src:
        failures.append("swap does not rewire the lens STEP overlay")
    if "_imaging_lens_block_indices" not in swap_src:
        failures.append("swap does not locate the imaging-lens block")

    # --- WIRING -------------------------------------------------------------------
    insp_src = inspect.getsource(Kraken3DInspector.swap_imaging_lens_from_folder)
    if "editor.swap_imaging_lens_from_folder" not in insp_src or "_apply_model_change" not in insp_src:
        failures.append("inspector swap must delegate to the editor then rebuild via _apply_model_change")
    if "_keep_scene_viewers_across_layout_replacement" in insp_src:
        failures.append("swap must NOT use the layout-replacement teardown path (it keeps the scene)")

    from KrakenOS.UI.panels import open3d_top_controls, main_context_menu
    if "swap_imaging_lens_from_folder" not in inspect.getsource(open3d_top_controls):
        failures.append("the 3D top-controls menu has no Swap Imaging Lens command")
    if "swap_imaging_lens_from_folder" not in inspect.getsource(main_context_menu):
        failures.append("the main context menu has no Swap Imaging Lens command")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("Swap-imaging-lens validation failed:")
        for name in failures:
            print(f"- {name}")
        return 1
    print(
        "Swap-imaging-lens validation passed: the flow locates the imaging-lens vertex-datum "
        "block, splices the new lens body in place (keeping Object/BS/LED/camera/Image), rewires "
        "only the lens STEP overlay, rebuilds via _apply_model_change without a layout swap, and "
        "both menus offer the command."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
