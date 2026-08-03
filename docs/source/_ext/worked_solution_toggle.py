"""Add compact solution steps and expandable details to worked exercises."""

from __future__ import annotations

import re
from collections.abc import Callable

from docutils import nodes


WORKED_PREFIX = "knowledge_base/worked_exercises/"
FUNDAMENTALS_PREFIX = f"{WORKED_PREFIX}fundamentals_of_photonics/ch"
UNDERSTANDING_PAGE = re.compile(
    rf"^{WORKED_PREFIX}understanding_lasers_ch\d+_quiz$"
)
PHOTONICS_PAGE = re.compile(
    rf"^{WORKED_PREFIX}photonics_essentials/(?:ch\d+_problems|ch11_questions)$"
)
MATRIX_PAGE = re.compile(
    rf"^{WORKED_PREFIX}introduction_matrix_methods_optics/"
    r"(?:ch02_paraxial_optics|ch03_resonators_and_laser_beams|"
    r"ch04_polarization_optics|appendix_a_apertures)$"
)
ROUTE_PREFIXES = (
    f"{WORKED_PREFIX}hecht_optics_5e/ch",
    f"{WORKED_PREFIX}siegman_lasers/ch",
    f"{WORKED_PREFIX}yariv_yeh_photonics_6e/ch",
)
FUNDAMENTALS_ITEM = re.compile(r"^(Exercise|Problem) \d+\.\d+-\d+\b")
PROBLEM_ITEM = re.compile(
    r"^Problem (?:\d+(?:\.\d+){1,2}|A\.\d+)(?:\*)?\s*(?:—|:)"
)
NUMBERED_QUIZ_ITEM = re.compile(r"^\d+\.\s+")

ContentPredicate = Callable[[nodes.Node], bool]


def _document_profile(docname: str) -> str | None:
    if docname.startswith(FUNDAMENTALS_PREFIX):
        return "fundamentals"
    if UNDERSTANDING_PAGE.match(docname):
        return "quiz"
    if PHOTONICS_PAGE.match(docname) or MATRIX_PAGE.match(docname):
        return "freeform"
    if docname.startswith(ROUTE_PREFIXES):
        return "route"
    return None


def _leading_strong_text(node: nodes.Node) -> str:
    if not isinstance(node, nodes.paragraph) or not node.children:
        return ""
    first = node.children[0]
    return first.astext() if isinstance(first, nodes.strong) else ""


def _is_content_node(node: nodes.Node) -> bool:
    return isinstance(
        node,
        (
            nodes.paragraph,
            nodes.math_block,
            nodes.bullet_list,
            nodes.enumerated_list,
            nodes.table,
        ),
    )


def _is_compact_content(node: nodes.Node) -> bool:
    return _is_content_node(node) and not isinstance(node, nodes.table)


def _is_check(node: nodes.Node) -> bool:
    marker = _leading_strong_text(node)
    return marker.startswith(("Step 5", "Check.", "Checks."))


def _is_explicit_result(node: nodes.Node) -> bool:
    marker = _leading_strong_text(node)
    return "State the numbered result" in marker or marker.startswith(
        ("Numbered result.", "Numbered results.")
    )


def _is_formula_marker(node: nodes.Node) -> bool:
    marker = _leading_strong_text(node)
    return marker.startswith(("Step 2", "Mathematical formulas used."))


def _is_derivation_marker(node: nodes.Node) -> bool:
    marker = _leading_strong_text(node)
    return marker.startswith(("Step 3", "Worked derivation."))


def _is_boilerplate(node: nodes.Node) -> bool:
    return node.astext().startswith(
        "The calculation is kept in symbolic form until the governing relation"
    )


def _is_fundamentals_content(node: nodes.Node) -> bool:
    return (
        _is_content_node(node)
        and not _leading_strong_text(node)
        and not _is_boilerplate(node)
    )


def _contains_boxed_math(node: nodes.Node) -> bool:
    if isinstance(node, (nodes.math, nodes.math_block)):
        return r"\boxed" in node.astext()
    return any(
        r"\boxed" in descendant.astext()
        for descendant in node.findall(
            lambda candidate: isinstance(candidate, (nodes.math, nodes.math_block))
        )
    )


def _answer_nodes(
    content: list[nodes.Node],
    end_index: int,
    is_content: ContentPredicate,
    *,
    explicit_result: bool,
    explicit_answer: bool = False,
) -> list[nodes.Node]:
    if explicit_answer:
        answer = next(
            (
                child
                for child in content[:end_index]
                if _leading_strong_text(child).startswith("Answer")
            ),
            None,
        )
        if answer is not None:
            return [answer]

    if explicit_result:
        result_index = next(
            (
                index
                for index, child in enumerate(content[:end_index])
                if _is_explicit_result(child)
            ),
            None,
        )
        if result_index is not None:
            result = [
                child
                for child in content[result_index + 1 : end_index]
                if is_content(child)
            ]
            if result:
                return result

    candidates = [
        (index, child)
        for index, child in enumerate(content[:end_index])
        if is_content(child)
    ]
    boxed = [
        entry
        for entry in candidates
        if isinstance(entry[1], (nodes.paragraph, nodes.math_block))
        and _contains_boxed_math(entry[1])
    ]
    if boxed:
        boxed_index = boxed[-1][0]
        companion = next(
            (
                child
                for index, child in candidates
                if index > boxed_index and isinstance(child, nodes.paragraph)
            ),
            None,
        )
        boxed_nodes = [child for _, child in boxed]
        return [*boxed_nodes, *([companion] if companion is not None else [])]

    return [candidates[-1][1]] if candidates else []


