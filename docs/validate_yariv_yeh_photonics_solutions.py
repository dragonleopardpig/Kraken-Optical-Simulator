"""Validate coverage and navigation for the Yariv/Yeh Photonics solutions."""

from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / "docs" / "source"
COLLECTION = (
    SOURCE
    / "knowledge_base"
    / "worked_exercises"
    / "yariv_yeh_photonics_6e"
)

# Counts were transcribed from every chapter's printed problem pages.  The
# page on which the references begin was included because several chapters
# continue their problem set above the references heading.
EXPECTED_COUNTS = {
    1: 37,
    2: 22,
    3: 15,
    4: 19,
    5: 8,
    6: 19,
    7: 12,
    8: 15,
    9: 24,
    10: 12,
    11: 12,
    12: 13,
    13: 13,
    14: 11,
    15: 11,
    16: 8,
    17: 7,
    18: 5,
}
RUBRIC_RE = re.compile(
    r"^\.\. rubric:: Problem (\d+)\.(\d+)(?=\s|—)", re.MULTILINE
)


def fail(message: str) -> None:
    raise SystemExit(f"Yariv/Yeh solutions validation failed: {message}")


def main() -> None:
    chapter_files = sorted(COLLECTION.glob("ch[0-9][0-9]_*.rst"))
    if len(chapter_files) != 18:
        fail(f"expected 18 chapter files, found {len(chapter_files)}")

    found_ids: set[tuple[int, int]] = set()
    total = 0
    for path in chapter_files:
        chapter = int(path.name[2:4])
        matches = RUBRIC_RE.findall(path.read_text(encoding="utf-8"))
        if len(matches) != EXPECTED_COUNTS[chapter]:
            fail(
                f"chapter {chapter} has {len(matches)} solutions, expected "
                f"{EXPECTED_COUNTS[chapter]}"
            )

        numbers: list[int] = []
        for id_chapter, number in matches:
            if int(id_chapter) != chapter:
                fail(f"{path.name} contains out-of-chapter ID {id_chapter}.{number}")
            identity = (int(id_chapter), int(number))
            if identity in found_ids:
                fail(f"duplicate problem ID {id_chapter}.{number}")
            found_ids.add(identity)
            numbers.append(int(number))

        if numbers != list(range(1, EXPECTED_COUNTS[chapter] + 1)):
            fail(f"{path.name} has missing or out-of-order problem IDs")
        total += len(matches)

    if total != 263:
        fail(f"found {total} solutions, expected 263")

    collection_index = (COLLECTION / "index.rst").read_text(encoding="utf-8")
    for path in chapter_files:
        if path.stem not in collection_index:
            fail(f"collection index omits {path.stem}")

    landing_page = (
        SOURCE / "knowledge_base" / "worked_exercises" / "index.rst"
    ).read_text(encoding="utf-8")
    if "yariv_yeh_photonics_6e/index" not in landing_page:
        fail("worked-exercise landing page omits the Yariv/Yeh collection")

    root_index = (SOURCE / "index.rst").read_text(encoding="utf-8")
    if ":caption: Worked Exercise Solutions" not in root_index:
        fail("Worked Exercise Solutions is not a root-level navigation section")
    if "knowledge_base/worked_exercises/index" not in root_index:
        fail("root navigation does not link the worked-exercise landing page")

    knowledge_index = (SOURCE / "knowledge_base" / "index.rst").read_text(
        encoding="utf-8"
    )
    if "worked_exercises/index" in knowledge_index:
        fail("Worked Exercise Solutions is still nested under Knowledge Base")

    print(f"Validated 18 chapters and {total} Yariv/Yeh worked solutions.")


if __name__ == "__main__":
    main()
