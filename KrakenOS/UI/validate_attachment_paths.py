from __future__ import annotations

import argparse
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
