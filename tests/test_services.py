from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from mpie.prompts import PROMPT_SPECS, AssignmentPart
from mpie.schemas import (
    InstrumentExtractionResult,
    OperationsDraftingResult,
    PolicySignalResult,
    RecommendationQualityResult,
)
from mpie.services import AssignmentService


class FakeLLM:
    def __init__(self) -> None:
        self.calls: list[tuple[str, type[BaseModel]]] = []

    def parse(self, prompt: str, text_format: type[BaseModel]) -> BaseModel:
        self.calls.append((prompt, text_format))
        return text_format.model_construct()


@pytest.fixture
def prompt_dir(tmp_path: Path) -> Path:
    for spec in PROMPT_SPECS.values():
        body = "\n".join(f"{{{{{name}}}}}" for name in spec.placeholders)
        (tmp_path / spec.filename).write_text(body, encoding="utf-8")
    return tmp_path


@pytest.mark.parametrize(
    ("part", "payload", "schema", "sentinel"),
    [
        (
            AssignmentPart.A,
            {"CENTRAL_BANK_EXCERPT": "A excerpt"},
            InstrumentExtractionResult,
            "A excerpt",
        ),
        (
            AssignmentPart.B,
            {
                "MODE": "review",
                "RAW_NOTES_OR_EMPTY": "B notes",
                "CB_TEXT_OR_EMPTY": "B source",
            },
            OperationsDraftingResult,
            "B notes",
        ),
        (
            AssignmentPart.C,
            {
                "REPORT_ID": "report-1",
                "RECOMMENDATIONS": "C recommendations",
                "REPORT_CONTENT": "C report",
            },
            RecommendationQualityResult,
            "report-1",
        ),
        (
            AssignmentPart.D,
            {
                "SEQUENCE_INTEGER": 0,
                "STABLE_SPEECH_ID": "speech-1",
                "DATE_OR_EMPTY": "",
                "SPEAKER_OR_EMPTY": "",
                "BIS_SPEECH_TEXT": "D speech",
            },
            PolicySignalResult,
            "speech-1",
        ),
    ],
)
def test_service_routes_each_part_to_its_prompt_and_schema(
    prompt_dir: Path,
    part: AssignmentPart,
    payload: dict[str, Any],
    schema: type[BaseModel],
    sentinel: str,
) -> None:
    llm = FakeLLM()
    service = AssignmentService(llm, prompt_dir=prompt_dir)

    result = service.run(part, **payload)

    assert isinstance(result, schema)
    assert llm.calls[-1][1] is schema
    assert sentinel in llm.calls[-1][0]
