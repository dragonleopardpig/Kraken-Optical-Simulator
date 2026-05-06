from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass

from KrakenOS.UI.layout_editor import (
    ZEMAX_TESTING_DIR,
    _available_testing_zemax_prescriptions,
    _load_zemax_zmx_data,
)


@dataclass
class TestingZemaxExampleCheck:
    label: str
    ok: bool
    detail: str


def validate_testing_zemax_examples() -> list[TestingZemaxExampleCheck]:
    files = _available_testing_zemax_prescriptions()
    checks: list[TestingZemaxExampleCheck] = []
    checks.append(
        TestingZemaxExampleCheck(
            "menu scan",
            bool(files),
            f"{len(files)} .zmx prescription(s) found under {ZEMAX_TESTING_DIR}",
        )
    )
    for label, path in files.items():
        try:
            info = _load_zemax_zmx_data(path)
            surface_count = len(info.get("surfaces", []))
            title = str(info.get("title", "") or path.stem)
            checks.append(
                TestingZemaxExampleCheck(
                    label,
                    surface_count >= 2,
                    f"title={title}, surfaces={surface_count}",
                )
            )
        except Exception as exc:
            checks.append(TestingZemaxExampleCheck(label, False, str(exc)))
    return checks


def _print_table(checks: list[TestingZemaxExampleCheck]) -> None:
    print("KrakenOS attachment Zemax example validation")
    print("label | status | detail")
    print("--- | --- | ---")
    for check in checks:
        print(f"{check.label} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate attachment/zemax .zmx prescriptions exposed in the Examples menu."
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    checks = validate_testing_zemax_examples()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
