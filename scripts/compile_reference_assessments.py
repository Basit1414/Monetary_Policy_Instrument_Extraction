#!/usr/bin/env python3
"""Validate, compile, summarize, and chart the three Part C reference runs."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any

from mpie.schemas import RecommendationQualityResult

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = PROJECT_ROOT / "outputs" / "reference_results"
RESULTS_DIR = PROJECT_ROOT / "data" / "results"
FIGURES_DIR = PROJECT_ROOT / "reports" / "figures"


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def body_text(manifest_entry: dict[str, Any]) -> str:
    pages = load_json(PROJECT_ROOT / manifest_entry["extracted_pages_json_path"])["pages"]
    start_text, end_text = manifest_entry["body_pages"].split("-", maxsplit=1)
    allowed = set(range(int(start_text), int(end_text) + 1))
    return "\n".join(page["text"] for page in pages if page["printed_page_number"] in allowed)


def verify_evidence(
    assessment: dict[str, Any],
    body: str,
) -> None:
    recommendation = normalized(assessment["original_text"])
    for dimension in ("specificity", "actionability"):
        for evidence in assessment[dimension]["evidence"]:
            if evidence["source"] != "recommendations":
                raise ValueError(
                    f"{assessment['recommendation_id']} {dimension} evidence has wrong source"
                )
            if normalized(evidence["quote"]) not in recommendation:
                raise ValueError(
                    f"{assessment['recommendation_id']} {dimension} evidence is not verbatim"
                )

    normalized_body = normalized(body)
    for evidence in assessment["internal_consistency"]["evidence"]:
        if assessment["evidence_status"] == "not_enough_information":
            expected = "Not enough information in the supplied report body"
            if evidence["quote"] != expected:
                raise ValueError(
                    f"{assessment['recommendation_id']} uses the wrong evidence sentinel"
                )
        elif evidence["source"] != "report_content":
            raise ValueError(
                f"{assessment['recommendation_id']} consistency evidence has wrong source"
            )
        elif normalized(evidence["quote"]) not in normalized_body:
            raise ValueError(
                f"{assessment['recommendation_id']} consistency evidence is not verbatim"
            )


def flatten_record(
    assessment: dict[str, Any],
    source: dict[str, Any],
    manifest_entry: dict[str, Any],
) -> dict[str, Any]:
    def evidence_text(dimension: str) -> str:
        return " | ".join(item["quote"] for item in assessment[dimension]["evidence"])

    return {
        "report_id": manifest_entry["slug"],
        "country": manifest_entry["country"],
        "report_title": manifest_entry["title"],
        "publication_date": manifest_entry["publication_date"],
        "landing_url": manifest_entry["landing_url"],
        "pdf_url": manifest_entry["pdf_url"],
        "recommendation_id": assessment["recommendation_id"],
        "original_text": assessment["original_text"],
        "priority": source["priority"],
        "timeframe": source["timeframe"],
        "table_group": source["table_group"],
        "recommendation_printed_page": source["recommendation_printed_page"],
        "body_section": source["body_section"],
        "body_context_printed_page": source["body_context_printed_page"],
        "specificity_score": assessment["specificity"]["score"],
        "specificity_justification": assessment["specificity"]["justification"],
        "specificity_evidence": evidence_text("specificity"),
        "actionability_score": assessment["actionability"]["score"],
        "actionability_justification": assessment["actionability"]["justification"],
        "actionability_evidence": evidence_text("actionability"),
        "internal_consistency_score": assessment["internal_consistency"]["score"],
        "internal_consistency_justification": assessment["internal_consistency"]["justification"],
        "internal_consistency_evidence": evidence_text("internal_consistency"),
        "evidence_status": assessment["evidence_status"],
        "overall_score": assessment["overall_score"],
        "overall_assessment": assessment["overall_assessment"],
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    report_ids = list(dict.fromkeys(row["report_id"] for row in rows))
    for report_id in report_ids:
        group = [row for row in rows if row["report_id"] == report_id]
        labels = Counter(row["overall_assessment"] for row in group)
        statuses = Counter(row["evidence_status"] for row in group)
        output.append(
            {
                "report_id": report_id,
                "country": group[0]["country"],
                "n_recommendations": len(group),
                "mean_specificity": round(mean(row["specificity_score"] for row in group), 2),
                "mean_actionability": round(mean(row["actionability_score"] for row in group), 2),
                "mean_internal_consistency": round(
                    mean(row["internal_consistency_score"] for row in group), 2
                ),
                "mean_overall": round(mean(row["overall_score"] for row in group), 2),
                "high_count": labels["High"],
                "medium_count": labels["Medium"],
                "low_count": labels["Low"],
                "supported_count": statuses["supported"],
                "partially_supported_count": statuses["partially_supported"],
                "contradicted_count": statuses["contradicted"],
                "not_enough_information_count": statuses["not_enough_information"],
            }
        )
    return output


def chart(summary: list[dict[str, Any]]) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    countries = [row["country"] for row in summary]
    dimensions = [
        ("Specificity", "mean_specificity", "#2F6B9A"),
        ("Actionability", "mean_actionability", "#D18B24"),
        ("Internal consistency", "mean_internal_consistency", "#287D6C"),
    ]
    x = np.arange(len(countries))
    width = 0.24

    fig, ax = plt.subplots(figsize=(10, 6), facecolor="white")
    ax.set_facecolor("white")
    for index, (label, field, color) in enumerate(dimensions):
        values = [row[field] for row in summary]
        bars = ax.bar(
            x + (index - 1) * width,
            values,
            width,
            label=label,
            color=color,
            edgecolor="#333333",
            linewidth=0.5,
        )
        ax.bar_label(bars, labels=[f"{value:.2f}" for value in values], padding=3, fontsize=9)

    ax.set_title("Mean recommendation-quality scores (8 recommendations per report)")
    ax.set_ylabel("Mean score (1 = low, 5 = high)")
    ax.set_xticks(x, countries)
    ax.set_ylim(0, 5.35)
    ax.set_yticks(range(6))
    ax.grid(axis="y", color="#D9D9D9", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.10), ncol=3, frameon=False)
    fig.text(
        0.01,
        0.01,
        "Source: schema-validated reference run using public IMF TA reports; scores are model judgments, not human ratings.",
        fontsize=8,
        color="#555555",
    )
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES_DIR / "recommendation_quality_by_report.png", dpi=200)
    plt.close(fig)


def main() -> None:
    manifest = load_json(PROJECT_ROOT / "data" / "reports" / "manifest.json")
    source_sample = load_json(PROJECT_ROOT / "data" / "reports" / "recommendations.json")
    run_metadata = load_json(PROJECT_ROOT / "outputs" / "reference_inputs" / "metadata.json")
    manifest_by_id = {entry["slug"]: entry for entry in manifest}
    source_by_id = {record["recommendation_id"]: record for record in source_sample["records"]}
    expected_ids_by_report = {
        run["report_id"]: run["recommendation_ids"] for run in run_metadata["runs"]
    }

    nested_results: list[dict[str, Any]] = []
    flat_rows: list[dict[str, Any]] = []
    for report_id, manifest_entry in manifest_by_id.items():
        path = INPUT_DIR / f"{report_id}.json"
        validated = RecommendationQualityResult.model_validate(load_json(path))
        result = validated.model_dump(mode="json")
        if result["report_id"] != report_id:
            raise ValueError(f"report id mismatch in {path}")
        actual_ids = [item["recommendation_id"] for item in result["assessments"]]
        if actual_ids != expected_ids_by_report[report_id]:
            raise ValueError(f"recommendation order/id mismatch in {path}")

        body = body_text(manifest_entry)
        for assessment in result["assessments"]:
            source = source_by_id[assessment["recommendation_id"]]
            if assessment["original_text"] != source["recommendation_text_verbatim"]:
                raise ValueError(f"original text mismatch for {assessment['recommendation_id']}")
            verify_evidence(assessment, body)
            flat_rows.append(flatten_record(assessment, source, manifest_entry))
        nested_results.append(result)

    summary = summarize(flat_rows)
    generated_at = datetime.now(UTC).isoformat(timespec="seconds")
    artifact = {
        "schema_version": "1.0",
        "generated_at": generated_at,
        "execution": {
            "engine": "OpenAI Codex CLI",
            "model": "gpt-5.6-terra",
            "reasoning_effort": "medium",
            "api": "Codex sign-in; no OPENAI_API_KEY used",
            "prompt_template": run_metadata["prompt_template"],
            "structured_output_schema": run_metadata["schema_path"],
        },
        "scope": {
            "reports": len(nested_results),
            "recommendations": len(flat_rows),
            "selection": "Eight purposively selected recommendations per report; not a statistical sample.",
        },
        "validation": {
            "pydantic_schema": "passed",
            "report_and_recommendation_ids": "passed",
            "verbatim_recommendation_text": "passed",
            "verbatim_evidence_substrings": "passed",
            "human_adjudication": "not_performed",
        },
        "runs": run_metadata["runs"],
        "results": nested_results,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "recommendation_quality_assessments.json").write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_csv(RESULTS_DIR / "recommendation_quality_assessments.csv", flat_rows)
    write_csv(RESULTS_DIR / "recommendation_quality_summary.csv", summary)
    chart(summary)
    print(f"Compiled {len(flat_rows)} validated assessments across {len(summary)} reports.")


if __name__ == "__main__":
    main()
