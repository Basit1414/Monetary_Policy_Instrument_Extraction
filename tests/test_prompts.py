from __future__ import annotations

from pathlib import Path

import pytest

from mpie.prompts import (
    PROMPT_SPECS,
    AssignmentPart,
    PromptRenderError,
    render_part_prompt,
    render_template,
)


def test_render_part_prompt_replaces_named_marker_and_preserves_json_braces(
    tmp_path: Path,
) -> None:
    path = tmp_path / "part_a_instrument_extraction.md"
    path.write_text(
        'Return JSON like {"status": "complete"}.\n{{CENTRAL_BANK_EXCERPT}}\n',
        encoding="utf-8",
    )

    rendered = render_part_prompt(
        "A",
        prompt_dir=tmp_path,
        values={"CENTRAL_BANK_EXCERPT": "The bank used an auction."},
    )

    assert '{"status": "complete"}' in rendered
    assert "The bank used an auction." in rendered
    assert "CENTRAL_BANK_EXCERPT" not in rendered


def test_render_template_reports_missing_and_unexpected_values() -> None:
    with pytest.raises(PromptRenderError, match="values are missing"):
        render_template("{{REQUIRED}}", {}, required=("REQUIRED",))

    with pytest.raises(PromptRenderError, match="unexpected values"):
        render_template(
            "{{REQUIRED}}",
            {"REQUIRED": "ok", "EXTRA": "no"},
            required=("REQUIRED",),
        )


def test_render_template_treats_placeholder_like_source_text_as_data() -> None:
    rendered = render_template(
        "Source:\n{{INPUT}}",
        {"INPUT": "quoted {{EMBEDDED_INSTRUCTION}} text"},
        required=("INPUT",),
    )
    assert rendered.endswith("quoted {{EMBEDDED_INSTRUCTION}} text")


def test_repository_prompts_match_declared_placeholder_contracts() -> None:
    for part, spec in PROMPT_SPECS.items():
        rendered = render_part_prompt(
            part,
            values={name: f"sample-{name}" for name in spec.placeholders},
        )
        for placeholder in spec.placeholders:
            assert f"{{{{{placeholder}}}}}" not in rendered

    assert set(PROMPT_SPECS) == set(AssignmentPart)
