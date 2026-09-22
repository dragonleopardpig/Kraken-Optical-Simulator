"""Guard support: read a state variable's DEFAULT from a constructor's source (step 1c, bugs/0852).

Several guards asserted "this toggle defaults to X" by searching the source for the exact text
``tk.BooleanVar(value=X)`` -- which stopped matching the moment the constructors made their
variables through the UI host (``self.ui.boolean_var(value=X)``) although no default changed. This
answers the question they were asking instead: whatever factory makes ``self.<attr>`` in
``cls.__init__``, what is its ``value=``?
"""
from __future__ import annotations

import ast
import inspect
import textwrap
from typing import Any

_MISSING = object()


def constructor_variable_default(cls, attr: str, method: str = "__init__") -> Any:
    """The literal ``value=`` of the call assigned to ``self.<attr>`` in ``cls.<method>``.

    Raises LookupError when there is no such assignment, and ValueError when the default is not
    a literal -- a guard should fail loudly, not compare against a guess."""
    source = textwrap.dedent(inspect.getsource(getattr(cls, method)))
    found: Any = _MISSING
    for node in ast.walk(ast.parse(source)):
        if not (isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)):
            continue
        for target in node.targets:
            if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) \
                    and target.value.id == "self" and target.attr == attr:
                for keyword in node.value.keywords:
                    if keyword.arg == "value":
                        found = ast.literal_eval(keyword.value)
    if found is _MISSING:
        raise LookupError(f"{cls.__name__}.{method} makes no self.{attr} with a literal value=")
    return found
