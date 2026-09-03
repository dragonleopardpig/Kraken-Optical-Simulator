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
        trace_rays: bool = True,
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

    # bugs/0700 ("Ctrl-Z to undo the rotation is super slow"): since bugs/0201/0243
    # the 2D preview traces the SAME folded-aware real system Open 3D would rebuild,
    # so products passed EXPLICITLY (the trace refresh_plot finished a moment ago)
    # must be TRUSTED even on promoted-STEP scenes -- discarding them re-ran a full
    # non-sequential trace and doubled every history restore (245 s on om05a).
    result = promoted_service.current_or_rebuild_scene(
        system="supplied-fresh-system",
        rays="supplied-fresh-rays",
        scene_bundle="supplied-fresh-bundle",
    )
    checks.append(
        PromotedStepRefreshCheck(
            "open inspector sync trusts an explicitly supplied fresh bundle (0700)",
            result.scene_bundle == "supplied-fresh-bundle"
            and promoted_editor.build_calls == 1
            and promoted_editor.current_preview_calls == 0,
            "Plot-refresh hands Open 3D the trace it just ran; re-tracing it doubled undo/redo wall time.",
        )
    )

    # The CACHED-trace path keeps the f35ffdec defence: with promoted STEP rows and
    # no explicit products, the sync must rebuild through the Open 3D trace path,
    # never adopt _current_preview_scene_trace().
    result = promoted_service.current_or_rebuild_scene()
    checks.append(
        PromotedStepRefreshCheck(
            "no-args sync still rebuilds for promoted STEP rows (cached trace refused)",
            result.scene_bundle == "rebuilt-open3d-bundle"
            and promoted_editor.build_calls == 2
            and promoted_editor.current_preview_calls == 0
            and promoted_editor.build_kwargs[-1]
            == {
                "sampling_mode": "world_envelope",
                "update_state": False,
                "include_live_step_overlays": False,
            },
            "Opening Open 3D without a fresh handoff must not reuse stale cached preview state.",
        )
    )

    # A supplied bundle whose sampling mode cannot feed the 3D scene is still
    # rejected -- the trust extends only to a mode-compatible fresh trace.
    promoted_editor._active_preview_sampling_mode = "display_slice"
    result = promoted_service.current_or_rebuild_scene(
        system="supplied-fan-system",
        rays="supplied-fan-rays",
        scene_bundle="supplied-fan-bundle",
    )
    promoted_editor._active_preview_sampling_mode = "world_envelope"
    checks.append(
        PromotedStepRefreshCheck(
            "mode-incompatible supplied bundle is still rebuilt",
            result.scene_bundle == "rebuilt-open3d-bundle"
            and promoted_editor.build_calls == 3,
            "The sampling-mode gate outranks the explicit-products trust.",
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
