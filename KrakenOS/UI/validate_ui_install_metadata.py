"""Validate the public UI install metadata without creating a Tk window."""

from __future__ import annotations

from pathlib import Path
import re
import tomllib


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"
SETUP_PATH = PROJECT_ROOT / "setup.py"

REQUIRED_UI_DEPS = (
    "cloudpickle",
    "ipykernel",
    "ipython",
    "packaging",
    "pybind11",
    "pygmo",
    "pyzmq",
    "sv-ttk",
)


def _normalize_requirement_name(requirement: str) -> str:
    return re.split(r"[<>=!~;\\[]", requirement.strip(), maxsplit=1)[0].lower()


def _pyproject_ui_extra_names() -> set[str]:
    data = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
    extras = data.get("project", {}).get("optional-dependencies", {})
    return {_normalize_requirement_name(requirement) for requirement in extras.get("ui", [])}


def _setup_ui_extra_names() -> set[str]:
    text = SETUP_PATH.read_text(encoding="utf-8")
    match = re.search(r"'ui'\s*:\s*\[(?P<body>.*?)\]", text, flags=re.DOTALL)
    if not match:
        return set()
    return {
        _normalize_requirement_name(value)
        for value in re.findall(r"['\"]([^'\"]+)['\"]", match.group("body"))
    }


def main() -> int:
    required = set(REQUIRED_UI_DEPS)
    pyproject_names = _pyproject_ui_extra_names()
    setup_names = _setup_ui_extra_names()
    checks = [
        ("pyproject.toml defines ui extra", bool(pyproject_names)),
        ("setup.py defines ui extra", bool(setup_names)),
        ("pyproject.toml ui extra has required deps", required <= pyproject_names),
        ("setup.py ui extra has required deps", required <= setup_names),
        ("pyproject.toml/setup.py ui extras stay aligned", pyproject_names == setup_names),
    ]
    failed = [name for name, ok in checks if not ok]
    if failed:
        print("UI install metadata validation failed:")
        for name in failed:
            print(f"- {name}")
        print(f"pyproject ui deps: {sorted(pyproject_names)}")
        print(f"setup.py ui deps: {sorted(setup_names)}")
        return 1
    print("UI install metadata validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
