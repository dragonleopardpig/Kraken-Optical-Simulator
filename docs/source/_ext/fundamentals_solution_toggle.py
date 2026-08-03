"""Add brief solution steps and expandable details to Fundamentals items."""

from __future__ import annotations

import re

from docutils import nodes


COLLECTION_PREFIX = (
    "knowledge_base/worked_exercises/fundamentals_of_photonics/ch"
)
ITEM_TITLE = re.compile(r"^(Exercise|Problem) \d+\.\d+-\d+\b")


def _leading_strong_text(node: nodes.Node) -> str:
    if not isinstance(node, nodes.paragraph) or not node.children:
        return ""
    first = node.children[0]
    return first.astext() if isinstance(first, nodes.strong) else ""


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


def _is_substantive(node: nodes.Node) -> bool:
    return (
        isinstance(
            node,
            (
                nodes.paragraph,
                nodes.math_block,
                nodes.bullet_list,
                nodes.enumerated_list,
                nodes.table,
            ),
        )
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
    content: list[nodes.Node], check_index: int
) -> list[nodes.Node]:
    result_index = next(
        (
            index
            for index, child in enumerate(content[:check_index])
            if _is_explicit_result(child)
        ),
        None,
    )
    if result_index is not None:
        explicit = [
            child
            for child in content[result_index + 1 : check_index]
            if _is_substantive(child)
        ]
        if explicit:
            return explicit

    candidates = [
        (index, child)
        for index, child in enumerate(content[:check_index])
        if _is_substantive(child)
    ]
    boxed = [entry for entry in candidates if _contains_boxed_math(entry[1])]
    if boxed:
        boxed_index, boxed_node = boxed[-1]
        companion = next(
            (
                child
                for index, child in candidates
                if index > boxed_index and isinstance(child, nodes.paragraph)
            ),
            None,
        )
        return [boxed_node, *([companion] if companion is not None else [])]

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


def _brief_parts(
    section: nodes.section,
) -> tuple[nodes.paragraph | None, list[nodes.Node], list[nodes.Node]]:
    content = list(section.children[1:])
    check_index = next(
        (index for index, child in enumerate(content) if _is_check(child)),
        len(content),
    )
    answer = _answer_nodes(content, check_index)
    answer_ids = {id(child) for child in answer}

    method = next(
        (
            child
            for child in content[:check_index]
            if _is_formula_marker(child)
        ),
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
            if _is_substantive(child) and id(child) not in answer_ids
        ]

    return method, _decisive_nodes(working), answer


def _sanitized_copy(node: nodes.Node) -> nodes.Node:
    clone = node.deepcopy()
    for descendant in clone.findall(include_self=True):
        if not isinstance(descendant, nodes.Element):
            continue
        for attribute in (
            "ids",
            "names",
            "dupnames",
            "backrefs",
        ):
            if attribute in descendant:
                descendant[attribute] = []
        if isinstance(descendant, nodes.math_block):
            descendant["label"] = None
            descendant["number"] = None
    return clone


def _brief_step(label: str, content: list[nodes.Node]) -> nodes.container:
    step = nodes.container(classes=["fop-brief-step"])
    step += nodes.paragraph(
        "",
        "",
        nodes.strong("", label),
        classes=["fop-brief-step-label"],
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
    method_copy["classes"].append("fop-brief-step-label")
    step = nodes.container(classes=["fop-brief-step"])
    step += method_copy
    return step


def _transform_solutions(app, doctree: nodes.document, docname: str) -> None:
    if not docname.startswith(COLLECTION_PREFIX):
        return

    for section in list(doctree.findall(nodes.section)):
        if not section.children or not isinstance(section.children[0], nodes.title):
            continue
        if not ITEM_TITLE.match(section.children[0].astext()):
            continue

        original = list(section.children[1:])
        if not original:
            continue

        method, working, answer = _brief_parts(section)
        brief = nodes.container(classes=["fop-brief-answer"])
        brief += nodes.paragraph(
            "",
            "",
            nodes.strong("", "Brief solution"),
            classes=["fop-brief-title"],
        )
        if method is not None:
            brief += _method_step(method)
        if working:
            brief += _brief_step("2. Key step.", working)
        if answer:
            label = "3. Answer." if working else "2. Reasoning and answer."
            brief += _brief_step(label, answer)

        detail_open = nodes.raw(
            "",
            '<details class="fop-solution-detail">'
            '<summary><span class="fop-show-label">Show detailed steps</span>'
            '<span class="fop-hide-label">Hide detailed steps</span></summary>'
            '<div class="fop-solution-detail-body">',
            format="html",
        )
        detail_close = nodes.raw("", "</div></details>", format="html")
        section.children[1:] = [brief, detail_open, *original, detail_close]
        for child in section.children[1:]:
            child.parent = section


def setup(app):
    app.connect("doctree-resolved", _transform_solutions)
    app.add_css_file(
        "knowledge_base/worked_exercises/fundamentals_of_photonics/"
        "solution_toggle.css"
    )
    return {
        "version": "1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
