"""Streamlit entry point for assignment parts A through D."""

from __future__ import annotations

from typing import Any

import streamlit as st
from openai import OpenAIError
from pydantic import ValidationError

from mpie.config import RuntimeConfig
from mpie.llm import OpenAIResponsesLLM, StructuredResponseError
from mpie.prompts import AssignmentPart, PromptError
from mpie.services import AssignmentService, result_to_csv, result_to_json, result_to_jsonl

PART_LABELS = {
    "A - Instrument extraction": AssignmentPart.A,
    "B - Operations review and drafting": AssignmentPart.B,
    "C - Recommendation quality": AssignmentPart.C,
    "D - Policy signal": AssignmentPart.D,
}


def _part_a_inputs() -> dict[str, object]:
    excerpt = st.text_area(
        "Central-bank excerpt",
        height=320,
        placeholder="Paste the source excerpt to inspect.",
    )
    return {"CENTRAL_BANK_EXCERPT": excerpt}


def _part_b_inputs() -> dict[str, object]:
    mode = st.selectbox(
        "Mode",
        options=("review", "draft", "review_and_draft"),
        index=2,
    )
    raw_notes = st.text_area("Raw notes", height=220)
    central_bank_text = st.text_area("Central-bank text", height=220)
    return {
        "MODE": mode,
        "RAW_NOTES_OR_EMPTY": raw_notes,
        "CB_TEXT_OR_EMPTY": central_bank_text,
    }


def _part_c_inputs() -> dict[str, object]:
    report_id = st.text_input("Report ID", placeholder="Stable report identifier")
    recommendations = st.text_area("Recommendations", height=220)
    report_content = st.text_area("Report body", height=300)
    return {
        "REPORT_ID": report_id,
        "RECOMMENDATIONS": recommendations,
        "REPORT_CONTENT": report_content,
    }


def _part_d_inputs() -> dict[str, object]:
    sequence = st.number_input("Sequence", min_value=0, step=1, value=0)
    speech_id = st.text_input("Speech ID", placeholder="Stable speech identifier")
    speech_date = st.text_input("Speech date (optional)", placeholder="YYYY-MM-DD")
    speaker = st.text_input("Speaker (optional)")
    speech_text = st.text_area("BIS speech text", height=360)
    return {
        "SEQUENCE_INTEGER": int(sequence),
        "STABLE_SPEECH_ID": speech_id,
        "DATE_OR_EMPTY": speech_date,
        "SPEAKER_OR_EMPTY": speaker,
        "BIS_SPEECH_TEXT": speech_text,
    }


def _validate_inputs(part: AssignmentPart, values: dict[str, object]) -> str | None:
    required: dict[AssignmentPart, tuple[str, ...]] = {
        AssignmentPart.A: ("CENTRAL_BANK_EXCERPT",),
        AssignmentPart.B: (),
        AssignmentPart.C: ("REPORT_ID", "RECOMMENDATIONS"),
        AssignmentPart.D: ("STABLE_SPEECH_ID", "BIS_SPEECH_TEXT"),
    }
    missing = [name for name in required[part] if not str(values.get(name, "")).strip()]
    if missing:
        labels = ", ".join(name.lower().replace("_", " ") for name in missing)
        return f"Complete the required input(s): {labels}."
    return None


def _render_downloads(part: AssignmentPart, result: Any) -> None:
    json_text = result_to_json(result)
    csv_text = result_to_csv(result)
    prefix = f"part_{part.value.lower()}_result"

    left, right = st.columns(2)
    left.download_button(
        "Download JSON",
        data=json_text,
        file_name=f"{prefix}.json",
        mime="application/json",
        use_container_width=True,
    )
    right.download_button(
        "Download CSV",
        data=csv_text,
        file_name=f"{prefix}.csv",
        mime="text/csv",
        use_container_width=True,
    )
    if part is AssignmentPart.D:
        st.download_button(
            "Download JSONL",
            data=result_to_jsonl(result),
            file_name=f"{prefix}.jsonl",
            mime="application/x-ndjson",
            use_container_width=True,
        )


def _humanize(value: object) -> str:
    if value is None or value == "":
        return "—"
    return str(value).replace("_", " ").title()


def _format_evidence(items: list[dict[str, Any]]) -> str:
    if not items:
        return "—"

    formatted: list[str] = []
    for item in items:
        quote = str(item.get("quote") or "")
        provenance = [str(value) for value in (item.get("source"), item.get("location")) if value]
        entry = f"“{quote}”"
        if provenance:
            entry += f" — {' · '.join(provenance)}"
        formatted.append(entry)
    return "\n".join(formatted)


