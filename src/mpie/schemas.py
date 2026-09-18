"""Strict response contracts for assignment parts A through D."""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class StrictSchema(BaseModel):
    """Base class that rejects unplanned output fields."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class InstrumentExtractionStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    NO_INSTRUMENTS = "no_instruments"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class EvidenceItem(StrictSchema):
    """Auditable support copied from or precisely located in the input."""

    quote: NonEmptyText
    source: NonEmptyText | None
    location: NonEmptyText | None


# Part A --------------------------------------------------------------------


class InstrumentUse(StrictSchema):
    instrument: NonEmptyText
    use: NonEmptyText
    evidence: list[EvidenceItem] = Field(min_length=1)


class InstrumentExtractionResult(StrictSchema):
    status: InstrumentExtractionStatus
    instruments: list[InstrumentUse]

    @model_validator(mode="after")
    def require_instruments_consistent_with_status(self) -> InstrumentExtractionResult:
        empty_statuses = {
            InstrumentExtractionStatus.NO_INSTRUMENTS,
            InstrumentExtractionStatus.INSUFFICIENT_EVIDENCE,
        }
        if self.status in empty_statuses and self.instruments:
            raise ValueError(f"{self.status.value} must use an empty instruments array")
        if self.status not in empty_statuses and not self.instruments:
            raise ValueError(f"{self.status.value} must contain at least one instrument")
        return self


# Part B --------------------------------------------------------------------


class OperationsMode(str, Enum):
    REVIEW = "review"
    DRAFT = "draft"
    REVIEW_AND_DRAFT = "review_and_draft"


class OperationsStatus(str, Enum):
    COMPLETE = "complete"
    NEEDS_CLARIFICATION = "needs_clarification"
    INSUFFICIENT_INPUT = "insufficient_input"


class SourceAvailability(StrictSchema):
    raw_notes: bool
    central_bank_text: bool


class CoverageElement(str, Enum):
    OPERATIONAL_TARGET = "operational_target"
    MAIN_INSTRUMENTS = "main_instruments"
    LIQUIDITY_FORECASTING = "liquidity_forecasting"
    STANDING_FACILITIES = "standing_facilities"
    STERILIZATION = "sterilization"


class CoverageStatus(str, Enum):
    PRESENT = "present"
    PARTIAL = "partial"
    EXPLICITLY_ABSENT = "explicitly_absent"
    MISSING = "missing"
    CONTRADICTORY = "contradictory"


class CoverageItem(StrictSchema):
    element: CoverageElement
    status: CoverageStatus
    summary: NonEmptyText | None
    evidence: list[EvidenceItem]
    needed: NonEmptyText | None


class ContradictionClaim(StrictSchema):
    source: NonEmptyText
    excerpt: NonEmptyText


class Contradiction(StrictSchema):
    topic: NonEmptyText
    claim_a: ContradictionClaim
    claim_b: ContradictionClaim
    same_period: bool
    resolution_needed: NonEmptyText
    evidence: list[EvidenceItem]


class OperationsDraft(StrictSchema):
    heading: Literal["Monetary Operations"]
    paragraphs: list[NonEmptyText]
    contains_placeholders: bool


class OperationsDraftingResult(StrictSchema):
    status: OperationsStatus
    mode: OperationsMode
    source_availability: SourceAvailability
    coverage: list[CoverageItem]
    contradictions: list[Contradiction]
    draft: OperationsDraft
    follow_up_questions: list[NonEmptyText]

    @model_validator(mode="after")
    def require_fixed_coverage_and_mode_output(self) -> OperationsDraftingResult:
        expected = list(CoverageElement)
        actual = [item.element for item in self.coverage]
        if actual != expected:
            raise ValueError(
                "coverage must contain each fixed element once in the documented order"
            )
        if self.mode is OperationsMode.REVIEW and self.draft.paragraphs:
            raise ValueError("review mode must use an empty draft paragraphs array")
        should_have_draft = (
            self.mode is not OperationsMode.REVIEW
            and self.status is not OperationsStatus.INSUFFICIENT_INPUT
        )
        if should_have_draft and not self.draft.paragraphs:
            raise ValueError("draft modes must produce paragraphs when input is usable")
        if self.status is OperationsStatus.INSUFFICIENT_INPUT and (
            self.source_availability.raw_notes or self.source_availability.central_bank_text
        ):
            raise ValueError("insufficient_input requires both source inputs to be unavailable")
        return self


# Part C --------------------------------------------------------------------


class RecommendationScore(StrictSchema):
    score: int = Field(ge=1, le=5)
    justification: NonEmptyText
    evidence: list[EvidenceItem] = Field(min_length=1)


class EvidenceStatus(str, Enum):
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    CONTRADICTED = "contradicted"
    NOT_ENOUGH_INFORMATION = "not_enough_information"


class OverallAssessment(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class RecommendationAssessment(StrictSchema):
    recommendation_id: NonEmptyText
    original_text: NonEmptyText
    specificity: RecommendationScore
    actionability: RecommendationScore
    internal_consistency: RecommendationScore
    overall_score: float = Field(ge=1, le=5, multiple_of=0.1)
    overall_assessment: OverallAssessment
    evidence_status: EvidenceStatus

    @model_validator(mode="after")
    def require_mean_overall_score(self) -> RecommendationAssessment:
        expected = round(
            (self.specificity.score + self.actionability.score + self.internal_consistency.score)
            / 3,
            1,
        )
        if self.overall_score != expected:
            raise ValueError(f"overall_score must be the one-decimal mean ({expected})")
        expected_label = (
            OverallAssessment.HIGH
            if expected >= 4.0
            else OverallAssessment.MEDIUM
            if expected >= 2.5
            else OverallAssessment.LOW
        )
        if self.overall_assessment is not expected_label:
            raise ValueError(f"overall_assessment must be {expected_label.value}")
        return self


class RecommendationQualityResult(StrictSchema):
    report_id: NonEmptyText
    assessments: list[RecommendationAssessment]


# Part D --------------------------------------------------------------------


class PolicyTone(str, Enum):
    DOVISH = "dovish"
    NEUTRAL = "neutral"
    HAWKISH = "hawkish"


class PolicySignalStatus(str, Enum):
    OK = "ok"
    INSUFFICIENT_INPUT = "insufficient_input"


class ForwardPathCommitment(str, Enum):
    YES = "yes"
    NO = "no"


class StanceDriver(str, Enum):
    EXPECTATIONS = "expectations"
    CURRENT_OR_PAST_CONDITIONS = "current_or_past_conditions"
    MIXED = "mixed"
    NOT_DETERMINABLE = "not_determinable"


class PolicySignalResult(StrictSchema):
    """One flat, serializable record suitable for a JSONL row."""

    status: PolicySignalStatus
    sequence: int = Field(ge=0)
    speech_id: NonEmptyText
    speech_date: date | None
    speaker: NonEmptyText | None
    tone: PolicyTone | None
    forward_path_commitment: ForwardPathCommitment | None
    stance_driver: StanceDriver | None
    justification: NonEmptyText
    evidence: list[EvidenceItem]

    @model_validator(mode="after")
    def constrain_nullable_commitment(self) -> PolicySignalResult:
        classifications = (self.tone, self.forward_path_commitment, self.stance_driver)
        insufficient = self.status is PolicySignalStatus.INSUFFICIENT_INPUT
        if insufficient and any(value is not None for value in classifications):
            raise ValueError("classification fields must be null for insufficient input")
        if insufficient and self.evidence:
            raise ValueError("evidence must be empty for insufficient input")
        if not insufficient and any(value is None for value in classifications):
            raise ValueError("classification fields may be null only for insufficient input")
        if not insufficient and not 1 <= len(self.evidence) <= 2:
            raise ValueError("ok results require one or two evidence items")
        return self
