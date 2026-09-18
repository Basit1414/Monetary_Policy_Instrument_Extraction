# Monetary Policy Instrument Extraction — Assignment Deliverables

This repository provides four version-controlled prompts, strict output schemas, a local chatbot, and a reproducible three-report recommendation assessment. Model-facing prompts return JSON so outputs can be validated and assembled reliably; the application renders them as readable tables and prose.

## A. Extracting monetary policy instruments

The complete prompt is [`prompts/part_a_instrument_extraction.md`](../prompts/part_a_instrument_extraction.md). Insert the central-bank paragraph at `{{CENTRAL_BANK_EXCERPT}}`; the validated output contains one row per instrument with its explicitly stated use and a short evidence span.

The central difficulty is separating operational tools from targets, outcomes, and ordinary macroeconomic discussion when central-bank terminology is inconsistent. Explicit inclusion and exclusion rules, source-order deduplication, preserved modality, short evidence spans, and a no-instrument state keep the extraction grounded and mechanically comparable.

## B. Drafting and reviewing monetary policy operations sections

The complete prompt is [`prompts/part_b_operations_drafting.md`](../prompts/part_b_operations_drafting.md). It includes these required placeholders:

- `{{MODE}}`: `review`, `draft`, or `review_and_draft`
- `{{RAW_NOTES_OR_EMPTY}}`: raw notes, or an empty string
- `{{CB_TEXT_OR_EMPTY}}`: central-bank source text, or an empty string

The response checks the operational target, main instruments, liquidity forecasting, standing facilities, and sterilization in a fixed coverage matrix. It separately records same-period contradictions and produces concise IMF-style prose with explicit information or clarification placeholders instead of inventing missing facts.

## C. Recommendation quality assessment

The scoring prompt is [`prompts/part_c_recommendation_quality.md`](../prompts/part_c_recommendation_quality.md), with `{{REPORT_ID}}`, `{{RECOMMENDATIONS}}`, and `{{REPORT_CONTENT}}` placeholders. It assigns separate 1–5 scores and short evidence-backed justifications for specificity, actionability, and internal consistency, preserves each recommendation verbatim, and computes a one-decimal overall mean.

Three public IMF technical-assistance reports were downloaded and checked page by page. Eight recommendations were extracted from each, for 24 total assessments. The main finding is that recommendations are highly aligned with their reports (mean internal consistency **4.92/5**) but only moderately self-contained (specificity **2.92/5** and actionability **2.83/5**); see the full [interpretation and chart](../reports/recommendation_quality_report.md), [executed notebook](../notebooks/01_recommendation_quality_assessment.ipynb), and [row-level CSV](../data/results/recommendation_quality_assessments.csv).

## D. Structured policy signal extraction

The complete prompt is [`prompts/part_d_policy_signal.md`](../prompts/part_d_policy_signal.md). It accepts `{{SEQUENCE_INTEGER}}`, `{{STABLE_SPEECH_ID}}`, `{{DATE_OR_EMPTY}}`, `{{SPEAKER_OR_EMPTY}}`, and `{{BIS_SPEECH_TEXT}}` and returns one JSONL-compatible record containing tone, forward-path commitment, stance driver, justification, and evidence.

One fixed JSON record per speech gives sequential processing a stable, appendable structure without stateful table headers. Strict distinctions among overall tone, an actual forward-path commitment, and the evidence driving the stance prevent conditional scenarios or phrases such as “prepared to act” from being misread as promises; `mixed` and `not_determinable` avoid forced driver classifications in ambiguous speeches.

## Reproducibility note

The downloaded PDFs and full text extracts remain local and are reproducible from the authoritative IMF URLs in the source manifest. The GitHub repository retains source metadata, hashes, the reviewed 24-row recommendation sample, prompts, validated results, and scripts while excluding API keys and temporary/generated corpus files.
