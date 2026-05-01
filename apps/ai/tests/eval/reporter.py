"""Formatação de resultado de eval pra mensagem de assertion failure e summary final."""

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from tests.eval.runner import EvalResult


def _truncate(text: str, limit: int = 600) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"... [+{len(text) - limit} chars truncated]"


def format_failure(result: "EvalResult") -> str:
    lines: list[str] = []
    lines.append(f"[FAIL] {result.case_id}")
    lines.append(f"  description: {result.description}")
    lines.append(f"  input:       {result.input!r}")
    lines.append("  failures:")
    for f in result.failures:
        lines.append(f"    - {f}")
    if result.actual_tools:
        names = [f"{t.name}({t.args!r})" for t in result.actual_tools]
        lines.append(f"  tools_called: {names}")
    else:
        lines.append("  tools_called: (none)")
    lines.append(f"  response: {_truncate(result.actual_response)!r}")
    lines.append(f"  duration: {result.duration_seconds:.2f}s")
    return "\n".join(lines)


def format_eval_summary(results: list["EvalResult"]) -> str:
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed

    lines: list[str] = []
    lines.append("")
    lines.append("=" * 60)
    lines.append("Eval Suite — Thor")
    lines.append("=" * 60)
    lines.append(f"Total:  {total}")
    lines.append(f"Passed: {passed}")
    lines.append(f"Failed: {failed}")

    if failed > 0:
        lines.append("")
        lines.append("Failures:")
        for r in results:
            if r.passed:
                continue
            lines.append("")
            lines.append(format_failure(r))

    return "\n".join(lines)
