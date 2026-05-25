"""Known prism CAD fixture paths used by UI diagnostics and tutorials."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PRISMS_DIR = PROJECT_ROOT / "attachment" / "prisms"


def first_existing_fixture(*paths: Path) -> Path:
    """Return the first existing fixture path, falling back to the preferred path."""
    for path in paths:
        if path.exists():
            return path
    if not paths:
        raise ValueError("at least one fixture path is required")
    return paths[0]


PRISM_42779_DIR = first_existing_fixture(PRISMS_DIR / "Penta", PRISMS_DIR / "42779")
PRISM_42779_STEP = first_existing_fixture(
    PRISM_42779_DIR / "step_42779.step",
    PRISMS_DIR / "42779" / "step_42779.step",
)
PRISM_42779_IGES = first_existing_fixture(
    PRISM_42779_DIR / "iges_42779.igs",
    PRISMS_DIR / "42779" / "iges_42779.igs",
)

PRISM_32336_DIR = first_existing_fixture(PRISMS_DIR / "Right_Angle", PRISMS_DIR / "32336")
PRISM_32336_STEP = first_existing_fixture(
    PRISM_32336_DIR / "step_32336.step",
    PRISMS_DIR / "32336" / "step_32336.step",
)
