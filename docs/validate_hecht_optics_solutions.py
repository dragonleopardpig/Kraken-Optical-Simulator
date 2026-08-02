"""Validate coverage and navigation for the Hecht Optics 5e solutions."""

from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / "docs" / "source"
COLLECTION = SOURCE / "knowledge_base" / "worked_exercises" / "hecht_optics_5e"

# Counts come from an OCR-normalized inventory of every problem in the fifth
# Global Edition.  The second number is the count marked with an asterisk.
EXPECTED_COUNTS = {
    1: (0, 0),
    2: (60, 42),
    3: (67, 43),
    4: (101, 67),
    5: (122, 79),
    6: (34, 22),
    7: (63, 45),
    8: (95, 66),
    9: (62, 40),
    10: (93, 64),
    11: (50, 35),
    12: (30, 21),
    13: (54, 34),
}
RUBRIC_RE = re.compile(
    r"^\.\. rubric:: Problem (\d+)\.(\d+)(\*)?(?=\s|—)", re.MULTILINE
)


def fail(message: str) -> None:
    raise SystemExit(f"Hecht solutions validation failed: {message}")


def main() -> None:
    chapter_files = sorted(COLLECTION.glob("ch[0-9][0-9]_*.rst"))
    if len(chapter_files) != 13:
        fail(f"expected 13 chapter files, found {len(chapter_files)}")

    found_ids: set[tuple[int, int]] = set()
    total_problems = 0
    total_starred = 0

    for path in chapter_files:
        chapter = int(path.name[2:4])
        text = path.read_text(encoding="utf-8")
        matches = RUBRIC_RE.findall(text)
        count = len(matches)
        starred = sum(bool(mark) for _, _, mark in matches)
        if (count, starred) != EXPECTED_COUNTS[chapter]:
            fail(
                f"chapter {chapter} has {(count, starred)}, expected "
                f"{EXPECTED_COUNTS[chapter]} (problems, starred)"
            )

        numbers: list[int] = []
        for id_chapter, number, _mark in matches:
            if int(id_chapter) != chapter:
                fail(f"{path.name} contains out-of-chapter ID {id_chapter}.{number}")
            identity = (int(id_chapter), int(number))
            if identity in found_ids:
                fail(f"duplicate problem ID {id_chapter}.{number}")
            found_ids.add(identity)
            numbers.append(int(number))

        if numbers != list(range(1, count + 1)):
            fail(f"{path.name} has missing or out-of-order problem IDs")

        total_problems += count
        total_starred += starred

    if (total_problems, total_starred) != (831, 558):
        fail(
            f"found {total_problems} problems and {total_starred} starred; "
            "expected 831 and 558"
        )

    collection_index = (COLLECTION / "index.rst").read_text(encoding="utf-8")
    for path in chapter_files:
        if path.stem not in collection_index:
            fail(f"collection index omits {path.stem}")

    landing_page = (
        SOURCE / "knowledge_base" / "worked_exercises" / "index.rst"
    ).read_text(encoding="utf-8")
    if "hecht_optics_5e/index" not in landing_page:
        fail("worked-exercise landing page omits the Hecht collection")

    root_index = (SOURCE / "index.rst").read_text(encoding="utf-8")
    if ":caption: Worked Exercise Solutions" not in root_index:
        fail("Worked Exercise Solutions is not a root-level navigation section")
    if "knowledge_base/worked_exercises/index" not in root_index:
        fail("root navigation does not link the worked-exercise landing page")

    print(
        "Validated 13 chapters: "
        f"{total_problems} worked solutions ({total_starred} starred, "
        f"{total_problems - total_starred} keyed)."
    )


if __name__ == "__main__":
    main()
