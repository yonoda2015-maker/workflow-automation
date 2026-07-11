"""Resolves `{{steps.<id>.output.<path>}}` references against prior step outputs.
Deliberately tiny — no eval(), no Jinja — this only ever walks a dict/list tree by
dotted path, so there is no code-execution surface even on an untrusted template."""
from __future__ import annotations

import re
from typing import Any

_TEMPLATE_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}")
_MAX_TEMPLATE_DEPTH = 10  # a config value nested deeper than this is a workflow bug


class TemplateResolutionError(Exception):
    pass


def _lookup(path: str, steps_output: dict[str, dict[str, Any]]) -> Any:
    parts = path.split(".")
    assert len(parts) <= _MAX_TEMPLATE_DEPTH, f"template path too deep: {path!r}"
    if len(parts) < 3 or parts[0] != "steps":
        raise TemplateResolutionError(f"expected 'steps.<id>.output...', got {path!r}")

    step_id = parts[1]
    if step_id not in steps_output:
        raise TemplateResolutionError(f"no output recorded for step {step_id!r}")

    node: Any = {"output": steps_output[step_id]}
    for part in parts[2:]:
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            raise TemplateResolutionError(f"path {path!r} not found in step {step_id!r} output")
    return node


def resolve(value: Any, steps_output: dict[str, dict[str, Any]]) -> Any:
    """Recursively resolves templates in strings/dicts/lists. A string that is
    *exactly* one `{{...}}` expression resolves to the referenced value's real type
    (int, dict, list, ...); a string with a template embedded in other text is
    resolved via plain string interpolation."""
    if isinstance(value, dict):
        return {k: resolve(v, steps_output) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve(v, steps_output) for v in value]
    if not isinstance(value, str):
        return value

    whole_match = _TEMPLATE_RE.fullmatch(value.strip())
    if whole_match:
        return _lookup(whole_match.group(1), steps_output)

    def _sub(match: re.Match) -> str:
        return str(_lookup(match.group(1), steps_output))

    return _TEMPLATE_RE.sub(_sub, value)
