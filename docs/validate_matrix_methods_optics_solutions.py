"""Validate the Gerrard/Burch matrix-methods worked-solution collection."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / "docs" / "source"
COLLECTION = (
    SOURCE
    / "knowledge_base"
    / "worked_exercises"
    / "introduction_matrix_methods_optics"
)
ASSETS = (
    SOURCE
    / "_static"
    / "knowledge_base"
    / "worked_exercises"
    / "introduction_matrix_methods_optics"
)

# The printed illustrative-problem sections contain 12, 6, and 8 numbered
# problems in Chapters II, III, and IV.  Chapters I and V have no numbered
# problem set.  Appendix A contributes one extended illustrative problem.
EXPECTED_COUNTS = {1: 0, 2: 12, 3: 6, 4: 8, 5: 0}
CHAPTER_RE = re.compile(
    r"^\.\. rubric:: Problem (\d+)\.(\d+)(?=\s|—)", re.MULTILINE
)
APPENDIX_RE = re.compile(
    r"^\.\. rubric:: Problem A\.(\d+)(?=\s|—)", re.MULTILINE
)
EXPECTED_ASSETS = {
    "ray_matrix_elements.svg",
    "resonator_stability.svg",
    "polarization_matrix_pipeline.svg",
    "aperture_stop_geometry.svg",
}


def fail(message: str) -> None:
    raise SystemExit(f"Matrix-methods solutions validation failed: {message}")


def main() -> None:
    chapter_files = sorted(COLLECTION.glob("ch[0-9][0-9]_*.rst"))
    if len(chapter_files) != 5:
        fail(f"expected 5 chapter files, found {len(chapter_files)}")

    found_ids: set[tuple[int, int]] = set()
    total = 0
    for path in chapter_files:
        chapter = int(path.name[2:4])
        matches = CHAPTER_RE.findall(path.read_text(encoding="utf-8"))
        expected = EXPECTED_COUNTS[chapter]
        if len(matches) != expected:
            fail(f"chapter {chapter} has {len(matches)} problems, expected {expected}")

        numbers: list[int] = []
        for id_chapter, number in matches:
            identity = (int(id_chapter), int(number))
            if identity[0] != chapter:
                fail(f"{path.name} contains out-of-chapter ID {id_chapter}.{number}")
            if identity in found_ids:
                fail(f"duplicate problem ID {id_chapter}.{number}")
            found_ids.add(identity)
            numbers.append(identity[1])

        if numbers != list(range(1, expected + 1)):
            fail(f"{path.name} has missing or out-of-order problem IDs")
        total += len(matches)

    appendix = COLLECTION / "appendix_a_apertures.rst"
    appendix_ids = [int(number) for number in APPENDIX_RE.findall(
        appendix.read_text(encoding="utf-8")
    )]
    if appendix_ids != [1]:
        fail(f"appendix problem IDs are {appendix_ids}, expected [1]")

    if total != 26:
        fail(f"found {total} chapter problems, expected 26")

    reference = (COLLECTION / "reference_tables.rst").read_text(encoding="utf-8")
    for number in range(1, 5):
        if f"Recreated Table {number}" not in reference:
            fail(f"reference page omits recreated Table {number}")

    actual_assets = {path.name for path in ASSETS.glob("*.svg")}
    if actual_assets != EXPECTED_ASSETS:
        fail(
            f"SVG set mismatch; missing={sorted(EXPECTED_ASSETS-actual_assets)}, "
            f"extra={sorted(actual_assets-EXPECTED_ASSETS)}"
        )
    for path in sorted(ASSETS.glob("*.svg")):
        root = ET.parse(path).getroot()
        namespace = "{http://www.w3.org/2000/svg}"
        if root.find(f"{namespace}title") is None or root.find(f"{namespace}desc") is None:
            fail(f"{path.name} lacks accessible title/description metadata")
        if path.name not in reference and path.name != "aperture_stop_geometry.svg":
            fail(f"reference page omits SVG {path.name}")
    if "aperture_stop_geometry.svg" not in appendix.read_text(encoding="utf-8"):
        fail("appendix page omits the aperture SVG")

    collection_index = (COLLECTION / "index.rst").read_text(encoding="utf-8")
    required_pages = [*chapter_files, appendix, COLLECTION / "reference_tables.rst"]
    for path in required_pages:
        if path.stem not in collection_index:
            fail(f"collection index omits {path.stem}")

    landing = (
        SOURCE / "knowledge_base" / "worked_exercises" / "index.rst"
    ).read_text(encoding="utf-8")
    if "introduction_matrix_methods_optics/index" not in landing:
        fail("worked-exercise landing page omits the matrix-methods collection")

    root_index = (SOURCE / "index.rst").read_text(encoding="utf-8")
    if ":caption: Worked Exercise Solutions" not in root_index:
        fail("Worked Exercise Solutions is not a root-level navigation section")

    print(
        "Validated 5 chapters, 26 numbered chapter problems, 1 appendix "
        "problem, 4 recreated tables, and 4 accessible SVGs."
    )


if __name__ == "__main__":
    main()
