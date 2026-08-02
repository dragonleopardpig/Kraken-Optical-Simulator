"""Validate coverage and navigation for the Fundamentals of Photonics solutions."""

from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / "docs" / "source"
COLLECTION = (
    SOURCE / "knowledge_base" / "worked_exercises" / "fundamentals_of_photonics"
)

# Counts come from an OCR-normalized inventory of every boxed exercise and
# end-of-chapter problem in the second edition.  Per-chapter checks make an
# omitted item impossible to hide behind an extra item in another chapter.
EXPECTED_COUNTS = {
    1: (16, 13),
    2: (12, 14),
    3: (11, 10),
    4: (7, 19),
    5: (1, 8),
    6: (7, 20),
    7: (1, 11),
    8: (4, 11),
    9: (2, 11),
    10: (7, 14),
    11: (4, 15),
    12: (5, 21),
    13: (3, 9),
    14: (7, 12),
    15: (5, 15),
    16: (7, 8),
    17: (4, 14),
    18: (3, 25),
    19: (4, 7),
    20: (2, 9),
    21: (14, 17),
    22: (2, 12),
    23: (3, 9),
    24: (0, 10),
}
RUBRIC_RE = re.compile(
    r"^\.\. rubric:: (Exercise|Problem) (\d+)\.(\d+)-(\d+)\b", re.MULTILINE
)


def fail(message: str) -> None:
    raise SystemExit(f"Fundamentals solutions validation failed: {message}")


def main() -> None:
    chapter_files = sorted(COLLECTION.glob("ch[0-9][0-9]_*.rst"))
    if len(chapter_files) != 24:
        fail(f"expected 24 chapter files, found {len(chapter_files)}")

    found_ids: set[tuple[str, int, int, int]] = set()
    total_exercises = 0
    total_problems = 0

    for path in chapter_files:
        chapter = int(path.name[2:4])
        matches = RUBRIC_RE.findall(path.read_text(encoding="utf-8"))
        exercises = sum(kind == "Exercise" for kind, *_ in matches)
        problems = sum(kind == "Problem" for kind, *_ in matches)
        if (exercises, problems) != EXPECTED_COUNTS[chapter]:
            fail(
                f"chapter {chapter} has {(exercises, problems)}, "
                f"expected {EXPECTED_COUNTS[chapter]} (exercises, problems)"
            )

        for kind, id_chapter, section, item in matches:
            if int(id_chapter) != chapter:
                fail(f"{path.name} contains out-of-chapter ID {id_chapter}.{section}-{item}")
            identity = (kind, int(id_chapter), int(section), int(item))
            if identity in found_ids:
                fail(f"duplicate {kind.lower()} ID {id_chapter}.{section}-{item}")
            found_ids.add(identity)

        total_exercises += exercises
        total_problems += problems

    if (total_exercises, total_problems) != (131, 314):
        fail(
            f"found {total_exercises} exercises and {total_problems} problems; "
            "expected 131 and 314"
        )

    collection_index = (COLLECTION / "index.rst").read_text(encoding="utf-8")
    for path in chapter_files:
        if path.stem not in collection_index:
            fail(f"collection index omits {path.stem}")

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

    print(
        "Validated 24 chapters: "
        f"{total_exercises} exercises + {total_problems} problems = "
        f"{len(found_ids)} worked solutions."
    )


if __name__ == "__main__":
    main()