def _decisive_nodes(candidates: list[nodes.Node]) -> list[nodes.Node]:
    if len(candidates) <= 3:
        return candidates

    selected = [candidates[0], candidates[-1]]
    displayed_math = [
        child for child in candidates[1:-1] if isinstance(child, nodes.math_block)
    ]
    if displayed_math:
        selected.append(displayed_math[-1])
    positions = {id(child): index for index, child in enumerate(candidates)}
    unique = {id(child): child for child in selected}.values()
    return sorted(unique, key=lambda child: positions[id(child)])


def _fundamentals_parts(
    section: nodes.section,
) -> tuple[nodes.paragraph | None, list[nodes.Node], list[nodes.Node]]:
    content = list(section.children[1:])
    check_index = next(
        (index for index, child in enumerate(content) if _is_check(child)),
        len(content),
    )
    answer = _answer_nodes(
        content,
        check_index,
        _is_fundamentals_content,
        explicit_result=True,
    )
    answer_ids = {id(child) for child in answer}
    method = next(
        (child for child in content[:check_index] if _is_formula_marker(child)),
        None,
    )
    derivation_index = next(
        (
            index
            for index, child in enumerate(content[:check_index])
            if _is_derivation_marker(child)
        ),
        None,
    )
    result_index = next(
        (
            index
            for index, child in enumerate(content[:check_index])
            if _is_explicit_result(child)
        ),
        check_index,
    )
    working = []
    if derivation_index is not None:
        working = [
            child
            for child in content[derivation_index + 1 : result_index]
            if _is_fundamentals_content(child) and id(child) not in answer_ids
        ]
    return method, _decisive_nodes(working), answer


def _generic_parts(
    content: list[nodes.Node], *, explicit_answer: bool = False
) -> tuple[list[nodes.Node], list[nodes.Node], list[nodes.Node]]:
    answer = _answer_nodes(
        content,
        len(content),
        _is_compact_content,
        explicit_result=False,
        explicit_answer=explicit_answer,
    )
    answer_ids = {id(child) for child in answer}
    answer_index = max(
        (
            index
            for index, child in enumerate(content)
            if id(child) in answer_ids and _contains_boxed_math(child)
        ),
        default=len(content),
    )
    if answer_index == len(content):
        answer_index = min(
            (
                index
                for index, child in enumerate(content)
                if id(child) in answer_ids
            ),
            default=len(content),
        )
    working_region = content if explicit_answer else content[:answer_index]
    remaining = [
        child
        for child in working_region
        if _is_compact_content(child) and id(child) not in answer_ids
    ]
    method = remaining[:1]
    working_candidates = remaining[1:]
    displayed_math = [
        child
        for child in working_candidates
        if isinstance(child, nodes.math_block)
    ]
    working = displayed_math[-1:] or working_candidates[-1:]
    return method, working, answer


def _split_paragraph_lines(paragraph: nodes.paragraph) -> list[nodes.paragraph]:
    lines = [nodes.paragraph()]
    for child in paragraph.children:
        if not isinstance(child, nodes.Text):
            lines[-1] += child.deepcopy()
            continue
        parts = str(child).split("\n")
        for index, part in enumerate(parts):
            if part:
                lines[-1] += nodes.Text(part)
            if index < len(parts) - 1:
                lines.append(nodes.paragraph())
    return [line for line in lines if line.astext().strip()]


def _sanitized_copy(node: nodes.Node) -> nodes.Node:
    clone = node.deepcopy()
    for descendant in clone.findall(include_self=True):
        if not isinstance(descendant, nodes.Element):
            continue
        for attribute in ("ids", "names", "dupnames", "backrefs"):
            if attribute in descendant:
                descendant[attribute] = []
        if isinstance(descendant, nodes.math_block):
            descendant["label"] = None
            descendant["number"] = None
    return clone


def _brief_step(label: str, content: list[nodes.Node]) -> nodes.container:
    step = nodes.container(classes=["worked-brief-step"])
    step += nodes.paragraph(
        "",
        "",
        nodes.strong("", label),
        classes=["worked-brief-step-label"],
    )
    for content_node in content:
        step += _sanitized_copy(content_node)
    return step


