"""Schemas Pydantic dos casos de eval e do dataset YAML."""

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class ExpectedAssertions(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    tool_called: str | None = None
    tool_args: dict[str, Any] = Field(default_factory=dict)
    tool_not_called: str | None = Field(default=None, alias="tool_NOT_called")
    response_contains: list[str] = Field(default_factory=list)
    response_not_contains: list[str] = Field(
        default_factory=list, alias="response_NOT_contains"
    )
    response_regex: list[str] = Field(default_factory=list)


class EvalCase(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    id: str
    description: str
    input: str
    expected: ExpectedAssertions
    tags: list[str] = Field(default_factory=list)


class Dataset(BaseModel):
    cases: list[EvalCase]


_DATASETS_DIR = Path(__file__).resolve().parent / "datasets"


def load_dataset(path: Path) -> Dataset:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Dataset.model_validate(raw)


def discover_dataset_files(directory: Path = _DATASETS_DIR) -> list[Path]:
    return sorted(p for p in directory.glob("*.yaml") if p.is_file())


def load_all_cases(directory: Path = _DATASETS_DIR) -> list[EvalCase]:
    cases: list[EvalCase] = []
    seen_ids: set[str] = set()
    for path in discover_dataset_files(directory):
        dataset = load_dataset(path)
        for case in dataset.cases:
            if case.id in seen_ids:
                raise ValueError(f"duplicate case id {case.id!r} in {path}")
            seen_ids.add(case.id)
            cases.append(case)
    return cases


def cases_iter() -> Iterable[EvalCase]:
    yield from load_all_cases()
