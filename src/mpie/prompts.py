"""Load and render version-controlled Markdown prompt templates."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .config import PROJECT_ROOT


class AssignmentPart(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


@dataclass(frozen=True)
class PromptSpec:
    filename: str
    placeholders: tuple[str, ...]


PROMPT_SPECS: dict[AssignmentPart, PromptSpec] = {
    AssignmentPart.A: PromptSpec(
        "part_a_instrument_extraction.md",
        ("CENTRAL_BANK_EXCERPT",),
    ),
    AssignmentPart.B: PromptSpec(
        "part_b_operations_drafting.md",
        ("MODE", "RAW_NOTES_OR_EMPTY", "CB_TEXT_OR_EMPTY"),
    ),
    AssignmentPart.C: PromptSpec(
        "part_c_recommendation_quality.md",
        ("REPORT_ID", "RECOMMENDATIONS", "REPORT_CONTENT"),
    ),
    AssignmentPart.D: PromptSpec(
        "part_d_policy_signal.md",
        (
            "SEQUENCE_INTEGER",
            "STABLE_SPEECH_ID",
            "DATE_OR_EMPTY",
            "SPEAKER_OR_EMPTY",
            "BIS_SPEECH_TEXT",
        ),
    ),
}

_PLACEHOLDER = re.compile(r"\{\{\s*([A-Z][A-Z0-9_]*)\s*\}\}")


class PromptError(RuntimeError):
    """Base exception for prompt loading and rendering failures."""


class PromptNotFoundError(PromptError):
    pass


class PromptRenderError(PromptError):
    pass


def coerce_part(part: AssignmentPart | str) -> AssignmentPart:
    if isinstance(part, AssignmentPart):
        return part
    try:
        return AssignmentPart(part.strip().upper())
    except (AttributeError, ValueError) as exc:
        raise ValueError(f"unknown assignment part: {part!r}") from exc


def load_prompt(
    part: AssignmentPart | str,
    *,
    prompt_dir: Path | str = PROJECT_ROOT / "prompts",
) -> str:
    """Read a task template as UTF-8 without mutating it."""

    normalized = coerce_part(part)
    path = Path(prompt_dir) / PROMPT_SPECS[normalized].filename
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise PromptNotFoundError(f"prompt template not found: {path}") from exc


def render_template(
    template: str,
    values: Mapping[str, object],
    *,
    required: tuple[str, ...] | None = None,
) -> str:
    """Render only explicit ``{{UPPER_CASE}}`` placeholders.

    ``str.format`` is deliberately avoided so JSON examples and Markdown braces
    inside templates remain untouched.
    """

    found = set(_PLACEHOLDER.findall(template))
    expected = set(required) if required is not None else found
    supplied = set(values)

    template_missing = expected - found
    missing_values = expected - supplied
    unexpected_values = supplied - expected
    unexpected_placeholders = found - expected
    problems: list[str] = []
    if template_missing:
        problems.append(f"template is missing placeholders: {sorted(template_missing)}")
    if missing_values:
        problems.append(f"values are missing: {sorted(missing_values)}")
    if unexpected_values:
        problems.append(f"unexpected values: {sorted(unexpected_values)}")
    if unexpected_placeholders:
        problems.append(f"unexpected placeholders: {sorted(unexpected_placeholders)}")
    if problems:
        raise PromptRenderError("; ".join(problems))

    def replacement(match: re.Match[str]) -> str:
        return str(values[match.group(1)])

    return _PLACEHOLDER.sub(replacement, template)


def render_part_prompt(
    part: AssignmentPart | str,
    *,
    prompt_dir: Path | str = PROJECT_ROOT / "prompts",
    values: Mapping[str, object],
) -> str:
    normalized = coerce_part(part)
    spec = PROMPT_SPECS[normalized]
    return render_template(
        load_prompt(normalized, prompt_dir=prompt_dir),
        values,
        required=spec.placeholders,
    )
