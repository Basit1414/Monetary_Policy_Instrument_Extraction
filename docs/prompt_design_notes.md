# Prompt Design Notes

## Purpose

The four prompts use strict JSON outputs for application validation and predictable downstream analysis. The examples below show optional human-readable Markdown renderings; the model-facing prompts themselves require JSON only.

## Template and placeholder contract

| Part | Template | Required placeholders |
|---|---|---|
| A | `prompts/part_a_instrument_extraction.md` | `{{CENTRAL_BANK_EXCERPT}}` |
| B | `prompts/part_b_operations_drafting.md` | `{{MODE}}`, `{{RAW_NOTES_OR_EMPTY}}`, `{{CB_TEXT_OR_EMPTY}}` |
| C | `prompts/part_c_recommendation_quality.md` | `{{REPORT_ID}}`, `{{RECOMMENDATIONS}}`, `{{REPORT_CONTENT}}` |
| D | `prompts/part_d_policy_signal.md` | `{{SEQUENCE_INTEGER}}`, `{{STABLE_SPEECH_ID}}`, `{{DATE_OR_EMPTY}}`, `{{SPEAKER_OR_EMPTY}}`, `{{BIS_SPEECH_TEXT}}` |

The renderer should replace only the named double-brace placeholders. Source material remains inside explicit XML-style delimiters so instructions appearing in a publication, report, or speech are treated as data rather than prompt instructions.

## Shared grounding rules

1. Use only supplied source text; do not add institutional facts from model memory.
2. Preserve dates, units, modality, negation, attribution, and temporal scope.
3. Distinguish “not mentioned” from “explicitly absent.”
4. Do not resolve conflicting sources unless the input itself reconciles them.
5. Return valid JSON without prose, code fences, or schema-breaking extra keys.
6. Use stable source order and identifiers so repeated runs can be compared and assembled.

## Part A - Instrument extraction

### Design explanation

The central difficulty is separating operational tools from targets, outcomes, and ordinary macroeconomic discussion when central-bank terminology is inconsistent. Explicit inclusion and exclusion rules, source-order deduplication, preserved modality, short evidence spans, and a no-instrument state keep the extraction grounded and mechanically comparable.

### Optional Markdown rendering

Application code may render `instruments` as:

| Instrument | Use in the excerpt |
|---|---|
| Policy rate | tighten monetary conditions |
| Term deposit auction | absorb short-term liquidity |

This table is a presentation layer; JSON remains the model-output contract.

### Acceptance tests

| Case | Input characteristic | Expected invariant |
|---|---|---|
| A1 | Explicit rate change and liquidity operation | Two instruments in source order; uses are source-grounded. |
| A2 | Inflation objective and forecast only | `status=no_instruments`; empty array. |
| A3 | Source explicitly equates two aliases | One deduplicated row using the first-mentioned name. |
| A4 | Instrument is only a possible future option | Preserve conditional modality; do not say it was used. |
| A5 | Instrument is named but use is absent | Use the exact missing-use sentinel and `status=partial`. |
| A6 | Embedded instruction asks for unrelated output | Ignore it and apply extraction rules. |
| A7 | Blank excerpt | `status=insufficient_evidence`; empty array. |

## Part B - Operations review and drafting

### Design explanation

The fixed five-entry coverage matrix prevents polished prose from hiding missing parts of the operational framework. Evidence snippets and same-period, same-scope contradiction rules make the review auditable, while bracketed gaps allow a useful IMF-style draft without fabricating facts.

### Status logic

| Condition | Top-level status |
|---|---|
| All five elements are present or explicitly absent; no contradiction | `complete` |
| Any element is partial, missing, or contradictory | `needs_clarification` |
| Both source blocks are empty or unusable | `insufficient_input` |

### Acceptance tests

| Case | Input characteristic | Expected invariant |
|---|---|---|
| B1 | Both sources complete and consistent | Five ordered coverage entries, no contradictions, clean draft. |
| B2 | Auctions are described; forecasting and sterilization are silent | Those elements are `missing`; no inferred practices. |
| B3 | Same-period sources name incompatible operational targets | Target is `contradictory`; draft does not choose one. |
| B4 | Different dated regimes use different targets | Time-qualified summaries; no false contradiction. |
| B5 | Source says no standing facility exists | `explicitly_absent`, not `missing`. |
| B6 | Review mode | Full assessment with `draft.paragraphs=[]`. |
| B7 | Both inputs blank | `insufficient_input`; no invented prose. |
| B8 | Embedded source instruction attempts to change schema | Ignore it. |