def _method_step(method: nodes.paragraph) -> nodes.container:
    method_copy = _sanitized_copy(method)
    leading = method_copy.children[0]
    if isinstance(leading, nodes.strong):
        leading.children = [nodes.Text("1. Method.")]
        leading.children[0].parent = leading
    method_copy["classes"].append("worked-brief-step-label")
    step = nodes.container(classes=["worked-brief-step"])
    step += method_copy
    return step


def _brief_container() -> nodes.container:
    brief = nodes.container(classes=["worked-brief-solution"])
    brief += nodes.paragraph(
        "",
        "",
        nodes.strong("", "Brief solution"),
        classes=["worked-brief-title"],
    )
    return brief


def _fundamentals_brief(section: nodes.section) -> nodes.container:
    method, working, answer = _fundamentals_parts(section)
    brief = _brief_container()
    if method is not None:
        brief += _method_step(method)
    if working:
        brief += _brief_step("2. Key step.", working)
    if answer:
        label = "3. Answer." if working else "2. Reasoning and answer."
        brief += _brief_step(label, answer)
    return brief


def _freeform_brief(
    content: list[nodes.Node], *, explicit_answer: bool = False
) -> nodes.container:
    method, working, answer = _generic_parts(
        content, explicit_answer=explicit_answer
    )
    brief = _brief_container()
    if method:
        brief += _brief_step("1. Method.", method)
    if working:
        brief += _brief_step("2. Key step.", working)
    if answer:
        answer_number = 3 if working else 2
        brief += _brief_step(f"{answer_number}. Answer.", answer)
    return brief


def _route_brief(content: list[nodes.Node]) -> nodes.container:
    route = [child for child in content if _is_content_node(child)]
    if len(route) == 1 and isinstance(route[0], nodes.paragraph):
        route = _split_paragraph_lines(route[0])
    brief = _brief_container()
    if route:
        brief += _brief_step("1. Method.", route[:1])
    if len(route) > 1:
        brief += _brief_step("2. Decisive step.", route[1:2])
    if len(route) > 2:
        brief += _brief_step("3. Verification.", route[2:3])
    return brief


def _quiz_list_brief(content: list[nodes.Node]) -> nodes.container:
    brief = _brief_container()
    first_paragraph = next(
        (child for child in content if isinstance(child, nodes.paragraph)),
        None,
    )
    if first_paragraph is not None:
        brief += _brief_step("1. Reasoning and answer.", [first_paragraph])
    displayed_math = [
        child for child in content if isinstance(child, nodes.math_block)
    ]
    if displayed_math:
        brief += _brief_step("2. Key calculation.", displayed_math[-1:])
    return brief


def _details_open() -> nodes.raw:
    return nodes.raw(
        "",
        '<details class="worked-solution-detail">'
        '<summary><span class="worked-show-label">Show detailed steps</span>'
        '<span class="worked-hide-label">Hide detailed steps</span></summary>'
        '<div class="worked-solution-detail-body">',
        format="html",
    )


def _wrap_content(
    parent: nodes.Element, offset: int, brief: nodes.container
) -> None:
    original = list(parent.children[offset:])
    if not original:
        return
    detail_close = nodes.raw("", "</div></details>", format="html")
    parent.children[offset:] = [brief, _details_open(), *original, detail_close]
    for child in parent.children[offset:]:
        child.parent = parent


def _section_matches(section: nodes.section, profile: str, docname: str) -> bool:
    if not section.children or not isinstance(section.children[0], nodes.title):
        return False
    title = section.children[0].astext()
    if profile == "fundamentals":
        return bool(FUNDAMENTALS_ITEM.match(title))
    if profile == "quiz":
        return bool(NUMBERED_QUIZ_ITEM.match(title))
    if docname.endswith("photonics_essentials/ch11_questions"):
        return title.endswith("?")
    return bool(PROBLEM_ITEM.match(title))


def _transform_quiz_list(doctree: nodes.document) -> None:
    for section in list(doctree.findall(nodes.section)):
        if not section.children or not isinstance(section.children[0], nodes.title):
            continue
        if section.children[0].astext() != "Worked reasoning":
            continue
        for child in section.children[1:]:
            if not isinstance(child, nodes.enumerated_list):
                continue
            for item in child.children:
                if isinstance(item, nodes.list_item):
                    _wrap_content(item, 0, _quiz_list_brief(list(item.children)))


def _transform_solutions(app, doctree: nodes.document, docname: str) -> None:
    profile = _document_profile(docname)
    if profile is None:
        return

    if profile == "quiz":
        _transform_quiz_list(doctree)

    for section in list(doctree.findall(nodes.section)):
        if not _section_matches(section, profile, docname):
            continue
        content = list(section.children[1:])
        if profile == "fundamentals":
            brief = _fundamentals_brief(section)
        elif profile == "route":
            brief = _route_brief(content)
        else:
            brief = _freeform_brief(
                content,
                explicit_answer=profile == "quiz",
            )
        _wrap_content(section, 1, brief)


def setup(app):
    app.connect("doctree-resolved", _transform_solutions)
    app.add_css_file("knowledge_base/worked_exercises/solution_toggle.css")
    return {
        "version": "2.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
