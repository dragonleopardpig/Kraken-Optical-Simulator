"""Validate coverage and navigation for the Siegman Lasers solutions."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / "docs" / "source"
COLLECTION = SOURCE / "knowledge_base" / "worked_exercises" / "siegman_lasers"

# Counts come from an OCR-normalized inventory of every section problem set.
# The printed numerals for 17.5.1, 18.3.1--2, and 21.3.1 are absent from the
# PDF text layer and were verified directly from the page layout.
EXPECTED_COUNTS = {
    (1, 1): 1,
    (1, 4): 1,
    (1, 5): 1,
    (1, 7): 2,
    (1, 11): 7,
    (2, 1): 3,
    (2, 2): 1,
    (2, 3): 1,
    (2, 4): 7,
    (2, 5): 2,
    (3, 1): 1,
    (3, 2): 1,
    (3, 3): 2,
    (3, 4): 5,
    (3, 5): 1,
    (3, 7): 6,
    (4, 3): 1,
    (4, 4): 1,
    (4, 5): 3,
    (4, 6): 5,
    (5, 1): 1,
    (5, 2): 5,
    (6, 1): 5,
    (6, 2): 5,
    (6, 3): 3,
    (7, 2): 3,
    (7, 3): 1,
    (7, 4): 8,
    (7, 5): 5,
    (7, 6): 4,
    (7, 7): 9,
    (8, 1): 2,
    (8, 2): 1,
    (8, 3): 6,
    (9, 1): 1,
    (9, 2): 1,
    (9, 3): 2,
    (9, 4): 3,
    (9, 5): 3,
    (10, 1): 7,
    (11, 1): 9,
    (11, 3): 7,
    (11, 5): 4,
    (11, 6): 3,
    (11, 7): 7,
    (12, 1): 1,
    (12, 2): 4,
    (12, 3): 6,
    (12, 4): 6,
    (13, 1): 4,
    (13, 2): 3,
    (13, 3): 5,
    (13, 4): 6,
    (13, 5): 3,
    (13, 7): 5,
    (14, 3): 6,
    (15, 1): 3,
    (15, 2): 7,
    (15, 3): 8,
    (15, 4): 4,
    (15, 6): 1,
    (16, 2): 2,
    (16, 3): 4,
    (16, 4): 3,
    (16, 6): 3,
    (16, 7): 2,
    (17, 1): 6,
    (17, 2): 3,
    (17, 3): 1,
    (17, 5): 3,
    (17, 6): 1,
    (18, 1): 1,
    (18, 3): 4,
    (18, 4): 8,
    (19, 1): 3,
    (19, 2): 3,
    (19, 3): 2,
    (19, 5): 2,
    (20, 2): 4,
    (20, 4): 1,
    (20, 5): 4,
    (21, 1): 1,
    (21, 3): 1,
    (21, 4): 6,
    (21, 5): 1,
    (21, 6): 7,
    (21, 7): 2,
    (22, 1): 1,
    (24, 1): 2,
    (24, 2): 4,
    (24, 4): 3,
    (24, 5): 1,
    (25, 1): 7,
    (25, 2): 2,
    (25, 3): 2,
    (25, 4): 3,
    (26, 2): 7,
    (26, 4): 4,
    (26, 5): 1,
    (27, 1): 7,
    (27, 3): 6,
    (27, 4): 2,
    (27, 6): 1,
    (27, 7): 6,
    (28, 1): 3,
    (29, 3): 1,
    (29, 4): 1,
    (29, 5): 2,
    (29, 6): 4,
    (30, 2): 3,
    (30, 6): 4,
    (31, 1): 2,
    (31, 2): 1,
    (31, 5): 2,
    (31, 6): 1,
    (31, 7): 4,
}
PROBLEM_RE = re.compile(
    r"^Problem (\d+)\.(\d+)\.(\d+)(?=\s|—)[^\n]*\n\^+\n",
    re.MULTILINE,
)


def fail(message: str) -> None:
    raise SystemExit(f"Siegman solutions validation failed: {message}")


def main() -> None:
    chapter_files = sorted(COLLECTION.glob("ch[0-9][0-9]_*.rst"))
    if len(chapter_files) != 31:
        fail(f"expected 31 chapter files, found {len(chapter_files)}")

    found: dict[tuple[int, int], list[int]] = defaultdict(list)
    identities: set[tuple[int, int, int]] = set()
    for path in chapter_files:
        chapter = int(path.name[2:4])
        for id_chapter, section, item in PROBLEM_RE.findall(
            path.read_text(encoding="utf-8")
        ):
            identity = (int(id_chapter), int(section), int(item))
            if identity[0] != chapter:
                fail(f"{path.name} contains out-of-chapter ID {'.'.join(map(str, identity))}")
            if identity in identities:
                fail(f"duplicate problem ID {'.'.join(map(str, identity))}")
            identities.add(identity)
            found[identity[:2]].append(identity[2])

    if set(found) != set(EXPECTED_COUNTS):
        missing = sorted(set(EXPECTED_COUNTS) - set(found))
        extra = sorted(set(found) - set(EXPECTED_COUNTS))
        fail(f"problem-section mismatch; missing={missing}, extra={extra}")

    for key, expected_count in EXPECTED_COUNTS.items():
        expected_items = list(range(1, expected_count + 1))
        if found[key] != expected_items:
            fail(f"section {key[0]}.{key[1]} has {found[key]}, expected {expected_items}")

    if len(identities) != 394:
        fail(f"found {len(identities)} problems, expected 394")

    chapter_23 = next(path for path in chapter_files if path.name.startswith("ch23_"))
    if PROBLEM_RE.search(chapter_23.read_text(encoding="utf-8")):
        fail("chapter 23 unexpectedly contains a numbered problem")

    collection_index = (COLLECTION / "index.rst").read_text(encoding="utf-8")
    for path in chapter_files:
        if path.stem not in collection_index:
            fail(f"collection index omits {path.stem}")

    landing_page = (
        SOURCE / "knowledge_base" / "worked_exercises" / "index.rst"
    ).read_text(encoding="utf-8")
    if "siegman_lasers/index" not in landing_page:
        fail("worked-exercise landing page omits the Siegman collection")

    root_index = (SOURCE / "index.rst").read_text(encoding="utf-8")
    if ":caption: Worked Exercise Solutions" not in root_index:
        fail("Worked Exercise Solutions is not a root-level navigation section")
    if "knowledge_base/worked_exercises/index" not in root_index:
        fail("root navigation does not link the worked-exercise landing page")

    print(
        f"Validated 31 chapters and {len(EXPECTED_COUNTS)} problem sections: "
        f"{len(identities)} worked solutions."
    )


if __name__ == "__main__":
    main()
