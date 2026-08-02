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
ENTRY_RE = re.compile(
    r"^\.\. rubric:: (Exercise|Problem) (\d+)\.(\d+)-(\d+)\b[^\n]*\n",
    re.MULTILINE,
)
EQUATION_LABEL_RE = re.compile(r"^   :label: (fop-[a-z0-9-]+)$", re.MULTILINE)


def fail(message: str) -> None:
    raise SystemExit(f"Fundamentals solutions validation failed: {message}")


def main() -> None:
    chapter_files = sorted(COLLECTION.glob("ch[0-9][0-9]_*.rst"))
    if len(chapter_files) != 24:
        fail(f"expected 24 chapter files, found {len(chapter_files)}")

    found_ids: set[tuple[str, int, int, int]] = set()
    found_equation_labels: set[str] = set()
    total_exercises = 0
    total_problems = 0
    structured_entries = 0
    numbered_entries = 0

    for path in chapter_files:
        chapter = int(path.name[2:4])
        chapter_text = path.read_text(encoding="utf-8")
        matches = RUBRIC_RE.findall(chapter_text)
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

        entries = list(ENTRY_RE.finditer(chapter_text))
        for entry_index, entry in enumerate(entries):
            entry_end = (
                entries[entry_index + 1].start()
                if entry_index + 1 < len(entries)
                else len(chapter_text)
            )
            body = chapter_text[entry.end() : entry_end]
            identity = f"{entry.group(1)} {entry.group(2)}.{entry.group(3)}-{entry.group(4)}"

            if "**Definitions" not in body:
                fail(f"{identity} has no definitions/setup block")
            if "**Mathematical formulas used.**" not in body:
                fail(f"{identity} has no mathematical-formula reference block")
            if not ("**Worked derivation.**" in body or "**Step 1" in body):
                fail(f"{identity} has no worked derivation")
            if not ("**Check.**" in body or "**Checks.**" in body):
                fail(f"{identity} has no verification block")
            structured_entries += 1

            # Every displayed equation must carry a Sphinx label immediately
            # after its directive.  Inline expressions are not equations and
            # are deliberately left unnumbered.
            body_lines = body.splitlines()
            for line_index, line in enumerate(body_lines):
                if line != ".. math::":
                    continue
                if line_index + 1 >= len(body_lines):
                    fail(f"{identity} ends with an empty math directive")
                label_line = body_lines[line_index + 1]
                if not label_line.startswith("   :label: fop-"):
                    fail(f"{identity} contains an unnumbered displayed equation")

            labels = EQUATION_LABEL_RE.findall(body)
            if labels:
                numbered_entries += 1
            elif "\\boxed" in body or re.search(r":math:`[^`]*=[^`]*`", body, re.DOTALL):
                fail(f"{identity} contains an equation but no numbered result")
            for label in labels:
                if label in found_equation_labels:
                    fail(f"duplicate equation label {label}")
                found_equation_labels.add(label)

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
    if "mathematical_formula_reference" not in collection_index:
        fail("collection index omits the mathematical formula reference")

    formula_reference = COLLECTION / "mathematical_formula_reference.rst"
    if not formula_reference.is_file():
        fail("mathematical formula reference page is missing")
    formula_text = formula_reference.read_text(encoding="utf-8")
    for target in (
        "fop-formula-algebra",
        "fop-formula-product-chain",
        "fop-formula-stationary",
        "fop-formula-fermat",
        "fop-formula-trigonometry",
        "fop-formula-fourier",
        "fop-formula-matrices",
        "fop-formula-vector-calculus",
        "fop-formula-odes",
        "fop-formula-probability",
        "fop-formula-power-decibels",
        "fop-formula-verification",
    ):
        if f".. _{target}:" not in formula_text:
            fail(f"mathematical formula reference omits target {target}")

    snell_svg = (
        SOURCE
        / "_static"
        / "knowledge_base"
        / "worked_exercises"
        / "fundamentals_of_photonics"
        / "snells_law_geometry.svg"
    )
    if not snell_svg.is_file():
        fail("Exercise 1.1-1 geometry SVG is missing")
    svg_text = snell_svg.read_text(encoding="utf-8")
    for variable in ("n₁", "n₂", "d₁", "d₂", "d − x", "θ₁", "θ₂", "P(x)"):
        if variable not in svg_text:
            fail(f"Exercise 1.1-1 geometry SVG omits variable {variable}")
    snell_text = chapter_files[0].read_text(encoding="utf-8")
    for required in (
        "snells_law_geometry.svg",
        "fop-ex-1-1-1-opl",
        "fop-ex-1-1-1-first-derivative",
        "fop-ex-1-1-1-snell-law",
        "fop-formula-square-root-derivative",
    ):
        if required not in snell_text:
            fail(f"Exercise 1.1-1 omits {required}")

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
        f"{len(found_ids)} structured worked solutions; "
        f"{numbered_entries} contain numbered equations "
        f"({len(found_equation_labels)} equation labels)."
    )


if __name__ == "__main__":
    main()
