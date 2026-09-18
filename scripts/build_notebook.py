#!/usr/bin/env python3
"""Create the reproducible Part C analysis notebook."""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = PROJECT_ROOT / "notebooks" / "01_recommendation_quality_assessment.ipynb"


def build_notebook() -> None:
    notebook = nbf.v4.new_notebook()
    notebook["metadata"] = {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {"name": "python", "version": "3.11"},
    }
    notebook["cells"] = [
        nbf.v4.new_markdown_cell(
            """# Recommendation quality in three IMF technical-assistance reports

This notebook validates and summarizes a schema-constrained reference assessment of 24 recommendations (eight per report). Scores are model judgments produced by the Part C prompt; they are not human ratings, and the purposive sample does not support population-wide claims about IMF recommendations."""
        ),
        nbf.v4.new_code_cell(
            """from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
RESULTS = ROOT / "data" / "results"

assessments = pd.read_csv(RESULTS / "recommendation_quality_assessments.csv")
summary = pd.read_csv(RESULTS / "recommendation_quality_summary.csv")
assessments.shape, summary.shape"""
        ),
        nbf.v4.new_markdown_cell("## Validation checks"),
        nbf.v4.new_code_cell(
            """score_columns = [
    "specificity_score",
    "actionability_score",
    "internal_consistency_score",
    "overall_score",
]

assert len(assessments) == 24
assert assessments["recommendation_id"].is_unique
assert assessments.groupby("country").size().eq(8).all()
assert assessments[score_columns].notna().all().all()
assert assessments[score_columns].apply(lambda col: col.between(1, 5).all()).all()
assert assessments["original_text"].str.strip().ne("").all()
print("Passed: 24 unique, complete, in-range assessments with an 8/8/8 report split.")"""
        ),
        nbf.v4.new_markdown_cell("## Report-level comparison"),
        nbf.v4.new_code_cell(
            """display_columns = [
    "country",
    "n_recommendations",
    "mean_specificity",
    "mean_actionability",
    "mean_internal_consistency",
    "mean_overall",
    "high_count",
    "medium_count",
    "low_count",
]
summary[display_columns].style.format(
    {
        "mean_specificity": "{:.2f}",
        "mean_actionability": "{:.2f}",
        "mean_internal_consistency": "{:.2f}",
        "mean_overall": "{:.2f}",
    }
)"""
        ),
        nbf.v4.new_code_cell(
            """dimensions = [
    ("Specificity", "mean_specificity", "#2F6B9A"),
    ("Actionability", "mean_actionability", "#D18B24"),
    ("Internal consistency", "mean_internal_consistency", "#287D6C"),
]
x = np.arange(len(summary))
width = 0.24

fig, ax = plt.subplots(figsize=(10, 6), facecolor="white")
for index, (label, field, color) in enumerate(dimensions):
    values = summary[field].tolist()
    bars = ax.bar(
        x + (index - 1) * width,
        values,
        width,
        label=label,
        color=color,
        edgecolor="#333333",
        linewidth=0.5,
    )
    ax.bar_label(bars, labels=[f"{value:.2f}" for value in values], padding=3)

ax.set_title("Mean recommendation-quality scores (8 recommendations per report)")
ax.set_ylabel("Mean score (1 = low, 5 = high)")
ax.set_xticks(x, summary["country"])
ax.set_ylim(0, 5.35)
ax.set_yticks(range(6))
ax.grid(axis="y", color="#D9D9D9", linewidth=0.8)
ax.set_axisbelow(True)
ax.spines[["top", "right"]].set_visible(False)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.10), ncol=3, frameon=False)
fig.tight_layout()
plt.show()"""
        ),
        nbf.v4.new_markdown_cell("## Distribution and diagnostic cases"),
        nbf.v4.new_code_cell(
            """overall = {
    "n": len(assessments),
    "mean_specificity": assessments["specificity_score"].mean(),
    "mean_actionability": assessments["actionability_score"].mean(),
    "mean_internal_consistency": assessments["internal_consistency_score"].mean(),
    "mean_overall": assessments["overall_score"].mean(),
}
pd.Series(overall).round(2)"""
        ),
        nbf.v4.new_code_cell(
            """assessment_mix = pd.crosstab(
    assessments["country"],
    assessments["overall_assessment"],
).reindex(columns=["High", "Medium", "Low"], fill_value=0)
evidence_mix = pd.crosstab(
    assessments["country"],
    assessments["evidence_status"],
)
assessment_mix, evidence_mix"""
        ),
        nbf.v4.new_code_cell(
            """diagnostic = assessments.loc[
    (assessments["specificity_score"] <= 2) | (assessments["actionability_score"] <= 2),
    [
        "country",
        "recommendation_id",
        "original_text",
        "specificity_score",
        "actionability_score",
        "internal_consistency_score",
        "overall_score",
    ],
].sort_values(["overall_score", "recommendation_id"])
diagnostic"""
        ),
        nbf.v4.new_markdown_cell(
            """## Interpretation

- The strongest pattern is alignment rather than standalone operational detail: internal-consistency means are 4.88–5.00, while specificity and actionability means are 2.75–3.00.
- Ukraine has the highest mean overall score in this sample, but the between-report differences are small and should not be interpreted as a ranking of countries or IMF teams.
- The arithmetic mean can hide a weak dimension. For example, a recommendation with an editorial placeholder can remain “Medium” overall when the body strongly supports its intended direction; dimension-level scores and justifications should therefore remain visible.
- Nearly every recommendation is supported by its report body. The practical improvement opportunity is to make the recommendation rows more self-contained by naming ownership, sequencing, operating conditions, and completion criteria where relevant."""
        ),
        nbf.v4.new_markdown_cell(
            """## Limitations

The sample is purposive, limited to eight recommendations from each of three reports, and includes a deliberately retained low-specificity edge case from the Sri Lanka source table. Scores come from one schema-constrained model run and were automatically checked for structure, source identity, verbatim recommendation text, and evidence substrings, but they were not independently adjudicated by a monetary-policy expert."""
        ),
    ]

    NOTEBOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(notebook, NOTEBOOK_PATH)
    print(f"Wrote {NOTEBOOK_PATH}")


if __name__ == "__main__":
    build_notebook()
