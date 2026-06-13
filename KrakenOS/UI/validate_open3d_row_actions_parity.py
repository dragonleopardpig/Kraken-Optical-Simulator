"""Validate that the 3D right-click menu mirrors core 2D row actions.

The principle: any spatially-meaningful row action available from the 2D
surface-table context menu (Flip, Move Up/Down, Group/Ungroup, Copy/Paste,
Delete, Element Settings) must be reachable from the 3D right-click on a
promoted optical-solid body. Without this parity, users who promote a STEP
overlay (especially a multi-row native achromat) lose access to actions the
table still exposes.

This validator checks contracts at the source level so the regression
surfaces immediately in CI, plus a behavioural check that flip_rows
correctly reverses + remaps rc/thickness/glass on a synthetic 3-row group
shaped like a Tier-3 native achromat.

Run from the repository root:

    python -m KrakenOS.UI.validate_open3d_row_actions_parity
"""

from __future__ import annotations

import inspect
from copy import deepcopy
from dataclasses import asdict

from KrakenOS.UI import layout_editor as le
from KrakenOS.UI.layout_editor import KrakenLayoutEditor, SurfaceRow
from KrakenOS.UI.open3d_inspector import Kraken3DInspector
from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService


def _check_source_contracts() -> list[str]:
    failures: list[str] = []

    flip_rows_src = inspect.getsource(KrakenLayoutEditor.flip_rows)
    flip_selected_src = inspect.getsource(KrakenLayoutEditor.flip_selected)
    if "def flip_rows(self, indices" not in flip_rows_src:
        failures.append("flip_rows must accept explicit indices for programmatic 3D use")
    if "flip_rows(" not in flip_selected_src:
        failures.append("flip_selected must delegate to flip_rows so 2D and 3D share the primitive")

    for attr in (
        "_lens_row_group_for_row",
        "_is_any_promoted_optical_solid_row",
        "_is_step_native_promoted_row",
        "_step_native_promotion_metadata",
    ):
        if not hasattr(KrakenLayoutEditor, attr):
            failures.append(f"KrakenLayoutEditor must expose {attr} for 3D row-action routing")

    predicate_src = inspect.getsource(Kraken3DInspector._show_scene_placement_handles)
    if "_is_any_promoted_optical_solid_row" not in predicate_src:
        failures.append(
            "_show_scene_placement_handles must enable handles for any promoted "
            "optical-solid row (Tier 2 STL or Tier 3 native), not just file-backed STL"
        )

    menu_src = inspect.getsource(Open3DFaceAssignmentService._show_surface_function_context_menu)
    cascade_src = inspect.getsource(Open3DFaceAssignmentService._build_row_actions_cascade)
    if "_build_row_actions_cascade" not in menu_src:
        failures.append("right-click menu must invoke _build_row_actions_cascade")

    required_action_hooks = (
        "flip_rows",
        "move_up",
        "move_down",
        "duplicate_selected",
        "delete_selected",
        "group_selected_as_element",
        "ungroup_selected_elements",
        "open_element_settings",
    )
    for hook in required_action_hooks:
        if hook not in cascade_src:
            failures.append(f"Row Actions cascade must wire {hook} so 2D action is reachable in 3D")
    if "single_row_scene_flip" not in cascade_src or "rotate_scene_row_pose_world_axis" not in cascade_src:
        failures.append("Open 3D Row Actions must enable Flip for a single promoted STEP/STL scene row")

    # An imported STEP must be promotable into a ray-traceable optical element
    # straight from the right-click menu (not only the top CAD/target dropdown):
    # Optical Solid Row (mesh solid), Analytic Surfaces and Native Rows (in-path
    # surfaces). Analytic/Native were dropdown-only, so a right-click only offered
    # the mesh-solid path -- the wrong element type for a light-through element.
    required_step_promote_options = (
        ("Promote STEP to Optical Solid Row", "_promote_step_from_context"),
        ("Promote STEP to Analytic Surfaces", "_promote_step_to_analytic_from_context"),
        ("Promote STEP to Native Rows", "_promote_step_to_native_from_context"),
    )
    for option_label, hook in required_step_promote_options:
        if option_label not in menu_src:
            failures.append(f"right-click STEP menu must offer '{option_label}' so an imported STEP is promotable from the canvas")
        if hook not in menu_src:
            failures.append(f"right-click STEP menu must wire {hook}")

    return failures


def _check_flip_rows_behaviour() -> list[str]:
    failures: list[str] = []
    le._load_3d_backends()
    app = KrakenLayoutEditor(headless=True)
    try:
        app.load_layouts()
        app.load_layout_by_name("Machine Vision 150Mm Measured", refresh=False)
        rows = app.rows
        template = next((row for row in rows if row.surface == "Standard"), None)
        if template is None:
            failures.append("MV150 fixture has no Standard row to template the synthetic group from")
            return failures
        synthetic_group_spec = [
            (28.5, 9.0, "BK7", "Front sphere"),
            (-31.0, 2.58, "F2", "Cemented sphere"),
            (-200.0, 0.0, "AIR", "Back asphere"),
        ]
        achr: list[SurfaceRow] = []
        promotion_meta = {"row_indices": [1, 2, 3]}
        for rc, th, glass, name in synthetic_group_spec:
            row = SurfaceRow(**asdict(template))
            row.surface = "Standard"
            row.rc = float(rc)
            row.thickness = float(th)
            row.glass = glass
            row.name = name
            row.advanced = {"StepNativePromotion": dict(promotion_meta)}
            achr.append(row)
        rows[1:4] = achr
        app._sync_table()

        group = app._lens_row_group_for_row(2)
        if group != [1, 2, 3]:
            failures.append(f"_lens_row_group_for_row should return sibling indices [1,2,3], got {group}")
            return failures

        rc_before = [rows[i].rc for i in group]
        th_before = [rows[i].thickness for i in group]
        glass_before = [rows[i].glass for i in group]
        if not app.flip_rows(group):
            failures.append("flip_rows returned False for a valid 3-row group")
            return failures
        rc_after = [rows[i].rc for i in group]
        th_after = [rows[i].thickness for i in group]
        glass_after = [rows[i].glass for i in group]

        expected_rc = [-rc for rc in reversed(rc_before)]
        expected_th = list(reversed(th_before[:-1])) + [th_before[-1]]
        expected_glass = list(reversed(glass_before[:-1])) + [glass_before[-1]]
        if any(abs(a - b) > 1e-9 for a, b in zip(rc_after, expected_rc)):
            failures.append(f"flip_rows rc remap wrong: expected {expected_rc}, got {rc_after}")
        if any(abs(a - b) > 1e-9 for a, b in zip(th_after, expected_th)):
            failures.append(f"flip_rows thickness remap wrong: expected {expected_th}, got {th_after}")
        if glass_after != expected_glass:
            failures.append(f"flip_rows glass remap wrong: expected {expected_glass}, got {glass_after}")

        if app.flip_rows([1]):
            failures.append("flip_rows on a single index should return False (nothing to reverse)")
    finally:
        app.destroy()
    return failures


def main() -> int:
    failures: list[str] = []
    failures.extend(_check_source_contracts())
    failures.extend(_check_flip_rows_behaviour())
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("Open 3D row-actions parity contract validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
