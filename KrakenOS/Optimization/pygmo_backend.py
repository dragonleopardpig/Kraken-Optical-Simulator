from __future__ import annotations

import ctypes
import importlib.util
import os
from pathlib import Path


def preload_configured_pagmo_library() -> None:
    """Preload an explicitly configured local pagmo2 library before pygmo import."""
    configured = os.getenv("KRAKEN_PAGMO2_LIB", "").strip()
    if not configured:
        return
    if configured.lower() == "auto":
        configured = "~/Projects/pagmo2/_install/lib64/libpagmo.so"
    pagmo_lib = Path(os.path.expanduser(configured))
    if not pagmo_lib.exists():
        return
    try:
        mode = getattr(ctypes, "RTLD_GLOBAL", None)
        if mode is None:
            ctypes.CDLL(str(pagmo_lib))
        else:
            ctypes.CDLL(str(pagmo_lib), mode=mode)
    except OSError:
        pass


def import_pygmo():
    preload_configured_pagmo_library()
    import pygmo as pg  # type: ignore

    return pg


def probe_pygmo_backend() -> tuple[bool, str]:
    if importlib.util.find_spec("pygmo") is None:
        return (
            False,
            "pygmo is not installed. Run `devenv shell kraken-install` "
            "or install the `pygmo` wheel in the active environment.",
        )
    try:
        pg = import_pygmo()
    except Exception as exc:
        return False, f"pygmo import failed: {exc}"
    version = str(getattr(pg, "__version__", "unknown") or "unknown")
    return True, f"pygmo {version}"