def _render_evidence_table(items: list[dict[str, Any]]) -> None:
    if not items:
        st.caption("No source evidence returned.")
        return

    rows = [
        {
            "Quote": item.get("quote") or "",
            "Source": item.get("source") or "—",
            "Location": item.get("location") or "—",
        }
        for item in items
    ]
    st.dataframe(rows, hide_index=True, use_container_width=True)


def _render_part_a_result(data: dict[str, Any]) -> None:
    instruments = data.get("instruments") or []
    status_col, count_col = st.columns(2)
    status_col.metric("Status", _humanize(data.get("status")))
    count_col.metric("Instruments found", len(instruments))

    st.markdown("### Instrument findings")
    if not instruments:
        st.info("No qualifying monetary-policy instruments were returned.")
        return

    rows = [
        {
            "Instrument": item.get("instrument") or "",
            "Use in the excerpt": item.get("use") or "",
            "Evidence": _format_evidence(item.get("evidence") or []),
        }
        for item in instruments
    ]
    st.dataframe(rows, hide_index=True, use_container_width=True)


def _render_part_b_result(data: dict[str, Any]) -> None:
    availability = data.get("source_availability") or {}
    available_sources = sum(bool(value) for value in availability.values())
    status_col, mode_col, source_col = st.columns(3)
    status_col.metric("Status", _humanize(data.get("status")))
    mode_col.metric("Mode", _humanize(data.get("mode")))
    source_col.metric("Sources supplied", f"{available_sources}/2")

    st.markdown("### Framework coverage")
    coverage = data.get("coverage") or []
    coverage_rows = [
        {
            "Element": _humanize(item.get("element")),
            "Status": _humanize(item.get("status")),
            "Summary": item.get("summary") or "—",
            "Information needed": item.get("needed") or "—",
            "Evidence": _format_evidence(item.get("evidence") or []),
        }
        for item in coverage
    ]
    if coverage_rows:
        st.dataframe(coverage_rows, hide_index=True, use_container_width=True)
    else:
        st.info("No coverage assessment was returned.")

    contradictions = data.get("contradictions") or []
    if contradictions:
        st.markdown("### Contradictions")
        st.warning(f"{len(contradictions)} unresolved contradiction(s) require review.")
        for index, contradiction in enumerate(contradictions, start=1):
            topic = contradiction.get("topic") or f"Contradiction {index}"
            with st.expander(str(topic), expanded=True):
                claim_a = contradiction.get("claim_a") or {}
                claim_b = contradiction.get("claim_b") or {}
                st.dataframe(
                    [
                        {
                            "Claim": "A",
                            "Source": claim_a.get("source") or "—",
                            "Excerpt": claim_a.get("excerpt") or "—",
                        },
                        {
                            "Claim": "B",
                            "Source": claim_b.get("source") or "—",
                            "Excerpt": claim_b.get("excerpt") or "—",
                        },
                    ],
                    hide_index=True,
                    use_container_width=True,
                )
                st.write(
                    "**Same period:**",
                    "Yes" if contradiction.get("same_period") else "No",
                )
                st.write(
                    "**Resolution needed:**",
                    contradiction.get("resolution_needed") or "—",
                )

    draft = data.get("draft") or {}
    paragraphs = draft.get("paragraphs") or []
    st.markdown("### Draft narrative")
    if paragraphs:
        st.markdown(f"#### {draft.get('heading') or 'Monetary Operations'}")
        for paragraph in paragraphs:
            st.write(paragraph)
        if draft.get("contains_placeholders"):
            st.warning("The draft contains bracketed placeholders that require source input.")
    else:
        st.caption("No narrative draft was produced for this result.")

    questions = data.get("follow_up_questions") or []
    if questions:
        st.markdown("### Follow-up questions")
        for index, question in enumerate(questions, start=1):
            st.write(f"{index}. {question}")


def _render_part_c_result(data: dict[str, Any]) -> None:
    assessments = data.get("assessments") or []
    report_col, count_col = st.columns(2)
    report_col.metric("Report ID", str(data.get("report_id") or "—"))
    count_col.metric("Recommendations assessed", len(assessments))

    st.markdown("### Recommendation scorecard")
    if not assessments:
        st.info("No recommendations were identified for assessment.")
        return

    rows = []
    for item in assessments:
        rows.append(
            {
                "ID": item.get("recommendation_id") or "",
                "Recommendation": item.get("original_text") or "",
                "Specificity": (item.get("specificity") or {}).get("score"),
                "Actionability": (item.get("actionability") or {}).get("score"),
                "Internal consistency": (item.get("internal_consistency") or {}).get("score"),
                "Overall": item.get("overall_score"),
                "Assessment": item.get("overall_assessment") or "",
                "Evidence status": _humanize(item.get("evidence_status")),
            }
        )
    st.dataframe(rows, hide_index=True, use_container_width=True)

    st.markdown("### Assessment details")
    dimensions = (
        ("Specificity", "specificity"),
        ("Actionability", "actionability"),
        ("Internal consistency", "internal_consistency"),
    )
    for item in assessments:
        recommendation_id = item.get("recommendation_id") or "Recommendation"
        assessment = item.get("overall_assessment") or "Unrated"
        with st.expander(f"{recommendation_id} · {assessment}"):
            st.write(item.get("original_text") or "")
            score_columns = st.columns(3)
            for column, (label, key) in zip(score_columns, dimensions, strict=True):
                detail = item.get(key) or {}
                column.metric(label, detail.get("score") or "—")
            for label, key in dimensions:
                detail = item.get(key) or {}
                st.markdown(f"**{label}**")
                st.write(detail.get("justification") or "No justification returned.")
                st.caption(_format_evidence(detail.get("evidence") or []))