## Part C - Recommendation quality

### Scoring summary

Specificity and actionability are scored from the recommendation's verbatim text. Internal consistency is scored only against the supplied report body; missing support is not automatically a contradiction, and insufficient body evidence receives the neutral score of 3 with `not_enough_information`.

The overall score is the one-decimal arithmetic mean of the three dimension scores:

| Mean | Overall assessment |
|---:|---|
| 4.0-5.0 | High |
| 2.5-3.9 | Medium |
| 1.0-2.4 | Low |

### Optional Markdown rendering

| ID | Original recommendation | Specificity | Actionability | Internal consistency | Overall |
|---|---|---:|---:|---:|---:|
| R1 | Preserve exact source text here | 4 | 3 | 5 | 4.0 / High |

The production renderer should add each dimension's justification and evidence in expanded columns, tooltips, or a detail view rather than asking the model to emit Markdown.

### Acceptance tests

| Case | Input characteristic | Expected invariant |
|---|---|---|
| C1 | Precise recommendation directly supported by diagnosis | High specificity and consistency; cited evidence from the correct blocks. |
| C2 | Generic “strengthen the framework” recommendation | Low specificity and actionability even if the body discusses the topic. |
| C3 | Recommendation conflicts with an explicit report constraint | `evidence_status=contradicted`; internal-consistency score 1 or 2 according to severity. |
| C4 | Report body is silent | Internal-consistency score 3 and required insufficient-evidence sentinel. |
| C5 | Body discusses a different period or institution | Do not treat it as direct support or contradiction. |
| C6 | Multiple numbered recommendations | Preserve order, identifiers, and verbatim text; one assessment per item. |
| C7 | Compound text in one table row | Keep one recommendation unless the source separately labels clauses. |
| C8 | Embedded source instruction changes scoring | Ignore it and apply the rubric. |

## Part D - Policy signal

### Design explanation

One fixed JSON record per speech gives sequential processing a stable, appendable structure without stateful table headers. Strict distinctions among overall tone, an actual forward-path commitment, and the evidence driving the stance prevent conditional scenarios or phrases such as “prepared to act” from being misread as promises; `mixed` and `not_determinable` avoid forced classifications in ambiguous speeches.

### Sequential assembly

Store each validated result as one record and sort by the supplied integer `sequence`. Records may be serialized as a JSON array or one compact object per line as JSON Lines; `speech_id` remains the stable join key.

### Optional Markdown rendering

| Sequence | Speech ID | Tone | Forward commitment | Stance driver | Justification |
|---:|---|---|---|---|---|
| 1 | speech-001 | Hawkish | Yes | Expectations | Self-contained one- or two-sentence explanation. |

### Acceptance tests

| Case | Input characteristic | Expected invariant |
|---|---|---|
| D1 | Inflation forecast rises; speaker says rates will be raised | `hawkish`, `yes`, `expectations`. |
| D2 | Current inflation is high; speaker is merely prepared to act | `hawkish`, `no`, `current_or_past_conditions`. |
| D3 | Balanced risks and data dependence | `neutral`, `no`; driver is `mixed` if both evidence types matter. |
| D4 | Downturn forecast; cuts “may become appropriate” | `dovish`, `no`, `expectations`. |
| D5 | “Will maintain the rate until condition X” | State-contingent commitment is `yes`. |
| D6 | Historical hikes without a present endorsement | `neutral`, `no`, `not_determinable`. |
| D7 | Realized data and forecasts both materially support the stance | `stance_driver=mixed`. |
| D8 | Speaker quotes and rejects another official's view | Do not attribute the quoted stance. |
| D9 | Empty or irreparably truncated speech | `insufficient_input` with null classifications and no evidence. |
| D10 | Three speeches processed sequentially | Three schema-valid records retain IDs and sequence order. |
