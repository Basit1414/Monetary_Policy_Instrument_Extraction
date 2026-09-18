"""Integrity checks for the checked-in Part C reference artifacts.

The test intentionally uses only the Python standard library so artifact
validation does not depend on the analysis or application dependency stack.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORT_MANIFEST = ROOT / "data/reports/manifest.json"
RECOMMENDATIONS = ROOT / "data/reports/recommendations.json"
RESULT_JSON = ROOT / "data/results/recommendation_quality_assessments.json"
RESULT_CSV = ROOT / "data/results/recommendation_quality_assessments.csv"
SUMMARY_CSV = ROOT / "data/results/recommendation_quality_summary.csv"
FIGURE = ROOT / "reports/figures/recommendation_quality_by_report.png"
NOTEBOOK = ROOT / "notebooks/01_recommendation_quality_assessment.ipynb"

DIMENSIONS = ("specificity", "actionability", "internal_consistency")
CSV_SCORE_COLUMNS = tuple(f"{dimension}_score" for dimension in DIMENSIONS)


def _read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _source_inventory() -> tuple[set[str], set[str]]:
    manifest = _read_json(REPORT_MANIFEST)
    assert isinstance(manifest, list)
    assert len(manifest) == 3

    report_ids = {entry["slug"] for entry in manifest}
    assert len(report_ids) == 3

    recommendations = _read_json(RECOMMENDATIONS)
    records = recommendations["records"]
    recommendation_ids = [record["recommendation_id"] for record in records]
    counts = Counter(record["report_slug"] for record in records)

    assert recommendations["recommendation_count"] == 24
    assert len(records) == 24
    assert len(set(recommendation_ids)) == 24
    assert counts == Counter({report_id: 8 for report_id in report_ids})
    assert recommendations["per_report_counts"] == dict(counts)
    return report_ids, set(recommendation_ids)


def test_reference_source_inventory_is_three_reports_and_twenty_four_unique_items() -> None:
    report_ids, recommendation_ids = _source_inventory()
    assert len(report_ids) == 3
    assert len(recommendation_ids) == 24


def test_result_json_and_csv_have_matching_counts_and_valid_scores() -> None:
    report_ids, source_recommendation_ids = _source_inventory()
    artifact = _read_json(RESULT_JSON)

    assert artifact["scope"]["reports"] == 3
    assert artifact["scope"]["recommendations"] == 24
    assert len(artifact["runs"]) == 3
    assert len(artifact["results"]) == 3
    assert {run["report_id"] for run in artifact["runs"]} == report_ids
    assert all(run["recommendation_count"] == 8 for run in artifact["runs"])

    json_ids: list[str] = []
    for result in artifact["results"]:
        assert result["report_id"] in report_ids
        assert len(result["assessments"]) == 8
        for assessment in result["assessments"]:
            json_ids.append(assessment["recommendation_id"])
            scores = [assessment[dimension]["score"] for dimension in DIMENSIONS]
            assert all(type(score) is int and 1 <= score <= 5 for score in scores)
            overall = assessment["overall_score"]
            assert type(overall) in {int, float} and not isinstance(overall, bool)
            assert 1 <= overall <= 5
            assert overall == round(sum(scores) / len(scores), 1)

    assert len(json_ids) == 24
    assert len(set(json_ids)) == 24
    assert set(json_ids) == source_recommendation_ids

    csv_rows = _read_csv(RESULT_CSV)
    csv_ids = [row["recommendation_id"] for row in csv_rows]
    assert len(csv_rows) == 24
    assert len(set(csv_ids)) == 24
    assert set(csv_ids) == source_recommendation_ids
    assert Counter(row["report_id"] for row in csv_rows) == Counter(
        {report_id: 8 for report_id in report_ids}
    )
    for row in csv_rows:
        dimension_scores = [int(row[column]) for column in CSV_SCORE_COLUMNS]
        assert all(1 <= score <= 5 for score in dimension_scores)
        overall = float(row["overall_score"])
        assert 1 <= overall <= 5
        assert overall == round(sum(dimension_scores) / len(dimension_scores), 1)


def test_summary_counts_cover_every_assessment_and_scores_are_in_range() -> None:
    report_ids, _ = _source_inventory()
    rows = _read_csv(SUMMARY_CSV)

    assert len(rows) == 3
    assert {row["report_id"] for row in rows} == report_ids
    assert sum(int(row["n_recommendations"]) for row in rows) == 24
    for row in rows:
        assert int(row["n_recommendations"]) == 8
        quality_counts = sum(
            int(row[column]) for column in ("high_count", "medium_count", "low_count")
        )
        evidence_counts = sum(
            int(row[column])
            for column in (
                "supported_count",
                "partially_supported_count",
                "contradicted_count",
                "not_enough_information_count",
            )
        )
        assert quality_counts == 8
        assert evidence_counts == 8
        for column in (
            "mean_specificity",
            "mean_actionability",
            "mean_internal_consistency",
            "mean_overall",
        ):
            assert 1 <= float(row[column]) <= 5


def test_figure_and_executed_notebook_are_complete() -> None:
    figure_bytes = FIGURE.read_bytes()
    assert len(figure_bytes) > 8
    assert figure_bytes.startswith(b"\x89PNG\r\n\x1a\n")

    notebook = _read_json(NOTEBOOK)
    assert notebook["nbformat"] == 4
    code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
    assert code_cells
    assert all(
        type(cell.get("execution_count")) is int and cell["execution_count"] >= 1
        for cell in code_cells
    )
    assert all(
        output.get("output_type") != "error"
        for cell in code_cells
        for output in cell.get("outputs", [])
    )
