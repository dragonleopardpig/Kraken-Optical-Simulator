"""Shared CAD/STEP cache paths for UI services."""

from __future__ import annotations

import os
from pathlib import Path


# bugs/0021: the generated CAD/STEP mesh cache (promoted-overlay body STLs and
# imported-CAD tessellations) used to live in ~/.cache/krakenos/cad, which is
# machine-local and NOT synced -- so a layout opened on another machine found
# its cached Solid_3d_stl missing and the whole Open 3D view went blank. It now
# lives under the project's attachment/ folder, which the user syncs (Filen), so
# the derived cache travels with the project and is present on every machine.
# A read-only checkout (or CI) can redirect it with KRAKENOS_CAD_CACHE_DIR.
PROJECT_ROOT = Path(__file__).resolve().parents[3]

_CAD_CACHE_ENV_OVERRIDE = os.environ.get("KRAKENOS_CAD_CACHE_DIR")
CAD_CACHE_DIR = (
    Path(_CAD_CACHE_ENV_OVERRIDE).expanduser()
    if _CAD_CACHE_ENV_OVERRIDE
    else PROJECT_ROOT / "attachment" / "cad_cache"
)
