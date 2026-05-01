"""Pytest fixtures e hooks pra eval suite."""

import asyncio
import sys

import pytest


_RESULTS_KEY = "_thor_eval_results"


def pytest_configure(config: pytest.Config) -> None:
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except Exception:
            pass
    config.stash[_eval_stash_key()] = []  # type: ignore[arg-type]


def _eval_stash_key() -> pytest.StashKey[list]:
    if not hasattr(_eval_stash_key, "_key"):
        _eval_stash_key._key = pytest.StashKey[list]()  # type: ignore[attr-defined]
    return _eval_stash_key._key  # type: ignore[attr-defined,no-any-return]


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[None]):
    outcome = yield
    report = outcome.get_result()
    if report.when != "call":
        return
    eval_result = getattr(item, "_thor_eval_result", None)
    if eval_result is None:
        return
    bucket: list = item.config.stash[_eval_stash_key()]
    bucket.append(eval_result)


def pytest_terminal_summary(
    terminalreporter: pytest.TerminalReporter,
    exitstatus: int,
    config: pytest.Config,
) -> None:
    bucket: list = config.stash.get(_eval_stash_key(), [])
    if not bucket:
        return
    from tests.eval.reporter import format_eval_summary

    terminalreporter.write_line("")
    terminalreporter.write(format_eval_summary(bucket))
    terminalreporter.write_line("")
