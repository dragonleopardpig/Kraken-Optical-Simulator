"""Validate that the optional UI runtime dependencies are importable."""

from __future__ import annotations

import importlib.util


REQUIRED_IMPORTS = {
    "cloudpickle": "cloudpickle",
    "ipykernel": "ipykernel",
    "IPython": "ipython",
    "packaging": "packaging",
    "pybind11": "pybind11",
    "pygmo": "pygmo",
    "zmq": "pyzmq",
    "sv_ttk": "sv-ttk",
}


def main() -> int:
    missing = [
        package_name
        for module_name, package_name in REQUIRED_IMPORTS.items()
        if importlib.util.find_spec(module_name) is None
    ]
    if missing:
        print("UI runtime dependency validation failed:")
        for package_name in missing:
            print(f"- missing {package_name}")
        print('Run: python -m pip install -e ".[ui]"')
        return 1
    print("UI runtime dependency validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
