"""Validate first-open Open 3D refresh policy for promoted STEP solids."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from KrakenOS.UI.services.open3d_trace_refresh import Open3DTraceRefreshService


@dataclass(frozen=True)
class PromotedStepRefreshCheck:
    check: str
    ok: bool
    detail: str


class _FakeInspector:
    _last_refresh_sampling_mode: str | None = None


class _FakeEditor:
    def __init__(self, *, promoted_rows: bool, transient_overlay: bool = False) -> None:
        self.rows = [
            {
                "advanced": {
                    "Solid_3d_stl": "/tmp/fake_promoted.step",
                    "OpticalSolidSourceFormat": "STEP",
                }
            }
        ] if promoted_rows else []
        self._active_preview_sampling_mode = "world_envelope"
        self.transient_overlay = bool(transient_overlay)
        self.current_preview_calls = 0
        self.build_calls = 0
        self.build_kwargs: list[dict[str, Any]] = []

    def _step_path_for_label(self, label: str) -> str | None:
        if label == "optical" and self.transient_overlay:
            return "/tmp/transient.step"
        return None

    def _is_open3d_promoted_optical_solid_row(self, row: Any) -> bool:
        advanced = row.get("advanced", {}) if isinstance(row, dict) else {}
        return bool(advanced.get("Solid_3d_stl")) and str(
            advanced.get("OpticalSolidSourceFormat", "")
        ).upper() in {"STEP", "STP"}

    def _preview_3d_sampling_mode(self) -> str:
        return "world_envelope"

    def _current_preview_scene_trace(self) -> tuple[str, str, str]:
        self.current_preview_calls += 1
        return ("cached-system", "cached-rays", "cached-detector-miss-bundle")

    def _build_preview_system_rays_bundle(
        self,
        *,
        sampling_mode: str | None,
        update_state: bool,
        include_live_step_overlays: bool,
    ) -> tuple[str, str, str]:
        self.build_calls += 1
        self.build_kwargs.append(
            {
                "sampling_mode": sampling_mode,
                "update_state": bool(update_state),
                "include_live_step_overlays": bool(include_live_step_overlays),
            }
        )
        return ("rebuilt-system", "rebuilt-rays", "rebuilt-open3d-bundle")

    def _preview_render_row_names(self, scene_bundle: Any) -> list[str]:
        return [str(scene_bundle)]


def validate_promoted_step_refresh() -> list[PromotedStepRefreshCheck]:
    checks: list[PromotedStepRefreshCheck] = []

    promoted_editor = _FakeEditor(promoted_rows=True)
    promoted_service = Open3DTraceRefreshService(promoted_editor)
    checks.append(
        PromotedStepRefreshCheck(
            "promoted STEP rows require Open 3D retrace",
            promoted_service.has_promoted_step_optical_solid_rows()
            and not promoted_service.has_traceable_step_overlays(),
            "Saved row-backed STEP optical solids are detected separately from transient overlays.",
        )
    )

    inspector = _FakeInspector()
    result = promoted_service.build_inspector_refresh(inspector, update_state=True)
    checks.append(
        PromotedStepRefreshCheck(
            "first Open 3D refresh ignores stale cached preview bundle",
            result.scene_bundle == "rebuilt-open3d-bundle"
            and promoted_editor.current_preview_calls == 0
            and promoted_editor.build_calls == 1
            and promoted_editor.build_kwargs[-1]
            == {
                "sampling_mode": "world_envelope",
                "update_state": True,
                "include_live_step_overlays": False,
            },
            "Opening Open 3D with promoted STEP rows must rebuild instead of reusing detector-miss 2D preview state.",
        )
    )

    result = promoted_service.current_or_rebuild_scene(
        system="supplied-2d-system",
        rays="supplied-2d-rays",
        scene_bundle="supplied-2d-detector-miss-bundle",
    )
    checks.append(
        PromotedStepRefreshCheck(
            "open inspector sync ignores supplied 2D bundle for promoted STEP rows",
            result.scene_bundle == "rebuilt-open3d-bundle"
            and promoted_editor.build_calls == 2
            and promoted_editor.current_preview_calls == 0
            and promoted_editor.build_kwargs[-1]
            == {
                "sampling_mode": "world_envelope",
                "update_state": False,
                "include_live_step_overlays": False,
            },
            "Plot-refresh sync must not push a cached 2D detector-miss bundle into Open 3D for row-backed CAD solids.",
        )
    )

    plain_editor = _FakeEditor(promoted_rows=False)
    plain_service = Open3DTraceRefreshService(plain_editor)
    plain_result = plain_service.build_inspector_refresh(_FakeInspector(), update_state=True)
    checks.append(
        PromotedStepRefreshCheck(
            "ordinary compatible scene bundles can still be reused",
            plain_result.scene_bundle == "cached-detector-miss-bundle"
            and plain_editor.current_preview_calls == 1
            and plain_editor.build_calls == 0,
            "The promoted-STEP guard does not disable valid cached SceneBundle reuse for ordinary scenes.",
        )
    )

    return checks


def main() -> int:
    checks = validate_promoted_step_refresh()
    failed = [check for check in checks if not check.ok]
    for check in checks:
        status = "PASS" if check.ok else "FAIL"
        print(f"{status}: {check.check} - {check.detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
