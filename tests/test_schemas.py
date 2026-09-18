from __future__ import annotations

import pytest
from pydantic import ValidationError

from mpie.schemas import (
    CoverageElement,
    InstrumentExtractionResult,
    OperationsDraftingResult,
    PolicySignalResult,
    RecommendationQualityResult,
)


def evidence(source: str = "source") -> dict[str, object]:
    return {"quote": "Exact supporting text", "source": source, "location": None}


def test_part_a_represents_usable_text_with_no_instruments() -> None:
    result = InstrumentExtractionResult.model_validate(
        {"status": "no_instruments", "instruments": []}
    )
    assert result.instruments == []


def test_part_a_rejects_status_content_mismatch_and_extra_fields() -> None:
    with pytest.raises(ValidationError):
        InstrumentExtractionResult.model_validate({"status": "complete", "instruments": []})

    with pytest.raises(ValidationError):
        InstrumentExtractionResult.model_validate(
            {"status": "no_instruments", "instruments": [], "unplanned": True}
        )


def _coverage() -> list[dict[str, object]]:
    return [
        {
            "element": element.value,
            "status": "missing",
            "summary": None,
            "evidence": [],
            "needed": f"Provide {element.value}",
        }
        for element in CoverageElement
    ]


def _part_b_payload() -> dict[str, object]:
    return {
        "status": "needs_clarification",
        "mode": "review",
        "source_availability": {"raw_notes": True, "central_bank_text": False},
        "coverage": _coverage(),
        "contradictions": [],
        "draft": {
            "heading": "Monetary Operations",
            "paragraphs": [],
            "contains_placeholders": False,
        },
        "follow_up_questions": ["What is the operating target?"],
    }


def test_part_b_requires_all_five_coverage_elements_in_order() -> None:
    valid = OperationsDraftingResult.model_validate(_part_b_payload())
    assert [item.element for item in valid.coverage] == list(CoverageElement)

    invalid = _part_b_payload()
    invalid["coverage"] = list(reversed(_coverage()))
    with pytest.raises(ValidationError, match="documented order"):
        OperationsDraftingResult.model_validate(invalid)


def _score(score: int, source: str) -> dict[str, object]:
    return {
        "score": score,
        "justification": "Grounded scoring explanation",
        "evidence": [evidence(source)],
    }


def _assessment(overall_score: float = 4.0) -> dict[str, object]:
    return {
        "recommendation_id": "R1",
        "original_text": "Adopt the documented operating procedure.",
        "specificity": _score(5, "recommendations"),
        "actionability": _score(4, "recommendations"),
        "internal_consistency": _score(3, "report_body"),
        "overall_score": overall_score,
        "overall_assessment": "High",
        "evidence_status": "supported",
    }


def test_part_c_enforces_dimension_ranges_and_deterministic_mean() -> None:
    result = RecommendationQualityResult.model_validate(
        {"report_id": "report-1", "assessments": [_assessment()]}
    )
    assert result.assessments[0].overall_score == 4.0

    with pytest.raises(ValidationError, match="one-decimal mean"):
        RecommendationQualityResult.model_validate(
            {"report_id": "report-1", "assessments": [_assessment(4.1)]}
        )


def test_part_c_can_represent_no_identifiable_recommendation() -> None:
    result = RecommendationQualityResult.model_validate(
        {"report_id": "report-1", "assessments": []}
    )
    assert result.assessments == []


def test_part_d_requires_nullable_classifications_only_for_insufficient_input() -> None:
    valid = PolicySignalResult.model_validate(
        {
            "status": "ok",
            "sequence": 0,
            "speech_id": "speech-1",
            "speech_date": "2026-01-02",
            "speaker": "A. Speaker",
            "tone": "neutral",
            "forward_path_commitment": "no",
            "stance_driver": "expectations",
            "justification": "The speech is balanced and discusses the outlook.",
            "evidence": [evidence("speech_text")],
        }
    )
    assert valid.sequence == 0

    insufficient = PolicySignalResult.model_validate(
        {
            "status": "insufficient_input",
            "sequence": 1,
            "speech_id": "speech-2",
            "speech_date": None,
            "speaker": None,
            "tone": None,
            "forward_path_commitment": None,
            "stance_driver": None,
            "justification": "No usable speech text was supplied.",
            "evidence": [],
        }
    )
    assert insufficient.tone is None

    bad = insufficient.model_dump(mode="json")
    bad["tone"] = "neutral"
    with pytest.raises(ValidationError, match="must be null"):
        PolicySignalResult.model_validate(bad)
