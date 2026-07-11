import pytest

from workflow_automation.templating import TemplateResolutionError, resolve


def test_whole_string_template_resolves_to_native_type():
    steps_output = {"fetch": {"status_code": 200, "body": {"ok": True}}}
    assert resolve("{{steps.fetch.output.status_code}}", steps_output) == 200
    assert resolve("{{steps.fetch.output.body}}", steps_output) == {"ok": True}


def test_embedded_template_resolves_via_string_interpolation():
    steps_output = {"fetch": {"name": "Acme"}}
    assert resolve("Hello, {{steps.fetch.output.name}}!", steps_output) == "Hello, Acme!"


def test_resolves_recursively_through_dicts_and_lists():
    steps_output = {"a": {"x": 1}}
    value = {"list": ["{{steps.a.output.x}}", "literal"], "nested": {"y": "{{steps.a.output.x}}"}}
    resolved = resolve(value, steps_output)
    assert resolved == {"list": [1, "literal"], "nested": {"y": 1}}


def test_unknown_step_raises():
    with pytest.raises(TemplateResolutionError):
        resolve("{{steps.missing.output.x}}", {})


def test_unknown_path_raises():
    with pytest.raises(TemplateResolutionError):
        resolve("{{steps.a.output.nope}}", {"a": {"x": 1}})


def test_non_string_non_container_passes_through():
    assert resolve(42, {}) == 42
    assert resolve(None, {}) is None
