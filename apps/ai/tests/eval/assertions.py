"""Asserts simples sobre resposta + tools chamadas. Sem LLM-as-judge."""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from tests.eval.runner import ToolCallRecord
    from tests.eval.schemas import ExpectedAssertions


@dataclass(frozen=True)
class AssertionResult:
    passed: bool
    reason: str


def _find_matching_call(
    name: str,
    expected_args: dict[str, Any],
    calls: Sequence["ToolCallRecord"],
) -> "ToolCallRecord | None":
    for call in calls:
        if call.name != name:
            continue
        if all(call.args.get(k) == v for k, v in expected_args.items()):
            return call
    return None


def assert_tool_called(
    name: str,
    expected_args: dict[str, Any],
    calls: Sequence["ToolCallRecord"],
) -> AssertionResult:
    candidates = [c for c in calls if c.name == name]
    if not candidates:
        called_names = [c.name for c in calls] or ["(none)"]
        return AssertionResult(
            False,
            f"expected tool {name!r} to be called; tools called: {called_names}",
        )
    if not expected_args:
        return AssertionResult(True, f"tool {name!r} was called")

    match = _find_matching_call(name, expected_args, calls)
    if match is None:
        actual_args_list = [c.args for c in candidates]
        return AssertionResult(
            False,
            f"tool {name!r} called but args did not match {expected_args!r}; "
            f"actual args seen: {actual_args_list!r}",
        )
    return AssertionResult(True, f"tool {name!r} called with matching args")


def assert_tool_not_called(
    name: str,
    calls: Sequence["ToolCallRecord"],
) -> AssertionResult:
    matched = [c for c in calls if c.name == name]
    if matched:
        return AssertionResult(
            False,
            f"tool {name!r} was called but should NOT have been (calls: {[c.args for c in matched]!r})",
        )
    return AssertionResult(True, f"tool {name!r} was not called")


def assert_response_contains(
    fragments: Sequence[str], response: str
) -> AssertionResult:
    missing = [f for f in fragments if f not in response]
    if missing:
        return AssertionResult(
            False,
            f"response missing required fragment(s): {missing!r}",
        )
    return AssertionResult(True, "all required fragments present")


def assert_response_not_contains(
    forbidden: Sequence[str], response: str
) -> AssertionResult:
    found = [f for f in forbidden if f in response]
    if found:
        return AssertionResult(
            False,
            f"response contains forbidden fragment(s): {found!r}",
        )
    return AssertionResult(True, "no forbidden fragments present")


def assert_response_regex(
    patterns: Sequence[str], response: str
) -> AssertionResult:
    failed: list[str] = []
    for pattern in patterns:
        if re.search(pattern, response) is None:
            failed.append(pattern)
    if failed:
        return AssertionResult(
            False,
            f"response did not match required regex pattern(s): {failed!r}",
        )
    return AssertionResult(True, "all regex patterns matched")


def evaluate_assertions(
    expected: "ExpectedAssertions",
    response: str,
    tools: Sequence["ToolCallRecord"],
) -> list[str]:
    failures: list[str] = []

    if expected.tool_called:
        result = assert_tool_called(expected.tool_called, expected.tool_args, tools)
        if not result.passed:
            failures.append(result.reason)

    if expected.tool_not_called:
        result = assert_tool_not_called(expected.tool_not_called, tools)
        if not result.passed:
            failures.append(result.reason)

    if expected.response_contains:
        result = assert_response_contains(expected.response_contains, response)
        if not result.passed:
            failures.append(result.reason)

    if expected.response_not_contains:
        result = assert_response_not_contains(expected.response_not_contains, response)
        if not result.passed:
            failures.append(result.reason)

    if expected.response_regex:
        result = assert_response_regex(expected.response_regex, response)
        if not result.passed:
            failures.append(result.reason)

    return failures
