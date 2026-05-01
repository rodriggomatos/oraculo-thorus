"""Eval suite — itera nos datasets YAML e roda 1 test_case por entrada."""

import pytest

from tests.eval.reporter import format_failure
from tests.eval.runner import get_or_build_agent, run_case
from tests.eval.schemas import EvalCase, load_all_cases


_ALL_CASES = load_all_cases()


@pytest.mark.eval
@pytest.mark.parametrize("case", _ALL_CASES, ids=[c.id for c in _ALL_CASES])
async def test_eval_case(request: pytest.FixtureRequest, case: EvalCase) -> None:
    agent = await get_or_build_agent()
    result = await run_case(agent, case)
    request.node._thor_eval_result = result
    assert result.passed, format_failure(result)
