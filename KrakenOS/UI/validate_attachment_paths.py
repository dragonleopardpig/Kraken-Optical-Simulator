from __future__ import annotations

import argparse
import inspect
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from KrakenOS.UI.camera_database import camera_record
from KrakenOS.UI.layout_editor import (
    ATTACHMENT_CAMERA_DIR,
    ATTACHMENT_DIR,
    ATTACHMENT_LED_DIR,
    ATTACHMENT_LENS_DIR,
    AUTO_PLOT_PATH,
    DEFAULT_CAMERA_STEP_PATH,
    DEFAULT_LED_STEP_PATH,
    DEFAULT_LENS_STEP_PATH,
    SCREENSHOT_DIR,
    STOCK_LENS_CATALOG_SPECS,
    ZEMAX_ATTACHMENT_DIR,
)
from KrakenOS.UI.services.layout_import_export import LayoutImportExportMixin
from KrakenOS.UI.services.layout_settings import LayoutSettingsService
from KrakenOS.UI.services.optical_solid_workflow import LayoutOpticalSolidWorkflowMixin
from KrakenOS.UI.services.step_overlay_import import StepOverlayImportService
from KrakenOS.common_optical_layouts import machine_vision_150mm_measured


@dataclass
class AttachmentPathCheck:
    check: str
    ok: bool
    detail: str


def _under(path: Path, root: Path) -> bool:
    try:
        path.expanduser().resolve().relative_to(root.expanduser().resolve())
        return True
    except Exception:
        return False


def validate_attachment_paths() -> list[AttachmentPathCheck]:
    checks: list[AttachmentPathCheck] = []
    checks.append(
        AttachmentPathCheck(
            "scratch/save directory",
            SCREENSHOT_DIR == ATTACHMENT_DIR,
            str(SCREENSHOT_DIR),
        )
    )
    checks.append(
        AttachmentPathCheck(
            "default 2D plot output",
            AUTO_PLOT_PATH == ATTACHMENT_DIR / "2D.png",
            str(AUTO_PLOT_PATH),
        )
    )
    checks.append(
        AttachmentPathCheck(
            "Zemax example directory",
            ZEMAX_ATTACHMENT_DIR == ATTACHMENT_DIR / "zemax",
            str(ZEMAX_ATTACHMENT_DIR),
        )
    )
    checks.append(
        AttachmentPathCheck(
            "camera STEP default",
            _under(DEFAULT_CAMERA_STEP_PATH, ATTACHMENT_DIR) and ATTACHMENT_CAMERA_DIR.name.lower().startswith("camera"),
            str(DEFAULT_CAMERA_STEP_PATH),
        )
    )
    checks.append(
        AttachmentPathCheck(
            "lens STEP default",
            _under(DEFAULT_LENS_STEP_PATH, ATTACHMENT_DIR) and ATTACHMENT_LENS_DIR.name.lower() == "lens",
            str(DEFAULT_LENS_STEP_PATH),
        )
    )
    checks.append(
        AttachmentPathCheck(
            "LED STEP default",
            _under(DEFAULT_LED_STEP_PATH, ATTACHMENT_DIR) and ATTACHMENT_LED_DIR.name.lower() == "led",
            str(DEFAULT_LED_STEP_PATH),
        )
    )
    step_import_source = inspect.getsource(StepOverlayImportService)
    ask_step_source = inspect.getsource(LayoutOpticalSolidWorkflowMixin._ask_step_file)
    zemax_import_source = inspect.getsource(LayoutImportExportMixin.import_zemax_file)
    layout_settings_source = inspect.getsource(LayoutSettingsService._collect_layout_settings)
    checks.append(
        AttachmentPathCheck(
            "Open STEP dialogs start at attachment root",
            'self._ask_step_file(title, le.ATTACHMENT_DIR' in step_import_source
            and 'self._ask_step_file("Import optical STEP", le.ATTACHMENT_DIR' in step_import_source
            and 'self._ask_step_file("Import camera STEP", le.ATTACHMENT_DIR' in step_import_source
            and "initial_dir = le.ATTACHMENT_DIR" in step_import_source
            and 'globals().get("ATTACHMENT_DIR", Path.home())' in ask_step_source,
            "Lens, optical, camera, LED STEP import dialogs use attachment/ as the first browser directory.",
        )
    )
    checks.append(
        AttachmentPathCheck(
            "Zemax open dialog starts at attachment root",
            "initial_dirs = [\n            ATTACHMENT_DIR," in zemax_import_source,
            "Import Zemax file opens at attachment/ before narrower fallback directories.",
        )
    )
    machine_vision_step_paths = [
        str(machine_vision_150mm_measured.SETTINGS.get(key, ""))
        for key in ("camera_step_path", "lens_step_path", "optical_step_path", "led_step_path")
        if str(machine_vision_150mm_measured.SETTINGS.get(key, "")).strip()
    ]
    checks.append(
        AttachmentPathCheck(
            "saved layout STEP paths stay portable",
            "_portable_step_path_text" in layout_settings_source
            and "relative_to(PROJECT_ROOT.resolve())" in layout_settings_source
            and machine_vision_step_paths
            and all(not Path(path).expanduser().is_absolute() for path in machine_vision_step_paths)
            and all(path.startswith("attachment/") for path in machine_vision_step_paths),
            ", ".join(machine_vision_step_paths),
        )
    )

    stock_project_catalogs = [
        (label, path)
        for label, path in STOCK_LENS_CATALOG_SPECS
        if "attachment" in label.lower()
    ]
    checks.append(
        AttachmentPathCheck(
            "stock catalog defaults",
            len(stock_project_catalogs) >= 2 and all(_under(Path(path), ATTACHMENT_DIR) for _, path in stock_project_catalogs),
            ", ".join(f"{label}: {path}" for label, path in stock_project_catalogs),
        )
    )

    camera = camera_record("Allied Vision hr25MCX") or {}
    camera_step = Path(camera.get("step_path", ""))
    camera_datasheet = Path(camera.get("datasheet", ""))
    checks.append(
        AttachmentPathCheck(
            "camera database defaults",
            _under(camera_step, ATTACHMENT_DIR) and _under(camera_datasheet, ATTACHMENT_DIR),
            f"step={camera_step}; datasheet={camera_datasheet}",
        )
    )
    return checks


def _print_table(checks: list[AttachmentPathCheck]) -> None:
    print("KrakenOS attachment path validation")
    print("check | status | detail")
    print("--- | --- | ---")
    for check in checks:
        print(f"{check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate attachment/ default paths used by the layout editor.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    checks = validate_attachment_paths()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
