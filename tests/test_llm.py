from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from mpie.llm import OpenAIResponsesLLM, StructuredResponseError
from mpie.schemas import InstrumentExtractionResult


class FakeResponses:
    def __init__(self, parsed: Any) -> None:
        self.parsed = parsed
        self.kwargs: dict[str, Any] | None = None

    def parse(self, **kwargs: Any) -> SimpleNamespace:
        self.kwargs = kwargs
        return SimpleNamespace(output_parsed=self.parsed)


class FakeClient:
    def __init__(self, parsed: Any) -> None:
        self.responses = FakeResponses(parsed)


def test_responses_adapter_uses_text_format_without_live_api_call() -> None:
    client = FakeClient({"status": "no_instruments", "instruments": []})
    llm = OpenAIResponsesLLM(client, model="test-model")

    result = llm.parse("prompt text", InstrumentExtractionResult)

    assert result.status.value == "no_instruments"
    assert client.responses.kwargs == {
        "model": "test-model",
        "input": "prompt text",
        "text_format": InstrumentExtractionResult,
    }


def test_responses_adapter_rejects_missing_parsed_output() -> None:
    llm = OpenAIResponsesLLM(FakeClient(None), model="test-model")
    with pytest.raises(StructuredResponseError, match="no parsed"):
        llm.parse("prompt text", InstrumentExtractionResult)
