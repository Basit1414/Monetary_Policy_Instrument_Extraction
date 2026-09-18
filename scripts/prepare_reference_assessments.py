#!/usr/bin/env python3
"""Build deterministic Part C prompts and a JSON Schema for reference runs.

This script performs no network or model calls. It joins the reviewed IMF
recommendation sample to the page-aware local report extracts, renders the
version-controlled Part C prompt, and records hashes for auditability.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from mpie.prompts import AssignmentPart, render_part_prompt
from mpie.schemas import RecommendationQualityResult

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "outputs" / "reference_inputs"


def parse_page_range(value: str) -> range:
    """Parse an inclusive printed-page range such as ``11-37``."""

    start_text, end_text = value.split("-", maxsplit=1)
    start, end = int(start_text), int(end_text)
    if start < 1 or end < start:
        raise ValueError(f"invalid page range: {value!r}")
    return range(start, end + 1)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def report_body(entry: dict[str, Any]) -> str:
    page_path = PROJECT_ROOT / entry["extracted_pages_json_path"]
    page_data = load_json(page_path)
    allowed = set(parse_page_range(entry["body_pages"]))
    selected = [page for page in page_data["pages"] if page["printed_page_number"] in allowed]
    if {page["printed_page_number"] for page in selected} != allowed:
        raise ValueError(f"missing body pages for {entry['slug']}")
    return "\n\n".join(
        f"--- Printed page {page['printed_page_number']} ---\n{page['text']}" for page in selected
    )


def recommendation_payload(records: list[dict[str, Any]]) -> str:
    items = [
        {
            "recommendation_id": record["recommendation_id"],
            "original_text": record["recommendation_text_verbatim"],
            "priority": record["priority"],
            "timeframe": record["timeframe"],
            "table_group": record["table_group"],
            "table_paragraph_refs": record["table_paragraph_refs"],
            "source_table_printed_page": record["recommendation_printed_page"],
        }
        for record in sorted(records, key=lambda item: item["selected_rank"])
    ]
    return json.dumps(items, ensure_ascii=False, indent=2)


def build(output_dir: Path) -> dict[str, Any]:
    manifest = load_json(PROJECT_ROOT / "data" / "reports" / "manifest.json")
    sample = load_json(PROJECT_ROOT / "data" / "reports" / "recommendations.json")
    records = sample["records"]
    output_dir.mkdir(parents=True, exist_ok=True)

    schema_path = output_dir / "recommendation_quality.schema.json"
    schema_path.write_text(
        json.dumps(RecommendationQualityResult.model_json_schema(), indent=2) + "\n",
        encoding="utf-8",
    )

    runs: list[dict[str, Any]] = []
    for entry in manifest:
        report_records = [record for record in records if record["report_slug"] == entry["slug"]]
        if len(report_records) != 8:
            raise ValueError(f"expected 8 recommendations for {entry['slug']}")

        body = report_body(entry)
        recommendations = recommendation_payload(report_records)
        prompt = render_part_prompt(
            AssignmentPart.C,
            values={
                "REPORT_ID": entry["slug"],
                "RECOMMENDATIONS": recommendations,
                "REPORT_CONTENT": body,
            },
        )
        prompt_path = output_dir / f"{entry['slug']}.prompt.md"
        prompt_path.write_text(prompt, encoding="utf-8")
        runs.append(
            {
                "report_id": entry["slug"],
                "country": entry["country"],
                "recommendation_ids": [
                    record["recommendation_id"]
                    for record in sorted(report_records, key=lambda item: item["selected_rank"])
                ],
                "recommendation_count": len(report_records),
                "body_printed_pages": entry["body_pages"],
                "source_pdf_sha256": entry["sha256"],
                "prompt_path": str(prompt_path.relative_to(PROJECT_ROOT)),
                "prompt_sha256": sha256_text(prompt),
            }
        )

    metadata = {
        "schema_version": "1.0",
        "prompt_template": "prompts/part_c_recommendation_quality.md",
        "schema_path": str(schema_path.relative_to(PROJECT_ROOT)),
        "runs": runs,
    }
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    metadata = build(args.output_dir.resolve())
    print(
        f"Prepared {len(metadata['runs'])} prompts and "
        f"{sum(run['recommendation_count'] for run in metadata['runs'])} recommendations."
    )


if __name__ == "__main__":
    main()
