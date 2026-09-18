"""Assignment service routing and serialization helpers."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from .config import PROJECT_ROOT
from .llm import StructuredLLM
from .prompts import AssignmentPart, coerce_part, render_part_prompt
from .schemas import (
    InstrumentExtractionResult,
    OperationsDraftingResult,
    PolicySignalResult,
    RecommendationQualityResult,
)

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class AssignmentService:
    """Render the correct task prompt and request its matching schema."""

    def __init__(
        self,
        llm: StructuredLLM,
        *,
        prompt_dir: Path | str = PROJECT_ROOT / "prompts",
    ) -> None:
        self.llm = llm
        self.prompt_dir = Path(prompt_dir)

    def _execute(
        self,
        part: AssignmentPart,
        values: dict[str, object],
        schema: type[SchemaT],
    ) -> SchemaT:
        prompt = render_part_prompt(part, prompt_dir=self.prompt_dir, values=values)
        return self.llm.parse(prompt, schema)

    def run_part_a(self, *, CENTRAL_BANK_EXCERPT: str) -> InstrumentExtractionResult:
        return self._execute(
            AssignmentPart.A,
            {"CENTRAL_BANK_EXCERPT": CENTRAL_BANK_EXCERPT},
            InstrumentExtractionResult,
        )

    def run_part_b(
        self,
        *,
        MODE: str,
        RAW_NOTES_OR_EMPTY: str,
        CB_TEXT_OR_EMPTY: str,
    ) -> OperationsDraftingResult:
        return self._execute(
            AssignmentPart.B,
            {
                "MODE": MODE,
                "RAW_NOTES_OR_EMPTY": RAW_NOTES_OR_EMPTY,
                "CB_TEXT_OR_EMPTY": CB_TEXT_OR_EMPTY,
            },
            OperationsDraftingResult,
        )

    def run_part_c(
        self,
        *,
        REPORT_ID: str,
        RECOMMENDATIONS: str,
        REPORT_CONTENT: str,
    ) -> RecommendationQualityResult:
        return self._execute(
            AssignmentPart.C,
            {
                "REPORT_ID": REPORT_ID,
                "RECOMMENDATIONS": RECOMMENDATIONS,
                "REPORT_CONTENT": REPORT_CONTENT,
            },
            RecommendationQualityResult,
        )

    def run_part_d(
        self,
        *,
        SEQUENCE_INTEGER: int,
        STABLE_SPEECH_ID: str,
        DATE_OR_EMPTY: str,
        SPEAKER_OR_EMPTY: str,
        BIS_SPEECH_TEXT: str,
    ) -> PolicySignalResult:
        return self._execute(
            AssignmentPart.D,
            {
                "SEQUENCE_INTEGER": SEQUENCE_INTEGER,
                "STABLE_SPEECH_ID": STABLE_SPEECH_ID,
                "DATE_OR_EMPTY": DATE_OR_EMPTY,
                "SPEAKER_OR_EMPTY": SPEAKER_OR_EMPTY,
                "BIS_SPEECH_TEXT": BIS_SPEECH_TEXT,
            },
            PolicySignalResult,
        )

    def run(self, part: AssignmentPart | str, **values: object) -> BaseModel:
        """Route a generic UI/API request to an explicitly typed task method."""

        normalized = coerce_part(part)
        routes = {
            AssignmentPart.A: self.run_part_a,
            AssignmentPart.B: self.run_part_b,
            AssignmentPart.C: self.run_part_c,
            AssignmentPart.D: self.run_part_d,
        }
        return routes[normalized](**values)  # type: ignore[arg-type]


def result_to_json(result: BaseModel) -> str:
    return json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n"


def result_to_jsonl(result: BaseModel) -> str:
    """Serialize exactly one validated result per line."""

    return (
        json.dumps(result.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":")) + "\n"
    )


def _csv_scalar(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return value


def _flatten_record(record: dict[str, Any], *, prefix: str = "") -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    for key, value in record.items():
        column = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flattened.update(_flatten_record(value, prefix=column))
        else:
            flattened[column] = _csv_scalar(value)
    return flattened


def _result_rows(result: BaseModel) -> list[dict[str, Any]]:
    data = result.model_dump(mode="json")
    context = {
        key: _csv_scalar(value)
        for key, value in data.items()
        if not (isinstance(value, list) and value and all(isinstance(item, dict) for item in value))
    }
    list_sections = {
        key: value
        for key, value in data.items()
        if isinstance(value, list) and value and all(isinstance(item, dict) for item in value)
    }
    if not list_sections:
        return [_flatten_record(data)]

    rows: list[dict[str, Any]] = []
    for section, records in list_sections.items():
        for record in records:
            rows.append({"section": section, **context, **_flatten_record(record)})
    return rows


def result_to_csv(result: BaseModel) -> str:
    rows = _result_rows(result)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)

    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()
