"""The user's own preferences, kept across runs (bugs/0971).

One small JSON file per user and machine -- not a layout's settings, which travel with the layout.
The first preference is which interface starts (`launcher.py`): the user asked for both the Tk and
the Qt interface to stay available, and to choose between them.

Where: ``$KRAKEN_CONFIG_DIR`` when set (guards point it at a temp folder), else the platform's
per-user configuration folder -- ``$XDG_CONFIG_HOME/krakenos`` or ``~/.config/krakenos`` on Linux,
``%APPDATA%/KrakenOS`` on Windows, ``~/Library/Application Support/KrakenOS`` on macOS.

Toolkit-free, and never fatal: a file that is missing, unreadable or not JSON reads as no
preferences; a folder that cannot be written is reported, not raised.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

FILE_NAME = "preferences.json"


def config_dir() -> Path:
    override = os.environ.get("KRAKEN_CONFIG_DIR")
    if override:
        return Path(override).expanduser()
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA")
        return (Path(base) if base else Path.home() / "AppData" / "Roaming") / "KrakenOS"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "KrakenOS"
    base = os.environ.get("XDG_CONFIG_HOME")
    return (Path(base).expanduser() if base else Path.home() / ".config") / "krakenos"


def path() -> Path:
    return config_dir() / FILE_NAME


def load() -> dict:
    """Every saved preference; {} when there is none to read."""
    try:
        data = json.loads(path().read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def get(key: str, default: Any = None) -> Any:
    return load().get(key, default)


def set_value(key: str, value: Any) -> str:
    """Save one preference, keeping the others. Returns "" when saved, else why it was not."""
    data = load()
    if value is None:
        data.pop(key, None)
    else:
        data[key] = value
    target = path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, target)
    except Exception as exc:
        return f"Could not save preferences to {target}: {exc}"
    return ""
