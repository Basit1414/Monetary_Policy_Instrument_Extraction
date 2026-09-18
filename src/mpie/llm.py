"""OpenAI Responses API adapter for typed assignment outputs."""

from __future__ import annotations

from typing import Any, Protocol, TypeVar, cast

from pydantic import BaseModel

from .config import DEFAULT_MODEL

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class StructuredLLM(Protocol):
    def parse(self, prompt: str, text_format: type[SchemaT]) -> SchemaT:
        """Return a response validated against ``text_format``."""


class StructuredResponseError(RuntimeError):
    pass


class OpenAIResponsesLLM:
    """Thin, injectable wrapper around ``client.responses.parse``."""

    def __init__(self, client: Any, *, model: str = DEFAULT_MODEL) -> None:
        if not model.strip():
            raise ValueError("model must not be empty")
        self._client = client
        self.model = model.strip()

    @classmethod
    def from_api_key(cls, api_key: str, *, model: str = DEFAULT_MODEL) -> OpenAIResponsesLLM:
        """Create an SDK client from an in-memory key.

        The key is passed directly to the OpenAI SDK and is never written by this
        application. Importing lazily keeps offline schema tests independent of
        the SDK.
        """

        if not api_key.strip():
            raise ValueError("an OpenAI API key is required")
        from openai import OpenAI

        return cls(OpenAI(api_key=api_key.strip()), model=model)

    def parse(self, prompt: str, text_format: type[SchemaT]) -> SchemaT:
        response = self._client.responses.parse(
            model=self.model,
            input=prompt,
            text_format=text_format,
        )
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise StructuredResponseError("the model returned no parsed structured output")
        if isinstance(parsed, text_format):
            return cast(SchemaT, parsed)
        return text_format.model_validate(parsed)