def _render_part_d_result(data: dict[str, Any]) -> None:
    status_col, tone_col, commitment_col, driver_col = st.columns(4)
    status_col.metric("Status", _humanize(data.get("status")))
    tone_col.metric("Tone", _humanize(data.get("tone")))
    commitment_col.metric(
        "Forward commitment",
        _humanize(data.get("forward_path_commitment")),
    )
    driver_col.metric("Stance driver", _humanize(data.get("stance_driver")))

    st.caption(
        f"Sequence {data.get('sequence', '—')} · "
        f"Speech ID: {data.get('speech_id') or '—'} · "
        f"Date: {data.get('speech_date') or '—'} · "
        f"Speaker: {data.get('speaker') or '—'}"
    )
    st.markdown("### Policy-signal assessment")
    if data.get("status") == "insufficient_input":
        st.warning(data.get("justification") or "The supplied speech could not be classified.")
    else:
        st.write(data.get("justification") or "No justification returned.")

    st.markdown("### Supporting evidence")
    _render_evidence_table(data.get("evidence") or [])


def _render_readable_result(part: AssignmentPart, result: Any) -> None:
    data = result.model_dump(mode="json")
    renderers = {
        AssignmentPart.A: _render_part_a_result,
        AssignmentPart.B: _render_part_b_result,
        AssignmentPart.C: _render_part_c_result,
        AssignmentPart.D: _render_part_d_result,
    }
    renderers[part](data)


def main() -> None:
    st.set_page_config(page_title="Monetary Policy Assistant", page_icon="🏦", layout="wide")
    config = RuntimeConfig.from_env()

    st.title("Monetary Policy Assignment Assistant")
    st.caption(
        "Run one source-grounded task at a time. API keys are used in memory and are never "
        "written by this application."
    )

    with st.sidebar:
        st.header("Runtime")
        model = st.text_input("OpenAI model", value=config.model)
        api_key_input = st.text_input(
            "OpenAI API key",
            type="password",
            placeholder="Uses OPENAI_API_KEY when left blank",
            help="The key is passed directly to the SDK and is not saved to a file.",
        )
        selected_label = st.selectbox("Assignment task", tuple(PART_LABELS))

    part = PART_LABELS[selected_label]
    st.subheader(selected_label)

    input_renderers = {
        AssignmentPart.A: _part_a_inputs,
        AssignmentPart.B: _part_b_inputs,
        AssignmentPart.C: _part_c_inputs,
        AssignmentPart.D: _part_d_inputs,
    }
    with st.form(f"part_{part.value.lower()}_form"):
        values = input_renderers[part]()
        submitted = st.form_submit_button("Run task", type="primary", use_container_width=True)

    if submitted:
        validation_message = _validate_inputs(part, values)
        api_key = config.resolved_api_key(api_key_input)
        if validation_message:
            st.error(validation_message)
        elif not api_key:
            st.error("Enter an API key or set OPENAI_API_KEY in the process environment.")
        elif not model.strip():
            st.error("Enter an OpenAI model name.")
        else:
            try:
                service = AssignmentService(
                    OpenAIResponsesLLM.from_api_key(api_key, model=model),
                    prompt_dir=config.prompt_dir,
                )
                with st.spinner("Running structured extraction..."):
                    result = service.run(part, **values)
                st.session_state["last_result"] = result
                st.session_state["last_part"] = part.value
            except (PromptError, StructuredResponseError, ValidationError, ValueError) as exc:
                st.error(f"Task failed: {exc}")
            except OpenAIError as exc:
                st.error(f"OpenAI request failed: {exc}")

    result = st.session_state.get("last_result")
    result_part = st.session_state.get("last_part")
    if result is not None and result_part == part.value:
        st.success("Validated structured result")
        _render_readable_result(part, result)
        st.divider()
        st.subheader("Validated JSON")
        st.json(result.model_dump(mode="json"))
        _render_downloads(part, result)


if __name__ == "__main__":
    main()
